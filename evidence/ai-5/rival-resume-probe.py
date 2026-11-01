"""Additional real ordinary-rival resume witness; no injected effects/results/items."""
import os,sys,random,tempfile,json,copy,hashlib,subprocess
from pathlib import Path
ROOT=Path.cwd();sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'roguelike')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from room_test import build_engine
from engine.venom import dose
pygame.init()
with tempfile.TemporaryDirectory(prefix='resonance-ai5-rival-resume-') as temp:
 os.chdir(ROOT/'roguelike');e=build_engine(dict(state_root=temp,seed=20261027,room_path='roguelike/data/layouts/ai4_rival_ground.json',session_id='ai5-rival-resume'))
 e.rng=random.Random(17);e.ai_system._rng=random.Random(19);e._handle_key(pygame.K_COMMA)
 a=next(a for a in e.entities if getattr(a,'_creature_id','')=='patient_amber_hunter')
 v=next(a for a in e.entities if getattr(a,'_creature_id','')=='highland_bandit')
 for _ in range(20):
  if dose(v):break
  e._handle_key(pygame.K_PERIOD)
 assert dose(v) and a.ai.hunt
 rows=[]
 for _ in range(8):
  before=dict(turn=e.world_time.turn,condition=copy.deepcopy(dose(v)),position=[v.x,v.y],source_hp=a.fighter.hp)
  e._handle_key(pygame.K_PERIOD)
  after=dict(turn=e.world_time.turn,condition=copy.deepcopy(dose(v)),position=[v.x,v.y],source_hp=a.fighter.hp,accumulator=v.ai.move_accumulator)
  if before['condition'] and before['condition']['stage']=='paralysis':
   assert before['position']==after['position'] and before['source_hp']==after['source_hp']
  rows.append(dict(before=before,after=after))
 severe=[r for r in rows if r['before']['condition'] and r['before']['condition']['stage']=='paralysis']
 resumed=[r for r in rows if r['before']['condition'] and r['before']['condition']['stage']=='recovery' and (r['after']['source_hp']<r['before']['source_hp'] or r['after']['position']!=r['before']['position'])]
 assert len(severe)==3 and resumed and all(r['after']['accumulator']<1 for r in rows)
 out=dict(passed=True,setup=__doc__,rows=rows,resumed=resumed,logs=[m.text for m in e.log.messages],revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
 (ROOT/'.baseline/ai-5/final/rival-resume.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 print(json.dumps(dict(passed=True,severe_phases=len(severe),resumed_phases=[r['after']['turn'] for r in resumed])))
