//! Saved-input capture and game ownership are independent of the request worker.
use super::*;
use sha2::{Digest,Sha256};
use std::{collections::BTreeMap,fs,io::Read};

const CONTRACT:&str="workbench-room-test-1";
const SEED:u32=20261027;
type Files=BTreeMap<String,String>;
fn error(e:impl ToString)->Failure {failure("ROOM_TEST",e,"Correct the saved room/resources or inspect test diagnostics, then retry. Existing drafts are retained.")}
fn hash(bytes:impl AsRef<[u8]>)->String {format!("{:x}",Sha256::digest(bytes))}

#[derive(Default,Clone)]
pub struct Games {inner:Arc<Mutex<GameState>>,generation:Arc<AtomicU64>}
#[derive(Default)]
struct GameState {capture:Option<Arc<Capture>>,process:Option<Owned>,status:Value,preparing:bool}
struct Capture {temp:tempfile::TempDir,project:PathBuf,source:String,files:Files,runtime:Files,identity:Value}
impl Capture {
    fn root(&self)->PathBuf {self.temp.path().join("payload")}
    fn python(&self)->PathBuf {self.temp.path().join("runtime/python.exe")}
}
impl Drop for Capture {
    fn drop(&mut self){
        // Only known files in this positively owned TempDir; no external cleanup.
        for (base,files) in [(self.root(),&self.files),(self.temp.path().join("runtime"),&self.runtime)] {
            for name in files.keys(){if let Ok(mut p)=fs::metadata(base.join(name)).map(|m|m.permissions()){
                #[allow(clippy::permissions_set_readonly_false)]
                p.set_readonly(false);let _=fs::set_permissions(base.join(name),p);
            }}
        }
    }
}

#[cfg(windows)]
struct Job(windows_sys::Win32::Foundation::HANDLE);
#[cfg(windows)]
unsafe impl Send for Job {}
#[cfg(windows)]
impl Job {
    fn attach(child:&Child)->Result<Self,Failure>{
        use windows_sys::Win32::{Foundation::*,System::JobObjects::*};
        use std::os::windows::io::AsRawHandle;
        unsafe {
            let handle=CreateJobObjectW(std::ptr::null(),std::ptr::null());
            if handle.is_null(){return Err(error(std::io::Error::last_os_error()));}
            let job=Self(handle);
            let mut info:JOBOBJECT_EXTENDED_LIMIT_INFORMATION=std::mem::zeroed();
            info.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            if SetInformationJobObject(handle,JobObjectExtendedLimitInformation,(&info as *const JOBOBJECT_EXTENDED_LIMIT_INFORMATION).cast(),std::mem::size_of_val(&info) as u32)==0
                || AssignProcessToJobObject(handle,child.as_raw_handle() as HANDLE)==0 {return Err(error(std::io::Error::last_os_error()));}
            Ok(job)
        }
    }
}
#[cfg(windows)]
impl Drop for Job {fn drop(&mut self){unsafe{windows_sys::Win32::Foundation::CloseHandle(self.0);}}}

struct Owned {child:Child,#[cfg(windows)] _job:Job,output:Arc<Mutex<Vec<u8>>>}
impl Owned {
    fn spawn(command:&mut Command)->Result<Self,Failure>{
        command.stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::piped());
        #[cfg(windows)] {use std::os::windows::process::CommandExt;command.creation_flags(0x08000000);}
        let mut child=command.spawn().map_err(error)?;
        #[cfg(windows)]
        let job=match Job::attach(&child){Ok(job)=>job,Err(e)=>{let _=child.kill();let _=child.wait();return Err(e);}};
        let output=Arc::new(Mutex::new(Vec::new()));
        fn drain(mut stream:impl Read+Send+'static,output:Arc<Mutex<Vec<u8>>>){std::thread::spawn(move||{
            let mut buf=[0;4096];while let Ok(n)=stream.read(&mut buf){if n==0{break;}let mut out=output.lock().unwrap();out.extend_from_slice(&buf[..n]);if out.len()>65536{let excess=out.len()-65536;out.drain(..excess);}}
        });}
        drain(child.stdout.take().unwrap(),output.clone());drain(child.stderr.take().unwrap(),output.clone());
        Ok(Self{child,#[cfg(windows)] _job:job,output})
    }
    fn diagnostics(&self)->String {String::from_utf8_lossy(&self.output.lock().unwrap()).into_owned()}
    fn reap(&mut self){let _=self.child.kill();let _=self.child.wait();}
}
impl Drop for Owned {fn drop(&mut self){self.reap();}}

