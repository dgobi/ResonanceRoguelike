#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    io::{Read, Write},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc, Mutex,
    },
    time::{Duration, Instant},
};
use tauri::{Emitter, Manager};
mod authoring;

const PROTOCOL: u64 = 4;
const MAX_OUTPUT: u64 = 16 * 1024 * 1024;

#[derive(Debug, Clone, Serialize)]
struct Failure {
    code: String,
    message: String,
    remedy: String,
}
fn failure(code: &str, message: impl ToString, remedy: &str) -> Failure {
    Failure {
        code: code.into(),
        message: message.to_string(),
        remedy: remedy.into(),
    }
}
#[derive(Default)]
struct Session {
    root: Option<PathBuf>,
    child: Option<Child>,
    scratch: Option<tempfile::TempDir>,
    busy: bool,
    discovered: std::collections::HashSet<String>,
    document: Option<authoring::Document>,
    pool_document: Option<authoring::Document>,
    applying: bool,
}
#[derive(Default, Clone)]
struct Host {
    inner: Arc<Mutex<Session>>,
    epoch: Arc<AtomicU64>,
    ids: Arc<AtomicU64>,
}
impl Host {
    fn cancel(&self, clear: bool) -> Result<(), Failure> {
        let mut state = self.inner.lock().unwrap();
        if state.applying {
            return Err(failure(
                "BUSY",
                "A validated file transaction is in progress.",
                "Wait for its result before closing or cancelling.",
            ));
        }
        self.epoch.fetch_add(1, Ordering::SeqCst);
        if let Some(mut child) = state.child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        state.busy = false;
        if clear {
            state.root = None;
            state.discovered.clear();
            state.document = None;
            state.pool_document = None;
        }
        cleanup_scratch(&mut state)
    }
}

fn cleanup_scratch(state: &mut Session) -> Result<(), Failure> {
    if let Some(directory) = state.scratch.take() {
        // This exact absolute path was created by tempfile, never supplied by
        // the frontend. Windows may retain short-lived process/scanner locks.
        let owned_path = directory.path().to_path_buf();
        if directory.close().is_err() {
            for _ in 0..40 {
                std::thread::sleep(Duration::from_millis(25));
                if !owned_path.exists() || std::fs::remove_dir_all(&owned_path).is_ok() {
                    return Ok(());
                }
            }
            return Err(failure("TEMP_CLEANUP_FAILED", format!("Unable to remove temporary preview directory {}", owned_path.display()), "A file is still locked. Close the locking process and remove this temporary preview directory."));
        }
    }
    Ok(())
}

fn canonical_root(path: &Path) -> Result<PathBuf, Failure> {
    let canonical = dunce::canonicalize(path).map_err(|e| {
        failure(
            "INVALID_PROJECT",
            e,
            "Choose an existing Resonance repository directory.",
        )
    })?;
    if !canonical.is_dir() {
        return Err(failure(
            "INVALID_PROJECT",
            "Expected a directory.",
            "Choose the repository root.",
        ));
    }
    // Permit selecting the roguelike subfolder, but never search unrelated parents.
    let root = if canonical.file_name().is_some_and(|n| n == "roguelike") {
        canonical.parent().unwrap().to_path_buf()
    } else {
        canonical
    };
    for file in [
        "roguelike/engine/data_loader.py",
        "roguelike/generation/structure_contract.py",
        "roguelike/generation/structure_preview.py",
        "roguelike/data/terrain.json",
        "requirements-baseline.txt",
    ] {
        let p = dunce::canonicalize(root.join(file)).map_err(|_| {
            failure(
                "INVALID_PROJECT",
                format!("Missing {file}"),
                "Choose the Resonance checkout, not a save or unrelated folder.",
            )
        })?;
        if !p.is_file() || !p.starts_with(&root) {
            return Err(failure(
                "INVALID_PROJECT",
                "External project marker",
                "Choose a complete local checkout.",
            ));
        }
    }
    Ok(root)
}

