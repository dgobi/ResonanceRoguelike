"""Actual saved-room F5/F9 and separate-process cold load of AI-2 commitments.

Concealment starts with an ordinary door input. Lost-sight persistence is a
separately disclosed controlled fixture: move the player to a legal hidden room
cell, then grant one real scheduled world phase. This is not a normal-input
player-response witness. All saves are disposable and explicitly owned.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
GAME=ROOT/'roguelike'
sys.path.insert(0,str(GAME))
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from room_test import build_engine
from engine.save_manager import _serialize_entity


def actor(e):
    return next(a for a in e.entities if getattr(a,'_creature_id','')=='gloam_stalker')


def state(e):
    return _serialize_entity(actor(e))['composite']


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cold',type=Path);ap.add_argument('--evidence',type=Path)
    args=ap.parse_args();os.chdir(GAME);pygame.init()
    if args.cold:
        e=build_engine(json.loads(args.cold.read_text(encoding='utf-8')),load=True)
        print('AI2_COLD='+json.dumps(state(e)))
        return
    assert args.evidence
    output=args.evidence.resolve();output.mkdir(parents=True,exist_ok=True)
    checks=[]
    with tempfile.TemporaryDirectory(prefix='resonance-ai2-cold-') as temp:
        cfg=dict(state_root=temp,seed=20261027,room_path='roguelike/data/layouts/ai2_shadow_opening.json',session_id='ai2-explicit-cold')
        config=Path(temp)/'session.json';config.write_text(json.dumps(cfg),encoding='utf-8')
        e=build_engine(cfg);e._handle_key(pygame.K_RIGHT)
        assert actor(e).ai.phase=='conceal',state(e)
        for phase in ('conceal','pursue'):
            if phase=='pursue':
                for _ in range(8):
                    if actor(e).ai.phase=='covered':break
                    e._handle_key(pygame.K_PERIOD)
                assert actor(e).ai.phase=='covered'
                # Disclosed fixture only: prey moves independently behind the wall.
                e.player.x,e.player.y=33,25
                assert e.local_map.walkable[33,25]
                e._advance_turn()
                assert actor(e).ai.phase=='pursue',state(e)
                assert actor(e).ai.target['x']!=e.player.x
            before=copy.deepcopy(state(e));turn=e.world_time.turn
            e._handle_key(pygame.K_F5);e._handle_key(pygame.K_F9)
            assert state(e)==before and e.world_time.turn==turn
            process=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--cold',str(config)],
                cwd=GAME,capture_output=True,text=True,encoding='utf-8',timeout=60)
            assert process.returncode==0,process.stderr
            loaded=json.loads(process.stdout.split('AI2_COLD=')[1])
            assert loaded==before,(loaded,before)
            checks.append(dict(phase=phase,turn=turn,state=before,f5_f9_equal=True,cold_equal=True,
                               cold_exit_code=process.returncode))
    inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [*GAME.rglob('*.py'),GAME/'data/layouts/ai2_shadow_opening.json',GAME/'data/entities/creatures/gloam_stalker.json']
        if '__pycache__' not in p.parts and 'saves' not in p.parts}
    report=dict(passed=True,setup=__doc__,checks=checks,inputs=inputs,python=sys.version)
    (output/'cold-load.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,phases=[c['phase'] for c in checks])))


if __name__=='__main__':main()
