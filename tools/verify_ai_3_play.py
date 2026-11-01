"""AI-3 saved-room ordinary-input responses and separate-process cold loads.

Fixed room seed 20261027, combat RNG 17 and AI RNG 19 are disclosed setup.
Normal loadout, visibility, damage, AI, pickup and inventory controls are used.
No fixture injects a condition or supplies an owned treatment. Controlled edge
cases are separately covered by test_ai_3, not claimed as these play witnesses.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'roguelike'
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
sys.path.insert(0,str(GAME))
import pygame
from room_test import build_engine
from engine.composite_diagnostics import inspect
from engine.venom import dose,snapshot
from engine.save_components import serialize_item


def state(e,label):
    return dict(label=label,turn=e.world_time.turn,player=[e.player.x,e.player.y],hp=e.player.fighter.hp,
        condition=snapshot(e.player),tactics=inspect(e),
        inventory=[serialize_item(i) for i in e.player.inventory.items],
        logs=[dict(text=m.text,count=m.count) for m in e.log.messages][-14:])


def condition_state(e):
    return dict(turn=e.world_time.turn,condition=snapshot(e.player),
        inventory=[serialize_item(i) for i in e.player.inventory.items],
        actors=[dict(id=getattr(a,'_creature_id',None),condition=snapshot(a),
                     composite=a.ai.snapshot() if hasattr(a.ai,'snapshot') else None)
                for a in e.entities if a is not e.player and getattr(a,'ai',None)])


def run(room,response,cold_checks=False):
    with tempfile.TemporaryDirectory(prefix='resonance-ai3-play-') as temp:
        os.chdir(GAME)
        config=dict(state_root=temp,seed=20261027,room_path=f'roguelike/data/layouts/{room}.json',session_id='ai3-handler-witness')
        e=build_engine(config);e.rng=random.Random(17);e.ai_system._rng=random.Random(19)
        pygame.display.set_mode((1280,900));e.display.init();e.inventory_screen.init(e.display)
        from rendering.ui_registry import UIRegistry
        e.ui_registry=UIRegistry();e.ui_registry.load()
        trace=[state(e,'initial')];persistence=[]
        def key(k):
            e._handle_key(k);trace.append(state(e,pygame.key.name(k)))
        def use(rejected=False):
            key(pygame.K_i);e.inventory_screen.render(pygame.Surface((1280,900)),e)
            for _ in range(40):
                item=e.inventory_screen._selected_item()
                if item and item.item_id=='measured_venom_remedy':break
                key(pygame.K_DOWN)
            else:raise AssertionError('Placed remedy was not acquired through ordinary pickup')
            before=condition_state(e);key(pygame.K_e);after=condition_state(e);key(pygame.K_ESCAPE)
            if rejected:
                assert before==after
            else:
                assert after['turn']==before['turn']+1
                assert len(after['inventory'])==len(before['inventory'])-1
                assert dose(e.player)['stage']=='recovery' and dose(e.player)['remaining']==3
            return dict(before=before,after=after)
        def checkpoint(stage):
            expected=condition_state(e);key(pygame.K_F5);key(pygame.K_F9)
            assert expected==condition_state(e),(stage,'F5/F9 changed state')
            path=Path(temp)/'config.json';path.write_text(json.dumps(config),encoding='utf-8')
            proc=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--cold',str(path)],capture_output=True,text=True)
            assert proc.returncode==0,proc.stderr
            assert expected==json.loads(proc.stdout.splitlines()[-1]),stage
            persistence.append(dict(stage=stage,state=expected,f5_f9_equal=True,separate_process_equal=True))
        key(pygame.K_COMMA)
        assert any(i.item_id=='measured_venom_remedy' for i in e.player.inventory.items)
        if response=='rival':
            for _ in range(15):
                key(pygame.K_PERIOD)
                if any(snapshot(a) for a in e.entities if a is not e.player):break
            victims=[a for a in e.entities if getattr(a,'_creature_id',None)=='highland_bandit']
            assert victims and dose(victims[0]),'No real rival delivery'
            victim=victims[0];identity=dose(victim)['application_id']
            for _ in range(9):
                if not victim.is_alive:break
                key(pygame.K_PERIOD)
            return dict(room=room,response=response,trace=trace,application_id=identity,passed=True)
        key(pygame.K_RIGHT)  # saved closed door; ordinary paid interaction
        for _ in range(30):
            if dose(e.player):break
            key(pygame.K_PERIOD)
        assert dose(e.player) and dose(e.player)['stage']=='warning','No real damaging delivery'
        accepted=state(e,'accepted');warning=dose(e.player)['remaining']
        assert warning==(6 if 'drowsing' in room else 3)
        # Actual accepted delivery earns an intent, not an immediate extra move.
        applier=next(a for a in e.entities if getattr(a,'_creature_id','') in ('nettle_stalker','drowsing_stalker'))
        assert applier.ai.phase=='withdraw'
        if cold_checks:checkpoint('warning')
        treatment=None;blocked=None
        if response=='treat_warning':
            treatment=use()
        elif response=='escape':
            for _ in range(warning):key(pygame.K_LEFT)
        else:
            for _ in range(warning):key(pygame.K_PERIOD)
        if response!='treat_warning':
            assert dose(e.player)['stage']=='paralysis'
            if cold_checks:checkpoint('paralysis')
            before=state(e,'before_denial');key(pygame.K_DOWN);after=state(e,'after_denial')
            assert (before['turn'],before['player'])==(after['turn'],after['player'])
            blocked=dict(before=before,after=after)
            if response=='treat_paralysis':treatment=use(rejected=True)
            while dose(e.player)['stage']=='paralysis':key(pygame.K_PERIOD)
            assert dose(e.player)['stage']=='recovery' and dose(e.player)['remaining']==4
        if cold_checks:checkpoint('recovery')
        recovery=dose(e.player)['remaining']
        for _ in range(recovery):key(pygame.K_PERIOD)
        assert dose(e.player) is None,'Recovery did not end at its recorded boundary'
        if response!='escape':
            for _ in range(20):
                key(pygame.K_PERIOD)
                if dose(e.player):break
            assert dose(e.player) and dose(e.player)['application_id']!=accepted['condition']['dose']['application_id']
        actions=[r for t in trace for a in t['tactics']['actors'] for r in a['recent']]
        assert any(r['reason']=='withdrawal' and r['action']=='move' for r in actions),'No real earned retreat'
        return dict(room=room,response=response,accepted=accepted,warning_phases=warning,trace=trace,
                    treatment=treatment,blocked=blocked,persistence=persistence,
                    summary=dict(hp_lost=trace[0]['hp']-e.player.fighter.hp,player_final=[e.player.x,e.player.y],
                                 inputs_during_warning=warning if response!='treat_warning' else 0),passed=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--evidence',type=Path);ap.add_argument('--cold',type=Path)
    args=ap.parse_args();pygame.init()
    if args.cold:
        os.chdir(GAME);e=build_engine(json.loads(args.cold.read_text(encoding='utf-8')),load=True)
        print(json.dumps(condition_state(e)));return
    output=args.evidence.resolve();output.mkdir(parents=True,exist_ok=True)
    rows=[run('ai3_nettle_opening',r,r=='treat_paralysis') for r in ('treat_warning','treat_paralysis','wait','escape')]
    rows += [run('ai3_drowsing_opening','treat_paralysis'),run('ai3_rival_ground','rival')]
    files=[*GAME.rglob('*.py'),*GAME.glob('data/layouts/ai3*.json'),*GAME.glob('data/entities/creatures/*stalker.json'),*GAME.glob('data/items/consumables/*venom*.json')]
    inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files if 'saves' not in p.parts and '__pycache__' not in p.parts}
    report=dict(passed=all(r['passed'] for r in rows),setup=__doc__,python=sys.version,inputs=inputs,scenarios=rows)
    (output/'responses.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([dict(room=r['room'],response=r['response'],passed=r['passed'],summary=r.get('summary')) for r in rows],indent=2))
    pygame.quit()


if __name__=='__main__':main()
