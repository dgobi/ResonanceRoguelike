"""SYS-4 registered profile and real host preview/publication boundary."""
import copy,json,tempfile,unittest
from test_bridge import ROOT,invoke
from test_authoring import data_fixture
PROFILE='roguelike/data/access_profiles/pale_lashings.json'
ROOM='roguelike/data/layouts/barrow_bound_store.json'
BUILDING='roguelike/data/buildings/commercial/workshop_e.json'


class AccessAuthoringTests(unittest.TestCase):
    def test_registered_noop_references_and_both_real_host_previews(self):
        r=invoke('inspect',asset=PROFILE)['result']
        self.assertTrue(r['valid'],r['diagnostics']);self.assertTrue(r['editable'])
        self.assertEqual('access',r['family']['id']);self.assertTrue(r['family']['compatible'])
        self.assertEqual({'building','room'},{x['family'] for x in r['family']['context']['references']})
        v=invoke('preview_draft',asset=PROFILE,draft=r['raw'])['result'];self.assertTrue(v['valid'],v['diagnostics'])
        for asset in (ROOM,BUILDING):
            v=invoke('inspect',asset=asset)['result'];self.assertTrue(v['valid'],v['diagnostics'])
            self.assertTrue(v['preview']['passed'])
            self.assertTrue(any(c['secured'] for c in v['preview']['containers']))
            if asset==ROOM:
                self.assertTrue(v['preview']['access_objects'])
                self.assertTrue(all(a['passed'] for a in v['preview']['access']))

    def test_profile_revision_variant_strict_invalid_and_exact_source(self):
        before=(ROOT/PROFILE).read_bytes();raw=json.loads(before)
        v=invoke('preview_draft',asset=PROFILE,draft=json.dumps(dict(raw,work_steps=2)))['result']
        self.assertTrue(v['valid'],v['diagnostics'])
        variant=dict(raw,id='sys4_worker_variant',work_steps=2,dissolution_threshold=.6)
        target=PROFILE.replace('pale_lashings','sys4_worker_variant')
        v=invoke('preview_draft',asset=target,source_asset=PROFILE,draft=json.dumps(variant))['result']
        self.assertTrue(v['valid'],v['diagnostics']);self.assertFalse((ROOT/target).exists())
        for key,value in [('work_steps',True),('version',2),('dissolution_threshold',0),('screen_careful_yield','crude_blade'),('extra_effect','damage')]:
            with self.subTest(key=key):
                v=invoke('preview_draft',asset=PROFILE,draft=json.dumps(dict(raw,**{key:value})))['result']
                self.assertFalse(v['valid']);self.assertTrue(v['diagnostics'])
        self.assertEqual(before,(ROOT/PROFILE).read_bytes())

    def test_screen_overlap_invalid_reference_and_readonly_decor_stay_rejected(self):
        raw=json.loads((ROOT/ROOM).read_bytes());before=(ROOT/ROOM).read_bytes()
        for change in ('arrival','container','missing','vine'):
            r=copy.deepcopy(raw)
            if change=='arrival':r['special_tiles'][0].update(r['player_start'])
            elif change=='container':r['special_tiles'][0].update(x=7,y=5)
            elif change=='missing':r['special_tiles'][0]['access_profile']='missing_profile'
            else:r['special_tiles'].append(dict(type='decor',x=5,y=5,decor_id='vine_growth'))
            v=invoke('preview_draft',asset=ROOM,draft=json.dumps(r))['result'];self.assertFalse(v['valid'],change)
        self.assertEqual(before,(ROOT/ROOM).read_bytes())

    def test_original_unsupported_source_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory(prefix='sys4-worker-') as tmp:
            root=data_fixture(tmp);nested=root/'roguelike/data/access_profiles/nested';nested.mkdir()
            raw=json.loads((ROOT/PROFILE).read_bytes());raw['id']='nested_profile'
            source='roguelike/data/access_profiles/nested/nested_profile.json';(root/source).write_text(json.dumps(raw))
            opened=invoke('inspect',root=root,asset=source)['result'];self.assertFalse(opened['editable'])
            raw['id']='promoted_profile'
            r=invoke('preview_draft',root=root,asset='roguelike/data/access_profiles/promoted_profile.json',source_asset=source,draft=json.dumps(raw))
            self.assertTrue(r['ok'],r);self.assertFalse(r['result']['valid'])
            self.assertIn('SOURCE_ENTITLEMENT',[d['code'] for d in r['result']['diagnostics']])

    def test_saved_dependency_failure_allows_diagnosis_and_exact_repair_only(self):
        import contextlib,io,sys
        sys.path.insert(0,str(ROOT/'roguelike'))
        from engine.data_loader import DataLoader
        from generation.structure_contract import StructureError
        wood='roguelike/data/items/components/wood_bundle.json'
        with tempfile.TemporaryDirectory(prefix='sys4-repair-') as tmp:
            root=data_fixture(tmp)
            for asset,field,value in ((PROFILE,'work_steps',0),(wood,'consumed_on_use',None)):
                saved=(root/asset).read_bytes();raw=json.loads(saved);raw[field]=value
                invalid=json.dumps(raw);(root/asset).write_text(invalid,encoding='utf8')
                with contextlib.redirect_stdout(io.StringIO()),self.assertRaises(StructureError):
                    DataLoader(str(root/'roguelike/data'))
                opened=invoke('inspect',root=root,asset=asset)['result']
                self.assertFalse(opened['valid']);self.assertTrue(opened['editable'],opened['diagnostics'])
                self.assertEqual(invalid,opened['raw'])
                if asset==wood:
                    self.assertTrue(any(d['code']=='ITEM_FIELD' and d['field']==field for d in opened['diagnostics']))
                else:
                    independent=invoke('inspect',root=root,asset='roguelike/data/items/components/flint_shard.json')['result']
                    self.assertFalse(independent['valid'])
                    self.assertIsNone(independent['family']['context']['records'][0]['factory']['loaded_catalog_sha256'])
                rejected=invoke('preview_draft',root=root,asset=asset,draft=invalid)['result']
                self.assertFalse(rejected['valid']);self.assertFalse(rejected['semantic_verified'])
                fixed=invoke('preview_draft',root=root,asset=asset,draft=saved.decode())['result']
                self.assertTrue(fixed['valid'],fixed['diagnostics']);self.assertTrue(fixed['semantic_verified'])
                self.assertEqual(invalid,(root/asset).read_text(encoding='utf8'))
                (root/asset).write_bytes(saved)
            saved=(root/PROFILE).read_bytes();unsupported=dict(json.loads(saved),version=2)
            (root/PROFILE).write_text(json.dumps(unsupported),encoding='utf8')
            self.assertFalse(invoke('inspect',root=root,asset=PROFILE)['result']['editable'])
            refused=invoke('preview_draft',root=root,asset=PROFILE,draft=saved.decode())['result']
            self.assertFalse(refused['valid']);self.assertIn('SOURCE_ENTITLEMENT',[d['code'] for d in refused['diagnostics']])
