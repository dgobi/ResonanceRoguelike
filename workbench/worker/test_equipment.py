"""W5M real-worker authority, definition consumers and exact-source candidates."""
import copy
import json
import tempfile
import unittest
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

PATHS = dict(weapon='weapons/crude_blade', armour='armor/leather_jack', shield='shields/faceted_ward', satchel='equipment/satchel/leather_satchel')

class EquipmentTests(unittest.TestCase):
    def check(self, path, raw, **kwargs):
        response=invoke('preview_draft',asset=path,draft=raw if isinstance(raw,str) else json.dumps(raw),**kwargs)
        self.assertTrue(response['ok'],response)
        return response['result']

    def test_classes_defaults_legacy_binding_and_definition_factory_boundary(self):
        for kind,suffix in PATHS.items():
            path='roguelike/data/items/'+suffix+'.json'
            raw=json.loads((ROOT/path).read_bytes())
            result=invoke('inspect',asset=path)['result'];r=result['family']['context']['records'][0]
            self.assertEqual(result['family']['contract'],'expedition-items-2')
            self.assertTrue(result['editable'],r['diagnostics']);self.assertEqual(r['capability']['equipment_class'],kind)
            self.assertIsNotNone(r['equipment']);self.assertIsNotNone(r['factory'])
            for field in r['equipment']['current_definition_fields']:self.assertNotIn(field,r['factory']['instance'])
            if kind=='satchel':
                self.assertFalse(r['use']['present']);self.assertTrue(r['use']['legacy']);self.assertEqual(r['use']['effective'],'equip_toggle')
                self.assertIsNone(r['factory']['instance']['on_use'])
            self.assertTrue(self.check(path,raw)['valid'])

    def test_every_legacy_source_variant_requires_explicit_binding_and_preserves_same_id(self):
        for suffix in ('weapons/revelation_lens',*(f'equipment/satchel/{id}' for id in ('leather_satchel','herbalist_pouch','component_satchel'))):
            path='roguelike/data/items/'+suffix+'.json';raw=json.loads((ROOT/path).read_bytes())
            self.assertTrue(self.check(path,{**raw,'name':'Same ID'})['valid'])
            new={**raw,'id':'w5m_variant'};target=path.rsplit('/',1)[0]+'/w5m_variant.json'
            r=self.check(target,new,source_asset=path);self.assertFalse(r['valid']);self.assertTrue(any(d['field']=='on_use' for d in r['diagnostics']))
            self.assertTrue(self.check(target,{**new,'on_use':'equip_toggle'},source_asset=path)['valid'])
            self.assertFalse(self.check(path,{**raw,'on_use':'equip_toggle'})['valid'])

    def test_locks_raw_source_removal_and_compatible_new_armour_slot(self):
        path='roguelike/data/items/armor/leather_jack.json';raw=json.loads((ROOT/path).read_bytes())
        for edit in ({'category':'weapon'},{'slot':'armor_head'},{'essence':'Severance'},{'essence_strength':.8},{'on_use':None}):self.assertFalse(self.check(path,{**raw,**edit})['valid'],edit)
        variant={**raw,'id':'w5m_arms','slot':'armor_arms'}
        self.assertTrue(self.check(path.replace('leather_jack','w5m_arms'),variant,source_asset=path)['valid'])
        bad=copy.deepcopy(raw);bad['armor_layers'][0]['coverage']=.1
        self.assertFalse(self.check(path,bad)['valid'])
        for suffix in ('weapons/debug_blade','tools/tallow_torch','consumables/resonant_tincture'):
            path='roguelike/data/items/'+suffix+'.json';raw=json.loads((ROOT/path).read_bytes())
            for key in ('essences','on_use_effects','light','burn_turns'):raw.pop(key,None)
            raw.update(category='weapon',slot='weapon',on_use='equip_toggle',damage_dice='1d4')
            self.assertFalse(self.check(path,raw)['valid'])

    def test_numeric_and_structure_errors_are_located(self):
        cases={
          'weapon': {'damage_dice':['0d6','101d6','1d1001','1d6+2','nonsense',None,True], 'damage_bonus':[True,1.5,2**31,None], 'crit_chance':[True,-.1,1.1,None]},
          'shield': {'block_chance':[False,-1,2,None], 'block_value':[True,-1,1.5,2**31,None]},
          'armour': {'armor_layers':[[],[{}],[True],[dict(name='a',material='b',armor_value=True)],[dict(name='a',material='b',armor_value=2**31-1)]*2,[dict(name='a',material='b',armor_value=0)]*33]},
          'satchel': {'weight_reductions':[None,[],{'component':.2},{'Unknown':.2},{'all':True},{'all':-1},{'Tools':1.01}]}}
        for kind,fields in cases.items():
            path='roguelike/data/items/'+PATHS[kind]+'.json';raw=json.loads((ROOT/path).read_bytes())
            for field,values in fields.items():
                for value in values:
                    with self.subTest(kind=kind,field=field,value=value):
                        result=self.check(path,{**raw,field:value});self.assertFalse(result['valid']);self.assertTrue(any(d.get('field','').startswith(field) for d in result['diagnostics']))
        path='roguelike/data/items/weapons/crude_blade.json';raw=json.loads((ROOT/path).read_bytes())
        for field in ('crit_chance','damage_bonus'):
            for token in ('NaN','Infinity','1e309'):
                text=json.dumps(raw)[:-1]+',"'+field+'":'+token+'}'
                self.assertFalse(self.check(path,text)['valid'])

    def test_map_empty_zero_metadata_layers_and_exact_candidate_bytes(self):
        with tempfile.TemporaryDirectory(prefix='w5m-worker-') as folder:
            root=data_fixture(folder)
            for kind in ('satchel','armour'):
                path='roguelike/data/items/'+PATHS[kind]+'.json';raw=json.loads((root/path).read_bytes())
                if kind=='satchel':raw['weight_reductions']={'all':.15,'Components':0,'Tools':.7}
                else:raw['armor_layers'][0]['author_note']={'nested':[None,False]}
                (root/path).write_bytes((json.dumps(raw,indent=2)+'\r\n').encode())
                candidate=copy.deepcopy(raw);candidate['name']='Useful variant'
                if kind=='armour':candidate['armor_layers'].append(dict(name='lining',material='cloth',armor_value=1))
                draft=json.dumps(candidate,indent=2)+'\r\n';r=self.check(path,draft,root=root)
                self.assertTrue(r['valid'],r);self.assertEqual(r['family']['context']['records'][0]['definition'],candidate)
                self.assertEqual((root/path).read_bytes(),(json.dumps(raw,indent=2)+'\r\n').encode())
            path='roguelike/data/items/equipment/satchel/leather_satchel.json';raw=json.loads((root/path).read_bytes());raw['weight_reductions']={}
            self.assertTrue(self.check(path,raw,root=root)['valid'])
            self.assertFalse(self.check(path,json.dumps(raw)[:-1]+',"weight_reductions":{"all":0,"all":1}}',root=root)['valid'])

    def test_source_collision_and_malformed_retained_payload_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory(prefix='w5m-source-') as folder:
            root=data_fixture(folder);path='roguelike/data/items/weapons/crude_blade.json';raw=json.loads((root/path).read_bytes())
            duplicate=root/'roguelike/data/items/weapons/case.json';duplicate.write_text(json.dumps({**raw,'id':'CRUDE_BLADE'}))
            self.assertFalse(invoke('inspect',root=root,asset=path)['result']['editable']);duplicate.unlink()
            for bad in ([{'id':'broken','key':'Q','effects':{'callback':'arbitrary'}}],None,[False]):
                malformed={**raw,'movesets':bad};(root/path).write_text(json.dumps(malformed))
                r=invoke('inspect',root=root,asset=path)['result'];self.assertFalse(r['editable'])
                self.assertIn('retained',r['family']['context']['records'][0]['capability']['reason'])
                self.assertFalse(self.check(path,raw,root=root)['valid'])

if __name__=='__main__':unittest.main(verbosity=2)
