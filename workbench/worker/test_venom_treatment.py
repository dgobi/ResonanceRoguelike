"""Cure seed grants a narrow new-ID item route, never class conversion."""
import json
import unittest
from test_bridge import ROOT, invoke

class VenomTreatmentAuthoring(unittest.TestCase):
    def test_seed_duplicate_tune_and_protected_binding(self):
        source='roguelike/data/items/consumables/venom_treatment.json'
        raw=json.loads((ROOT/source).read_bytes());raw.update(id='ai3_remedy_variant',name='Measured Remedy',weight=.2)
        target=source.replace('venom_treatment.json','ai3_remedy_variant.json')
        r=invoke('preview_draft',asset=target,source_asset=source,draft=json.dumps(raw))['result']
        self.assertTrue(r['valid'],r['diagnostics'])
        record=r['family']['context']['records'][0]
        self.assertEqual('venom treatment',record['capability']['supply_class'])
        self.assertIn('accepted dose snapshot',record['effective_use']['explanation'])
        for field,value in [('on_use','heal_minor'),('heal_amount',12),('effects',[]),('nutrition',80)]:
            changed=dict(raw,**{field:value})
            self.assertFalse(invoke('preview_draft',asset=target,source_asset=source,draft=json.dumps(changed))['result']['valid'])
        dressing=source.replace('venom_treatment.json','herbal_dressing.json')
        changed=json.loads((ROOT/dressing).read_bytes());changed.pop('heal_amount');changed['on_use']='cure_numbing_venom'
        self.assertFalse(invoke('preview_draft',asset=dressing,source_asset=dressing,draft=json.dumps(changed))['result']['valid'])

if __name__=='__main__':unittest.main()
