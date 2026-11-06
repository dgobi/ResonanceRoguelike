"""SYS-2 exact worker source entitlement, bounded controls and captured fields."""
import copy,json,unittest
from test_bridge import ROOT,invoke


class LightAuthoringTests(unittest.TestCase):
    def test_supported_light_factory_and_second_configuration(self):
        path='roguelike/data/items/tools/oil_lantern.json'
        raw=json.loads((ROOT/path).read_bytes())
        for radius,fuel in [(9,420),(3,8)]:
            candidate=dict(raw,id='light_witness',light_radius=radius,burn_turns=fuel)
            r=invoke('preview_draft',asset=path.replace('oil_lantern','light_witness'),source_asset=path,draft=json.dumps(candidate))['result']
            self.assertTrue(r['valid'],r.get('diagnostics'))
            self.assertEqual('held light',r['family']['context']['records'][0]['capability']['supply_class'])
            instance=r['family']['context']['records'][0]['factory']['instance']
            self.assertEqual(radius,instance['held_light']['radius']);self.assertEqual(fuel,instance['burn_turns'])
            self.assertEqual(raw['light'],instance['light_data'])

    def test_bounds_protected_use_heat_role_and_cosmetics(self):
        path='roguelike/data/items/tools/tallow_torch.json';raw=json.loads((ROOT/path).read_bytes())
        edits=[('light_radius',0),('light_radius',41),('light_radius',True),('burn_turns',0),('burn_turns',None),('burn_turns',10001),
               ('provides_burning',9),('consumed_on_use',True),('stackable',True),('on_use','equip_toggle'),('slot','belt'),('keywords',[])]
        for field,value in edits:
            with self.subTest(field=field,value=value):
                candidate=dict(raw);candidate[field]=value
                r=invoke('preview_draft',asset=path,draft=json.dumps(candidate))['result']
                self.assertFalse(r['valid'],r)
        for field,value in [('radius',15),('color',[1,2,3]),('falloff',0),('flicker',1)]:
            candidate=copy.deepcopy(raw);candidate['light'][field]=value
            r=invoke('preview_draft',asset=path,draft=json.dumps(candidate))['result']
            self.assertFalse(r['valid'],r)

    def test_original_unsupported_source_cannot_promote_to_light(self):
        path='roguelike/data/items/consumables/resonant_tincture.json'
        raw=json.loads((ROOT/'roguelike/data/items/tools/tallow_torch.json').read_bytes());raw['id']='resonant_tincture'
        r=invoke('preview_draft',asset='roguelike/data/items/tools/light_promotion.json',source_asset=path,draft=json.dumps(dict(raw,id='light_promotion')))['result']
        self.assertFalse(r['valid']);self.assertIn('SOURCE_ENTITLEMENT',[d['code'] for d in r['diagnostics']])


if __name__=='__main__':unittest.main()
