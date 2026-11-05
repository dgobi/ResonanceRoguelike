"""SYS-1 full frozen-input gates, using the established production-main harnesses."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import argparse,hashlib,importlib.metadata,json,os,re,subprocess,sys,threading,time
from pathlib import Path
from verify_ai_9 import inputs as inherited_inputs,digest
ROOT=Path(__file__).resolve().parents[1];WB=ROOT/'workbench'


def inputs():
    result=inherited_inputs()
    for p in (ROOT/'evidence/sys-1').glob('legacy*'):
        if p.is_file():result[p.relative_to(ROOT).as_posix()]=digest(p)
    for p in [WB/'README.md',*(WB/'docs').glob('*.md')]:
        result[p.relative_to(ROOT).as_posix()]=digest(p)
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path,required=True);args=ap.parse_args()
    assert sys.platform=='win32' and sys.version_info[:3]==(3,11,0)
    out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True);assert not (out/'release.json').exists()
    assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='main'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    frozen=inputs();(out/'inputs.json').write_text(json.dumps(frozen,indent=2),encoding='utf8')
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',SYS1_RUNTIME_ONLY='1')
    report=dict(passed=False,revision=head,started_utc=datetime.now(timezone.utc).isoformat(),inputs_sha256=digest(out/'inputs.json'),commands=[],environment=dict(platform=sys.platform,python=sys.version,python_executable=sys.executable,dependencies={k:importlib.metadata.version(k) for k in ('pygame','tcod','numpy','cffi','pycparser','typing_extensions')}))
    for name,cmd in [('node',['node','--version']),('cargo',['cargo','--version']),('rustc',['rustc','--version'])]:report['environment'][name]=subprocess.check_output(cmd,text=True).strip()
    lock=threading.Lock()
    def write():(out/'release.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    def execute(name,cmd,cwd=ROOT,timeout=3600):
        began=time.perf_counter();cmd=[str(x) for x in cmd];log=out/(name+'.log')
        with log.open('w',encoding='utf8') as f:
            try:
                code=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,creationflags=0x08000000).returncode;error=None
            except subprocess.TimeoutExpired:code=2;error='finite timeout'
        row=dict(gate=name,command=cmd,cwd=str(cwd),exit_code=code,error=error,seconds=time.perf_counter()-began,source_stable=inputs()==frozen,log_sha256=digest(log))
        row['passed']=code==0 and row['source_stable']
        with lock:report['commands'].append(row);write()
        print(json.dumps(row),flush=True);return row
    py=[sys.executable,'-X','utf8','-B'];write()
    ui=[('frontend',['npm.cmd','test']),('typecheck',['npm.cmd','run','typecheck']),('host',['cargo','test','--locked','--manifest-path','src-tauri/Cargo.toml']),('clippy',['cargo','clippy','--locked','--manifest-path','src-tauri/Cargo.toml','--','-D','warnings']),('debug-build',['cargo','build','--locked','--manifest-path','src-tauri/Cargo.toml']),('build',['npm.cmd','run','build']),('bundle',['npm.cmd','run','bundle']),('startup',['node','scripts/startup-test.mjs']),('desktop',['node','scripts/desktop-test.mjs']),('native',['node','scripts/run-sys-1.mjs'])]
    def ui_gates():
        for name,cmd in ui:
            if not execute(name,cmd,WB)['passed']:return False
        package=WB/'src-tauri/target/release/resonance-workbench.exe'
        with lock:
            report['package']=dict(path=package.relative_to(ROOT).as_posix(),sha256=digest(package))
            report['installers']=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p),size=p.stat().st_size) for p in (WB/'src-tauri/target/release/bundle/nsis').glob('*0.9.0*setup.exe')];write()
        return True
    names=sorted(p.stem for p in (WB/'worker').glob('test_*.py'))
    def worker_gate():
        began=time.perf_counter()
        def one(name):
            cmd=[WB/'worker/runtime/python.exe','-X','utf8','-I','-B','-c',"import sys,unittest;sys.path.insert(0,'worker');r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(["+repr(name)+"]));sys.exit(not r.wasSuccessful())"]
            return execute(name,cmd,WB)
        with ThreadPoolExecutor(max_workers=4) as workers:rows=list(workers.map(one,names))
        log=out/'worker.log';log.write_text(''.join((out/(name+'.log')).read_text(encoding='utf8') for name in names),encoding='utf8')
        row=dict(gate='worker',cohort=names,modules=rows,seconds=time.perf_counter()-began,tests=sum(map(int,re.findall(r'Ran (\d+) tests?',log.read_text(encoding='utf8')))),passed=all(r['passed'] for r in rows),source_stable=inputs()==frozen,log_sha256=digest(log))
        with lock:report['commands']=[r for r in report['commands'] if r['gate'] not in names]+[row];write()
        return row['passed']
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(execute,'focused',py+[ROOT/'tools/critical_fix_regressions/verify_fixes.py','--timeout','3600','--evidence',out/'focused']),pool.submit(execute,'production-d',py+[ROOT/'tools/verify_d.py','--evidence',out/'production-d']),pool.submit(worker_gate),pool.submit(ui_gates)]
        execute('play',py+[ROOT/'tools/verify_sys_1_play.py','--evidence',out/'play'])
        execute('worker-dependency-control',py+['-c',"import sys,unittest;sys.path.insert(0,'worker');r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_bridge.BridgeTests.test_dependency_absence_structured'));sys.exit(not r.wasSuccessful())"],WB)
        for job in jobs:job.result()
    expected={name for name,_ in ui}|{'focused','production-d','worker','play','worker-dependency-control'}
    report['source_stable']=inputs()==frozen
    report['passed']=report['source_stable'] and {r['gate'] for r in report['commands']}==expected and all(r['passed'] for r in report['commands'])
    report['finished_utc']=datetime.now(timezone.utc).isoformat();write()
    print(json.dumps(dict(passed=report['passed'],revision=head)));return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
