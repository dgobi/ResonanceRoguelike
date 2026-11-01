"""Controlled real-consumer scheduling proof; no alternate movement simulator."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
from test_ai_2 import ObservationTests
from engine.save_manager import _serialize_entity, _deserialize_entities


def main():
    fixture=ObservationTests()
    fixture.setUpClass();fixture.setUp()
    try:
        e=fixture.e
        a=fixture.actor(x=19)
        e.data.entities[a._creature_id]['speed']=2
        fixture.tick()  # real scheduler: exactly two ordinary opportunities
        fast=copy.deepcopy(a.ai.trace)
        assert a.x==16 and a.ai.opportunities==2
        assert [len(r['steps']) for r in fast]==[2,1]
        assert all(not step['observed'] for r in fast for step in r['steps'])
        assert a.ai.bonus_phase==e.world_time.turn==0
        saved=_serialize_entity(a)
        restored=_deserialize_entities([saved],e)[0]
        assert restored.ai.snapshot()==a.ai.snapshot()
        e.entities=[e.player,restored]
        # Disclosed current-weather fixture keeps a later normal step unseen too.
        # Rearming exposure patience must not rearm the spent movement allowance.
        e.weather=copy.copy(e.weather)
        e.weather.get_mechanic=lambda key,default=None:1 if key=='fov_cap' else default
        fixture.decision(restored)
        after=copy.deepcopy(restored.ai.trace[-1])
        assert restored.x==15 and len(after['steps'])==1
        assert not after['steps'][0]['observed']
        assert restored.ai.bonus_phase==0
        inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            ROOT/'roguelike/engine/ai_system.py',ROOT/'roguelike/components/observation_averse.py',
            ROOT/'roguelike/components/composite_ai.py',ROOT/'roguelike/engine/ai_profiles.py',
            ROOT/'roguelike/engine/save_manager.py',ROOT/'tools/critical_fix_regressions/tests/test_ai_2.py']}
        result=dict(passed=True,setup=__doc__,initial_x=19,fast_final_x=16,
            fast_ordinary_opportunities=2,fast_steps=3,all_fast_steps_unseen=True,
            fast=fast,same_phase_restore_normal_step_unseen=True,after_restore=after,
            saved_spent_phase=saved['composite']['state']['bonus_phase'],inputs=inputs)
        Path(__file__).with_name('scheduling.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(passed=True,fast_steps=3,ordinary_opportunities=2,same_phase_restored_steps=1)))
    finally:
        fixture.doCleanups()


if __name__=='__main__':main()
