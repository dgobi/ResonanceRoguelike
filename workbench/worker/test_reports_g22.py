"""Bounded report attachment, including unbound production preview."""
import copy
import json
import tempfile
import unittest
from test_bridge import invoke
from test_texts import text_fixture

ASSET='roguelike/data/texts/lab/lab_route_sheet_a.json'
TARGET='roguelike/data/texts/lab/g22_worker_variant.json'


class ReportsTests(unittest.TestCase):
    def test_fixed_attachment_raw_negatives_and_unbound_reader(self):
        with tempfile.TemporaryDirectory(prefix='g22-text-') as directory:
            root=text_fixture(directory);raw=json.loads((root/ASSET).read_bytes());raw['id']='g22_worker_variant'
            for roles in ([],[dict(role='workshop')],[dict(role='ward_store')],[dict(role='workshop'),dict(role='ward_store')]):
                candidate=dict(raw,location_reports=roles)
                r=invoke('preview_draft',root=root,asset=TARGET,source_asset=ASSET,draft=json.dumps(candidate))
                self.assertTrue(r['ok']);self.assertTrue(r['result']['valid'],r)
            for value in (None,True,['workshop'],[dict(role='anything')],[dict(role='workshop'),dict(role='workshop')],[dict(role='ward_store',selector='expression')]):
                r=invoke('preview_draft',root=root,asset=TARGET,source_asset=ASSET,draft=json.dumps(dict(raw,location_reports=value)))
                self.assertTrue(r['ok']);self.assertFalse(r['result']['valid']);self.assertIn('TEXT_REPORTS',[d['code'] for d in r['result']['diagnostics']])
            r=invoke('preview_draft',root=root,asset=TARGET,source_asset=ASSET,draft=json.dumps(raw),preview_inputs=dict(page=1,scroll=0))
            self.assertTrue(r['ok'],r);self.assertEqual(1,r['result']['family_preview']['page'])
            self.assertFalse((root/TARGET).exists())
            self.assertFalse(invoke('inspect',root=root,asset='roguelike/data/layouts/starting_lab_b.json')['result']['editable'])


if __name__=='__main__':unittest.main()
