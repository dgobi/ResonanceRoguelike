"""W5P authority and actual ordinary consumer checks in owned disposable data."""
import contextlib,copy,io,json,tempfile,unittest
from pathlib import Path
from test_bridge import ROOT,invoke
from test_authoring import data_fixture
import sys
sys.path.insert(0,str(ROOT/'roguelike'))
from engine import building_authoring as building
from generation.building_preview import orientations

SOURCE='roguelike/data/buildings/residential/house_small_a.json'


def example():
    return dict(id='house_small_a',layers=['##..#####','#.......#','#.......#','#.......#','#.......#','#########'],legend={'#':'wall','.':'floor',' ':None},
        special_tiles=[dict(type='item',x=2,y=2,item_id='wood_bundle'),dict(type='item',x=3,y=3,item_id='wood_bundle',text_id='world_graffiti_a'),dict(type='container',x=6,y=2,decor_id='crate',loot_pools=['workshop_b_fuel'])],
        decor_layer=[[None]*9 for _ in range(6)],placement=dict(version=1,contexts=['grid','roadside'],weight=1,rotations=[0,90,180,270,0],mirror_x=True,buffer=1,approach=2,road_relation='frontage',
            entrances=[dict(id='main',x=2,y=0,width=2,normal='N',role='main',required=True)],targets=[dict(x=3,y=3,kind='readable',required=True),dict(x=6,y=2,kind='container',required=True),dict(x=0,y=0,kind='item',required=False)]))


