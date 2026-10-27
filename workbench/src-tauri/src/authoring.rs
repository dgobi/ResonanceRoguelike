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
// Host-owned filesystem registration. Descriptors cannot enlarge these roots.
// (source root, publication root, reserved basenames)
const CONTENT_ROOTS: &[(&str, &str, &[&str])] = &[
    ("roguelike/data/items/", "roguelike/data/items/components/", &[]),
    ("roguelike/data/recipes/", "roguelike/data/recipes/", &[]),
    ("roguelike/data/texts/", "roguelike/data/texts/", &["text_item_map.json"]),
];
pub fn content_root(source: &str) -> Option<&'static str> {
    CONTENT_ROOTS.iter().find_map(|(source_root, write_root, reserved)| {
        let suffix = source.strip_prefix(source_root)?;
        let parts: Vec<_> = suffix.split('/').collect();
        (parts[..parts.len()-1].iter().all(|s| valid_id(s)) && valid_filename(parts[parts.len()-1])
            && !reserved.iter().any(|name| parts[parts.len()-1].eq_ignore_ascii_case(name))).then_some(*write_root)
    })
}
/// Only a verified worker result can supply this policy. Renderer arguments have
/// no schema/policy fields. Filesystem confinement is independently host-owned.
#[derive(Clone)]
struct FamilyPolicy {
    id: String,
    route: String,
    contract: String,
    descriptor: Value,
    digest: String,
    root: String,
    operations: Vec<String>,
}
impl FamilyPolicy {
    fn from_result(result: &Value, source: &str) -> Option<Self> {
        let f = &result["family"];
        let d = &f["descriptor"];
        let id = f["id"].as_str()?;
        let route = result["route"].as_str()?;
        let contract = f["contract"].as_str()?;
        let digest = f["descriptor_sha256"].as_str()?;
        let root = d["policy"]["root"].as_str()?;
        let operations: Vec<String> = d["policy"]["operations"].as_array()?.iter()
            .map(|v| v.as_str().map(str::to_owned)).collect::<Option<_>>()?;
        if f["compatible"] != true || !valid_id(id) || contract.is_empty() || contract.len() > 100
            || route != format!("{id}_definition") || digest.len() != 64 || !digest.bytes().all(|b| b.is_ascii_hexdigit())
            || d["vocabulary"] != "resonance-controls-1" || d["schema"]["$schema"] != "https://json-schema.org/draft/2020-12/schema"
            || d["policy"]["identity"] != "id" || operations.is_empty()
            || operations.iter().any(|op| op != "edit" && op != "variant")
            || content_root(source) != Some(root)
        { return None; }
        Some(Self { id:id.into(), route:route.into(), contract:contract.into(), descriptor:d.clone(), digest:digest.into(), root:root.into(), operations })
    }
}
fn family_evidence(doc: &Document, result: &Value, variant: bool) -> bool {
    let Some(policy) = &doc.family else { return content_root(&doc.relative).is_none(); };
    let Some(current) = FamilyPolicy::from_result(result, &doc.relative) else { return false; };
    current.id == policy.id && current.contract == policy.contract && current.digest == policy.digest
        && current.descriptor == policy.descriptor && current.route == policy.route
        && policy.operations.iter().any(|op| op == if variant { "variant" } else { "edit" })
        && result["semantic_verified"] == true && result["source_asset"] == doc.relative
        && result["source_sha256"] == hash(&doc.original)
}
#[derive(Clone)]
pub struct Document {
    token: String,
    relative: String,
    original: Vec<u8>,
    id: Option<String>,
    review: Option<Review>,
    writable: bool,
    family: Option<FamilyPolicy>,
    evidence_inputs: Option<String>,
    revision: u64,
    attempt: u64,
    inspection: Value,
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
// Session-local completed write identity. It cannot authorize another write.
#[derive(Clone)]
pub struct Handoff {
    source: String,
    revision: u64,
    path: String,
    sha256: String,
    replacement: Option<String>,
}
fn handoff_owner(state: &mut Session, id: &str, asset: &str, expected: Option<&str>) -> Result<(String, bool), Failure> {
    let h = state.handoffs.get(id).cloned().ok_or_else(unknown_document)?;
    if file_key(asset) != file_key(&h.path) || expected != Some(h.sha256.as_str()) { return Err(conflict()); }
    let token = h.replacement.as_ref().unwrap_or(&h.source);
    let doc = current_document(state, token).ok_or_else(unknown_document)?;
    let revision = if h.replacement.is_some() { 0 } else { h.revision };
    if doc.revision != revision { return Err(failure("NEWER_DRAFT", "Published candidate no longer covers this document.", "Keep or copy the newer draft before deliberate reconciliation.")); }
    Ok((token.clone(), h.replacement.is_some()))
}
pub(crate) fn hash(bytes: &[u8]) -> String {
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
#[cfg(test)]
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
pub const G17_EXAMPLE: &str = "roguelike/docs/examples/g17_authored_creature_room.json";
pub fn is_layout(s: &str) -> bool {
    let p: Vec<_> = s.split('/').collect();
    p.len() == 4 && p[..3] == ["roguelike", "data", "layouts"] && valid_filename(p[3])
}
fn is_submap(s: &str) -> bool { is_layout(s) || s == G17_EXAMPLE }
fn dependency_bound(s: &str) -> bool { content_root(s).is_some() || is_creature(s) || is_layout(s) || s == G17_EXAMPLE }
fn relative_content(s: &str) -> Result<PathBuf, Failure> {
    if is_pool(s) || content_root(s).is_some() || is_creature(s) || is_layout(s) || s == G17_EXAMPLE { Ok(PathBuf::from(s)) } else { relative_building(s) }
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
    if new && relative == G17_EXAMPLE { return Err(failure("PATH_ESCAPE", "Documentation is read-only.", "Save a supported layout variant.")); }
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
#[cfg(test)]
fn session_doc(host: &Host, token: &str) -> Result<(PathBuf, Document), Failure> {
    let state = host.inner.lock().unwrap();
    let doc = state
        .document
        .as_ref()
        .into_iter()
        .chain(state.pool_document.as_ref())
        .chain(state.content_documents.values()).chain(state.creature_document.as_ref())
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
fn revoke(doc: &mut Document) {
    doc.attempt += 1;
    doc.review = None;
}
pub(super) fn revoke_all(state: &mut Session) {
    for doc in state.document.iter_mut().chain(state.pool_document.iter_mut()).chain(state.content_documents.values_mut()).chain(state.creature_document.iter_mut()) { revoke(doc); }
}
#[cfg(test)]
fn revoke_review(host: &Host, token: &str) {
    let mut state = host.inner.lock().unwrap();
    if !state.applying {
        if let Some(doc) = current_document(&mut state, token) { revoke(doc); }
    }
}
#[tauri::command]
pub fn invalidate_document(host: tauri::State<'_, Host>, token: String) -> Result<(), Failure> {
    advance_document(&host, &token)
}
fn advance_document(host: &Host, token: &str) -> Result<(), Failure> {
    let mut state = host.inner.lock().unwrap();
    if state.applying { return Err(busy_failure()); }
    let doc = current_document(&mut state, token).ok_or_else(|| io_error("Document changed."))?;
    doc.revision += 1;
    revoke(doc);
    Ok(())
}
fn current_document<'a>(state: &'a mut Session, token: &str) -> Option<&'a mut Document> {
    state.document.as_mut().into_iter().chain(state.pool_document.as_mut()).chain(state.content_documents.values_mut()).chain(state.creature_document.as_mut()).find(|d| d.token == token)
}
fn envelope(result: Value) -> Value {
    json!({"protocol":PROTOCOL,"id":uuid::Uuid::new_v4().to_string(),"ok":true,"result":result,"host_elapsed_ms":0})
}

// File ownership is scoped by Session's canonical project root. Discovery
// supplies spelling; Windows aliases share one key. IDs/pointers are metadata.
fn file_key(relative: &str) -> String {
    if cfg!(windows) { relative.replace('\\', "/").to_lowercase() }
    else { relative.to_owned() }
}
fn discovered_path(state: &Session, asset: &str) -> Result<String, Failure> {
    let key = file_key(asset);
    state.discovered.iter().find(|p| file_key(p) == key).cloned()
        .ok_or_else(|| failure("UNKNOWN_SOURCE", "Source was not returned by trusted discovery.", "Refresh the asset index and select a supported file."))
}
fn replacement_snapshot(state: &mut Session, token: Option<&str>) -> Result<Option<Document>, Failure> {
    token.map(|t| current_document(state, t).cloned().ok_or_else(unknown_document)).transpose()
}
fn check_replacement(state: &mut Session, previous: Option<&Document>) -> Result<(), Failure> {
    if let Some(previous) = previous {
        let current = current_document(state, &previous.token).ok_or_else(unknown_document)?;
        if current.revision != previous.revision || current.attempt != previous.attempt {
            return Err(failure("DRAFT_CHANGED", "Document changed while reopening.", "Keep the draft and deliberately reload again."));
        }
    }
    Ok(())
}
fn owner_collision(state: &Session, asset: &str, replacing: Option<&str>) -> Result<(), Failure> {
    if state.content_documents.get(&file_key(asset)).is_some_and(|d| Some(d.token.as_str()) != replacing) {
        return Err(failure("DOCUMENT_OPEN", "The destination already has an open document.", "Keep its draft, or deliberately close that document before retrying."));
    }
    Ok(())
}
fn remove_document(host: &Host, token: &str) -> Result<(), Failure> {
    let mut state = host.inner.lock().unwrap();
    if state.applying { return Err(busy_failure()); }
    let key = state.content_documents.iter().find(|(_, d)| d.token == token).map(|(k, _)| k.clone()).ok_or_else(unknown_document)?;
    state.content_documents.remove(&key);
    // Do not kill a worker or release resources belonging to another document.
    Ok(())
}
#[tauri::command]
pub fn close_document(host: tauri::State<'_, Host>, token: String) -> Result<(), Failure> {
    remove_document(&host, &token)
}

fn begin_validation(host: &Host, token: &str) -> Result<(Operation, PathBuf, Document), Failure> {
    let mut state = host.inner.lock().unwrap();
    // Rejected requests do not revoke anything. Accepted requests revoke before
    // filesystem/identity/worker checks, including replacements that fail early.
    if state.busy.is_some() || state.applying { return Err(busy_failure()); }
    let root = state.root.clone().ok_or_else(|| io_error("No project open."))?;
    let doc = current_document(&mut state, token).ok_or_else(unknown_document)?;
    revoke(doc);
    let doc = doc.clone();
    let operation = Operation::reserve(host, &mut state, false)?;
    Ok((operation, root, doc))
}
fn unknown_document() -> Failure {
    failure("UNKNOWN_DOCUMENT", "Document identity is stale or forged.", "Open the definition again from discovery.")
}
fn install_validation(operation: &Operation, doc: &Document, inputs: Option<String>, review: Option<Review>) -> Result<(), Failure> {
    let mut state = operation.host.inner.lock().unwrap();
    operation.check(&state)?;
    let current = current_document(&mut state, &doc.token).ok_or_else(unknown_document)?;
    if current.revision != doc.revision || current.attempt != doc.attempt {
        return Err(failure("DRAFT_CHANGED", "Draft changed. Validate again.", "Validate the current draft."));
    }
    current.review = review;
    current.evidence_inputs = inputs;
    Ok(())
}

fn admit_apply(host: &Host, token: &str, review_token: &str, confirmed: bool, before_reservation: impl FnOnce()) -> Result<(Operation, PathBuf, Document, Review), Failure> {
    // Test-only callers can pause before admission. There is no snapshot before
    // this lock: authorization, consumption and transaction inputs are atomic.
    before_reservation();
    let mut state = host.inner.lock().unwrap();
    if state.busy.is_some() || state.applying { return Err(busy_failure()); }
    let root = state.root.clone().ok_or_else(|| io_error("No project open."))?;
    let doc = current_document(&mut state, token).ok_or_else(unknown_document)?;
    let review = doc.review.as_ref().filter(|r| r.token == review_token)
        .ok_or_else(|| failure("REVIEW_REQUIRED", "A current valid review is required.", "Validate this draft and review the source diff."))?.clone();
    if !confirmed { return Err(failure("CONFIRMATION_REQUIRED", "Apply must be deliberate.", "Read the diff and confirm this single-file change.")); }
    doc.review = None;
    let doc = doc.clone();
    owner_collision(&state, &review.destination, Some(&doc.token))?;
    let operation = Operation::reserve(host, &mut state, true)?;
    Ok((operation, root, doc, review))
}

#[tauri::command]
pub async fn open_document(
    app: tauri::AppHandle,
    host: tauri::State<'_, Host>,
    asset: String,
    replace_token: Option<String>,
    expected_sha256: Option<String>,
    handoff_id: Option<String>,
) -> Result<Value, Failure> {
    let operation = Operation::begin(&host)?;
    let host = host.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let (root, asset, discovered_family, previous, replace_token, already_reopened) = {
            let mut state = host.inner.lock().unwrap();
            operation.check(&state)?;
            let asset = discovered_path(&state, &asset)?;
            let family = state.discovered_families.get(&asset).cloned();
            let (replace_token, already_reopened) = if let Some(id) = &handoff_id {
                let (token, done) = handoff_owner(&mut state, id, &asset, expected_sha256.as_deref())?;
                (Some(token), done)
            } else { (replace_token, false) };
            let previous = replacement_snapshot(&mut state, replace_token.as_deref())?;
            if family.is_some() {
                if replace_token.is_none() {
                    if let Some(existing) = state.content_documents.get(&file_key(&asset)) {
                        return Ok(envelope(existing.inspection.clone()));
                    }
                }
                owner_collision(&state, &asset, replace_token.as_deref())?;
            }
            (state
                .root
                .clone()
                .ok_or_else(|| io_error("No project open."))?, asset, family, previous, replace_token, already_reopened)
        };
        let path = checked_target(&root, &asset, false)?;
        let original = read_source(&path)?;
        if expected_sha256.as_ref().is_some_and(|expected| *expected != hash(&original)) {
            return Err(conflict());
        }
        if already_reopened {
            let mut state=host.inner.lock().unwrap(); operation.check(&state)?;
            check_replacement(&mut state, previous.as_ref())?;
            return Ok(envelope(previous.unwrap().inspection));
        }
        let evidence_inputs = if dependency_bound(&asset) { Some(input_stamp(&root)?) } else { None };
        let mut response = run_worker(
            app,
            &operation,
            Request {
                op: "inspect".into(),
                asset: Some(asset.clone()),
                ..Default::default()
            },
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
        operation.check(&state)?;
        check_replacement(&mut state, previous.as_ref())?;
        let family = FamilyPolicy::from_result(&response["result"], &asset)
            .filter(|f| discovered_family.as_ref() == Some(&f.id));
        let writable = if content_root(&asset).is_some() {
            family.as_ref().is_some_and(|f| asset.starts_with(&f.root)) && response["result"]["editable"] == true
        } else if is_submap(&asset) { response["result"]["editable"] == true && response["result"]["layout_contract"] == "direct-creatures-1" }
        else if is_creature(&asset) { asset.starts_with("roguelike/data/entities/creatures/") && response["result"]["editable"] == true } else { true };
        let registered = discovered_family.is_some();
        if registered { owner_collision(&state, &asset, replace_token.as_deref())?; }
        response["result"]["document_token"] = json!(token);
        response["result"]["file_identity"] = json!(file_key(&asset));
        let document = Document {
            family,
            token: token.clone(),
            relative: asset,
            original,
            id,
            review: None,
            writable,
            evidence_inputs,
            revision: 0,
            attempt: 0,
            inspection: response["result"].clone(),
        };
        if registered {
            if let Some(previous) = previous { state.content_documents.retain(|_, d| d.token != previous.token); }
            state.content_documents.insert(file_key(&document.relative), document);
            if let Some(id)=handoff_id { state.handoffs.get_mut(&id).ok_or_else(unknown_document)?.replacement=Some(token); }
        }
        else {
            let slot = if is_pool(&document.relative) { &mut state.pool_document } else if is_creature(&document.relative) { &mut state.creature_document } else { &mut state.document };
            *slot = Some(document);
        }
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
        return Err(failure(if is_submap(&doc.relative) || doc.relative == G17_EXAMPLE { "READ_ONLY_LAYOUT" } else if is_creature(&doc.relative) { "READ_ONLY_CREATURE" } else if is_recipe(&doc.relative) { "READ_ONLY_RECIPE" } else { "READ_ONLY_ITEM" }, "This source is outside its supported authoring capability.", "Inspect unsupported or ambiguous sources read-only."));
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
            format!("{}/{}.json", if doc.relative == G17_EXAMPLE { "roguelike/data/layouts" } else { doc.relative.rsplit_once('/').unwrap().0 }, id),
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
    preview_inputs: Option<Value>,
) -> Result<Value, Failure> {
    let (operation, root, doc) = begin_validation(&host, &token)?;
    tauri::async_runtime::spawn_blocking(move || {
        let seed = seed.unwrap_or(20261023);
        let source_path = checked_target(&root, &doc.relative, false)?;
        if read_source(&source_path)? != doc.original {
            return Err(conflict());
        }
        let (dest, variant) = destination(&doc, &draft, variant_id.as_deref())?;
        checked_target(&root, &dest, variant)?;
        let inputs = if dependency_bound(&doc.relative) { Some(input_stamp(&root)?) } else { None };
        let preview_only = preview_inputs.is_some();
        let mut response = run_worker(
            app,
            &operation,
            Request {
                op: "preview_draft".into(),
                asset: Some(dest.clone()),
                draft: Some(draft.clone()),
                source_asset: (doc.family.is_some() || is_creature(&doc.relative) || is_submap(&doc.relative)).then(|| doc.relative.clone()),
                seed: Some(seed),
                preview_inputs,
                ..Default::default()
            },
        )?;
        if read_source(&source_path)? != doc.original {
            return Err(conflict());
        }
        if let Some(stamp) = &inputs {
            if input_stamp(&root)? != *stamp { return Err(failure("SOURCE_CHANGED", "Content dependencies changed during validation.", "Validate again.")); }
        }
        if response["ok"] == true {
            if let Some(policy) = &doc.family {
                if !FamilyPolicy::from_result(&response["result"], &doc.relative).is_some_and(|current|
                    current.id == policy.id && current.contract == policy.contract && current.digest == policy.digest && current.descriptor == policy.descriptor)
                {
                    return Err(failure("CONTRACT_CHANGED", "The opened content descriptor is incompatible or changed.", "Retain the exact draft, then reopen its source to obtain the current contract."));
                }
            }
        }
        let mut review = None;
        if response["ok"] == true
            && !preview_only
            && response["result"]["valid"] == true
            && response["result"]["draft_sha256"] == hash(draft.as_bytes())
            && (!(is_creature(&doc.relative) || is_submap(&doc.relative)) || variant)
            && family_evidence(&doc, &response["result"], variant)
            && (!is_submap(&doc.relative) || (response["result"]["layout_contract"] == "direct-creatures-1" && response["result"]["population_verified"] == true && response["result"]["route"] == "authored_submap"))
            && (!is_creature(&doc.relative) || (response["result"]["creature_contract"] == "revenant-hp-1" && response["result"]["factory_verified"] == true && response["result"]["route"] == "creature_definition"))
        {
            let review_token = uuid::Uuid::new_v4().to_string();
            review = Some(Review {
                token: review_token.clone(),
                draft,
                destination: dest,
                variant,
                seed,
                inputs: inputs.clone(),
            });
            response["result"]["review_token"] = json!(review_token);
        }
        install_validation(&operation, &doc, inputs, review)?;
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
    let examples = root.join("roguelike/docs/examples");
    if examples.exists() {
        handles.push(pin(&root.join("roguelike/docs"), true)?);
        handles.push(pin(&examples, true)?);
        for name in ["g17_authored_creature_room.json", "g17_authored_creature_room.access.json"] {
            let p = examples.join(name);
            if p.exists() && dunce::canonicalize(&p).map_err(io_error)? != dunce::canonicalize(target).map_err(io_error)? {
                handles.push(pin(&p, false)?);
            }
        }
    }
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
    // Production preview resources also invalidate evidence. Keep the existing
    // conservative Python/data stamp; this only extends its dependency coverage.
    fn resources(path: &Path, digest: &mut Sha256) -> Result<(), Failure> {
        no_link(path)?;
        if path.is_dir() {
            let mut entries = fs::read_dir(path).map_err(io_error)?.collect::<Result<Vec<_>, _>>().map_err(io_error)?;
            entries.sort_by_key(|e| e.file_name());
            for entry in entries { resources(&entry.path(), digest)?; }
        } else { digest.update(path.to_string_lossy().as_bytes()); digest.update(fs::read(path).map_err(io_error)?); }
        Ok(())
    }
    for relative in ["roguelike/assets/Fonts", "roguelike/assets/ui"] {
        digest.update(relative.as_bytes());
        let path = root.join(relative);
        if path.exists() { no_link(&root.join("roguelike/assets"))?; resources(&path, &mut digest)?; }
    }
    // Fixed read-only example inputs; never broaden documentation write access.
    for relative in [G17_EXAMPLE, "roguelike/docs/examples/g17_authored_creature_room.access.json"] {
        digest.update(relative.as_bytes());
        let path = root.join(relative);
        if path.exists() {
            let mut cursor = root.to_path_buf();
            for component in Path::new(relative).components() { cursor.push(component); no_link(&cursor)?; }
            digest.update(fs::read(path).map_err(io_error)?);
        }
    }
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
    if is_submap(&doc.relative) && !review.variant {
        return Err(failure("LAYOUT_VARIANT_REQUIRED", "Layout publication requires a new ID/file in layouts/.", "Review a unique layout variant."));
    }
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
    let (operation, root, doc, review) = admit_apply(&host, &token, &review_token, confirmed, || {})?;
    let host = host.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let mut result = (|| {
            let target = checked_target(&root, &doc.relative, false)?;
            let _pins = pin_inputs(&root, &target)?;
            let source_lock = pin_source(&target)?;
            let stamp = input_stamp(&root)?;
            if read_source(&target)? != doc.original { return Err(conflict()); }
            if review.inputs.as_ref().is_some_and(|s| *s != stamp) {
                return Err(failure("SOURCE_CHANGED", "Content dependencies changed since review.", "Validate the retained draft and review again."));
            }
            let response = run_worker(app, &operation, Request {op:"preview_draft".into(),asset:Some(review.destination.clone()),draft:Some(review.draft.clone()),source_asset:(doc.family.is_some() || is_creature(&doc.relative) || is_submap(&doc.relative)).then(||doc.relative.clone()),seed:Some(review.seed),..Default::default()})?;
            if response["ok"] != true || response["result"]["valid"] != true || response["result"]["draft_sha256"] != hash(review.draft.as_bytes())
                || response["result"]["route"] != if let Some(family) = &doc.family { family.route.as_str() } else if is_pool(&doc.relative) { "contextual_loot_pool" } else if is_creature(&doc.relative) { "creature_definition" } else if is_submap(&doc.relative) { "authored_submap" } else { "ordinary_building" }
                || response["result"]["contract"] != "g2-2" || response["result"]["worker_version"] != env!("CARGO_PKG_VERSION")
                || (is_submap(&doc.relative) && (!review.variant || response["result"]["layout_contract"] != "direct-creatures-1" || response["result"]["population_verified"] != true))
                || !family_evidence(&doc, &response["result"], review.variant)
                || (is_creature(&doc.relative) && (!review.variant || response["result"]["creature_contract"] != "revenant-hp-1" || response["result"]["factory_verified"] != true))
                || (!is_creature(&doc.relative) && !is_pool(&doc.relative) && doc.family.is_none() && response["result"]["preview"]["passed"] != true) {
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
        operation.check(&state)?;
        revoke_all(&mut state);
        if let Ok(receipt)=&mut result {
            if doc.family.is_some() {
                let id=uuid::Uuid::new_v4().to_string();
                state.handoffs.insert(id.clone(),Handoff {source:doc.token.clone(),revision:doc.revision,
                    path:review.destination.clone(),sha256:hash(review.draft.as_bytes()),replacement:None});
                receipt["handoff_id"]=json!(id);
            }
        }
        drop(state);
        result.map(envelope)
    }).await.map_err(io_error)?
}

fn disk_result(root: &Path, doc: &Document, stamp: Option<&str>) -> Result<Value, Failure> {
    let path = checked_target(root, &doc.relative, false)?;
    let bytes = read_source(&path)?;
    let dependencies_changed = doc.evidence_inputs.as_deref().is_some_and(|old| Some(old) != stamp);
    let pending: Vec<_> = fs::read_dir(path.parent().unwrap())
        .map_err(io_error)?
        .filter_map(Result::ok)
        .filter(|e| e.file_name().to_string_lossy().starts_with(".w1-"))
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .collect();
    Ok(
        json!({"changed":bytes != doc.original,"dependencies_changed":dependencies_changed,"raw":String::from_utf8(bytes.clone()).map_err(io_error)?,"sha256":hash(&bytes),"recovery_files":pending}),
    )
}
fn install_disk(operation: &Operation, doc: &Document, result: &Result<Value, Failure>) -> Result<bool, Failure> {
    let mut state = operation.host.inner.lock().unwrap();
    operation.check(&state)?;
    let Some(current) = current_document(&mut state, &doc.token) else { return Ok(false); };
    if current.revision != doc.revision || current.attempt != doc.attempt { return Ok(false); }
    if result.as_ref().map_or(true, |r| r["changed"] == true || r["dependencies_changed"] == true) { revoke(current); }
    Ok(true)
}
fn sweep_disk(operation: &Operation, token: Option<&str>, stamp_fn: impl FnOnce(&Path) -> Result<String, Failure>) -> Result<Value, Failure> {
    let started = Instant::now();
    let (root, documents) = {
        let state = operation.host.inner.lock().unwrap();
        operation.check(&state)?;
        let docs: Vec<_> = state.document.iter().chain(state.pool_document.iter()).chain(state.content_documents.values()).chain(state.creature_document.iter())
            .filter(|d| token.is_none_or(|t| t == d.token)).cloned().collect();
        if token.is_some() && docs.is_empty() { return Err(unknown_document()); }
        (state.root.clone().ok_or_else(|| io_error("No project open."))?, docs)
    };
    let scans = usize::from(documents.iter().any(|d| d.evidence_inputs.is_some()));
    let stamp = if scans > 0 { Some(stamp_fn(&root)) } else { None };
    let mut results = Vec::new();
    for doc in documents {
        let result = match &stamp {
            Some(Err(error)) => Err(error.clone()),
            Some(Ok(stamp)) => disk_result(&root, &doc, Some(stamp)),
            None => disk_result(&root, &doc, None),
        };
        if install_disk(operation, &doc, &result)? {
            results.push(match result {
                Ok(disk) => json!({"token":doc.token,"revision":doc.revision,"attempt":doc.attempt,"disk":disk}),
                Err(error) => json!({"token":doc.token,"revision":doc.revision,"attempt":doc.attempt,"error":error}),
            });
        }
    }
    Ok(json!({"documents":results,"dependency_scans":scans,"elapsed_ms":started.elapsed().as_secs_f64()*1000.0,"project_epoch":operation.epoch}))
}
#[tauri::command]
pub async fn workspace_disk(host: tauri::State<'_, Host>) -> Result<Value, Failure> {
    let operation = Operation::begin(&host)?;
    tauri::async_runtime::spawn_blocking(move || sweep_disk(&operation, None, input_stamp).map(envelope)).await.map_err(io_error)?
}
#[tauri::command]
pub fn document_disk(host: tauri::State<'_, Host>, token: String) -> Result<Value, Failure> {
    let operation = Operation::begin(&host)?;
    let result = sweep_disk(&operation, Some(&token), input_stamp)?;
    let row = &result["documents"][0];
    if row.get("error").is_some() { return Err(io_error(row["error"]["message"].as_str().unwrap_or("Disk check failed."))); }
    if row.get("disk").is_none() { return Err(unknown_document()); }
    Ok(envelope(row["disk"].clone()))
}
#[tauri::command]
pub fn finish_close(window: tauri::Window, host: tauri::State<'_, Host>) -> Result<(), Failure> {
    host.cancel(true)?;
    window.destroy().map_err(io_error)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn workspace_fixture() -> (tempfile::TempDir, Host, Vec<Document>) {
        let (root, host, first, _) = lifecycle_fixture(false);
        let mut documents = vec![first.clone()];
        {
            let mut state = host.inner.lock().unwrap();
            for (token, relative) in [("item2","roguelike/data/items/components/second.json"),
                ("recipe1","roguelike/data/recipes/first.json"),("recipe2","roguelike/data/recipes/second.json"),
                ("text1","roguelike/data/texts/first.json"),("text2","roguelike/data/texts/second.json")] {
                let mut doc = first.clone();doc.token=token.into();doc.relative=relative.into();
                let path=root.path().join(relative);fs::create_dir_all(path.parent().unwrap()).unwrap();fs::write(path,&doc.original).unwrap();
                state.content_documents.insert(file_key(relative),doc.clone());documents.push(doc);
            }
            state.discovered.extend(documents.iter().map(|d|d.relative.clone()));
        }
        (root,host,documents)
    }
    #[test]
    fn completed_handoff_rejects_newer_drafts_and_reacquires_only_its_successor() {
        let (_root,host,docs)=workspace_fixture();
        let first=&docs[0]; let mut state=host.inner.lock().unwrap();
        let h=Handoff {source:first.token.clone(),revision:first.revision,path:first.relative.clone(),sha256:hash(&first.original),replacement:None};
        state.handoffs.insert("fact".into(),h.clone());
        assert_eq!(handoff_owner(&mut state,"fact",&h.path,Some(&h.sha256)).unwrap(),(first.token.clone(),false));
        current_document(&mut state,&first.token).unwrap().revision+=1;
        assert_eq!(handoff_owner(&mut state,"fact",&h.path,Some(&h.sha256)).unwrap_err().code,"NEWER_DRAFT");
        let mut replacement=first.clone();replacement.token="successor".into();replacement.revision=0;
        state.content_documents.insert(file_key(&h.path),replacement);
        state.handoffs.get_mut("fact").unwrap().replacement=Some("successor".into());
        assert!(replacement_snapshot(&mut state,Some(&first.token)).is_err());
        for _ in 0..2 {assert_eq!(handoff_owner(&mut state,"fact",&h.path,Some(&h.sha256)).unwrap(),("successor".into(),true));}
        assert!(handoff_owner(&mut state,"fact",&docs[1].relative,Some(&h.sha256)).is_err());
        assert!(handoff_owner(&mut state,"fact",&h.path,Some("forged")).is_err());
        current_document(&mut state,"successor").unwrap().revision+=1;
        assert!(handoff_owner(&mut state,"fact",&h.path,Some(&h.sha256)).is_err());
    }
    #[test]
    fn workspace_six_file_owners_aliases_and_cross_document_authority() {
        let (_root,host,docs)=workspace_fixture();
        let mut state=host.inner.lock().unwrap();
        assert_eq!(state.content_documents.len(),6);
        for doc in &docs {
            assert_eq!(state.content_documents[&file_key(&doc.relative)].token,doc.token);
            assert_eq!(discovered_path(&state,&doc.relative).unwrap(),doc.relative);
            if cfg!(windows) {assert_eq!(discovered_path(&state,&doc.relative.to_uppercase().replace('/',"\\")).unwrap(),doc.relative);}
        }
        assert_eq!(owner_collision(&state,&docs[1].relative,Some(&docs[0].token)).unwrap_err().code,"DOCUMENT_OPEN");
        assert!(owner_collision(&state,&docs[1].relative,Some(&docs[1].token)).is_ok());
        current_document(&mut state,&docs[1].token).unwrap().review.as_mut().unwrap().token="other-review".into();drop(state);
        assert_eq!(admit_apply(&host,&docs[0].token,"other-review",true,||{}).err().unwrap().code,"REVIEW_REQUIRED");
        let (op,_,snapshot)=begin_validation(&host,&docs[0].token).unwrap();
        advance_document(&host,&docs[1].token).unwrap();
        install_validation(&op,&snapshot,None,None).unwrap();
        assert_eq!(session_doc(&host,&docs[1].token).unwrap().1.revision,1);
    }
    #[test]
    fn workspace_close_reopen_rejects_old_results_without_touching_other_owners() {
        let (_root,host,docs)=workspace_fixture();
        let (op,_,snapshot)=begin_validation(&host,&docs[0].token).unwrap();
        remove_document(&host,&docs[0].token).unwrap();
        assert!(install_validation(&op,&snapshot,None,None).is_err());
        assert!(!install_disk(&op,&snapshot,&Ok(json!({"changed":true}))).unwrap());
        assert_eq!(host.inner.lock().unwrap().busy,Some(op.id));
        let mut reopened=snapshot.clone();reopened.token="new-instance".into();
        host.inner.lock().unwrap().content_documents.insert(file_key(&reopened.relative),reopened.clone());
        assert!(check_replacement(&mut host.inner.lock().unwrap(),Some(&snapshot)).is_err());
        assert!(begin_validation(&host,&docs[1].token).is_err());drop(op);
        assert!(session_doc(&host,&snapshot.token).is_err());
        assert!(session_doc(&host,&reopened.token).is_ok());
        for doc in &docs[1..] {assert_eq!(session_doc(&host,&doc.token).unwrap().1.original,doc.original);}
    }
    #[test]
    fn workspace_sweep_shares_stamp_refuses_overlap_and_includes_legacy() {
        let (root,host,docs)=workspace_fixture();
        let stamp=input_stamp(root.path()).unwrap();
        {let mut state=host.inner.lock().unwrap();
            for doc in state.content_documents.values_mut(){doc.evidence_inputs=Some(stamp.clone());}
            let mut legacy=docs[0].clone();legacy.token="legacy".into();state.document=Some(legacy);
        }
        let op=Operation::begin(&host).unwrap();let mut scans=0;
        let result=sweep_disk(&op,None,|r|{scans+=1;assert_eq!(Operation::begin(&host).err().unwrap().code,"BUSY");input_stamp(r)}).unwrap();
        assert_eq!(scans,1);assert_eq!(result["dependency_scans"],1);assert_eq!(result["documents"].as_array().unwrap().len(),7);
        drop(op);
        fs::write(root.path().join(&docs[1].relative),b"external edit").unwrap();
        let op=Operation::begin(&host).unwrap();
        let result=sweep_disk(&op,None,input_stamp).unwrap();
        let rows=result["documents"].as_array().unwrap();
        assert_eq!(rows.iter().filter(|r|r["disk"]["changed"]==true).count(),1);
        assert_eq!(rows.iter().find(|r|r["disk"]["changed"]==true).unwrap()["token"],docs[1].token);
        drop(op);
        let (validation,_,current)=begin_validation(&host,&docs[0].token).unwrap();
        install_validation(&validation,&current,None,docs[0].review.clone()).unwrap();drop(validation);
        let (reserved,_,_,_)=admit_apply(&host,&docs[0].token,"reviewed",true,||{}).unwrap();
        assert_eq!(remove_document(&host,&docs[1].token).unwrap_err().code,"BUSY");
        assert_eq!(Operation::begin(&host).err().unwrap().code,"BUSY");
        drop(reserved);
    }
    #[test]
    fn workspace_old_sweep_cannot_revoke_newer_validation_or_replaced_instance() {
        let (_root,host,docs)=workspace_fixture();
        let op=Operation::begin(&host).unwrap();let snapshot=docs[0].clone();
        advance_document(&host,&snapshot.token).unwrap();
        assert!(!install_disk(&op,&snapshot,&Ok(json!({"dependencies_changed":true}))).unwrap());
        let state=host.inner.lock().unwrap();let current=&state.content_documents[&file_key(&snapshot.relative)];
        assert_eq!(current.attempt,snapshot.attempt+1);drop(state);
        host.cancel(false).unwrap();
        assert_eq!(install_disk(&op,&snapshot,&Ok(json!({"changed":true}))).unwrap_err().code,"CANCELLED");
    }
    #[test]
    fn workspace_failed_or_cancelled_project_change_restores_connection_and_owners() {
        for cancelled in [false,true] {
            let (root,host,docs)=workspace_fixture();let other=tempfile::tempdir().unwrap();
            let operation=Operation::begin(&host).unwrap();
            {let mut state=host.inner.lock().unwrap();
                let previous=ProjectConnection{root:state.root.take(),ready:state.ready,
                    discovered:std::mem::take(&mut state.discovered),families:std::mem::take(&mut state.discovered_families)};
                state.pending_project=Some((operation.id,previous));state.root=Some(other.path().into());state.ready=false;
            }
            if cancelled {host.cancel(false).unwrap();}
            drop(operation);
            let state=host.inner.lock().unwrap();assert_eq!(state.root.as_deref(),Some(root.path()));assert!(state.ready);assert!(state.pending_project.is_none());
            assert_eq!(state.content_documents.len(),6);drop(state);
            for doc in docs {assert_eq!(session_doc(&host,&doc.token).unwrap().1.original,doc.original);}
        }
    }
    fn family_result(doc: &Document, id: &str, operations: Value) -> Value {
        json!({"route":format!("{id}_definition"),"source_asset":doc.relative,"source_sha256":hash(&doc.original),"semantic_verified":true,
            "family":{"id":id,"contract":"compatible-domain-contract","compatible":true,"descriptor_sha256":"a".repeat(64),
                "descriptor":{"vocabulary":"resonance-controls-1","schema":{"$schema":"https://json-schema.org/draft/2020-12/schema"},
                    "policy":{"root":content_root(&doc.relative).unwrap(),"identity":"id","operations":operations}}}})
    }
    #[test]
    fn registered_policy_binds_identity_descriptor_source_and_operations() {
        let (_,mut doc,_) = fixture();
        for (id,path) in [("item","roguelike/data/items/components/sample.json"),("recipe","roguelike/data/recipes/sample.json"),("text","roguelike/data/texts/lab/sample.json")] {
            doc.relative = path.into();
            let result = family_result(&doc,id,if id == "item" {json!(["edit","variant"])} else {json!(["variant"])});
            doc.family = FamilyPolicy::from_result(&result,&doc.relative);
            assert!(doc.family.is_some()); assert!(family_evidence(&doc,&result,true));
            assert_eq!(family_evidence(&doc,&result,false),id == "item");
            for pointer in ["/family/id","/family/contract","/family/descriptor_sha256","/family/descriptor/vocabulary","/family/descriptor/policy/root","/family/descriptor/policy/identity","/source_asset","/source_sha256","/semantic_verified"] {
                let mut altered=result.clone(); *altered.pointer_mut(pointer).unwrap()=json!("forged");
                assert!(!family_evidence(&doc,&altered,true),"{pointer}");
            }
            let mut altered=result.clone(); altered["family"]["descriptor"]["policy"]["operations"]=json!(["execute"]);
            assert!(FamilyPolicy::from_result(&altered,&doc.relative).is_none());
            altered=result.clone(); altered["family"]["compatible"]=json!(false);
            assert!(FamilyPolicy::from_result(&altered,&doc.relative).is_none());
        }
    }
    #[test]
    fn registered_text_confinement_cancellation_and_resource_freshness() {
        for path in ["roguelike/data/texts/text_item_map.json", "roguelike/data/texts/lab/text_item_map.json", "roguelike/data/texts/lab/TEXT_ITEM_MAP.json", "roguelike/data/texts/../x.json", "roguelike/data/texts/lab/x.json/evil", "roguelike/data/texts/CON.json"] {
            assert!(content_root(path).is_none(),"{path}");
        }
        let (root,host,item,review)=lifecycle_fixture(false);
        let mut text=item.clone();text.token="text-token".into();text.relative="roguelike/data/texts/lab/source.json".into();
        text.family=FamilyPolicy::from_result(&family_result(&text,"text",json!(["variant"])),&text.relative);
        let mut recipe=item.clone();recipe.token="recipe-token".into();recipe.relative="roguelike/data/recipes/sample.json".into();
        {let mut state=host.inner.lock().unwrap();state.content_documents.insert(file_key(&text.relative),text.clone());state.content_documents.insert(file_key(&recipe.relative),recipe.clone());}
        let (operation,_,snapshot)=begin_validation(&host,&text.token).unwrap();
        host.cancel(false).unwrap();
        assert!(install_validation(&operation,&snapshot,None,Some(review)).is_err());
        assert_eq!(session_doc(&host,&item.token).unwrap().1.original,item.original);
        assert_eq!(session_doc(&host,&recipe.token).unwrap().1.original,recipe.original);
        assert!(session_doc(&host,&text.token).unwrap().1.review.is_none());
        let assets=root.path().join("roguelike/assets/ui");fs::create_dir_all(&assets).unwrap();
        let before=input_stamp(root.path()).unwrap();fs::write(assets.join("panel.png"),b"frame").unwrap();
        assert_ne!(input_stamp(root.path()).unwrap(),before);
    }
    #[test]
    fn registered_replacement_cannot_address_new_document_with_old_token() {
        let (root,host,mut doc,review)=lifecycle_fixture(false);
        doc.token="replacement".into();
        {host.inner.lock().unwrap().content_documents.insert(file_key(&doc.relative),doc.clone());}
        assert!(begin_validation(&host,"trusted").is_err());
        assert!(admit_apply(&host,"trusted",&review.token,true,||{}).is_err());
        assert!(session_doc(&host,"replacement").is_ok());
        assert_eq!(fs::read(root.path().join(doc.relative)).unwrap(),doc.original);
    }
    #[test]
    fn w4d_invalidation_before_reservation_rejects_snapshot() {
        for submap in [false,true] {
            let (root,host,doc,_) = lifecycle_fixture(submap);
            let (paused,resume) = (Arc::new(std::sync::Barrier::new(2)),Arc::new(std::sync::Barrier::new(2)));
            let other=host.clone(); let p=paused.clone(); let r=resume.clone();
            let task=std::thread::spawn(move || admit_apply(&other,"trusted","reviewed",true,||{p.wait();r.wait();}).is_err());
            paused.wait();advance_document(&host,"trusted").unwrap();resume.wait();
            assert!(task.join().unwrap(),"revoked snapshot admitted");
            assert_eq!(fs::read(root.path().join(doc.relative)).unwrap(),doc.original);
        }
    }
    #[test]
    fn w4d_cancel_after_worker_before_install_rejects_result() {
        for submap in [false,true] {
            let (_,host,_,review)=lifecycle_fixture(submap);
            let (operation,_,doc)=begin_validation(&host,"trusted").unwrap();
            host.cancel(false).unwrap();
            assert!(install_validation(&operation,&doc,None,Some(review)).is_err(),"cancelled completion installed review");
        }
    }
    #[test]
    fn w4d_failed_replacement_cannot_restore_old_completion() {
        for submap in [false,true] {
            let (_,host,_,review)=lifecycle_fixture(submap);
            let (operation,_,doc)=begin_validation(&host,"trusted").unwrap();
            revoke_review(&host,"trusted");
            assert!(destination(&doc,"{}",Some("bad/id")).is_err());
            assert!(install_validation(&operation,&doc,None,Some(review)).is_err(),"old completion restored revoked review");
        }
    }
    fn lifecycle_fixture(submap: bool) -> (tempfile::TempDir, Host, Document, Review) {
        let (root, mut doc, mut review) = fixture();
        doc.relative = if submap { G17_EXAMPLE } else { "roguelike/data/items/components/sample.json" }.into();
        let path = root.path().join(&doc.relative);
        fs::create_dir_all(path.parent().unwrap()).unwrap(); fs::write(path, &doc.original).unwrap();
        review.variant = true;
        review.destination = if submap { "roguelike/data/layouts/variant.json" } else { "roguelike/data/items/components/variant.json" }.into();
        fs::create_dir_all(root.path().join(&review.destination).parent().unwrap()).unwrap();
        doc.review = Some(review.clone());
        if !submap { doc.family = FamilyPolicy::from_result(&family_result(&doc,"item",json!(["edit","variant"])),&doc.relative); }
        let host = Host::default();
        { let mut state = host.inner.lock().unwrap(); state.root = Some(root.path().into()); state.ready = true;
          if submap { state.document = Some(doc.clone()); } else { state.content_documents.insert(file_key(&doc.relative), doc.clone()); } }
        (root, host, doc, review)
    }
    #[test]
    fn w4d_live_admission_rejects_edit_replacement_and_project_switch() {
        for submap in [false, true] {
            for boundary in ["edit", "replace", "close", "switch", "cancel"] {
                let (root, host, doc, review) = lifecycle_fixture(submap);
                let other_root = tempfile::tempdir().unwrap();
                // Hold an obsolete local snapshot, then pause the real admission helper.
                let snapshot = session_doc(&host, &doc.token).unwrap().1;
                let result = admit_apply(&host, &snapshot.token, &review.token, true, || {
                    match boundary {
                        "edit" => advance_document(&host, &doc.token).unwrap(),
                        "replace" => { let mut state = host.inner.lock().unwrap(); current_document(&mut state, &doc.token).unwrap().token = "replacement".into(); }
                        "close" | "switch" => { host.cancel(true).unwrap(); if boundary == "switch" { host.inner.lock().unwrap().root = Some(other_root.path().into()); } }
                        _ => { host.cancel(false).unwrap(); }
                    }
                });
                assert!(result.is_err(), "{submap}/{boundary}");
                assert_eq!(fs::read(root.path().join(&doc.relative)).unwrap(), doc.original);
                assert!(!root.path().join(&review.destination).exists());
                assert_eq!(fs::read_dir(other_root.path()).unwrap().count(), 0);
                if boundary == "edit" || boundary == "cancel" {
                    let (operation, _, current) = begin_validation(&host, &doc.token).unwrap();
                    install_validation(&operation, &current, None, Some(review.clone())).unwrap(); drop(operation);
                    let (_transaction, _, _, _) = admit_apply(&host, &doc.token, &review.token, true, || {}).unwrap();
                }
            }
        }
    }
    #[test]
    fn w4d_late_completion_and_cleanup_cannot_touch_new_owner() {
        for submap in [false, true] {
            let (_root, host, doc, review) = lifecycle_fixture(submap);
            let (old, _, snapshot) = begin_validation(&host, &doc.token).unwrap();
            // An in-flight replacement is rejected, without changing attempt identity.
            assert_eq!(begin_validation(&host, &doc.token).err().unwrap().code, "BUSY");
            assert_eq!(session_doc(&host, &doc.token).unwrap().1.attempt, snapshot.attempt);
            host.cancel(false).unwrap();
            let (new, _, current) = begin_validation(&host, &doc.token).unwrap();
            let mut newest = review.clone(); newest.token = "new-review".into();
            install_validation(&new, &current, None, Some(newest)).unwrap();
            assert_eq!(install_validation(&old, &snapshot, Some("obsolete".into()), Some(review)).unwrap_err().code, "CANCELLED");
            drop(old);
            let state = host.inner.lock().unwrap(); assert_eq!(state.busy, Some(new.id)); drop(state);
            let current = session_doc(&host, &doc.token).unwrap().1;
            assert_eq!(current.review.unwrap().token, "new-review"); assert!(current.evidence_inputs.is_none());
            drop(new); assert!(host.inner.lock().unwrap().busy.is_none());
        }
    }
    #[test]
    fn w4d_failed_accepted_replacement_and_edit_revoke_attempt() {
        for submap in [false, true] {
            let (_root, host, doc, review) = lifecycle_fixture(submap);
            let (old, _, snapshot) = begin_validation(&host, &doc.token).unwrap();
            advance_document(&host, &doc.token).unwrap();
            assert_eq!(install_validation(&old, &snapshot, None, Some(review.clone())).unwrap_err().code, "DRAFT_CHANGED");
            host.cancel(false).unwrap();
            let (replacement, _, current) = begin_validation(&host, &doc.token).unwrap();
            assert!(destination(&current, "{}", Some("bad/id")).is_err()); drop(replacement);
            assert!(install_validation(&old, &snapshot, None, Some(review.clone())).is_err()); drop(old);
            assert!(session_doc(&host, &doc.token).unwrap().1.review.is_none());
            assert_eq!(admit_apply(&host, &doc.token, &review.token, true, || {}).err().unwrap().code, "REVIEW_REQUIRED");
            assert_eq!(session_doc(&host, &doc.token).unwrap().1.original, doc.original);
        }
    }
    #[test]
    fn w4d_reserved_apply_consumes_once_and_refuses_conflicts() {
        for submap in [false, true] {
            let (root, host, doc, review) = lifecycle_fixture(submap);
            let (transaction, selected, snapshot, reviewed) = admit_apply(&host, &doc.token, &review.token, true, || {}).unwrap();
            assert_eq!(host.cancel(false).unwrap_err().code, "BUSY");
            assert_eq!(host.cancel(true).unwrap_err().code, "BUSY");
            assert_eq!(advance_document(&host, &doc.token).unwrap_err().code, "BUSY");
            assert_eq!(begin_validation(&host, &doc.token).err().unwrap().code, "BUSY");
            assert_eq!(Operation::begin(&host).err().unwrap().code, "BUSY");
            assert_eq!(admit_apply(&host, &doc.token, &review.token, true, || {}).err().unwrap().code, "BUSY");
            assert_eq!(session_doc(&host, &doc.token).unwrap().1.revision, doc.revision);
            publish(&selected, &snapshot, &reviewed, Fault::None).unwrap(); drop(transaction);
            assert_eq!(admit_apply(&host, &doc.token, &review.token, true, || {}).err().unwrap().code, "REVIEW_REQUIRED");
            assert_eq!(fs::read(root.path().join(review.destination)).unwrap(), reviewed.draft.as_bytes());
            assert_eq!(fs::read(root.path().join(doc.relative)).unwrap(), doc.original);
        }
    }
    #[test]
    fn w4d_failed_transaction_releases_owner_without_reusing_review() {
        for submap in [false, true] {
            for fault in [Fault::BeforeStage, Fault::AfterStage, Fault::BeforeReplace] {
                let (root, host, doc, review) = lifecycle_fixture(submap);
                let (transaction, selected, snapshot, reviewed) = admit_apply(&host, &doc.token, &review.token, true, || {}).unwrap();
                assert!(publish(&selected, &snapshot, &reviewed, fault).is_err()); drop(transaction);
                assert!(!host.inner.lock().unwrap().applying); assert!(host.inner.lock().unwrap().busy.is_none());
                assert!(!root.path().join(&review.destination).exists());
                assert_eq!(admit_apply(&host, &doc.token, &review.token, true, || {}).err().unwrap().code, "REVIEW_REQUIRED");
                let (next, _, current) = begin_validation(&host, &doc.token).unwrap();
                install_validation(&next, &current, None, Some(review)).unwrap();
                assert_eq!(session_doc(&host, &doc.token).unwrap().1.original, doc.original);
            }
        }
    }
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
            family: None,
            evidence_inputs: None,
            revision: 0,
            attempt: 0,
            inspection: Value::Null,
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
    fn submap_example_variant_only_and_interrupted_publication() {
        let (root, mut doc, mut review) = fixture();
        doc.relative = G17_EXAMPLE.into();
        let source = root.path().join(G17_EXAMPLE);
        fs::create_dir_all(source.parent().unwrap()).unwrap(); fs::write(&source, &doc.original).unwrap();
        fs::create_dir_all(root.path().join("roguelike/data/layouts")).unwrap();
        assert_eq!(destination(&doc, "{\"id\":\"new_room\"}", Some("new_room")).unwrap(), ("roguelike/data/layouts/new_room.json".into(), true));
        assert_eq!(publish(root.path(), &doc, &review, Fault::None).unwrap_err().code, "LAYOUT_VARIANT_REQUIRED");
        review.destination = "roguelike/data/layouts/new_room.json".into(); review.variant = true;
        for fault in [Fault::BeforeStage,Fault::AfterStage,Fault::BeforeReplace] {
            assert!(publish(root.path(), &doc, &review, fault).is_err());
            assert_eq!(fs::read(&source).unwrap(), doc.original);
            assert_eq!(fs::read_dir(root.path().join("roguelike/data/layouts")).unwrap().count(),0);
        }
        publish(root.path(), &doc, &review, Fault::None).unwrap();
        assert_eq!(fs::read(root.path().join(&review.destination)).unwrap(), review.draft.as_bytes());
        assert_eq!(publish(root.path(), &doc, &review, Fault::None).unwrap_err().code,"VARIANT_EXISTS");
        assert_eq!(fs::read(&source).unwrap(),doc.original);
        for path in ["roguelike/data/layouts/a.json:ads","roguelike/data/layouts/nul.json","roguelike/data/layouts/../a.json","roguelike/data/layouts/nested/a.json","roguelike/saves/a.json","roguelike/docs/examples/new.json"] {assert!(relative_content(path).is_err());}
        doc.writable=false;
        assert_eq!(destination(&doc,"{\"id\":\"promoted\"}",Some("promoted")).unwrap_err().code,"READ_ONLY_LAYOUT");
    }
    #[test]
    fn draft_revision_and_sidecar_changes_revoke_evidence() {
        let (root, mut doc, review)=fixture();
        doc.review=Some(review);let host=Host::default();
        {let mut state=host.inner.lock().unwrap();state.root=Some(root.path().to_path_buf());state.document=Some(doc);}
        advance_document(&host,"trusted").unwrap();
        let current=session_doc(&host,"trusted").unwrap().1;
        assert_eq!(current.revision,1);assert!(current.review.is_none());
        assert!(advance_document(&host,"forged").is_err());
        let before=input_stamp(root.path()).unwrap();
        let sidecar=root.path().join("roguelike/docs/examples/g17_authored_creature_room.access.json");
        fs::create_dir_all(sidecar.parent().unwrap()).unwrap();fs::write(&sidecar,b"{}").unwrap();
        assert_ne!(input_stamp(root.path()).unwrap(),before);
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
            for (token, slot) in [("structure", &mut state.document), ("pool", &mut state.pool_document)] {
                let mut other = doc.clone(); other.token = token.into(); *slot = Some(other);
            }
            state.creature_document = Some(doc.clone());
        }
        assert!(session_doc(&host, &doc.token).is_ok());
        { let mut state = host.inner.lock().unwrap(); for key in ["item", "recipe"] {
            let mut d = doc.clone(); d.token = key.into(); d.relative = format!("roguelike/data/{key}s/sample.json"); state.content_documents.insert(file_key(&d.relative), d);
        }}
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
            let mut a=recipe.clone(); a.token="item".into(); a.relative="roguelike/data/items/components/sample.json".into(); state.content_documents.insert(file_key(&a.relative),a);
            state.content_documents.insert(file_key(&recipe.relative),recipe.clone());
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
            state.document = Some(structure); state.pool_document = Some(pool); state.content_documents.insert(file_key(&item.relative), item);
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
