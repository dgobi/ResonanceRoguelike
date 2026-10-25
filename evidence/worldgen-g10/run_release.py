"""Serial final G10 gates, finite timeouts and exact frozen-input receipts."""
import argparse
import json
from pathlib import Path
import subprocess
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from verify_g10 import inputs


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--resume-production',action='store_true');a=p.parse_args()
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True);frozen=inputs()
    report=dict(passed=False,frozen_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source=frozen,checks=[])
    production_root=ROOT/'.baseline'/('g10-'+out.name+'-production')
    checks=[('catalog',['tools/structure_authoring.py','--check-editor-catalog'],60),
        ('g10',['tools/verify_g10.py','--evidence',str(out/'g10')],1500),
        ('focused',['tools/critical_fix_regressions/verify_fixes.py','--game','roguelike','--evidence',str(out/'focused'),'--timeout','1800'],1860),
        ('production',['tools/verify_d.py','--evidence',str(production_root)],2400)]
    if a.resume_production:
        report=json.loads((out/'release.json').read_text())
        assert report['frozen_head']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        assert report['source']==frozen and all(c['passed'] for c in report['checks'][:3])
        assert len(report['checks'])==4 and report['checks'][-1]['name']=='production' and not report['checks'][-1]['passed']
        report.setdefault('superseded_checks',[]).append(report['checks'].pop())
        old_log=out/'production-output.txt';saved_log=out/'production-guard-rejection-output.txt'
        assert not saved_log.exists();old_log.rename(saved_log)
        checks=checks[-1:]
    for name,args,timeout in checks:
        command=[sys.executable,'-X','utf8',*args];start=time.perf_counter();print('Final '+name,flush=True)
        with (out/(name+'-output.txt')).open('w',encoding='utf-8') as log:
            try:r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=timeout);code=r.returncode
            except subprocess.TimeoutExpired:code=None
        stable=inputs()==frozen
        if name=='production' and (production_root/'latest.json').exists():
            latest=json.loads((production_root/'latest.json').read_text())
            original=Path(latest['result']);target=out/'production'/original.parent.name
            assert original.resolve().is_relative_to(production_root.resolve())
            shutil.copytree(original.parent,target,ignore=shutil.ignore_patterns('saves'))
            latest.update(original_result=str(original),result=str(target/'results.json'))
            (out/'production/latest.json').write_text(json.dumps(latest,indent=2)+'\n',encoding='utf-8')
        report['checks'].append(dict(name=name,command=command,timeout_seconds=timeout,seconds=time.perf_counter()-start,exit_code=code,source_stable=stable,passed=code==0 and stable))
        report['passed']=all(row['passed'] for row in report['checks']) and len(report['checks'])==4
        (out/'release.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        if code!=0 or not stable:return 1
    print(json.dumps(dict(passed=True,evidence=str(out))))
    return 0


if __name__=='__main__':raise SystemExit(main())
