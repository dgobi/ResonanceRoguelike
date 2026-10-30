"""Supplemental actual-loop rendering of the already verified cold revisit.

No source/actor/item/terrain changes, no game action, and no world phase.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
import config
config.DEBUG_MODE=False
from g12_journey import run_stage
from verify_g21_play import ledger
archive=ROOT/'evidence/gameplay-g21/final-c/play/revisit/revisited.zip'
def actions(e,key,capture,choose,ev,out):
    turn=e.world_time.turn
    assert e.current_submap_id=='g21-rival-room'
    assert not any(i.source_creature=='heath_stalker' for rows in e.local_map.floor_objects.values() for i in rows)
    assert any(i.item_id=='stalker_meat' for rows in e.local_map.floor_objects.values() for i in rows)
    ev.record.update(controls='Separate-process ordinary cold load of final-c revisited.zip; allow a free original-loop render before capture. No new action, world phase, resource, actor, location or terrain staging. Supplements the prior capture made before the direct return method had rendered.',head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),checkpoint_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),state=ledger(e))
    yield None
    capture('cold-revisit-rendered')
    assert e.world_time.turn==turn
    ev.record.update(completion=True,world_phases=0)
r=run_stage(Path(__file__).resolve().parent,'rendered-cold-revisit',actions,archive,max_frames=10,max_seconds=60,max_turns=1)
assert r['passed']
print(json.dumps(dict(passed=True,head=r['head'],world_phases=r['world_phases'])))
