"""Two selected-world SYS-1 journeys. One disclosed initial public-join staging each.
All later travel, acquisition, fire construction, water, work and use are game inputs.
Disposable saves; no supplies inserted, threats removed, costs or rules overridden.
"""
import argparse,copy,hashlib,json,os,random,subprocess,sys,tempfile,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];GAME=ROOT/'roguelike'
sys.path[:0]=[str(GAME),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from engine.save_components import serialize_item
from engine.save_manager import _serialize_player,_serialize_world,SceneAddress
from verify_ai_6_play import capture,display
from g10_play import path,status,KEYS
KEYS.update({(-1,-1):pygame.K_KP7,(1,-1):pygame.K_KP9,(-1,1):pygame.K_KP1,(1,1):pygame.K_KP3})


def snapshot(e):
 m=e.local_map
 jobs=[]
 for xy,r in sorted(m.processing_layer.items()):
  row=copy.deepcopy(r)
  if 'vessel_job' in row:row['vessel_job']['vessel']=serialize_item(row['vessel_job']['vessel'])
  jobs.append([list(xy),row])
 return json.loads(json.dumps(dict(player=_serialize_player(e),turn=e.world_time.turn,scene=[e.world_x,e.world_y,e.current_submap_id],
  world_sha256=hashlib.sha256(json.dumps(_serialize_world(e.world_map),sort_keys=True).encode()).hexdigest(),jobs=jobs,
  containers=[[list(xy),[serialize_item(i) if not isinstance(i,dict) else i for i in c['items']]] for xy,c in sorted(m.container_state.items())],
  floor=[[list(xy),[serialize_item(i) for i in rows]] for xy,rows in sorted(m.floor_objects.items())])))


class Journey:
 def __init__(self,e,out):self.e=e;self.out=out;self.receipt={'controls':__doc__,'events':0,'checkpoints':[],'stages':[]}
 def key(self,k):
  self.e._handle_key(k);self.receipt['events']+=1
  assert not self.e._player_is_dead,('player died',status(self.e))
 def stage(self,label):
  self.receipt['stages'].append(dict(label=label,state=status(self.e),logs=[m.text for m in self.e.log.messages][-8:]))
  print(label,status(self.e)['turn'],flush=True)
 def close(self):
  e=self.e
  for _ in range(5):
   if not (e.inventory_screen.open or e.craft_screen.open or e.text_reader.open or e.lexicon_screen.open or e.interaction_cursor._selection_prompt or getattr(e,'_vessel_menu',None) or e.mode.value!='local'):return
   self.key(pygame.K_ESCAPE)
  raise AssertionError('modal did not close')
 def move(self,goals):
  goals=set(goals)
  for _ in range(400):
   if (self.e.player.x,self.e.player.y) in goals:return
   route=path(self.e,goals,prefer_firm=True);a,b=route[:2];self.key(KEYS[b[0]-a[0],b[1]-a[1]])
  raise AssertionError(('route budget',status(self.e),goals))
 def approach(self,xy):
  from engine.interaction_cursor import InteractionCursor
  goals={(xy[0]+dx,xy[1]+dy) for dx,dy in [(0,0),(0,1),(0,-1),(1,0),(-1,0)] if self.e.local_map.in_bounds(xy[0]+dx,xy[1]+dy)}
  for _ in range(8):
   self.move(goals)
   if InteractionCursor.can_reach(self.e,*xy):return
   goals.discard((self.e.player.x,self.e.player.y))
  raise AssertionError(('unreachable target',xy))
 def interact(self,xy):
  e=self.e;self.key(pygame.K_e)
  while e.interaction_cursor.cursor_x!=xy[0]:self.key(pygame.K_RIGHT if e.interaction_cursor.cursor_x<xy[0] else pygame.K_LEFT)
  while e.interaction_cursor.cursor_y!=xy[1]:self.key(pygame.K_DOWN if e.interaction_cursor.cursor_y<xy[1] else pygame.K_UP)
  self.key(pygame.K_RETURN)
 def take(self,xy,iid):
  e=self.e;self.approach(xy);self.interact(xy)
  p=e.interaction_cursor._selection_prompt;assert p,(iid,status(e),[m.text for m in e.log.messages][-8:])
  n=next(n for n,i in enumerate(p['items']) if i.item_id==iid)
  while p['selected']!=n:self.key(pygame.K_DOWN if p['selected']<n else pygame.K_UP)
  self.key(pygame.K_RETURN);self.close()
  assert e.player.inventory.has(iid)
 def item(self,iid):
  e=self.e
  if not e.inventory_screen.open:self.key(pygame.K_i)
  e.inventory_screen.render(pygame.Surface((1280,900)),e)
  for _ in range(100):
   i=e.inventory_screen._selected_item()
   if i and i.item_id==iid:self.key(pygame.K_e);return
   self.key(pygame.K_DOWN)
  raise AssertionError(iid)
 def choice(self,n=0):
  for _ in range(n):self.key(pygame.K_DOWN)
  self.key(pygame.K_RETURN)
 def recipe(self,iid,vessel=None):
  e=self.e;self.key(pygame.K_c);s=e.craft_screen
  flat=s._build_flat_items(s._get_recipes(e));n=next(n for n,r in enumerate(flat) if r.get('recipe',{}).get('id')==iid)
  while s.selected!=n:self.key(pygame.K_DOWN if s.selected<n else pygame.K_UP)
  self.key(pygame.K_RETURN)
  while s._choosing:
   p=s._choice_prompts[s._choice_index];n=next(n for n,o in enumerate(p['options']) if o['item_id']==(vessel or 'wood_bundle'))
   while s._choice_selected!=n:self.key(pygame.K_DOWN if s._choice_selected<n else pygame.K_UP)
   self.key(pygame.K_RETURN)
 def place(self,xy):
  e=self.e;assert e.mode.value=='placement_cursor',(e.mode,[m.text for m in e.log.messages][-5:])
  while e._placement_cursor_x!=xy[0]:self.key(pygame.K_RIGHT if e._placement_cursor_x<xy[0] else pygame.K_LEFT)
  while e._placement_cursor_y!=xy[1]:self.key(pygame.K_DOWN if e._placement_cursor_y<xy[1] else pygame.K_UP)
  self.key(pygame.K_RETURN)
 def checkpoint(self,label):
  e=self.e;before=snapshot(e);self.key(pygame.K_F5);self.key(pygame.K_F9)
  after=snapshot(e)
  if before!=after:
   (self.out/(label+'-difference.json')).write_text(json.dumps(dict(before=before,after=after),indent=2),encoding='utf8')
  assert before==after,(label,e.save_manager.last_error)
  archive=self.out/(label+'.zip')
  with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
   for p in e.save_manager.checkpoint_path().rglob('*'):
    if p.is_file():z.write(p,p.relative_to(e.save_manager.checkpoint_path()))
  expected=self.out/(label+'.json');expected.write_text(json.dumps(before),encoding='utf8')
  cold=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--cold',str(archive)],capture_output=True,text=True,timeout=120)
  assert cold.returncode==0,cold.stdout+cold.stderr
  result=json.loads(cold.stdout.splitlines()[-1]);assert result['pid']!=os.getpid()
  self.receipt['checkpoints'].append(dict(label=label,f5_f9_equal=True,cold=result,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))


def journey(which,out):
 from g10_play import boot
 from engine.interaction_cursor import InteractionCursor
 from generation.access import enterable
 spec=(dict(chunk=(17,55),suffix='81-3-S-0-building',bone=(7,11),vessel=(15,13),iid='copper_steeping_kettle',corner=(79,0),cross=pygame.K_KP9,destination=(18,54),wood=[(34,13),(37,14)],water=(14,8)) if which=='kettle' else
       dict(chunk=(16,56),suffix='42-66-N-0-building',bone=(64,31),vessel=(56,29),iid='clay_pot',corner=(0,42),cross=pygame.K_KP1,destination=(15,57),wood=[(75,5),(70,5)],water=(50,22)))
 with tempfile.TemporaryDirectory(prefix='sys1-ordinary-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)/'saves'):
  e=boot(Path(tmp)/'saves',seed=20261024);e.rng=random.Random(20261020);e.ai_system._rng=random.Random(20261020)
  p=next(p for p in e.world_map.plan['placements'] if p['asset']=='apothecary_b' and p['id'].endswith(spec['suffix']))
  wx,wy=spec['chunk'];prepared=e._ensure_surface_scene(wx,wy);SceneAddress(e.world_x,e.world_y,e.current_submap_id).store(e.save_manager.cache,e.local_map,e.entities)
  e.local_map,natives=prepared;e.world_x,e.world_y,e.current_submap_id=wx,wy,None;e.entities=[e.player]+natives
  e.player.x,e.player.y=p['join'][0]%80,p['join'][1]%43;e.world_map.get(wx,wy).visited=True;e._update_fov();display(e)
  s=Journey(e,out);s.receipt.update(seed=20261024,placement=p,native_stock={str(xy):[serialize_item(i) for i in c['items']] for xy,c in e.local_map.container_state.items()},initial=status(e))
  try:
   s.stage('selected public approach');capture(e,out/'arrival.png')
   s.item('crude_blade');s.close();s.item('leather_jack');s.close()
   s.take(spec['bone'],'resonant_bone_fragment');s.take(spec['vessel'],spec['iid'])
   if which=='clay':s.take(spec['vessel'],'waxed_water_flask')
   note=next((xy for xy,c in sorted(e.local_map.container_state.items(),key=lambda row:abs(row[0][0]-e.player.x)+abs(row[0][1]-e.player.y)) if any(i.item_id=='steeping_note' for i in c['items'])),None)
   if note:
    s.take(note,'steeping_note');words=set(e.player.language.known_deep_words);s.item('steeping_note');assert e.text_reader.open
    capture(e,out/'optional-note.png');s.close();assert words==e.player.language.known_deep_words
   s.stage('acquired native bone and vessel');s.checkpoint('acquired')
   s.move([spec['corner']]);s.key(spec['cross']);assert (e.world_x,e.world_y)==spec['destination'],status(e)
   for _ in range(2):
    candidates=[]
    for x in range(e.local_map.width):
     for y in range(e.local_map.height):
      if str(e.local_map.tiles[x,y]['terrain'])!='dead_wood':continue
      goals={(x+dx,y+dy) for dx,dy in [(0,0),(0,1),(0,-1),(1,0),(-1,0)] if e.local_map.in_bounds(x+dx,y+dy)}
      try:route=path(e,goals,prefer_firm=True)
      except AssertionError:continue
      candidates.append((len(route),(x,y)))
    assert candidates,'No normally reachable dead wood'
    xy=min(candidates)[1];s.receipt.setdefault('harvested_native_wood',[]).append(list(xy))
    s.approach(xy);s.interact(xy);s.close()
   assert sum(i.count for i in e.player.inventory.items if i.item_id=='wood_bundle')>=2
   fill_id='waxed_water_flask' if which=='clay' else spec['iid']
   s.approach(spec['water']);s.item(fill_id);s.choice();s.choice();s.choice()
   assert e.player.inventory.get_by_id(fill_id).vessel['water_ml']==250
   v=e.player.inventory.get_by_id(spec['iid'])
   vessel_id=v.vessel['id'];s.stage('measured native water and gathered fuel');capture(e,out/'water.png')
   fire=next((e.player.x+dx,e.player.y+dy) for dx,dy in KEYS if e._check_placement_valid(e.player.x+dx,e.player.y+dy) and InteractionCursor.can_reach(e,e.player.x+dx,e.player.y+dy) and (e.player.x+dx,e.player.y+dy) not in e.local_map.decor and not e.data.terrain.get(str(e.local_map.tiles[e.player.x+dx,e.player.y+dy]['terrain']),{}).get('drinkable'))
   s.recipe('campfire');s.place(fire);assert e.local_map.decor.get(fire)=='campfire_unlit'
   s.interact(fire);s.close();assert e.local_map.decor.get(fire)=='campfire_lit',(fire,[m.text for m in e.log.messages][-5:])
   if which=='clay':
    before=snapshot(e);s.recipe('resonant_bone_tincture','waxed_water_flask')
    assert e.mode.value=='local' and before==snapshot(e)
    assert any('heatproof' in m.text for m in e.log.messages)
    s.receipt['unsuitable_rejected_without_cost']=True;capture(e,out/'unsuitable-carrier.png');s.close()
    s.item('waxed_water_flask');s.choice(1);s.choice();s.choice()
    assert e.player.inventory.get_by_id('waxed_water_flask').vessel['water_ml']==0
    assert e.player.inventory.get_by_id('clay_pot').vessel['water_ml']==250
    s.stage('transferred the batch to suitable found clay pot')
   s.recipe('resonant_bone_tincture',spec['iid']);work=(e.player.x,e.player.y);s.place(work)
   assert len(e.local_map.processing_layer)==1;assert e.local_map.processing_layer[work]['turns_remaining']==34
   assert not e.player.inventory.has(spec['iid']);s.stage('ordinary preparation busy');capture(e,out/'busy.png');s.checkpoint('busy')
   for _ in range(34):s.key(pygame.K_PERIOD)
   assert not e.local_map.processing_layer
   for iid in (spec['iid'],'resonant_bone_tincture'):
    s.key(pygame.K_COMMA)
    prompt=e.interaction_cursor._selection_prompt
    if prompt:
     n=next(n for n,i in enumerate(prompt['items']) if i.item_id==iid)
     while prompt['selected']!=n:s.key(pygame.K_DOWN if prompt['selected']<n else pygame.K_UP)
     s.key(pygame.K_RETURN);s.close()
   v=e.player.inventory.get_by_id(spec['iid']);assert v.vessel['id']==vessel_id and v.vessel['water_ml']==0
   before=set(e.player.language.known_deep_words);s.item('resonant_bone_tincture');s.close()
   learned=e.player.language.known_deep_words-before;assert len(learned)==1 and not e.player.inventory.has('resonant_bone_tincture')
   s.key(pygame.K_l);assert e.lexicon_screen.open;capture(e,out/'learned-lexicon.png');s.key(pygame.K_ESCAPE)
   s.receipt['learned']=[dict(id=wid,definition=e.data.deep_tongue[wid]) for wid in learned];s.stage('dose consumed and lexicon read');s.checkpoint('learned')
   # Ordinary boundary travel back to the very same selected shop and owners.
   if which=='kettle':
    s.move([(0,42)]);s.key(pygame.K_KP1)
   else:
    # The NE forest corner is a tree; use the open eastern boundary then north.
    goals=[(79,y) for y in range(43) if enterable(e.local_map,(79,y),e.data)];s.move(goals);s.key(pygame.K_RIGHT)
    goals=[(x,0) for x in range(80) if enterable(e.local_map,(x,0),e.data)];s.move(goals);s.key(pygame.K_UP)
   assert (e.world_x,e.world_y)==spec['chunk'],status(e)
   s.approach(spec['bone']);s.interact(spec['bone']);assert not any(i.item_id=='resonant_bone_fragment' for i in e.local_map.container_state[spec['bone']]['items']);s.close()
   s.approach(spec['vessel']);s.interact(spec['vessel']);assert not any(i.item_id==spec['iid'] for i in e.local_map.container_state[spec['vessel']]['items']);s.close()
   s.stage('returned to depleted native owners');capture(e,out/'returned.png');s.checkpoint('returned');s.receipt['passed']=True
  finally:
   s.receipt['final']=status(e);(out/'journey.json').write_text(json.dumps(s.receipt,indent=2),encoding='utf8')
 return s.receipt


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path);ap.add_argument('--cold',type=Path);args=ap.parse_args()
 if args.evidence:args.evidence=args.evidence.resolve()
 if args.cold:args.cold=args.cold.resolve()
 pygame.init();os.chdir(GAME)
 if args.cold:
  from g12_journey import install_checkpoint
  from test_effect_persistence import make_engine,load_data
  with tempfile.TemporaryDirectory(prefix='sys1-cold-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)):
   install_checkpoint(args.cold,tmp);e=make_engine(load_data());assert e.save_manager.load(e),e.save_manager.last_error
   assert snapshot(e)==json.loads(args.cold.with_suffix('.json').read_text(encoding='utf8'))
   print(json.dumps(dict(passed=True,pid=os.getpid(),state_equal=True)))
  return
 out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True);rows=[]
 for which in ('kettle','clay'):
  folder=out/which;folder.mkdir();rows.append(journey(which,folder))
 (out/'play.json').write_text(json.dumps(dict(passed=True,journeys=rows),indent=2),encoding='utf8')
 print(json.dumps(dict(passed=True,evidence=str(out))))


if __name__=='__main__':main()