fn runtime(app: &tauri::AppHandle, root: &Path) -> Result<(PathBuf, PathBuf), Failure> {
    let resource = app
        .path()
        .resource_dir()
        .map_err(|e| failure("WORKER_MISSING", e, "Rebuild the desktop package."))?;
    let dev = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../worker");
    let script = if cfg!(debug_assertions) {
        dev.join("bridge.py")
    } else {
        resource.join("bridge.py")
    };
    let packaged = if cfg!(debug_assertions) {
        dev.join("runtime/python.exe")
    } else {
        resource.join("python/python.exe")
    };
    let python = if let Some(value) = std::env::var_os("RESONANCE_PYTHON") {
        let path = PathBuf::from(value);
        if !path.is_absolute() {
            return Err(failure(
                "WORKER_MISSING",
                "RESONANCE_PYTHON must be an absolute interpreter path.",
                "Set it in the launching shell, then restart.",
            ));
        }
        path
    } else if packaged.is_file() {
        packaged
    } else {
        root.join(".venv/Scripts/python.exe")
    };
    if !python.is_file() || !script.is_file() {
        return Err(failure("WORKER_MISSING", format!("Python: {}; bridge: {}", python.display(), script.display()), "Set RESONANCE_PYTHON to the pinned Python 3.11 executable, or build the bundled runtime using scripts/prepare-runtime.ps1; then restart."));
    }
    Ok((python, script))
}

#[derive(Deserialize, Default)]
#[serde(deny_unknown_fields)]
struct Request {
    op: String,
    asset: Option<String>,
    seed: Option<u32>,
    invalid_fixture: Option<bool>,
    draft: Option<String>,
}
fn validate_request(request: &Request) -> Result<(), Failure> {
    if ![
        "identify",
        "describe",
        "inspect",
        "preview",
        "validate_draft",
        "preview_draft",
    ]
    .contains(&request.op.as_str())
    {
        return Err(failure(
            "UNSUPPORTED_OPERATION",
            "Only W0 requests are allowed.",
            "Use the supported controls.",
        ));
    }
    if ["inspect", "preview", "validate_draft", "preview_draft"].contains(&request.op.as_str()) {
        let asset = request.asset.as_deref().unwrap_or("");
        let parts: Vec<_> = asset.split('/').collect();
        let layout = parts.len() == 4
            && parts[..3] == ["roguelike", "data", "layouts"]
            && authoring::valid_filename(parts[3]);
        if !layout && !authoring::is_pool(asset) && authoring::relative_building(asset).is_err() {
            return Err(failure(
                "PATH_ESCAPE",
                "Asset is outside the W0 layout route.",
                "Select a shipped layout from the list.",
            ));
        }
    }
    if request
        .draft
        .as_ref()
        .is_some_and(|s| s.len() > authoring::MAX_DRAFT)
        || (["validate_draft", "preview_draft"].contains(&request.op.as_str()))
            != request.draft.is_some()
    {
        return Err(failure(
            "MALFORMED_REQUEST",
            "Draft operation or size is invalid.",
            "Use the bounded authoring controls.",
        ));
    }
    if request.seed.is_some_and(|s| s > i32::MAX as u32)
        || (request.invalid_fixture == Some(true) && request.op != "inspect")
    {
        return Err(failure(
            "MALFORMED_REQUEST",
            "Invalid seed or fixture operation.",
            "Use the supported W0 inputs.",
        ));
    }
    Ok(())
}

fn parse_response(bytes: &[u8], id: &str) -> Result<Value, Failure> {
    let response: Value = serde_json::from_slice(bytes).map_err(|e| {
        failure(
            "MALFORMED_WORKER_OUTPUT",
            e,
            "Rebuild the matching worker. Diagnostics must use stderr.",
        )
    })?;
    if response["protocol"].as_u64() != Some(PROTOCOL) || response["id"].as_str() != Some(id) {
        return Err(failure(
            "PROTOCOL_MISMATCH",
            "Worker version or correlation ID does not match.",
            "Rebuild matching frontend, host and worker.",
        ));
    }
    match response["ok"].as_bool() {
        Some(true) if response["result"].is_object() => Ok(response),
        Some(false)
            if response["error"]["code"].is_string()
                && response["error"]["message"].is_string() =>
        {
            Ok(response)
        }
        _ => Err(failure(
            "MALFORMED_WORKER_OUTPUT",
            "Invalid response envelope.",
            "Rebuild the matching worker.",
        )),
    }
}