/// Bounded enumeration visits only admitted trees, skipping caches before descent.
fn inventory(root:&Path, runtime:bool, check:&impl Fn()->Result<(),Failure>)->Result<Files,Failure>{
    fn walk(root:&Path,path:&Path,runtime:bool,out:&mut Files,total:&mut u64,depth:usize,check:&impl Fn()->Result<(),Failure>)->Result<(),Failure>{
        check()?;if depth>24{return Err(error("Input directory depth exceeds 24"));}
        authoring::no_link(path)?;
        if path.is_dir(){
            let mut entries=fs::read_dir(path).map_err(error)?.collect::<Result<Vec<_>,_>>().map_err(error)?;
            if entries.len()>12000{return Err(error("Input directory exceeds enumeration bound"));}
            entries.sort_by_key(|e|e.file_name());
            for entry in entries {if ["__pycache__",".git","saves",".sessions",".venv","node_modules"].iter().any(|s|entry.file_name()==*s){continue;}
                walk(root,&entry.path(),runtime,out,total,depth+1,check)?;
            }
        }else{
            let rel=path.strip_prefix(root).map_err(error)?.to_string_lossy().replace('\\',"/");
            let allowed=runtime || rel.starts_with("roguelike/assets/") || rel.starts_with("roguelike/data/") && path.extension().is_some_and(|e|e=="json"||e=="txt") || path.extension().is_some_and(|e|e=="py") || rel=="requirements-baseline.txt" || rel.starts_with("roguelike/docs/examples/");
            if !allowed{return Ok(());}
            let size=path.metadata().map_err(error)?.len();*total+=size;
            if size>64*1024*1024 || *total>384*1024*1024 || out.len()>=12000{return Err(error("Input capture exceeds file/byte limits"));}
            out.insert(rel,hash(fs::read(path).map_err(error)?));
        }Ok(())
    }
    let mut files=Files::new();let mut total=0;
    if runtime {walk(root,root,true,&mut files,&mut total,0,check)?;}else{
        authoring::no_link(root)?;authoring::no_link(&root.join("roguelike"))?;
        // No repository-wide walk; saves, environments, logs and owner material
        // are neither traversed nor consulted.
        for relative in ["requirements-baseline.txt","roguelike/main.py","roguelike/config.py","roguelike/room_test.py","roguelike/engine","roguelike/components","roguelike/entities","roguelike/generation","roguelike/rendering","roguelike/world","roguelike/data","roguelike/assets/Fonts","roguelike/assets/ui","roguelike/assets/sprites","roguelike/docs/examples/g17_authored_creature_room.json","roguelike/docs/examples/g17_authored_creature_room.access.json"] {
            let path=root.join(relative);
            // Check lexical intermediate roots, including assets/docs junctions.
            let mut ancestor=root.to_path_buf();for part in Path::new(relative).components(){ancestor.push(part);if ancestor.exists(){authoring::no_link(&ancestor)?;}}
            if path.exists(){walk(root,&path,false,&mut files,&mut total,0,check)?;}
        }
        if !files.contains_key("roguelike/room_test.py"){return Err(error("Selected project has no compatible room_test.py entry point"));}
    }
    Ok(files)
}
fn copy_verified(source:&Path,target:&Path,files:&Files,check:&impl Fn()->Result<(),Failure>)->Result<(),Failure>{
    for (relative,digest) in files{
        check()?;let from=source.join(relative);let mut ancestor=source.to_path_buf();authoring::no_link(&ancestor)?;for part in Path::new(relative).components(){ancestor.push(part);authoring::no_link(&ancestor)?;}
        let bytes=fs::read(&from).map_err(error)?;if hash(&bytes)!=*digest{return Err(error(format!("Input changed during capture: {relative}")));}
        let to=target.join(relative);fs::create_dir_all(to.parent().unwrap()).map_err(error)?;fs::write(&to,bytes).map_err(error)?;
        if hash(fs::read(&to).map_err(error)?)!=*digest{return Err(error("Copied input failed byte verification"));}
    }Ok(())
}
fn freeze(root:&Path,files:&Files)->Result<(),Failure>{for name in files.keys(){let p=root.join(name);let mut permissions=p.metadata().map_err(error)?.permissions();permissions.set_readonly(true);fs::set_permissions(p,permissions).map_err(error)?;}Ok(())}
fn sessions_root()->Result<PathBuf,Failure>{
    let root=std::env::temp_dir().join("ResonanceWorkbenchRoomTests");fs::create_dir_all(&root).map_err(error)?;authoring::no_link(&root)?;dunce::canonicalize(root).map_err(error)
}
#[cfg(windows)]
fn owner_alive(pid:u32)->bool{
    use windows_sys::Win32::{Foundation::*,System::Threading::*};
    unsafe {let handle=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,0,pid);if handle.is_null(){return GetLastError()!=ERROR_INVALID_PARAMETER;}CloseHandle(handle);true}
}
#[cfg(not(windows))]
fn owner_alive(_pid:u32)->bool{true}
fn cleanup_abandoned(base:&Path)->Result<(),Failure>{
    let executable=std::env::current_exe().map_err(error)?;let mut removed=0;
    for entry in fs::read_dir(base).map_err(error)?.take(128){
        let path=entry.map_err(error)?.path();
        if !path.file_name().is_some_and(|n|n.to_string_lossy().starts_with("session-")) || authoring::no_link(&path).is_err(){continue;}
        let marker=path.join("ownership.json");if authoring::no_link(&marker).is_err(){continue;}
        let owner=read_value(&marker);
        if owner["contract"]!=CONTRACT || owner["application"]!=executable.to_string_lossy().as_ref() || owner["pid"].as_u64().is_none_or(|pid|pid>u32::MAX as u64||owner_alive(pid as u32)){continue;}
        // A bounded complete link check precedes deletion; only dead owners of
        // this exact installation qualify. Other live/foreign sessions stay.
        fn paths(path:&Path,out:&mut Vec<PathBuf>,depth:usize)->Result<(),Failure>{
            if depth>24||out.len()>20000{return Err(error("Abandoned payload exceeds cleanup bounds"));}authoring::no_link(path)?;
            out.push(path.into());if path.is_dir(){for e in fs::read_dir(path).map_err(error)?{paths(&e.map_err(error)?.path(),out,depth+1)?;}}Ok(())
        }
        let mut owned=Vec::new();if paths(&path,&mut owned,0).is_err(){continue;}
        let resolved=dunce::canonicalize(&path).map_err(error)?;if resolved.parent()!=Some(base){continue;}
        for p in owned {if p.is_file(){let mut permissions=p.metadata().map_err(error)?.permissions();#[allow(clippy::permissions_set_readonly_false)] permissions.set_readonly(false);fs::set_permissions(p,permissions).map_err(error)?;}}
        fs::remove_dir_all(resolved).map_err(error)?;removed+=1;if removed==4{break;}
    }Ok(())
}
fn capture(project:PathBuf,source:String,original:Vec<u8>,python:PathBuf,check:&impl Fn()->Result<(),Failure>)->Result<Capture,Failure>{
    let runtime_root=python.parent().ok_or_else(||error("Runtime path unavailable"))?;
    if !runtime_root.join("python311._pth").is_file(){return Err(error("Room tests require the packaged pinned runtime (or prepared worker/runtime), not a mutable virtual environment"));}
    let files=inventory(&project,false,check)?;let runtime=inventory(runtime_root,true,check)?;
    if files.get(&source)!=Some(&hash(&original)){return Err(error("Saved room changed before capture"));}
    let sessions=sessions_root()?;cleanup_abandoned(&sessions)?;
    let temp=tempfile::Builder::new().prefix("session-").tempdir_in(sessions).map_err(error)?;
    fs::write(temp.path().join("ownership.json"),serde_json::to_vec(&json!({"contract":CONTRACT,"pid":std::process::id(),"application":std::env::current_exe().map_err(error)?})).unwrap()).map_err(error)?;
    copy_verified(&project,&temp.path().join("payload"),&files,check)?;
    copy_verified(runtime_root,&temp.path().join("runtime"),&runtime,check)?;
    if inventory(&project,false,check)?!=files || inventory(runtime_root,true,check)?!=runtime{return Err(error("Source/data/resource/runtime changed during capture; retry from stable saved inputs"));}
    let snapshot_id=uuid::Uuid::new_v4().to_string();
    let identity=json!({"contract":CONTRACT,"snapshot_id":snapshot_id,"captured_ms":recovery::now(),"project":project,"room_path":source,"room_sha256":hash(&original),"manifest_sha256":hash(serde_json::to_vec(&files).unwrap()),"runtime_sha256":hash(serde_json::to_vec(&runtime).unwrap()),"seed":SEED,"files":files,"runtime_files":runtime});
    fs::write(temp.path().join("manifest.json"),serde_json::to_vec(&identity).unwrap()).map_err(error)?;
    Ok(Capture{temp,project,source,files,runtime,identity})
}
fn config(capture:&Capture,session:&str)->Result<(PathBuf,Value),Failure>{
    let root=capture.temp.path().join(format!("state-{session}"));fs::create_dir(&root).map_err(error)?;
    let mut value=capture.identity.clone();
    value["session_id"]=json!(session);value["manifest"]=json!(capture.temp.path().join("manifest.json"));value["state_root"]=json!(root);
    value["diagnostic_events"]=json!(std::env::var("RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION").as_deref()==Ok("1"));
    for (key,file) in [("ready_path","ready.json"),("validation_path","validation.json"),("stop_path","stop")] {value[key]=json!(root.join(file));}
    let path=root.join("session.json");fs::write(&path,serde_json::to_vec(&value).unwrap()).map_err(error)?;Ok((path,value))
}
fn command(capture:&Capture,config:&Path)->Command{
    let mut cmd=Command::new(capture.python());
    cmd.args(["-I","-B","-u","-c","import sys,runpy;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('room_test',run_name='__main__')"])
        .arg(capture.root().join("roguelike")).arg("--session").arg(config)
        .current_dir(capture.root().join("roguelike"))
        .env_remove("PYTHONPATH").env("PYTHONDONTWRITEBYTECODE","1")
        .env("TMP",config.parent().unwrap()).env("TEMP",config.parent().unwrap())
        .env("OPENBLAS_NUM_THREADS","1").env("OMP_NUM_THREADS","1");cmd
}
fn validation(capture:&Capture,check:&impl Fn()->Result<(),Failure>)->Result<Value,Failure>{
    let (path,config)=config(capture,&format!("validation-{}",uuid::Uuid::new_v4()))?;
    let mut child=Owned::spawn(command(capture,&path).arg("--validate").env("SDL_VIDEODRIVER","dummy").env("SDL_AUDIODRIVER","dummy"))?;
    let start=Instant::now();loop{
        check()?;
        if let Some(code)=child.child.try_wait().map_err(error)?{
            if !code.success(){return Err(error(format!("Captured validation exited {code}: {}",child.diagnostics())));}
            let report=read_value(Path::new(config["validation_path"].as_str().unwrap()));
            let room:Value=serde_json::from_slice(&fs::read(capture.root().join(&capture.source)).map_err(error)?).map_err(error)?;
            if report["contract"]!=CONTRACT || report["room_contract"]!="authored-room-1" || report["route"]!="authored_submap" || report["room_id"]!=room["id"] || !report["profile"].is_string(){return Err(error("Captured game did not confirm the compatible room-test contract"));}
            return Ok(report);
        }
        if start.elapsed()>Duration::from_secs(60){return Err(error("Captured validation timed out"));}
        std::thread::sleep(Duration::from_millis(30));
    }
}
impl Games {
    fn check(&self,generation:u64)->Result<(),Failure>{if self.generation.load(Ordering::SeqCst)==generation{Ok(())}else{Err(error("Room test cancelled or project replaced"))}}
    pub fn stop(&self,clear:bool)->Result<(),Failure>{
        self.generation.fetch_add(1,Ordering::SeqCst);
        let mut state=self.inner.lock().unwrap();state.preparing=false;
        if let Some(mut process)=state.process.take(){
            if let Some(path)=state.status["stop_path"].as_str(){let _=fs::write(path,b"stop");}
            let started=Instant::now();while started.elapsed()<Duration::from_secs(2){if process.child.try_wait().map_err(error)?.is_some(){break;}std::thread::sleep(Duration::from_millis(20));}
            process.reap();state.status["diagnostics"]=json!(process.diagnostics());state.status["reaped"]=json!(true);
        }
        state.status["status"]=json!("stopped");
        if clear{state.capture=None;state.status=Value::Null;}Ok(())
    }
    fn status(&self)->Value{
        let state=self.inner.lock().unwrap();let mut value=state.status.clone();
        if value.is_null(){value=json!({"status":"stopped"});}
        value["preparing"]=json!(state.preparing);
        if let Some(c)=&state.capture{
            value["captured"]=c.identity.clone();
            let mut path=c.project.clone();let safe=authoring::no_link(&path).is_ok() && Path::new(&c.source).components().all(|part|{path.push(part);authoring::no_link(&path).is_ok()});
            value["newer_saved"]=json!(value["newer_saved"]==true || !safe || fs::read(path).map(|b|hash(b)!=c.identity["room_sha256"]).unwrap_or(true));
        }
        if let Some(p)=&state.process{value["diagnostics"]=json!(p.diagnostics());}
        value
    }
    fn launch(&self,capture:Arc<Capture>,generation:u64)->Result<(),Failure>{
        self.check(generation)?;
        let session=uuid::Uuid::new_v4().to_string();let (path,config)=config(&capture,&session)?;
        // Previous running test survives capture/validation failures. Replacement
        // becomes destructive only after the new frozen version is admitted.
        let mut state=self.inner.lock().unwrap();self.check(generation)?;
        if let Some(mut process)=state.process.take(){process.reap();}
        let child=Owned::spawn(&mut command(&capture,&path))?;
        let cleanup=state.capture.as_ref().and_then(|old|state.status["state_root"].as_str().map(|p|discard_state(old,Path::new(p)))).transpose();
        let pid=child.child.id();state.capture=Some(capture.clone());state.process=Some(child);state.preparing=false;
        state.status=json!({"status":"starting","session_id":session,"snapshot_id":capture.identity["snapshot_id"],"pid":pid,"state_root":config["state_root"],"ready_path":config["ready_path"],"stop_path":config["stop_path"],"started_ms":recovery::now(),"validation":read_value(Path::new(config["validation_path"].as_str().unwrap()))});
        state.status["validation"]=read_value(&capture.temp.path().join("validation.json"));
        if let Err(e)=cleanup {state.status["cleanup_warning"]=json!(e);}
        drop(state);
        let snapshot_id=capture.identity["snapshot_id"].clone();
        let games=self.clone();std::thread::spawn(move||{
            let started=Instant::now();loop{
                std::thread::sleep(Duration::from_millis(50));if games.check(generation).is_err(){break;}
                let mut state=games.inner.lock().unwrap();if games.check(generation).is_err() || state.status["session_id"]!=session{break;}
                let Some(process)=state.process.as_mut() else{break;};
                match process.child.try_wait(){
                    Ok(Some(code))=>{let diagnostics=process.diagnostics();state.process.take();state.status["status"]=json!(if code.success(){"stopped"}else{"failed"});state.status["exit_code"]=json!(code.code());state.status["diagnostics"]=json!(diagnostics);state.status["reaped"]=json!(true);break;},
                    Err(e)=>{state.process.take();state.status["status"]=json!("failed");state.status["error"]=json!(e.to_string());break;},_=>{}
                }
                let ready=read_value(Path::new(config["ready_path"].as_str().unwrap()));
                if ready_for(&ready,&session,&snapshot_id,pid) {state.status["status"]=json!("running");state.status["readiness"]=ready;state.status["validation"]=read_value(Path::new(config["validation_path"].as_str().unwrap()));}
                else if started.elapsed()>Duration::from_secs(45){state.process.take();state.status["status"]=json!("failed");state.status["error"]=json!("Game failed to produce a usable frame within 45 seconds");state.status["reaped"]=json!(true);break;}
            }
        });Ok(())
    }
}
fn read_value(path:&Path)->Value{
    if authoring::no_link(path).is_err() || !path.metadata().is_ok_and(|m|m.len()<=4*1024*1024){return Value::Null;}
    fs::read(path).ok().and_then(|b|serde_json::from_slice(&b).ok()).unwrap_or(Value::Null)
}
fn ready_for(value:&Value,session:&str,snapshot:&Value,pid:u32)->bool{
    value["session_id"]==session && value["snapshot_id"]==*snapshot && value["pid"]==pid && value["contract"]==CONTRACT
}

fn discard_state(capture:&Capture,path:&Path)->Result<(),Failure>{
    if path.parent()!=Some(capture.temp.path()) || !path.file_name().is_some_and(|s|s.to_string_lossy().starts_with("state-")){return Err(error("Refused non-owned session cleanup"));}
    fn check(path:&Path)->Result<(),Failure>{authoring::no_link(path)?;if path.is_dir(){for e in fs::read_dir(path).map_err(error)?{check(&e.map_err(error)?.path())?;}}Ok(())}
    check(path)?;fs::remove_dir_all(path).map_err(error)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn put(root:&Path,name:&str,bytes:&[u8]){let p=root.join(name);fs::create_dir_all(p.parent().unwrap()).unwrap();fs::write(p,bytes).unwrap();}
    #[test]
    fn bounded_inputs_include_sprites_exclude_saves_and_detect_mutations(){
        let temp=tempfile::tempdir().unwrap();let root=temp.path();
        for name in ["roguelike/room_test.py","roguelike/config.py","roguelike/data/layouts/test.json","roguelike/assets/sprites/sheet.png","roguelike/assets/Fonts/font.ttf","roguelike/assets/ui/panel.png","roguelike/data/display/typography.json"]{put(root,name,b"input");}
        for name in ["roguelike/saves/sentinel",".git/sentinel",".venv/sentinel","owner-plan.md","roguelike/engine/__pycache__/cache.py"]{put(root,name,b"sentinel");}
        let files=inventory(root,false,&||Ok(())).unwrap();assert_eq!(files.len(),7);assert!(files.contains_key("roguelike/assets/sprites/sheet.png"));
        let target=tempfile::tempdir().unwrap();copy_verified(root,target.path(),&files,&||Ok(())).unwrap();
        put(root,"roguelike/assets/sprites/sheet.png",b"changed");assert_ne!(files,inventory(root,false,&||Ok(())).unwrap());
        assert!(copy_verified(root,target.path(),&files,&||Ok(())).is_err());assert_eq!(fs::read(target.path().join("roguelike/assets/sprites/sheet.png")).unwrap(),b"input");
        assert!(inventory(root,false,&||Err(error("cancelled"))).is_err());
    }
    #[test]
    fn abandoned_cleanup_preserves_live_and_foreign_owners(){
        let temp=tempfile::tempdir().unwrap();let app=std::env::current_exe().unwrap();
        for (name,pid,application) in [("session-live",std::process::id(),app.clone()),("session-foreign",u32::MAX,PathBuf::from("foreign.exe")),("session-abandoned",u32::MAX,app)]{
            put(temp.path(),&format!("{name}/ownership.json"),serde_json::to_string(&json!({"contract":CONTRACT,"pid":pid,"application":application})).unwrap().as_bytes());put(temp.path(),&format!("{name}/payload/input"),b"saved");
        }
        cleanup_abandoned(temp.path()).unwrap();assert!(temp.path().join("session-live").exists());assert!(temp.path().join("session-foreign").exists());
        #[cfg(windows)] assert!(!temp.path().join("session-abandoned").exists());
    }
    #[test]
    fn readiness_requires_current_session_snapshot_process_and_contract(){
        let snapshot=json!("snapshot-new");let ready=json!({"session_id":"session-new","snapshot_id":snapshot,"pid":42,"contract":CONTRACT});
        assert!(ready_for(&ready,"session-new",&snapshot,42));
        for field in ["session_id","snapshot_id","pid","contract"]{let mut old=ready.clone();old[field]=json!("stale");assert!(!ready_for(&old,"session-new",&snapshot,42));}
    }
    #[cfg(windows)]
    #[test]
    fn junctions_are_refused_before_copying(){
        use std::os::windows::process::CommandExt;
        let root=tempfile::tempdir().unwrap();let foreign=tempfile::tempdir().unwrap();put(root.path(),"roguelike/room_test.py",b"input");
        put(foreign.path(),"sentinel",b"foreign");fs::create_dir_all(root.path().join("roguelike/assets")).unwrap();
        let result=Command::new("cmd").args(["/c","mklink","/J"]).arg(root.path().join("roguelike/assets/sprites").to_string_lossy().replace('/',"\\")).arg(foreign.path()).creation_flags(0x08000000).output().unwrap();assert!(result.status.success(),"{} {}",String::from_utf8_lossy(&result.stdout),String::from_utf8_lossy(&result.stderr));
        assert_eq!(inventory(root.path(),false,&||Ok(())).unwrap_err().code,"PATH_ESCAPE");
        fs::remove_dir(root.path().join("roguelike/assets/sprites")).unwrap();assert_eq!(fs::read(foreign.path().join("sentinel")).unwrap(),b"foreign");
    }
    fn sleeper()->Owned{Owned::spawn(Command::new("python").args(["-c","import time;time.sleep(120)"])).unwrap()}
    #[test]
    fn actual_noncooperating_stop_reaps_only_owned_child(){
        let mut sentinel=sleeper();let game=sleeper();let pid=game.child.id();
        let games=Games::default();{let mut state=games.inner.lock().unwrap();state.process=Some(game);state.status=json!({"status":"running","pid":pid});}
        games.stop(false).unwrap();assert!(games.inner.lock().unwrap().process.is_none());assert_eq!(games.status()["reaped"],true);assert!(sentinel.child.try_wait().unwrap().is_none());
        let old=games.generation.load(Ordering::SeqCst);games.stop(true).unwrap();assert!(games.check(old).is_err());
    }
    #[cfg(windows)]
    #[test]
    fn job_owner_child(){
        if let Some(path)=std::env::var_os("W5H_JOB_RECEIPT") {let process=sleeper();fs::write(path,process.child.id().to_string()).unwrap();std::thread::sleep(Duration::from_secs(120));}
    }
    #[cfg(windows)]
    #[test]
    fn abrupt_owner_death_closes_job_and_kills_game(){
        use windows_sys::Win32::{Foundation::*,System::Threading::*};
        let temp=tempfile::tempdir().unwrap();let receipt=temp.path().join("pid");let mut sentinel=sleeper();
        let mut owner=Command::new(std::env::current_exe().unwrap()).args(["--exact","room_test::tests::job_owner_child","--nocapture"]).env("W5H_JOB_RECEIPT",&receipt).stdout(Stdio::null()).spawn().unwrap();
        let start=Instant::now();while !receipt.exists(){assert!(start.elapsed()<Duration::from_secs(10));std::thread::sleep(Duration::from_millis(20));}
        let pid=fs::read_to_string(&receipt).unwrap().parse().unwrap();
        unsafe{let handle=OpenProcess(PROCESS_SYNCHRONIZE,0,pid);assert!(!handle.is_null());owner.kill().unwrap();owner.wait().unwrap();assert_eq!(WaitForSingleObject(handle,5000),WAIT_OBJECT_0);CloseHandle(handle);}
        assert!(sentinel.child.try_wait().unwrap().is_none());
    }
}

#[tauri::command]
pub async fn room_test_action(app:tauri::AppHandle,host:tauri::State<'_,Host>,action:String,token:Option<String>)->Result<Value,Failure>{
    let games=host.games.clone();
    if action=="refresh" {
        let capture=games.inner.lock().unwrap().capture.clone();
        return tauri::async_runtime::spawn_blocking(move||{
            if let Some(c)=capture {let changed=inventory(&c.project,false,&||Ok(())).map(|f|f!=c.files).unwrap_or(true);let mut state=games.inner.lock().unwrap();if state.capture.as_ref().is_some_and(|current|Arc::ptr_eq(current,&c)){state.status["newer_saved"]=json!(changed);}}
            Ok(games.status())
        }).await.map_err(error)?;
    }
    if action=="status"{return Ok(games.status());}
    if action=="stop"{return tauri::async_runtime::spawn_blocking(move||{games.stop(false)?;Ok(games.status())}).await.map_err(error)?;}
    if !["test","latest","reset"].contains(&action.as_str()){return Err(error("Unknown room action"));}
    let source=if action=="reset"{None}else{Some(authoring::room_test_source(&host,token.as_deref().ok_or_else(||error("Select the saved room"))?)?)};
    let runtime=if source.is_some(){Some(startup::runtime(&app)?)}else{None};
    let generation={let mut state=games.inner.lock().unwrap();
        if state.preparing || action=="test" && state.process.is_some(){return Err(error("A room test is already preparing/running; use Stop, Reset or Test latest saved version"));}
        if action=="reset" && state.capture.is_none(){return Err(error("No captured room test to reset"));}
        state.preparing=true;games.generation.load(Ordering::SeqCst)
    };
    let owned_host=host.inner().clone();
    tauri::async_runtime::spawn_blocking(move||{
        let result=(||{
            let check=||games.check(generation);
            let capture=if let Some((root,path,bytes))=source{
                let mut capture=capture(root,path,bytes,runtime.unwrap().python,&check)?;
                let report=validation(&capture,&check)?;
                // Final complete saved-input freshness check after validation.
                if inventory(&capture.project,false,&check)?!=capture.files{return Err(error("Saved inputs changed during captured validation"));}
                let admitted=authoring::room_test_source(&owned_host,token.as_deref().unwrap())?;
                if admitted.0!=capture.project || admitted.1!=capture.source || hash(admitted.2)!=capture.identity["room_sha256"]{return Err(error("Document/project changed before launch"));}
                fs::write(capture.temp.path().join("validation.json"),serde_json::to_vec(&report).unwrap()).map_err(error)?;
                capture.identity["profile"]=report["profile"].clone();capture.identity["room_id"]=report["room_id"].clone();capture.identity["descriptor_sha256"]=report["descriptor_sha256"].clone();
                fs::write(capture.temp.path().join("manifest.json"),serde_json::to_vec(&capture.identity).unwrap()).map_err(error)?;
                freeze(&capture.root(),&capture.files)?;freeze(&capture.temp.path().join("runtime"),&capture.runtime)?;
                Arc::new(capture)
            }else{games.inner.lock().unwrap().capture.clone().ok_or_else(||error("No captured version"))?};
            games.launch(capture,generation)?;Ok(games.status())
        })();
        if let Err(e)=&result{if games.check(generation).is_ok(){let mut state=games.inner.lock().unwrap();state.preparing=false;state.status["last_action_error"]=json!(e);if state.capture.is_none(){state.status["status"]=json!("failed");}}}
        result
    }).await.map_err(error)?
}
