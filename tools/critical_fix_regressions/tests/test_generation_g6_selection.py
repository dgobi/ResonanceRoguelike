"""Original bounded review fixtures through the corrected production fitter."""
import contextlib
import copy
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
FIXTURES=Path(__file__).resolve().parents[1]/'fixtures/g6'


class G6Selection(unittest.TestCase):
    def probe(self,name):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'result.json'
            with patch.object(sys,'argv',[name,'--source',str(ROOT),'--output',str(output)]),contextlib.redirect_stdout(io.StringIO()):
                scope=runpy.run_path(str(FIXTURES/name))
            return scope,json.loads(output.read_text())

    def test_same_seed_transform_witness_and_atomic_failure_distinction(self):
        scope,result=self.probe('probe_required_transform_search.py')
        self.assertTrue(all(r['accepted'] for r in result['ordinary_rng_order']))
        self.assertTrue(result['feasible_transform_witness']['accepted'])
        profile=scope['data'].settlement_profiles['profiles']['roadside']
        profile['required_fit_budget']=1
        small=scope['run'](0)
        self.assertFalse(small['accepted']);self.assertIn('budget exhausted; feasibility unresolved',small['message'])
        self.assertEqual((small['published_placements'],small['published_plots']),(0,0))
        profile['required_fit_budget']=256
        scope['data'].structures['market_stall_a']['placement']['buffer']=8
        impossible=scope['run'](0)
        self.assertFalse(impossible['accepted']);self.assertIn('all enumerated alternatives exhausted',impossible['message'])
        self.assertEqual((impossible['published_placements'],impossible['published_plots']),(0,0))

    def test_membership_permutations_preserve_fresh_choices(self):
        _,result=self.probe('probe_selection_list_order.py')
        self.assertTrue(result['required_choices_equal'])
        self.assertEqual(result['results'][0]['placements'],result['results'][1]['placements'])
