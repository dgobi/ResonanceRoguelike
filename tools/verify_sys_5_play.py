"""SYS-5 ordinary selected-world comparisons with living AI and real controls.
One disclosed initial surface-entrance approach staging per destination. Full-map
route knowledge is used, never debug vision; all later travel, acquisition,
placement, cooking, combat, work, harvest and F5/F9 are ordinary input handlers.
Replay branches install the same genuine F5. Personal saves are never opened.
"""
import argparse,copy,json,os,random,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];GAME=ROOT/'roguelike'
sys.path[:0]=[str(GAME),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from verify_sys_4_play import Journey as BaseJourney,snapshot
from g10_play import boot,path,status,KEYS
from engine.save_manager import SceneAddress
from engine.save_components import serialize_item
from verify_ai_6_play import capture,display
from g12_journey import install_checkpoint


class Journey(BaseJourney):
 def state(self):
  e=self.e
  return dict(player=status(e),floor=[[list(xy),[serialize_item(i) for i in rows]] for xy,rows in e.local_map.floor_objects.items()],
   scavengers=[dict(id=a._creature_id,xy=[a.x,a.y],hp=a.fighter.hp,host=a.ai.profile,config=a.ai.scavenging_config,state=copy.deepcopy(a.ai.scavenging_state),trace=copy.deepcopy(a.ai.trace[-6:]),territory=copy.deepcopy(getattr(a.ai,'territory',None))) for a in e.entities if getattr(getattr(a,'ai',None),'scavenging_config',None)],
   access=copy.deepcopy(snapshot(e)['access']))
 def mark(self,label):
  self.stage(label);self.receipt.setdefault('observations',[]).append(dict(label=label,state=self.state()))
  (self.out/'progress.json').write_text(json.dumps(self.receipt,indent=2),encoding='utf8')
 def portion(self,iid):
  e=self.e;self.key(pygame.K_i);e.inventory_screen.render(pygame.Surface((1280,900)),e)
  for _ in range(100):
   i=e.inventory_screen._selected_item()
   if i and i.item_id==iid:break
   self.key(pygame.K_DOWN)
  else:raise AssertionError(iid)
  before=sum(i.count for i in e.player.inventory.items if i.item_id==iid);turn=e.world_time.turn
  self.key(pygame.K_p);self.choice();self.close()
  assert e.world_time.turn==turn+1
  assert sum(i.count for i in e.player.inventory.items if i.item_id==iid)==before-1
  return next(i for i in e.local_map.floor_objects[e.player.x,e.player.y] if i.item_id==iid)
 def light(self,on):
  from engine.held_light import active_item
  if bool(active_item(self.e.player))!=on:self.item('tallow_torch');self.close()
 def harvest(self,xy):
  self.approach(xy);self.interact(xy);self.close()
 def fight(self,actor):
  actor=next((a for a in self.e.entities if getattr(a,'_creature_id',None)==actor._creature_id and getattr(a,'is_alive',False)),None)
  if actor is None:return
  for _ in range(80):
   if not actor.is_alive:return
   self.sustain();dx,dy=actor.x-self.e.player.x,actor.y-self.e.player.y
   if max(abs(dx),abs(dy))<=1:self.key(KEYS[(dx>0)-(dx<0),(dy>0)-(dy<0)])
   else:self.approach((actor.x,actor.y))
  raise AssertionError('ordinary fight budget')


def stage(which,out,save_root):
 e=boot(save_root,seed=20261023);e.rng=random.Random(20261020);e.ai_system._rng=random.Random(20261020)
 name='barrow_scavenger_store' if which=='store' else 'barrow_carrion_sump'
 candidates=[(x,y,sub) for (x,y),c in e.world_map.chunks.items() for sub in c.submaps if sub.layout_id==name]
 # A deterministic genuine assignment, chosen near the earlier public town.
 wx,wy,sub=min(candidates,key=lambda row:abs(row[0]-75)+abs(row[1]-100))
 prepared=e._ensure_surface_scene(wx,wy);SceneAddress(e.world_x,e.world_y,e.current_submap_id).store(e.save_manager.cache,e.local_map,e.entities)
 e.local_map,natives=prepared;e.world_x,e.world_y,e.current_submap_id=wx,wy,None;e.entities=[e.player]+natives
 entrance=next(xy for xy,sid in e.local_map.submap_links.items() if sid==sub.submap_id)
 from generation.access import enterable
 approach=next((entrance[0]+dx,entrance[1]+dy) for dx,dy in ((-3,0),(3,0),(0,3),(0,-3),(-1,0),(1,0)) if e.local_map.in_bounds(entrance[0]+dx,entrance[1]+dy) and enterable(e.local_map,(entrance[0]+dx,entrance[1]+dy),e.data) and not any((a.x,a.y)==(entrance[0]+dx,entrance[1]+dy) for a in natives))
 e.player.x,e.player.y=approach;e.world_map.get(wx,wy).visited=True;e.reality_bubble.update(wx,wy,e.world_map);e._update_fov();display(e)
 s=Journey(e,out);s.receipt.update(controls=__doc__,seed=20261023,layout=name,assignment=dict(chunk=[wx,wy],submap=sub.submap_id,entrance=entrance,staged_surface_approach=approach),sounds=[],comparisons=[])
 s.mark('selected ordinary surface approach');capture(e,out/'surface-approach.png')
 s.item('crude_blade');s.close();s.item('leather_jack');s.close();s.light(False)
 s.move([entrance]);e._handle_key(pygame.K_GREATER,'>');s.receipt['events']+=1
 assert e.current_submap_id==sub.submap_id
 offset=e.player.x-3,e.player.y-12
 return s,lambda x,y:(x+offset[0],y+offset[1]),entrance


def restore(s,label):
 install_checkpoint(s.out/(label+'.zip'),s.e.save_manager.save_path.parent);s.key(pygame.K_F9)
 assert snapshot(s.e)==json.loads((s.out/(label+'.json')).read_text(encoding='utf8'))


def revisit(s,at,entrance,check):
 e=s.e;s.move([at(3,12)]);e._handle_key(pygame.K_LESS,'<');s.receipt['events']+=1
 assert e.current_submap_id is None;s.checkpoint('inactive')
 for _ in range(8):s.key(pygame.K_PERIOD)
 s.move([entrance]);e._handle_key(pygame.K_GREATER,'>');s.receipt['events']+=1
 check();s.mark('ordinary revisit retains depletion and access');s.checkpoint('returned');capture(e,s.out/'returned.png')


def store(s,at,entrance):
 e=s.e
 for xy in (at(4,11),at(5,12)):s.move([xy]);s.pick('gleaner_flesh')
 s.move([at(10,8)]);s.mark('unlit shelf approach with two acquired portions');s.checkpoint('choice')
 corpse=next(i for i in e.local_map.floor_objects[at(10,5)] if i.item_id=='corpse');crow_uid=corpse.flesh_resource['uid']
 s.harvest(at(10,5));assert not any(i is corpse for rows in e.local_map.floor_objects.values() for i in rows)
 s.move([at(10,5)])
 while any(i.item_id=='crow_meat' for i in e.local_map.floor_objects.get(at(10,5),[])):s.pick('crow_meat')
 s.move([at(5,11)]);s.recipe('cook_meat',{0:'gleaner_flesh'});s.place(at(5,10))
 for _ in range(8):s.key(pygame.K_PERIOD)
 s.approach(at(5,10));s.interact(at(5,10));s.close();assert e.player.inventory.has('cooked_meat');s.mark('conserved flesh becomes useful cooked food')
 s.move([at(22,8)]);s.light(True);s.key(pygame.K_PERIOD);s.mark('conserved route exposes player to original guard position')
 s.receipt['comparisons'].append(dict(branch='conserve',state=s.state()))
 restore(s,'choice');s.move([at(12,5)]);bait=s.portion('gleaner_flesh');bait_uid=bait.flesh_resource['uid'];s.move([at(10,8)])
 actor=next(a for a in e.entities if getattr(a,'_creature_id','')=='gutter_gleaner')
 assert actor.ai.scavenging_state['completed']==0;s.mark('one portion placed while dark; food not yet discovered')
 s.light(True)
 for _ in range(3):
  if actor.ai.scavenging_state['current']:break
  s.key(pygame.K_PERIOD)
 assert actor.ai.scavenging_state['current']['uid']==bait_uid
 s.move([at(11,8)]);s.move([at(13,8)])
 for _ in range(15):
  if actor.ai.scavenging_state['completed']>=1:break
  s.key(pygame.K_PERIOD)
 assert actor.ai.scavenging_state['completed']==1,s.state()
 s.move([at(11,7)])
 for _ in range(3):
  if actor.ai.scavenging_state['current']:break
  s.key(pygame.K_PERIOD)
 assert actor.ai.scavenging_state['current']['uid']==crow_uid
 s.move([at(12,8)]);s.move([at(13,8)])
 for _ in range(15):
  if actor.ai.scavenging_state['completed']>=2:break
  s.key(pygame.K_PERIOD)
 assert actor.ai.scavenging_state['completed']==2,s.state()
 corpse=next(i for i in e.local_map.floor_objects[at(10,5)] if i.item_id=='corpse');assert corpse.flesh_resource['state']=='stripped'
 assert not any(getattr(i,'flesh_resource',{}).get('uid')==bait_uid for rows in e.local_map.floor_objects.values() for i in rows)
 s.mark('loose portion gone and corpse stripped; eater displaced');s.checkpoint('stripped')
 s.move([at(22,8)]);s.move([at(23,5)]);s.pick('resonant_bone_fragment');s.mark('spent-flesh route reaches far-store objective')
 s.receipt['comparisons'].append(dict(branch='spend',state=s.state(),bait_uid=bait_uid))
 # Hostility remains real. Ordinary combat is the cost of approaching the body.
 s.move([at(11,7)]);s.light(True);s.fight(actor);s.mark('hostile interruption and ordinary combat near contested remains')
 before=sum(i.count for i in e.player.inventory.items if i.item_id=='animal_bone')
 s.harvest(at(10,5));s.move([at(10,5)]);s.pick('animal_bone')
 assert sum(i.count for i in e.player.inventory.items if i.item_id=='animal_bone')>before
 assert not any(i.item_id=='crow_meat' for i in e.local_map.floor_objects.get(at(10,5),[]))
 s.mark('stripped crow still yields useful bone through ordinary equipped blade');s.checkpoint('harvested')
 def check():
  assert not any(getattr(i,'flesh_resource',{}).get('uid') in (crow_uid,bait_uid) for rows in e.local_map.floor_objects.values() for i in rows)
 revisit(s,at,entrance,check)


def sump(s,at,entrance):
 e=s.e;s.move([at(5,11)]);s.pick('stalker_meat');s.move([at(11,8)]);s.move([at(11,3)]);s.move([at(14,3)]);s.move([at(14,4)])
 screen=at(14,5);s.mark('screen intact; darkvision beetle cannot see through timber');s.checkpoint('choice')
 s.move([at(11,3)]);s.move([at(11,10)]);s.move([at(22,10)]);s.move([at(22,5)]);s.pick('resonant_bone_fragment')
 assert e.local_map.access_objects[screen]['completed_by'] is None;s.mark('intact southern bypass reaches east objective')
 s.receipt['bypass']=s.state()
 for method in ('Careful','Quick force'):
  restore(s,'choice');turn=e.world_time.turn
  steps=e.local_map.access_objects[screen]['profile']['work_steps'] if method=='Careful' else 1
  for n in range(steps):s.method(screen,method if n==0 else 'Continue')
  s.mark(method+' opening');s.move([at(14,3)]);s.move([at(13,3)]);s.move([at(12,3)]);s.move([at(11,3)]);s.move([at(9,3)])
  for _ in range(6):s.key(pygame.K_PERIOD)
  s.mark(method+' aftermath');s.receipt['comparisons'].append(dict(branch=method,elapsed=e.world_time.turn-turn,state=s.state()))
  capture(e,s.out/(method.replace(' ','-')+'.png'))
 # Preserve one real final branch and remaining harvest/access on revisit.
 corpse=next(i for i in e.local_map.floor_objects.get(at(12,5),[]) if i.item_id=='corpse')
 actor=next(a for a in e.entities if getattr(a,'_creature_id','')=='pale_carrion_beetle')
 for _ in range(20):
  if corpse.flesh_resource['state']=='stripped':break
  s.key(pygame.K_PERIOD)
 s.mark('sump final remaining resources');s.checkpoint('sump-final')
 expected=copy.deepcopy(corpse.flesh_resource)
 def check():
  found=next(i for rows in e.local_map.floor_objects.values() for i in rows if getattr(i,'flesh_resource',{}).get('uid')==expected['uid'])
  assert found.flesh_resource==expected and e.local_map.access_objects[screen]['completed_by']=='force'
 revisit(s,at,entrance,check)


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--which',choices=['store','sump','both'],default='both');args=ap.parse_args();out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
 pygame.init();os.chdir(GAME);results=[]
 for which in (['store','sump'] if args.which=='both' else [args.which]):
  target=out/which;target.mkdir(exist_ok=True);s=None
  with tempfile.TemporaryDirectory(prefix='sys5-ordinary-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)/'saves'):
   try:
    # The boot root is disposable; no save files beneath the repository are read.
    s,at,entrance=stage(which,target,Path(tmp)/'saves')
    from engine import sound
    emitter=sound.emit
    def heard(*args,**kwargs):
     result=emitter(*args,**kwargs)
     s.receipt['sounds'].append(dict(turn=s.e.world_time.turn,x=args[1],y=args[2],event=args[3],receivers=result,
      interests=[dict(id=getattr(a,'_creature_id',''),xy=[a.x,a.y],sound=copy.deepcopy(getattr(getattr(a,'ai',None),'sound_interest',None))) for a in s.e.entities if a is not s.e.player]))
     return result
    with patch('engine.sound.emit',side_effect=heard):(store if which=='store' else sump)(s,at,entrance)
    s.receipt['passed']=True
   finally:
    if s:
     s.receipt['final']=s.state();(target/'journey.json').write_text(json.dumps(s.receipt,indent=2),encoding='utf8');results.append(s.receipt)
 (out/'play.json').write_text(json.dumps(dict(passed=True,journeys=results),indent=2),encoding='utf8');print(json.dumps(dict(passed=True,evidence=str(out))))

if __name__=='__main__':main()
