//! Project preferences contain only a root, never executable paths or file entitlements.
use crate::{canonical_root, failure, Failure};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    io::Write,
    path::{Path, PathBuf},
};
use tauri::{path::BaseDirectory, Manager};

#[derive(Deserialize)]
struct Defaults {
    version: u32,
    project_root: PathBuf,
    development_python: PathBuf,
}
fn defaults() -> Defaults {
    let profile: Defaults = serde_json::from_str(include_str!("../../owner-defaults.json"))
        .expect("versioned build profile");
    assert_eq!(profile.version, 1);
    profile
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Preferences {
    version: u32,
    project_root: PathBuf,
}

#[derive(Debug, Serialize)]
pub struct Selection {
    pub root: PathBuf,
    pub selected_from: String,
    pub notices: Vec<String>,
}

pub fn config_file(app: &tauri::AppHandle) -> Result<PathBuf, Failure> {
    // Process-only diagnostic isolation; never changes the source or runtime.
    let directory = if let Some(path) = std::env::var_os("RESONANCE_WORKBENCH_CONFIG_DIR") {
        let path = PathBuf::from(path);
        if !path.is_absolute() {
            return Err(failure(
                "SETTINGS_PATH",
                "Diagnostic config directory must be absolute.",
                "Unset RESONANCE_WORKBENCH_CONFIG_DIR to use per-user app settings.",
            ));
        }
        path
    } else {
        app.path().app_config_dir().map_err(|e| {
            failure(
                "SETTINGS_PATH",
                e,
                "Check per-user application configuration access.",
            )
        })?
    };
    Ok(directory.join("project.json"))
}

pub fn select(
    config: &Path,
    explicit: Option<&Path>,
    executable: &Path,
    fallback: &Path,
) -> Result<Selection, Failure> {
    if let Some(path) = explicit {
        return Ok(Selection {
            root: canonical_root(path)?,
            selected_from: "explicit choice".into(),
            notices: vec![],
        });
    }
    let mut notices = Vec::new();
    match std::fs::read(config) {
        Ok(bytes) => {
            let saved = serde_json::from_slice::<Preferences>(&bytes);
            match saved {
                Ok(saved) if saved.version == 1 && saved.project_root.is_absolute() => {
                    match canonical_root(&saved.project_root) {
                        Ok(root) => {
                            return Ok(Selection {
                                root,
                                selected_from: "saved project".into(),
                                notices,
                            })
                        }
                        Err(error) => notices.push(format!(
                            "Saved project {} is unavailable: {}",
                            saved.project_root.display(),
                            error.message
                        )),
                    }
                }
                _ => notices.push(format!(
                    "Invalid project settings at {}; checking validated defaults.",
                    config.display()
                )),
            }
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => notices.push(format!("Cannot read {}: {e}", config.display())),
    }
    // Only this executable's ancestors, never cwd, PATH, sibling projects or the
    // interpreter's environment. A portable installation falls through to profile.
    for ancestor in executable.ancestors().skip(1) {
        if let Ok(root) = canonical_root(ancestor) {
            return Ok(Selection {
                root,
                selected_from: "application checkout".into(),
                notices,
            });
        }
    }
    if let Ok(root) = canonical_root(fallback) {
        return Ok(Selection {
            root,
            selected_from: "owner default".into(),
            notices,
        });
    }
    notices.push(format!(
        "No valid application checkout; owner default {} is missing or invalid.",
        fallback.display()
    ));
    Err(failure("PROJECT_UNAVAILABLE", notices.join("\n"), "Use Change Project once to select the complete Resonance checkout. No game files were changed."))
}

pub fn resolve_project(
    app: &tauri::AppHandle,
    explicit: Option<&Path>,
) -> Result<(Selection, PathBuf), Failure> {
    let config = config_file(app)?;
    let executable = std::env::current_exe().map_err(|e| {
        failure(
            "STARTUP_PATH",
            e,
            "Launch Workbench from its supported shortcut.",
        )
    })?;
    Ok((
        select(&config, explicit, &executable, &defaults().project_root)?,
        config,
    ))
}

pub fn save(config: &Path, root: &Path) -> Result<(), Failure> {
    let io_error = |e: std::io::Error| {
        failure(
            "SETTINGS_WRITE",
            e,
            "Check per-user application configuration access, then reopen the project.",
        )
    };
    let parent = config.parent().expect("settings directory");
    std::fs::create_dir_all(parent).map_err(io_error)?;
    let bytes = serde_json::to_vec_pretty(&Preferences {
        version: 1,
        project_root: root.to_path_buf(),
    })
    .expect("serializable settings");
    let mut file = tempfile::NamedTempFile::new_in(parent).map_err(io_error)?;
    file.write_all(&bytes).map_err(io_error)?;
    file.as_file().sync_all().map_err(io_error)?;
    file.persist(config).map_err(|e| io_error(e.error))?;
    Ok(())
}

#[derive(Debug, Serialize)]
pub struct Runtime {
    pub mode: String,
    pub python: PathBuf,
    pub bridge: PathBuf,
    pub resource_directory: PathBuf,
    pub application: PathBuf,
    pub override_present: bool,
    pub notice: Option<String>,
}

pub fn resolve_runtime(
    executable: &Path,
    resource: &Path,
    development: bool,
    diagnostic: bool,
    override_path: Option<PathBuf>,
    development_python: &Path,
) -> Result<Runtime, Failure> {
    if executable
        .parent()
        .and_then(Path::file_name)
        .is_some_and(|name| name == "deps")
    {
        return Err(failure("UNSUPPORTED_LAUNCH", format!("Cargo dependency executable {} has no application resource bundle.", executable.display()), "Open workbench/Launch Workbench.vbs or the installed Resonance Workbench shortcut. Do not launch target/release/deps executables."));
    }
    let override_present = override_path.is_some();
    let use_override = diagnostic || development;
    let (mode, python, bridge) = if development {
        let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../worker");
        let python = override_path.clone().unwrap_or_else(|| {
            if development_python.is_file() {
                development_python.to_path_buf()
            } else {
                worker.join("runtime/python.exe")
            }
        });
        ("development", python, worker.join("bridge.py"))
    } else if diagnostic && override_present {
        (
            "diagnostic external",
            override_path.clone().unwrap(),
            resource.join("bridge.py"),
        )
    } else {
        (
            "bundled",
            resource.join("python/python.exe"),
            resource.join("bridge.py"),
        )
    };
    let remedy = if use_override && override_present {
        "The explicit RESONANCE_PYTHON diagnostic candidate is unavailable. Remove that override or launch normally to use the bundled worker. Project selection is unchanged."
    } else if development {
        "Restore the pinned development interpreter in owner-defaults.json or prepare worker/runtime. The current project is independent of that environment."
    } else {
        "The application resource bundle is incomplete. Use the supported Workbench launcher or rebuild with npm run bundle. No external Python is needed for ordinary launch."
    };
    if !python.is_absolute() || !python.is_file() || !bridge.is_file() {
        return Err(failure(
            "WORKER_MISSING",
            format!(
                "Mode: {mode}; Python: {}; bridge: {}; resources: {}",
                python.display(),
                bridge.display(),
                resource.display()
            ),
            remedy,
        ));
    }
    let bytes = std::fs::read(&bridge).map_err(|e| failure("WORKER_MISSING", e, remedy))?;
    if Sha256::digest(bytes) != Sha256::digest(include_bytes!("../../worker/bridge.py")) {
        return Err(failure(
            "BRIDGE_MISMATCH",
            format!(
                "Bridge {} does not match this application build.",
                bridge.display()
            ),
            "Rebuild the application and all resources together.",
        ));
    }
    Ok(Runtime {mode: mode.into(), python, bridge, resource_directory: resource.into(), application: executable.into(), override_present,
        notice: (override_present && !use_override).then(|| "RESONANCE_PYTHON is ignored during ordinary bundled launch. Deliberate external-runtime diagnostics require --diagnostic-runtime.".into())})
}

pub fn runtime(app: &tauri::AppHandle) -> Result<Runtime, Failure> {
    // Uses Tauri's bundle resource mapping for installed and portable Windows apps.
    let resource = app
        .path()
        .resolve("", BaseDirectory::Resource)
        .map_err(|e| {
            failure(
                "WORKER_MISSING",
                e,
                "Restore the complete application bundle.",
            )
        })?;
    let executable = std::env::current_exe()
        .map_err(|e| failure("STARTUP_PATH", e, "Use the supported Workbench launcher."))?;
    resolve_runtime(
        &executable,
        &resource,
        cfg!(debug_assertions),
        std::env::args().any(|arg| arg == "--diagnostic-runtime"),
        std::env::var_os("RESONANCE_PYTHON").map(PathBuf::from),
        &defaults().development_python,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    fn project(path: &Path) {
        for marker in crate::PROJECT_MARKERS {
            let file = path.join(marker);
            std::fs::create_dir_all(file.parent().unwrap()).unwrap();
            std::fs::write(file, "fixture").unwrap();
        }
        for directory in crate::PROJECT_DIRECTORIES {
            std::fs::create_dir_all(path.join(directory)).unwrap();
        }
    }
    #[test]
    fn saved_choice_precedes_checkout_and_default_and_survives_restart() {
        let temp = tempfile::tempdir().unwrap();
        let first = temp.path().join("project one");
        let second = temp.path().join("project two");
        project(&first);
        project(&second);
        let config = temp.path().join("config/project.json");
        let exe = first.join("workbench/app.exe");
        assert_eq!(select(&config, None, &exe, &second).unwrap().root, first);
        save(&config, &second).unwrap();
        assert_eq!(select(&config, None, &exe, &first).unwrap().root, second);
        save(&config, &first).unwrap();
        assert_eq!(select(&config, None, &exe, &second).unwrap().root, first);
        assert_eq!(
            select(&config, Some(&second), &exe, &first).unwrap().root,
            second
        );
    }
    #[test]
    fn missing_corrupt_stale_and_wrong_version_settings_validate_fallback() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("valid project");
        project(&root);
        let config = temp.path().join("project.json");
        let exe = temp.path().join("portable/app.exe");
        assert_eq!(
            select(&config, None, &exe, &root).unwrap().selected_from,
            "owner default"
        );
        for bytes in [
            "bad JSON",
            r#"{"version":99,"project_root":"missing"}"#,
            r#"{"version":1,"project_root":"G:\\missing-w4b"}"#,
        ] {
            std::fs::write(&config, bytes).unwrap();
            let result = select(&config, None, &exe, &root).unwrap();
            assert_eq!(result.root, root);
            assert!(!result.notices.is_empty());
        }
        assert_eq!(
            select(&config, None, &exe, temp.path()).unwrap_err().code,
            "PROJECT_UNAVAILABLE"
        );
        assert!(select(&config, Some(temp.path()), &exe, &root).is_err());
        assert!(canonical_root(&root.join("roguelike/data")).is_err());
    }
    #[test]
    fn bundled_raw_external_missing_and_bridge_identity() {
        let temp = tempfile::tempdir().unwrap();
        let resource = temp.path().join("path with spaces");
        std::fs::create_dir_all(resource.join("python")).unwrap();
        std::fs::write(resource.join("python/python.exe"), "fixture").unwrap();
        std::fs::write(
            resource.join("bridge.py"),
            include_bytes!("../../worker/bridge.py"),
        )
        .unwrap();
        let exe = resource.join("app.exe");
        let missing = resource.join("missing.exe");
        let result = resolve_runtime(
            &exe,
            &resource,
            false,
            false,
            Some(missing.clone()),
            &missing,
        )
        .unwrap();
        assert_eq!(result.mode, "bundled");
        assert!(result.notice.is_some());
        assert_eq!(
            resolve_runtime(
                &exe,
                &resource,
                false,
                true,
                Some(missing.clone()),
                &missing
            )
            .unwrap_err()
            .code,
            "WORKER_MISSING"
        );
        assert_eq!(
            resolve_runtime(
                &resource.join("deps/raw.exe"),
                &resource,
                false,
                false,
                None,
                &missing
            )
            .unwrap_err()
            .code,
            "UNSUPPORTED_LAUNCH"
        );
        #[cfg(windows)]
        {
            let extended = std::fs::canonicalize(&resource).unwrap();
            assert!(resolve_runtime(
                &extended.join("app.exe"),
                &extended,
                false,
                false,
                None,
                &missing
            )
            .is_ok());
        }
        std::fs::write(resource.join("bridge.py"), "stale").unwrap();
        assert_eq!(
            resolve_runtime(&exe, &resource, false, false, None, &missing)
                .unwrap_err()
                .code,
            "BRIDGE_MISMATCH"
        );
    }
}
