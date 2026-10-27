//! A building and a contextual pool may stay open; each publication is one file.
//! Renderer paths and validation verdicts never authorize publication.
use super::*;
use sha2::{Digest, Sha256};
use std::fs::{self, File, OpenOptions};

pub const MAX_DRAFT: usize = 1024 * 1024;
const CATEGORIES: &[&str] = &[
    "civic",
    "commercial",
    "religious",
    "residential",
    "ruins",
    "storage",
    "wilderness",
];
#[derive(Clone)]
pub struct Document {
    token: String,
    relative: String,
    original: Vec<u8>,
    id: Option<String>,
    review: Option<Review>,
    writable: bool,
    evidence_inputs: Option<String>,
}
#[derive(Clone)]
struct Review {
    token: String,
    draft: String,
    destination: String,
    variant: bool,
    seed: u32,
    inputs: Option<String>,
}
fn hash(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
fn io_error(e: impl ToString) -> Failure {
    failure("FILE_TRANSACTION_FAILED", e, "The draft is retained. Check file permissions/locks and retry; reload after an external edit.")
}
fn conflict() -> Failure {
    failure("EXTERNAL_MODIFICATION_CONFLICT", "The disk bytes differ from the opened source.", "Inspect the disk version. Keep your unsaved draft for manual reconciliation, or discard and reload; no forced save is available.")
}
fn valid_id(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 100
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
        && ![
            "con", "prn", "aux", "nul", "com1", "com2", "com3", "com4", "com5", "com6", "com7",
            "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
        ]
        .contains(&s.to_ascii_lowercase().as_str())
}
pub fn valid_filename(s: &str) -> bool {
    s.strip_suffix(".json").is_some_and(valid_id)
}
pub fn relative_building(s: &str) -> Result<PathBuf, Failure> {
    let p: Vec<_> = s.split('/').collect();
    if p.len() != 5
        || p[..3] != ["roguelike", "data", "buildings"]
        || !CATEGORIES.contains(&p[3])
        || !valid_filename(p[4])
    {
        return Err(failure("PATH_ESCAPE", "Only buildings/<existing-category>/<safe-id>.json is writable.", "Select a discovered ordinary building. Variants stay in its existing category directory."));
    }
    Ok(PathBuf::from(s))
}
pub fn is_pool(s: &str) -> bool {
    let p: Vec<_> = s.split('/').collect();
    p.len() == 4 && p[..3] == ["roguelike", "data", "loot_pools"] && valid_filename(p[3])
}
pub fn is_item(s: &str) -> bool {
    let p: Vec<_> = s.split('/').collect();
    p.len() >= 4 && p[..3] == ["roguelike", "data", "items"]
        && p[3..p.len()-1].iter().all(|s| valid_id(s)) && valid_filename(p[p.len()-1])
}
pub fn is_recipe(s: &str) -> bool {
    let p: Vec<_> = s.split('/').collect();
    p.len() >= 4 && p[..3] == ["roguelike", "data", "recipes"]
        && p[3..p.len()-1].iter().all(|s| valid_id(s)) && valid_filename(p[p.len()-1])
}
pub fn is_creature(s: &str) -> bool {
    let p: Vec<_> = s.split('/').collect();
    p.len() >= 4 && p[..3] == ["roguelike", "data", "entities"]
        && p[3..p.len()-1].iter().all(|s| valid_id(s)) && valid_filename(p[p.len()-1])
}
fn dependency_bound(s: &str) -> bool { is_recipe(s) || is_creature(s) }
fn relative_content(s: &str) -> Result<PathBuf, Failure> {
    if is_pool(s) || is_item(s) || is_recipe(s) || is_creature(s) { Ok(PathBuf::from(s)) } else { relative_building(s) }
}
fn no_link(path: &Path) -> Result<(), Failure> {
    let meta = fs::symlink_metadata(path).map_err(io_error)?;
    #[cfg(windows)]
    let linked = {
        use std::os::windows::fs::MetadataExt;
        meta.file_attributes() & 0x400 != 0
    };
    #[cfg(not(windows))]
    let linked = meta.file_type().is_symlink();
    if linked {
        return Err(failure(
            "PATH_ESCAPE",
            format!("Linked/reparse path rejected: {}", path.display()),
            "Use regular directories and files inside the selected checkout.",
        ));
    }
    Ok(())
}
fn checked_target(root: &Path, relative: &str, new: bool) -> Result<PathBuf, Failure> {
    let rel = relative_content(relative)?;
    let mut path = root.to_path_buf();
    no_link(&path)?;
    for part in rel.components() {
        path.push(part);
        if new && path == root.join(&rel) && !path.try_exists().map_err(io_error)? {
            break;
        }
        no_link(&path)?;
        if !dunce::canonicalize(&path)
            .map_err(io_error)?
            .starts_with(root)
        {
            return Err(failure(
                "PATH_ESCAPE",
                "Resolved path escaped the selected root.",
                "Reload a regular content file.",
            ));
        }
    }
    if !path.parent().unwrap().is_dir() {
        return Err(io_error("Destination parent is unavailable."));
    }
    if new && path.exists() {
        return Err(failure(
            "VARIANT_EXISTS",
            "The variant destination already exists.",
            "Choose a unique new ID; existing files are never overwritten by Save as variant.",
        ));
    }
    if new {
        let name = path.file_name().unwrap().to_string_lossy().to_lowercase();
        if fs::read_dir(path.parent().unwrap()).map_err(io_error)?.filter_map(Result::ok)
            .any(|e| e.file_name().to_string_lossy().to_lowercase() == name) {
            return Err(failure("VARIANT_EXISTS", "Case-insensitive destination collision.", "Choose a unique new filename."));
        }
    }
    if !new && !path.is_file() {
        return Err(io_error("Source is unavailable."));
    }
    Ok(path)
}
fn read_source(path: &Path) -> Result<Vec<u8>, Failure> {
    if path.metadata().map_err(io_error)?.len() > MAX_DRAFT as u64 {
        return Err(io_error("Definition exceeds the 1 MiB authoring limit."));
    }
    let bytes = fs::read(path).map_err(io_error)?;
    std::str::from_utf8(&bytes).map_err(io_error)?;
    Ok(bytes)
}
fn session_doc(host: &Host, token: &str) -> Result<(PathBuf, Document), Failure> {
    let state = host.inner.lock().unwrap();
    let doc = state
        .document
        .as_ref()
        .into_iter()
        .chain(state.pool_document.as_ref())
        .chain(state.item_document.as_ref()).chain(state.recipe_document.as_ref()).chain(state.creature_document.as_ref())
        .find(|d| d.token == token)
        .ok_or_else(|| {
            failure(
                "UNKNOWN_DOCUMENT",
                "Document identity is stale or forged.",
                "Open the definition again from discovery.",
            )
        })?;
    Ok((
        state
            .root
            .clone()
            .ok_or_else(|| io_error("No project open."))?,
        doc.clone(),
    ))
}
fn revoke_review(host: &Host, token: &str) {
    let mut state = host.inner.lock().unwrap();
    if let Some(doc) = current_document(&mut state, token) {
        doc.review = None;
    }
}
fn current_document<'a>(state: &'a mut Session, token: &str) -> Option<&'a mut Document> {
    state.document.as_mut().into_iter().chain(state.pool_document.as_mut()).chain(state.item_document.as_mut()).chain(state.recipe_document.as_mut()).chain(state.creature_document.as_mut()).find(|d| d.token == token)
}
fn envelope(result: Value) -> Value {
    json!({"protocol":PROTOCOL,"id":uuid::Uuid::new_v4().to_string(),"ok":true,"result":result,"host_elapsed_ms":0})
}

