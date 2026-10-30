"""G20 A original-loop proof: staged scene, real gather and ordinary input."""
import argparse
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def journey(out):
    import pygame
    from b1_support import Evidence
    from b1_journey import run_journey
    from components.ai import AIState
    from test_gameplay_g20 import snapshot
    ev=Evidence(dict(run_id='g20-sound-loop',scenario='journey',phase='loop',flavor='candidate',variant='g20',result=str(out/'journey.json')))
    ev.record['controls']='Controlled laboratory geometry and factory Revenant, normal stats/AI. Stage one natural flint-rock tile, gather through ordinary cursor and RNG (seed 1), inventory selection, targeting, cancellation and throw through app-local keys. Normal FOV, survival, time and rendering remain. No ordinary-world discovery or balance claim; connected outings are separate.'
    with tempfile.TemporaryDirectory(prefix='resonance-g20-sound-loop-') as root,patch('engine.save_manager.SAVE_DIR',Path(root)):
        slot=Path(root)/'slot_0';slot.mkdir();(slot/'world.json').write_text('{"seed":20261023}')
        def actions(e,key,capture,choose):
            e.entities=[e.player];e.player.x,e.player.y=12,12;e.rng=random.Random(1)
            for x in range(9,23):
                for y in range(9,20):
                    e.local_map.set_tile(x,y,'flagstone',True,True)
                    e.local_map.decor.pop((x,y),None);e.local_map.container_state.pop((x,y),None)
            for y in range(12,16):e.local_map.set_tile(14,y,'wall',False,False)
            e.local_map.set_tile(12,12,'flint_rock',True,True);e._update_fov()
            # Ordinary supported interaction cursor; opening is free.
            e._try_open_interaction_cursor();before=e.world_time.turn
            for _ in range(8):
                yield key(pygame.K_RETURN)
                if e.player.inventory.get_by_id('flint_shard'):break
                e._try_open_interaction_cursor()
            shard=e.player.inventory.get_by_id('flint_shard');assert shard
            ev.check('G20-A','ordinary gather depleted source','flint_rock_depleted',str(e.local_map.tiles['terrain'][12,12]))
            ev.check('G20-A','real gather charged at least one phase',True,e.world_time.turn>before)
            a=e.creature_factory.spawn('hollow_revenant',17,15);e.entities.append(a)
            e._update_fov();yield key(pygame.K_i,'i');yield from choose(e,shard);capture('gathered-cutting-shard')
            before=e.world_time.turn;yield key(pygame.K_e,'e');yield key(pygame.K_ESCAPE)
            ev.check('G20-A','cancel keeps owned shard and world time',[True,before],[e.player.inventory.contains(shard),e.world_time.turn])
            yield key(pygame.K_i,'i');yield from choose(e,shard);yield key(pygame.K_e,'e')
            # Cursor begins north of player: down five and right one to (13,16).
            for _ in range(5):yield key(pygame.K_DOWN)
            yield key(pygame.K_RIGHT);yield key(pygame.K_RETURN)
            ev.check('G20-A','one throw phase and finite consumption',[before+1,False],[e.world_time.turn,e.player.inventory.contains(shard)])
            ev.check('G20-A','impact source distinct from hidden player',[13,16],[a.ai.sound_interest['x'],a.ai.sound_interest['y']])
            start=[a.x,a.y];yield key(pygame.K_z,'z')
            ev.check('G20-A','normal budget changes guard route',True,[a.x,a.y]!=start)
            ev.check('G20-A','investigation has no player trail',[AIState.INVESTIGATING.value,None],[a.ai.state.value,getattr(a,'_last_known_px',None)])
            capture('clatter-investigation');yield key(pygame.K_F5);saved=snapshot(e)
            yield key(pygame.K_z,'z');yield key(pygame.K_F9)
            ev.check('G20-A','F9 restores source and clock without replay',saved,snapshot(e))
            ev.record['completion']=True
        old=Path.cwd();started=time.perf_counter()
        try:
            os.chdir(ROOT/'roguelike');run_journey(ev,actions,max_frames=150,max_seconds=100,max_turns=40)
            ev.bind_sources(ROOT/'roguelike');ev.record.update(passed=True,elapsed_seconds=time.perf_counter()-started)
        finally:
            os.chdir(old);(out/'journey.json').write_text(json.dumps(ev.record,indent=2)+'\n')
    return ev.record


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
    from b1_support import ENV
    os.environ.update(ENV)
    import config
    config.DEBUG_MODE=False
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    r=journey(out);print(json.dumps(dict(passed=r['passed'],checks=len(r['checks']),seconds=r['elapsed_seconds'])))


if __name__=='__main__':main()
