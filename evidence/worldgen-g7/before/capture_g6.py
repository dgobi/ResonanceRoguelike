"""Run once on unmodified G6; fixture actions are not player interactions."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'tools/critical_fix_regressions'),
               str(ROOT/'tools/critical_fix_regressions/tests'), str(ROOT/'roguelike')]
from b1_support import hashes
from verify_b3 import source_manifest
from test_generation_g3_lifecycle import G3Lifecycle
from generation.placement import digest
from g1_support import fingerprint

out = Path(os.environ['RESONANCE_TEST_EVIDENCE_DIR'])
fixture = ROOT/'tools/critical_fix_regressions/fixtures/g7'
fixture.mkdir(parents=True, exist_ok=True)
case = G3Lifecycle(); case.root = out/'saves'; case.root.mkdir()
source = source_manifest()
with patch('engine.save_manager.SAVE_DIR', case.root):
    e = case.boot()
    assert e.world_map.plan['version'] == 4
    sites = e.world_map.plan['sites']; visited, pending = sites[:2]
    xy = visited['chunk']; m, actors = e._prepare_destination(*xy)
    target = next(iter(m.container_state))
    state = m.container_state[target]; before = len(state['items'])
    taken = state['items'].pop(); e.player.inventory.add(taken)
    m.set_tile(2, 2, 'mud', True, True)
    e.save_manager.cache.store(*xy, m, actors)
    assert e.save_manager.cache.load(*pending['chunk']) is None
    assert e.save_manager.save(e), e.save_manager.last_error
    checkpoint = e.save_manager.checkpoint_path()
    plan_bytes = json.dumps(e.world_map.plan, sort_keys=True, separators=(',', ':')).encode()
    with gzip.GzipFile(filename=str(fixture/'g6_plan_20261023.json.gz'), mode='wb', mtime=0) as f:
        f.write(plan_bytes)
    with zipfile.ZipFile(fixture/'authentic-g6-checkpoint.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(checkpoint.rglob('*')):
            if path.is_file(): z.write(path, path.relative_to(checkpoint).as_posix())
    record = dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        command=sys.argv, interpreter=sys.executable, source=source,
        plan_identity=digest(e.world_map.plan), plan_version=4, visited=xy, pending=pending['chunk'],
        visited_site=visited['id'], pending_site=pending['id'],
        visited_fingerprint=fingerprint(m, actors), visited_provenance=m.plan_provenance,
        visited_revision=m.generation_revision,
        mutation=dict(kind='direct fixture mutation; not a player interaction', tile=[2,2,'mud'],
                      container=list(target), before=before, after=len(state['items']), taken=taken.item_id),
        checkpoint=hashes(checkpoint), fixture=hashes(fixture))
    (fixture/'g6-witness.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    (out/'capture.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:record[k] for k in ('source_commit','plan_identity','visited','pending','mutation')},indent=2))