#[tauri::command]
pub async fn open_document(
    app: tauri::AppHandle,
    host: tauri::State<'_, Host>,
    asset: String,
) -> Result<Value, Failure> {
    let epoch = host.epoch.load(Ordering::SeqCst);
    let host = host.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let root = {
            let state = host.inner.lock().unwrap();
            if state.busy || state.applying {
                return Err(io_error("A request is active."));
            }
            if !state.discovered.contains(&asset) {
                return Err(failure(
                    "UNKNOWN_SOURCE",
                    "Source was not returned by trusted discovery.",
                    "Refresh the asset index and select a supported building.",
                ));
            }
            state
                .root
                .clone()
                .ok_or_else(|| io_error("No project open."))?
        };
        let path = checked_target(&root, &asset, false)?;
        let original = read_source(&path)?;
        let evidence_inputs = if dependency_bound(&asset) { Some(input_stamp(&root)?) } else { None };
        let mut response = run_worker(
            app,
            host.clone(),
            Request {
                op: "inspect".into(),
                asset: Some(asset.clone()),
                ..Default::default()
            },
            epoch,
        )?;
        if response["ok"] != true {
            return Ok(response);
        }
        if read_source(&path)? != original || response["result"]["sha256"] != hash(&original) {
            return Err(conflict());
        }
        if let Some(stamp) = &evidence_inputs {
            if input_stamp(&root)? != *stamp { return Err(failure("SOURCE_CHANGED", "Content dependencies changed during opening.", "Reopen the recipe.")); }
        }
        let token = uuid::Uuid::new_v4().to_string();
        let id = serde_json::from_str::<Value>(
            std::str::from_utf8(&original)
                .map_err(io_error)?
                .trim_start_matches('\u{feff}'),
        )
        .ok()
        .and_then(|v| v["id"].as_str().map(str::to_owned));
        let mut state = host.inner.lock().unwrap();
        if host.epoch.load(Ordering::SeqCst) != epoch {
            return Err(io_error("Project changed."));
        }
        let writable = if is_creature(&asset) { asset.starts_with("roguelike/data/entities/creatures/") && response["result"]["editable"] == true } else if is_recipe(&asset) { response["result"]["editable"] == true } else { !is_item(&asset) || (asset.starts_with("roguelike/data/items/components/") && response["result"]["editable"] == true) };
        let slot = if is_pool(&asset) { &mut state.pool_document } else if is_item(&asset) { &mut state.item_document } else if is_recipe(&asset) { &mut state.recipe_document } else if is_creature(&asset) { &mut state.creature_document } else { &mut state.document };
        *slot = Some(Document {
            token: token.clone(),
            relative: asset,
            original,
            id,
            review: None,
            writable,
            evidence_inputs,
        });
        response["result"]["document_token"] = json!(token);
        Ok(response)
    })
    .await
    .map_err(io_error)?
}

fn destination(
    doc: &Document,
    draft: &str,
    variant_id: Option<&str>,
) -> Result<(String, bool), Failure> {
    if !doc.writable {
        return Err(failure(if is_creature(&doc.relative) { "READ_ONLY_CREATURE" } else if is_recipe(&doc.relative) { "READ_ONLY_RECIPE" } else { "READ_ONLY_ITEM" }, "This source is outside its supported authoring capability.", "Inspect unsupported or ambiguous sources read-only."));
    }
    if draft.len() > MAX_DRAFT {
        return Err(io_error("Draft exceeds 1 MiB."));
    }
    // Syntax/schema verdict comes from Python; this is only the publication identity rule.
    let raw: Value =
        serde_json::from_str(draft.trim_start_matches('\u{feff}')).unwrap_or(Value::Null);
    if let Some(id) = variant_id {
        if !valid_id(id) || raw["id"].as_str() != Some(id) || doc.id.as_deref() == Some(id) {
            return Err(failure(
                "VARIANT_ID",
                "A new variant requires a different safe ID matching the draft's id field.",
                "Use letters, digits, underscores or hyphens and update the draft ID.",
            ));
        }
        Ok((
            format!("{}/{}.json", doc.relative.rsplit_once('/').unwrap().0, id),
            true,
        ))
    } else {
        if let Some(id) = &doc.id {
            if raw.is_object() && raw["id"].as_str() != Some(id) {
                return Err(failure(
                    "IDENTITY_CHANGE",
                    "Changing an existing definition's ID requires Save as variant.",
                    "Keep the existing ID or create a unique variant.",
                ));
            }
        }
        Ok((doc.relative.clone(), false))
    }
}

