"""SYS-4 selected-world journey. One disclosed initial public-join staging.
Thereafter only ordinary game keys acquire, prepare, travel, work, retreat and save.
Comparison branches restore the same genuine F5; no stock/actor/safety fixtures.
"""
import argparse,copy,hashlib,json,os,random,subprocess,sys,tempfile,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];GAME=ROOT/'roguelike'
sys.path[:0]=[str(GAME),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from verify_sys_3_play import Journey as BaseJourney,snapshot as old_snapshot
from engine.save_components import serialize_item
from engine.save_manager import SceneAddress
from g10_play import boot,path,status,KEYS
from verify_ai_6_play import capture,display
KEYS.update({(-1,-1):pygame.K_KP7,(1,-1):pygame.K_KP9,(-1,1):pygame.K_KP1,(1,1):pygame.K_KP3})


def snapshot(e):
 d=old_snapshot(e);m=e.local_map
 d.update(access=[[list(xy),copy.deepcopy(row)] for xy,row in sorted(m.access_objects.items())],
          access_manifest={'version':m.access_manifest['version'],'owners':[[list(xy),v] for xy,v in sorted(m.access_manifest['owners'].items())]} if hasattr(m,'access_manifest') else None,
          terrain=m.tiles['terrain'].tolist(),walkable=m.walkable.tolist(),transparent=m.transparent.tolist())
 return json.loads(json.dumps(d))


class Journey(BaseJourney):
 def sustain(self):
  e=self.e
  for need,iid,threshold in [('thirst','water_flask',.65),('thirst','water_skin',.65),('hunger','crow_jerky',.6)]:
   if getattr(e.player.needs,need)>threshold and e.player.inventory.has(iid):self.item(iid);self.close()
  if e.player.fighter.hp<23 and e.player.inventory.has('herbal_dressing'):self.item('herbal_dressing');self.close()
 def move(self,goals):
  goals=set(goals);e=self.e
  for _ in range(600):
   self.sustain()
   close=[a for a in e.entities if a is not e.player and getattr(a,'ai',None) and getattr(a.ai.state,'name','') in ('HUNTING','ATTACKING') and max(abs(a.x-e.player.x),abs(a.y-e.player.y))<=1]
   if close:
    a=close[0];self.key(KEYS[(a.x>e.player.x)-(a.x<e.player.x),(a.y>e.player.y)-(a.y<e.player.y)]);continue
   if (e.player.x,e.player.y) in goals:return
   route=path(e,goals,prefer_firm=False);a,b=route[:2];self.key(KEYS[b[0]-a[0],b[1]-a[1]])
  raise AssertionError(('route budget',status(e),goals))
 def stage(self,label):
  super().stage(label);self.receipt['stages'][-1]['access']=snapshot(self.e)['access']
 def checkpoint(self,label):
  e=self.e;before=snapshot(e);self.key(pygame.K_F5);self.key(pygame.K_F9)
  after=snapshot(e)
  if before!=after:(self.out/(label+'-difference.json')).write_text(json.dumps(dict(before=before,after=after),indent=2),encoding='utf8')
  assert before==after,(label,e.save_manager.last_error)
  archive=self.out/(label+'.zip')
  with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
   for p in e.save_manager.checkpoint_path().rglob('*'):
    if p.is_file():z.write(p,p.relative_to(e.save_manager.checkpoint_path()))
  archive.with_suffix('.json').write_text(json.dumps(before),encoding='utf8')
  cold=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--cold',str(archive)],capture_output=True,text=True,timeout=120)
  assert cold.returncode==0,cold.stdout+cold.stderr
  result=json.loads(cold.stdout.splitlines()[-1]);assert result['pid']!=os.getpid()
  self.receipt['checkpoints'].append(dict(label=label,f5_f9_equal=True,cold=result,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
 def method(self,xy,method,dose=None):
  self.interact(xy);menu=self.e._vessel_menu;assert menu,(xy,[m.text for m in self.e.log.messages][-8:])
  n=next(n for n,(t,_) in enumerate(menu['options']) if t.startswith(method));self.choice(n)
  if method=='Dissolution':
   n=next(n for n,(t,_) in enumerate(self.e._vessel_menu['options']) if dose is None or t.startswith(dose.name+':'))
   self.choice(n)
  self.close()
 def boundary(self,dx,dy):
  e=self.e;old=e.world_x,e.world_y
  from generation.access import enterable
  if dx:goals={(79 if dx>0 else 0,y) for y in range(43) if enterable(e.local_map,(79 if dx>0 else 0,y),e.data)}
  else:goals={(x,42 if dy>0 else 0) for x in range(80) if enterable(e.local_map,(x,42 if dy>0 else 0),e.data)}
  # Choose a central reachable edge, avoiding disconnected corner landings.
  for goal in sorted(goals,key=lambda xy:abs(xy[1]-21) if dx else abs(xy[0]-40)):
   try:path(e,{goal},prefer_firm=True)
   except AssertionError:continue
   self.move([goal]);break
  else:raise AssertionError('No reachable boundary')
  self.key(KEYS[dx,dy]);assert (e.world_x,e.world_y)==(old[0]+dx,old[1]+dy),status(e)
 def pick(self,iid):
  self.key(pygame.K_COMMA);p=self.e.interaction_cursor._selection_prompt
  if p:
   n=next(n for n,i in enumerate(p['items']) if i.item_id==iid)
   while p['selected']!=n:self.key(pygame.K_DOWN if p['selected']<n else pygame.K_UP)
   self.key(pygame.K_RETURN)
  self.close()


def journey(out):
 from engine.interaction_cursor import InteractionCursor
 from engine import sound
 from generation.access import enterable,reachable
 with tempfile.TemporaryDirectory(prefix='sys4-ordinary-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)/'saves'):
  e=boot(Path(tmp)/'saves',seed=20261023);e.rng=random.Random(20261020);e.ai_system._rng=random.Random(20261020)
  p=next(p for p in e.world_map.plan['placements'] if p['asset']=='workshop_e' and p['id']=='settlement-0-cross-market-lot-1-44-S-0-building')
  wx,wy=75,100;prepared=e._ensure_surface_scene(wx,wy);SceneAddress(e.world_x,e.world_y,e.current_submap_id).store(e.save_manager.cache,e.local_map,e.entities)
  e.local_map,natives=prepared;e.world_x,e.world_y,e.current_submap_id=wx,wy,None;e.entities=[e.player]+natives
  e.player.x,e.player.y=p['join'][0]%80,p['join'][1]%43;e.world_map.get(wx,wy).visited=True;e._update_fov();display(e)
  s=Journey(e,out);s.receipt.update(controls=__doc__,seed=20261023,placement=p,initial=status(e),sounds=[],comparisons=[])
  emitter=sound.emit
  def heard(*args,**kwargs):
   result=emitter(*args,**kwargs)
   s.receipt['sounds'].append(dict(turn=e.world_time.turn,x=args[1],y=args[2],event=args[3],receivers=result,actors=[dict(id=getattr(a,'_creature_id',''),x=a.x,y=a.y,state=str(getattr(getattr(a,'ai',None),'state',None)),interest=copy.deepcopy(getattr(getattr(a,'ai',None),'sound_interest',None))) for a in e.entities if a is not e.player]));return result
  def item(iid):return e.player.inventory.get_by_id(iid)
  try:
   with patch('engine.sound.emit',side_effect=heard):
    s.stage('selected workshop public approach');capture(e,out/'surface-arrival.png')
    s.item('crude_blade');s.close();s.item('leather_jack');s.close()
    coffer=(25,11);original=[serialize_item(i) for i in e.local_map.container_state[coffer]['items']]
    s.approach(coffer);s.method(coffer,'Careful');assert e.local_map.access_objects[coffer]['progress']==1
    s.checkpoint('coffer-partial');s.stage('one careful step; withdraw with progress retained')
    s.move([(24,15)]);s.approach(coffer)
    for _ in range(2):s.method(coffer,'Continue')
    assert [serialize_item(i) for i in e.local_map.container_state[coffer]['items']]==original
    for iid in ('dried_bitter_herb','wood_bundle'):s.take(coffer,iid)
    s.take((18,11),'wood_bundle')
    for iid in ('water_flask','crow_jerky','herbal_dressing','tallow_torch'):s.take((25,15),iid)
    for iid in ('clay_pot','crow_bile','etching_wash'):s.take((56,29),iid)
    s.take((64,31),'herbal_dressing');s.take((60,27),'crow_jerky')
    finished=item('etching_wash');assert finished.coating_dose['hits']==6
    s.stage('earned original coffer goods and acquired actual apothecary kit');s.checkpoint('surface-looted')
    # Actual roads and chunk boundaries to the selected barrow's wet surface.
    for dx,dy in [(1,0),(0,-1),(1,0),(1,0),(0,1)]:s.boundary(dx,dy)
    assert (e.world_x,e.world_y)==(78,100)
    waters=[(x,y) for x in range(80) for y in range(43) if e.data.terrain.get(str(e.local_map.tiles[x,y]['terrain']),{}).get('drinkable')]
    water=min(waters,key=lambda xy:len(path(e,{(xy[0]+dx,xy[1]+dy) for dx,dy in KEYS if e.local_map.in_bounds(xy[0]+dx,xy[1]+dy) and enterable(e.local_map,(xy[0]+dx,xy[1]+dy),e.data)},prefer_firm=True)))
    s.approach(water);s.item('clay_pot');s.choice();s.choice();s.choice(next(n for n,(title,_) in enumerate(e._vessel_menu['options']) if '125 mL' in title));s.close()
    vessel=item('clay_pot');vessel_id=vessel.vessel['id'];assert vessel.vessel['water_ml']==125
    fire=next((e.player.x+dx,e.player.y+dy) for dx,dy in KEYS if e._check_placement_valid(e.player.x+dx,e.player.y+dy) and InteractionCursor.can_reach(e,e.player.x+dx,e.player.y+dy) and (e.player.x+dx,e.player.y+dy) not in e.local_map.decor and not e.data.terrain.get(str(e.local_map.tiles[e.player.x+dx,e.player.y+dy]['terrain']),{}).get('drinkable'))
    s.recipe('campfire');s.place(fire);s.interact(fire);s.close()
    s.recipe('etching_wash',{0:'crow_bile',1:'dried_bitter_herb','vessel':'clay_pot'});work=(e.player.x,e.player.y);s.place(work)
    assert e.local_map.processing_layer[work]['turns_remaining']==14;s.checkpoint('wash-busy')
    for _ in range(14):s.key(pygame.K_PERIOD)
    s.pick('clay_pot');s.pick('etching_wash');assert item('clay_pot').vessel['id']==vessel_id
    prepared=next(i for i in e.player.inventory.items if i.item_id=='etching_wash' and i.coating_dose['hits']==12)
    prepared_payload=copy.deepcopy(prepared.coating_dose);s.stage('self-prepared twelve-contact wash, same vessel returned');s.checkpoint('wash-ready')
    # Normal physical stairs and production assigned layout; never create_submap by hand.
    entrance=next(xy for xy,sid in e.local_map.submap_links.items() if sid=='submap_78_100_0');s.move([entrance]);e._handle_key(pygame.K_GREATER,'>');s.receipt['events']+=1
    assert e.current_submap_id=='submap_78_100_0';assert e.world_map.get(78,100).submaps[0].layout_id=='barrow_bound_store'
    screen=next(xy for xy,r in e.local_map.access_objects.items() if r['host']=='screen');coffer=next(xy for xy,r in e.local_map.access_objects.items() if r['host']=='container')
    actor=next(a for a in e.entities if getattr(a,'_creature_id','')=='hollow_revenant');s.receipt['barrow']=dict(entrance=list(entrance),screen=list(screen),coffer=list(coffer),native=status(e)['actors'])
    # This natural approach remains on the near side; the longer route is available.
    s.move([(screen[0]-1,screen[1])]);assert not e.local_map.walkable[screen]
    from engine.held_light import active_item
    if active_item(e.player):s.item(active_item(e.player).item_id);s.close()
    baseline=snapshot(e);s.checkpoint('barrow-intact');rng=e.rng.getstate();ai_rng=e.ai_system._rng.getstate()
    from g12_journey import install_checkpoint
    def restore():
     install_checkpoint(out/'barrow-intact.zip',e.save_manager.save_path.parent)
     s.key(pygame.K_F9);e.rng.setstate(rng);e.ai_system._rng.setstate(ai_rng);assert snapshot(e)==baseline
    s.move([(screen[0]+1,screen[1]+6)])
    assert e.local_map.access_objects[screen]['completed_by'] is None
    s.receipt['bypass']=dict(intact=True,from_position=[screen[0]-1,screen[1]],arrived=status(e),note='Actual keys around the southern end; restored the genuine initial checkpoint for comparisons.')
    for method in ('Careful','Quick force','Dissolution'):
     restore()
     prepared=next(i for i in e.player.inventory.items if i.item_id=='etching_wash' and i.coating_dose['hits']==12)
     # Select by contact label when two same-ID eligible instances are carried.
     from engine.illumination import scene_light
     turn=e.world_time.turn;before=status(e);before_sound=len(s.receipt['sounds']);before_visible=bool(e.local_map.visible[screen[0]+3,screen[1]])
     assert not scene_light(e).lit[screen[0]-1,screen[1]] and not before_visible
     s.interact(screen);n=next(n for n,(t,_) in enumerate(e._vessel_menu['options']) if t.startswith(method));s.choice(n)
     if method=='Dissolution':
      n=next(n for n,(t,_) in enumerate(e._vessel_menu['options']) if '12 weapon contacts' in t);s.choice(n)
     s.close()
     if method=='Careful':
      s.stage('living encounter after first cut');assert e.local_map.access_objects[screen]['progress']==1
      for _ in range(2):s.method(screen,'Continue')
     assert e.local_map.walkable[screen] and e.local_map.transparent[screen]
     assert scene_light(e).lit[screen[0]-1,screen[1]] and e.local_map.visible[screen[0]+3,screen[1]]
     assert e.world_time.turn-turn==(3 if method=='Careful' else 1)
     rows=e.local_map.floor_objects.get(screen,[]);assert [i.item_id for i in rows]==(['wood_bundle'] if method=='Careful' else [])
     if method=='Dissolution':assert not e.player.inventory.contains(prepared)
     else:assert e.player.inventory.contains(prepared) and prepared.coating_dose==prepared_payload
     s.receipt['comparisons'].append(dict(method=method,before=before,after=status(e),before_visible=before_visible,after_visible=bool(e.local_map.visible[screen[0]+3,screen[1]]),sounds=s.receipt['sounds'][before_sound:],dose_spent=method=='Dissolution',salvage=[i.item_id for i in rows]))
     capture(e,out/(method.replace(' ','-')+'.png'))
     s.key(pygame.K_RIGHT);assert (e.player.x,e.player.y)==screen
     s.key(pygame.K_RIGHT);assert (e.player.x,e.player.y)==(screen[0]+1,screen[1])
     s.receipt['comparisons'][-1]['crossed_shortcut']=status(e)
     if method=='Careful':
      s.key(pygame.K_LEFT);assert (e.player.x,e.player.y)==screen
      s.pick('wood_bundle');assert e.player.inventory.has('wood_bundle');assert not e.local_map.floor_objects.get(screen)
      s.checkpoint('careful-salvage-carried')
    quiet=s.receipt['comparisons'][0]['sounds'];loud=s.receipt['comparisons'][1]['sounds']
    assert all(a['interest'] is None for p in quiet for a in p['actors'])
    assert any(a['interest'] and a['interest']['kind']=='dismantle' for p in loud for a in p['actors'])
    # Retain a distinct partial-work -> wash finish, and exercise actual retreat.
    restore()
    s.method(screen,'Careful');s.move([(screen[0]-2,screen[1]+1)]);s.move([(screen[0]-1,screen[1])]);s.interact(screen);s.choice(2)
    s.choice(next(n for n,(t,_) in enumerate(e._vessel_menu['options']) if '12 weapon contacts' in t));s.close()
    assert e.local_map.access_objects[screen]['completed_by']=='dissolution';assert not e.local_map.floor_objects.get(screen)
    assert not any(i.item_id=='etching_wash' and i.coating_dose['hits']==12 for i in e.player.inventory.items)
    s.key(pygame.K_RIGHT);assert (e.player.x,e.player.y)==screen
    s.key(pygame.K_RIGHT);assert (e.player.x,e.player.y)==(screen[0]+1,screen[1])
    s.key(pygame.K_LEFT);s.key(pygame.K_LEFT)
    s.stage('withdrew from partial work, returned and spent whole self-prepared wash')
    # Accessible coffer remains original loot, opened by one force action.
    s.approach(coffer);original=list(e.local_map.container_state[coffer]['items']);s.method(coffer,'Quick force');assert e.local_map.container_state[coffer]['items']==original
    for i in list(original):s.take(coffer,i.item_id)
    s.stage('second ordinary context opened and looted');s.checkpoint('barrow-looted')
    stairs=next((x,y) for x in range(e.local_map.width) for y in range(e.local_map.height) if str(e.local_map.tiles[x,y]['terrain'])=='stairs_up')
    s.move([stairs]);e._handle_key(pygame.K_LESS,'<');s.receipt['events']+=1;assert e.current_submap_id is None
    s.checkpoint('barrow-inactive');s.move([entrance]);e._handle_key(pygame.K_GREATER,'>');s.receipt['events']+=1
    assert e.local_map.access_objects[screen]['completed_by']=='dissolution' and not e.local_map.container_state[coffer]['items']
    s.stage('ordinary return retains cleared shortcut and depleted original coffer');capture(e,out/'returned.png');s.checkpoint('returned')
    s.receipt['passed']=True
  finally:
   s.receipt['final']=status(e);s.receipt['inventory']=[serialize_item(i) for i in e.player.inventory.items]
   (out/'journey.json').write_text(json.dumps(s.receipt,indent=2),encoding='utf8')
 return s.receipt


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path);ap.add_argument('--cold',type=Path);args=ap.parse_args()
 if args.evidence:args.evidence=args.evidence.resolve()
 if args.cold:args.cold=args.cold.resolve()
 pygame.init();os.chdir(GAME)
 if args.cold:
  from g12_journey import install_checkpoint
  from test_effect_persistence import make_engine,load_data
  with tempfile.TemporaryDirectory(prefix='sys4-cold-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)):
   install_checkpoint(args.cold,tmp);e=make_engine(load_data());assert e.save_manager.load(e),e.save_manager.last_error
   assert snapshot(e)==json.loads(args.cold.with_suffix('.json').read_text(encoding='utf8'))
   print(json.dumps(dict(passed=True,pid=os.getpid(),state_equal=True)))
  return
 out=args.evidence;out.mkdir(parents=True,exist_ok=True);r=journey(out)
 (out/'play.json').write_text(json.dumps(dict(passed=True,journey=r),indent=2),encoding='utf8');print(json.dumps(dict(passed=True,evidence=str(out))))

if __name__=='__main__':main()
