"""Capture B2's two B3 defects in production main before implementation."""
from pathlib import Path
import os
import sys
import hashlib
from b1_support import ENV, Evidence, boot, dump, hashes, SEED

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / '.baseline/b3-20261023/before'
RUN.mkdir(parents=True, exist_ok=False)
os.environ.update(ENV)
sys.path.insert(0, str(ROOT / 'roguelike'))
os.chdir(ROOT / 'roguelike')
import engine.save_manager as sm
sm.SAVE_DIR = RUN / 'saves'
slot = sm.SAVE_DIR / 'slot_0'
slot.mkdir(parents=True)
dump(slot / 'world.json', {'seed': SEED})
ev = Evidence(dict(run_id='b3-before', scenario='coherence', phase='before', flavor='before'))

def probe(e):
    from world.local_map import LocalMap
    e._ascend_from_submap()
    e.entities = [e.player]
    e.local_map.set_tile(3, 3, 'grass', True, True)
    e.save_manager.save(e)
    saved = hashes(slot)
    e.local_map.set_tile(3, 3, 'dirt', True, True)
    e._descend_to_submap(e.world_map.get(e.world_x, e.world_y).submaps[0].submap_id)
    ev.check('before', 'stairs alter persisted checkpoint', True, hashes(slot) != saved)
    ev.check('before', 'load completes', True, e.save_manager.load(e))
    ev.check('before', 'checkpoint overwritten by later travel', 'dirt', str(e.local_map.tiles[3, 3]['terrain']))
    other = LocalMap(80, 43)
    other.set_tile(3, 3, 'grass', True, True)
    wx, wy = e.world_x+1, e.world_y
    e.save_manager.cache.store(wx, wy, other, [])
    other.set_tile(3, 3, 'mud', True, True)
    e.save_manager.cache.store_hot_only(wx, wy, other, [])
    e.save_manager.save(e)
    cold = sm.ChunkCache(slot).load(wx, wy)
    ev.check('before', 'dirty inactive checkpoint loses hot change', 'grass', str(cold.local_map.tiles[3, 3]['terrain']))
    ev.record['legacy_checkpoint'] = hashes(slot)

boot(probe, ev)
ev.bind_sources(ROOT / 'roguelike')
ev.record['completed'] = ev.record['passed'] = True
ev.record['source'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                       for base in ('roguelike', 'tools') for p in (ROOT / base).rglob('*.py')
                       if '__pycache__' not in p.parts and 'saves' not in p.parts}
dump(RUN / 'result.json', ev.record)
print('B3 before: both defects reproduced; actual B2 legacy checkpoint retained in disposable root.')
