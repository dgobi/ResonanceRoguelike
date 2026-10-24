"""CLI preservation checks use only disposable drafts and exact byte comparisons."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
CLI=ROOT/'tools/structure_authoring.py'


class AuthoringDestinations(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='g8-authoring-')
        self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        for name in ('g7_travellers_court.json','g7_wayhouse.json','g7_poi_example.json'):
            shutil.copyfile(ROOT/'roguelike/docs/examples'/name,self.root/name)
        self.recipe=self.root/'g7_travellers_court.json';self.child=self.root/'g7_wayhouse.json'

    def run_cli(self,*args):
        return subprocess.run([sys.executable,'-X','utf8',str(CLI),*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=60)

    def assert_rejected(self,args):
        before={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        result=self.run_cli(*args)
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertIn('conflict',result.stderr.lower())
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()})

    def test_explicit_read_inputs_and_initializer_targets(self):
        for flag in ('--compound','--child','--poi-config','--selection-config','--config','--access','--editor-catalog','candidate'):
            with self.subTest(flag=flag):
                args=[str(self.child)] if flag=='candidate' else [flag,str(self.child)]
                if flag=='--editor-catalog':args+=['--check-editor-catalog']
                self.assert_rejected([*args,'--output',str(self.child)])
        self.assert_rejected(['--init-compound',self.root,'--output',self.child])
        absent=self.root/'new-drafts'
        result=self.run_cli('--init-compound',absent,'--output',absent/'g7_wayhouse.json')
        self.assertNotEqual(result.returncode,0);self.assertFalse(absent.exists())

    def test_aliases_and_all_artifacts_validate_before_mutation(self):
        alias=self.root/'alias.json';os.link(self.recipe,alias)
        self.assert_rejected(['--compound',self.recipe,'--output',alias])
        diagram=self.root/'report.svg';os.link(self.recipe,diagram)
        self.assert_rejected(['--compound',self.recipe,'--child',self.child,'--assigned-compound','S','--output',self.root/'report.json'])
        diagram.unlink()
        # This derived output is known only after a complete scene preview.
        diagram=self.root/'report-0.svg';os.link(self.recipe,diagram)
        self.assert_rejected(['--compound',self.recipe,'--child',self.child,'--assigned-compound','S',
                              '--refresh-editor-catalog','--editor-catalog',self.root/'catalog.js','--output',self.root/'report.json'])
        self.assertFalse((self.root/'catalog.js').exists())

    def test_distinct_outputs_replacement_and_initialization_preservation(self):
        output=self.root/'report.json'
        for _ in range(2):
            result=self.run_cli('--init-compound',self.root,'--output',output)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(len(json.loads(output.read_text())['preserved']),3)
        original=self.child.read_bytes()
        result=self.run_cli('--compound',self.recipe,'--child',self.child,'--assigned-compound','S','--output',output)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.child.read_bytes(),original);self.assertTrue(output.with_suffix('.svg').is_file())
        result=self.run_cli('--refresh-editor-catalog','--editor-catalog',self.root/'catalog.js','--output',output)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.root/'catalog.js').is_file())

    def test_catalog_refresh_cannot_replace_unrelated_read_input(self):
        target=self.root/'catalog.js';target.write_text('edited owner input')
        self.assert_rejected(['--refresh-editor-catalog','--editor-catalog',target,'--access',target])

    def test_installed_hardlink_is_protected(self):
        alias=self.root/'installed.json'
        try:os.link(ROOT/'roguelike/data/generation/settlement_profiles.json',alias)
        except OSError as error:self.skipTest('cross-volume hard link unavailable: '+str(error))
        self.assert_rejected(['--catalog','--output',alias])