#[tauri::command]
pub async fn validate_document(
    app: tauri::AppHandle,
    host: tauri::State<'_, Host>,
    token: String,
    draft: String,
    variant_id: Option<String>,
    seed: Option<u32>,
) -> Result<Value, Failure> {
    if host.inner.lock().unwrap().applying {
        return Err(failure(
            "BUSY",
            "A file transaction is in progress.",
            "Wait for its result before validating another draft.",
        ));
    }
    let (root, doc) = session_doc(&host, &token)?;
    // A failed/cancelled replacement validation must not leave an older review
    // capability usable, even when failure happens before a worker response.
    revoke_review(&host, &token);
    let seed = seed.unwrap_or(20261023);
    let source_path = checked_target(&root, &doc.relative, false)?;
    if read_source(&source_path)? != doc.original {
        return Err(conflict());
    }
    let (dest, variant) = destination(&doc, &draft, variant_id.as_deref())?;
    checked_target(&root, &dest, variant)?;
    let inputs = if dependency_bound(&doc.relative) { Some(input_stamp(&root)?) } else { None };
    let epoch = host.epoch.load(Ordering::SeqCst);
    let host = host.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let mut response = run_worker(
            app,
            host.clone(),
            Request {
                op: "preview_draft".into(),
                asset: Some(dest.clone()),
                draft: Some(draft.clone()),
                source_asset: is_creature(&doc.relative).then(|| doc.relative.clone()),
                seed: Some(seed),
                ..Default::default()
            },
            epoch,
        )?;
        if read_source(&source_path)? != doc.original {
            return Err(conflict());
        }
        if let Some(stamp) = &inputs {
            if input_stamp(&root)? != *stamp { return Err(failure("SOURCE_CHANGED", "Content dependencies changed during validation.", "Validate again.")); }
        }
        let mut state = host.inner.lock().unwrap();
        let current = current_document(&mut state, &token)
            .ok_or_else(|| io_error("Document changed."))?;
        current.review = None;
        current.evidence_inputs = inputs.clone();
        if response["ok"] == true
            && response["result"]["valid"] == true
            && response["result"]["draft_sha256"] == hash(draft.as_bytes())
            && (!(is_recipe(&doc.relative) || is_creature(&doc.relative)) || variant)
            && (!is_creature(&doc.relative) || (response["result"]["creature_contract"] == "revenant-hp-1" && response["result"]["factory_verified"] == true && response["result"]["route"] == "creature_definition"))
        {
            let review_token = uuid::Uuid::new_v4().to_string();
            current.review = Some(Review {
                token: review_token.clone(),
                draft,
                destination: dest,
                variant,
                seed,
                inputs,
            });
            response["result"]["review_token"] = json!(review_token);
        }
        Ok(response)
    })
    .await
    .map_err(io_error)?
}

/// Windows handles pin each source/data directory and deny dependency writes or
/// renames while Python validates and the host publishes. The source's separate
/// read lock is released for ReplaceFileW; its displaced bytes are checked again
/// via the backup, restoring an intervening external version on a conflict.
fn pin_inputs(root: &Path, target: &Path) -> Result<Vec<File>, Failure> {
    fn pin(path: &Path, directory: bool) -> Result<File, Failure> {
        no_link(path)?;
        let mut options = OpenOptions::new();
        options.read(true);
        #[cfg(windows)]
        {
            use std::os::windows::fs::OpenOptionsExt;
            options.share_mode(if directory { 1 | 2 } else { 1 });
            if directory {
                options.custom_flags(0x02000000);
            }
        }
        #[cfg(not(windows))]
        {
            let _ = directory;
        }
        let handle = options.open(path).map_err(io_error)?;
        no_link(path)?;
        Ok(handle)
    }
    fn walk(
        path: &Path,
        target: &Path,
        handles: &mut Vec<File>,
        data: bool,
    ) -> Result<(), Failure> {
        handles.push(pin(path, true)?);
        for entry in fs::read_dir(path).map_err(io_error)? {
            let p = entry.map_err(io_error)?.path();
            if ["saves", "__pycache__", "assets", "docs"]
                .iter()
                .any(|n| p.file_name().is_some_and(|v| v == *n))
            {
                continue;
            }
            no_link(&p)?;
            if p.is_dir() {
                walk(
                    &p,
                    target,
                    handles,
                    data || p.file_name().is_some_and(|s| s == "data"),
                )?;
            } else if dunce::canonicalize(&p).map_err(io_error)?
                != dunce::canonicalize(target).map_err(io_error)?
                && p.extension()
                    .is_some_and(|e| e == "py" || (data && e == "json"))
            {
                handles.push(pin(&p, false)?);
            }
        }
        Ok(())
    }
    let mut handles = vec![pin(root, true)?];
    walk(&root.join("roguelike"), target, &mut handles, false)?;
    Ok(handles)
}

fn pin_source(path: &Path) -> Result<File, Failure> {
    let mut options = OpenOptions::new();
    options.read(true);
    #[cfg(windows)]
    {
        use std::os::windows::fs::OpenOptionsExt;
        options.share_mode(1);
    }
    options.open(path).map_err(io_error)
}

fn input_stamp(root: &Path) -> Result<String, Failure> {
    fn walk(path: &Path, digest: &mut Sha256, data: bool) -> Result<(), Failure> {
        let mut entries = fs::read_dir(path)
            .map_err(io_error)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(io_error)?;
        entries.sort_by_key(|e| e.file_name());
        for entry in entries {
            let p = entry.path();
            if ["saves", "__pycache__", "assets", "docs"]
                .iter()
                .any(|n| p.file_name().is_some_and(|v| v == *n))
            {
                continue;
            }
            no_link(&p)?;
            if p.is_dir() {
                walk(
                    &p,
                    digest,
                    data || p.file_name().is_some_and(|v| v == "data"),
                )?;
            } else if p
                .extension()
                .is_some_and(|e| e == "py" || (data && e == "json"))
            {
                digest.update(p.to_string_lossy().as_bytes());
                digest.update(fs::read(p).map_err(io_error)?);
            }
        }
        Ok(())
    }
    let mut digest = Sha256::new();
    walk(&root.join("roguelike"), &mut digest, false)?;
    Ok(format!("{:x}", digest.finalize()))
}

