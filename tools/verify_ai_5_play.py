"""AI-5 ordinary inputs plus a genuine pre-change P2 save, never a campaign.

Six real saved-room scenarios reuse the current AI-4 driver under the corrected
contract. Old-save bytes were captured at 721c71e before changing runtime code.
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
import zipfile
from verify_ai_4_play import ROOT,GAME,run,continuity
import pygame
from room_test import build_engine
from engine.venom import dose,fully_paralysed


def legacy(archive,snapshot):
    original=json.loads(snapshot.read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='resonance-ai5-old-load-') as temp:
        with zipfile.ZipFile(archive) as z:z.extractall(temp)
        config=dict(state_root=temp,seed=20261027,room_path='roguelike/data/layouts/ai4_patient_opening.json',session_id='ai5-legacy-p2')
        os.chdir(GAME);e=build_engine(config,load=True)
        a=next(a for a in e.entities if getattr(a,'_creature_id','')=='patient_amber_hunter')
        assert dose(e.player)==original['condition']['dose']
        assert a.ai.snapshot()==original['actors'][0]['composite']
        assert a.ai.profile['paralysis_phases']==2
        assert fully_paralysed(e.player) and not e.player.fighter.can_attack()
        before=continuity(e)
        e._handle_key(pygame.K_i);e._handle_key(pygame.K_ESCAPE)
        e._handle_key(pygame.K_h);e._handle_key(pygame.K_ESCAPE)
        for k in (pygame.K_RIGHT,e.display.MOVESET_KEY_1):e._handle_key(k)
        assert not e.item_system.use(e.player.inventory.items[0],e)
        assert before==continuity(e)
        e._handle_key(pygame.K_F5);e._handle_key(pygame.K_F9)
        assert before==continuity(e)
        path=Path(temp)/'config.json';path.write_text(json.dumps(config),encoding='utf-8')
        child=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--cold',str(path)],capture_output=True,text=True)
        assert child.returncode==0,child.stderr
        assert before==json.loads(child.stdout.splitlines()[-1])
        left=dose(e.player)['remaining'];turn=e.world_time.turn
        for _ in range(left):e._handle_key(pygame.K_PERIOD)
        assert e.world_time.turn==turn+left and dose(e.player)['stage']=='recovery'
        assert e.player.fighter.can_attack()
        return dict(passed=True,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    original=original,loaded=before,after=continuity(e),f5_f9_equal=True,cold_equal=True,
                    original_remaining=left,physical_rejections_free=True,free_inspection=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidence',type=Path)
    ap.add_argument('--legacy-archive',type=Path,default=ROOT/'evidence/ai-5/legacy-save.zip')
    ap.add_argument('--legacy-snapshot',type=Path,default=ROOT/'evidence/ai-5/legacy-snapshot.json')
    ap.add_argument('--cold',type=Path);args=ap.parse_args();pygame.init()
    if args.cold:
        os.chdir(GAME);e=build_engine(json.loads(args.cold.read_text(encoding='utf-8')),load=True)
        print(json.dumps(continuity(e)));return
    output=args.evidence.resolve();output.mkdir(parents=True,exist_ok=True)
    old=legacy(args.legacy_archive.resolve(),args.legacy_snapshot.resolve())
    rows=[run('ai4_patient_opening','untreated',True),run('ai4_patient_opening','hidden_treatment',True),
          run('ai4_timed_opening','hidden_treatment'),run('ai4_patient_opening','escape'),
          run('ai4_patient_opening','cure_after_close'),run('ai4_rival_ground','rival')]
    files=[*GAME.rglob('*.py'),*GAME.glob('data/layouts/ai4*.json'),*GAME.glob('data/entities/creatures/*amber*.json'),
           *GAME.glob('data/items/consumables/*venom*.json'),Path(__file__),ROOT/'tools/verify_ai_4_play.py']
    inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files if 'saves' not in p.parts and '__pycache__' not in p.parts}
    report=dict(passed=True,setup=__doc__,python=sys.version,inputs=inputs,scenarios=rows,legacy=old)
    (output/'responses.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,scenarios=len(rows),legacy_p2=True,cold_comparisons=4)))
    pygame.quit()


if __name__=='__main__':main()
