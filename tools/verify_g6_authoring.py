"""Execute G6 owner recipes, preserving drafts and recording expected negatives."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from verify_b3 import source_manifest

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--evidence',type=Path,required=True);args=ap.parse_args()
    out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True);source=source_manifest();records=[]
    environment={k:os.environ[k] for k in ('PYTHONPATH','PYTHONHASHSEED','SDL_VIDEODRIVER','SDL_AUDIODRIVER') if k in os.environ}
    def run(argv,expected=0,outputs=()):
        result=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=180)
        records.append(dict(argv=list(map(str,argv)),cwd=str(ROOT),environment=environment,exit_code=result.returncode,
            expected_exit=expected,expected_negative=expected!=0,stdout=result.stdout,stderr=result.stderr,
            outputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs if p.exists()}))
        if result.returncode!=expected:raise AssertionError(result.stdout+result.stderr)
    def cli(argv,name,expected=0):
        output=out/(name+'.json')
        run([sys.executable,'-X','utf8',ROOT/'tools/structure_authoring.py',*argv,'--output',output],expected,[output])
    try:
        run([sys.executable,'-X','utf8',ROOT/'tools/verify_g5_authoring.py','--evidence',out/'g5-recipes'])
        with tempfile.TemporaryDirectory(prefix='g6-authoring-') as temporary:
            temp=Path(temporary);draft=temp/'g6_wayhouse.json';original=ROOT/'roguelike/docs/examples/g6_wayhouse.json'
            command=['powershell','-NoProfile','-Command',f"if (-not (Test-Path -LiteralPath '{draft}')) {{ Copy-Item -LiteralPath '{original}' -Destination '{draft}' }}"]
            run(command,outputs=[draft]);raw=json.loads(draft.read_text(encoding='utf-8-sig'));raw['owner_sentinel']='G6 edited draft survives initialization'
            draft.write_text(json.dumps(raw,indent=2)+'\n',encoding='utf-8');before=draft.read_bytes()
            run(command,outputs=[draft]);run(command,outputs=[draft]);assert draft.read_bytes()==before
            records.append(dict(action='sentinel survives twice-repeated guarded initialization',sha256=hashlib.sha256(before).hexdigest(),path=str(draft)))
            cli([draft,'--route','ordinary_building','--category','wilderness','--orientations'],'direct')
            for normal in 'NESW':cli([draft,'--assigned-site',normal,'--category','wilderness'],'assigned-'+normal)
            policy=ROOT/'roguelike/docs/examples/g6_poi_example.json'
            cli([draft,'--site','--category','wilderness','--poi-config',policy],'selected')
            catalog=temp/'data';shutil.copytree(ROOT/'roguelike/data',catalog)
            shutil.copyfile(draft,catalog/'buildings/wilderness/g6_wayhouse.json');shutil.copyfile(policy,catalog/'generation/poi_profiles.json')
            records.append(dict(action='deliberate install in disposable data catalog',layout=str(catalog/'buildings/wilderness/g6_wayhouse.json'),policy=str(catalog/'generation/poi_profiles.json')))
            cli(['--data-root',catalog,'--catalog'],'installed-catalog');cli(['--data-root',catalog,'--world-plan'],'installed-world')
            default=json.loads((ROOT/'roguelike/data/generation/poi_profiles.json').read_text())
            # The preserved G6 recipes explicitly exercise v1 single-site policy.
            if default['version']==2:
                default['assets']=[{k:v for k,v in r.items() if k!='kind'} for r in default.pop('choices') if r['kind']=='single']
                default.pop('kind_minimum');default['version']=1
            short=copy.deepcopy(default);short['assets']=[dict(asset='hunter_cabin',weight=1,cap=2)]
            negative=temp/'policy.json';negative.write_text(json.dumps(short));cli(['--world-plan','--poi-config',negative],'cap-shortfall')
            report=json.loads((out/'cap-shortfall.json').read_text());assert report['plan']['site_selection']['accepted']==2 and report['plan']['site_selection']['desired']==3
            zero=dict(default,minimum=0,maximum=0);negative.write_text(json.dumps(zero));cli([draft,'--site','--poi-config',negative],'eligible-unselected',1)
            low=dict(default,fit_budget=1);negative.write_text(json.dumps(low));cli(['--world-plan','--poi-config',negative],'minimum-failure',1)
            invalid=dict(default,minimum=5);negative.write_text(json.dumps(invalid));cli(['--world-plan','--poi-config',negative],'invalid-policy',1)
            excluded=copy.deepcopy(raw);excluded['placement']['rotations']=[0];excluded_path=temp/'excluded.json';excluded_path.write_text(json.dumps(excluded))
            cli([excluded_path,'--assigned-site','E'],'transform-exclusion',1)
            cli([draft,'--planned','--category','wilderness','--context','grid'],'wrong-context',1)
            cli(['--check-editor-catalog'],'editor-catalog')
            assert draft.read_bytes()==before
        report=dict(passed=True,records=records,source=source,source_stable=source==source_manifest())
    except Exception as error:report=dict(passed=False,error=str(error),records=records,source=source,source_stable=source==source_manifest())
    (out/'commands.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('passed','source_stable','error') if k in report}))
    return 0 if report['passed'] and report['source_stable'] else 1


if __name__=='__main__':raise SystemExit(main())