#[cfg(windows)]
fn replace(target: &Path, stage: &Path, backup: &Path) -> std::io::Result<()> {
    use std::os::windows::ffi::OsStrExt;
    let wide = |p: &Path| {
        p.as_os_str()
            .encode_wide()
            .chain(Some(0))
            .collect::<Vec<_>>()
    };
    let (t, s, b) = (wide(target), wide(stage), wide(backup));
    // Preserve Windows ACLs, creation time and other supported target metadata.
    let ok = unsafe {
        windows_sys::Win32::Storage::FileSystem::ReplaceFileW(
            t.as_ptr(),
            s.as_ptr(),
            b.as_ptr(),
            0,
            std::ptr::null(),
            std::ptr::null(),
        )
    };
    if ok == 0 {
        Err(std::io::Error::last_os_error())
    } else {
        Ok(())
    }
}
#[cfg(not(windows))]
fn replace(_target: &Path, _stage: &Path, _backup: &Path) -> std::io::Result<()> {
    Err(std::io::Error::other(
        "Publication is verified and enabled only on Windows.",
    ))
}

fn rollback(target: &Path, backup: &Path, expected_new: &[u8]) -> Result<(), Failure> {
    if target.exists() {
        let failed = target.with_file_name(format!(".w1-failed-{}.tmp", uuid::Uuid::new_v4()));
        replace(target, backup, &failed).map_err(|e| failure("RECOVERY_REQUIRED", format!("{e}; previous source retained at {}", backup.display()), "Do not delete recovery files. Resolve the filesystem lock and restore the named backup manually."))?;
        if fs::read(&failed).map_err(io_error)? != expected_new {
            return Err(failure("RECOVERY_REQUIRED", format!("Prior source restored; a concurrent version is preserved at {}",failed.display()), "Keep the named recovery file and reconcile both versions. Nothing was silently discarded."));
        }
        fs::remove_file(failed).map_err(io_error)?;
    } else {
        fs::rename(backup, target).map_err(io_error)?;
    }
    Ok(())
}

#[derive(Clone, Copy, Default, PartialEq)]
enum Fault {
    #[default]
    None,
    BeforeStage,
    AfterStage,
    BeforeReplace,
    AfterReplace,
    ConcurrentReplace,
}

fn publish(root: &Path, doc: &Document, review: &Review, fault: Fault) -> Result<Value, Failure> {
    if is_creature(&doc.relative) && !review.variant {
        return Err(failure("CREATURE_VARIANT_REQUIRED", "Creature publication requires a new ID and file.", "Review a unique creature variant."));
    }
    if is_recipe(&doc.relative) && !review.variant {
        return Err(failure("RECIPE_VARIANT_REQUIRED", "Recipe publication requires a new ID and file.", "Create and review a unique recipe variant."));
    }
    let original_path = checked_target(root, &doc.relative, false)?;
    if read_source(&original_path)? != doc.original {
        return Err(conflict());
    }
    let target = checked_target(root, &review.destination, review.variant)?;
    if fault == Fault::BeforeStage {
        return Err(io_error("Injected stage creation failure."));
    }
    let mut stage = tempfile::Builder::new()
        .prefix(".w1-stage-")
        .suffix(".tmp")
        .tempfile_in(target.parent().unwrap())
        .map_err(io_error)?;
    stage.write_all(review.draft.as_bytes()).map_err(io_error)?;
    stage.as_file().sync_all().map_err(io_error)?;
    // ReplaceFileW requires the replacement writer handle to be closed.
    let stage = stage.into_temp_path();
    if fault == Fault::AfterStage {
        return Err(io_error("Injected staged write failure."));
    }
    // Recheck target and parents immediately before publication.
    checked_target(root, &review.destination, review.variant)?;
    if read_source(&original_path)? != doc.original {
        return Err(conflict());
    }
    if fault == Fault::BeforeReplace {
        return Err(io_error("Injected rename failure."));
    }
    if fault == Fault::ConcurrentReplace {
        fs::write(&target, b"external edit between comparison and replacement")
            .map_err(io_error)?;
    }
    let before_hash = (!review.variant).then(|| hash(&doc.original));
    if review.variant {
        // persist_noclobber refuses a destination created after validation.
        stage
            .persist_noclobber(&target)
            .map_err(|e| io_error(e.error))?;
        if read_source(&target)? != review.draft.as_bytes() {
            return Err(failure("EXTERNAL_MODIFICATION_CONFLICT", "The new variant changed immediately after publication; its disk version was retained.", "Reload and reconcile the draft with the current variant."));
        }
    } else {
        let backup = target.with_file_name(format!(
            ".w1-backup-{}-{}.bak",
            target.file_stem().unwrap().to_string_lossy(),
            uuid::Uuid::new_v4()
        ));
        if let Err(error) = replace(&target, &stage, &backup) {
            // ReplaceFileW documents some partial-failure states. Restore from
            // its actual backup if present, never from an assumed cached value.
            if backup.exists() {
                rollback(&target, &backup, review.draft.as_bytes())?;
            }
            return Err(io_error(error));
        }
        let displaced = fs::read(&backup).map_err(|e| {
            failure(
                "RECOVERY_REQUIRED",
                format!("{e}; previous source is at {}", backup.display()),
                "Inspect the target and named backup; automatic cleanup could not verify them.",
            )
        })?;
        if displaced != doc.original || fault == Fault::AfterReplace {
            rollback(&target, &backup, review.draft.as_bytes())?;
            return Err(if displaced != doc.original {
                conflict()
            } else {
                io_error("Injected post-replacement failure; original restored.")
            });
        }
        if fs::read(&target).map_err(io_error)? != review.draft.as_bytes() {
            return Err(failure("RECOVERY_REQUIRED", format!("Published bytes changed externally; disk version preserved and original retained at {}",backup.display()), "Keep both versions and reconcile before another apply."));
        }
        fs::remove_file(&backup).map_err(|e| {
            failure(
                "RECOVERY_REQUIRED",
                format!(
                    "File applied, but backup cleanup failed: {e}; {}",
                    backup.display()
                ),
                "Reload the target; retain the named backup until its contents have been checked.",
            )
        })?;
    }
    Ok(
        json!({"outcome":"applied", "path":review.destination,"before_sha256":before_hash,"after_sha256":hash(review.draft.as_bytes()),"variant":review.variant,"selection_profiles_changed":false}),
    )
}