fn run_worker(
    app: tauri::AppHandle,
    host: Host,
    request: Request,
    expected_epoch: u64,
) -> Result<Value, Failure> {
    validate_request(&request)?;
    let id = format!("w0-{}", host.ids.fetch_add(1, Ordering::SeqCst));
    let mut state = host.inner.lock().unwrap();
    if host.epoch.load(Ordering::SeqCst) != expected_epoch {
        return Err(failure(
            "CANCELLED",
            "Project changed.",
            "Open the new project.",
        ));
    }
    if state.busy {
        return Err(failure(
            "BUSY",
            "A worker request is already running.",
            "Wait or cancel the current request.",
        ));
    }
    let root = state.root.clone().ok_or_else(|| {
        failure(
            "NO_PROJECT",
            "No repository is open.",
            "Choose a Resonance repository.",
        )
    })?;
    let (python, script) = runtime(&app, &root)?;
    // Parent-owned scratch survives until cancellation/exit is reaped, including
    // hard kills. Child tempdirs live here; no game-tree cwd or cache writes.
    let scratch = tempfile::Builder::new()
        .prefix("resonance-w0-host-")
        .tempdir()
        .map_err(|e| failure("TEMP_FAILED", e, "Check the system temporary directory."))?;
    let mut command = Command::new(python);
    command
        .args(["-I", "-B", "-u"])
        .arg(script)
        .arg("--root")
        .arg(&root)
        .current_dir(scratch.path())
        .env("TMP", scratch.path())
        .env("TEMP", scratch.path())
        .env("TMPDIR", scratch.path())
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = command.spawn().map_err(|e| {
        failure(
            "WORKER_START_FAILED",
            e,
            "Check the pinned interpreter, runtime DLLs and package resources.",
        )
    })?;
    let mut input = json!({"protocol": PROTOCOL, "id": id, "op": request.op});
    if let Some(value) = request.asset {
        input["asset"] = json!(value);
    }
    if let Some(value) = request.seed {
        input["seed"] = json!(value);
    }
    if let Some(value) = request.invalid_fixture {
        input["invalid_fixture"] = json!(value);
    }
    if let Some(value) = request.draft {
        input["draft"] = json!(value);
    }
    let sent = writeln!(child.stdin.take().unwrap(), "{}", input);
    if let Err(error) = sent {
        let _ = child.kill();
        let _ = child.wait();
        return Err(failure(
            "WORKER_EXIT",
            error,
            "Inspect the runtime and retry.",
        ));
    }
    let stdout = child.stdout.take().unwrap();
    let stderr = child.stderr.take().unwrap();
    // Bounded buffers while still draining pipes avoid deadlocks on diagnostics.
    fn drain(mut stream: impl Read) -> Vec<u8> {
        let mut output = Vec::new();
        let mut buffer = [0u8; 8192];
        while let Ok(n) = stream.read(&mut buffer) {
            if n == 0 {
                break;
            }
            if output.len() < MAX_OUTPUT as usize {
                output.extend_from_slice(&buffer[..n]);
            }
        }
        output
    }
    let output_thread = std::thread::spawn(move || drain(stdout));
    let diagnostic_thread = std::thread::spawn(move || drain(stderr));
    state.child = Some(child);
    state.scratch = Some(scratch);
    state.busy = true;
    drop(state);
    let start = Instant::now();
    let outcome = loop {
        let mut state = host.inner.lock().unwrap();
        if host.epoch.load(Ordering::SeqCst) != expected_epoch {
            break Err(failure(
                "CANCELLED",
                "Worker cancelled; disposable work discarded.",
                "Run the preview again when ready.",
            ));
        }
        let child = state.child.as_mut().unwrap();
        if start.elapsed() > Duration::from_secs(90) {
            let _ = child.kill();
            let _ = child.wait();
            state.child = None;
            state.busy = false;
            if let Err(error) = cleanup_scratch(&mut state) {
                break Err(error);
            }
            break Err(failure(
                "WORKER_TIMEOUT",
                "The worker exceeded 90 seconds.",
                "Check the selected source and retry.",
            ));
        }
        match child.try_wait() {
            Ok(Some(status)) => {
                state.child = None;
                state.busy = false;
                break cleanup_scratch(&mut state).map(|()| status);
            }
            Err(e) => {
                let _ = child.kill();
                let _ = child.wait();
                state.child = None;
                state.busy = false;
                if let Err(error) = cleanup_scratch(&mut state) {
                    break Err(error);
                }
                break Err(failure("WORKER_EXIT", e, "Reopen the repository."));
            }
            Ok(None) => {}
        }
        drop(state);
        std::thread::sleep(Duration::from_millis(15));
    };
    let bytes = output_thread.join().unwrap_or_default();
    let diagnostics = diagnostic_thread.join().unwrap_or_default();
    let status = outcome?;
    if !status.success() {
        return Err(failure(
            "WORKER_EXIT",
            format!(
                "Worker exited {status}: {}",
                String::from_utf8_lossy(&diagnostics[..diagnostics.len().min(4000)])
            ),
            "Check the Python runtime and reopen the repository.",
        ));
    }
    if bytes.len() > MAX_OUTPUT as usize {
        return Err(failure(
            "MALFORMED_WORKER_OUTPUT",
            "Worker output exceeded 16 MiB.",
            "Use a supported W0 preview.",
        ));
    }
    let mut response = parse_response(&bytes, &id)?;
    response["host_elapsed_ms"] = json!(start.elapsed().as_millis() as u64);
    if input["op"] == "describe" && response["ok"] == true {
        let mut state = host.inner.lock().unwrap();
        if host.epoch.load(Ordering::SeqCst) == expected_epoch {
            state.discovered = response["result"]["assets"]
                .as_array()
                .into_iter()
                .flatten()
                .filter(|a| a["editable"] == true)
                .filter_map(|a| a["path"].as_str().map(str::to_owned))
                .collect();
        }
    }
    Ok(response)
}

