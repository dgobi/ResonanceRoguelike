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
mod startup;
mod recovery;
mod room_test;

const PROTOCOL: u64 = 8;
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
    busy: Option<u64>,
    ready: bool,
    discovered: std::collections::HashSet<String>,
    discovered_families: std::collections::HashMap<String, String>,
    document: Option<authoring::Document>,
    pool_document: Option<authoring::Document>,
    content_documents: std::collections::HashMap<String, authoring::Document>,
    handoffs: std::collections::HashMap<String, authoring::Handoff>,
    applying: bool,
    closing: bool,
    pending_project: Option<(u64, ProjectConnection)>,
}
struct ProjectConnection {
    root: Option<PathBuf>,
    ready: bool,
    discovered: std::collections::HashSet<String>,
    families: std::collections::HashMap<String, String>,
}
fn restore_project(state: &mut Session, owner: Option<u64>) {
    if state.pending_project.as_ref().is_some_and(|(id, _)| owner.is_none_or(|owner| owner == *id)) {
        let (_, previous) = state.pending_project.take().unwrap();
        state.root = previous.root; state.ready = previous.ready;
        state.discovered = previous.discovered; state.discovered_families = previous.families;
    }
}
#[derive(Default, Clone)]
struct Host {
    inner: Arc<Mutex<Session>>,
    epoch: Arc<AtomicU64>,
    ids: Arc<AtomicU64>,
    recovery: Arc<Mutex<Option<recovery::Store>>>,
    games: room_test::Games,
}
impl Host {
    fn cancel(&self, clear: bool) -> Result<u64, Failure> {
        let mut state = self.inner.lock().unwrap();
        if state.applying {
            return Err(failure(
                "BUSY",
                "A validated file transaction is in progress.",
                "Wait for its result before closing or cancelling.",
            ));
        }
        let epoch = self.epoch.fetch_add(1, Ordering::SeqCst) + 1;
        state.closing=false;
        if let Some(mut child) = state.child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        state.busy = None;
        restore_project(&mut state, None);
        authoring::revoke_all(&mut state);
        if clear {
            if let Some(store)=self.recovery.lock().unwrap().as_mut(){store.release_all();}
            state.root = None;
            state.ready = false;
            state.discovered.clear();
            state.discovered_families.clear();
            state.document = None;
            state.pool_document = None;
            state.content_documents.clear();
            state.handoffs.clear();
        }
        cleanup_scratch(&mut state)?;
        Ok(epoch)
    }
}

fn busy_failure() -> Failure {
    failure("BUSY", "A request is active.", "Wait for its result, or cancel a validation before retrying.")
}

