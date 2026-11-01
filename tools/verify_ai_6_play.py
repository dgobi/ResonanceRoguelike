"""AI-6 ordinary saved-room inputs and disclosed natural-entrance/sound staging.
No combat, perception, AI, damage, or action rules are overridden. Seeds are fixed.
The sound case alone provisions one existing flint shard in an owned inventory.
"""
import argparse,copy,gzip,hashlib,json,os,random,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];GAME=ROOT/'roguelike'
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
sys.path[:0]=[str(GAME),str(ROOT/'tools')]
import pygame
from room_test import build_engine
from engine.save_manager import _serialize_entity,_serialize_world,_deserialize_world
from engine.save_components import serialize_item
from engine.composite_diagnostics import inspect
from world.world_map import WorldMap


def snapshot(e):
 return dict(turn=e.world_time.turn,player=[e.player.x,e.player.y],hp=e.player.fighter.hp,
  inventory=[serialize_item(i) for i in e.player.inventory.items],
  actors=[_serialize_entity(a) for a in e.entities if a is not e.player],
  floor=[dict(position=list(xy),items=[serialize_item(i) for i in rows]) for xy,rows in sorted(e.local_map.floor_objects.items())])


def display(e):
 pygame.display.set_mode((1280,900));e.display.init();e.inventory_screen.init(e.display)
 from rendering.ui_registry import UIRegistry
 e.ui_registry=UIRegistry();e.ui_registry.load()


def capture(e,path):
 class Done(Exception):pass
 before=snapshot(e)
 def frame(engine,screen):pygame.image.save(screen,str(path));raise Done()
 try:e.run(on_frame=frame)
 except Done:pass
 assert before==snapshot(e),'render advanced physical state'


class Session:
 def __init__(self,e,config,out):self.e=e;self.config=config;self.out=out;self.rows=[];self.persistence=[]
 def state(self,label):
  self.rows.append(dict(label=label,player=[self.e.player.x,self.e.player.y],hp=self.e.player.fighter.hp,tactics=inspect(self.e),logs=[m.text for m in self.e.log.messages][-8:]))
 def key(self,k):
  self.e._handle_key(k);self.state(pygame.key.name(k));assert not self.e._player_is_dead,'ordinary player died'
 def use(self,iid):
  self.key(pygame.K_i);self.e.inventory_screen.render(pygame.Surface((1280,900)),self.e)
  for _ in range(60):
   item=self.e.inventory_screen._selected_item()
   if item and item.item_id==iid:break
   self.key(pygame.K_DOWN)
  else:raise AssertionError('No owned item '+iid)
  self.key(pygame.K_e);self.key(pygame.K_ESCAPE)
 def move(self,x,y,limit=80):
  from engine.spatial import melee_contact
  from collections import deque
  keys={(0,-1):pygame.K_UP,(-1,0):pygame.K_LEFT,(1,0):pygame.K_RIGHT,(0,1):pygame.K_DOWN,
        (-1,-1):pygame.K_y,(1,-1):pygame.K_u,(-1,1):pygame.K_b,(1,1):pygame.K_n}
  for _ in range(limit):
   e=self.e;start=(e.player.x,e.player.y)
   if start==(x,y):return
   # Disclosed known saved-room geometry; inputs remain ordinary. Avoid living
   # actors except the goal so this route never injects an attack/move result.
   blocked={(a.x,a.y) for a in e.entities if a is not e.player and getattr(a,'blocks_movement',False)}-{(x,y)}
   q=deque([start]);parents={start:None}
   while q:
    a=q.popleft()
    if a==(x,y):break
    for dx,dy in keys:
     b=a[0]+dx,a[1]+dy
     if b not in parents and b not in blocked and melee_contact(e.local_map,*a,*b) and not e._decor_blocks_movement(*b):parents[b]=a;q.append(b)
   assert (x,y) in parents,('no ordinary route',start,(x,y))
   step=(x,y)
   while parents[step]!=start:step=parents[step]
   self.key(keys[step[0]-start[0],step[1]-start[1]])
  raise AssertionError('bounded route did not finish')
 def checkpoint(self,label):
  before=snapshot(self.e);self.key(pygame.K_F5);self.key(pygame.K_F9)
  assert before==snapshot(self.e),(label,'F5/F9 changed state')
  config=Path(self.config['state_root'])/'cold-config.json';config.write_text(json.dumps(self.config),encoding='utf-8')
  child=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--cold',str(config)],capture_output=True,text=True)
  assert child.returncode==0,child.stderr
  assert before==json.loads(child.stdout.splitlines()[-1]),(label,'cold state differed')
  self.persistence.append(dict(label=label,f5_f9_equal=True,cold_equal=True,state=before))
 def report(self):return dict(passed=True,rows=self.rows,persistence=self.persistence,final=snapshot(self.e))