#[tauri::command]
async fn choose_project() -> Option<String> {
    rfd::AsyncFileDialog::new()
        .set_title("Choose Resonance source repository (read-only)")
        .pick_folder()
        .await
        .map(|p| p.path().to_string_lossy().into())
}
#[tauri::command]
async fn open_project(
    app: tauri::AppHandle,
    host: tauri::State<'_, Host>,
    path: String,
) -> Result<Value, Failure> {
    host.cancel(true)?;
    let root = canonical_root(Path::new(&path))?;
    host.inner.lock().unwrap().root = Some(root);
    let epoch = host.epoch.load(Ordering::SeqCst);
    let host = host.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        run_worker(
            app,
            host,
            Request {
                op: "identify".into(),
                asset: None,
                seed: None,
                invalid_fixture: None,
                draft: None,
            },
            epoch,
        )
    })
    .await
    .map_err(|e| failure("HOST_FAILED", e, "Restart Workbench."))?
}
#[tauri::command]
async fn worker_request(
    app: tauri::AppHandle,
    host: tauri::State<'_, Host>,
    request: Request,
) -> Result<Value, Failure> {
    if host.inner.lock().unwrap().applying
        || ["validate_draft", "preview_draft"].contains(&request.op.as_str())
    {
        return Err(failure(
            "UNSUPPORTED_OPERATION",
            "Use the document authoring boundary.",
            "Open a discovered building.",
        ));
    }
    let epoch = host.epoch.load(Ordering::SeqCst);
    let host = host.inner().clone();
    tauri::async_runtime::spawn_blocking(move || run_worker(app, host, request, epoch))
        .await
        .map_err(|e| failure("HOST_FAILED", e, "Restart Workbench."))?
}
#[tauri::command]
fn cancel_worker(host: tauri::State<'_, Host>) -> Result<(), Failure> {
    host.cancel(false)
}
#[tauri::command]
fn close_project(host: tauri::State<'_, Host>) -> Result<(), Failure> {
    host.cancel(true)
}

