"""AI-1 exact-source authority and shared game-owned profile validation."""
import copy
import json
import unittest
from test_bridge import ROOT, invoke

BASE='roguelike/data/entities/creatures/'
SOURCE=BASE+'hollow_revenant.json'


class CompositeAuthoringTests(unittest.TestCase):
    def test_independent_enemy_responses_game_defaults_host_and_exact_metadata(self):
        raw=self.draft();raw['perception'].update(faction='hollow',hostile_to=['player'])
        for recipe,version in [('strike_and_withdraw',1),('territorial_guard',5)]:
            raw['ai_profile']={'version':version,'recipe':recipe}
            for ids in [('alarm_call_on_sight',),('investigate_allied_alarm',),('alarm_call_on_sight','investigate_allied_alarm')]:
                raw['enemy_responses']={'version':1,'modules':[{'id':k} for k in ids]}
                r=self.validate(raw);self.assertTrue(r['valid'],r['diagnostics'])
                record=r['family']['context']['records'][0]
                self.assertEqual(2,len(record['capability']['response_defaults']))
                self.assertEqual(list(ids),[m['id'] for m in record['factory']['instance']['effective_enemy_responses']['modules']])
        for value in (True,0,25):
            raw['enemy_responses']={'version':1,'modules':[{'id':'investigate_allied_alarm','opportunity_budget':value}]}
            self.assertFalse(self.validate(raw)['valid'])
        raw['enemy_responses']={'version':1,'modules':[{'id':'alarm_call_on_sight'}]}
        raw['perception']['faction']='player';self.assertFalse(self.validate(raw)['valid'])

    def test_escort_registry_alignment_bounds_same_id_tuning_and_preserved_art(self):
        raw=self.draft();raw['ai_profile']={'version':6,'recipe':'protective_escort'}
        raw['perception'].update(faction='player',hostile_to=['hollow'])
        r=self.validate(raw);self.assertTrue(r['valid'],r['diagnostics'])
        record=r['family']['context']['records'][0]
        self.assertIn('protective_escort',record['capability']['profile_recipes'])
        self.assertEqual([1,2],record['capability']['profile_recipe_bounds']['protective_escort']['follow_spacing'])
        for field,value in [('initial_order','attack'),('follow_spacing',True),('follow_spacing',3),('protection_radius',6),('pursuit_budget',33)]:
            bad=copy.deepcopy(raw);bad['ai_profile'][field]=value
            self.assertFalse(self.validate(bad)['valid'],(field,value))
        for faction,hostile in [('hollow',['hollow']),('player',['player']),('player',None)]:
            bad=copy.deepcopy(raw);bad['perception'].update(faction=faction,hostile_to=hostile)
            self.assertFalse(self.validate(bad)['valid'])
        for identifier in ('ash_escort','stone_escort'):
            path=BASE+identifier+'.json';original=json.loads((ROOT/path).read_bytes());raw=copy.deepcopy(original)
            raw['ai_profile']['initial_order']='hold' if raw['ai_profile']['initial_order']=='follow' else 'follow'
            self.assertTrue(invoke('preview_draft',asset=path,source_asset=path,draft=json.dumps(raw))['result']['valid'])
            raw['tile']='plague_crow'
            self.assertFalse(invoke('preview_draft',asset=path,source_asset=path,draft=json.dumps(raw))['result']['valid'])

    def test_territorial_profile_two_engagements_strict_bounds_and_host_authority(self):
        raw=self.draft();raw['ai_profile']={'version':5,'recipe':'territorial_guard'}
        for engagement in ('direct_melee','strike_and_withdraw'):
            raw['ai_profile']['engagement']=engagement
            r=self.validate(raw);self.assertTrue(r['valid'],r['diagnostics'])
            p=r['family']['context']['records'][0]['factory']['instance']['effective_ai_profile']
            self.assertEqual((4,6,32,engagement),tuple(p[k] for k in ('defended_radius','excursion_radius','pursuit_budget','engagement')))
        for field,value in [('defended_radius',True),('defended_radius',6),('excursion_radius',4),('excursion_radius',9),('engagement','venom'),('scene_scope','world'),('pursuit_budget',0)]:
            bad=copy.deepcopy(raw);bad['ai_profile'][field]=value
            self.assertFalse(self.validate(bad)['valid'],(field,value))
        raw['ai_profile'].update(engagement='direct_melee',hold_opportunities=3)
        self.assertFalse(self.validate(raw)['valid'])
        raw['ai_profile']['engagement']='strike_and_withdraw';self.assertTrue(self.validate(raw)['valid'])

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
        self.assertEqual('creature-composite-9',record['capability']['contract'])
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

    def test_venom_recipe_trait_bounds_and_same_id_family_protection(self):
        raw=self.draft();raw['id']='ai3_contract_variant'
        raw['ai_profile']={'version':3,'recipe':'venom_strike_and_withdraw'}
        raw['numbing_venom_trait']='immune'
        r=self.validate(raw);self.assertTrue(r['valid'],r['diagnostics'])
        p=r['family']['context']['records'][0]['factory']['instance']['effective_ai_profile']
        self.assertEqual(('numbing_melee','accepted_application','numbing_venom',3,3,4),
            tuple(p[k] for k in ('capability','trigger','effect','warning_phases','paralysis_phases','recovery_phases')))
        for field,value in [('warning_phases',1),('paralysis_phases',4),('recovery_phases',3),('trigger','hit'),('effect','other')]:
            bad=copy.deepcopy(raw);bad['ai_profile'][field]=value
            self.assertFalse(self.validate(bad)['valid'],(field,value))
        bad=copy.deepcopy(raw);bad['numbing_venom_trait']='resistant'
        self.assertFalse(self.validate(bad)['valid'])
        path=BASE+'grave_skirmisher.json';same=json.loads((ROOT/path).read_bytes());same['ai_profile']=raw['ai_profile']
        self.assertFalse(invoke('preview_draft',asset=path,source_asset=path,draft=json.dumps(same))['result']['valid'])

    def test_observation_recipe_defaults_and_strict_discriminator(self):
        raw=self.draft();raw['id']='ai2_contract_variant'
        raw['ai_profile']={'version':2,'recipe':'observation_averse'}
        r=self.validate(raw);self.assertTrue(r['valid'],r['diagnostics'])
        p=r['family']['context']['records'][0]['factory']['instance']['effective_ai_profile']
        self.assertEqual((8,1,'defensive_melee',32),(p['concealment_budget'],p['unseen_extra_step'],p['no_cover'],p['pursuit_budget']))
        for field,value in [('version',1),('unseen_extra_step',2),('unseen_extra_step',True),('concealment_budget',0),('pursuit_budget',65),('no_cover','attack_anyone'),('trigger','hit'),('observer','camera')]:
            bad=copy.deepcopy(raw);bad['ai_profile'][field]=value
            self.assertFalse(self.validate(bad)['valid'],(field,value))
        old=BASE+'grave_skirmisher.json';same=json.loads((ROOT/old).read_bytes())
        same['ai_profile']=raw['ai_profile']
        r=invoke('preview_draft',asset=old,source_asset=old,draft=json.dumps(same))['result']
        self.assertIn('COMPOSITE_RECIPE_ID',[d['code'] for d in r['diagnostics']])

    def test_patient_policy_reuses_delivery_and_preserves_protected_insect_source(self):
        raw=self.draft();raw['ai_profile']={'version':4,'recipe':'patient_venom_hunt'}
        for policy in ('observed_paralysis','after_hold'):
            raw['ai_profile']['return_policy']=policy
            r=self.validate(raw);self.assertTrue(r['valid'],r['diagnostics'])
            p=r['family']['context']['records'][0]['factory']['instance']['effective_ai_profile']
            self.assertEqual(('numbing_melee','accepted_application',policy),tuple(p[k] for k in ('capability','trigger','return_policy')))
        for field,value in [('return_policy','effect_link'),('version',3),('observer','debug_reveal')]:
            bad=copy.deepcopy(raw);bad['ai_profile'][field]=value
            self.assertFalse(self.validate(bad)['valid'])
        source=BASE+'patient_amber_hunter.json';saved=json.loads((ROOT/source).read_bytes())
        saved['ai_profile']['return_policy']='after_hold'
        self.assertTrue(invoke('preview_draft',asset=source,source_asset=source,draft=json.dumps(saved))['result']['valid'])
        saved['limbs'][0]['size']=20
        self.assertFalse(invoke('preview_draft',asset=source,source_asset=source,draft=json.dumps(saved))['result']['valid'])
        a=json.loads((ROOT/BASE/'patient_amber_hunter.json').read_bytes())
        b=json.loads((ROOT/BASE/'timed_amber_hunter.json').read_bytes())
        for v in (a,b):
            for key in ('id','name','description'):v.pop(key)
            v['ai_profile'].pop('return_policy')
        self.assertEqual(a,b)


if __name__=='__main__':unittest.main()
