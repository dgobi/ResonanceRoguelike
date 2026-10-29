"""Bounded controlled policy injection; never persist selection or inspect saves."""
import contextlib,hashlib,io,json,sys
from pathlib import Path
root=Path(sys.argv[1]);source=root/sys.argv[2];out=Path(sys.argv[3])
sys.path.insert(0,str(root/'roguelike'))
from engine.data_loader import DataLoader
from generation.plan_preview import planned_preview
from generation.context import GenerationError
raw=json.loads(source.read_bytes());attempts=[]
with contextlib.redirect_stdout(io.StringIO()):data=DataLoader(str(root/'roguelike/data'))
before=json.dumps(data.settlement_profiles,sort_keys=True)
for seed in range(20261029,20261037):
    try:
        with contextlib.redirect_stdout(io.StringIO()):report=planned_preview(data,seed,raw,category='residential',context='grid',role='residential')
        assert json.dumps(data.settlement_profiles,sort_keys=True)==before
        selected=[p for p in report['plan']['placements'] if p['asset']==raw['id']]
        assert selected and report['previews']
        candidate_receipts=[r for scene in report['previews'] for r in scene['receipts'] if any(r['record_id'].startswith(p['id']+':') for p in selected)]
        assert len(candidate_receipts)==len(selected)*len(raw['special_tiles'])
        assert all(r['objects'] for r in candidate_receipts if r['kind'] in ('item','container','scene'))
        assert any(r.get('item_id')=='wood_bundle' and r.get('text_id')=='world_graffiti_a' and r['objects'][0]['item_id']!='wood_bundle' for r in candidate_receipts)
        assert any(r['kind']=='container' and r.get('loot_pools')==['workshop_b_fuel'] and r['objects'][0]['items'][0]['item_id']=='wood_bundle' for r in candidate_receipts)
        result=dict(passed=True,source=sys.argv[2],source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),seed=seed,attempts=attempts,
            scope='Existing planned_preview with disposable in-memory grid/residential policy injection; preserves unrelated candidates. No registration, expedition or frequency claim.',
            plan_identity=report['plan_identity'],planning_seconds=report['planning_seconds'],selected=selected,
            scenes=[dict(chunk=p['chunk'],placements=p['placements'],receipts=p['receipts'],containers=p['containers'],items=p['items']) for p in report['previews']],
            candidate_receipts=candidate_receipts,preserved_installed_policy=True)
        out.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(dict(passed=True,seed=seed,selected=len(selected))));break
    except GenerationError as error:attempts.append(dict(seed=seed,error=str(error)))
else:
    out.write_text(json.dumps(dict(passed=False,attempts=attempts)),encoding='utf-8');raise SystemExit('No fitting candidate within eight bounded seeds')
