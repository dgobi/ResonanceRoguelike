//! Auxiliary exact-source copies. No live tokens, reviews, diagnostics or permission.
use crate::{authoring::{hash, MAX_DRAFT}, failure, Failure};
use serde::{Deserialize, Serialize};
use std::{collections::{HashMap, HashSet}, fs::{self, File, OpenOptions}, io::Write, path::{Path, PathBuf}};
use tauri::Manager;

pub const VERSION: u32 = 1;
const MAX_RECORD: u64 = (MAX_DRAFT * 14) as u64; // JSON escaping of two 1 MiB strings.
pub fn error(message: impl ToString) -> Failure {
    failure("RECOVERY", message, "The in-memory draft and previous complete checkpoint are retained. Retry recovery save, or copy Source before discarding.")
}
pub fn now() -> u64 { std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_millis() as u64 }
pub fn project_key(root: &Path) -> String {
    let spelling=root.to_string_lossy().replace('\\', "/");
    hash(if cfg!(windows) {spelling.to_lowercase()} else {spelling}.as_bytes())
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Published {
    pub path: String,
    pub after_sha256: String,
    pub generation: u64,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Record {
    pub version: u32,
    pub id: String,
    pub project: PathBuf,
    pub source: String,
    pub family: String,
    pub contract: String,
    pub descriptor_sha256: String,
    pub source_sha256: String,
    pub baseline: String,
    pub draft: String,
    pub variant: bool,
    pub variant_id: String,
    pub target: String,
    pub generation: u64,
    pub captured_ms: u64,
    pub published: Option<Published>,
}
impl Record {
    pub fn key(&self) -> String { format!("{}/{}",project_key(&self.project),self.id) }
    pub fn validate(&self) -> Result<(), Failure> {
        if self.version != VERSION || uuid::Uuid::parse_str(&self.id).is_err() || !self.project.is_absolute()
            || self.project.to_string_lossy().len()>4096 || self.generation==0 || self.generation>9_007_199_254_740_990
            || self.baseline.len()>MAX_DRAFT || self.draft.len()>MAX_DRAFT || self.variant_id.len()>128
            || self.contract.len()>100 || self.contract.is_empty() || self.descriptor_sha256.len()!=64
            || !["item","recipe","text","typography","creature"].contains(&self.family.as_str())
            || ((self.family=="typography" || self.source==crate::authoring::TYPOGRAPHY) &&
                (self.family!="typography" || self.source!=crate::authoring::TYPOGRAPHY || self.variant || !self.variant_id.is_empty()
                 || self.target!=crate::authoring::TYPOGRAPHY || self.published.as_ref().is_some_and(|p|p.path!=crate::authoring::TYPOGRAPHY)))
            || ((self.family=="creature" || self.source.starts_with("roguelike/data/entities/")) &&
                (self.family!="creature" || !self.source.starts_with("roguelike/data/entities/creatures/")
                 || !self.target.starts_with("roguelike/data/entities/creatures/")
                 || self.published.as_ref().is_some_and(|p|!p.path.starts_with("roguelike/data/entities/creatures/"))))
            || crate::authoring::content_root(&self.source).is_none()
            || self.source_sha256 != hash(self.baseline.as_bytes())
            || self.target != intent_target(&self.source,self.variant,&self.variant_id)
            || self.published.as_ref().is_some_and(|p| crate::authoring::content_root(&p.path).is_none() || p.after_sha256.len()!=64 || p.generation>self.generation)
        { return Err(error("Malformed or unsupported recovery envelope; retained for inspection outside Workbench.")); }
        Ok(())
    }
}
pub fn intent_target(source: &str, variant: bool, id: &str) -> String {
    if variant {format!("{}/{}.json",source.rsplit_once('/').unwrap().0,id)} else {source.into()}
}
pub struct Store {
    root: PathBuf,
    claims: HashMap<String, File>,
    retired: HashSet<String>,
}
impl Store {
    pub fn new(root: PathBuf) -> Result<Self, Failure> {
        if !root.is_absolute() {return Err(error("Recovery storage must be absolute."));}
        fs::create_dir_all(&root).map_err(error)?;
        crate::authoring::no_link(&root)?;
        Ok(Self {root,claims:HashMap::new(),retired:HashSet::new()})
    }
    fn path(&self,key:&str,extension:&str)->Result<PathBuf,Failure> {
        let parts:Vec<_>=key.split('/').collect();
        if parts.len()!=2 || parts[0].len()!=64 || !parts[0].bytes().all(|b|b.is_ascii_hexdigit()) || uuid::Uuid::parse_str(parts[1]).is_err() {return Err(error("Unknown recovery identity."));}
        let dir=self.root.join(parts[0]);
        if dir.exists(){crate::authoring::no_link(&dir)?;}
        let path=dir.join(format!("{}.{extension}",parts[1]));
        if path.exists(){crate::authoring::no_link(&path)?;}
        Ok(path)
    }
    pub fn claim(&mut self,key:&str)->Result<(),Failure> {
        if self.retired.contains(key) {return Err(error("This recovery generation was retired."));}
        if self.claims.contains_key(key){return Ok(());}
        let path=self.path(key,"lock")?;
        fs::create_dir_all(path.parent().unwrap()).map_err(error)?;
        let lock=OpenOptions::new().read(true).write(true).create(true).truncate(false).open(path).map_err(error)?;
        lock.try_lock().map_err(|_|error("This draft is owned by another running Workbench instance. Keep it for later."))?;
        self.claims.insert(key.into(),lock); Ok(())
    }
    pub fn release(&mut self,key:&str){self.claims.remove(key);}
    // The authoritative read happens only under the process claim. A failed
    // request may release its own new claim, never one protecting a live owner.
    pub fn acquired<T>(&mut self,key:&str,generation:u64,action:impl FnOnce(&mut Self,Record)->Result<T,Failure>)->Result<T,Failure>{
        let owned=self.claims.contains_key(key);self.claim(key)?;
        let result=(||{
            let record=self.read(key)?;
            if record.generation!=generation{return Err(error("Recovery generation changed. Refresh the list."));}
            action(self,record)
        })();
        if result.is_err() && !owned{self.release(key);}
        result
    }
    pub fn release_all(&mut self){self.claims.clear();}
    pub fn read(&self,key:&str)->Result<Record,Failure> {
        let path=self.path(key,"json")?;
        if fs::metadata(&path).map_err(error)?.len()>MAX_RECORD{return Err(error("Recovery envelope exceeds its size bound."));}
        let record:Record=serde_json::from_slice(&fs::read(path).map_err(error)?).map_err(error)?;
        record.validate()?;
        if record.key()!=key{return Err(error("Recovery file and project identity disagree."));}
        Ok(record)
    }
    pub fn write(&mut self,record:&Record)->Result<(),Failure>{self.write_at_boundary(record,false)}
    fn write_at_boundary(&mut self,record:&Record,fail:bool)->Result<(),Failure> {
        record.validate()?;let key=record.key(); self.claim(&key)?;
        let path=self.path(&key,"json")?;
        if path.exists(){
            let previous=self.read(&key)?;
            if previous.generation>record.generation || previous.generation==record.generation && previous!=*record {return Err(error("Obsolete checkpoint refused."));}
            if previous==*record{return Ok(());}
        }
        let bytes=serde_json::to_vec(record).map_err(error)?;
        if bytes.len() as u64>MAX_RECORD{return Err(error("Recovery envelope exceeds its size bound."));}
        let mut stage=tempfile::NamedTempFile::new_in(path.parent().unwrap()).map_err(error)?;
        stage.write_all(&bytes).map_err(error)?;stage.as_file().sync_all().map_err(error)?;
        #[cfg(test)]
        if let Ok(ready)=std::env::var("W5D_CHILD_INTERRUPT") {
            fs::write(ready,b"complete stage; previous checkpoint not replaced").unwrap();
            loop{std::thread::sleep(std::time::Duration::from_millis(20));}
        }
        if fail{return Err(error("Injected interruption before checkpoint replacement."));}
        stage.persist(path).map_err(|e|error(e.error))?;
        Ok(())
    }
    pub fn retire(&mut self,key:&str,generation:u64)->Result<(),Failure> {
        if self.retired.contains(key){return Ok(());}
        self.claim(key)?;
        let path=self.path(key,"json")?;
        if path.exists(){
            if self.read(key)?.generation>generation{return Err(error("A newer checkpoint cannot be retired by this request."));}
            fs::remove_file(path).map_err(error)?;
        }
        self.retired.insert(key.into());self.release(key);Ok(())
    }
    pub fn list(&self)->Result<(Vec<Record>,Vec<String>),Failure> {
        let mut records=Vec::new();let mut notices=Vec::new();let mut count=0;
        for directory in fs::read_dir(&self.root).map_err(error)? {
            let directory=directory.map_err(error)?;
            if !directory.file_type().map_err(error)?.is_dir(){continue;}
            let partition=directory.file_name().to_string_lossy().into_owned();
            if partition.len()!=64 || !partition.bytes().all(|b|b.is_ascii_hexdigit()){continue;}
            crate::authoring::no_link(&directory.path())?;
            for entry in fs::read_dir(directory.path()).map_err(error)? {
                let entry=entry.map_err(error)?;let path=entry.path();
                if path.extension().is_none_or(|s|s!="json"){continue;}
                count+=1;if count>1024{notices.push("Only the first 1024 records are listed; all remaining records are retained.".into());return Ok((records,notices));}
                let key=format!("{partition}/{}",path.file_stem().unwrap().to_string_lossy());
                match self.read(&key){Ok(record)=>records.push(record),Err(e)=>notices.push(format!("{key}: {}",e.message))}
            }
        }
        records.sort_by_key(|r|std::cmp::Reverse(r.captured_ms));Ok((records,notices))
    }
}
pub fn storage(app:&tauri::AppHandle)->Result<PathBuf,Failure> {
    if let Some(root)=std::env::var_os("RESONANCE_WORKBENCH_RECOVERY_DIR"){return Ok(PathBuf::from(root));}
    // All existing app-local diagnostics get isolated recovery, including startup.
    if let Some(root)=std::env::var_os("RESONANCE_WORKBENCH_CONFIG_DIR"){return Ok(PathBuf::from(root).join("draft-recovery"));}
    Ok(app.path().app_local_data_dir().map_err(error)?.join("draft-recovery-v1"))
}
pub fn with_store<T>(app:&tauri::AppHandle,host:&crate::Host,action:impl FnOnce(&mut Store)->Result<T,Failure>)->Result<T,Failure>{
    let mut slot=host.recovery.lock().unwrap();
    if slot.is_none(){*slot=Some(Store::new(storage(app)?)?);}
    action(slot.as_mut().unwrap())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn sample(root:&Path)->Record {Record {version:VERSION,id:uuid::Uuid::new_v4().to_string(),project:root.into(),source:"roguelike/data/texts/lab/a.json".into(),family:"text".into(),contract:"ordinary-found-text-1".into(),descriptor_sha256:"a".repeat(64),baseline:"\u{feff}{\r\n\"metadata\":\"λ\\n\"}".into(),source_sha256:hash("\u{feff}{\r\n\"metadata\":\"λ\\n\"}".as_bytes()),draft:"\u{feff}{\r\n\"pages\": [\"λ\\n\"".into(),variant:true,variant_id:"letter".into(),target:"roguelike/data/texts/lab/letter.json".into(),generation:1,captured_ms:now(),published:None}}
    #[test]
    fn ordered_atomic_checkpoint_retirement_and_instance_isolation(){
        let dir=tempfile::tempdir().unwrap();let project=tempfile::tempdir().unwrap();let mut a=Store::new(dir.path().into()).unwrap();let mut b=Store::new(dir.path().into()).unwrap();
        let one=sample(project.path());let key=one.key();a.write(&one).unwrap();assert_eq!(b.read(&key).unwrap(),one);
        assert!(b.retire(&key,1).is_err());assert!(b.write(&one).is_err());
        let mut two=one.clone();two.generation=2;two.draft+=" sentinel";
        assert!(a.write_at_boundary(&two,true).is_err());assert_eq!(a.read(&key).unwrap(),one);
        a.write(&two).unwrap();assert!(a.write(&one).is_err());assert!(a.retire(&key,1).is_err());
        a.release(&key);b.claim(&key).unwrap();assert!(a.write(&two).is_err());
        b.retire(&key,2).unwrap();assert!(b.write(&two).is_err());assert!(b.read(&key).is_err());
    }
    #[test]
    fn failed_checkpoint_releases_new_claim_but_preserves_existing_owner(){
        let dir=tempfile::tempdir().unwrap();let project=tempfile::tempdir().unwrap();let mut a=Store::new(dir.path().into()).unwrap();let mut b=Store::new(dir.path().into()).unwrap();
        let record=sample(project.path());let key=record.key();a.write(&record).unwrap();a.release(&key);
        assert!(a.acquired(&key,1,|s,mut r|{r.generation+=1;s.write_at_boundary(&r,true)}).is_err());
        b.claim(&key).unwrap();b.release(&key);assert_eq!(a.read(&key).unwrap(),record);
        a.claim(&key).unwrap();assert!(a.acquired(&key,1,|s,mut r|{r.generation+=1;s.write_at_boundary(&r,true)}).is_err());assert!(b.claim(&key).is_err());
    }
    #[test]
    fn independent_records_survive_reopen_and_malformed_neighbors(){
        let dir=tempfile::tempdir().unwrap();let project=tempfile::tempdir().unwrap();let other=tempfile::tempdir().unwrap();let mut store=Store::new(dir.path().into()).unwrap();
        let a=sample(project.path());let mut b=sample(project.path());b.source="roguelike/data/texts/lab/b.json".into();let mut c=sample(other.path());c.family="item".into();c.source="roguelike/data/items/components/a.json".into();c.target="roguelike/data/items/components/letter.json".into();
        for r in [&a,&b,&c]{store.write(r).unwrap();}
        let bad=sample(project.path());let path=store.path(&bad.key(),"json").unwrap();fs::write(path,b"{invalid").unwrap();drop(store);
        let store=Store::new(dir.path().into()).unwrap();let (rows,notices)=store.list().unwrap();assert_eq!(rows.len(),3);assert_eq!(notices.len(),1);
        for r in [a,b,c]{assert_eq!(store.read(&r.key()).unwrap(),r);}
        assert!(store.read("../outside").is_err());
    }
    #[test]
    fn checkpoint_child_process(){
        let Ok(root)=std::env::var("W5D_CHILD_STORE") else{return};
        let record:Record=serde_json::from_str(&std::env::var("W5D_CHILD_RECORD").unwrap()).unwrap();
        Store::new(root.into()).unwrap().write(&record).unwrap();
    }
    #[test]
    fn exact_bytes_survive_real_child_exit(){
        let dir=tempfile::tempdir().unwrap();let project=tempfile::tempdir().unwrap();let record=sample(project.path());
        let output=std::process::Command::new(std::env::current_exe().unwrap()).args(["--exact","recovery::tests::checkpoint_child_process","--nocapture"])
            .env("W5D_CHILD_STORE",dir.path()).env("W5D_CHILD_RECORD",serde_json::to_string(&record).unwrap()).output().unwrap();
        assert!(output.status.success(),"{}",String::from_utf8_lossy(&output.stderr));
        assert_eq!(Store::new(dir.path().into()).unwrap().read(&record.key()).unwrap(),record);
    }
    #[test]
    fn terminated_child_at_replace_boundary_preserves_previous_complete_record(){
        let dir=tempfile::tempdir().unwrap();let project=tempfile::tempdir().unwrap();let record=sample(project.path());
        Store::new(dir.path().into()).unwrap().write(&record).unwrap();let mut next=record.clone();next.generation=2;next.draft+=" interrupted";
        let ready=dir.path().join("ready");
        let mut child=std::process::Command::new(std::env::current_exe().unwrap()).args(["--exact","recovery::tests::checkpoint_child_process"])
            .env("W5D_CHILD_STORE",dir.path()).env("W5D_CHILD_RECORD",serde_json::to_string(&next).unwrap()).env("W5D_CHILD_INTERRUPT",&ready).spawn().unwrap();
        let began=std::time::Instant::now();while !ready.exists() && began.elapsed().as_secs()<10{std::thread::sleep(std::time::Duration::from_millis(10));}
        child.kill().unwrap();child.wait().unwrap();assert!(ready.exists());
        let mut restarted=Store::new(dir.path().into()).unwrap();assert_eq!(restarted.read(&record.key()).unwrap(),record);
        restarted.write(&next).unwrap();assert_eq!(restarted.read(&record.key()).unwrap(),next);
    }
    #[cfg(windows)]
    #[test]
    fn windows_locked_replacement_keeps_previous_complete_checkpoint(){
        use std::os::windows::fs::OpenOptionsExt;
        let dir=tempfile::tempdir().unwrap();let project=tempfile::tempdir().unwrap();let mut store=Store::new(dir.path().into()).unwrap();let record=sample(project.path());store.write(&record).unwrap();
        let pinned=OpenOptions::new().read(true).share_mode(1).open(store.path(&record.key(),"json").unwrap()).unwrap();
        let mut next=record.clone();next.generation=2;next.draft+=" next";
        assert!(store.write(&next).is_err());assert_eq!(store.read(&record.key()).unwrap(),record);drop(pinned);
        store.write(&next).unwrap();assert_eq!(store.read(&record.key()).unwrap(),next);
    }
}
