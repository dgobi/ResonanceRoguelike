"""Bounded AI-1 player-response comparison through the real saved-room bootstrap.

Only setup: select the authored room and seed the combat/AI RNGs. No HP, stats,
terrain, actor locations, equipment or needs are altered. Inputs use ordinary
game handlers. Native packaged frame/event witnesses are recorded separately.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'roguelike'
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
sys.path.insert(0,str(GAME))
import pygame
from engine.composite_diagnostics import inspect
from room_test import build_engine


def run(style,response):
    with tempfile.TemporaryDirectory(prefix='resonance-ai1-play-') as temp:
        cfg=dict(state_root=temp,seed=20261027,room_path=f'roguelike/data/layouts/ai1_{style}_room.json',session_id='ai-1-headless-response')
        os.chdir(GAME)
        e=build_engine(cfg)
        e.rng=random.Random(17);e.ai_system._rng=random.Random(19)
        a=next(a for a in e.entities if getattr(a,'_creature_id','')=='grave_'+('skirmisher' if style=='skirmisher' else 'harrier'))
        def snapshot():
            return dict(turn=e.world_time.turn,player=[e.player.x,e.player.y],hp=e.player.fighter.hp,
                        actor=[a.x,a.y],alive=a.is_alive,visible=bool(e.local_map.visible[a.x,a.y]),
                        diagnostic=inspect(e),logs=[m.text for m in e.log.messages][-8:])
        initial=snapshot();lead=[]
        for _ in range(24):
            e._handle_key(pygame.K_PERIOD);lead.append(snapshot())
            if a.ai.phase=='withdraw':break
        assert a.ai.phase=='withdraw','No qualifying real melee in bounded preflight'
        start=snapshot();trace=[]
        for step in range(48 if response=='pressure' else 16):
            if not a.is_alive:break
            if response=='reposition' and step<4:
                key=(pygame.K_LEFT,pygame.K_LEFT,pygame.K_DOWN,pygame.K_DOWN)[step]
            elif response=='pressure' and e.local_map.visible[a.x,a.y]:
                dx,dy=a.x-e.player.x,a.y-e.player.y
                key=(pygame.K_RIGHT if dx>0 else pygame.K_LEFT) if abs(dx)>=abs(dy) and dx else (pygame.K_DOWN if dy>0 else pygame.K_UP)
            else:key=pygame.K_PERIOD
            e._handle_key(key);trace.append(dict(key=pygame.key.name(key),**snapshot()))
        remains=[dict(position=list(xy),source=i.source_creature,item=i.item_id) for xy,rows in e.local_map.floor_objects.items() for i in rows if getattr(i,'source_creature',None)]
        result=dict(style=style,response=response,initial=initial,lead=lead,start=start,trace=trace,remains=remains,
                    summary=dict(hp_lost=start['hp']-e.player.fighter.hp,player_final=[e.player.x,e.player.y],actor_alive=a.is_alive,
                                 phases=sorted({r['phase'] for s in trace for d in s['diagnostic']['actors'] for r in d['recent']})))
        result['passed']=(trace[3]['hp']==start['hp'] and trace[3]['player']!=start['player']) if response=='reposition' else (not a.is_alive or 'cornered' in result['summary']['phases']) if response=='pressure' else True
        return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--evidence',type=Path,required=True);args=ap.parse_args()
    output=args.evidence.resolve();output.mkdir(parents=True,exist_ok=True)
    pygame.init()
    rows=[run(style,response) for style in ('skirmisher','harrier') for response in ('wait','reposition','pressure')]
    inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [
        *[p for p in GAME.rglob('*.py') if '__pycache__' not in p.parts and 'saves' not in p.parts],
        GAME/'data/entities/creatures/grave_skirmisher.json',GAME/'data/entities/creatures/grave_harrier.json',
        GAME/'data/layouts/ai1_skirmisher_room.json',GAME/'data/layouts/ai1_harrier_room.json']}
    (output/'responses.json').write_text(json.dumps(dict(passed=all(r['passed'] for r in rows),inputs=inputs,python=sys.version,setup=__doc__,scenarios=rows),indent=2)+'\n',encoding='utf-8')
    print(json.dumps([dict(style=r['style'],response=r['response'],**r['summary']) for r in rows],indent=2))
    pygame.quit()
    assert all(r['passed'] for r in rows),'Response preflight failed; inspect exact observations'


if __name__=='__main__':main()
