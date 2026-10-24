"""Consume actual browser download bytes on controlled vertical town frontage."""
import json
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
    return records
