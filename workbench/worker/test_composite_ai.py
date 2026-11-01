"""AI-1 exact-source authority and shared game-owned profile validation."""
import copy
import json
import unittest
from test_bridge import ROOT, invoke

BASE='roguelike/data/entities/creatures/'
SOURCE=BASE+'hollow_revenant.json'


class CompositeAuthoringTests(unittest.TestCase):
    def draft(self):
        raw=json.loads((ROOT/SOURCE).read_bytes())
        raw.update(id='ai1_contract_variant',ai_type='composite',ai_profile={'version':1,'recipe':'strike_and_withdraw'},
                   can_cross_chunks=False,can_use_stairs=False)
        return raw

    def validate(self,raw,source=SOURCE):
        return invoke('preview_draft',asset=BASE+raw['id']+'.json',source_asset=source,draft=json.dumps(raw))['result']

    def test_defaults_construct_same_contract_without_turns(self):
        r=self.validate(self.draft());self.assertTrue(r['valid'],r['diagnostics'])
        record=r['family']['context']['records'][0]
        self.assertEqual('creature-composite-4',record['capability']['contract'])
        self.assertEqual('CompositeAI',record['factory']['instance']['ai_class'])
        p=record['factory']['instance']['effective_ai_profile']
        self.assertEqual((2,1,6,12),(p['retreat_distance'],p['hold_opportunities'],p['withdrawal_budget'],p['pursuit_timeout']))
        self.assertIn('fresh actors',r['family']['descriptor']['publication_note'])
        self.assertFalse((ROOT/BASE/'ai1_contract_variant.json').exists())

    def test_invalid_profiles_retain_exact_repairable_draft_and_diagnostic(self):
        for key,value in [('version',True),('version',2),('recipe','planner'),('trigger','poisoned'),('capability','crow_range'),
                          ('retreat_distance',True),('retreat_distance',1.5),('hold_opportunities',-1),
                          ('withdrawal_budget',33),('scene_scope','world'),('target_id','player')]:
            raw=self.draft();raw['ai_profile'][key]=value
            r=self.validate(raw);self.assertFalse(r['valid'],(key,value))
            self.assertIn('CREATURE_PROFILE',[d['code'] for d in r['diagnostics']])
        raw=self.draft();raw['can_use_stairs']=True;self.assertFalse(self.validate(raw)['valid'])

    def test_source_cannot_be_promoted_by_deleting_special_fields(self):
        raw=self.draft()
        raw['id']='hollow_revenant'
        r=invoke('preview_draft',asset=SOURCE,source_asset=SOURCE,draft=json.dumps(raw))['result']
        self.assertFalse(r['valid']);self.assertIn('COMPOSITE_AUTHORITY',[d['code'] for d in r['diagnostics']])
        for identifier in ('stone_lurker','plague_crow'):
            raw=json.loads((ROOT/BASE/(identifier+'.json')).read_bytes())
            raw.update(id='ai1_contract_variant',ai_type='composite',ai_profile={'version':1},can_cross_chunks=False,can_use_stairs=False)
            raw.pop('ranged_attack',None)
            self.assertFalse(self.validate(raw,BASE+identifier+'.json')['valid'])

    def test_saved_examples_same_id_profile_edit_and_protected_metadata(self):
        for identifier in ('grave_skirmisher','grave_harrier'):
            path=BASE+identifier+'.json';raw=json.loads((ROOT/path).read_bytes())
            original=copy.deepcopy(raw);raw['ai_profile']['hold_opportunities']=0
            r=invoke('preview_draft',asset=path,source_asset=path,draft=json.dumps(raw))['result']
            self.assertTrue(r['valid'],r['diagnostics'])
            for key,value in [('can_cross_chunks',True),('tile','plague_crow'),('ai_type','wandering')]:
                changed=copy.deepcopy(original);changed[key]=value
                self.assertFalse(invoke('preview_draft',asset=path,source_asset=path,draft=json.dumps(changed))['result']['valid'])


if __name__=='__main__':unittest.main()
