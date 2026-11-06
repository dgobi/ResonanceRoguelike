"""SYS-5 authoring entitlement, captured declarations and native remains trial."""
import copy
import json
import unittest
from test_bridge import ROOT, invoke


class ScavengingAuthoringTests(unittest.TestCase):
    def preview(self,source,raw,target=None):
        return invoke('preview_draft',asset=target or source,source_asset=source,draft=json.dumps(raw))['result']

    def test_same_attachment_on_two_hosts_and_original_authority(self):
        source='roguelike/data/entities/creatures/sewer_thing.json'
        original=(ROOT/source).read_bytes();raw=json.loads(original)
        inspected=invoke('inspect',asset=source)['result']
        cap=inspected['family']['context']['records'][0]['capability']
        for host in ('strike_and_withdraw','territorial_guard'):
            candidate=copy.deepcopy(raw)
            candidate.update(id='sys5_validation_eater',ai_type='composite',can_cross_chunks=False,can_use_stairs=False,
                ai_profile=cap['profile_recipes'][host],enemy_scavenging=cap['scavenging_defaults'])
            target=source.replace('sewer_thing','sys5_validation_eater')
            result=self.preview(source,candidate,target)
            self.assertTrue(result['valid'],result['diagnostics'])
            instance=result['family']['context']['records'][0]['factory']['instance']
            self.assertEqual(instance['effective_enemy_scavenging']['feed_opportunities'],3)
        candidate['enemy_scavenging']=dict(version=1,feed_opportunities=True)
        self.assertFalse(self.preview(source,candidate,target)['valid'])
        candidate['enemy_scavenging']=cap['scavenging_defaults'];candidate['ai_profile']=cap['profile_recipes']['observation_averse']
        self.assertFalse(self.preview(source,candidate,target)['valid'])
        candidate['id']=raw['id'];candidate['ai_profile']=cap['profile_recipes']['strike_and_withdraw']
        self.assertFalse(self.preview(source,candidate)['valid'])
        self.assertEqual((ROOT/source).read_bytes(),original)

    def test_flesh_output_authority_and_saved_reference_validation(self):
        source='roguelike/data/entities/creatures/plague_crow.json';raw=json.loads((ROOT/source).read_bytes())
        result=self.preview(source,raw);self.assertTrue(result['valid'],result['diagnostics'])
        bad=copy.deepcopy(raw);bad['butcher_yield']['tiers'][0]['yields'][1]['flesh']=True
        self.assertFalse(self.preview(source,bad)['valid'])
        bad=copy.deepcopy(raw);bad['butcher_yield']['tiers'][0]['yields'][0]['flesh']=False
        self.assertFalse(self.preview(source,bad)['valid'])
        bad=copy.deepcopy(raw);bad['butcher_yield']['tiers'][0]['yields'][0]['flesh']='true'
        self.assertFalse(self.preview(source,bad)['valid'])
        unsupported='roguelike/data/entities/creatures/bog_wraith.json'
        bad=json.loads((ROOT/unsupported).read_bytes());bad['ephemeral']=False;bad['butcher_yield']=raw['butcher_yield']
        self.assertFalse(self.preview(unsupported,bad)['valid'])

    def test_new_meat_keyword_factory_and_invalid_tier(self):
        source='roguelike/data/items/butchery/crow_meat.json';raw=json.loads((ROOT/source).read_bytes())
        raw.update(id='sys5_validation_meat',name='Validation flesh')
        target=source.replace('crow_meat','sys5_validation_meat')
        result=self.preview(source,raw,target);self.assertTrue(result['valid'],result['diagnostics'])
        next(k for k in raw['keywords'] if k['tag']=='flesh')['tier']=2
        self.assertFalse(self.preview(source,raw,target)['valid'])

    def test_remains_native_trial_and_invalid_source_location(self):
        source='roguelike/data/layouts/sys4_access_room.json';original=(ROOT/source).read_bytes()
        raw=json.loads(original);raw['id']='sys5_validation_room'
        raw['special_tiles']=[dict(type='remains',x=7,y=5,creature_id='plague_crow')]
        target=source.replace('sys4_access_room','sys5_validation_room')
        result=self.preview(source,raw,target);self.assertTrue(result['valid'],result['diagnostics'])
        for source_id in ('sewer_thing','missing','bog_wraith'):
            bad=copy.deepcopy(raw);bad['special_tiles'][0]['creature_id']=source_id
            self.assertFalse(self.preview(source,bad,target)['valid'])
        bad=copy.deepcopy(raw);bad['special_tiles'][0].update(raw['player_start'])
        self.assertFalse(self.preview(source,bad,target)['valid'])
        bad=copy.deepcopy(raw);bad['special_tiles'][0]['state']='stripped'
        self.assertFalse(self.preview(source,bad,target)['valid'])
        self.assertEqual((ROOT/source).read_bytes(),original)


if __name__=='__main__':unittest.main()
