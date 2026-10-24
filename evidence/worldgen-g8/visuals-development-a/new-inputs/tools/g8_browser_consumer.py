"""Consume actual browser download bytes on controlled vertical town frontage."""
import json
import copy
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def consume(download,out,browser):
    raw=json.loads(download.read_text(encoding='utf-8'));policy=json.loads((ROOT/'roguelike/data/generation/settlement_profiles.json').read_text())
    policy['profiles']['grid']['roles']['residential']=[dict(asset=raw['id'],weight=1,max_per_settlement=128)]
    policy['profiles']['grid']['schedule']=['residential','commercial']
    path=out/(browser+'-g8-selection.json');path.write_text(json.dumps(policy,indent=2)+'\n')
    records=[]
    for layout in ('cross-market','linked-courts'):
        output=out/(browser+'-g8-'+layout+'.json')
        argv=[sys.executable,'-X','utf8',str(ROOT/'tools/structure_authoring.py'),str(download),'--planned','--category','residential','--context','grid','--layout',layout,'--selection-config',str(path),'--output',str(output)]
        r=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=120);assert r.returncode==0,r.stdout+r.stderr
        report=json.loads(output.read_text());selected={p['id'] for p in report['plan']['placements'] if p['asset']==raw['id']};normals=sorted({p['normal'] for p in report['plan']['plots'] if p['placement'] in selected})
        assert set(normals)&set('EW'),normals
        records.append(dict(argv=argv,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,layout=layout,actual_download=str(download),normals=normals,materialized_scenes=report['materialized_scenes'],control='residential membership restricted to actual downloaded asset; complete production planner/materializer; no downloaded bytes modified'))
    # Independent assigned-frontage negative: explicitly restrict a COPY of the
    # exported document, then use a real accepted vertical lot from that plan.
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
    from test_effect_persistence import load_data
    from generation.structure_contract import compile_structure
    from generation.world_plan import Reservations,_plot
    restricted=copy.deepcopy(raw);restricted['placement']['rotations']=[0]
    d=load_data();d.structures=dict(d.structures,**{raw['id']:compile_structure(restricted,'ordinary_building',d,category='residential').definition})
    plot=next(p for p in report['plan']['plots'] if p['placement'] in selected and p['normal'] in 'EW');road=next(r for r in report['plan']['routes'] if r['id']==plot['road'])
    plan=dict(version=6,seed=20261023,settings=report['plan']['settings'],plots=[],placements=[],dependencies={},routes=[road]);authority=Reservations()
    for rect in road['rects']:authority.add(road['id'],'road',rect)
    lot=dict(id=plot['id'],owner=plot['owner'],block=plot['block'],bounds=plot['buildable'],join=plot['join'],frontage=plot['frontage'],civic=plot['civic_lot']);wx,wy=lot['bounds'][0]//80,lot['bounds'][1]//43
    failed=_plot(plan,authority,d,plot['owner'],'grid',wx,wy,plot['join'][0]-wx*80,plot['join'][1],plot['normal'],plot['road'],weighted_rows=[(raw['id'],1)],identity=plot['id'],explicit_bounds=lot['bounds'],lot=lot)
    assert failed['placement'] is None and any('no eligible permitted transform' in r['reason'] for r in failed['rejected']),failed
    records.append(dict(control='explicit copy of actual downloaded building restricted to rotation 0; original download unchanged',assigned_normal=plot['normal'],rejections=failed['rejected'],required_rotation_excluded=True))
    return records
