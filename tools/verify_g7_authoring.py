"""Execute all six G7 owner workflows in disposable draft/data directories."""
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True);source=source_manifest();records=[]
    env={k:os.environ[k] for k in ('PYTHONPATH','PYTHONHASHSEED','SDL_VIDEODRIVER','SDL_AUDIODRIVER') if k in os.environ}
    def run(command,expected=0,outputs=(),workflow=None):
        argv=list(map(str,command));result=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=300)
        row=dict(workflow=workflow,argv=argv,cwd=str(ROOT),environment=env,expected_exit=expected,exit_code=result.returncode,expected_negative=expected!=0,
                 stdout=result.stdout,stderr=result.stderr,outputs={str(p):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in outputs if p.exists()})
        records.append(row)
        if result.returncode!=expected:raise AssertionError(result.stdout+result.stderr)
        return row
    def cli(arguments,name,expected=0,workflow=None):
        output=out/(name+'.json');run([sys.executable,'-X','utf8',ROOT/'tools/structure_authoring.py',*arguments,'--output',output],expected,[output],workflow)
        return json.loads(output.read_text()) if output.exists() else None
    def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    try:
        run([sys.executable,'-X','utf8',ROOT/'tools/verify_g6_authoring.py','--evidence',out/'inherited-g6'],workflow='inherited G6/G5 workflows; nested counts retained separately')
        with tempfile.TemporaryDirectory(prefix='g7-authoring-') as temporary:
            temp=Path(temporary);drafts=temp/'drafts'
            cli(['--init-compound',drafts],'init',workflow=1)
            child=drafts/'g7_wayhouse.json';recipe=drafts/'g7_travellers_court.json';policy=drafts/'g7_poi_example.json'
            raw=json.loads(child.read_text());raw['owner_sentinel']='G7 edited child survives repeated initialization';write(child,raw)
            before={p.name:p.read_bytes() for p in drafts.iterdir()}
            for i in range(2):cli(['--init-compound',drafts],f'init-repeat-{i}',workflow=1)
            assert before=={p.name:p.read_bytes() for p in drafts.iterdir()}
            records.append(dict(workflow=1,action='sentinel and all draft bytes preserved across two repeated initializations',hashes={k:hashlib.sha256(v).hexdigest() for k,v in before.items()}))
            cli([child,'--route','ordinary_building','--category','wilderness','--orientations'],'child-direct',workflow=2)
            for normal in 'SE':cli(['--compound',recipe,'--child',child,'--assigned-compound',normal],'whole-'+normal,workflow=3)
            cli(['--compound',recipe,'--child',child,'--poi-config',policy],'ordinary-draft',workflow=3)
            zero=json.loads(policy.read_text());zero.update(minimum=0,maximum=0,kind_minimum=dict(single=0,compound=0));zero_path=temp/'zero.json';write(zero_path,zero)
            result=cli(['--compound',recipe,'--child',child,'--poi-config',zero_path],'valid-unselected',workflow=3)
            assert result['status']=='valid but unselected' and result['materialized_scenes']==0
            catalog=temp/'data';shutil.copytree(ROOT/'roguelike/data',catalog)
            for src,dst in [(child,catalog/'buildings/wilderness/g7_wayhouse.json'),(recipe,catalog/'generation/compounds/g7_travellers_court.json'),(policy,catalog/'generation/poi_profiles.json')]:shutil.copyfile(src,dst)
            records.append(dict(workflow=4,action='deliberate installation in disposable data catalog; no alternate game checkout',files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (child,recipe,policy)}))
            cli(['--data-root',catalog,'--catalog'],'installed-catalog',workflow=4)
            editor=temp/'catalog.js';cli(['--data-root',catalog,'--refresh-editor-catalog','--editor-catalog',editor],'refresh-disposable-editor',workflow=4)
            cli(['--data-root',catalog,'--check-editor-catalog','--editor-catalog',editor],'check-disposable-editor',workflow=4)
            cli(['--data-root',catalog,'--world-plan'],'installed-world',workflow=4)
            altered=temp/'altered-recipe.json';base=json.loads(recipe.read_text())
            replaced=copy.deepcopy(base);replaced['slots'][1]['assets']=[dict(asset='roadside_shrine_a',weight=1)];write(altered,replaced)
            cli(['--compound',altered,'--assigned-compound','S'],'replaced-child',workflow=5)
            yard=json.loads((ROOT/'roguelike/data/generation/compounds/homestead_workyard.json').read_text());optional=yard['slots'].pop();write(altered,yard)
            cli(['--compound',altered,'--assigned-compound','S'],'two-building-yard',workflow=5)
            yard['slots'].append(optional);write(altered,yard);expanded=cli(['--compound',altered,'--assigned-compound','S'],'third-building-yard',workflow=5)
            assert all(s['placement'] for s in expanded['plan']['sites'][0]['slots'])
            resized=copy.deepcopy(base);resized['paths'][0]['rects']=[[2,8,17,14]];resized['rotations']=[90];write(altered,resized)
            cli(['--compound',altered,'--child',child,'--assigned-compound','W','--compound-rotation','90'],'path-and-orientation',workflow=5)
            tuned=json.loads(policy.read_text());tuned.update(minimum=3,maximum=4,repeat_multiplier=.1);tuned['choices'][-1].update(weight=8,cap=1);tuned_path=temp/'tuned.json';write(tuned_path,tuned)
            cli(['--compound',recipe,'--child',child,'--poi-config',tuned_path],'tuned-parent-policy',workflow=5)
            negatives=[('unknown-child',lambda r:r['slots'][0]['assets'][0].update(asset='unknown-child')),
                ('disconnected-gate',lambda r:r['gate'].update(x=0,y=0,normal='N',width=1)),
                ('private-overlap',lambda r:r['slots'][1].update(buildable=r['slots'][0]['buildable'])),
                ('out-of-envelope',lambda r:r['slots'][0].update(buildable=[-1,0,8,8])),
                ('forbidden-effective-transform',lambda r:r['slots'][0].update(assets=[dict(asset='house_hearth_a',weight=1)])),
                ('required-child-failure',lambda r:r['slots'][0].update(buildable=[0,0,2,2]))]
            for name,change in negatives:
                failed=copy.deepcopy(base);change(failed);write(altered,failed)
                cli(['--compound',altered,'--child',child,'--assigned-compound','S'],name,1,6)
            no_goal=copy.deepcopy(raw)
            for target in no_goal['placement']['targets']:target['required']=False
            bad_child=temp/'no-goal.json';write(bad_child,no_goal)
            cli(['--compound',recipe,'--child',bad_child,'--assigned-compound','S'],'missing-required-goal',1,6)
            blocked=copy.deepcopy(raw);blocked['special_tiles'].append(dict(type='container',x=2,y=4,decor_id='crate',loot_pools=['storage_general']));bad_child=temp/'blocked-door.json';write(bad_child,blocked)
            cli(['--compound',recipe,'--child',bad_child,'--assigned-compound','S'],'blocked-final-door',1,6)
            exhausted=json.loads(policy.read_text());exhausted['fit_budget']=1;write(tuned_path,exhausted)
            cli(['--compound',recipe,'--child',child,'--assigned-compound','S','--poi-config',tuned_path],'budget-exhaustion',1,6)
            yard['slots'][2]['buildable']=[27,0,44,2];write(altered,yard)
            omitted=cli(['--compound',altered,'--assigned-compound','S'],'valid-optional-omission',workflow=6)
            assert omitted['plan']['sites'][0]['slots'][2]['placement'] is None
            assert before=={p.name:p.read_bytes() for p in drafts.iterdir()}
            for path in drafts.iterdir():shutil.copyfile(path,out/path.name)
        report=dict(passed=True,records=records,source=source,source_stable=source==source_manifest(),workflow_ids=[1,2,3,4,5,6],browser_export_evidence='separate both-engine verify_structure_editor gate; actual downloads consumed by direct and assigned-compound previews')
    except Exception as error:report=dict(passed=False,error=str(error),records=records,source=source,source_stable=source==source_manifest())
    (out/'commands.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('passed','source_stable','error') if k in report}))
    return 0 if report['passed'] and report['source_stable'] else 1


if __name__=='__main__':raise SystemExit(main())
