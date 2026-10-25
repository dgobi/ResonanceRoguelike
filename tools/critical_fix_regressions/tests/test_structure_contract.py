"""Shared contract, actual consumers, original stamps and retained root isolation."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from test_effect_persistence import load_data,make_engine,GAME_ROOT
from generation.structure_contract import compile_structure,read_document,StructureError,StructureCatalog
from generation.structure_preview import preview,registration
from generation.context import GenerationError,GenerationContext,GENERATION_REVISION
from generation.town_gen import _stamp_building_at,BuildingLoader
from generation.layout_stamper import stamp_layout_interior
from generation.entrance_gen import _pick_layout
from world.local_map import LocalMap,make_tile
from world.world_map import Chunk,RegionType
from engine.data_loader import DataLoader

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures/g2_original'


class StructureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_data()
        cls.cottage=read_document(GAME_ROOT/'docs/examples/author_cottage_a.json')

    def compile(self,doc,data=None,route='ordinary_building',category='residential'):
        return compile_structure(doc,route,data or self.data,path='draft.json',category=category)

    def assert_bad(self,doc,code,data=None):
        with self.assertRaises(StructureError) as caught: self.compile(doc,data)
        self.assertTrue(any(d.code==code for d in caught.exception.diagnostics),str(caught.exception))
        self.assertTrue(all(d.path=='draft.json' and d.correction for d in caught.exception.diagnostics))

    def test_complete_inventory_and_immutable_defaults(self):
        entries=self.data.structure_catalog.entries
        self.assertEqual(len(entries),66)
        self.assertEqual({r:sum(e.route==r for e in entries) for r in self.data.structure_catalog.by_route},
                         {'ordinary_building':57,'plaza':2,'interior_entrance':6,'authored_submap':1})
        self.assertEqual(len(self.data.buildings['residential']),12)
        doc=copy.deepcopy(self.cottage)
        c=next(s for s in doc['special_tiles'] if s['type']=='container')
        c.pop('decor_id'); c.pop('loot_pools')
        before=copy.deepcopy(doc); result=self.compile(doc)
        self.assertEqual(before,doc)
        c=next(s for s in result.definition['special_tiles'] if s['type']=='container')
        self.assertEqual((c['decor_id'],c['loot_pools']),('crate',[]))
        self.assertEqual(result.raw,doc)

    def test_invalid_grids_coordinates_types_and_all_alternatives(self):
        variants=[('ROOT',[]),('ROOT','scalar')]
        def change(code,key,value):
            d=copy.deepcopy(self.cottage); d[key]=value; variants.append((code,d))
        change('ID','id',False); change('GRID','layers',None)
        change('RAGGED_GRID','layers',['...', '..'])
        change('DIMENSION','width',False)
        change('LEGEND_ENTRY','legend',{'..':'floor'})
        change('TERRAIN_USED','legend',{**self.cottage['legend'],'#':'missing'})
        change('DECOR_GRID','decor_layer',['crate']*7)
        for x in (15,False,'2',None): change('COORDINATE','special_tiles',[{'type':'item','item_id':'flint_shard','x':x,'y':2}])
        for special,code in [
            ({'type':'item','item_id':'flint_shard','text_id':'missing'},'REFERENCE'),
            ({'type':'container','decor_id':'overturned_chair'},'CONTAINER_CAPABILITY'),
            ({'type':'container','loot_pools':None},'POOL_LIST'),
            ({'type':'scene','scene_id':'missing'},'REFERENCE'),
            ({'type':'weighted','spawn_table':[{'type':'empty','weight':1},{'type':'item','item_id':'missing','weight':0}]},'REFERENCE'),
            ({'type':'weighted','spawn_table':[{'type':'empty','weight':0}]},'WEIGHTS'),
            ({'type':'weighted','spawn_table':[{'type':'empty','weight':True}]},'NUMBER'),
            ({'type':'weighted','spawn_table':[{'type':'weighted','spawn_table':[{'type':'empty'}]}]},'WEIGHTED_NESTING'),
            ({'type':'weighted','spawn_table':[{'type':'empty','x':4,'y':2}]},'CHOICE_COORDINATE'),
            ({'type':'weighted','spawn_table':[{'type':'body'}]},'SPECIAL_KIND')]:
            change(code,'special_tiles',[dict(special,x=2,y=2)])
        for code,doc in variants:
            with self.subTest(code=code,doc=doc): self.assert_bad(doc,code)

    def test_referenced_scenes_and_pools_are_validated_without_rolling(self):
        d=copy.copy(self.data); d.scenes=copy.deepcopy(self.data.scenes); d.loot_pools=copy.deepcopy(self.data.loot_pools)
        for rows in ([None],[{'item_id':'missing'}],[{'item_id':'flint_shard','count':3}],None):
            d.scenes['bad']={'floor_objects':rows}
            doc=copy.deepcopy(self.cottage); doc['special_tiles']=[{'type':'scene','x':2,'y':2,'scene_id':'bad'}]
            with self.assertRaises(StructureError): self.compile(doc,d)
        for pool in ({'items':[{'item_id':'missing','weight':0},{'item_id':'flint_shard'}]},
                     {'roll_count':[True,2],'items':[]},{'items':[None]},{'items':[{'item_id':'flint_shard','weight':-1}]}):
            d.loot_pools['bad']=pool
            doc=copy.deepcopy(self.cottage); doc['special_tiles']=[{'type':'container','x':2,'y':2,'loot_pools':['bad']}]
            with self.assertRaises(StructureError): self.compile(doc,d)

    def test_duplicate_ids_keys_root_shapes_and_unrelated_list_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'buildings/residential').mkdir(parents=True)
            d=copy.copy(self.data); d.root=root
            for name in ('a','b'): (root/f'buildings/residential/{name}.json').write_text(json.dumps(self.cottage))
            with self.assertRaises(StructureError) as caught: StructureCatalog(d)
            diagnostic=next(x for x in caught.exception.diagnostics if x.code=='DUPLICATE_ID')
            self.assertIn('a.json',diagnostic.path); self.assertIn('b.json',diagnostic.path)
            for value in ('[]','42','null','{"id":"a","id":"b"}','{"x":NaN}'):
                file=root/'buildings/residential/a.json'; file.write_text(value)
                with self.assertRaises(StructureError): StructureCatalog(d)
            (root/'items').mkdir(); (root/'items/a.json').write_text('[{"id":"still_supported"}]')
            self.assertIn('still_supported',d._load_dir('items'))

    def test_route_alias_inactive_fields_and_transform_rejection(self):
        doc=copy.deepcopy(self.cottage); doc['layout']=doc.pop('layers')
        self.assert_bad(doc,'LAYOUT_ALIAS')
        plaza=self.compile(doc,route='plaza',category='plaza')
        self.assertTrue(any(d.field=='special_tiles' and d.code=='INACTIVE_FIELD' for d in plaza.diagnostics))
        doc['layers']=['.']; self.assert_bad(doc,'LAYOUT_CONFLICT')
        m=LocalMap(80,43); m.tiles[:]=make_tile('grass',True,True); before=m.tiles.copy()
        with self.assertRaises(GenerationError): _stamp_building_at(m,self.cottage,79,0,self.data.terrain,data=self.data)
        self.assertTrue((m.tiles==before).all())
        doc=copy.deepcopy(self.cottage); doc['special_tiles'][0]['x']=15
        with self.assertRaises(StructureError): _stamp_building_at(m,doc,10,10,self.data.terrain,data=self.data)
        self.assertTrue((m.tiles==before).all())

    def test_eight_data_corrections_preserve_actual_stamps_and_contents(self):
        changes=json.loads((GAME_ROOT.parent/'evidence/worldgen-g2/data-corrections.json').read_text())
        self.assertEqual(len(changes),8)
        for row in changes:
            original=read_document(FIXTURES/row['path']); current=read_document(GAME_ROOT.parent/row['path'])
            results=[]
            for doc in (original,current):
                m=LocalMap(80,43,generation_context=GenerationContext(1,2,('equivalence',)))
                m.tiles[:]=make_tile('grass',True,True)
                if '/entrances/' in row['path']:
                    stamp_layout_interior(m,doc,40,21,self.data.terrain,random.Random(19)); specs=[]
                else:
                    # Bypass only the new source validator for the frozen invalid
                    # legacy input; exercise the exact production stamper twice.
                    compiled=SimpleNamespace(definition=doc,width=max(map(len,doc['layers'])),height=len(doc['layers']),path=row['path'])
                    with patch('generation.structure_contract.compile_structure',return_value=compiled):
                        specs=_stamp_building_at(m,doc,20,10,self.data.terrain)
                    from engine.scene_generation import populate
                    from engine.item_factory import ItemFactory
                    from engine.creature_factory import CreatureFactory
                    populate(self.data,ItemFactory(self.data),CreatureFactory(self.data),m,specs,map_text=True)
                results.append((m,specs))
            self.assertTrue((results[0][0].tiles==results[1][0].tiles).all(),row['path'])
            self.assertEqual(results[0][0].decor,results[1][0].decor)
            self.assertEqual(results[0][1],results[1][1])
            from g1_support import fingerprint
            self.assertEqual(fingerprint(results[0][0],[]),fingerprint(results[1][0],[]))

    def test_retained_catalogs_same_ids_alternate_all_four_real_consumers(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            catalogs=[]
            for letter,item,terrain in [('a','flint_shard','floor'),('b','dried_provisions','gravel')]:
                root=Path(tmp)/letter; shutil.copytree(GAME_ROOT/'data',root)
                ordinary={'id':'root_probe','layers':['...']*3,'legend':{'.':terrain},'special_tiles':[{'type':'item','x':1,'y':1,'item_id':item}]}
                entrance={'id':'root_probe','entrance_type':'root_probe','layers':['...','.>.','...'],'legend':{'.':terrain,'>':'stairs_down'}}
                submap={'id':'root_probe','layers':['...','.<.','...'],'legend':{'.':terrain,'<':'stairs_up'},'player_start':{'x':1,'y':1},'special_tiles':ordinary['special_tiles']}
                for file,doc in [('buildings/residential/root_probe.json',ordinary),('buildings/plaza/root_plaza.json',dict(ordinary,id='root_plaza')),
                                 ('entrances/root_probe.json',entrance),('layouts/root_probe.json',submap)]:
                    (root/file).write_text(json.dumps(doc))
                catalogs.append(DataLoader(str(root)))
            records={}
            for index in (0,1,0,1,0,1):
                d=catalogs[index]; outputs=[]
                for route in ('ordinary_building','plaza','interior_entrance','authored_submap'):
                    identifier='root_plaza' if route=='plaza' else 'root_probe'
                    asset=d.structure_catalog.by_route[route][identifier]
                    random.seed(100+len(records)); [random.random() for _ in range(31)]
                    report,_,_=preview(asset.raw,route,d,category=asset.category)
                    outputs.append(report)
                self.assertEqual(_pick_layout('root_probe',random.Random(3),d)['legend']['.'], 'floor' if index==0 else 'gravel')
                plaza=BuildingLoader.from_definitions({'plaza':[d.structures['root_plaza']]}).pick_plaza(random.Random(2))
                self.assertEqual(plaza.legend['.'],'floor' if index==0 else 'gravel')
                # Exercise the actual town dispatch with an explicitly isolated
                # plaza pool as well; no module-global loader can supply it.
                bound=copy.copy(d);bound.buildings={'plaza':[d.structures['root_plaza']]}
                from generation.region_gen import generate_region
                from g1_support import fingerprint
                chunk=Chunk(1,1,RegionType.TOWN,77,town_id=1,town_role='C')
                town,_=generate_region(chunk,80,43,bound.terrain,bound)
                outputs.append(fingerprint(town,[]))
                if index in records: self.assertEqual(records[index],outputs)
                records[index]=outputs
            self.assertNotEqual(records[0],records[1])
            for index,outputs in records.items():
                expected='flint_shard' if index==0 else 'dried_provisions'
                self.assertIn(expected,json.dumps(outputs[0]['items']))
                self.assertIn(expected,json.dumps(outputs[3]['items']))

    def test_explicit_wg1_world_scene_mutations_survive_new_exploration_and_f9(self):
        with tempfile.TemporaryDirectory() as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)),contextlib.redirect_stdout(io.StringIO()):
            e=make_engine(self.data); e.world_map.generation_revision='wg1'; e.local_map.generation_revision='wg1'
            e.world_map.get(0,0).generation_revision='wg1'; e.local_map.generation_complete=True
            e.local_map.set_tile(3,4,'flagstone',True,True)
            e.world_map.width=2; e.world_map.set(Chunk(1,0,RegionType.PLAINS,77))
            self.assertTrue(e.save_manager.save(e))
            e.overmap_cursor_x,e.overmap_cursor_y=1,0; e._teleport_to_overmap_cursor()
            self.assertEqual(e.local_map.generation_revision,GENERATION_REVISION)
            self.assertEqual(e.world_map.generation_revision,'wg1')
            e.overmap_cursor_x=0
            with patch('engine.scene_generation.create_surface',side_effect=AssertionError('regeneration')):
                e._teleport_to_overmap_cursor()
            self.assertEqual(str(e.local_map.tiles[3,4]['terrain']),'flagstone')
            self.assertEqual(e.local_map.generation_revision,'wg1')
            self.assertTrue(e.save_manager.save(e)); self.assertTrue(e.save_manager.load(e))
            self.assertEqual(e.world_map.generation_revision,'wg1')
            self.assertEqual(e.local_map.generation_revision,'wg1')
            self.assertEqual(e.save_manager.cache.load(1,0).local_map.generation_revision,GENERATION_REVISION)