/// Owns one host request through result installation, not merely child exit.
/// Cancellation detaches this owner; its late cleanup cannot release a new one.
struct Operation {
    host: Host,
    id: u64,
    epoch: u64,
}
impl Operation {
    fn reserve(host: &Host, state: &mut Session, applying: bool) -> Result<Self, Failure> {
        if state.busy.is_some() || state.applying { return Err(busy_failure()); }
        let id = host.ids.fetch_add(1, Ordering::SeqCst);
        state.busy = Some(id);
        state.applying = applying;
        Ok(Self { host: host.clone(), id, epoch: host.epoch.load(Ordering::SeqCst) })
    }
    fn begin(host: &Host) -> Result<Self, Failure> {
        Self::reserve(host, &mut host.inner.lock().unwrap(), false)
    }
    fn check(&self, state: &Session) -> Result<(), Failure> {
        if self.host.epoch.load(Ordering::SeqCst) != self.epoch || state.busy != Some(self.id) {
            return Err(failure("CANCELLED", "Request cancelled or replaced.", "Validate the current draft again."));
        }
        Ok(())
    }
}
impl Drop for Operation {
    fn drop(&mut self) {
        let mut state = self.host.inner.lock().unwrap();
        if state.busy == Some(self.id) {
            restore_project(&mut state, Some(self.id));
            // Handled errors and unwinding release only this request's resources.
            if let Some(mut child) = state.child.take() { let _ = child.kill(); let _ = child.wait(); }
            let _ = cleanup_scratch(&mut state);
            state.busy = None;
            state.applying = false;
        }
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

const PROJECT_MARKERS: &[&str] = &[
    "roguelike/engine/data_loader.py", "roguelike/engine/creature_authoring.py",
    "roguelike/engine/recipe_authoring.py", "roguelike/generation/structure_contract.py",
    "roguelike/generation/structure_preview.py", "roguelike/data/terrain.json",
    "requirements-baseline.txt", "workbench/src-tauri/tauri.conf.json",
];
const PROJECT_DIRECTORIES: &[&str] = &[
    "roguelike/data/layouts", "roguelike/data/buildings", "roguelike/data/entities",
    "roguelike/data/items", "roguelike/data/recipes", "roguelike/data/loot_pools",
];

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
    for file in PROJECT_MARKERS {
        let p = dunce::canonicalize(root.join(file)).map_err(|_| {
            failure(
                "INVALID_PROJECT",
                format!("{}: missing {file}", root.display()),
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
    for directory in PROJECT_DIRECTORIES {
        let path = dunce::canonicalize(root.join(directory)).map_err(|_| failure("INVALID_PROJECT", format!("{}: missing {directory}", root.display()), "Choose the complete Resonance checkout."))?;
        if !path.is_dir() || !path.starts_with(&root) {
            return Err(failure("INVALID_PROJECT", format!("External data directory {directory}"), "Choose a checkout with local data."));
        }
    }
    Ok(root)
}

#[derive(Deserialize, Default)]
#[serde(deny_unknown_fields)]
struct Request {
    op: String,
    asset: Option<String>,
    seed: Option<u32>,
    invalid_fixture: Option<bool>,
    draft: Option<String>,
    source_asset: Option<String>,
    preview_inputs: Option<Value>,
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
        if !layout && asset != authoring::G17_EXAMPLE && !authoring::is_pool(asset) && authoring::content_root(asset).is_none() && !authoring::is_creature(asset) && authoring::relative_building(asset).is_err() {
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
    if request.preview_inputs.as_ref().is_some_and(|v| !v.is_object() || v.to_string().len() > 4096)
        || (request.preview_inputs.is_some() && request.op != "preview_draft") {
        return Err(failure("MALFORMED_REQUEST", "Preview inputs must be a bounded object on a draft request.", "Use the registered preview controls."));
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
    operation: &Operation,
    request: Request,
) -> Result<Value, Failure> {
    validate_request(&request)?;
    let host = &operation.host;
    let id = format!("w0-{}", host.ids.fetch_add(1, Ordering::SeqCst));
    let state = host.inner.lock().unwrap();
    operation.check(&state)?;
    let root = state.root.clone().ok_or_else(|| {
        failure(
            "NO_PROJECT",
            "No repository is open.",
            "Choose a Resonance repository.",
        )
    })?;
    if request.op != "identify" && !state.ready {
        return Err(failure("WORKER_NOT_READY", "No verified worker handshake for this project.", "Reopen the project and resolve the startup problem."));
    }
    drop(state);
    let runtime = startup::runtime(&app)?;
    // Parent-owned scratch survives until cancellation/exit is reaped, including
    // hard kills. Child tempdirs live here; no game-tree cwd or cache writes.
    let scratch = tempfile::Builder::new()
        .prefix("resonance-w0-host-")
        .tempdir()
        .map_err(|e| failure("TEMP_FAILED", e, "Check the system temporary directory."))?;
    let mut command = Command::new(&runtime.python);
    command
        .args(["-I", "-B", "-u"])
        .arg(&runtime.bridge)
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
    if let Some(value) = request.source_asset { input["source_asset"] = json!(value); }
    if let Some(value) = request.preview_inputs { input["preview_inputs"] = value; }
    if let Some(value) = request.seed {
        input["seed"] = json!(value);
    }
    if let Some(value) = request.invalid_fixture {
        input["invalid_fixture"] = json!(value);
    }
    if let Some(value) = request.draft {
        input["draft"] = json!(value);
    }
    let mut stdin = child.stdin.take().unwrap();
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
    let mut state = host.inner.lock().unwrap();
    if let Err(error) = operation.check(&state) {
        drop(state);
        let _ = child.kill(); let _ = child.wait();
        let _ = output_thread.join(); let _ = diagnostic_thread.join();
        return Err(error);
    }
    state.child = Some(child);
    state.scratch = Some(scratch);
    drop(state);
    let start = Instant::now();
    let sent = writeln!(stdin, "{}", input);
    drop(stdin);
    let outcome = loop {
        let mut state = host.inner.lock().unwrap();
        if let Err(error) = operation.check(&state) { break Err(error); }
        let child = state.child.as_mut().unwrap();
        if let Err(error) = &sent {
            let _ = child.kill(); let _ = child.wait(); state.child = None;
            break cleanup_scratch(&mut state).and(Err(failure("WORKER_EXIT", error, "Inspect the runtime and retry.")));
        }
        if start.elapsed() > Duration::from_secs(90) {
            let _ = child.kill();
            let _ = child.wait();
            state.child = None;
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
                break cleanup_scratch(&mut state).map(|()| status);
            }
            Err(e) => {
                let _ = child.kill();
                let _ = child.wait();
                state.child = None;
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
    operation.check(&host.inner.lock().unwrap())?;
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
    if input["op"] == "identify" && response["ok"] == true {
        verify_identity(&response["result"], &root, &runtime.bridge)?;
        let mut state = host.inner.lock().unwrap();
        operation.check(&state)?;
        state.ready = true;
        response["result"]["host_runtime"] = serde_json::to_value(runtime).unwrap();
    }
    if input["op"] == "describe" && response["ok"] == true {
        let mut state = host.inner.lock().unwrap();
        operation.check(&state)?;
        {
            state.discovered = response["result"]["assets"]
                .as_array()
                .into_iter()
                .flatten()
                .filter(|a| a["editable"] == true || a["route"] == "authored_submap" || a["family_id"].is_string() || a["route"] == "creature_definition")
                .filter_map(|a| a["path"].as_str().map(str::to_owned))
                .collect();
            state.discovered_families = response["result"]["assets"].as_array().into_iter().flatten()
                .filter_map(|a| Some((a["path"].as_str()?.to_owned(), a["family_id"].as_str()?.to_owned()))).collect();
        }
    }
    Ok(response)
}

fn verify_identity(identity: &Value, root: &Path, bridge: &Path) -> Result<(), Failure> {
    let same_root = identity["source"]["root"].as_str().and_then(|p| dunce::canonicalize(p).ok()).is_some_and(|p| p == root);
    let bridge_hash = std::fs::read(bridge).map(|bytes| authoring::hash(&bytes)).unwrap_or_default();
    if !same_root || identity["protocol"] != PROTOCOL || identity["worker_sha256"] != bridge_hash || identity["worker_version"] != env!("CARGO_PKG_VERSION")
        || identity["runtime"]["compatible"] != true || identity["runtime"]["imports_verified"] != true
        || identity["layout_contract"] != "authored-room-2" || !identity["families"].is_array()
        || identity["contract"] != "g2-3" {
        return Err(failure("HANDSHAKE_MISMATCH", "Worker, source imports or authoring capabilities do not match the selected project.", "Use matching current game, application and worker resources."));
    }
    Ok(())
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
    path: Option<String>,
) -> Result<Value, Failure> {
    // Retain open drafts until the new project has passed its handshake and
    // preferences were saved. Cancellation or refusal restores the old root.
    authoring::flush_registered(&app,&host)?;
    host.games.stop(true)?;
    let epoch = host.cancel(false)?;
    let (selection, config) = startup::resolve_project(&app, path.as_deref().map(Path::new))?;
    let operation = {
        let mut state = host.inner.lock().unwrap();
        if host.epoch.load(Ordering::SeqCst) != epoch { return Err(failure("CANCELLED", "Project selection changed.", "Open the current project.")); }
        let operation = Operation::reserve(&host, &mut state, false)?;
        let previous = ProjectConnection {root:state.root.take(),ready:state.ready,
            discovered:std::mem::take(&mut state.discovered),families:std::mem::take(&mut state.discovered_families)};
        state.pending_project = Some((operation.id, previous));
        state.root = Some(selection.root.clone());
        state.ready = false;
        operation
    };
    let host = host.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let mut response = run_worker(
            app,
            &operation,
            Request {
                op: "identify".into(),
                asset: None,
                seed: None,
                invalid_fixture: None,
                draft: None,
                source_asset: None,
                preview_inputs: None,
            },
        )?;
        if response["ok"] == true {
            let mut state = host.inner.lock().unwrap();
            operation.check(&state)?;
            if !state.ready {
                return Err(failure("CANCELLED", "Project changed before saving preferences.", "Open the current project."));
            }
            startup::save(&config, &selection.root)?;
            state.pending_project = None;
            state.document = None; state.pool_document = None;
            state.content_documents.clear();
            state.handoffs.clear();
            response["result"]["project_selection"] = serde_json::to_value(selection).unwrap();
            if let Some(store)=host.recovery.lock().unwrap().as_mut(){store.release_all();}
        }
        Ok(response)
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
    if ["validate_draft", "preview_draft"].contains(&request.op.as_str())
    {
        return Err(failure(
            "UNSUPPORTED_OPERATION",
            "Use the document authoring boundary.",
            "Open a discovered building.",
        ));
    }
    let operation = Operation::begin(&host)?;
    tauri::async_runtime::spawn_blocking(move || run_worker(app, &operation, request))
        .await
        .map_err(|e| failure("HOST_FAILED", e, "Restart Workbench."))?
}
#[tauri::command]
fn cancel_worker(host: tauri::State<'_, Host>) -> Result<(), Failure> {
    host.cancel(false).map(|_| ())
}
#[tauri::command]
fn close_project(app:tauri::AppHandle,host: tauri::State<'_, Host>) -> Result<(), Failure> {
    authoring::flush_registered(&app,&host)?;
    host.games.stop(true)?;
    host.cancel(true).map(|_| ())
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
            room_test::room_test_action,
            authoring::open_document,
            authoring::validate_document,
            authoring::invalidate_document,
            authoring::edit_document,
            authoring::checkpoint_document,
            authoring::discard_document_draft,
            authoring::list_recovery,
            authoring::inspect_recovery,
            authoring::discard_recovery,
            authoring::restore_recovery,
            authoring::reconcile_recovery,
            authoring::acknowledge_reopen,
            authoring::apply_document,
            authoring::document_disk,
            authoring::workspace_disk,
            authoring::close_document,
            authoring::finish_close
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let host = window.state::<Host>();
                let state = host.inner.lock().unwrap();
                if state.applying || state.document.is_some() || state.pool_document.is_some() || !state.content_documents.is_empty() {
                    api.prevent_close();
                    let _ = window.emit("authoring-close-requested", ());
                    return;
                }
            }
            if matches!(
                event,
                tauri::WindowEvent::CloseRequested { .. } | tauri::WindowEvent::Destroyed
            ) {
                let _=window.state::<Host>().games.stop(true);
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
                draft: None,
                source_asset: None,
                preview_inputs: None,
            })
            .is_err());
        }
        assert!(validate_request(&Request {
            op: "exec".into(),
            asset: None,
            seed: None,
            invalid_fixture: None,
            draft: None,
                source_asset: None,
                preview_inputs: None,
        })
        .is_err());
    }
    #[test]
    fn strict_envelopes() {
        assert!(parse_response(br#"{"protocol":8,"id":"x","ok":true,"result":{}}"#, "x").is_ok());
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
    fn handshake_requires_selected_imports_matching_bridge_and_capabilities() {
        let temp = tempfile::tempdir().unwrap();
        let root = dunce::canonicalize(temp.path()).unwrap();
        let bridge = root.join("bridge.py");
        std::fs::write(&bridge, "bridge fixture").unwrap();
        let valid = json!({"protocol":8,"worker_version":env!("CARGO_PKG_VERSION"),"source":{"root":root},"worker_sha256":authoring::hash(b"bridge fixture"),
            "runtime":{"compatible":true,"imports_verified":true},"contract":"g2-3",
            "layout_contract":"authored-room-2","families":[],"creature_contract":"creature-common-1"});
        assert!(verify_identity(&valid, &root, &bridge).is_ok());
        for pointer in ["/protocol", "/worker_version", "/source/root", "/worker_sha256", "/runtime/compatible", "/runtime/imports_verified", "/contract", "/families"] {
            let mut bad = valid.clone();
            *bad.pointer_mut(pointer).unwrap() = Value::Null;
            assert_eq!(verify_identity(&bad, &root, &bridge).unwrap_err().code, "HANDSHAKE_MISMATCH");
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
