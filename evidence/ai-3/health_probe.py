import sys,os,json,tempfile,random
from pathlib import Path
root=Path('.').resolve();sys.path.insert(0,str(root/'roguelike'));os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from room_test import build_engine
from engine.venom import dose,snapshot
from rendering.ui_registry import UIRegistry
out=root/'.baseline/ai-3/final/health';out.mkdir(parents=True,exist_ok=True)
pygame.init();pygame.display.set_mode((1280,900));os.chdir(root/'roguelike')
rows=[]
with tempfile.TemporaryDirectory(prefix='resonance-ai3-health-') as temp:
 e=build_engine(dict(state_root=temp,seed=20261027,room_path='roguelike/data/layouts/ai3_nettle_opening.json',session_id='ai3-health'))
 e.rng=random.Random(17);e.ai_system._rng=random.Random(19);e.display.init();e.health_screen.init(e.display);e.ui_registry=UIRegistry();e.ui_registry.load()
 e._handle_key(pygame.K_RIGHT)
 for stage in ('warning','paralysis','recovery'):
  for _ in range(30):
   if dose(e.player) and dose(e.player)['stage']==stage:break
   e._handle_key(pygame.K_PERIOD)
  else:raise AssertionError(stage)
  before=snapshot(e.player);turn=e.world_time.turn;e._handle_key(pygame.K_h)
  assert e.health_screen.open
  surface=pygame.Surface((1280,900));e.health_screen.render(surface,e);assert e.health_screen.open
  conditions=e.health_screen._collect_conditions(e);assert any(name=='Numbing venom: '+stage for name,_,_ in conditions)
  pygame.image.save(surface,str(out/(stage+'.png')));e._handle_key(pygame.K_ESCAPE)
  assert before==snapshot(e.player) and turn==e.world_time.turn
  rows.append(dict(stage=stage,conditions=conditions,turn=turn,free_inspection=True))
(out/'health.json').write_text(json.dumps(dict(passed=True,setup='Actual saved-room delivery; ordinary H/Escape and health render; RNG17/19, seed20261027.',checks=rows),indent=2),encoding='utf-8')
print('Three actual health stages rendered; inspection stayed free.')
