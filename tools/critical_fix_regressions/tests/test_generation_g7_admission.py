"""A consumer-specific obligation, without changing historical compilation."""
import copy
import random
import unittest
from unittest.mock import patch
from test_effect_persistence import load_data
from generation.context import GenerationError
from generation.poi_selection import resolve, require_usable_goal
from generation.poi_preview import site_preview
from generation.structure_contract import compile_structure
from generation.structure_preview import preview
from generation.world_gen import generate_world
from world.world_map import WorldMap


class G7Admission(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=load_data()

    def draft(self):
        data=copy.copy(self.data);data.structures=copy.deepcopy(self.data.structures)
        for t in data.structures['roadside_shrine_a']['placement']['targets']:t['required']=False
        return data

    def test_all_optional_is_legal_direct_but_rejected_before_selection(self):
        data=self.draft();raw=data.structures['roadside_shrine_a']
        compile_structure(raw,'ordinary_building',data,category='wilderness')
        entrance=raw['placement']['entrances'][0]
        result,_,_=preview(raw,'ordinary_building',data,category='wilderness',expectations=dict(entry=dict(x=entrance['x'],y=entrance['y']),targets=raw['placement']['targets']))
        self.assertTrue(result['passed'])
        for action in (lambda:resolve(data),lambda:site_preview(data,20261023,raw,normal='S')):
            with self.assertRaisesRegex(GenerationError,'roadside_shrine_a.*additional rural-site.*required usable target.*required: true'):
                action()
        w=WorldMap(128,128);w.seed=20261023;before=copy.deepcopy(vars(w))
        with patch('generation.poi_selection.candidates',side_effect=AssertionError('fitting started')):
            with self.assertRaisesRegex(GenerationError,'required usable target'):generate_world(w,data,random.Random(0))
        self.assertEqual(vars(w),before)

    def test_mixed_targets_and_shipped_candidates_remain_eligible(self):
        self.assertTrue(resolve(self.data))
        data=self.draft();raw=data.structures['roadside_shrine_a']
        raw['placement']['targets'].append(dict(raw['placement']['targets'][0],required=True))
        self.assertTrue(resolve(data))
        self.assertTrue(site_preview(data,20261023,raw,normal='S')['passed'])
        for consumer in ('additional rural-site candidate','compound child slot house'):
            with self.assertRaisesRegex(GenerationError,consumer):require_usable_goal(self.draft().structures['roadside_shrine_a'],consumer)
