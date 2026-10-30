"""G18 disclosed ordinary-input demonstration in the original headless game loop."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def journey(out):
    import pygame
    from b1_support import Evidence
    from b1_journey import run_journey
    from g12_journey import inventory, archive_checkpoint
    from test_gameplay_g18 import timing
    from engine.save_manager import _serialize_entity

    job = dict(run_id='g18-local-demo',scenario='journey',phase='loop',flavor='candidate',
               variant='g18',result=str(out/'journey.json'))
    ev = Evidence(job)
    ev.record['controls'] = (
        'Disposable original-loop laboratory fixture, not acquisition/discovery or an expedition. '
        'Stage a clear local patch, player at (12,12) with 25 HP, two factory weapons in inventory, '
        'one durable Revenant with fixture AI disabled and one wounded 1-HP Press target. '
        'Move the durable target away before staging the Press target. Equipment uses real inventory events. '
        'Weapon definitions, combat resolver, cooldowns, phase systems, save/load and rendering remain real. '
        'Cold arithmetic continuation suppresses only AI processing, since factory reload restores AI; '
        'all cooldown waits are paid with ordinary input. No cooldown clearing or invincibility.')

    with tempfile.TemporaryDirectory(prefix='resonance-g18-loop-') as root, patch('engine.save_manager.SAVE_DIR',Path(root)):
        slot = Path(root)/'slot_0'; slot.mkdir(); (slot/'world.json').write_text('{"seed":20261023}')

        def observe(e, label):
            ev.record.setdefault('timing_trace',[]).append(dict(label=label,state=timing(e),
                position=[e.player.x,e.player.y],cooldowns=dict(e.moveset_cooldowns),hp=e.player.fighter.hp))

        def cold_check(e, label, steps):
            result = subprocess.run([sys.executable,'-X','utf8',
                str(ROOT/'tools/critical_fix_regressions/tests/test_gameplay_g18.py'),
                '--cold',root,str(steps)],capture_output=True,text=True,timeout=60,env=dict(os.environ))
            assert result.returncode==0,result.stdout+result.stderr
            actual = json.loads(result.stdout.strip().splitlines()[-1])
            ev.record.setdefault('cold',{})[label] = actual
            ev.check('G18',label+' cold timing',timing(e),actual['initial'])
            return actual

        def actions(e,key,capture,choose):
            e.entities = [e.player]; e.player.x,e.player.y = 12,12; e.player.fighter.hp = 25
            for x in range(10,19):
                for y in range(10,19):
                    e.local_map.set_tile(x,y,'flagstone',True,True)
                    e.local_map.decor.pop((x,y),None); e.local_map.container_state.pop((x,y),None)
            e.local_map.set_tile(12,11,'wall',False,False)
            weapons = {}
            for iid in ('crude_blade','heavy_blade'):
                weapons[iid] = e.item_factory.create(iid); assert e.player.inventory.add(weapons[iid])
            t = e.creature_factory.spawn('hollow_revenant',13,12); t.ai = None
            t.fighter.max_hp = t.fighter.hp = 1000; e.entities.append(t); e._update_fov()
            yield from inventory(e,weapons['crude_blade'],key,choose)
            observe(e,'crude blade equipped through inventory'); before = e.world_time.turn
            yield key(e.display.MOVESET_KEY_2,'r')
            ev.check('G18','legal real Desperate Slash',[before+1,-200000,0],timing(e)[:3])
            observe(e,'legal Desperate Slash'); yield key(pygame.K_F5)
            archive_checkpoint(e,out,'fast-checkpoint')
            cold = cold_check(e,'fast',-1)
            ev.check('G18','cold four continued actions with authored cooldown waits',[1,1,1,0],cold['phases'])
            capture('desperate-slash-saved')
            # Disclosed staging isolates the subsequent Press kill.
            t.x,t.y = 30,30
            yield from inventory(e,weapons['heavy_blade'],key,choose)
            victim = e.creature_factory.spawn('hollow_revenant',13,12); victim.fighter.hp = 1
            e.entities.append(victim); e._update_fov(); before = e.world_time.turn
            yield key(e.display.MOVESET_KEY_1,'q')
            ev.check('G18','real Press kill pays then grants',[before+1,True,False],
                     [e.world_time.turn,e._free_move_pending,victim.is_alive])
            observe(e,'Press killing blow settled'); yield key(pygame.K_F5)
            archive_checkpoint(e,out,'press-pending-checkpoint')
            cold = cold_check(e,'pending',2)
            ev.check('G18','cold pending step then ordinary step',[0,1],cold['phases'])
            capture('press-momentum-feedback')
            before = e.world_time.turn; yield key(pygame.K_UP)
            ev.check('G18','blocked step preserves',[before,True],[e.world_time.turn,e._free_move_pending])
            observe(e,'blocked input preserves opportunity')
            yield key(pygame.K_DOWN)
            ev.check('G18','first local step',[before,False],[e.world_time.turn,e._free_move_pending])
            observe(e,'first step uses momentum'); capture('press-free-step')
            yield key(pygame.K_DOWN)
            ev.check('G18','second local step costs one',before+1,e.world_time.turn)
            observe(e,'second step pays'); yield key(pygame.K_F9)
            ev.check('G18','F9 restores pending',[before,True],[e.world_time.turn,e._free_move_pending])
            yield key(pygame.K_z,'z')
            ev.check('G18','wait pays and expires',[before+1,False],[e.world_time.turn,e._free_move_pending])
            observe(e,'rewound pending then wait expires'); yield key(pygame.K_F5)
            archive_checkpoint(e,out,'press-expired-checkpoint')
            ev.check('G18','cold expired steps both pay',[1,1],cold_check(e,'expired',2)['phases'])
            ev.record['final_actor_count'] = len(e.entities)-1
            ev.record['completion'] = True

        old = Path.cwd(); started = time.monotonic()
        try:
            os.chdir(ROOT/'roguelike')
            run_journey(ev,actions,max_frames=180,max_seconds=120,max_turns=80)
            ev.bind_sources(ROOT/'roguelike')
            ev.record.update(passed=True,elapsed_seconds=time.monotonic()-started)
        finally:
            os.chdir(old); (out/'journey.json').write_text(json.dumps(ev.record,indent=2)+'\n')
    return ev.record


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--evidence',type=Path,required=True); a = p.parse_args()
    assert sys.platform=='win32' and sys.version_info[:2]==(3,11),'Use the production-tested Windows/Python 3.11 environment'
    out = a.evidence.resolve(); out.mkdir(parents=True,exist_ok=True)
    sys.path[:0] = [str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
    from b1_support import ENV
    os.environ.update(ENV)
    os.environ['PYTHONPATH'] = os.pathsep.join([str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')])
    import config
    config.DEBUG_MODE = False
    result = journey(out)
    print(json.dumps(dict(passed=result['passed'],seconds=result['elapsed_seconds'],
                         trace=result['timing_trace'],checks=len(result['checks']))))


if __name__=='__main__': main()
