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