class Buildings(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='w5p-building-');self.addCleanup(self.tmp.cleanup)
        self.root=data_fixture(self.tmp.name);self.data_root=self.root/'roguelike/data'
    def save(self,path,raw):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(raw),encoding='utf-8')
    def data(self):
        from engine.data_loader import DataLoader
        with contextlib.redirect_stdout(io.StringIO()):return DataLoader(str(self.data_root))
    def check(self,raw):
        return invoke('preview_draft',root=self.root,source_asset=SOURCE,asset=SOURCE,draft=json.dumps(raw))['result']
    def test_inventory_original_authority_and_invalid_value_repair(self):
        rows=invoke('describe')['result']['assets'];ordinary=[r for r in rows if r.get('family_id')=='building']
        self.assertEqual(len(ordinary),58);self.assertTrue(all(r['editable'] for r in ordinary));self.assertEqual(len([r for r in rows if r['route']=='plaza']),2)
        raw=example();raw['width']=99;self.save(SOURCE,raw)
        inspected=invoke('inspect',root=self.root,asset=SOURCE)['result'];self.assertTrue(inspected['editable']);self.assertFalse(inspected['valid'])
        raw.pop('width');self.assertTrue(self.check(raw)['valid'])
        (self.root/SOURCE).write_bytes(('\ufeff'+json.dumps(raw)).encode('utf-8'))
        self.assertTrue(invoke('inspect',root=self.root,asset=SOURCE)['result']['editable'])
        self.assertTrue(invoke('preview_draft',root=self.root,source_asset=SOURCE,asset=SOURCE,draft='\ufeff'+json.dumps(raw))['result']['valid'])
        for path,original in [('roguelike/data/buildings/residential/array.json',[dict(id='array')]),('roguelike/data/buildings/residential/nested/nested.json',dict(id='nested'))]:
            self.save(path,original);candidate=example();candidate['id']='fresh'
            r=invoke('preview_draft',root=self.root,source_asset=path,asset='roguelike/data/buildings/residential/fresh.json',draft=json.dumps(candidate))
            self.assertFalse(r.get('result',{}).get('valid',False));(self.root/path).unlink()
    def test_identity_case_alias_and_variant_publication_authority(self):
        raw=example();self.save(SOURCE,raw)
        changed={**raw,'id':'renamed'};self.assertIn('IDENTITY_CHANGE',[d['code'] for d in self.check(changed)['diagnostics']])
        for path in ('roguelike/data/buildings/storage/conflict.json','roguelike/data/buildings/residential/nested/conflict.json'):
            self.save(path,{**raw,'id':'HOUSE_SMALL_A'});self.assertFalse(invoke('inspect',root=self.root,asset=SOURCE)['result']['editable']);(self.root/path).unlink()
        self.save('roguelike/data/buildings/storage/other.json',{**raw,'id':'NEW_BUILDING'})
        candidate={**raw,'id':'new_building'}
        r=invoke('preview_draft',root=self.root,source_asset=SOURCE,asset='roguelike/data/buildings/residential/new_building.json',draft=json.dumps(candidate))['result']
        self.assertFalse(r['valid']);self.assertIn('VARIANT_EXISTS',[d['code'] for d in r['diagnostics']])
        r=invoke('preview_draft',root=self.root,source_asset=SOURCE,asset='roguelike/data/buildings/storage/new_building.json',draft=json.dumps(candidate))['result'];self.assertFalse(r['valid'])
    def test_every_orientation_full_spans_optional_goals_null_decor_and_effective_readable(self):
        raw=example();raw['layers'][1]='# ..... #';raw['decor_layer'][1][5]='dried_herbs';self.save(SOURCE,raw)
        result=self.check(raw);self.assertTrue(result['valid'],result['diagnostics']);reports=result['preview']['orientations'];self.assertEqual(len(reports),8)
        self.assertEqual(len({(r['rotation'],r['mirror']) for r in reports}),8)
        for r in reports:
            self.assertTrue(r['passed']);self.assertTrue(all(a['passed'] for a in r['access']));self.assertTrue(all(a['receipt_owned'] for a in r['record_access']))
            self.assertEqual(len([a for a in r['access'] if '.span[' in a['target']]),2)
            self.assertFalse(any(a['target']=='placement.targets[2]' for a in r['access']))
            item=r['population_receipts'][1];self.assertEqual(item['item_id'],'wood_bundle');self.assertEqual(item['objects'][0]['item_id'],self.data().text_item_map.get('world_graffiti_a','letter'));self.assertEqual(item['objects'][0]['text_id'],'world_graffiti_a')
            self.assertEqual(r['population_receipts'][2]['objects'][0]['items'][0]['item_id'],'wood_bundle')
        first=reports[0];ox,oy=first['origin'];self.assertEqual(first['terrain'][oy+1][ox+1],'grass');self.assertIn(dict(x=ox+5,y=oy+1,id='dried_herbs',blocking=False),first['decor'])
    def test_blocked_span_and_required_goal_failure_are_precise_not_retargeted(self):
        raw=example();self.save(SOURCE,raw)
        # Use a known blocking saved furnishing without relying on its name.
        data=self.data();blocking=next(k for k,v in data.decoratives.items() if v.get('blocks_movement') and not v.get('container'))
        raw['decor_layer'][0][3]=blocking;self.save(SOURCE,raw)
        r=self.check(raw);self.assertFalse(r['valid']);self.assertTrue(any('.span[1]' in d['field'] and d.get('source_xy') for d in r['diagnostics']),r['diagnostics'])
        raw=example();raw['layers'][3]='#..#....#';self.save(SOURCE,raw);r=self.check(raw);self.assertFalse(r['valid'])
        self.assertTrue(any(d['field']=='placement.targets[0]' for d in r['diagnostics']));record=r['preview']['orientations'][0]['population_receipts'][1];self.assertTrue(record['relocated']);self.assertNotEqual(record['source_xy'],[record['xy'][0]-r['preview']['origin'][0],record['xy'][1]-r['preview']['origin'][1]])
    def test_remote_optional_entry_no_profile_and_transform_refusals(self):
        raw=example();raw['placement']['road_relation']='remote';raw['placement']['entrances'][0]['required']=False;self.save(SOURCE,raw)
        r=self.check(raw);self.assertTrue(r['valid'],r['diagnostics']);self.assertTrue(all(not p['access_verified'] for p in r['preview']['orientations']))
        raw.pop('placement');self.save(SOURCE,raw);r=self.check(raw);self.assertTrue(r['valid']);self.assertTrue(r['preview']['legacy_transform_limit']);self.assertFalse(r['preview']['access_verified'])
        raw=example();raw['special_tiles'][0]['unknown']={'position':[2,2]};self.save(SOURCE,raw);r=self.check(raw);self.assertFalse(r['valid']);self.assertTrue(any('unknown' in d['message'] for d in r['diagnostics']))
        raw=example();raw['special_tiles'][0]=dict(type='weighted',x=2,y=2,spawn_table=[dict(type='item',x=3,y=2,item_id='wood_bundle',weight=1)])
        self.save(SOURCE,raw);r=self.check(raw);self.assertFalse(r['valid']);self.assertTrue(any(d['code']=='CHOICE_COORDINATE' for d in r['diagnostics']))
        raw=example();raw['layers']=['.'*60]*5;raw['decor_layer']=[[None]*60 for _ in range(5)];raw['placement']['entrances'][0].update(x=2,y=0);self.save(SOURCE,raw);r=self.check(raw);self.assertFalse(r['valid']);self.assertTrue(any('exceeds scene' in d['message'] for d in r['diagnostics']))
    def test_pending_selected_semantic_closure_restores_and_new_variant_does_not_rewrite(self):
        from generation.placement import dependencies,check_dependencies
        from generation.context import GenerationError
        raw=example();self.save(SOURCE,raw);data=self.data();old=dependencies(raw,data);plan={'dependencies':{'d':old}};selected={'id':'owned-pending','asset':raw['id'],'dependency':'d'}
        check_dependencies(selected,plan,data)
        for field in ('building','pool'):
            changed=copy.deepcopy(data)
            if field=='building':changed.structures[raw['id']]['layers'][2]='#..#....#'
            else:changed.loot_pools['workshop_b_fuel']['items']=[dict(item_id='animal_bone')]
            with self.assertRaisesRegex(GenerationError,'changed dependency'):check_dependencies(selected,plan,changed)
            check_dependencies(selected,plan,data)
        data.structures['new_variant']={**raw,'id':'new_variant'};check_dependencies(selected,plan,data)
        data.structures[raw['id']]['description']='inactive';check_dependencies(selected,plan,data)


if __name__=='__main__':unittest.main()
