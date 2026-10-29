"""Real worker furnished-room admission and saved dependency freshness."""
import copy, json, tempfile, unittest
import test_rooms_w5g
from test_bridge import invoke


class FurnishedWorker(test_rooms_w5g.RoomTests):
    # Reuse the established lifecycle/reference cases with a furnished source.
    def setUp(self):
        super().setUp()
        self.raw['special_tiles'] += [dict(type='decor',x=4,y=3,decor_id='campfire_unlit'),
                                     dict(type='decor',x=1,y=1,decor_id='worn_mat')]
        self.save()

    def test_furnished_receipts_and_source_bound_saved_dependency_change(self):
        result=self.check(self.raw);self.assertTrue(result['valid'],result['diagnostics'])
        self.assertEqual(result['layout_contract'],'authored-room-2')
        receipt=result['preview']['population_receipts'][-2]
        self.assertEqual(receipt['objects'],[]);self.assertEqual(receipt['realized_decor']['id'],'campfire_unlit')
        before=result['source']['data_sha256'] if 'data_sha256' in result['source'] else result['source']
        p=self.root/'roguelike/data/decoratives.json';raw=json.loads(p.read_bytes())
        next(r for r in raw if r['id']=='campfire_unlit')['description']='Actual saved furnishing change'
        p.write_text(json.dumps(raw),encoding='utf-8')
        after=self.check(self.raw);self.assertTrue(after['valid'],after['diagnostics']);self.assertNotEqual(before,after['source'].get('data_sha256',after['source']))

    def test_registry_ambiguity_and_final_invalid_layout_refused(self):
        p=self.root/'roguelike/data/decoratives.json';original=p.read_bytes();rows=json.loads(original)
        rows.append(copy.deepcopy(next(r for r in rows if r['id']=='campfire_unlit')))
        p.write_text(json.dumps(rows),encoding='utf-8')
        result=self.check(self.raw);self.assertFalse(result['valid']);self.assertIn('DECOR_CAPABILITY',str(result['diagnostics']))
        p.write_bytes(original)
        raw=copy.deepcopy(self.raw);raw['special_tiles'][-2].update(x=2,y=5)
        result=self.check(raw);self.assertFalse(result['valid']);self.assertIn('special_tiles[3]',str(result['diagnostics']))

    # Historical exact receipt counts/positions are covered by the base class on
    # its original fixture, not repeated against this deliberately extended one.
    test_receipt_owned_overlapping_items_relocation_and_container_access=None