#[tauri::command]
pub async fn apply_document(
    app: tauri::AppHandle,
    host: tauri::State<'_, Host>,
    token: String,
    review_token: String,
    confirmed: bool,
) -> Result<Value, Failure> {
    let (root, doc) = session_doc(&host, &token)?;
    let review = doc
        .review
        .clone()
        .filter(|r| r.token == review_token)
        .ok_or_else(|| {
            failure(
                "REVIEW_REQUIRED",
                "A current valid review is required.",
                "Validate this draft and review the source diff.",
            )
        })?;
    if !confirmed {
        return Err(failure(
            "CONFIRMATION_REQUIRED",
            "Apply must be deliberate.",
            "Read the diff and confirm this single-file change.",
        ));
    }
    {
        let mut state = host.inner.lock().unwrap();
        if state.busy || state.applying {
            return Err(io_error("A request is active."));
        }
        state.applying = true;
    }
    let epoch = host.epoch.load(Ordering::SeqCst);
    let host = host.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let result = (|| {
            let target = checked_target(&root, &doc.relative, false)?;
            let _pins = pin_inputs(&root, &target)?;
            let source_lock = pin_source(&target)?;
            let stamp = input_stamp(&root)?;
            if read_source(&target)? != doc.original { return Err(conflict()); }
            if review.inputs.as_ref().is_some_and(|s| *s != stamp) {
                return Err(failure("SOURCE_CHANGED", "Content dependencies changed since review.", "Validate the retained draft and review again."));
            }
            let response = run_worker(app, host.clone(), Request {op:"preview_draft".into(),asset:Some(review.destination.clone()),draft:Some(review.draft.clone()),source_asset:is_creature(&doc.relative).then(||doc.relative.clone()),seed:Some(review.seed),..Default::default()}, epoch)?;
            if response["ok"] != true || response["result"]["valid"] != true || response["result"]["draft_sha256"] != hash(review.draft.as_bytes())
                || response["result"]["route"] != if is_pool(&doc.relative) { "contextual_loot_pool" } else if is_item(&doc.relative) { "item_definition" } else if is_recipe(&doc.relative) { "recipe_definition" } else if is_creature(&doc.relative) { "creature_definition" } else { "ordinary_building" }
                || response["result"]["contract"] != "g2-2" || response["result"]["worker_version"] != "0.7.0"
                || (is_item(&doc.relative) && (response["result"]["factory_verified"] != true || response["result"]["item_contract"] != "component-1"))
                || (is_recipe(&doc.relative) && (!review.variant || response["result"]["recipe_contract"] != "immediate-components-1"))
                || (is_creature(&doc.relative) && (!review.variant || response["result"]["creature_contract"] != "revenant-hp-1" || response["result"]["factory_verified"] != true))
                || (!is_creature(&doc.relative) && !is_pool(&doc.relative) && !is_item(&doc.relative) && !is_recipe(&doc.relative) && response["result"]["preview"]["passed"] != true) {
                let details = if response["ok"] == true {
                    response["result"]["diagnostics"].as_array().into_iter().flatten().take(3)
                        .map(|d| format!("{} {}: {}",d["code"],d["field"],d["message"])).collect::<Vec<_>>().join("; ")
                } else { response["error"]["message"].as_str().unwrap_or("Worker compatibility failed.").to_owned() };
                return Err(failure("VALIDATION_FAILED", format!("Fresh publication validation failed. {details}"), "Current game validation rejected the exact publication bytes. Review Problems and validate again."));
            }
            if input_stamp(&root)? != stamp { return Err(failure("SOURCE_CHANGED", "Validation inputs changed during publication.", "Validate the current draft again.")); }
            drop(source_lock);
            publish(&root, &doc, &review, Fault::None)
        })();
        let mut state = host.inner.lock().unwrap();
        state.applying = false;
        if let Some(current) = &mut state.document { current.review = None; }
        if let Some(current) = &mut state.pool_document { current.review = None; }
        if let Some(current) = &mut state.item_document { current.review = None; }
        if let Some(current) = &mut state.recipe_document { current.review = None; }
        if let Some(current) = &mut state.creature_document { current.review = None; }
        result.map(envelope)
    }).await.map_err(io_error)?
}

