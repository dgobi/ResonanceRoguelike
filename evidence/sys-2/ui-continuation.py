"""Continue unreached UI gates on the identical SYS-2 frozen inputs.

The first host run's contradictory path expectation is retained as failed. This
does not mark it passed or mutate sources; a separately bound correction follows.
"""
from pathlib import Path
import json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from verify_sys_2 import inputs,digest
OUT=ROOT/'.baseline/sys-2/final-a';WB=ROOT/'workbench'
frozen=json.loads((OUT/'inputs.json').read_text())
assert inputs()==frozen
env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',SYS1_RUNTIME_ONLY='1',SYS2_RUNTIME_ONLY='1')
report=dict(passed=False,revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),inputs_sha256=digest(OUT/'inputs.json'),script_sha256=digest(Path(__file__)),commands=[])
sequence=[('clippy',['cargo','clippy','--locked','--manifest-path','src-tauri/Cargo.toml','--','-D','warnings']),('debug-build',['cargo','build','--locked','--manifest-path','src-tauri/Cargo.toml']),('build',['npm.cmd','run','build']),('bundle',['npm.cmd','run','bundle']),('startup',['node','scripts/startup-test.mjs']),('desktop',['node','scripts/desktop-test.mjs']),('native',['node','scripts/run-sys-2.mjs']),('retained-native',['node','scripts/run-sys-1.mjs'])]
for name,command in sequence:
    log=OUT/(name+'.log');assert not log.exists()
    began=time.perf_counter()
    with log.open('w',encoding='utf8') as f:
        code=subprocess.run(command,cwd=WB,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=3600,creationflags=0x08000000).returncode
    row=dict(gate=name,command=command,cwd=str(WB),exit_code=code,seconds=time.perf_counter()-began,source_stable=inputs()==frozen,log_sha256=digest(log))
    row['passed']=code==0 and row['source_stable'];report['commands'].append(row)
    (OUT/'ui-continuation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(row),flush=True)
    if not row['passed']:raise SystemExit(1)
report['package']=dict(path='workbench/src-tauri/target/release/resonance-workbench.exe',sha256=digest(WB/'src-tauri/target/release/resonance-workbench.exe'))
report['installers']=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p),size=p.stat().st_size) for p in (WB/'src-tauri/target/release/bundle/nsis').glob('*0.9.0*setup.exe')]
report['passed']=True
(OUT/'ui-continuation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
