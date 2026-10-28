"""Registered fixed assignment profile, exact bytes and saved-only generation."""
import copy, hashlib, json, tempfile, unittest
from test_authoring import data_fixture
from test_bridge import ROOT, invoke
PROFILE='roguelike/data/generation/authored_submap_selection.json'

class AssignmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='assignment-worker-');self.addCleanup(self.temp.cleanup)
        self.root=data_fixture(self.temp.name)
        room=json.loads((ROOT/'roguelike/docs/examples/g17_authored_creature_room.json').read_bytes());room['id']='assignment_room'
        (self.root/'roguelike/data/layouts/assignment_room.json').write_text(json.dumps(room),encoding='utf-8')
        self.raw=json.loads((self.root/PROFILE).read_bytes())
    def check(self,raw,**kwargs):
        r=invoke('preview_draft',root=self.root,asset=PROFILE,source_asset=PROFILE,draft=json.dumps(raw),**kwargs)
        self.assertTrue(r['ok'],r);return r['result']
    def test_fixed_registered_operations_exact_bytes_and_inactive_diagnostics(self):
        r=invoke('inspect',root=self.root,asset=PROFILE)['result'];self.assertTrue(r['editable']);self.assertEqual(r['family']['effective_operations'],['edit'])
        self.assertEqual(r['raw'].encode(),(self.root/PROFILE).read_bytes())
        raw=dict(self.raw,enabled=True,authored_chance=1,candidates=[dict(layout_id='assignment_room',weight=1)])
        result=self.check(raw);self.assertTrue(result['valid'],result);self.assertIsNone(result['family_preview'])
        self.assertEqual(result['draft_sha256'],hashlib.sha256(json.dumps(raw).encode()).hexdigest())
        self.assertEqual((self.root/PROFILE).read_bytes(),r['raw'].encode())
        result=self.check(dict(raw,enabled=False,candidates=[dict(layout_id='absent',weight=1)]));self.assertTrue(result['valid']);self.assertTrue(result['diagnostics'])
    def test_active_dependencies_and_original_identity_cannot_be_promoted(self):
        raw=dict(self.raw,enabled=True,authored_chance=1,candidates=[dict(layout_id='starting_lab',weight=1)])
        self.assertFalse(self.check(raw)['valid'])
        for mutation in (dict(id='other'),dict(version=2),dict(version=True)):
            self.assertFalse(self.check(dict(self.raw,**mutation))['valid'])
        (self.root/PROFILE).write_text(json.dumps(dict(self.raw,version=2)))
        self.assertFalse(self.check(self.raw)['valid'])
        r=invoke('preview_draft',root=self.root,asset='roguelike/data/generation/other.json',source_asset=PROFILE,draft=json.dumps(self.raw))
        self.assertFalse(r['ok'])
    def test_preview_refuses_unsaved_assignment_and_binds_actual_default_world(self):
        raw=dict(self.raw,enabled=True,authored_chance=1,candidates=[dict(layout_id='assignment_room',weight=1)])
        r=invoke('preview_draft',root=self.root,asset=PROFILE,source_asset=PROFILE,draft=json.dumps(raw),preview_inputs={'seed':20261028})
        self.assertFalse(r['ok']);self.assertIn('saved assignments',r['error']['message'])
        (self.root/PROFILE).write_text(json.dumps(raw),encoding='utf-8')
        r=self.check(raw,preview_inputs={'seed':20261028});self.assertTrue(r['valid'],r)
        p=r['family_preview'];self.assertEqual((p['width'],p['height'],p['plan_mode']),(128,128,'shared-v1'))
        self.assertGreater(p['matching_count'],0);self.assertEqual(p['authored_count'],p['matching_count']);self.assertEqual(p['procedural_count'],0)
        self.assertTrue(all(row['layout_id']=='assignment_room' for row in p['rows']));self.assertEqual(p['truncated']+len(p['rows']),p['authored_count'])
        self.assertEqual(p['profile_sha256'],hashlib.sha256((self.root/PROFILE).read_bytes()).hexdigest())

if __name__=='__main__': unittest.main()