def setup(temp,room,out):
 os.chdir(GAME);config=dict(state_root=temp,seed=20261027,room_path=f'roguelike/data/layouts/{room}.json',session_id='ai6-input-witness')
 e=build_engine(config);e.rng=random.Random(17);e.ai_system._rng=random.Random(19);display(e)
 s=Session(e,config,out);s.state('arrival');return s


def withdrawal(out):
 with tempfile.TemporaryDirectory(prefix='resonance-ai6-withdraw-') as temp:
  s=setup(temp,'ai6_sentinel_post',out);e=s.e;a=e.entities[1];home=(a.ai.home_x,a.ai.home_y)
  s.key(pygame.K_RIGHT);assert a.ai.target;s.checkpoint('engaged')
  a=e.entities[1]
  for _ in range(8):
   s.key(pygame.K_PERIOD)
   if e.player.fighter.hp<60:break
  assert e.player.fighter.hp<60
  for _ in range(5):s.key(pygame.K_LEFT)
  a=e.entities[1];assert a.ai.territory['phase']=='return',a.ai.snapshot()
  s.checkpoint('return');a=e.entities[1]
  for _ in range(16):s.key(pygame.K_PERIOD)
  assert (a.x,a.y)==home and a.ai.territory['phase']=='guard'
  assert e.player.fighter.hp>0
  capture(e,out/'withdrawal-normal-fov.png');return s.report()


def lifecycle(out):
 with tempfile.TemporaryDirectory(prefix='resonance-ai6-scene-') as temp:
  s=setup(temp,'ai6_sentinel_post',out);e=s.e;s.key(pygame.K_RIGHT);a=e.entities[1]
  original=a.ai.snapshot();pos=(a.x,a.y);home=(a.ai.home_x,a.ai.home_y);hp=a.fighter.hp
  e._try_ascend();assert original==a.ai.snapshot(),'failed exit cancelled commitment'
  # Disclosed lifecycle fixture: stage only player at the room's actual return.
  stair=next((x,y) for x in range(e.local_map.width) for y in range(e.local_map.height) if str(e.local_map.tiles[x,y]['terrain'])=='stairs_up')
  e.player.x,e.player.y=stair;e._try_ascend();assert e.current_submap_id is None
  assert (a.x,a.y)==pos and (a.ai.home_x,a.ai.home_y)==home and a.fighter.hp==hp
  assert a.ai.target is None and a.ai.sound_interest is None and a.ai.move_accumulator==0
  assert a.ai.territory['phase']=='return'
  e._try_descend();assert e.current_submap_id=='room-test-instance';a=e.entities[1]
  assert (a.ai.home_x,a.ai.home_y)==home and a.fighter.hp==hp
  assert max(abs(a.x-pos[0]),abs(a.y-pos[1]))<=1,'revisit relocated guard'
  s.state('revisited_displaced_survivor');return s.report()


