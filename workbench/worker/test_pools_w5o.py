"""Registered pool source authority, physical dependencies and bounded rules."""
import contextlib, copy, io, json, random, sys, tempfile, unittest
from unittest.mock import patch
from test_bridge import ROOT,invoke
from test_authoring import data_fixture
sys.path.insert(0,str(ROOT/'roguelike'))
from engine.data_loader import DataLoader
from engine import pool_authoring as pool
SOURCE='roguelike/data/loot_pools/alchemist_reagents.json'
BUILDING='roguelike/data/buildings/commercial/apothecary_a.json'


class RegisteredPools(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='w5o-pool-');self.addCleanup(self.tmp.cleanup)
        self.root=data_fixture(self.tmp.name);self.data_root=self.root/'roguelike/data'
    def save(self,path,raw):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(raw),encoding='utf-8')
    def data(self):
        with contextlib.redirect_stdout(io.StringIO()):return pool.load_authoring_data(self.data_root)
    def check(self,raw,bounded=True):
        self.save(SOURCE,raw);return pool.validate_pool(raw,self.data(),SOURCE,self.data_root,bounded=bounded)
    def test_inventory_and_repairable_values_original_source_policy(self):
        rows=[r for r in invoke('describe')['result']['assets'] if r.get('family_id')=='pool']
        self.assertEqual(len(rows),19);self.assertTrue(all(r['editable'] for r in rows))
        self.assertIn('roguelike/data/loot_pools/workshop_d_treatment.json',[r['path'] for r in rows])
        raw={'id':'alchemist_reagents','items':None,'roll_count':None};self.save(SOURCE,raw)
        result=invoke('inspect',root=self.root,asset=SOURCE)['result'];self.assertTrue(result['editable']);self.assertFalse(result['valid'])
        fixed={**raw,'items':[]};fixed.pop('roll_count')
        self.assertTrue(invoke('preview_draft',root=self.root,source_asset=SOURCE,asset=SOURCE,draft=json.dumps(fixed))['result']['valid'])
        # Neither a repaired array/nested original nor candidate flags grant authority.
        for source,value in [('roguelike/data/loot_pools/array.json',[{'id':'array','items':[]}]),('roguelike/data/loot_pools/nested/nested.json',{'id':'nested','items':[]})]:
            self.save(source,value)
            target='roguelike/data/loot_pools/repaired.json'
            response=invoke('preview_draft',root=self.root,source_asset=source,asset=target,draft=json.dumps(dict(id='repaired',items=[])))
            self.assertFalse(response.get('result',{}).get('valid',False))
            self.assertIn('SOURCE_ENTITLEMENT',[d['code'] for d in response.get('result',{}).get('diagnostics',[])])
    def test_defaults_numeric_bounds_and_publication_only_row_limit(self):
        base=dict(id='alchemist_reagents')
        valid=[{},dict(items=[]),dict(roll_count=[0]),dict(roll_count=[2**53-1]),dict(roll_count=[1,2]),dict(items=[dict(item_id='tallow_torch')]),dict(roll_count=[0],items=[dict(item_id='wood_bundle',weight=1e100)])]
        for fields in valid:self.assertFalse([d for d in self.check({**base,**fields}) if d['severity']=='error'],fields)
        invalid=[dict(roll_count=x) for x in (None,True,[],[True],[1.5],[2**53],[-1],[2,1],[0,1,2])]
        invalid += [dict(items=[dict(item_id='wood_bundle',weight=x)]) for x in (None,True,-1,'heavy',0)]
        invalid += [dict(items=None),dict(items=[{}]),dict(items=[dict(item_id='wood_bundle',weight=1e308)]*2)]
        for fields in invalid:self.assertTrue([d for d in self.check({**base,**fields}) if d['severity']=='error'],fields)
        raw={**base,'items':[dict(item_id='wood_bundle')]*65}
        self.assertIn('POOL_BOUND',[d['code'] for d in self.check(raw)])
        self.assertFalse([d for d in self.check(raw,bounded=False) if d['severity']=='error'])
        c=pool.authoring_context(raw,self.data(),SOURCE,self.data_root,{},'a'*64);self.assertTrue(c['records'][0]['capability']['editable'])
        container=dict(special_tiles=[dict(type='container',loot_pools=['alchemist_reagents'])])
        self.assertFalse([d for d in pool.container_dependencies(container,self.data(),'<room>',self.data_root) if d['severity']=='error'])
    def test_case_alias_paths_loader_and_all_unowned_factory_fields(self):
        raw=dict(id='alchemist_reagents',items=[dict(item_id='wood_bundle',weight=0),dict(item_id='tallow_torch')])
        self.assertFalse(self.check(raw))
        self.save('roguelike/data/items/components/alias.json',dict(id='WOOD_BUNDLE',weight=.1))
        errors=self.check(raw);self.assertTrue(any(d['code']=='ITEM_SOURCE' and 'alias.json' in d['message'] for d in errors))
        (self.data_root/'items/components/alias.json').unlink()
        from engine.item_factory import ItemFactory
        original=ItemFactory.create
        def bad(factory,identifier,*args,**kwargs):
            item=original(factory,identifier,*args,**kwargs)
            if identifier=='wood_bundle':item.weight='heavy'
            return item
        before=random.getstate();catalog=self.data();saved=copy.deepcopy(catalog.items)
        with patch.object(ItemFactory,'create',bad):
            self.assertIn('ITEM_FACTORY',[d['code'] for d in pool.validate_pool(raw,catalog,SOURCE,self.data_root)])
        self.assertEqual(random.getstate(),before);self.assertEqual(catalog.items,saved)
        self.save('roguelike/data/loot_pools/alias.json',dict(id='ALCHEMIST_REAGENTS',items=[]))
        self.assertTrue(any(d['code']=='DUPLICATE_ID' and 'alias.json' in d['message'] for d in self.check(raw)))
        (self.data_root/'loot_pools/alias.json').unlink()
        (self.root/SOURCE).write_bytes(('\ufeff'+json.dumps(raw)).encode())
        response=invoke('inspect',root=self.root,asset=SOURCE)['result'];self.assertFalse(response['editable']);self.assertIn('LOADER_IDENTITY',[d['code'] for d in response['diagnostics']])
    def test_saved_building_and_room_invalidate_after_item_dependency_change(self):
        raw=dict(id='alchemist_reagents',items=[dict(item_id='wood_bundle',weight=1)])
        self.save(SOURCE,raw)
        room=json.loads((ROOT/'roguelike/docs/examples/g17_authored_creature_room.json').read_bytes());room['id']='w5o_dependency';room['special_tiles']=[dict(type='container',x=2,y=2,loot_pools=['alchemist_reagents'],decor_id='crate')]
        room_path='roguelike/data/layouts/w5o_dependency.json';self.save(room_path,room)
        for path in (BUILDING,room_path):self.assertTrue(invoke('inspect',root=self.root,asset=path)['result']['valid'])
        locations=pool.locations(pool.definition_sources(self.data_root,'items'),'wood_bundle');item_path=locations[0]['path'];item=locations[0]['definition'];item['weight']='heavy';self.save(item_path,item)
        for path in (BUILDING,room_path):
            result=invoke('inspect',root=self.root,asset=path)['result'];self.assertFalse(result['valid']);self.assertIn('ITEM_FACTORY',[d['code'] for d in result['diagnostics']])
        item['weight']=.1;self.save(item_path,item)
        for path in (BUILDING,room_path):self.assertTrue(invoke('inspect',root=self.root,asset=path)['result']['valid'])
        # Existing ordinary weighted containers receive the same safety proof,
        # including an unselected alternative; the usage list stays direct-only.
        item['weight']='heavy';self.save(item_path,item)
        weighted=dict(special_tiles=[dict(type='weighted',spawn_table=[dict(type='empty',weight=1),dict(type='container',weight=0,loot_pools=['alchemist_reagents'])])])
        self.assertTrue(any(d['code']=='ITEM_FACTORY' and 'spawn_table[1]' in d['field'] for d in pool.container_dependencies(weighted,self.data(),'<building>',self.data_root)))


if __name__=='__main__':unittest.main()
