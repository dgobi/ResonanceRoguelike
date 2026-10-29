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
    ("roguelike/data/entities/", "roguelike/data/entities/creatures/", &[]),
    ("roguelike/data/items/", "roguelike/data/items/", &[]),
    ("roguelike/data/recipes/", "roguelike/data/recipes/", &[]),
    ("roguelike/data/texts/", "roguelike/data/texts/", &["text_item_map.json"]),
];
pub const TYPOGRAPHY: &str = "roguelike/data/display/typography.json";
pub const ASSIGNMENT: &str = "roguelike/data/generation/authored_submap_selection.json";
pub fn item_authoring_path(source:&str)->bool {
    let p:Vec<_>=source.split('/').collect();
    p.len()>=5 && p[..3]==["roguelike","data","items"]
        && (["components","butchery","consumables","weapons","armor","shields"].contains(&p[3]) || (p.len()>=6 && p[3]=="equipment" && p[4]=="satchel"))
        && p[4..p.len()-1].iter().all(|s|valid_id(s)) && valid_filename(p[p.len()-1])
        && !p[p.len()-1].eq_ignore_ascii_case("empty_water_skin.json")
}
pub fn content_root(source: &str) -> Option<&'static str> {
    if source == TYPOGRAPHY { return Some(TYPOGRAPHY); }
    if source == ASSIGNMENT { return Some(ASSIGNMENT); }
    if is_layout(source) || source == G17_EXAMPLE { return Some("roguelike/data/layouts/"); }
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
            || d["production_route"] != route || digest.len() != 64 || !digest.bytes().all(|b| b.is_ascii_hexdigit())
            || d["vocabulary"] != "resonance-controls-1" || d["schema"]["$schema"] != "https://json-schema.org/draft/2020-12/schema"
            || d["policy"]["identity"] != "id" || operations.is_empty()
            || operations.iter().any(|op| op != "edit" && op != "variant")
            || content_root(source) != Some(root)
            || (source == TYPOGRAPHY && (id != "typography" || operations != ["edit"]))
            || (source == ASSIGNMENT && (id != "assignment" || route != "assignment_definition" || contract != "authored-submap-selection-1" || operations != ["edit"]))
        { return None; }
        let effective = f["effective_operations"].as_array()?.iter().map(|v|v.as_str().map(str::to_owned)).collect::<Option<Vec<_>>>()?;
        if effective.iter().any(|op| !operations.contains(op))
            || (source.starts_with("roguelike/data/items/") && (id!="item" || route!="item_definition" || (!effective.is_empty() && !item_authoring_path(source))))
            || (is_submap(source) && (id != "room" || route != "authored_submap"))
            || (is_creature(source) && (id != "creature" || root != "roguelike/data/entities/creatures/")) { return None; }
        Some(Self { id:id.into(), route:route.into(), contract:contract.into(), descriptor:d.clone(), digest:digest.into(), root:root.into(), operations:effective })
    }
}
fn family_evidence(doc: &Document, result: &Value, variant: bool) -> bool {
    let Some(policy) = &doc.family else { return content_root(&doc.relative).is_none(); };
    let Some(current) = FamilyPolicy::from_result(result, &doc.relative) else { return false; };
    current.id == policy.id && current.contract == policy.contract && current.digest == policy.digest
        && current.descriptor == policy.descriptor && current.route == policy.route && current.operations == policy.operations
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
    accepted: Option<recovery::Record>,
    edit_sequence: u64,
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
    acknowledged: bool,
}