def natural(out):
 from engine.data_loader import DataLoader
 from engine.display_config import DisplayConfig
 from engine.creature_factory import CreatureFactory
 from engine.item_factory import ItemFactory
 from engine.player_setup import create_player
 from engine.scene_generation import create_surface,publish_metadata
 from engine.engine import Engine
 from engine.save_manager import SaveManager
 from rendering.tile_registry import TileRegistry
 from generation.world_gen import generate_world
 from engine import location_reports
 from config import MAP_WIDTH,MAP_HEIGHT
 os.chdir(GAME);data=DataLoader('data');world=WorldMap(128,128);world.seed=20261027
 world=generate_world(world,data,random.Random(world.seed))
 selected=[(wx,wy,c,s) for (wx,wy),c in world.chunks.items() for s in c.submaps if s.layout_id=='barrow_ward_store_b']
 assert selected;assert any(s.layout_id=='barrow_ward_store_a' for c in world.chunks.values() for s in c.submaps)
 wx,wy,chunk,sub=min(selected,key=lambda r:(abs(r[0]-world.start_wx)+abs(r[1]-world.start_wy),r[0],r[1]))
 assert any(r[2]==sub.submap_id and r[3]=='barrow_ward_store_b' for r in location_reports.candidates(world,'ward_store'))
 items=ItemFactory(data);factory=CreatureFactory(data)
 result=create_surface(world,chunk,data,items,factory,MAP_WIDTH,MAP_HEIGHT);publish_metadata(chunk,result.metadata);chunk.generation_revision=result.local_map.generation_revision;chunk.visited=True
 with tempfile.TemporaryDirectory(prefix='resonance-ai6-natural-') as temp:
  # Disclosed staging at a real naturally selected entrance, not a journey.
  p=create_player(data,items,sub.surface_x,sub.surface_y)
  e=Engine(p,result.local_map,[p]+result.actors,TileRegistry('data/tiles.json',mode='sprite'),world,wx,wy,data,DisplayConfig.from_config(),save_manager=SaveManager(save_root=Path(temp)/'saves'),debug_mode=False)
  e.item_system.use(p.inventory.get_by_id('tallow_torch'),e);e._try_descend()
  assert e.current_submap_id==sub.submap_id
  e.rng=random.Random(17);e.ai_system._rng=random.Random(19);display(e)
  config=dict(state_root=temp,seed=20261027,room_path='roguelike/data/layouts/barrow_ward_store_b.json',session_id='natural')
  s=Session(e,config,out);s.state('naturally_selected_native_entrance')
  a=next(a for a in e.entities if getattr(a,'_creature_id','')=='barrow_sentinel');offset=a.ai.home_x-17,a.ai.home_y-5
  sx=lambda x:x+offset[0];sy=lambda y:y+offset[1]
  assert a.ai.home_x==a.x and a.ai.home_y==a.y
  capture(e,out/'natural-arrival.png')
  s.use('crude_blade');s.use('leather_jack')
  s.move(sx(20),sy(9));s.move(sx(20),sy(8));s.state('eastern_approach')
  from engine.spatial import melee_attack_legal
  for _ in range(30):
   living=[a for a in e.entities if getattr(a,'_creature_id','')=='barrow_sentinel' and getattr(a,'is_alive',False)]
   if not living:break
   a=living[0]
   mask=e.normal_player_vision()['visible'];assert mask[a.x,a.y],'confrontation selected an unseen actor'
   if melee_attack_legal(e.local_map,e.player,a):
    dx=(a.x>e.player.x)-(a.x<e.player.x);dy=(a.y>e.player.y)-(a.y<e.player.y)
    keys={(0,-1):pygame.K_UP,(-1,0):pygame.K_LEFT,(1,0):pygame.K_RIGHT,(0,1):pygame.K_DOWN,(-1,-1):pygame.K_y,(1,-1):pygame.K_u,(-1,1):pygame.K_b,(1,1):pygame.K_n};s.key(keys[dx,dy])
   else:s.key(pygame.K_PERIOD)
  else:raise AssertionError('bounded ordinary confrontation did not finish')
  assert not any(getattr(a,'_creature_id','')=='barrow_sentinel' and getattr(a,'is_alive',False) for a in e.entities)
  s.move(sx(20),sy(4));s.key(pygame.K_COMMA)
  assert e.player.inventory.get_by_id('faceted_ward');assert not any(i.item_id=='faceted_ward' for rows in e.local_map.floor_objects.values() for i in rows)
  capture(e,out/'confrontation-ward.png')
  before=snapshot(e);s.key(pygame.K_F5);s.key(pygame.K_F9);assert before==snapshot(e)
  # Natural worlds use the ordinary SaveManager loader, not bounded-room bootstrap.
  coldpath=Path(temp)/'natural-config.json';coldpath.write_text(json.dumps(config),encoding='utf-8')
  child=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--natural-cold',str(coldpath)],capture_output=True,text=True)
  assert child.returncode==0,child.stderr;assert before==json.loads(child.stdout.splitlines()[-1])
  s.move(sx(3),sy(12));e._try_ascend();assert e.current_submap_id is None
  e._try_descend();assert e.current_submap_id==sub.submap_id
  assert e.player.inventory.get_by_id('faceted_ward')
  assert not any(getattr(a,'_creature_id','')=='barrow_sentinel' and getattr(a,'is_alive',False) for a in e.entities)
  report=s.report();report.update(seed=world.seed,world_size=[128,128],selected_chunk=[wx,wy],selected_id=sub.submap_id,selected_seed=sub.seed,selected_b_count=len(selected),report_candidates_recognized=True,native_room=True,dead_guard_and_taken_ward_revisit=True,cold_consequences_equal=True,staging='Ordinary player placed at naturally selected entrance; no unaided laboratory journey claimed.')
  return report


