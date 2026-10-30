"""Supplement: genuinely archived G16 null-handler shard, normal owned use.

This review artifact is outside covered source. Frozen runtime and this artifact
are independently hashed; no historical archive, campaign or game source changes.
"""
from pathlib import Path
import contextlib, hashlib, json, os, sys, time

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent/'historical-flint'
ARCHIVE=ROOT/'evidence/gameplay-g16/final-a/journey/cold-return/homeward/returned-pellet.zip'
sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
import config
config.DEBUG_MODE=False
from g12_journey import run_stage,interact,select_prompt,inventory,archive_checkpoint
from g16_journey import approach,close
from g20_journey import aim
from engine.save_components import serialize_item
from engine.effect_lifecycle import valid_throw
import pygame

frozen=json.loads((OUT.parent/'inputs.json').read_text())
def stable():return all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in frozen['source'].items())
assert stable()
original=None
def acquire(e,key,capture,choose,ev,out):
    global original
    assert e.current_submap_id=='sub_73_99_0'
    source=(26,17)
    shard=next(i for i in e.local_map.container_state[source]['items'] if i.item_id=='flint_shard')
    assert shard.on_use is None
    original=serialize_item(shard)
    ev.record.update(controls='Genuine immutable G16 archive. Archived laboratory crate shard, normal app-local reach/take, no inserted item or actor/needs/HP/fuel edits. Separate owned save then a separate process-style Engine cold load. Full-state row/target choice, no discovery or balance claim.',archive_sha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),archived_item=original,start_turn=e.world_time.turn)
    yield from approach(e,source,key)
    yield from interact(e,source,key)
    yield from select_prompt(e,'flint_shard',key)
    yield from close(e,key)
    assert e.player.inventory.contains(shard) and serialize_item(shard)==original
    yield key(pygame.K_F5)
    ev.record.update(checkpoint=str(archive_checkpoint(e,out,'owned-old-shard')),owned_item=serialize_item(shard),turn=e.world_time.turn,completion=True)

def throw(e,key,capture,choose,ev,out):
    shard=e.player.inventory.get_by_id('flint_shard')
    assert shard and shard.on_use is None and serialize_item(shard)==original
    before=e.world_time.turn
    yield from inventory(e,shard,key,choose)
    assert e._pending_throw['item'] is shard and e.world_time.turn==before
    assert serialize_item(shard)==original
    candidates=[(x,y) for x in range(e.local_map.width) for y in range(e.local_map.height) if valid_throw(e,x,y) and (x,y)!=(e.player.x,e.player.y)]
    impact=min(candidates,key=lambda xy:abs(xy[0]-e.player.x)+abs(xy[1]-e.player.y))
    capture('genuinely-restored-old-shard-cursor')
    yield from aim(e,impact,key)
    assert not e.player.inventory.contains(shard) and e.world_time.turn==before+1
    assert shard.on_use is None
    ev.record.update(restored_item=original,free_cursor_preserved_fields=True,impact=list(impact),phases=1,consumed=True,completion=True)
    capture('genuinely-restored-old-shard-thrown')

OUT.mkdir(exist_ok=True)
started=time.perf_counter()
with (OUT/'output.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
    acquired=run_stage(OUT,'acquire',acquire,ARCHIVE,max_frames=300,max_seconds=100,max_turns=100)
    thrown=run_stage(OUT,'throw',throw,Path(acquired['checkpoint']),max_frames=100,max_seconds=100,max_turns=5)
assert stable()
receipt=dict(passed=True,tested_revision=frozen['head'],source_stable=True,artifact_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),archive=str(ARCHIVE.relative_to(ROOT)),archive_sha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),item=original,acquire_turns=acquired['turn']-acquired['start_turn'],throw_phases=thrown['phases'],seconds=time.perf_counter()-started,scope='Archived old physical shard acquired through ordinary container UI, saved as owned, then cold-restored and used with no stored handler mutation. Existing controlled stack fixture covers count and explicit override separately.')
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
