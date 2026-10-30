"""Short G19 original-loop demonstration; staged fixtures, disposable saves only."""
import argparse
import inspect
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def journey(out):
    import pygame
    import components.ai as ai
    from b1_support import Evidence
    from b1_journey import run_journey
    from test_gameplay_g19 import physical
    job=dict(run_id='g19-local-demo',scenario='journey',phase='loop',flavor='candidate',
             variant='g19',result=str(out/'journey.json'))
    ev=Evidence(job)
    ev.record['controls']=(
        'Stage a clear laboratory patch, cover and wall, a Revenant seven tiles away with '
        'wander_radius=0/home fixed (perception and pursuit remain active), and a factory Lurker '
        'at distance three behind the wall. Use fixed combat RNG, ordinary keys and real '
        'AI/combat/turns/save/load/renderer. Later stage one pending Press step and move the '
        'already-awake Lurker into legal contact to isolate its bonus from its normal budget. '
        'Cold pending continuation isolates Lurker normal AI while proving blocked retention '
        'then one legal miss consumes the bonus. No acquisition, frequency, balance or expedition claim.')
    with tempfile.TemporaryDirectory(prefix='resonance-g19-loop-') as root, patch('engine.save_manager.SAVE_DIR',Path(root)):
        slot=Path(root)/'slot_0'; slot.mkdir(); (slot/'world.json').write_text('{"seed":20261023}')

        def observe(e,label):
            ev.record.setdefault('states',[]).append(dict(label=label,**physical(e)))

        def visible(e,actor):
            return ai._creature_can_see_player(actor,e.player,e.local_map,1,engine=e)

        def cold(e,label):
            proc=subprocess.run([sys.executable,'-X','utf8',
                str(ROOT/'tools/critical_fix_regressions/tests/test_gameplay_g19.py'),'--cold',root],
                capture_output=True,text=True,timeout=45,env=dict(os.environ))
            assert proc.returncode==0,proc.stdout+proc.stderr
            actual=json.loads(proc.stdout.strip().splitlines()[-1])
            ev.check('G19',label+' cold snapshot without replay',physical(e),actual)
            ev.record.setdefault('cold',{})[label]=actual

        def actions(e,key,capture,choose):
            e.entities=[e.player]; e.player.x,e.player.y=12,11; e.rng=random.Random(29417)
            for x in range(10,22):
                for y in range(10,17):
                    e.local_map.set_tile(x,y,'flagstone',True,True)
                    e.local_map.decor.pop((x,y),None); e.local_map.container_state.pop((x,y),None)
            e.local_map.set_tile(12,12,'tall_grass',True,True)
            e.local_map.set_tile(12,14,'wall',False,False)
            observer=e.creature_factory.spawn('hollow_revenant',19,12)
            observer.ai.wander_radius=0; observer.ai.set_home(19,12)
            lurker=e.creature_factory.spawn('stone_lurker',12,15)
            e.entities += [observer,lurker]; e._update_fov()
            before=e.world_time.turn; hp=e.player.fighter.hp
            yield key(pygame.K_DOWN)
            ev.check('G19','enter cover applies real terrain surcharge',2,e.world_time.turn-before)
            ev.check('G19','cover hides at fixed distance',False,visible(e,observer))
            ev.check('G19','wake at three retains pending without remote damage',
                     [False,True,False,hp],[lurker._hibernating,lurker._ambush_ready,lurker.ai._triggered,e.player.fighter.hp])
            before=e.world_time.turn
            for _ in range(2): yield key(pygame.K_z,'z')
            ev.check('G19','two waits pay while cover persists',[before+2,False,hp],
                     [e.world_time.turn,visible(e,observer),e.player.fighter.hp])
            observe(e,'entered cover and waited twice'); capture('cover-waits-pending-lurker')
            before=e.world_time.turn
            yield key(pygame.K_x,'x'); yield key(pygame.K_ESCAPE)
            yield key(pygame.K_i,'i'); yield key(pygame.K_i,'i')
            yield key(e.display.MOVESET_KEY_1,'q'); yield key(pygame.K_F5)
            ev.check('G19','inspect inventory rejection save stay free in cover',
                     [before,False],[e.world_time.turn,visible(e,observer)])
            saved=physical(e); cold(e,'covered-pending')
            e._free_move_pending=True  # disclosed staged G18 opportunity
            yield key(pygame.K_RIGHT)
            ev.check('G19','free Press step exits cover immediately',[before,False,True],
                     [e.world_time.turn,e._free_move_pending,visible(e,observer)])
            observe(e,'free step exposed without AI phase'); capture('free-step-exposed')
            yield key(pygame.K_F9)
            ev.check('G19','F9 after divergent movement restores physical checkpoint',saved,physical(e))
            observer=next(a for a in e.entities if getattr(a,'_creature_id','')=='hollow_revenant')
            lurker=next(a for a in e.entities if getattr(a,'_creature_id','')=='stone_lurker')
            lurker.x,lurker.y=13,12; e.local_map.set_tile(13,12,'flagstone',True,True)
            calls=[]; original=ai._monster_attack_entity
            def observed(*args,**kwargs):
                caller=inspect.currentframe().f_back.f_code.co_name
                committed=original(*args,**kwargs)
                calls.append(dict(caller=caller,committed=committed))
                return committed
            with patch.object(ai,'_monster_attack_entity',new=observed):
                yield key(pygame.K_z,'z')
                ev.check('G19','legal bonus consumed',False,lurker._ambush_ready)
                yield key(pygame.K_z,'z')
            ev.check('G19','single bonus separately from one normal action',
                     ['process','_attack'],[row['caller'] for row in calls if row['committed']])
            ev.record['attack_callers']=calls
            observe(e,'legal bonus then normal budget'); capture('legal-ambush-consumed')
            yield key(pygame.K_F5); cold(e,'covered-consumed')
            ev.record['completion']=True

        old=Path.cwd(); started=time.monotonic()
        try:
            os.chdir(ROOT/'roguelike')
            run_journey(ev,actions,max_frames=60,max_seconds=90,max_turns=30)
            ev.bind_sources(ROOT/'roguelike')
            ev.record.update(passed=True,elapsed_seconds=time.monotonic()-started)
        finally:
            os.chdir(old); (out/'journey.json').write_text(json.dumps(ev.record,indent=2)+'\n')
    return ev.record


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--evidence',type=Path,required=True); a=p.parse_args()
    assert sys.platform=='win32' and sys.version_info[:2]==(3,11),'Use production Windows/Python 3.11'
    out=a.evidence.resolve(); out.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
    from b1_support import ENV
    os.environ.update(ENV)
    os.environ['PYTHONPATH']=os.pathsep.join([str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')])
    import config
    config.DEBUG_MODE=False
    result=journey(out)
    print(json.dumps(dict(passed=result['passed'],seconds=result['elapsed_seconds'],checks=len(result['checks']))))


if __name__=='__main__': main()
