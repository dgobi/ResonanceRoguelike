"""AI-2 bounded actual saved-room witnesses, ordinary handler inputs.

Setup selects saved authored rooms and fixed combat/AI RNG seeds only. The tuning
comparison is separately labelled: saved definition copied in memory, only its
movement allowance edited, then a fresh actor constructed by the real factory.
No personal campaigns, debug reveal, stat buffs or external desktop control.
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
from room_test import build_engine
from engine.composite_diagnostics import inspect


def run(room, response, allowance=None):
    with tempfile.TemporaryDirectory(prefix='resonance-ai2-play-') as temp:
        os.chdir(GAME)
        e=build_engine(dict(state_root=temp,seed=20261027,
            room_path=f'roguelike/data/layouts/{room}.json',session_id='ai2-handler-witness'))
        e.rng=random.Random(17);e.ai_system._rng=random.Random(19)
        a=next(a for a in e.entities if getattr(a,'_creature_id','').startswith('gloam_'))
        if allowance is not None:
            e.data.entities=copy.deepcopy(e.data.entities)
            e.data.entities[a._creature_id]['ai_profile']['unseen_extra_step']=allowance
            fresh=e.creature_factory.spawn(a._creature_id,a.x,a.y)
            e.entities.remove(a);e.entities.append(fresh);a=fresh
        trace=[]
        def snapshot(label):
            return dict(label=label,turn=e.world_time.turn,player=[e.player.x,e.player.y],
                hp=e.player.fighter.hp,actor=[a.x,a.y],alive=a.is_alive,
                observed=bool(e.normal_player_vision()['visible'][a.x,a.y]),
                diagnostic=inspect(e),logs=[m.text for m in e.log.messages][-10:])
        def key(k):
            e._handle_key(k);trace.append(snapshot(pygame.key.name(k)))
        def torch():
            # Populate the actual inventory UI and navigate its ordinary input route.
            from rendering.ui_registry import UIRegistry
            pygame.display.set_mode((1280,720))
            e.display.init();e.inventory_screen.init(e.display)
            e.ui_registry=UIRegistry();e.ui_registry.load()
            key(pygame.K_i)
            e.inventory_screen.render(pygame.Surface((1280,900)),e)
            for _ in range(30):
                selected=e.inventory_screen._selected_item()
                if selected and selected.item_id=='tallow_torch':break
                key(pygame.K_DOWN)
            else:raise AssertionError('Starting torch absent from ordinary inventory UI')
            key(pygame.K_e);key(pygame.K_ESCAPE)
            assert not e.player.light_source.active
        initial=snapshot('initial')
        if response=='dark' or allowance is not None:
            torch()
        if 'opening' in room and response!='sealed':
            key(pygame.K_RIGHT)  # walk into the saved closed door: paid ordinary opening
        opening=snapshot('opening')
        if allowance is not None:
            first=copy.deepcopy(a.ai.trace[-1])
            return dict(room=room,response=response,allowance=allowance,
                        setup='controlled fresh-definition tuning fixture',initial=initial,
                        trace=trace,first=first,passed=len(first['steps'])==1+allowance)
        if response=='disengage':
            for k in [pygame.K_UP]*3+[pygame.K_LEFT]*3:key(k)
        else:
            for _ in range(18 if 'opening' in room else 5):
                if not e.player.is_alive:break
                key(pygame.K_PERIOD)
        recent=[r for row in trace for actor in row['diagnostic']['actors']
                if actor['id']==a._creature_id for r in actor['recent']]
        summary=dict(hp_lost=initial['hp']-e.player.fighter.hp,
                     player_final=[e.player.x,e.player.y],actor_final=[a.x,a.y],
                     reasons=sorted({r['reason'] for r in recent}),
                     accelerated=any(len(r['steps'])==2 for r in recent),
                     committed_melee=any(r['result'] and r['result']['committed'] for r in recent),
                     # Current restrained sensory wording; preserve the visible
                     # tell obligation rather than the retired AI-2 prose.
                     tells=sorted({m for row in trace for m in row['logs'] if 'shudders in the light' in m}),
                     safe_response_inputs=sum(row['hp']==opening['hp'] for row in trace if row['turn']>opening['turn']))
        if response=='sealed':
            passed=summary['actor_final']==initial['actor'] and not summary['committed_melee']
        elif room=='ai2_cowering_ground':passed=summary['hp_lost']==0 and not summary['committed_melee']
        elif room=='ai2_defensive_ground':passed=summary['committed_melee']
        elif response=='disengage':passed=summary['safe_response_inputs']>=2 and summary['player_final']!=initial['player']
        elif response=='dark':passed=summary['accelerated'] and summary['committed_melee']
        else:passed=bool(summary['tells']) and 'seek_concealment' in summary['reasons'] and 'watched' in summary['reasons']
        return dict(room=room,response=response,setup='ordinary handler witness',
                    initial=initial,opening=opening,trace=trace,summary=summary,passed=passed)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidence',type=Path,required=True);args=ap.parse_args()
    output=args.evidence.resolve();output.mkdir(parents=True,exist_ok=True)
    pygame.init()
    rows=[run('ai2_shadow_opening',response) for response in ('sealed','lit','dark','disengage')]
    rows += [run('ai2_mixed_opening','disengage'),run('ai2_defensive_ground','wait'),run('ai2_cowering_ground','wait')]
    rows += [run('ai2_shadow_opening','dark',allowance) for allowance in (0,1)]
    inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [*GAME.rglob('*.py'),*GAME.glob('data/layouts/ai2*.json'),
                  *GAME.glob('data/entities/creatures/gloam_*.json')]
        if '__pycache__' not in p.parts and 'saves' not in p.parts}
    report=dict(passed=all(r['passed'] for r in rows),inputs=inputs,python=sys.version,
                setup=__doc__,scenarios=rows)
    (output/'responses.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([dict(room=r['room'],response=r['response'],passed=r['passed'],
                          allowance=r.get('allowance'),summary=r.get('summary')) for r in rows],indent=2))
    pygame.quit()
    assert report['passed'],'AI-2 preflight failed: inspect exact observations'


if __name__=='__main__':main()