fn main() {
    tauri::Builder::default()
        .manage(Host::default())
        .invoke_handler(tauri::generate_handler![
            choose_project,
            open_project,
            worker_request,
            cancel_worker,
            close_project,
            authoring::open_document,
            authoring::validate_document,
            authoring::apply_document,
            authoring::document_disk,
            authoring::finish_close
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let host = window.state::<Host>();
                let state = host.inner.lock().unwrap();
                if state.applying || state.document.is_some() || state.pool_document.is_some() {
                    api.prevent_close();
                    let _ = window.emit("authoring-close-requested", ());
                    return;
                }
            }
            if matches!(
                event,
                tauri::WindowEvent::CloseRequested { .. } | tauri::WindowEvent::Destroyed
            ) {
                if let Err(error) = window.state::<Host>().cancel(true) {
                    eprintln!("{}: {}", error.code, error.message);
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("Unable to start Resonance Workbench");
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_unrelated_roots() {
        let t = tempfile::tempdir().unwrap();
        assert_eq!(
            canonical_root(t.path()).unwrap_err().code,
            "INVALID_PROJECT"
        );
    }
    #[test]
    fn rejects_traversal_and_unknown_operations() {
        for asset in [
            "../secrets.json",
            "roguelike/data/layouts/../secret.json",
            "C:/secrets.json",
            "roguelike/data/layouts/a\\b.json",
        ] {
            assert!(validate_request(&Request {
                op: "inspect".into(),
                asset: Some(asset.into()),
                seed: None,
                invalid_fixture: None,
                draft: None
            })
            .is_err());
        }
        assert!(validate_request(&Request {
            op: "exec".into(),
            asset: None,
            seed: None,
            invalid_fixture: None,
            draft: None
        })
        .is_err());
    }
    #[test]
    fn strict_envelopes() {
        assert!(parse_response(br#"{"protocol":4,"id":"x","ok":true,"result":{}}"#, "x").is_ok());
        for bytes in [
            br#"log line\n{}"#.as_slice(),
            br#"{"protocol":1,"id":"x","ok":true,"result":{}}"#,
            br#"{"protocol":1,"id":"y","ok":true,"result":{}}"#,
            br#"{"protocol":1,"id":"x","ok":true}"#,
            br#"{} {}"#,
        ] {
            assert!(parse_response(bytes, "x").is_err());
        }
    }
    #[test]
    fn cancellation_reaps_child() {
        let host = Host::default();
        // Exercise cancellation with a single live Python sleeper.
        let python = std::env::var("RESONANCE_PYTHON").unwrap_or("python".into());
        let mut command = Command::new(python);
        command.args(["-c", "import time; time.sleep(30)"]);
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000);
        }
        host.inner.lock().unwrap().child = Some(command.spawn().unwrap());
        host.cancel(true).unwrap();
        assert!(host.inner.lock().unwrap().child.is_none());
        assert_eq!(host.epoch.load(Ordering::SeqCst), 1);
    }
    #[test]
    #[cfg(windows)]
    fn cleanup_retries_a_transient_windows_file_lock() {
        use std::os::windows::fs::OpenOptionsExt;
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().to_path_buf();
        let lock = std::fs::OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .share_mode(0)
            .open(path.join("locked-fixture"))
            .unwrap();
        let release = std::thread::spawn(move || {
            std::thread::sleep(Duration::from_millis(100));
            drop(lock);
        });
        let mut state = Session {
            scratch: Some(directory),
            ..Default::default()
        };
        cleanup_scratch(&mut state).unwrap();
        release.join().unwrap();
        assert!(!path.exists());
    }
}
