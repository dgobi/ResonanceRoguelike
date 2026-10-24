"""Six G8 workflows plus inherited G5-G7 workflows, counted separately."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True);records=[]
    def run(argv,expected=0,workflow=None):
        argv=list(map(str,argv));r=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=900)
        records.append(dict(workflow=workflow,argv=argv,cwd=str(ROOT),exit_code=r.returncode,expected_exit=expected,expected_negative=expected!=0,stdout=r.stdout,stderr=r.stderr));assert r.returncode==expected,r.stdout+r.stderr
    def cli(args,name,expected=0,workflow=None):
        f=out/(name+'.json');run([sys.executable,'-X','utf8',ROOT/'tools/structure_authoring.py',*args,'--output',f],expected,workflow);return json.loads(f.read_text()) if f.exists() else None
    def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
    try:
        run([sys.executable,'-X','utf8',ROOT/'tools/verify_g7_authoring.py','--evidence',out/'inherited-g7'],workflow='inherited; nested counts are separate')
        folder=ROOT/'.baseline/g8-authoring';folder.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as temporary:
            temp=Path(temporary);draft=temp/'drafts';cli(['--init-settlement',draft],'init',workflow=1)
            layout=draft/'g8_layouts.json';selection=draft/'g8_selection.json';config=draft/'g8_planning.json';raw=json.loads(layout.read_text());raw['grid'][0]['weight']=2;write(layout,raw)
            before={p.name:p.read_bytes() for p in draft.iterdir()}
            for n in range(2):cli(['--init-settlement',draft],f'init-repeat-{n}',workflow=1)
            assert before=={p.name:p.read_bytes() for p in draft.iterdir()}
            records.append(dict(workflow=1,preserved_hashes={k:hashlib.sha256(v).hexdigest() for k,v in before.items()}))
            for name in ('cross-market','linked-courts'):
                result=cli(['--layout-config',layout,'--layout',name,'--settlement-preview','grid'],name,workflow=2);assert len(result['previews'])>=4
            result=cli(['--layout-config',layout,'--settlement-preview','roadside'],'roadside',workflow=2);assert len(result['previews'])>=2
            edited=copy.deepcopy(raw);street=next(r for r in edited['grid'][0]['streets'] if r['id']=='north-south-1')
            for point in street['points']:point[0]+=2
            write(layout,edited);cli(['--layout-config',layout,'--layout',edited['grid'][0]['id'],'--settlement-preview','grid'],'geometry-edit',workflow=3)
            tuned=json.loads(selection.read_text());tuned['profiles']['grid']['schedule']=['residential','commercial'];tuned['profiles']['grid']['repeat_multiplier']=0.1;write(selection,tuned)
            for name in ('cross-market','linked-courts'):
                result=cli(['--layout-config',layout,'--selection-config',selection,'--layout',name,'--settlement-preview','grid'],'tuned-'+name,workflow=4)
                s=result['plan']['settlements'][0];assert {p['normal'] for p in result['plan']['plots'] if p['owner']==s['id'] and p['placement']}==set('NESW')
            broken=copy.deepcopy(raw)
            for l in broken['grid']:l['civic_lot']['bounds'][2]=l['civic_lot']['bounds'][0]+4
            bad=temp/'too-small-civic.json';write(bad,broken);cli(['--layout-config',bad,'--settlement-preview','grid'],'required-no-fit',1,5)
            prior=layout.read_bytes();run([sys.executable,'-X','utf8',ROOT/'tools/structure_authoring.py','--layout-config',layout,'--settlement-preview','grid','--output',layout],1,5);assert layout.read_bytes()==prior
            # Derived diagram alias must fail before any catalog refresh or draft writes.
            linked=out/'collision-settlement-0-plan.svg';linked.hardlink_to(layout)
            run([sys.executable,'-X','utf8',ROOT/'tools/structure_authoring.py','--layout-config',layout,'--settlement-preview','grid','--output',out/'collision.json'],1,5)
            assert layout.read_bytes()==prior and not (out/'collision.json').exists();linked.unlink()
            absent=temp/'fresh';run([sys.executable,'-X','utf8',ROOT/'tools/structure_authoring.py','--init-settlement',absent,'--output',absent/'g8_layouts.json'],1,5);assert not absent.exists()
            installed=temp/'data';shutil.copytree(ROOT/'roguelike/data',installed)
            for src,name in [(layout,'settlement_layouts.json'),(selection,'settlement_profiles.json'),(config,'g3_config.json')]:shutil.copyfile(src,installed/'generation'/name)
            cli(['--data-root',installed,'--settlement-preview','all'],'installed-complete',workflow=6)
            catalog=temp/'catalog.js';cli(['--data-root',installed,'--refresh-editor-catalog','--editor-catalog',catalog],'refresh',workflow=6);cli(['--data-root',installed,'--check-editor-catalog','--editor-catalog',catalog],'check',workflow=6)
            for path in draft.iterdir():shutil.copyfile(path,out/path.name)
        passed=True;error=None
    except Exception as exc:passed=False;error=str(exc)
    (out/'workflows.json').write_text(json.dumps(dict(passed=passed,error=error,g8_top_level_workflows=6,inherited='G7 six workflows with its G6/G5 subruns; do not sum nested counts',records=records),indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=passed,error=error)));return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
