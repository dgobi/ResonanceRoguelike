"""W5J trusted-worker variants, original permissions and exact dependencies."""
import copy, json, tempfile, unittest
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

class SuppliesWorker(unittest.TestCase):
    def test_unsupported_candidate_shapes_are_located_not_generic_worker_failures(self):
        path='roguelike/data/items/butchery/crow_meat.json'
        raw=json.loads((ROOT/path).read_bytes())
        # Keep the original catalogue valid; only the candidate takes array shape.
        for candidate in ([raw], [], [{}]):
            for variant in (False, True):
                target=path.replace('crow_meat.json','shape_variant.json') if variant else path
                response=invoke('preview_draft',asset=target,source_asset=path,draft=json.dumps(candidate))
                self.assertTrue(response['ok'],response)
                result=response['result'];self.assertFalse(result['valid']);self.assertIsNone(result['family']['context'])
                diagnostic=next(d for d in result['diagnostics'] if d['code']=='ITEM_SHAPE')
                self.assertEqual(diagnostic['path'],target);self.assertEqual(diagnostic['field'],'')

    def test_four_classes_second_food_and_original_promotion_rejected(self):
        for source,changes in [('components/wood_bundle',dict(weight=.75)),('butchery/animal_bone',dict(name='Second material')),
                ('consumables/bitter_herb',dict(nutrition=.35)),('consumables/cooked_meat',dict(nutrition=300)),
                ('consumables/water_flask',dict(hydration=0,empty_form='clay_pot')),('consumables/herbal_dressing',dict(heal_amount=7))]:
            path='roguelike/data/items/'+source+'.json';raw=json.loads((ROOT/path).read_bytes());raw.update(changes)
            for variant in (False,True):
                candidate=dict(raw,id='w5j_'+raw['id']) if variant else raw
                target=path.rsplit('/',1)[0]+'/'+candidate['id']+'.json' if variant else path
                result=invoke('preview_draft',asset=target,source_asset=path,draft=json.dumps(candidate))['result']
                self.assertTrue(result['valid'],result);self.assertTrue(result['factory_verified']);self.assertEqual(result['family']['contract'],'expedition-items-2')
            candidate=dict(raw,on_use='drink' if raw.get('on_use')!='drink' else 'eat')
            result=invoke('preview_draft',asset=path,draft=json.dumps(candidate))['result']
            self.assertFalse(result['valid']);self.assertIn('ITEM_CLASS',[d['code'] for d in result['diagnostics']])
        for source in ('consumables/empty_water_skin','consumables/resonant_tincture','tools/leather_satchel'):
            path='roguelike/data/items/'+source+'.json'
            if not (ROOT/path).exists():continue
            raw=json.loads((ROOT/path).read_bytes());raw={k:v for k,v in raw.items() if k in ('id','name','description','weight','tile','keywords','stackable')};raw['category']='consumable';raw['on_use']=None
            result=invoke('preview_draft',asset=path,draft=json.dumps(raw))['result']
            self.assertFalse(result['valid']);self.assertIn('SOURCE_ENTITLEMENT',[d['code'] for d in result['diagnostics']])

    def test_return_and_survival_changes_stale_source_identity(self):
        path='roguelike/data/items/consumables/water_flask.json'
        with tempfile.TemporaryDirectory(prefix='w5j-worker-') as folder:
            root=data_fixture(folder);raw=json.loads((root/path).read_bytes());raw['empty_form']='clay_pot';draft=json.dumps(raw)
            first=invoke('preview_draft',root=root,asset=path,draft=draft)['result']
            for relative in ('items/components/clay_pot.json','survival.json'):
                p=root/'roguelike/data'/relative;p.write_bytes(p.read_bytes()+b'\n')
                after=invoke('preview_draft',root=root,asset=path,draft=draft)['result']
                self.assertTrue(after['valid']);self.assertNotEqual(first['source']['catalog_sha256'],after['source']['catalog_sha256'])
                first=after

if __name__=='__main__':unittest.main()
