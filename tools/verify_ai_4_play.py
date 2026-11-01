"""AI-4 ordinary saved-room input witness, seed 20261027/combat 17/AI 19.

Normal player loadout, visibility, damage and AI. No injected condition, owned
remedy, or attack result. Setup uses the three control-published saved rooms.
Player choices are scripted; this is bounded rule evidence, not human discovery.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1];GAME=ROOT/'roguelike'
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
sys.path.insert(0,str(GAME))
import pygame
from room_test import build_engine
from engine.venom import dose
from engine.save_manager import _serialize_entity
from verify_ai_3_play import state,condition_state


def continuity(e):
    return dict(condition_state(e),actors=[_serialize_entity(a) for a in e.entities if a is not e.player])


def run(room,response,cold=False):
    with tempfile.TemporaryDirectory(prefix='resonance-ai4-play-') as temp:
        os.chdir(GAME)
        config=dict(state_root=temp,seed=20261027,room_path=f'roguelike/data/layouts/{room}.json',session_id='ai4-input-witness')
        e=build_engine(config);e.rng=random.Random(17);e.ai_system._rng=random.Random(19)
        pygame.display.set_mode((1280,900));e.display.init();e.inventory_screen.init(e.display)
        from rendering.ui_registry import UIRegistry
        e.ui_registry=UIRegistry();e.ui_registry.load()
        trace=[state(e,'initial')];persistence=[];treatment=None
        def key(k):
            e._handle_key(k);trace.append(state(e,pygame.key.name(k)))
        def checkpoint(label):
            nonlocal a
            before=continuity(e);key(pygame.K_F5);key(pygame.K_F9)
            assert before==continuity(e),(label,'F5/F9 changed commitment')
            path=Path(temp)/'config.json';path.write_text(json.dumps(config),encoding='utf-8')
            child=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--cold',str(path)],capture_output=True,text=True)
            assert child.returncode==0,child.stderr
            assert before==json.loads(child.stdout.splitlines()[-1]),label
            a=next(x for x in e.entities if getattr(x,'_creature_id','') in ('patient_amber_hunter','timed_amber_hunter'))
            persistence.append(dict(label=label,state=before,f5_f9_equal=True,cold_equal=True))
        def use():
            key(pygame.K_i);e.inventory_screen.render(pygame.Surface((1280,900)),e)
            for _ in range(40):
                item=e.inventory_screen._selected_item()
                if item and item.item_id=='measured_venom_remedy':break
                key(pygame.K_DOWN)
            else:raise AssertionError('No ordinarily picked-up remedy')
            before=continuity(e);key(pygame.K_e);after=continuity(e);key(pygame.K_ESCAPE)
            assert after['turn']==before['turn']+1
            assert len(after['inventory'])==len(before['inventory'])-1
            return dict(before=before,after=after)
        key(pygame.K_COMMA)
        assert any(i.item_id=='measured_venom_remedy' for i in e.player.inventory.items)
        a=next(a for a in e.entities if getattr(a,'_creature_id','') in ('patient_amber_hunter','timed_amber_hunter'))
        if response=='rival':
            for _ in range(20):
                if a.ai.hunt:break
                key(pygame.K_PERIOD)
            victim=next(v for v in e.entities if getattr(v,'_creature_id','')=='highland_bandit')
            assert a.ai.hunt and a.ai.target['id']==victim._individual_id and dose(victim)
            original=copy.deepcopy(a.ai.hunt)
            retained=a.ai.target['id']
            for _ in range(6):
                key(pygame.K_PERIOD)
                if a.ai.hunt==original:assert a.ai.target['id']==retained
            assert a.ai.hunt is None or a.ai.hunt['application_id']!=original['application_id']
            return dict(room=room,response=response,trace=trace,original_commitment=original,passed=True)
        key(pygame.K_RIGHT)  # ordinary paid opening of the saved door
        for _ in range(30):
            if a.ai.hunt:break
            key(pygame.K_PERIOD)
        assert a.ai.hunt and dose(e.player) and dose(e.player)['stage']=='warning'
        original=copy.deepcopy(a.ai.hunt);sting=e.world_time.turn
        assert dose(e.player)['remaining']==3 and a.ai.phase=='withdraw'
        assert max(abs(a.x-e.player.x),abs(a.y-e.player.y))==1
        if response=='untreated':
            key(pygame.K_PERIOD)
            assert a.ai.phase=='monitor' and max(abs(a.x-e.player.x),abs(a.y-e.player.y))==2
            if cold:checkpoint('monitor')
            key(pygame.K_PERIOD);key(pygame.K_PERIOD)
            assert dose(e.player)['stage']=='paralysis'
            hp=e.player.fighter.hp;key(pygame.K_PERIOD)
            assert a.ai.trace[-1]['action']=='move' and a.ai.phase=='return'
            if cold:checkpoint('confirmed_then_close')
            key(pygame.K_PERIOD)
            r=a.ai.trace[-1]
            assert r['turn']==original['last_useful_phase'] and r['action']=='melee' and r['result']['committed']
            assert r['result']['damage']>0 and e.player.fighter.hp<hp
            assert dose(e.player)['stage']=='recovery'
            key(pygame.K_PERIOD);assert a.ai.hunt is None
        elif response in ('hidden_treatment','escape'):
            # Step behind the wall's northern corner during the warning.
            # The door stays operable; no terrain is changed by this driver.
            key(pygame.K_UP);key(pygame.K_UP)
            assert a.ai.hunt==original,json.dumps(dict(original=original,current=a.ai.snapshot(),recent=a.ai.trace,player=[e.player.x,e.player.y]))
            from components.patient_hunt import observe
            assert observe(a.ai,e,a,e.player,1)['cue'] is None,'Treatment must occur out of hunter sight'
            if cold:checkpoint('reacquisition')
            if response=='hidden_treatment':
                treatment=use()
                # No hidden notification can assert a cure or change provenance.
                if a.ai.hunt:assert a.ai.hunt==original
            else:key(pygame.K_PERIOD)
            key(pygame.K_DOWN);key(pygame.K_DOWN)
            for _ in range(6):key(pygame.K_PERIOD)
            if a.ai.profile['return_policy']=='observed_paralysis':
                assert not any(r['phase_before']=='return' and r['action']=='melee' for t in trace for x in t['tactics']['actors'] for r in x['recent'])
                assert a.ai.hunt is None
            else:
                assert any(r['phase_before']=='return' and r['action']=='melee' for t in trace for x in t['tactics']['actors'] for r in x['recent'])
        elif response=='cure_after_close':
            for _ in range(4):key(pygame.K_PERIOD)
            assert a.ai.phase=='return' and dose(e.player)['stage']=='paralysis'
            hp=e.player.fighter.hp;treatment=use()
            assert e.player.fighter.hp==hp and a.ai.hunt is None
            assert a.ai.last_cancellation=='expected_impairment_absent'
        else:raise AssertionError(response)
        return dict(room=room,response=response,trace=trace,sting_phase=sting,original_commitment=original,
                    persistence=persistence,treatment=treatment,passed=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--evidence',type=Path);ap.add_argument('--cold',type=Path)
    args=ap.parse_args();pygame.init()
    if args.cold:
        os.chdir(GAME);e=build_engine(json.loads(args.cold.read_text(encoding='utf-8')),load=True)
        print(json.dumps(continuity(e)));return
    output=args.evidence.resolve();output.mkdir(parents=True,exist_ok=True)
    rows=[run('ai4_patient_opening','untreated',True),run('ai4_patient_opening','hidden_treatment',True),
          run('ai4_timed_opening','hidden_treatment'),run('ai4_patient_opening','escape'),
          run('ai4_patient_opening','cure_after_close'),run('ai4_rival_ground','rival')]
    files=[*GAME.rglob('*.py'),*GAME.glob('data/layouts/ai4*.json'),*GAME.glob('data/entities/creatures/*amber*.json')]
    inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files if 'saves' not in p.parts and '__pycache__' not in p.parts}
    report=dict(passed=True,setup=__doc__,python=sys.version,inputs=inputs,scenarios=rows)
    (output/'responses.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([dict(room=r['room'],response=r['response'],passed=r['passed']) for r in rows],indent=2));pygame.quit()


if __name__=='__main__':main()
