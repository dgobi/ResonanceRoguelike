"""W5K real-worker source authority and bounded preparation semantics."""
import copy, json, tempfile, unittest
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

class PreparationWorker(unittest.TestCase):
    def preview(self, source, changes=None, root=ROOT, variant=False):
        path='roguelike/data/recipes/'+source+'.json'
        raw=json.loads((root/path).read_bytes());raw.update(changes or {})
        target=path
        if variant:
            raw['id']='w5k_variant';target=path.rsplit('/',1)[0]+'/w5k_variant.json'
        response=invoke('preview_draft',root=root,asset=target,source_asset=path,draft=json.dumps(raw))
        self.assertTrue(response['ok'],response)
        return response['result']

    def test_rules_admit_fifteen_sources_both_operations_exact_paths(self):
        admitted=[]
        for p in sorted((ROOT/'roguelike/data/recipes').glob('*.json')):
            path=p.relative_to(ROOT).as_posix();response=invoke('inspect',asset=path)['result']
            if response['editable']:
                admitted.append(response['id']);self.assertEqual(response['family']['effective_operations'],['edit','variant'])
                self.assertEqual(response['family']['contract'],'item-preparation-1')
        self.assertEqual(len(admitted),15);self.assertIn('dry_resonant_herb',admitted)
        for source in ('cook_meat','dry_coldbell','briar_binding_oil'):
            for variant in (False,True):
                r=self.preview(source,dict(name='Authored preparation'),variant=variant)
                self.assertTrue(r['valid'],r['diagnostics'])

    def test_original_class_exclusions_and_candidate_shape_are_authoritative(self):
        for source,changes in [('cook_meat',dict(passive_processing=False)),('bile_coating',dict(passive_processing=True)),
                ('campfire',dict(places_in_world=False,result_item='cooked_meat')),('hungering_oil',dict(apply_turns=None)),
                ('coldbell_extract_deprecated',dict(_deprecated=False))]:
            r=self.preview(source,changes);self.assertFalse(r['valid'])
            self.assertIn('RECIPE_CLASS' if source in ('cook_meat','bile_coating') else 'SOURCE_ENTITLEMENT',[d['code'] for d in r['diagnostics']])
        path='roguelike/data/recipes/cook_meat.json'
        for value in ([],[{}]):
            r=invoke('preview_draft',asset=path,draft=json.dumps(value))
            self.assertTrue(r['ok'],r);self.assertIn('RECIPE_SHAPE',[d['code'] for d in r['result']['diagnostics']])

    def test_passive_probe_no_exchange_includes_real_implicit_condition(self):
        r=self.preview('dry_bitter_herb');self.assertTrue(r['valid'],r['diagnostics'])
        probe=r['family']['context']['records'][0]['probe'];yes,_,_,torch=probe['cases']
        self.assertTrue(yes['eligible']);self.assertIsNone(yes['committed']);self.assertEqual(yes['before'],yes['after'])
        self.assertFalse(yes['output']['in_inventory']);self.assertFalse(torch['eligible'])
        self.assertIn('stationary_fire',[d['tag'] for d in torch['missing']])
        immediate=self.preview('briar_binding_oil');self.assertTrue(immediate['valid'],immediate['diagnostics'])
        self.assertTrue(immediate['family']['context']['records'][0]['probe']['cases'][0]['committed'])

    def test_shape_numbers_references_and_templates_rejected_without_coercion(self):
        for field,values,code in [('processing_turns',[0,-1,True,1.5,2**53], 'PROCESSING_TURNS'),
                ('processing_source',['unknown',None,[]],'PROCESSING_SOURCE'),
                ('processing_decor',['crate','missing',None],'PROCESSING_DECOR'),
                ('completion_message',['Ready {unknown}','{item_name.name}','{item_name[0]}','{item_name!s}','{item_name:}','{item_name:>10}','{','}'], 'COMPLETION_TEMPLATE'),
                ('requires_single_item',[{},[],True,{'tags':[]}],'CONJUNCTION_SHAPE')]:
            for value in values:
                with self.subTest(field=field,value=value):
                    r=self.preview('dry_bitter_herb',{field:value});self.assertFalse(r['valid']);self.assertIn(code,[d['code'] for d in r['diagnostics']])
        for quantity in (True,0,33,1.5,2**53):
            r=self.preview('dry_bitter_herb',dict(requires_single_item=dict(tags=[dict(tag='edible')],max_quantity=quantity)))
            self.assertIn('REQUIREMENT_QUANTITY',[d['code'] for d in r['diagnostics']])
        r=self.preview('cook_meat',dict(processing_decor='',completion_message='{{Ready}} {item_name}'))
        self.assertTrue(r['valid'],r['diagnostics'])

    def test_protected_conjunction_negative_and_dependency_stamps(self):
        with tempfile.TemporaryDirectory(prefix='w5k-worker-') as folder:
            root=data_fixture(folder)
            # No invented conjunction choice channel: every matching saved
            # definition is protected while the catalogue remains factory-valid.
            for p in (root/'roguelike/data/items').rglob('*.json'):
                raw=json.loads(p.read_bytes())
                if isinstance(raw,dict):raw['consumed_on_use']=False;p.write_text(json.dumps(raw),encoding='utf-8')
            r=self.preview('dry_bitter_herb',root=root);self.assertTrue(r['valid'],r['diagnostics'])
            record=r['family']['context']['records'][0];self.assertTrue(record['candidates'][0]['matches'])
            self.assertFalse(record['candidates'][0]['automatic_matches']);self.assertFalse(record['probe']['cases'][0]['eligible'])
            previous=r['source']
            for relative in ('items/consumables/cooked_meat.json','keywords.json','decoratives.json','processing_messages.json'):
                p=root/'roguelike/data'/relative;p.write_bytes(p.read_bytes()+b'\n')
                r=self.preview('dry_bitter_herb',root=root);self.assertTrue(r['valid'],r['diagnostics'])
                self.assertNotEqual(previous['catalog_sha256'],r['source']['catalog_sha256']);previous=r['source']

    def test_combined_requirements_defaults_metadata_and_total_slot_bound(self):
        changes=dict(requires_single_item=dict(tags=[dict(tag='bitter',meta={'keep':[True,None]}),dict(tag='edible')],max_quantity=2,extra={'retained':1}),
            components=[dict(tag='vital')],tools=[dict(tag='vessel')])
        r=self.preview('dry_bitter_herb',changes);self.assertTrue(r['valid'],r['diagnostics'])
        record=r['family']['context']['records'][0];self.assertEqual(record['definition']['requires_single_item'],changes['requires_single_item'])
        yes=record['probe']['cases'][0];self.assertTrue(yes['eligible']);self.assertEqual(len(set(yes['selected'])),4);self.assertEqual(len(yes['materials']),3)
        changes['components']=[dict(tag='vital',quantity=32),dict(tag='vital',quantity=32)]
        r=self.preview('dry_bitter_herb',changes);self.assertIn('PROBE_LIMIT',[d['code'] for d in r['diagnostics']])

if __name__=='__main__':unittest.main()