/// Launch admission uses accepted host intent and the saved baseline, never
/// renderer cleanliness or an authoring review token.
pub fn room_test_source(host:&Host, token:&str) -> Result<(PathBuf,String,Vec<u8>),Failure> {
    let mut state=host.inner.lock().unwrap();
    if state.applying || state.closing || state.pending_project.is_some() || !state.ready {return Err(busy_failure());}
    let root=state.root.clone().ok_or_else(unknown_document)?;
    if state.handoffs.values().any(|h| !h.acknowledged && (h.source==token || h.replacement.as_deref()==Some(token))) {
        return Err(failure("ROOM_HANDOFF","Publication reopen is unresolved.","Complete verified reopen before testing the saved room."));
    }
    let doc=current_document(&mut state,token).ok_or_else(unknown_document)?;
    if !is_layout(&doc.relative) || doc.family.as_ref().is_none_or(|f|f.id!="room" || f.route!="authored_submap" || f.contract!="authored-room-2" || !f.operations.iter().any(|op|op=="edit")) || !doc.writable {
        return Err(failure("ROOM_INELIGIBLE","Only an eligible saved ordinary room can run.","Save the template as an ordinary room variant; select its reopened document."));
    }
    if doc.accepted.as_ref().is_some_and(|r|r.draft.as_bytes()!=doc.original || r.variant || r.published.is_some()) {
        return Err(failure("ROOM_DIRTY","The target room has an unsaved draft or unresolved publication.","Save and reopen, or deliberately discard/reconcile this room draft. Other parked drafts may stay open."));
    }
    let bytes=read_source(&checked_target(&root,&doc.relative,false)?)?;
    if bytes!=doc.original {return Err(conflict());}
    Ok((root,doc.relative.clone(),bytes))
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
fn recovery_owner(state:&mut Session,token:&str,handoff:Option<&str>)->Result<String,Failure>{
    if current_document(state,token).is_some(){return Ok(token.into());}
    let id=handoff.ok_or_else(unknown_document)?;
    let h=state.handoffs.get(id).cloned().filter(|h|h.source==token).ok_or_else(unknown_document)?;
    handoff_owner(state,id,&h.path,Some(&h.sha256)).map(|(token,_)|token)
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
pub fn variant_directory(source:&str)->&str {
    if source==G17_EXAMPLE { "roguelike/data/layouts" } else { source.rsplit_once('/').unwrap().0 }
}
fn dependency_bound(s: &str) -> bool { content_root(s).is_some() || is_creature(s) || is_layout(s) || s == G17_EXAMPLE }
fn relative_content(s: &str) -> Result<PathBuf, Failure> {
    if is_pool(s) || content_root(s).is_some() || is_creature(s) || is_layout(s) || s == G17_EXAMPLE { Ok(PathBuf::from(s)) } else { relative_building(s) }
}
pub(super) fn no_link(path: &Path) -> Result<(), Failure> {
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
        .chain(state.content_documents.values())
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
    for doc in state.document.iter_mut().chain(state.pool_document.iter_mut()).chain(state.content_documents.values_mut()) { revoke(doc); }
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
fn accept_edit(host:&Host, token:&str, sequence:u64, draft:String, variant:bool, variant_id:String)->Result<u64,Failure> {
    let mut state=host.inner.lock().unwrap();
    if state.applying || state.closing{return Err(busy_failure());}
    if draft.len()>MAX_DRAFT || variant_id.len()>128{return Err(recovery::error("Draft or variant ID exceeds the recovery bound."));}
    let root=state.root.clone().ok_or_else(unknown_document)?;
    let doc=current_document(&mut state,token).ok_or_else(unknown_document)?;
    let family=doc.family.as_ref().filter(|_|doc.writable).ok_or_else(||recovery::error("Only eligible registered documents have durable drafts."))?;
    if !draft_intent_allowed(family,variant) || (doc.relative==TYPOGRAPHY || doc.relative==ASSIGNMENT) && !variant_id.is_empty(){
        return Err(recovery::error("This family is edit-only; recovery cannot retain a variant target."));
    }
    if sequence<=doc.edit_sequence || sequence>9_007_199_254_740_990{return Err(recovery::error("Obsolete or invalid edit acknowledgement refused."));}
    let mut record=doc.accepted.clone().unwrap_or_else(||recovery::Record {
        version:recovery::VERSION,id:uuid::Uuid::new_v4().to_string(),project:root,source:doc.relative.clone(),
        family:family.id.clone(),contract:family.contract.clone(),descriptor_sha256:family.digest.clone(),
        source_sha256:hash(&doc.original),baseline:String::from_utf8(doc.original.clone()).unwrap(),draft:String::new(),
        variant:false,variant_id:String::new(),target:doc.relative.clone(),generation:0,captured_ms:0,published:None,
    });
    record.generation+=1;record.captured_ms=recovery::now();record.draft=draft;record.variant=variant;
    record.target=recovery::intent_target(&doc.relative,variant,&variant_id);record.variant_id=variant_id;
    record.validate()?;let generation=record.generation;
    doc.accepted=Some(record);doc.edit_sequence=sequence;doc.revision+=1;revoke(doc);Ok(generation)
}
pub(super) fn flush_registered(app:&tauri::AppHandle,host:&Host)->Result<(),Failure>{
    let mut state=host.inner.lock().unwrap();if state.applying{return Err(busy_failure());}
    for doc in state.content_documents.values(){if let Some(record)=&doc.accepted{recovery::with_store(app,host,|store|store.write(record))?;}}
    state.closing=true;
    Ok(())
}
#[tauri::command]
pub fn edit_document(host:tauri::State<'_,Host>,token:String,sequence:u64,draft:String,variant:bool,variant_id:String)->Result<u64,Failure>{
    accept_edit(&host,&token,sequence,draft,variant,variant_id)
}
#[tauri::command]
pub fn checkpoint_document(app:tauri::AppHandle,host:tauri::State<'_,Host>,token:String,handoff_id:Option<String>)->Result<Value,Failure>{
    let mut state=host.inner.lock().unwrap();
    let token=recovery_owner(&mut state,&token,handoff_id.as_deref())?;
    let doc=current_document(&mut state,&token).ok_or_else(unknown_document)?;
    let Some(record)=&doc.accepted else{return Ok(json!({"generation":0,"token":token}));};
    let started=Instant::now();recovery::with_store(&app,&host,|store|store.write(record))?;
    Ok(json!({"generation":record.generation,"key":record.key(),"token":token,"elapsed_ms":started.elapsed().as_secs_f64()*1000.0}))
}
#[tauri::command]
pub fn discard_document_draft(app:tauri::AppHandle,host:tauri::State<'_,Host>,token:String,handoff_id:Option<String>)->Result<String,Failure>{
    let mut state=host.inner.lock().unwrap();if state.applying{return Err(busy_failure());}
    let token=recovery_owner(&mut state,&token,handoff_id.as_deref())?;
    let doc=current_document(&mut state,&token).ok_or_else(unknown_document)?;
    if let Some(record)=&doc.accepted {recovery::with_store(&app,&host,|store|store.retire(&record.key(),record.generation))?;}
    doc.accepted=None;doc.revision+=1;revoke(doc);Ok(token)
}
fn recovery_status(record:&recovery::Record)->(String,Option<String>){
    let result=(||{
        let root=canonical_root(&record.project)?;
        if recovery::project_key(&root)!=recovery::project_key(&record.project){return Err(recovery::error("Project identity changed."));}
        let bytes=read_source(&checked_target(&root,&record.source,false)?)?;
        Ok(String::from_utf8(bytes).unwrap())
    })();
    match result {
        Ok(raw) if hash(raw.as_bytes())==record.source_sha256 =>("Source unchanged; fresh compatibility inspection required".into(),Some(raw)),
        Ok(raw)=>("Source changed; retained draft and current disk text available for comparison".into(),Some(raw)),
        Err(e)=>(format!("Source/project unavailable: {}",e.message),None),
    }
}
#[tauri::command]
pub fn list_recovery(app:tauri::AppHandle,host:tauri::State<'_,Host>)->Result<Value,Failure>{
    // No worker or compatibility handshake. This is a trusted-storage inventory.
    let (records,notices)=recovery::with_store(&app,&host,|store|store.list())?;
    let records:Vec<_>=records.into_iter().map(|r|{
        let (status,_)=recovery_status(&r);
        json!({"key":r.key(),"project":r.project,"source":r.source,"family":r.family,"generation":r.generation,"captured_ms":r.captured_ms,"status":status,"published":r.published})
    }).collect();Ok(json!({"records":records,"notices":notices}))
}
#[tauri::command]
pub fn inspect_recovery(app:tauri::AppHandle,host:tauri::State<'_,Host>,key:String)->Result<Value,Failure>{
    let record=recovery::with_store(&app,&host,|store|store.read(&key))?;
    let (status,disk)=recovery_status(&record);Ok(json!({"key":key,"record":record,"status":status,"disk":disk}))
}
#[tauri::command]
pub fn discard_recovery(app:tauri::AppHandle,host:tauri::State<'_,Host>,key:String,generation:u64)->Result<(),Failure>{
    let state=host.inner.lock().unwrap();
    require_unowned_recovery(&state,&key)?;
    recovery::with_store(&app,&host,|store|store.acquired(&key,generation,|store,_|store.retire(&key,generation)))
}
fn require_unowned_recovery(state:&Session,key:&str)->Result<(),Failure>{
    if let Some(doc)=state.content_documents.values().find(|d|d.accepted.as_ref().is_some_and(|r|r.key()==key)) {
        return Err(recovery::error(format!("Recovery belongs to open document {}. Use that owner's verified reopen or close choices; its newer work is preserved.",doc.relative)));
    }
    Ok(())
}
#[tauri::command]
pub fn restore_recovery(app:tauri::AppHandle,host:tauri::State<'_,Host>,token:String,key:String,generation:u64)->Result<Value,Failure>{
    let mut state=host.inner.lock().unwrap();if state.applying || !state.ready{return Err(busy_failure());}
    require_unowned_recovery(&state,&key)?;
    let root=state.root.clone().ok_or_else(unknown_document)?;
    let doc=current_document(&mut state,&token).ok_or_else(unknown_document)?;
    recovery::with_store(&app,&host,|store|restore_claimed(store,&root,doc,&key,generation))
}
fn restore_claimed(store:&mut recovery::Store,root:&Path,doc:&mut Document,key:&str,generation:u64)->Result<Value,Failure>{
    store.acquired(key,generation,|store,mut record|{
        check_restore(root,doc,&record)?;
        infer_completed_write(root,&mut record);store.write(&record)?;
        doc.accepted=Some(record.clone());doc.edit_sequence=0;doc.revision+=1;revoke(doc);
        Ok(json!({"key":key,"generation":record.generation,"draft":record.draft,"variant":record.variant,"variant_id":record.variant_id,"published":record.published}))
    })
}
fn infer_completed_write(root:&Path,record:&mut recovery::Record){
    // A write may precede persistence of its fact. Matching bytes permit only
    // deliberate read reconciliation, never another write or restored review.
    if record.published.is_none() && record.target!=record.source {
        if let Ok(bytes)=checked_target(root,&record.target,false).and_then(|p|read_source(&p)) {
            if hash(&bytes)==hash(record.draft.as_bytes()) {
                record.generation+=1;record.captured_ms=recovery::now();
                record.published=Some(recovery::Published {path:record.target.clone(),after_sha256:hash(&bytes),generation:record.generation});
            }
        }
    }
}
fn check_restore(root:&Path,doc:&Document,record:&recovery::Record)->Result<(),Failure>{
    if doc.revision!=0 || doc.accepted.is_some(){return Err(recovery::error("An open draft already owns this file. Focus it and resolve that draft explicitly."));}
    let family=doc.family.as_ref().filter(|_|doc.writable).ok_or_else(||recovery::error("Current source/contract is not editable. Recovery remains inspectable and copyable."))?;
    if recovery::project_key(root)!=recovery::project_key(&record.project) || file_key(&doc.relative)!=file_key(&record.source)
        || family.id!=record.family || !draft_intent_allowed(family,record.variant)
        || hash(&doc.original)!=record.source_sha256
        || read_source(&checked_target(root,&doc.relative,false)?)?!=doc.original {
        return Err(recovery::error("Source or project changed. Keep and compare both versions; no baseline was adopted."));
    }
    Ok(())
}
// Accepted unfinished intent is not a publication request. In particular a
// variant-only source has useful exact drafts before a target is chosen.
// Explicit variant intent still requires that operation on the original source.
fn draft_intent_allowed(family:&FamilyPolicy,variant:bool)->bool {
    !family.operations.is_empty() && (!variant || family.operations.iter().any(|op|op=="variant"))
}
#[tauri::command]
pub fn reconcile_recovery(app:tauri::AppHandle,host:tauri::State<'_,Host>,token:String,key:String,generation:u64)->Result<(),Failure>{
    let mut state=host.inner.lock().unwrap();if state.applying || !state.ready{return Err(busy_failure());}
    recovery::with_store(&app,&host,|store|reconcile_claimed(store,&mut state,&token,&key,generation))
}
fn reconcile_claimed(store:&mut recovery::Store,state:&mut Session,token:&str,key:&str,generation:u64)->Result<(),Failure>{
    require_unowned_recovery(state,key)?;
    let root=state.root.clone().ok_or_else(unknown_document)?;
    let doc=current_document(state,token).ok_or_else(unknown_document)?;
    store.acquired(key,generation,|store,record|{
    let (path,expected)=record.published.as_ref().map(|p|(p.path.as_str(),p.after_sha256.clone())).unwrap_or((&record.target,hash(record.draft.as_bytes())));
    if recovery::project_key(&root)!=recovery::project_key(&record.project) || file_key(&doc.relative)!=file_key(path)
        || !doc.writable || doc.family.as_ref().is_none_or(|f|f.id!=record.family)
        || doc.revision!=0 || doc.accepted.is_some() || record.generation!=generation
        || hash(&doc.original)!=expected || hash(record.draft.as_bytes())!=expected || record.target!=path
        || record.published.as_ref().is_some_and(|p|p.generation!=record.generation)
        || read_source(&checked_target(&root,path,false)?)?!=doc.original {
        return Err(recovery::error("Saved target does not cover this exact recovery generation. Newer or conflicting work remains available to inspect/copy."));
    }
    store.retire(key,generation)?;revoke(doc);Ok(())
    })
}
#[tauri::command]
pub fn acknowledge_reopen(app:tauri::AppHandle,host:tauri::State<'_,Host>,handoff_id:String)->Result<(),Failure>{
    let mut state=host.inner.lock().unwrap();
    let h=state.handoffs.get(&handoff_id).cloned().ok_or_else(unknown_document)?;
    let (token,done)=handoff_owner(&mut state,&handoff_id,&h.path,Some(&h.sha256))?;
    if !done{return Err(recovery::error("Host reopen is not complete."));}
    let root=state.root.clone().ok_or_else(unknown_document)?;
    if hash(&read_source(&checked_target(&root,&h.path,false)?)?)!=h.sha256{return Err(conflict());}
    let doc=current_document(&mut state,&token).ok_or_else(unknown_document)?;
    if let Some(r)=&doc.accepted {
        if r.published.as_ref().is_none_or(|p|p.generation!=r.generation) || hash(r.draft.as_bytes())!=h.sha256{return Err(recovery::error("Newer unsaved generation retained."));}
        recovery::with_store(&app,&host,|store|store.retire(&r.key(),r.generation))?;
        doc.accepted=None;
    }
    state.handoffs.get_mut(&handoff_id).unwrap().acknowledged=true;
    Ok(())
}
fn current_document<'a>(state: &'a mut Session, token: &str) -> Option<&'a mut Document> {
    state.document.as_mut().into_iter().chain(state.pool_document.as_mut()).chain(state.content_documents.values_mut()).find(|d| d.token == token)
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
fn remove_document_with(host: &Host, token: &str, checkpoint:impl FnOnce(&Document)->Result<(),Failure>) -> Result<(), Failure> {
    let mut state = host.inner.lock().unwrap();
    if state.applying { return Err(busy_failure()); }
    let key = state.content_documents.iter().find(|(_, d)| d.token == token).map(|(k, _)| k.clone()).ok_or_else(unknown_document)?;
    checkpoint(&state.content_documents[&key])?;
    let removed=state.content_documents.remove(&key).unwrap();
    if let Some(record)=removed.accepted {if let Some(store)=host.recovery.lock().unwrap().as_mut(){store.release(&record.key());}}
    // Do not kill a worker or release resources belonging to another document.
    Ok(())
}
#[cfg(test)]
fn remove_document(host:&Host,token:&str)->Result<(),Failure>{remove_document_with(host,token,|_|Ok(()))}
#[tauri::command]
pub fn close_document(app:tauri::AppHandle,host: tauri::State<'_, Host>, token: String, handoff_id:Option<String>) -> Result<(), Failure> {
    let token=recovery_owner(&mut host.inner.lock().unwrap(),&token,handoff_id.as_deref())?;
    remove_document_with(&host,&token,|doc|{if let Some(record)=&doc.accepted{recovery::with_store(&app,&host,|store|store.write(record))?;}Ok(())})
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
        let recovery_app=app.clone();
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
            family.as_ref().is_some_and(|f| !f.operations.is_empty() && (asset.starts_with(&f.root) || asset==G17_EXAMPLE)) && response["result"]["editable"] == true
        } else { !is_submap(&asset) };
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
            accepted: previous.as_ref().and_then(|p| if handoff_id.is_some() {p.accepted.clone()} else {None}),
            edit_sequence: 0,
        };
        if registered {
            if let Some(previous) = previous {
                if handoff_id.is_none() {if let Some(record)=previous.accepted {recovery::with_store(&recovery_app,&host,|store|{store.write(&record)?;store.release(&record.key());Ok(())})?;}}
                state.content_documents.retain(|_, d| d.token != previous.token);
            }
            state.content_documents.insert(file_key(&document.relative), document);
            if let Some(id)=handoff_id { state.handoffs.get_mut(&id).ok_or_else(unknown_document)?.replacement=Some(token); }
        }
        else {
            let slot = if is_pool(&document.relative) { &mut state.pool_document } else { &mut state.document };
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
    if !doc.writable && variant_id.is_none() && draft.as_bytes() == doc.original
        && doc.family.as_ref().is_some_and(|f| f.id == "creature")
        && doc.inspection["family"]["context"]["records"][0]["capability"]["constructible"] == true {
        return Ok((doc.relative.clone(), false));
    }
    if !doc.writable {
        return Err(failure(if is_submap(&doc.relative) || doc.relative == G17_EXAMPLE { "READ_ONLY_LAYOUT" } else if is_creature(&doc.relative) { "READ_ONLY_CREATURE" } else if is_recipe(&doc.relative) { "READ_ONLY_RECIPE" } else { "READ_ONLY_ITEM" }, "This source is outside its supported authoring capability.", "Inspect unsupported or ambiguous sources read-only."));
    }
    if doc.relative.starts_with("roguelike/data/items/") && !item_authoring_path(&doc.relative) {
        return Err(failure("READ_ONLY_ITEM","Item writing is confined to supported item routes.","Choose a supported original item source."));
    }
    if draft.len() > MAX_DRAFT {
        return Err(io_error("Draft exceeds 1 MiB."));
    }
    // Syntax/schema verdict comes from Python; this is only the publication identity rule.
    let raw: Value =
        serde_json::from_str(draft.trim_start_matches('\u{feff}')).unwrap_or(Value::Null);
    if let Some(family)=&doc.family {
        // Variant-only families still permit same-source semantic inspection;
        // family_evidence denies a publication review for that edit operation.
        if variant_id.is_some() && !family.operations.iter().any(|op|op=="variant") {
            return Err(failure("OPERATION_POLICY","This family does not support the requested publication operation.","Use the family's supported edit or variant action."));
        }
    }
    if doc.relative==TYPOGRAPHY && raw.is_object() && (raw["id"]!="game_typography" || raw["version"].as_u64()!=Some(1)) {
        return Err(failure("IDENTITY_CHANGE","Typography requires fixed id game_typography and integer version 1.","Restore the fixed identity/version."));
    }
    if doc.relative==ASSIGNMENT && raw.is_object() && (raw["id"]!="authored_submap_selection" || raw["version"].as_u64()!=Some(1)) {
        return Err(failure("IDENTITY_CHANGE","Assignment requires fixed id authored_submap_selection and integer version 1.","Restore the fixed identity/version."));
    }
    if let Some(id) = variant_id {
        if doc.relative.starts_with("roguelike/data/items/") && !item_authoring_path(&format!("{}/{}.json",variant_directory(&doc.relative),id)) {
            return Err(failure("READ_ONLY_ITEM","Reserved or unsupported item destination.","Choose a unique ordinary item ID."));
        }
        if !valid_id(id) || raw["id"].as_str() != Some(id) || doc.id.as_ref().is_some_and(|original|original.eq_ignore_ascii_case(id)) {
            return Err(failure(
                "VARIANT_ID",
                "A new variant requires a different safe ID matching the draft's id field.",
                "Use letters, digits, underscores or hyphens and update the draft ID.",
            ));
        }
        Ok((
            format!("{}/{}.json", variant_directory(&doc.relative), id),
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
        if doc.relative==ASSIGNMENT && preview_only && (draft.as_bytes()!=doc.original || doc.accepted.as_ref().is_some_and(|r|r.draft.as_bytes()!=doc.original || r.variant)) {
            return Err(failure("ASSIGNMENT_UNSAVED","Preview uses saved assignments and saved dependencies.","Apply and byte-check reopen the profile first; parked drafts are excluded."));
        }
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
                    current.id == policy.id && current.contract == policy.contract && current.digest == policy.digest && current.descriptor == policy.descriptor && current.operations == policy.operations)
                {
                    return Err(failure("CONTRACT_CHANGED", "The opened content descriptor is incompatible or changed.", "Retain the exact draft, then reopen its source to obtain the current contract."));
                }
            }
        }
        let mut review = None;
        if response["ok"] == true
            && !preview_only
            && doc.writable
            && response["result"]["valid"] == true
            && response["result"]["draft_sha256"] == hash(draft.as_bytes())
            && family_evidence(&doc, &response["result"], variant)
            && (!is_submap(&doc.relative) || (response["result"]["layout_contract"] == "authored-room-2" && response["result"]["population_verified"] == true && response["result"]["placement_verified"] == true && response["result"]["preview"]["passed"] == true && response["result"]["route"] == "authored_submap"))
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
    if is_recipe(&doc.relative) && doc.family.as_ref().is_none_or(|f| f.id != "recipe" || f.root != "roguelike/data/recipes/") {
        return Err(failure("OPERATION_POLICY", "Recipe publication requires its registered source policy.", "Reopen the supported recipe."));
    }
    if doc.relative==TYPOGRAPHY || doc.relative==ASSIGNMENT {
        let (target,variant)=destination(doc,&review.draft,review.variant.then_some("forbidden"))?;
        if target!=review.destination || variant {return Err(failure("OPERATION_POLICY","This profile has one fixed target.","Review the canonical profile."));}
    }
    if is_submap(&doc.relative) && ((!review.variant && (doc.relative==G17_EXAMPLE || doc.family.is_none())) || !is_layout(&review.destination)) {
        return Err(failure("LAYOUT_VARIANT_REQUIRED", "Layout publication requires a new ID/file in layouts/.", "Review a unique layout variant."));
    }
    if let Some(family) = &doc.family {
        if !doc.writable || !family.operations.iter().any(|op| op == if review.variant { "variant" } else { "edit" }) {
            return Err(failure("OPERATION_POLICY", "Original source does not grant this publication operation.", "Reopen and use its supported operations."));
        }
        {
            let raw:Value=serde_json::from_str(review.draft.trim_start_matches('\u{feff}')).map_err(io_error)?;
            let (target,variant)=destination(doc,&review.draft,if review.variant {raw["id"].as_str()} else {None})?;
            if target!=review.destination || variant!=review.variant {return Err(conflict());}
        }
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
        let recovery_app=app.clone();
        let mut result = (|| {
            if let Some(record)=&doc.accepted {recovery::with_store(&recovery_app,&host,|store|store.write(record))?;}
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
                || response["result"]["contract"] != "g2-3" || response["result"]["worker_version"] != env!("CARGO_PKG_VERSION")
                || (is_submap(&doc.relative) && (response["result"]["layout_contract"] != "authored-room-2" || response["result"]["population_verified"] != true || response["result"]["placement_verified"] != true || response["result"]["preview"]["passed"] != true))
                || !family_evidence(&doc, &response["result"], review.variant)
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
                      path:review.destination.clone(),sha256:hash(review.draft.as_bytes()),replacement:None,acknowledged:false});
                receipt["handoff_id"]=json!(id);
                if let Some(current)=current_document(&mut state,&doc.token) {
                    if let Some(record)=&mut current.accepted {
                        record.generation+=1;record.captured_ms=recovery::now();
                        record.published=Some(recovery::Published{path:review.destination.clone(),after_sha256:hash(review.draft.as_bytes()),generation:record.generation});
                        if let Err(e)=recovery::with_store(&recovery_app,&host,|store|store.write(record)) {receipt["recovery_error"]=json!(e);}
                    }
                }
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
        let docs: Vec<_> = state.document.iter().chain(state.pool_document.iter()).chain(state.content_documents.values())
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
    flush_registered(window.app_handle(),&host)?;
    host.games.stop(true)?;
    host.cancel(true)?;
    window.destroy().map_err(io_error)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn w5g_room_operation_freeze_recovery_mapping_and_host_destinations() {
        let (root,host,mut doc,mut review)=lifecycle_fixture(true);
        doc.family=FamilyPolicy::from_result(&family_result(&doc,"room",json!(["variant"])),&doc.relative);
        assert!(doc.family.is_some());
        {let mut state=host.inner.lock().unwrap();state.document=None;state.content_documents.insert(file_key(&doc.relative),doc.clone());}
        let invalid="\u{feff}{\r\n \"room\": [\"λ\",";
        accept_edit(&host,&doc.token,1,invalid.into(),false,"".into()).unwrap();
        let unfinished=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();
        assert_eq!(unfinished.target,G17_EXAMPLE);assert!(!unfinished.variant);assert!(unfinished.published.is_none());
        let storage=tempfile::tempdir().unwrap();let mut store=recovery::Store::new(storage.path().into()).unwrap();store.write(&unfinished).unwrap();store.release_all();
        let mut fresh=doc.clone();fresh.review=None;restore_claimed(&mut store,root.path(),&mut fresh,&unfinished.key(),unfinished.generation).unwrap();
        assert_eq!(fresh.accepted.unwrap().draft,invalid);
        accept_edit(&host,&doc.token,2,invalid.into(),true,"".into()).unwrap(); // incomplete deliberate ID is still recoverable
        accept_edit(&host,&doc.token,3,"{\"id\":\"new_room\"}".into(),true,"new_room".into()).unwrap();
        let selected=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();assert_eq!(selected.target,"roguelike/data/layouts/new_room.json");
        assert_eq!(recovery::intent_target(G17_EXAMPLE,true,"new_room"),destination(&doc,"{\"id\":\"new_room\"}",Some("new_room")).unwrap().0);
        review.variant=false;review.destination=G17_EXAMPLE.into();assert!(publish(root.path(),&doc,&review,Fault::None).is_err());
        let mut bad=selected;bad.published=Some(recovery::Published{path:G17_EXAMPLE.into(),after_sha256:"a".repeat(64),generation:bad.generation});assert!(bad.validate().is_err());
        for forbidden in ["roguelike/data/layouts/nested/new_room.json","roguelike/docs/examples/other.json","roguelike/docs/examples/new_room.json"] {assert!(checked_target(root.path(),forbidden,true).is_err());}
        let mut saved=doc;saved.relative="roguelike/data/layouts/sample.json".into();fs::write(root.path().join(&saved.relative),&saved.original).unwrap();
        let result=family_result(&saved,"room",json!(["edit","variant"]));saved.family=FamilyPolicy::from_result(&result,&saved.relative);
        review.variant=false;review.destination=saved.relative.clone();review.draft="{\"id\":\"sample\",\"unknown\":[[1,2]],\"description\":\"same ID\"}".into();
        publish(root.path(),&saved,&review,Fault::None).unwrap();assert_eq!(fs::read(root.path().join(&saved.relative)).unwrap(),review.draft.as_bytes());
        let mut narrowed=result;narrowed["family"]["effective_operations"]=json!(["variant"]);assert!(!family_evidence(&saved,&narrowed,false));
        assert!(destination(&saved,"{\"id\":\"SAMPLE\"}",Some("SAMPLE")).is_err());
    }
    fn actual_family_result(op:&str,asset:&str,draft:Option<&str>,source:Option<&str>)->Value {
        use std::io::Write;
        let workbench=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
        let root=workbench.parent().unwrap();
        let python=workbench.join("worker/runtime/python.exe");
        let mut command=std::process::Command::new(python);
        command.args(["-I","-B"]).arg(workbench.join("worker/bridge.py")).arg("--root").arg(root)
            .stdin(std::process::Stdio::piped()).stdout(std::process::Stdio::piped()).stderr(std::process::Stdio::piped());
        #[cfg(windows)] {use std::os::windows::process::CommandExt;command.creation_flags(0x08000000);}
        let mut child=command.spawn().unwrap();
        let request=json!({"protocol":8,"id":"w5g-real-policy","op":op,"asset":asset,"draft":draft,"source_asset":source,"seed":20261027});
        child.stdin.take().unwrap().write_all(request.to_string().as_bytes()).unwrap();
        let output=child.wait_with_output().unwrap();
        let response:Value=serde_json::from_slice(&output.stdout).expect("actual worker JSON");
        assert_eq!(response["ok"],true,"{response} {}",String::from_utf8_lossy(&output.stderr));
        response["result"].clone()
    }
    #[test]
    fn registered_text_and_recipe_restore_unfinished_intent() {
        for (id,source) in [("text","roguelike/data/texts/lab/lab_note_primary_b.json"),("recipe","roguelike/data/recipes/bile_coating.json")] {
            let result=actual_family_result("inspect",source,None,None);
            let (root,mut doc,_)=fixture();doc.relative=source.into();doc.original=result["raw"].as_str().unwrap().as_bytes().to_vec();
            doc.id=result["id"].as_str().map(str::to_owned);doc.review=None;
            doc.family=FamilyPolicy::from_result(&result,source);
            assert_eq!(doc.family.as_ref().unwrap().id,id);
            assert_eq!(doc.family.as_ref().unwrap().operations,if id=="recipe" {vec!["edit","variant"]} else {vec!["variant"]});
            let path=root.path().join(source);fs::create_dir_all(path.parent().unwrap()).unwrap();fs::write(path,&doc.original).unwrap();
            let host=Host::default();{let mut state=host.inner.lock().unwrap();state.root=Some(root.path().into());state.ready=true;state.content_documents.insert(file_key(source),doc.clone());}
            for (sequence,text) in [(1,String::from_utf8(doc.original.clone()).unwrap()+"\r\n"),(2,"\u{feff}{\r\n \"unfinished\": [\"λ\",".into())] {
                accept_edit(&host,&doc.token,sequence,text.clone(),false,"".into()).unwrap();
                let record=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();
                assert!(!record.variant);assert_eq!(record.target,source);assert_eq!(record.variant_id,"");
                let storage=tempfile::tempdir().unwrap();let mut store=recovery::Store::new(storage.path().into()).unwrap();store.write(&record).unwrap();store.release_all();
                let mut restarted=recovery::Store::new(storage.path().into()).unwrap();let mut fresh=doc.clone();fresh.token="cold-owner".into();
                restore_claimed(&mut restarted,root.path(),&mut fresh,&record.key(),record.generation).unwrap();
                assert_eq!(fresh.accepted.as_ref().unwrap().draft,text);assert!(!fresh.accepted.as_ref().unwrap().variant);assert!(fresh.review.is_none());
                assert!(!family_evidence(&fresh,&result,false)); // recovery/inspection carries no validation authority
                let mut competitor=recovery::Store::new(storage.path().into()).unwrap();assert!(competitor.acquired(&record.key(),record.generation,|_,_|Ok(())).is_err());
            }
            let mut candidate:Value=serde_json::from_slice(&doc.original).unwrap();candidate["id"]=json!("w5g_repaired_variant");let draft=candidate.to_string();
            accept_edit(&host,&doc.token,3,draft.clone(),true,"w5g_repaired_variant".into()).unwrap();
            let (target,variant)=destination(&doc,&draft,Some("w5g_repaired_variant")).unwrap();assert!(variant);
            let validated=actual_family_result("preview_draft",&target,Some(&draft),Some(source));
            assert_eq!(validated["valid"],true,"{validated}");assert!(family_evidence(&doc,&validated,true));assert_eq!(family_evidence(&doc,&validated,false),id=="recipe");
        }
    }
    #[test]
    fn creature_original_operations_bind_review_recovery_and_publication() {
        let (root,host,old,mut review)=lifecycle_fixture(false);
        let mut doc=old.clone();doc.relative="roguelike/data/entities/creatures/sample.json".into();
        let source=root.path().join(&doc.relative);fs::create_dir_all(source.parent().unwrap()).unwrap();fs::write(&source,&doc.original).unwrap();
        let mut result=family_result(&doc,"creature",json!(["edit","variant"]));
        result["family"]["effective_operations"]=json!(["edit"]);
        doc.family=FamilyPolicy::from_result(&result,&doc.relative);assert!(doc.family.is_some());
        assert!(family_evidence(&doc,&result,false));assert!(!family_evidence(&doc,&result,true));
        let mut forged=result.clone();forged["family"]["effective_operations"]=json!(["edit","variant"]);
        assert!(!family_evidence(&doc,&forged,true));assert!(!family_evidence(&doc,&forged,false));
        assert!(destination(&doc,"{\"id\":\"variant\"}",Some("variant")).is_err());
        {let mut state=host.inner.lock().unwrap();state.content_documents.clear();state.content_documents.insert(file_key(&doc.relative),doc.clone());}
        assert!(accept_edit(&host,&doc.token,1,"clone".into(),true,"variant".into()).is_err());
        let exact="\u{feff}{\r\n \"unfinished\": [\"λ\",";
        accept_edit(&host,&doc.token,1,exact.into(),false,"".into()).unwrap();
        let record=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();
        let dir=tempfile::tempdir().unwrap();let mut store=recovery::Store::new(dir.path().into()).unwrap();
        store.write(&record).unwrap();store.release(&record.key());
        let mut fresh=doc.clone();restore_claimed(&mut store,root.path(),&mut fresh,&record.key(),record.generation).unwrap();
        assert_eq!(fresh.accepted.unwrap().draft,exact);assert!(fresh.review.is_none());store.release(&record.key());
        let mut bad=record.clone();bad.generation+=1;bad.variant=true;bad.variant_id="clone".into();bad.target=recovery::intent_target(&bad.source,true,"clone");
        store.write(&bad).unwrap();store.release(&bad.key());fresh=doc.clone();
        assert!(restore_claimed(&mut store,root.path(),&mut fresh,&bad.key(),bad.generation).is_err());
        assert_eq!(store.read(&bad.key()).unwrap().draft,exact);
        review.variant=true;review.destination=bad.target;review.draft="{\"id\":\"clone\"}".into();
        assert!(publish(root.path(),&doc,&review,Fault::None).is_err());assert_eq!(fs::read(&source).unwrap(),doc.original);
        for path in ["roguelike/data/entities/../outside.json","roguelike/data/entities/creatures/x.json:ads","roguelike/data/entities/creatures/nul.json","roguelike/saves/x.json"] {assert!(relative_content(path).is_err());}
        let mut bad=record;bad.family="item".into();assert!(bad.validate().is_err());
    }
    #[test]
    fn creature_readonly_construction_requires_exact_opened_bytes() {
        let (_,mut doc,_)=fixture();doc.relative="roguelike/data/entities/outside.json".into();doc.writable=false;
        let mut result=family_result(&doc,"creature",json!(["edit","variant"]));result["family"]["effective_operations"]=json!([]);
        result["family"]["context"]=json!({"records":[{"capability":{"constructible":true}}]});
        doc.family=FamilyPolicy::from_result(&result,&doc.relative);doc.inspection=result;
        let exact=String::from_utf8(doc.original.clone()).unwrap();assert!(destination(&doc,&exact,None).is_ok());
        assert!(destination(&doc,&(exact.clone()+" "),None).is_err());assert!(destination(&doc,&exact,Some("variant")).is_err());
    }
    #[test]
    fn typography_singleton_policy_recovery_and_freshness_are_host_enforced(){
        let (root,host,old,mut review)=lifecycle_fixture(false);
        let mut doc=old.clone();doc.relative=TYPOGRAPHY.into();doc.id=Some("game_typography".into());
        doc.original=b"{\"id\":\"game_typography\",\"version\":1}".to_vec();
        let family=doc.family.as_mut().unwrap();family.id="typography".into();family.route="typography_definition".into();family.root=TYPOGRAPHY.into();family.operations=vec!["edit".into()];
        let path=root.path().join(TYPOGRAPHY);fs::create_dir_all(path.parent().unwrap()).unwrap();fs::write(&path,&doc.original).unwrap();
        {let mut state=host.inner.lock().unwrap();state.content_documents.clear();state.content_documents.insert(file_key(TYPOGRAPHY),doc.clone());}
        assert_eq!(content_root(TYPOGRAPHY),Some(TYPOGRAPHY));
        for path in ["roguelike/data/display/other.json","roguelike/data/display/typography.JSON","roguelike/data/display/nested/typography.json","roguelike/assets/Fonts/typography.json"]{assert!(content_root(path).is_none());assert!(checked_target(root.path(),path,true).is_err());}
        let draft="{\"id\":\"game_typography\",\"version\":1,\"metadata\":true}";
        assert_eq!(destination(&doc,draft,None).unwrap(),(TYPOGRAPHY.into(),false));
        assert!(destination(&doc,draft,Some("other")).is_err());
        for invalid in ["{\"id\":\"other\",\"version\":1}","{\"id\":\"game_typography\",\"version\":2}","{\"id\":\"game_typography\",\"version\":true}"]{assert!(destination(&doc,invalid,None).is_err());}
        assert!(accept_edit(&host,&doc.token,1,draft.into(),true,"other".into()).is_err());
        assert!(accept_edit(&host,&doc.token,1,draft.into(),false,"other".into()).is_err());
        accept_edit(&host,&doc.token,1,"{invalid exact typography λ".into(),false,"".into()).unwrap();
        let record=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();assert_eq!(record.target,TYPOGRAPHY);
        let dir=tempfile::tempdir().unwrap();let mut store=recovery::Store::new(dir.path().into()).unwrap();store.write(&record).unwrap();
        let mut forged=record.clone();forged.target="roguelike/data/display/other.json".into();assert!(forged.validate().is_err());
        forged=record.clone();forged.variant=true;assert!(forged.validate().is_err());
        forged=record.clone();forged.family="item".into();assert!(forged.validate().is_err());
        store.release(&record.key());let mut restored=doc.clone();restore_claimed(&mut store,root.path(),&mut restored,&record.key(),record.generation).unwrap();assert!(restored.review.is_none());assert_eq!(restored.accepted.unwrap().draft,record.draft);
        review.destination="roguelike/data/items/components/elsewhere.json".into();review.variant=false;review.draft=draft.into();assert!(publish(root.path(),&doc,&review,Fault::None).is_err());assert_eq!(fs::read(&path).unwrap(),doc.original);
        let before=input_stamp(root.path()).unwrap();fs::write(&path,draft).unwrap();assert_ne!(input_stamp(root.path()).unwrap(),before);
        let fonts=root.path().join("roguelike/assets/Fonts");fs::create_dir_all(&fonts).unwrap();fs::write(fonts.join("selected.ttf"),b"selected font bytes").unwrap();let before=input_stamp(root.path()).unwrap();fs::write(fonts.join("selected.ttf"),b"changed bytes").unwrap();assert_ne!(input_stamp(root.path()).unwrap(),before);
    }
    #[test]
    fn assignment_fixed_file_recovery_identity_and_freshness_are_host_enforced(){
        let (root,host,old,mut review)=lifecycle_fixture(false);
        let mut doc=old.clone();doc.relative=ASSIGNMENT.into();doc.id=Some("authored_submap_selection".into());
        doc.original=b"{\"id\":\"authored_submap_selection\",\"version\":1}".to_vec();
        let family=doc.family.as_mut().unwrap();family.id="assignment".into();family.route="assignment_definition".into();family.root=ASSIGNMENT.into();family.operations=vec!["edit".into()];
        let path=root.path().join(ASSIGNMENT);fs::create_dir_all(path.parent().unwrap()).unwrap();fs::write(&path,&doc.original).unwrap();
        {let mut state=host.inner.lock().unwrap();state.content_documents.clear();state.content_documents.insert(file_key(ASSIGNMENT),doc.clone());}
        assert_eq!(content_root(ASSIGNMENT),Some(ASSIGNMENT));
        for path in ["roguelike/data/generation/other.json","roguelike/data/generation/authored_submap_selection.JSON","roguelike/data/generation/nested/authored_submap_selection.json","roguelike/assets/Fonts/typography.json"]{assert!(content_root(path).is_none());assert!(checked_target(root.path(),path,true).is_err());}
        let draft="{\"id\":\"authored_submap_selection\",\"version\":1,\"metadata\":true}";
        assert_eq!(destination(&doc,draft,None).unwrap(),(ASSIGNMENT.into(),false));
        assert!(destination(&doc,draft,Some("other")).is_err());
        for invalid in ["{\"id\":\"other\",\"version\":1}","{\"id\":\"authored_submap_selection\",\"version\":2}","{\"id\":\"authored_submap_selection\",\"version\":true}"]{assert!(destination(&doc,invalid,None).is_err());}
        assert!(accept_edit(&host,&doc.token,1,draft.into(),true,"other".into()).is_err());
        assert!(accept_edit(&host,&doc.token,1,draft.into(),false,"other".into()).is_err());
        accept_edit(&host,&doc.token,1,"{invalid exact assignment λ".into(),false,"".into()).unwrap();
        let record=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();assert_eq!(record.target,ASSIGNMENT);
        let dir=tempfile::tempdir().unwrap();let mut store=recovery::Store::new(dir.path().into()).unwrap();store.write(&record).unwrap();
        let mut forged=record.clone();forged.target="roguelike/data/generation/other.json".into();assert!(forged.validate().is_err());
        forged=record.clone();forged.variant=true;assert!(forged.validate().is_err());
        forged=record.clone();forged.family="item".into();assert!(forged.validate().is_err());
        store.release(&record.key());let mut restored=doc.clone();restore_claimed(&mut store,root.path(),&mut restored,&record.key(),record.generation).unwrap();assert!(restored.review.is_none());assert_eq!(restored.accepted.unwrap().draft,record.draft);
        review.destination="roguelike/data/items/components/elsewhere.json".into();review.variant=false;review.draft=draft.into();assert!(publish(root.path(),&doc,&review,Fault::None).is_err());assert_eq!(fs::read(&path).unwrap(),doc.original);
        let before=input_stamp(root.path()).unwrap();fs::write(&path,draft).unwrap();assert_ne!(input_stamp(root.path()).unwrap(),before);
        let fonts=root.path().join("roguelike/assets/Fonts");fs::create_dir_all(&fonts).unwrap();fs::write(fonts.join("selected.ttf"),b"selected font bytes").unwrap();let before=input_stamp(root.path()).unwrap();fs::write(fonts.join("selected.ttf"),b"changed bytes").unwrap();assert_ne!(input_stamp(root.path()).unwrap(),before);
    }
    #[test]
    fn recovery_acquisition_refuses_deleted_or_advanced_inspection_and_cleans_failed_claim(){
        let (root,host,doc,_)=lifecycle_fixture(false);
        accept_edit(&host,&doc.token,1,"exact unfinished".into(),true,"variant".into()).unwrap();
        let record=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();let key=record.key();
        let dir=tempfile::tempdir().unwrap();let mut a=recovery::Store::new(dir.path().into()).unwrap();let mut b=recovery::Store::new(dir.path().into()).unwrap();
        a.write(&record).unwrap();a.release(&key);let inspected=a.read(&key).unwrap();
        let mut advanced=record.clone();advanced.generation+=1;b.write(&advanced).unwrap();b.release(&key);
        let mut fresh=doc.clone();assert!(restore_claimed(&mut a,root.path(),&mut fresh,&key,inspected.generation).is_err());
        b.claim(&key).unwrap();b.retire(&key,advanced.generation).unwrap();
        assert!(restore_claimed(&mut a,root.path(),&mut fresh,&key,inspected.generation).is_err());assert!(a.read(&key).is_err());assert!(fresh.accepted.is_none());
        // A separate fresh key: failed source check releases only the new claim.
        let mut next=record;next.id=uuid::Uuid::new_v4().to_string();let key=next.key();b.write(&next).unwrap();b.release(&key);
        fresh.revision=1;assert!(restore_claimed(&mut a,root.path(),&mut fresh,&key,next.generation).is_err());b.claim(&key).unwrap();b.release(&key);
        a.claim(&key).unwrap();assert!(restore_claimed(&mut a,root.path(),&mut fresh,&key,next.generation).is_err());assert!(b.claim(&key).is_err());
    }
    #[test]
    fn saved_variant_reconciliation_preserves_live_source_owner_and_next_checkpoint(){
        let (root,host,doc,mut review)=lifecycle_fixture(false);
        review.draft="{\"id\":\"variant\",\"description\":\"saved\"}".into();
        accept_edit(&host,&doc.token,1,review.draft.clone(),true,"variant".into()).unwrap();
        publish(root.path(),&doc,&review,Fault::None).unwrap();
        let dir=tempfile::tempdir().unwrap();let mut store=recovery::Store::new(dir.path().into()).unwrap();
        let mut record=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();infer_completed_write(root.path(),&mut record);store.write(&record).unwrap();
        {let mut state=host.inner.lock().unwrap();current_document(&mut state,&doc.token).unwrap().accepted=Some(record.clone());
          let mut target=doc.clone();target.token="saved-target".into();target.relative=record.target.clone();target.original=review.draft.as_bytes().to_vec();
          state.content_documents.insert(file_key(&target.relative),target);
          let error=reconcile_claimed(&mut store,&mut state,"saved-target",&record.key(),record.generation).unwrap_err();assert!(error.message.contains(&doc.relative));}
        accept_edit(&host,&doc.token,2,"newer exact draft".into(),true,"variant".into()).unwrap();
        let newer=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();store.write(&newer).unwrap();assert_eq!(store.read(&record.key()).unwrap(),newer);assert_eq!(newer.published,record.published);
    }
    #[test]
    fn reconcile_claimed_rechecks_inspected_generation_and_accepts_exact_unrecorded_write(){
        let (root,host,doc,mut review)=lifecycle_fixture(false);review.draft="{\"id\":\"variant\",\"description\":\"exact saved bytes\"}".into();
        accept_edit(&host,&doc.token,1,review.draft.clone(),true,"variant".into()).unwrap();let record=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();let key=record.key();
        publish(root.path(),&doc,&review,Fault::None).unwrap();let target=root.path().join(&review.destination);let before=fs::metadata(&target).unwrap().modified().unwrap();
        let dir=tempfile::tempdir().unwrap();let mut a=recovery::Store::new(dir.path().into()).unwrap();let mut b=recovery::Store::new(dir.path().into()).unwrap();a.write(&record).unwrap();a.release(&key);
        let mut state=host.inner.lock().unwrap();state.content_documents.clear();let mut saved=doc.clone();saved.token="saved".into();saved.relative=review.destination.clone();saved.original=review.draft.as_bytes().to_vec();state.content_documents.insert(file_key(&saved.relative),saved);
        let mut advanced=record.clone();advanced.generation+=1;b.write(&advanced).unwrap();b.release(&key);
        assert!(reconcile_claimed(&mut a,&mut state,"saved",&key,record.generation).is_err());b.claim(&key).unwrap();b.release(&key);
        assert_eq!(a.read(&key).unwrap(),advanced);assert!(advanced.published.is_none());
        reconcile_claimed(&mut a,&mut state,"saved",&key,advanced.generation).unwrap();assert!(a.read(&key).is_err());
        assert_eq!(fs::read(&target).unwrap(),review.draft.as_bytes());assert_eq!(fs::metadata(&target).unwrap().modified().unwrap(),before);
        assert!(reconcile_claimed(&mut b,&mut state,"saved",&key,advanced.generation).is_err());assert!(b.read(&key).is_err());
    }
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
    fn publication_before_fact_checkpoint_is_reconciled_as_read_only_evidence(){
        let (root,host,doc,mut review)=lifecycle_fixture(false);
        review.draft="{\"id\":\"variant\",\"unknown\":[[1,2]],\"description\":\"exact candidate λ\"}".into();
        accept_edit(&host,&doc.token,1,review.draft.clone(),true,"variant".into()).unwrap();
        let record=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();
        let storage=tempfile::tempdir().unwrap();recovery::Store::new(storage.path().into()).unwrap().write(&record).unwrap();
        let written=publish(root.path(),&doc,&review,Fault::None).unwrap();
        // Simulate exit before recording the successful write, then use the same
        // helper as restart restoration against the actual published target.
        drop(host);let store=recovery::Store::new(storage.path().into()).unwrap();let mut recovered=store.read(&record.key()).unwrap();assert!(recovered.published.is_none());
        let target=root.path().join(&review.destination);let bytes=fs::read(&target).unwrap();let modified=fs::metadata(&target).unwrap().modified().unwrap();
        infer_completed_write(root.path(),&mut recovered);
        assert_eq!(recovered.published.as_ref().unwrap().after_sha256,written["after_sha256"].as_str().unwrap());
        assert_eq!(recovered.published.as_ref().unwrap().generation,recovered.generation);
        assert_eq!(fs::read(&target).unwrap(),bytes);assert_eq!(fs::metadata(&target).unwrap().modified().unwrap(),modified);
        assert_eq!(store.read(&record.key()).unwrap().draft,review.draft);
        let mut ambiguous=record;fs::write(&target,b"different existing target").unwrap();infer_completed_write(root.path(),&mut ambiguous);
        assert!(ambiguous.published.is_none());assert_eq!(fs::read(&target).unwrap(),b"different existing target");
        assert_eq!(publish(root.path(),&doc,&review,Fault::None).unwrap_err().code,"VARIANT_EXISTS");
    }
    #[test]
    fn recovery_fresh_source_authority_rejects_changed_missing_unsupported_and_other_project(){
        let (root,host,doc,_)=lifecycle_fixture(false);
        accept_edit(&host,&doc.token,1,"invalid retained λ".into(),true,"new_variant".into()).unwrap();
        let record=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();
        let mut fresh=doc.clone();fresh.token="fresh-after-restart".into();fresh.review=None;
        assert!(check_restore(root.path(),&fresh,&record).is_ok());
        fresh.family.as_mut().unwrap().contract="new-supported-contract".into();
        assert!(check_restore(root.path(),&fresh,&record).is_ok()); // Fresh support, old evidence discarded.
        fresh.writable=false;assert!(check_restore(root.path(),&fresh,&record).is_err());fresh.writable=true;
        fresh.family=None;assert!(check_restore(root.path(),&fresh,&record).is_err());fresh.family=doc.family.clone();
        let other=tempfile::tempdir().unwrap();assert!(check_restore(other.path(),&fresh,&record).is_err());
        fresh.revision=1;assert!(check_restore(root.path(),&fresh,&record).is_err());fresh.revision=0;
        fs::write(root.path().join(&doc.relative),b"changed source {").unwrap();assert!(check_restore(root.path(),&fresh,&record).is_err());
        fs::remove_file(root.path().join(&doc.relative)).unwrap();assert!(check_restore(root.path(),&fresh,&record).is_err());
        assert_eq!(record.draft,"invalid retained λ");assert!(fresh.review.is_none());
    }
    #[test]
    fn accepted_recovery_state_rejects_busy_old_sequences_and_retains_exact_intent(){
        let (_root,host,doc,_)=lifecycle_fixture(false);
        let text="\u{feff}{\r\n\"metadata\": \"λ\\n\",\r\n\"invalid\": [";
        assert_eq!(accept_edit(&host,&doc.token,2,text.into(),true,"unfinished_".into()).unwrap(),1);
        let accepted=session_doc(&host,&doc.token).unwrap().1.accepted.unwrap();
        assert_eq!(accepted.draft,text);assert!(accepted.variant);assert_eq!(accepted.variant_id,"unfinished_");assert!(accepted.published.is_none());
        assert!(accept_edit(&host,&doc.token,1,"older".into(),false,"".into()).is_err());
        host.inner.lock().unwrap().applying=true;
        assert_eq!(accept_edit(&host,&doc.token,3,"BUSY optimistic sentinel".into(),false,"".into()).unwrap_err().code,"BUSY");
        host.inner.lock().unwrap().applying=false;
        assert_eq!(session_doc(&host,&doc.token).unwrap().1.accepted.unwrap(),accepted);
        let dir=tempfile::tempdir().unwrap();let mut store=recovery::Store::new(dir.path().into()).unwrap();store.write(&accepted).unwrap();
        let serialized=fs::read_to_string(dir.path().join(format!("{}.json",accepted.key()))).unwrap();
        for forbidden in ["document_token","review_token","writable","inspection","BUSY optimistic sentinel"]{assert!(!serialized.contains(forbidden));}
    }
    #[test]
    fn completed_handoff_rejects_newer_drafts_and_reacquires_only_its_successor() {
        let (_root,host,docs)=workspace_fixture();
        let first=&docs[0]; let mut state=host.inner.lock().unwrap();
        let h=Handoff {source:first.token.clone(),revision:first.revision,path:first.relative.clone(),sha256:hash(&first.original),replacement:None,acknowledged:false};
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
        json!({"route":if id=="room" {"authored_submap".into()} else {format!("{id}_definition")},"source_asset":doc.relative,"source_sha256":hash(&doc.original),"semantic_verified":true,
            "family":{"id":id,"contract":"compatible-domain-contract","compatible":true,"descriptor_sha256":"a".repeat(64),"effective_operations":operations,
                "descriptor":{"production_route":if id=="room" {"authored_submap".into()} else {format!("{id}_definition")},"vocabulary":"resonance-controls-1","schema":{"$schema":"https://json-schema.org/draft/2020-12/schema"},
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
        review.draft="{\"id\":\"variant\",\"unknown\":[[1,2]],\"description\":\"edited\"}".into();
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
    fn room_launch_admission_binds_saved_host_intent_and_completed_handoff(){
        let (root,host,mut doc,_)=lifecycle_fixture(false);
        doc.relative="roguelike/data/layouts/sample.json".into();
        let path=root.path().join(&doc.relative);fs::create_dir_all(path.parent().unwrap()).unwrap();fs::write(&path,&doc.original).unwrap();
        let mut result=family_result(&doc,"room",json!(["edit","variant"]));result["family"]["contract"]=json!("authored-room-2");
        doc.family=FamilyPolicy::from_result(&result,&doc.relative);
        {let mut state=host.inner.lock().unwrap();state.content_documents.clear();state.content_documents.insert(file_key(&doc.relative),doc.clone());}
        assert!(room_test_source(&host,&doc.token).is_ok());
        accept_edit(&host,&doc.token,1,"{unfinished".into(),false,String::new()).unwrap();
        assert_eq!(room_test_source(&host,&doc.token).unwrap_err().code,"ROOM_DIRTY");
        accept_edit(&host,&doc.token,2,String::from_utf8(doc.original.clone()).unwrap(),false,String::new()).unwrap();assert!(room_test_source(&host,&doc.token).is_ok());
        fs::write(&path,b"external").unwrap();assert_eq!(room_test_source(&host,&doc.token).unwrap_err().code,"EXTERNAL_MODIFICATION_CONFLICT");fs::write(&path,&doc.original).unwrap();
        {let mut state=host.inner.lock().unwrap();state.handoffs.insert("handoff".into(),Handoff{source:"old-owner".into(),revision:0,path:doc.relative.clone(),sha256:hash(&doc.original),replacement:Some(doc.token.clone()),acknowledged:false});}
        assert_eq!(room_test_source(&host,&doc.token).unwrap_err().code,"ROOM_HANDOFF");
        host.inner.lock().unwrap().handoffs.get_mut("handoff").unwrap().acknowledged=true;assert!(room_test_source(&host,&doc.token).is_ok());
        {let mut state=host.inner.lock().unwrap();current_document(&mut state,&doc.token).unwrap().relative=G17_EXAMPLE.into();}
        assert_eq!(room_test_source(&host,&doc.token).unwrap_err().code,"ROOM_INELIGIBLE");
        assert!(room_test_source(&host,"forged-token").is_err());
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
            accepted: None,
            edit_sequence: 0,
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
        assert_eq!(publish(root.path(),&recipe,&review,Fault::None).unwrap_err().code,"OPERATION_POLICY");
        recipe.family=FamilyPolicy::from_result(&family_result(&recipe,"recipe",json!(["edit","variant"])),&recipe.relative);
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
    fn supplies_routes_are_independent_of_worker_permissions_and_recovery() {
        let (root,mut doc,_) = fixture();
        for route in ["components","butchery","consumables","weapons","armor","shields","equipment/satchel"] {
            doc.relative=format!("roguelike/data/items/{route}/sample.json");doc.writable=true;
            assert!(item_authoring_path(&doc.relative));
            doc.family=FamilyPolicy::from_result(&family_result(&doc,"item",json!(["edit","variant"])),&doc.relative);
            assert!(doc.family.is_some());
            assert!(destination(&doc,r#"{"id":"sample"}"#,None).is_ok());
            assert!(destination(&doc,r#"{"id":"empty_water_skin"}"#,Some("empty_water_skin")).is_err());
            let record=recovery::Record{version:1,id:uuid::Uuid::new_v4().to_string(),project:root.path().into(),source:doc.relative.clone(),
                family:"item".into(),contract:"usable-supplies-1".into(),descriptor_sha256:"a".repeat(64),source_sha256:hash(&doc.original),
                baseline:String::from_utf8(doc.original.clone()).unwrap(),draft:"{invalid".into(),variant:false,variant_id:String::new(),target:doc.relative.clone(),generation:1,captured_ms:1,published:None};
            assert!(record.validate().is_ok());
        }
        for source in ["roguelike/data/items/equipment/other/sample.json","roguelike/data/items/tools/sample.json","roguelike/data/items/consumables/empty_water_skin.json"] {
            doc.relative=source.into();doc.writable=true;
            assert!(!item_authoring_path(source));
            assert!(FamilyPolicy::from_result(&family_result(&doc,"item",json!(["edit","variant"])),source).is_none());
            assert!(destination(&doc,r#"{"id":"sample"}"#,None).is_err());
        }
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
