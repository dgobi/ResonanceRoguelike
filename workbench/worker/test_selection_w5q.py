"""W5Q native source authority, saved references and ordinary consumer bindings."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from test_authoring import data_fixture
from test_bridge import ROOT, invoke
import sys
sys.path.insert(0, str(ROOT/'roguelike'))
from engine import selection_authoring as selection
from generation.context import GenerationError


class Selection(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='w5q-selection-');self.addCleanup(self.tmp.cleanup)
        self.root=data_fixture(self.tmp.name);self.path=self.root/selection.PROFILE
        self.raw=json.loads(self.path.read_text(encoding='utf-8'));self.original=self.path.read_bytes()
    def data(self):
        from engine.data_loader import DataLoader
        with contextlib.redirect_stdout(io.StringIO()):return DataLoader(str(self.root/'roguelike/data'))
    def validate(self,raw):
        result=invoke('validate_draft',root=self.root,asset=selection.PROFILE,source_asset=selection.PROFILE,draft=raw if isinstance(raw,str) else json.dumps(raw))
        self.assertTrue(result['ok'],result);return result['result']
    def test_fixed_registration_and_all_seven_tables_protected_policy(self):
        r=invoke('inspect',root=self.root,asset=selection.PROFILE)['result']
        self.assertTrue(r['editable']);self.assertEqual(r['family']['descriptor']['policy']['identity'],'fixed-file');self.assertNotIn('id',json.loads(r['raw']))
        for profile,roles in selection.TABLES.items():
            for role in roles:
                raw=copy.deepcopy(self.raw);raw['profiles'][profile]['roles'][role][0]['weight']=2.5
                self.assertTrue(self.validate(raw)['valid'],(profile,role))
        for pointer,value in [(('version',),2),(('id',),'forged'),(('profiles','grid','roles','civic',0,'weight'),2),(('profiles','grid','minimum','civic'),0),(('profiles','roadside','repeat_multiplier'),0.3),(('profiles','landmark','required_fit_budget'),1)]:
            raw=copy.deepcopy(self.raw);parent=raw
            for k in pointer[:-1]:parent=parent[k]
            parent[pointer[-1]]=value
            self.assertFalse(self.validate(raw)['valid'],pointer)
        self.assertEqual(self.path.read_bytes(),self.original)
    def test_original_authority_unsupported_shapes_versions_paths_and_bom(self):
        for original in ({**self.raw,'version':2},{**self.raw,'id':'fake'},[self.raw],{**self.raw,'profiles':{}}):
            self.path.write_text(json.dumps(original),encoding='utf-8')
            inspected=invoke('inspect',root=self.root,asset=selection.PROFILE)['result'];self.assertFalse(inspected['editable'])
            self.assertFalse(self.validate(self.raw)['valid'])
        self.path.write_bytes(self.original)
        r=self.validate('\ufeff'+self.original.decode('utf-8'));self.assertFalse(r['valid']);self.assertIn('SELECTION_JSON',[d['code'] for d in r['diagnostics']])
        for alias in ('roguelike/data/generation/Settlement_profiles.json','roguelike/data/generation/nested/settlement_profiles.json','roguelike/data/generation/../settlement_profiles.json'):
            self.assertFalse(invoke('inspect',root=self.root,asset=alias)['ok'])
        r=invoke('validate_draft',root=self.root,asset='roguelike/data/generation/authored_submap_selection.json',source_asset=selection.PROFILE,draft=json.dumps(self.raw));self.assertFalse(r['ok'])
        self.path.write_bytes(b'\xef\xbb\xbf'+self.original)
        r=invoke('inspect',root=self.root,asset=selection.PROFILE)['result'];self.assertFalse(r['editable']);self.assertIn('BOM',r['diagnostics'][0]['message']);self.assertEqual(r['raw'].encode('utf-8'),b'\xef\xbb\xbf'+self.original)
        self.assertTrue(invoke('identify',root=self.root)['ok']);self.assertTrue(invoke('describe',root=self.root)['ok'])
    def test_invalid_editable_values_repair_and_exact_malformed_draft_diagnostics(self):
        broken=copy.deepcopy(self.raw);broken['profiles']['grid']['roles']['residential'][0]['weight']=0
        self.path.write_text(json.dumps(broken),encoding='utf-8')
        r=invoke('inspect',root=self.root,asset=selection.PROFILE)['result'];self.assertTrue(r['editable']);self.assertFalse(r['valid'])
        self.assertTrue(self.validate(self.raw)['valid'])
        r=self.validate('{"profiles":"exact λ\\n",');self.assertFalse(r['valid']);self.assertFalse(r['syntax_valid'])
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8')),broken)
    def test_actual_native_value_duplicate_scope_caps_minima_context_and_unique_references(self):
        for field,bad in [('weight',0),('weight',1001),('weight',True),('weight','1'),('max_per_settlement',True),('max_per_settlement',0),('max_per_settlement',129),('max_per_settlement',1.5)]:
            raw=copy.deepcopy(self.raw);raw['profiles']['grid']['roles']['residential'][0][field]=bad
            r=self.validate(raw);self.assertFalse(r['valid']);self.assertIn(field,r['diagnostics'][0]['field'])
        raw=copy.deepcopy(self.raw);raw['profiles']['grid']['roles']['support'].append(copy.deepcopy(raw['profiles']['grid']['roles']['residential'][0]));r=self.validate(raw);self.assertFalse(r['valid']);self.assertIn('duplicate',r['diagnostics'][0]['message'])
        # The existing same ID in grid and roadside is legal. Zero-minimum pools stay nonempty.
        self.assertTrue(self.validate(self.raw)['valid'])
        raw=copy.deepcopy(self.raw);raw['profiles']['grid']['roles']['support']=[];self.assertFalse(self.validate(raw)['valid'])
        data=self.data();raw=copy.deepcopy(self.raw)
        data.structures['house_small_a']['placement']['contexts']=['landmark']
        self.assertIn('grid',selection.authoring_validate(raw,data,selection.PROFILE,data.root)[0]['message'])
        data=self.data();data.structures['house_small_a']['placement']['road_relation']='remote'
        self.assertIn('remote',selection.authoring_validate(raw,data,selection.PROFILE,data.root)[0]['message'])
        duplicate=self.root/'roguelike/data/buildings/storage/duplicate.json';building=json.loads((self.root/'roguelike/data/buildings/residential/house_small_a.json').read_text(encoding='utf-8'));duplicate.write_text(json.dumps({**building,'id':'HOUSE_SMALL_A'}),encoding='utf-8')
        self.assertTrue(any(d['code']=='BUILDING_SOURCE' for d in self.validate(self.raw)['diagnostics']))
        duplicate.unlink()
        # Saved consumer eligibility does not grant or require definition editing.
        original=self.root/'roguelike/data/buildings/residential/house_small_a.json'
        renamed=original.with_name('retained_filename.json');original.rename(renamed)
        from engine.building_authoring import capability
        self.assertFalse(capability(building,'roguelike/data/buildings/residential/retained_filename.json')['editable'])
        reference=next(b for b in selection.saved_buildings(self.data(),self.root/'roguelike/data') if b['id']=='house_small_a')
        self.assertTrue(reference['resolved']);self.assertIn('grid',reference['eligible_profiles']);self.assertTrue(self.validate(self.raw)['valid'])
        from generation.settlement_selection import validate
        caps=copy.deepcopy(self.raw);caps['profiles']['grid']['minimum']['residential']=8
        for row in caps['profiles']['grid']['roles']['residential']:row['max_per_settlement']=1
        with self.assertRaisesRegex(GenerationError,'minimum exceeds hard caps'):validate(caps,self.data())
    def test_ordinary_saved_sample_selected_building_landmark_construction_freshness_and_removal(self):
        from generation.selection_preview import preview
        from generation.settlement_selection import resolve
        # Exact accepted W5P fixture, saved in disposable data; retain all competitors.
        building=(ROOT/'workbench/docs/evidence/w5p/fixtures/building_v2.json').read_bytes()
        target=self.root/'roguelike/data/buildings/residential/w5p_lodge.json';target.write_bytes(building)
        self.raw['profiles']['grid']['roles']['residential'].append(dict(asset='w5p_lodge',weight=5,max_per_settlement=3))
        self.path.write_text(json.dumps(self.raw),encoding='utf-8')
        def sample(inputs):
            with contextlib.redirect_stdout(io.StringIO()):return preview(self.root,json.loads(self.path.read_text(encoding='utf-8')),inputs)
        first=sample({'seed':20261029});self.assertTrue(first['selection_matches_saved_resolve']);self.assertEqual(first['captured_selection'],resolve(self.data()))
        selected=[r for r in first['rows'] if r['asset']=='w5p_lodge'];self.assertTrue(selected)
        for p in [selected[0],next(r for r in first['rows'] if r['profile']=='landmark')]:
            inputs=dict(seed=first['seed'],placement_id=p['id'],plan_identity=first['plan_identity'],input_identity=first['input_identity'])
            scene=sample(inputs)['scene'];self.assertEqual(scene['placement']['id'],p['id']);self.assertTrue(scene['passed']);self.assertTrue(all(r['receipt_owned'] for r in scene['records']));self.assertTrue(all(r['record_id'].startswith(p['id']+':') for r in scene['records']))
            if p['asset']=='w5p_lodge':
                self.assertTrue(any(r.get('declared_text_id') and r['objects'][0].get('text_id') for r in scene['records']))
                self.assertTrue(any(r['kind']=='container' and r['objects'][0]['items'] for r in scene['records']))
            with self.assertRaisesRegex(GenerationError,'plan'):sample({**inputs,'plan_identity':'0'*64})
            with self.assertRaisesRegex(GenerationError,'Placement'):sample({**inputs,'placement_id':'invented'})
        unsaved=copy.deepcopy(self.raw);unsaved['profiles']['grid']['roles']['residential'][-1]['weight']=6
        with self.assertRaisesRegex(GenerationError,'saved selection'):
            with contextlib.redirect_stdout(io.StringIO()):preview(self.root,unsaved,{'seed':20261029})
        self.raw['profiles']['grid']['roles']['residential'].pop();self.path.write_text(json.dumps(self.raw),encoding='utf-8')
        with self.assertRaisesRegex(GenerationError,'Stale saved inputs'):sample(inputs)
        removed=sample({'seed':20261029});self.assertFalse(any(r['asset']=='w5p_lodge' for r in removed['rows']));self.assertNotEqual(first['plan_identity'],removed['plan_identity']);self.assertEqual(target.read_bytes(),building)
        # Valid, eligible membership honestly selects zero at this same seed.
        self.raw['profiles']['grid']['roles']['residential'].append(dict(asset='w5p_lodge',weight=1e-100,max_per_settlement=1));self.path.write_text(json.dumps(self.raw),encoding='utf-8')
        absent=sample({'seed':20261029});self.assertEqual(next(r['selected'] for r in absent['summary'] if r['asset']=='w5p_lodge'),0)


if __name__=='__main__':unittest.main()
