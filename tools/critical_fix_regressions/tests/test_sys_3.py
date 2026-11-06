"""SYS-3 physical material response, owned dose, transactions and genuine saves."""
import copy
import json
import os
import pickle
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
import pygame
from test_effect_persistence import load_data,make_engine
from test_gameplay_g12 import use
from engine import coating_doses as doses, material_response as response, vessels
from engine.crafting import plan_craft
from engine.save_components import serialize_item,restore_item,validate_item
from rendering.craft_screen import CraftScreen
from generation.decor_utils import place_decor
from engine.inventory_screen import _flat_list,_group_items

ROOT=Path(__file__).resolve().parents[3]


class WashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();cls.data=load_data()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='sys3-test-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'saves'
        with patch('engine.save_manager.SAVE_DIR',self.root):self.e=make_engine(copy.copy(self.data))
        self.e.data.items=copy.deepcopy(self.data.items);self.e.data.recipes=copy.deepcopy(self.data.recipes)
        self.e.debug=False
        place_decor(self.e.local_map,13,12,'campfire_lit');self.e._update_fov()

    def item(self,iid):
        i=self.e.item_factory.create(iid);self.assertTrue(self.e.player.inventory.add(i));return i

    def setup_batch(self,iid='binding_wash',tier=1):
        r=self.e.data.recipes[iid];tag=r['material_response']['tag']
        primary=self.item('coldbell_cutting' if tag=='binding' else 'sulphur_cap_fragment')
        primary.keywords=[dict(tag=tag,tier=tier)]
        fix=self.item('dried_bitter_herb');pot=self.item('small_steeping_cup');vessels.set_water(pot,125)
        return r,primary,fix,pot

    def plan(self,r,choice=None):
        p,m=plan_craft(r,self.e.player.inventory,ambient_sources=CraftScreen._build_ambient_sources(self.e),chosen_items=choice)
        self.assertFalse(m,m);return p

    def start(self,r,p):
        self.e._start_processing_placement(r,p);self.e._placement_cursor_x,self.e._placement_cursor_y=12,11
        self.e._handle_key(pygame.K_RETURN)
        return self.e.local_map.processing_layer.get((12,11))

    def finish(self):
        for _ in range(14):self.e._handle_key(pygame.K_PERIOD)
        return self.e.local_map.floor_objects[(12,11)][1]

    def weapon(self):
        w=self.item('binding_knife');self.e.player.equipment.equip(w,'weapon');return w

    def test_exact_same_id_primary_low_high_duplicates_and_nonprimary_pack(self):
        r,low,fix,pot=self.setup_batch();high=self.item(low.item_id)
        high.keywords=[dict(tag='binding',tier=2),dict(tag='binding',tier=1),dict(tag='binding',tier=2)]
        for ordering in (high.keywords,list(reversed(high.keywords))):
            high.keywords=ordering
            self.assertIs(low,self.plan(r).roles['primary'])
            for i,hits in ((low,6),(high,12)):
                p=self.plan(r,{0:i});self.assertIs(i,p.roles['primary']);self.assertEqual(hits,p.primary_state['hits'])
                self.assertEqual(hits,response.output(r,p,self.e.item_factory)['coating_dose']['hits'])
        prompts=CraftScreen._find_ambiguous_components(r,self.e.player.inventory,self.e.data.keywords)
        self.assertEqual({id(low),id(high)},{id(o['instance']) for o in prompts[0]['options']})
        self.assertIn('12 contacts',next(o for o in prompts[0]['options'] if o['instance'] is high)['kw_display'])
        high.keywords=[dict(tag='binding',tier=True),dict(tag='binding',tier=1.9),dict(tag='binding',tier=1)]
        self.assertEqual(1,response.tier(high,'binding'))

    def test_primary_slot_pinned_with_multitag_fixative_and_conjunction(self):
        r,primary,fix,pot=self.setup_batch();primary.keywords.append(dict(tag='fixative',tier=2))
        fix.keywords.append(dict(tag='binding',tier=2))
        r['requires_single_item']=[dict(tag='fibrous',min_tier=1)]
        extra=self.item('dried_aromatic_herb')
        p=self.plan(r,{0:primary});self.assertIs(primary,p.roles['primary'])
        self.assertEqual(3,len(p.materials));self.assertEqual(3,len({id(i) for i in p.materials}))
        self.assertEqual(6,p.primary_state['hits'])

    def test_oils_excluded_by_capability_even_duplicated(self):
        r,primary,fix,pot=self.setup_batch();self.e.player.inventory.remove(primary)
        oil=self.item('briar_binding_oil');oil.item_id='another_oil'
        p,missing=plan_craft(r,self.e.player.inventory,ambient_sources=CraftScreen._build_ambient_sources(self.e),chosen_items={0:oil})
        self.assertTrue(missing);self.assertFalse(response.eligible(oil,'binding',1))
        prompts=CraftScreen._find_ambiguous_components(r,self.e.player.inventory,self.e.data.keywords)
        self.assertFalse(any(o.get('instance') is oil for p in prompts for o in p['options']))

    def test_stale_primary_rejects_without_cost_or_substitution(self):
        r,primary,fix,pot=self.setup_batch();p=self.plan(r)
        before=(list(self.e.player.inventory.items),self.e.world_time.turn)
        primary.keywords=[dict(tag='binding',tier=2)]
        self.assertIsNone(self.start(r,p))
        self.assertEqual(before,(self.e.player.inventory.items,self.e.world_time.turn));self.assertEqual(125,pot.vessel['water_ml'])

    def test_stale_fixative_tool_roles_and_duplicate_owners_reject(self):
        r,primary,fix,pot=self.setup_batch();tool=self.item('dried_bitter_herb')
        fix.keywords.append(dict(tag='fibrous',tier=1));tool.keywords.append(dict(tag='fibrous',tier=1))
        r['tools']=[dict(tag='fibrous',min_tier=1)];p=self.plan(r)
        used=next(i for i in p.materials if i is not primary)
        used.keywords=[k for k in used.keywords if k['tag']!='fixative']
        before=list(self.e.player.inventory.items);self.assertIsNone(self.start(r,p));self.assertEqual(before,self.e.player.inventory.items)
        dose=self.item('bile_coating');self.e.player.inventory.remove(dose)
        self.e.local_map.floor_objects[(10,10)]=[dose]
        self.e.local_map.container_state[(8,8)]=dict(items=[dose],state='open')
        with self.assertRaisesRegex(ValueError,'duplicate ownership'):vessels.validate_map(self.e.local_map)
        self.assertFalse(self.e.save_manager.save(self.e))

    def test_actual_water_menu_offers_both_batches_and_cancellation_free(self):
        from engine import vessel_menu
        pot=self.item('small_steeping_cup');self.e.local_map.set_tile(12,11,'shallow_water',True,True);self.e._update_fov()
        before=self.e.world_time.turn
        vessel_menu.amounts(self.e,pot,'fill',xy=(12,11))
        labels=[r[0] for r in self.e._vessel_menu['options']]
        self.assertIn('One preparation batch: 250 mL',labels)
        n=next(n for n,s in enumerate(labels) if '125 mL' in s)
        self.e._vessel_menu['selected']=n;self.e._handle_key(pygame.K_RETURN)
        self.assertEqual(125,pot.vessel['water_ml']);self.assertEqual(before+1,self.e.world_time.turn)
        vessel_menu.open_item(self.e,pot);self.e._handle_key(pygame.K_ESCAPE)
        self.assertEqual(before+1,self.e.world_time.turn)

    def test_map_alias_same_address_allowed_distinct_serialized_owners_rejected(self):
        from engine.save_manager import CachedChunk
        e=self.e;dose=self.item('binding_wash');e.player.inventory.remove(dose)
        e.local_map.floor_objects[(10,10)]=[dose];cache=e.save_manager.cache
        cache.hot[(e.world_x,e.world_y)]=CachedChunk(e.local_map,[])
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        cache.hot[(100,100)]=CachedChunk(e.local_map,[])
        self.assertFalse(e.save_manager.save(e));self.assertIn('duplicate ownership',e.save_manager.last_error)
        cache.hot.pop((100,100));cache.submap_hot['owner_alias']=CachedChunk(e.local_map,[])
        self.assertFalse(e.save_manager.save(e));self.assertIn('duplicate ownership',e.save_manager.last_error)
        cache.submap_hot.clear();cache.hot.clear()
        other=copy.deepcopy(e.local_map);other.floor_objects[(10,10)]=[dose]
        cache.hot[(100,100)]=CachedChunk(other,[])
        self.assertFalse(e.save_manager.save(e));self.assertIn('duplicate ownership',e.save_manager.last_error)

    def test_equal_input_real_combat_favorable_nonwinning_and_contacts(self):
        import random
        from engine import combat
        results={}
        # Controlled identical heavy iron weapon without an innate essence;
        # actual creature armour/body, resolver and contact consumer retained.
        self.e.data.items['heavy_blade']['essence']=None
        weapon=self.item('heavy_blade');self.e.player.equipment.equip(weapon,'weapon')
        for creature in ('hollow_revenant','briar_lurker'):
            for dose in (None,'binding_wash','etching_wash'):
                target=self.e.creature_factory.spawn(creature,13,12);target.ai=None
                self.e.entities=[self.e.player,target];weapon.temporary_essence=[]
                if dose:self.assertTrue(self.e.item_system.use(self.item(dose),self.e))
                self.e.rng=random.Random(4);observed=[];resolve=combat.resolve_attack
                def traced(**kwargs):
                    result=resolve(**kwargs);observed.append(result);return result
                with patch('engine.combat.resolve_attack',side_effect=traced):self.e._player_attack(target)
                self.assertTrue(observed[0].hit);self.assertFalse(observed[0].dodged)
                results[creature,dose]=observed[0]
        self.assertGreater(results['hollow_revenant','binding_wash'].damage_dealt,results['hollow_revenant',None].damage_dealt)
        self.assertGreater(results['briar_lurker','etching_wash'].damage_dealt,results['briar_lurker',None].damage_dealt)
        # Both active rows spend on real contact even when only one wins.
        self.e.item_system.use(self.item('binding_wash'),self.e)
        self.e.item_system.use(self.item('etching_wash'),self.e)
        for row in weapon.temporary_essence:row['hits_remaining']=1
        target=self.e.creature_factory.spawn('hollow_revenant',13,12);target.ai=None;self.e.entities=[self.e.player,target]
        self.e.rng=random.Random(4);observed=[]
        with patch('engine.combat.resolve_attack',side_effect=traced):self.e._player_attack(target)
        self.assertEqual('Binding',observed[0].essence_applied);self.assertFalse(weapon.temporary_essence)

    def test_contact_zero_block_miss_dodge_and_wait_preserve_existing_rules(self):
        from engine.combat import CombatResult
        w=self.weapon();self.e.item_system.use(self.item('binding_wash'),self.e)
        self.e.item_system.use(self.item('etching_wash'),self.e)
        target=self.e.creature_factory.spawn('hollow_revenant',13,12);target.ai=None;self.e.entities=[self.e.player,target]
        for hit,dodged,expected in ((False,False,6),(True,True,6),(True,False,5)):
            result=CombatResult(hit=hit,dodged=dodged,damage_dealt=0)
            with patch('engine.combat.resolve_attack',return_value=result):self.e._player_attack(target)
            self.assertEqual([expected,expected],[r['hits_remaining'] for r in w.temporary_essence])
        self.e._handle_key(pygame.K_PERIOD)
        self.assertEqual([5,5],[r['hits_remaining'] for r in w.temporary_essence])

    def test_both_jobs_snapshot_definition_edits_clock_and_same_vessel(self):
        for iid in ('binding_wash','etching_wash'):
            with self.subTest(iid=iid):
                self.e.local_map.processing_layer.clear();self.e.local_map.floor_objects.clear();self.e.player.inventory.items.clear()
                r,primary,fix,pot=self.setup_batch(iid,2);job=self.start(r,self.plan(r))
                self.assertEqual(14,job['turns_remaining']);self.assertIs(pot,job['vessel_job']['vessel'])
                self.assertEqual(0,pot.vessel['water_ml']);self.assertFalse(self.e.player.inventory.contains(primary))
                self.e.data.items[iid]['temporary_essence'][0].update(strength=.8,hits=20)
                r['material_response']['high_hits']=30
                self.e._handle_key(pygame.K_F5);self.e._handle_key(pygame.K_F9)
                dose=self.finish();self.assertEqual(dict(version=1,essence='Binding' if iid=='binding_wash' else 'Dissolution',strength=.4,hits=12),dose.coating_dose)
                self.assertEqual(pot.vessel['id'],self.e.local_map.floor_objects[(12,11)][0].vessel['id'])

    def test_blocked_delivery_rolls_back_then_abandon_returns_empty_once(self):
        r,primary,fix,pot=self.setup_batch();job=self.start(r,self.plan(r));job['turns_remaining']=0
        saved=self.e.data.items.pop('binding_wash');self.e._tick_processing_map(self.e.local_map,active=True)
        self.assertIs(job,self.e.local_map.processing_layer[(12,11)]);self.assertFalse(self.e.local_map.floor_objects)
        self.e.data.items['binding_wash']=saved
        from engine.vessel_jobs import deliver,abandon
        from generation.floor_object_utils import place_floor_object
        calls=[]
        def fail(m,x,y,i):
            calls.append(i)
            return place_floor_object(m,x,y,i) if len(calls)==1 else False
        with patch('generation.floor_object_utils.place_floor_object',side_effect=fail):self.e._tick_processing_map(self.e.local_map,active=True)
        self.assertFalse(any(self.e.local_map.floor_objects.values()));self.assertIn((12,11),self.e.local_map.processing_layer)
        self.assertTrue(abandon(self.e,(12,11),job,vessels.context(self.e)))
        self.assertFalse(abandon(self.e,(12,11),job,vessels.context(self.e)))
        self.assertEqual([pot],self.e.local_map.floor_objects[(12,12)])

    def test_dose_captured_variants_group_and_apply_exact_one_action(self):
        w=self.weapon();a=self.item('briar_binding_oil')
        self.e.data.items[a.item_id]['temporary_essence'][0].update(hits=12,strength=.4)
        b=self.item(a.item_id)
        rows=_flat_list(_group_items(self.e.player.inventory.items,self.e))
        self.assertEqual(2,len([i for i,h,l in rows if i is a or i is b]))
        turn=self.e.world_time.turn;use(self.e,b)
        self.assertEqual(turn+1,self.e.world_time.turn);self.assertTrue(self.e.player.inventory.contains(a));self.assertFalse(self.e.player.inventory.contains(b))
        self.assertEqual([dict(essence='Binding',strength=.4,hits_remaining=12)],w.temporary_essence)
        c=self.item('etching_wash');use(self.e,c);use(self.e,a)
        self.assertEqual({'Dissolution':6,'Binding':8},{r['essence']:r['hits_remaining'] for r in w.temporary_essence})

    def test_historical_projection_is_exact_and_keeps_spent_rows(self):
        from g1_support import semantic_item_state
        for iid in ('bile_coating','briar_binding_oil','hungering_oil'):
            row=serialize_item(self.item(iid));row['temporary_essence']=[dict(essence='Binding',strength=.4,hits_remaining=2)]
            projected=semantic_item_state(row,historical=True)
            self.assertNotIn('coating_dose',projected)
            self.assertEqual(row['temporary_essence'],projected['temporary_essence'])
            self.assertIn('coating_dose',semantic_item_state(row))
            row['coating_dose']['hits']+=1
            self.assertIn('coating_dose',semantic_item_state(row,historical=True))
        row['coating_dose']['version']=True
        with self.assertRaises(ValueError):semantic_item_state(row,historical=True)

    def test_wash_hot_alias_clock_and_cold_freeze(self):
        from engine.save_manager import CachedChunk
        r,primary,fix,pot=self.setup_batch();job=self.start(r,self.plan(r));e=self.e;cache=e.save_manager.cache
        cache.hot[(e.world_x,e.world_y)]=CachedChunk(e.local_map,[])
        cache.submap_hot['clock_alias']=CachedChunk(e.local_map,[])
        e._handle_key(pygame.K_PERIOD);self.assertEqual(13,job['turns_remaining'])
        cache.hot.clear();cache.submap_hot.clear()
        m=copy.deepcopy(e.local_map);j=m.processing_layer[(12,11)]
        e.local_map.processing_layer.clear();e.local_map.decor.pop((12,11),None)
        cache.store_hot_only(100,100,m,[]);cache.submap_hot['clock_alias']=cache.hot[(100,100)]
        e._handle_key(pygame.K_PERIOD);self.assertEqual(12,j['turns_remaining'])
        cache.submap_hot.clear();cache.evict_distant(e.world_x,e.world_y)
        for _ in range(4):e._handle_key(pygame.K_PERIOD)
        restored=cache.load(100,100).local_map
        self.assertEqual(12,restored.processing_layer[(12,11)]['turns_remaining'])
        for _ in range(12):e._handle_key(pygame.K_PERIOD)
        self.assertEqual(6,restored.floor_objects[(12,11)][1].coating_dose['hits'])
        self.assertEqual(pot.vessel['id'],restored.floor_objects[(12,11)][0].vessel['id'])

    def test_captured_wash_job_malformed_state_rejected(self):
        r,primary,fix,pot=self.setup_batch();job=self.start(r,self.plan(r));original=copy.deepcopy(job)
        for field,value in [('version',True),('version',3),('primary',{}),('output',{})]:
            job['vessel_job'][field]=value
            with self.assertRaises(ValueError):vessels.validate_map(self.e.local_map)
            job['vessel_job']=copy.deepcopy(original['vessel_job'])
        job['vessel_job']['output']['count']=2
        with self.assertRaises(ValueError):vessels.validate_map(self.e.local_map)

    def test_malformed_inventory_floor_and_busy_job_loads_install_nothing(self):
        from engine.save_manager import SaveManager
        r,primary,fix,pot=self.setup_batch();self.start(r,self.plan(r));self.item('binding_wash')
        self.e.local_map.floor_objects[(9,9)]=[self.e.item_factory.create('etching_wash')]
        self.assertTrue(self.e.save_manager.save(self.e))
        source=self.e.save_manager.checkpoint_path()
        original={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file() and p.name!='manifest.json'}
        scene=next(n for n in original if n.startswith('chunks/'))
        for case in ('inventory','floor','job-version','primary-mismatch'):
            payloads=dict(original)
            if case=='inventory':
                player=json.loads(payloads['player.json']);player['inventory']['items'][0]['coating_dose']['strength']=True
                payloads['player.json']=json.dumps(player).encode()
            else:
                cached=pickle.loads(payloads[scene])
                if case=='floor':cached.local_map.floor_objects[(9,9)][0].coating_dose['hits']=0
                else:
                    b=cached.local_map.processing_layer[(12,11)]['vessel_job']
                    if case=='job-version':b['version']=3
                    else:b['primary']['hits']+=1
                payloads[scene]=pickle.dumps(cached)
            manager=SaveManager(save_root=Path(self.tmp.name)/case);manager.store.publish(payloads,None,None)
            before=(self.e.player,self.e.local_map,self.e.world_time.turn,list(self.e.player.inventory.items))
            self.assertFalse(manager.load(self.e),case)
            self.assertEqual(before,(self.e.player,self.e.local_map,self.e.world_time.turn,self.e.player.inventory.items))

    def test_invalid_or_failed_consumption_and_stale_weapon_are_free(self):
        w=self.weapon();a=self.item('binding_wash');before=serialize_item(w)
        with patch('engine.item_transfers.consume_throw_unit',return_value=False):self.assertFalse(self.e.item_system.use(a,self.e))
        self.assertEqual(before,serialize_item(w));self.assertTrue(self.e.player.inventory.contains(a))
        self.e.player.inventory.remove(w);self.assertFalse(self.e.item_system.use(a,self.e))
        self.e.player.inventory.add(w);a.count=0;self.assertFalse(self.e.item_system.use(a,self.e))
        a.count=2;self.assertTrue(self.e.item_system.use(a,self.e));self.assertEqual(1,a.count)

    def test_modern_payload_rejects_all_consumed_owners_and_no_partial_load(self):
        a=self.item('binding_wash');row=serialize_item(a)
        for value in (None,{},dict(a.coating_dose,version=True),dict(a.coating_dose,hits=True),dict(a.coating_dose,strength=float('nan'))):
            with self.subTest(value=value):
                bad=dict(row,coating_dose=value)
                with self.assertRaises(ValueError):validate_item(bad,'bad')
                self.e.local_map.container_state[(8,8)]=dict(items=[bad],state='open')
                self.assertFalse(self.e.save_manager.save(self.e))
        self.e.local_map.container_state.clear();self.assertTrue(self.e.save_manager.save(self.e))
        source=self.e.save_manager.checkpoint_path();payloads={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file() and p.name!='manifest.json'}
        scene=next(n for n in payloads if n.startswith('chunks/'));cached=pickle.loads(payloads[scene])
        cached.local_map.container_state[(8,8)]=dict(items=[dict(row,on_use='eat')],state='open');payloads[scene]=pickle.dumps(cached)
        from engine.save_manager import SaveManager
        manager=SaveManager(save_root=Path(self.tmp.name)/'invalid');manager.store.publish(payloads,None,None)
        before=(self.e.player,self.e.local_map,self.e.world_time.turn)
        self.assertFalse(manager.load(self.e));self.assertEqual(before,(self.e.player,self.e.local_map,self.e.world_time.turn))

    def test_job_and_completed_doses_cold_load(self):
        r,primary,fix,pot=self.setup_batch();self.start(r,self.plan(r));w=self.weapon();use(self.e,self.item('briar_binding_oil'))
        w.temporary_essence[0]['hits_remaining']=3
        low=self.item('binding_wash');high=self.item('binding_wash');high.coating_dose['hits']=12
        self.assertTrue(self.e.save_manager.save(self.e),self.e.save_manager.last_error)
        script="""
import json,sys,pygame
from pathlib import Path
from unittest.mock import patch
from test_effect_persistence import load_data,make_engine
pygame.init()
with patch('engine.save_manager.SAVE_DIR',Path(sys.argv[1])):e=make_engine(load_data())
assert e.save_manager.load(e),e.save_manager.last_error
assert e.local_map.processing_layer[(12,11)]['vessel_job']['output']['coating_dose']['hits']==6
assert e.player.equipment.slots['weapon'].temporary_essence[0]['hits_remaining']==3
assert sorted(i.coating_dose['hits'] for i in e.player.inventory.items if i.item_id=='binding_wash')==[6,12]
for _ in range(14):e._handle_key(pygame.K_PERIOD)
assert e.local_map.floor_objects[(12,11)][1].coating_dose['hits']==6
assert e.save_manager.save(e),e.save_manager.last_error
print('cold-pass')
"""
        result=subprocess.run([sys.executable,'-X','utf8','-B','-c',script,str(self.root)],capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stderr);self.assertIn('cold-pass',result.stdout)
        self.assertTrue(self.e.save_manager.load(self.e));self.assertEqual(6,self.e.local_map.floor_objects[(12,11)][1].coating_dose['hits'])

    def test_genuine_prechange_json_cache_and_job_keep_historical_semantics(self):
        archive=ROOT/'evidence/sys-3/legacy-coatings-job.zip'
        with zipfile.ZipFile(archive) as z:z.extractall(self.tmp.name)
        self.assertTrue(self.e.save_manager.load(self.e),self.e.save_manager.last_error)
        e=self.e;job=e.local_map.processing_layer[(12,11)]
        self.assertEqual({'version','requirement','vessel'},set(job['vessel_job']))
        self.assertEqual(1,job['vessel_job']['version'])
        self.assertEqual(6,e.player.equipment.slots['weapon'].temporary_essence[0]['hits_remaining'])
        oils=[i for i in e.player.inventory.items if i.on_use=='apply_to_weapon']
        self.assertEqual(3,len(oils));self.assertTrue(all(hasattr(i,'coating_dose') for i in oils))
        self.assertTrue(hasattr(e.local_map.floor_objects[(14,11)][0],'coating_dose'))
        from generation.floor_object_utils import get_container_items
        e.local_map.container_state[(8,8)]['state']='open'
        self.assertTrue(hasattr(get_container_items(e.local_map,8,8,e.item_factory)[0],'coating_dose'))
        self.assertFalse(hasattr(pickle.loads((Path(self.tmp.name)/'dose.pkl').read_bytes()),'coating_dose'))
        for _ in range(34):e._handle_key(pygame.K_PERIOD)
        self.assertEqual('resonant_bone_tincture',e.local_map.floor_objects[(12,11)][1].item_id)

    def test_contract_validation_and_supported_source_entitlement(self):
        from engine import item_authoring as ia,recipe_authoring as ra
        from engine.content_authoring import schema_problems,definition_sources
        self.assertFalse(schema_problems(ia.SCHEMA));self.assertFalse(schema_problems(ra.SCHEMA))
        sources=definition_sources(self.e.data.root,'items');recipes=definition_sources(self.e.data.root,'recipes')
        for iid in ('briar_binding_oil','bile_coating','hungering_oil','binding_wash','etching_wash'):
            path=sources[iid][0]['path'];raw=self.e.data.items[iid]
            self.assertTrue(ia.capability(raw,path)['editable']);self.assertFalse(ia.validate_definition(raw,self.e.data,path,sources,writable=True))
        for iid in ('binding_wash','etching_wash'):
            raw=self.e.data.recipes[iid];self.assertFalse(ra.validate_definition(raw,self.e.data,recipes[iid][0]['path'],recipes,sources,writable=True))
            for field,value in [('high_tier',True),('low_hits',0),('high_hits',101),('primary_role','other')]:
                bad=copy.deepcopy(raw);bad['material_response'][field]=value
                with self.assertRaises(ValueError):response.configuration(bad)
            bad=copy.deepcopy(raw);bad['components'].append(copy.deepcopy(bad['components'][0]))
            with self.assertRaises(ValueError):response.configuration(bad)


if __name__=='__main__':unittest.main()