#[tauri::command]
pub fn document_disk(host: tauri::State<'_, Host>, token: String) -> Result<Value, Failure> {
    let (root, doc) = session_doc(&host, &token)?;
    let path = checked_target(&root, &doc.relative, false)?;
    let bytes = read_source(&path)?;
    let dependencies_changed = if let Some(stamp) = &doc.evidence_inputs { input_stamp(&root)? != *stamp } else { false };
    let pending: Vec<_> = fs::read_dir(path.parent().unwrap())
        .map_err(io_error)?
        .filter_map(Result::ok)
        .filter(|e| e.file_name().to_string_lossy().starts_with(".w1-"))
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .collect();
    Ok(envelope(
        json!({"changed":bytes != doc.original,"dependencies_changed":dependencies_changed,"raw":String::from_utf8(bytes.clone()).map_err(io_error)?,"sha256":hash(&bytes),"recovery_files":pending}),
    ))
}
#[tauri::command]
pub fn finish_close(window: tauri::Window, host: tauri::State<'_, Host>) -> Result<(), Failure> {
    host.cancel(true)?;
    window.destroy().map_err(io_error)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> (tempfile::TempDir, Document, Review) {
        let root = tempfile::tempdir().unwrap();
        let relative = "roguelike/data/buildings/commercial/sample.json";
        let path = root.path().join(relative);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        let original = b"{\r\n  \"id\":\"sample\", \"unknown\":[[1,2]]\r\n}".to_vec();
        fs::write(path, &original).unwrap();
        let doc = Document {
            token: "trusted".into(),
            relative: relative.into(),
            original,
            id: Some("sample".into()),
            review: None,
            writable: true,
            evidence_inputs: None,
        };
        let review = Review {
            token: "reviewed".into(),
            draft: "{\"id\":\"sample\",\"unknown\":[[1,2]],\"description\":\"edited\"}".into(),
            destination: relative.into(),
            variant: false,
            seed: 20261023,
            inputs: None,
        };
        (root, doc, review)
    }
    #[test]
    fn creature_entitlement_fifth_document_and_variant_only() {
        let (root, mut doc, mut review) = fixture();
        doc.relative = "roguelike/data/entities/creatures/sample.json".into();
        let path = root.path().join(&doc.relative);
        fs::create_dir_all(path.parent().unwrap()).unwrap(); fs::write(&path, &doc.original).unwrap();
        for path in ["roguelike/data/entities/../x.json", "roguelike/data/entities/x.json:ads", "roguelike/data/entities/creatures/nul.json", "roguelike/saves/creatures/x.json"] {
            assert!(!is_creature(path));
        }
        doc.writable = false;
        assert_eq!(destination(&doc, "{\"id\":\"promoted_player\"}", Some("promoted_player")).unwrap_err().code, "READ_ONLY_CREATURE");
        doc.writable = true;
        let host = Host::default();
        {
            let mut state = host.inner.lock().unwrap(); state.root = Some(root.path().to_path_buf());
            let state = &mut *state;
            for (token, slot) in [("structure", &mut state.document), ("pool", &mut state.pool_document), ("item", &mut state.item_document), ("recipe", &mut state.recipe_document)] {
                let mut other = doc.clone(); other.token = token.into(); *slot = Some(other);
            }
            state.creature_document = Some(doc.clone());
        }
        assert!(session_doc(&host, &doc.token).is_ok());
        for token in ["structure", "pool", "item", "recipe"] { assert!(session_doc(&host, token).is_ok()); }
        assert_eq!(publish(root.path(), &doc, &review, Fault::None).unwrap_err().code, "CREATURE_VARIANT_REQUIRED");
        review.variant = true; review.destination = "roguelike/data/entities/creatures/variant.json".into();
        review.draft = "{\"id\":\"variant\"}".into();
        for fault in [Fault::BeforeStage, Fault::AfterStage, Fault::BeforeReplace] {
            assert!(publish(root.path(), &doc, &review, fault).is_err());
            assert!(!root.path().join(&review.destination).exists());
            assert_eq!(fs::read(&path).unwrap(), doc.original);
        }
        assert!(publish(root.path(), &doc, &review, Fault::None).is_ok());
        assert_eq!(publish(root.path(), &doc, &review, Fault::None).unwrap_err().code, "VARIANT_EXISTS");
        assert_eq!(fs::read(&path).unwrap(), doc.original);
    }
    #[test]
    fn paths_and_identity_are_not_renderer_authority() {
        for p in [
            "../x.json",
            "C:/x.json",
            "roguelike/saves/x.json",
            "roguelike/data/buildings/../x.json",
            "roguelike/data/buildings/commercial/../x.json",
            "roguelike/data/buildings/commercial/a.json:ads",
            "roguelike/data/buildings/plaza/a.json",
            "roguelike/data/buildings/new/a.json",
            "roguelike/data/buildings/commercial/con.json",
            "roguelike/engine/x.py",
            "roguelike/data/layouts/x.json",
            "roguelike/data/buildings/commercial/x/y.json",
        ] {
            assert!(relative_building(p).is_err(), "{p}");
        }
        let (_, doc, _) = fixture();
        assert!(destination(&doc, "{\"id\":\"other\"}", None).is_err());
        assert!(destination(&doc, "{\"id\":\"other\"}", Some("../other")).is_err());
        assert!(session_doc(&Host::default(), "forged").is_err());
    }
    #[test]
    fn recipe_entitlement_four_documents_and_atomic_variant() {
        let (root, mut recipe, mut review) = fixture();
        recipe.relative = "roguelike/data/recipes/nested/sample.json".into(); recipe.token = "recipe".into();
        let path = root.path().join(&recipe.relative);
        fs::create_dir_all(path.parent().unwrap()).unwrap(); fs::write(&path, &recipe.original).unwrap();
        for p in ["roguelike/data/recipes/../saves/x.json", "roguelike/data/recipes/nul.json", "roguelike/data/recipes/x.json:ads", "roguelike/data/recipes/.git/x.json"] {
            assert!(!is_recipe(p));
        }
        recipe.writable = false;
        assert_eq!(destination(&recipe, "{\"id\":\"forged\"}", Some("forged")).unwrap_err().code, "READ_ONLY_RECIPE");
        recipe.writable = true; recipe.review = Some(review.clone());
        let host = Host::default();
        {
            let mut state = host.inner.lock().unwrap(); state.root = Some(root.path().to_path_buf());
            let mut a=recipe.clone(); a.token="building".into(); state.document=Some(a);
            let mut a=recipe.clone(); a.token="pool".into(); state.pool_document=Some(a);
            let mut a=recipe.clone(); a.token="item".into(); state.item_document=Some(a);
            state.recipe_document=Some(recipe.clone());
        }
        revoke_review(&host,"recipe");
        assert!(session_doc(&host,"recipe").unwrap().1.review.is_none());
        for token in ["building","pool","item"] { assert!(session_doc(&host,token).unwrap().1.review.is_some()); }
        assert_eq!(publish(root.path(),&recipe,&review,Fault::None).unwrap_err().code,"RECIPE_VARIANT_REQUIRED");
        review.variant=true; review.destination="roguelike/data/recipes/nested/variant.json".into();
        review.draft="{\"id\":\"variant\"}".into();
        for fault in [Fault::BeforeStage,Fault::AfterStage,Fault::BeforeReplace] {
            assert!(publish(root.path(),&recipe,&review,fault).is_err());
            assert_eq!(fs::read_dir(path.parent().unwrap()).unwrap().count(),1);
        }
        publish(root.path(),&recipe,&review,Fault::None).unwrap();
        assert_eq!(fs::read(&path).unwrap(),recipe.original);
        assert_eq!(fs::read(root.path().join(&review.destination)).unwrap(),review.draft.as_bytes());
        assert!(publish(root.path(),&recipe,&review,Fault::None).is_err());
        host.cancel(true).unwrap(); assert!(session_doc(&host,"recipe").is_err());
    }
    #[test]
    fn item_capability_paths_and_three_document_reviews() {
        let (root, mut item, review) = fixture();
        item.relative = "roguelike/data/items/components/nested/wood.json".into();
        item.token = "item".into();
        let path = root.path().join(&item.relative);
        fs::create_dir_all(path.parent().unwrap()).unwrap(); fs::write(&path, &item.original).unwrap();
        assert!(is_item(&item.relative));
        for p in ["roguelike/data/items/../saves/x.json", "roguelike/data/items/components/con.json",
                  "roguelike/data/items/components/x.json:ads", "roguelike/data/items/components/.git/x.json",
                  "roguelike/data/items/components/x.JSON", "roguelike/data/items/components/a/../../x.json"] {
            assert!(!is_item(p), "{p}");
        }
        item.writable = false;
        assert_eq!(destination(&item, "{}", None).unwrap_err().code, "READ_ONLY_ITEM");
        item.writable = true; item.review = Some(review.clone());
        let host = Host::default();
        {
            let mut state = host.inner.lock().unwrap(); state.root = Some(root.path().to_path_buf());
            let mut structure = item.clone(); structure.token = "building".into();
            let mut pool = item.clone(); pool.token = "pool".into();
            state.document = Some(structure); state.pool_document = Some(pool); state.item_document = Some(item);
        }
        revoke_review(&host, "item");
        assert!(session_doc(&host, "item").unwrap().1.review.is_none());
        assert!(session_doc(&host, "pool").unwrap().1.review.is_some());
        assert!(session_doc(&host, "building").unwrap().1.review.is_some());
        host.cancel(true).unwrap(); assert!(session_doc(&host, "item").is_err());
    }
    #[test]
    fn item_transaction_noclobber_conflict_and_rollback() {
        let (root, mut doc, mut review) = fixture();
        doc.relative = "roguelike/data/items/components/sample.json".into();
        review.destination = doc.relative.clone();
        let path = root.path().join(&doc.relative);
        fs::create_dir_all(path.parent().unwrap()).unwrap(); fs::write(&path, &doc.original).unwrap();
        for fault in [Fault::BeforeStage, Fault::AfterStage, Fault::BeforeReplace, Fault::AfterReplace] {
            assert!(publish(root.path(), &doc, &review, fault).is_err());
            assert_eq!(fs::read(&path).unwrap(), doc.original);
        }
        fs::write(&path, b"external change").unwrap();
        assert_eq!(publish(root.path(), &doc, &review, Fault::None).unwrap_err().code, "EXTERNAL_MODIFICATION_CONFLICT");
        fs::write(&path, &doc.original).unwrap();
        review.variant = true; review.destination = "roguelike/data/items/components/new_item.json".into();
        publish(root.path(), &doc, &review, Fault::None).unwrap();
        assert_eq!(fs::read(&path).unwrap(), doc.original);
        assert!(publish(root.path(), &doc, &review, Fault::None).is_err());
        review.destination = "roguelike/data/items/components/NEW_ITEM.json".into();
        assert_eq!(checked_target(root.path(), &review.destination, true).unwrap_err().code, "VARIANT_EXISTS");
    }
    #[test]
    fn replacement_validation_revokes_the_previous_review() {
        let (root, mut doc, review) = fixture();
        doc.review = Some(review);
        let host = Host::default();
        {
            let mut state = host.inner.lock().unwrap();
            state.root = Some(root.path().to_path_buf());
            state.document = Some(doc);
        }
        revoke_review(&host, "forged");
        assert!(session_doc(&host, "trusted").unwrap().1.review.is_some());
        revoke_review(&host, "trusted");
        assert!(session_doc(&host, "trusted").unwrap().1.review.is_none());
    }
    #[test]
    fn pool_and_building_tokens_are_independent_and_paths_stay_confined() {
        let (root, doc, review) = fixture();
        let mut pool = doc.clone();
        pool.token = "pool".into();
        pool.relative = "roguelike/data/loot_pools/sample.json".into();
        pool.review = Some(review);
        let host = Host::default();
        {
            let mut state = host.inner.lock().unwrap();
            state.root = Some(root.path().to_path_buf());
            state.document = Some(doc);
            state.pool_document = Some(pool.clone());
        }
        assert!(session_doc(&host, "trusted").is_ok());
        assert_eq!(session_doc(&host, "pool").unwrap().1.relative, pool.relative);
        revoke_review(&host, "trusted");
        assert!(session_doc(&host, "pool").unwrap().1.review.is_some());
        for p in ["roguelike/data/loot_pools/nested/a.json", "roguelike/data/loot_pools/../a.json",
                  "roguelike/data/loot_pools/con.json", "roguelike/data/loot_pools/a.json:ads",
                  "roguelike/data/loot/a.json", "roguelike/saves/a.json", ".git/a.json", "workbench/docs/a.json"] {
            assert!(relative_content(p).is_err(), "{p}");
        }
        assert!(relative_content(&pool.relative).is_ok());
        host.cancel(true).unwrap();
        assert!(session_doc(&host, "pool").is_err());
        assert!(session_doc(&host, "trusted").is_err());
    }
    #[test]
    #[cfg(windows)]
    fn pool_publication_conflicts_rollback_and_unique_variant() {
        for fault in [Fault::AfterStage, Fault::AfterReplace, Fault::ConcurrentReplace] {
            let (root, mut doc, mut review) = fixture();
            doc.relative = "roguelike/data/loot_pools/sample.json".into();
            review.destination = doc.relative.clone();
            let path = root.path().join(&doc.relative);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(&path, &doc.original).unwrap();
            assert!(publish(root.path(), &doc, &review, fault).is_err());
            if fault != Fault::ConcurrentReplace { assert_eq!(fs::read(&path).unwrap(), doc.original); }
            fs::write(&path, b"external pool bytes").unwrap();
            assert_eq!(publish(root.path(), &doc, &review, Fault::None).unwrap_err().code, "EXTERNAL_MODIFICATION_CONFLICT");
            fs::write(&path, &doc.original).unwrap();
            review.destination = "roguelike/data/loot_pools/sample_new.json".into();
            review.draft = "{\"id\":\"sample_new\",\"items\":[]}".into();
            review.variant = true;
            publish(root.path(), &doc, &review, Fault::None).unwrap();
            assert_eq!(fs::read(&path).unwrap(), doc.original);
            assert_eq!(fs::read(root.path().join(&review.destination)).unwrap(), review.draft.as_bytes());
            assert_eq!(publish(root.path(), &doc, &review, Fault::None).unwrap_err().code, "VARIANT_EXISTS");
        }
    }
    #[test]
    #[cfg(windows)]
    fn replacement_conflict_and_failure_recovery() {
        for fault in [
            Fault::BeforeStage,
            Fault::AfterStage,
            Fault::BeforeReplace,
            Fault::AfterReplace,
        ] {
            let (root, doc, review) = fixture();
            let _pins = pin_inputs(root.path(), &root.path().join(&doc.relative)).unwrap();
            let failure = publish(root.path(), &doc, &review, fault).unwrap_err();
            assert!(failure.message.contains("Injected"), "{}", failure.message);
            assert_eq!(
                fs::read(root.path().join(&doc.relative)).unwrap(),
                doc.original
            );
            assert_eq!(
                fs::read_dir(root.path().join(&doc.relative).parent().unwrap())
                    .unwrap()
                    .count(),
                1
            );
        }
        let (root, doc, review) = fixture();
        let path = root.path().join(&doc.relative);
        fs::write(&path, b"external version").unwrap();
        assert_eq!(
            publish(root.path(), &doc, &review, Fault::None)
                .unwrap_err()
                .code,
            "EXTERNAL_MODIFICATION_CONFLICT"
        );
        assert_eq!(fs::read(&path).unwrap(), b"external version");
    }
    #[test]
    #[cfg(windows)]
    fn readonly_target_rejected_and_original_reopens() {
        let (root, doc, review) = fixture();
        let path = root.path().join(&doc.relative);
        let old = path.metadata().unwrap().permissions();
        let mut locked = old.clone();
        locked.set_readonly(true);
        fs::set_permissions(&path, locked).unwrap();
        let result = publish(root.path(), &doc, &review, Fault::None);
        fs::set_permissions(&path, old).unwrap();
        assert!(result.is_err());
        assert_eq!(read_source(&path).unwrap(), doc.original);
        assert_eq!(fs::read_dir(path.parent().unwrap()).unwrap().count(), 1);
    }
    #[test]
    #[cfg(windows)]
    fn edit_between_compare_and_replace_is_recovered_from_actual_backup() {
        let (root, doc, review) = fixture();
        let path = root.path().join(&doc.relative);
        let _pins = pin_inputs(root.path(), &path).unwrap();
        assert_eq!(
            publish(root.path(), &doc, &review, Fault::ConcurrentReplace)
                .unwrap_err()
                .code,
            "EXTERNAL_MODIFICATION_CONFLICT"
        );
        assert_eq!(
            read_source(&path).unwrap(),
            b"external edit between comparison and replacement"
        );
        assert_eq!(fs::read_dir(path.parent().unwrap()).unwrap().count(), 1);
    }
    #[test]
    #[cfg(windows)]
    fn windows_replace_metadata_locks_and_variant_noclobber() {
        use std::os::windows::fs::{MetadataExt, OpenOptionsExt};
        let (root, doc, mut review) = fixture();
        let path = root.path().join(&doc.relative);
        let creation = path.metadata().unwrap().creation_time();
        let lock = OpenOptions::new()
            .read(true)
            .share_mode(1)
            .open(&path)
            .unwrap();
        assert!(publish(root.path(), &doc, &review, Fault::None).is_err());
        assert_eq!(fs::read(&path).unwrap(), doc.original);
        drop(lock);
        let _pins = pin_inputs(root.path(), &path).unwrap();
        let source_lock = pin_source(&path).unwrap();
        assert!(OpenOptions::new().write(true).open(&path).is_err());
        drop(source_lock);
        publish(root.path(), &doc, &review, Fault::None).unwrap();
        assert_eq!(fs::read(&path).unwrap(), review.draft.as_bytes());
        assert_eq!(path.metadata().unwrap().creation_time(), creation);
        drop(_pins);
        let updated = Document {
            original: review.draft.as_bytes().to_vec(),
            ..doc
        };
        review.variant = true;
        review.destination = "roguelike/data/buildings/commercial/variant.json".into();
        publish(root.path(), &updated, &review, Fault::None).unwrap();
        assert!(publish(root.path(), &updated, &review, Fault::None).is_err());
        assert_eq!(fs::read_dir(path.parent().unwrap()).unwrap().count(), 2);
    }
}