def sound(out):
 reports=[]
 for distraction in (False,True):
  with tempfile.TemporaryDirectory(prefix='resonance-ai6-sound-') as temp:
   s=setup(temp,'barrow_ward_store_b',out);e=s.e;a=e.entities[1];ox,oy=a.x-17,a.y-5
   s.move(20+ox,9+oy)
   assert not a.ai.sees(e,a,e.player,1),'staged thrower must be unseen'
   if distraction:
    # Existing ordinary throwable, provisioned for this controlled comparison.
    item=e.item_factory.create('flint_shard');assert item;e.player.inventory.add(item)
    e.item_system.use(item,e);e._placement_cursor_x,e._placement_cursor_y=20+ox,7+oy
    from engine.effect_lifecycle import valid_throw
    e._update_fov();assert valid_throw(e,20+ox,7+oy)
    before=(a.x,a.y);s.key(pygame.K_RETURN)
    assert not e.player.inventory.contains(item) and (a.x,a.y)!=before
    assert a.ai.target is None and a.ai.territory['phase']=='investigate'
    s.state('anonymous_real_flint_changed_position');capture(e,out/'flint-distraction.png')
    for _ in range(16):
     if a.ai.territory['phase']=='return':break
     s.key(pygame.K_PERIOD)
    assert a.ai.territory['phase']=='return'
   else:
    for _ in range(11):s.key(pygame.K_PERIOD)
   hp=e.player.fighter.hp
   for x,y in ((20,8),(21,7),(21,6),(20,5),(20,4)):s.move(x+ox,y+oy)
   s.key(pygame.K_COMMA);assert e.player.inventory.get_by_id('faceted_ward')
   s.state('ward_access_without_attacking_guard')
   s.move(22+ox,7+oy);s.move(20+ox,9+oy);s.move(20+ox,12+oy)
   for _ in range(16):s.key(pygame.K_PERIOD)
   assert a.fighter.hp==14 and a.is_alive and a.ai.territory['phase']=='guard' and (a.x,a.y)==(a.ai.home_x,a.ai.home_y)
   r=s.report();r.update(distraction=distraction,access_and_withdrawal_damage=hp-e.player.fighter.hp,ward_taken=True,guard_survived=True)
   reports.append(r)
 assert reports[1]['access_and_withdrawal_damage'] < reports[0]['access_and_withdrawal_damage'],[(r['distraction'],r['access_and_withdrawal_damage']) for r in reports]
 return dict(passed=True,comparison=reports,controlled_setup='One existing flint_shard provisioned for the distraction comparison. Ordinary owned throw, visibility/range/consume/sound/time/AI rules; saved geometry unchanged. Both use the same eastern access route and leave the living guard without attacking. Damage cost is specific to fixed combat RNG 17/AI 19.')


def legacy(out):
 old=ROOT/'evidence/ai-6';original=json.loads((old/'legacy-snapshot.json').read_text())
 with tempfile.TemporaryDirectory(prefix='resonance-ai6-prechange-') as temp:
  with zipfile.ZipFile(old/'legacy-save.zip') as z:z.extractall(temp)
  config=dict(original['config'],state_root=temp);os.chdir(GAME);e=build_engine(config,load=True);display(e)
  a=next(a for a in e.entities if getattr(a,'_creature_id','')=='patient_amber_hunter')
  assert original['actor']==_serialize_entity(a)
  s=Session(e,config,out);s.checkpoint('genuine_pre_ai6_hunt')
  w=WorldMap(64,64);raw=json.loads(gzip.decompress((old/'legacy-world.json.gz').read_bytes()));_deserialize_world(raw,w)
  assert raw==json.loads(json.dumps(_serialize_world(w)))
  return dict(passed=True,hunter_exact=True,world_selected_ids_and_reports_exact=True,archive_sha256=hashlib.sha256((old/'legacy-save.zip').read_bytes()).hexdigest(),persistence=s.persistence)


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path);ap.add_argument('--cold',type=Path);ap.add_argument('--natural-cold',type=Path);ap.add_argument('--only',choices=['withdrawal','natural','sound','legacy','lifecycle']);args=ap.parse_args();pygame.init();os.chdir(GAME)
 if args.cold:
  e=build_engine(json.loads(args.cold.read_text()),load=True);print(json.dumps(snapshot(e)));return
 if args.natural_cold:
  from engine.data_loader import DataLoader
  from engine.item_factory import ItemFactory
  from engine.player_setup import create_player
  from engine.engine import Engine
  from engine.save_manager import SaveManager
  from engine.display_config import DisplayConfig
  from rendering.tile_registry import TileRegistry
  from world.local_map import LocalMap
  from config import MAP_WIDTH,MAP_HEIGHT
  config=json.loads(args.natural_cold.read_text());d=DataLoader('data');p=create_player(d,ItemFactory(d),12,12)
  e=Engine(p,LocalMap(MAP_WIDTH,MAP_HEIGHT),[p],TileRegistry('data/tiles.json',mode='sprite'),WorldMap(128,128),0,0,d,DisplayConfig.from_config(),save_manager=SaveManager(save_root=Path(config['state_root'])/'saves'),debug_mode=False)
  assert e.save_manager.load(e),e.save_manager.last_error;print(json.dumps(snapshot(e)));return
 out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
 report=dict(passed=False,setup=__doc__,python=sys.version,scenarios={})
 for name,fn in [('withdrawal',withdrawal),('sound',sound),('natural',natural),('legacy',legacy),('lifecycle',lifecycle)]:
  if args.only and args.only!=name:continue
  report['scenarios'][name]=fn(out);(out/'responses.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(name+' passed',flush=True)
 report['passed']=True;(out/'responses.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(dict(passed=True,scenarios=list(report['scenarios']))))


if __name__=='__main__':main()
