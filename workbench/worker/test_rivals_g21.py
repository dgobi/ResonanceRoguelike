"""Exact document authority; runtime targeting is covered by native saved probes."""
import copy
import json
import unittest
from test_bridge import ROOT, invoke

ASSET='roguelike/data/entities/creatures/highland_bandit.json'


class RivalAuthoringTests(unittest.TestCase):
    def test_supported_lists_empty_directional_and_token_bounds(self):
        raw=json.loads((ROOT/ASSET).read_bytes())
        for faction,hostile in [('outlaw',[]),('local_watch',['unmatched']),('outlaw',['player','stalker'])]:
            candidate=copy.deepcopy(raw);candidate['perception'].update(faction=faction,hostile_to=hostile)
            r=invoke('preview_draft',asset=ASSET,source_asset=ASSET,draft=json.dumps(candidate))['result']
            self.assertTrue(r['valid'],r['diagnostics'])
            record=r['family']['context']['records'][0]
            self.assertTrue(record['capability']['relationship_editable'])
            self.assertEqual(hostile,record['factory']['instance']['perception']['hostile_to'])
        for key,value in [('faction','Upper'),('faction','x'*33),('hostile_to','stalker'),('hostile_to',['outlaw','outlaw']),('hostile_to',[False]),('hostile_to',[f'group_{i}' for i in range(17)])]:
            candidate=copy.deepcopy(raw);candidate['perception'][key]=value
            r=invoke('preview_draft',asset=ASSET,source_asset=ASSET,draft=json.dumps(candidate))['result']
            self.assertFalse(r['valid']);self.assertIn('CREATURE_RELATIONSHIP',[d['code'] for d in r['diagnostics']])

    def test_original_and_candidate_archetype_entitlements_cannot_be_promoted(self):
        for identifier in ('stone_lurker','plague_crow','hollow_knight'):
            path=ASSET.replace('highland_bandit',identifier)
            raw=json.loads((ROOT/path).read_bytes());raw['perception']['hostile_to']=[]
            r=invoke('preview_draft',asset=path,source_asset=path,draft=json.dumps(raw))['result']
            self.assertFalse(r['valid']);self.assertIn('READ_ONLY_FIELD',[d['code'] for d in r['diagnostics']])
        raw=json.loads((ROOT/ASSET).read_bytes());raw.update(id='g21_variant',ai_type='ambush')
        target=ASSET.replace('highland_bandit','g21_variant')
        r=invoke('preview_draft',asset=target,source_asset=ASSET,draft=json.dumps(raw))['result']
        self.assertTrue(r['valid'],r['diagnostics'])
        self.assertFalse(r['family']['context']['records'][0]['capability']['relationship_editable'])
        raw['perception']['hostile_to']=[]
        self.assertFalse(invoke('preview_draft',asset=target,source_asset=ASSET,draft=json.dumps(raw))['result']['valid'])
