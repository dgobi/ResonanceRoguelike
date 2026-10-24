"""Executed on untouched G5: real boot, visited mutation, checkpoint bytes."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'roguelike'), str(ROOT/'tools'), str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
from test_generation_g3_lifecycle import G3Lifecycle
from generation.placement import digest
from generation.world_plan import address
from g1_support import fingerprint
import gzip

out = Path(__file__).resolve().parent
case = G3Lifecycle()
case.setUp()
try:
    e = case.boot()
    assert e.world_map.plan['version'] == 3
    plan = e.world_map.plan
    supplied = json.loads(gzip.decompress((ROOT/'.codex-review/g6-brief/evidence/fixtures/g5_plan_20261023.json.gz').read_bytes()))
    assert digest(plan) == digest(supplied), 'actual G5 JSON value tree differs from independently bound plan'
    placement = next(p for p in plan['placements'] if p['asset']=='house_small_a')
    visited = address(*placement['origin'])[:2]
    m, actors = e._prepare_destination(*visited)
    assert m.generation_revision == 'wg5'
    m.set_tile(2, 2, 'mud', True, True)
    # Explicit fixture mutation; this is not represented as a handler interaction.
    removed = None
    for xy, objects in sorted(m.floor_objects.items()):
        if objects:
            removed = [list(xy), objects.pop().name]
            break
    e.save_manager.cache.store(*visited, m, actors)
    pending = next(tuple(s['members'][0]) for s in plan['settlements'] if tuple(s['members'][0]) != visited)
    assert e.save_manager.cache.load(*pending) is None
    assert e.save_manager.save(e), e.save_manager.last_error
    checkpoint = e.save_manager.checkpoint_path()
    inventory = {}
    with zipfile.ZipFile(out/'authentic-g5-checkpoint.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(checkpoint.rglob('*')):
            if p.is_file():
                name = p.relative_to(checkpoint).as_posix()
                z.write(p, name)
                inventory[name] = dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    (out/'g5-witness.json').write_text(json.dumps(dict(
        source_commit='6f255435f567b99f172e20c38ca2e2d660ff629e',
        provenance='Actual untouched G5 production boot/materializer/checkpoint, disposable seed-only startup envelope.',
        seed=20261023, plan_identity=digest(plan), supplied_plan_equal=True,
        visited=list(visited), pending=list(pending), removed_floor_object=removed,
        visited_fingerprint=fingerprint(m, actors), revision=m.generation_revision,
        adapter=m.plan_provenance['adapter'], inventory=inventory), indent=2)+'\n')
finally:
    case.doCleanups()
