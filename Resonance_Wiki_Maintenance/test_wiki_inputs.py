"""Tiny documentation-only repositories exercise real revision transitions."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from wiki_inputs import reviewed_inputs,bind_products,check_products


class WikiInputs(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='wiki-contract-');self.addCleanup(temp.cleanup)
        self.repo=Path(temp.name);self.root=self.repo/'wiki';self.root.mkdir()
        self.git('init','-q')
        (self.repo/'guide.md').write_text('Reviewed authoritative guide.\n')
        self.git('add','guide.md');self.commit('review source')
        self.config=dict(commit=self.git('rev-parse','HEAD').strip(),source_scope=['guide.md','inputs/'],chapters=[dict(file='chapters/guide.md')],reviewed_evidence='evidence.json')
        for name in ('wiki-config.json','wiki_inputs.py','build_wiki.py','validate_wiki.py','theme.css','reader.js','requirements-docs.txt','README.txt','verify_reader.py','verify_edition.py','test_wiki_inputs.py','evidence.json','chapters/guide.md'):
            p=self.root/name;p.parent.mkdir(exist_ok=True);p.write_text('wiki authoring input '+name)
        self.output=self.root/'Resonance_Owner_Wiki.html';self.output.write_text('<html>Reviewed fixture</html>')
        self.bind()

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.repo),*args],text=True,stderr=subprocess.DEVNULL)

    def commit(self,message):self.git('-c','user.name=Wiki Test','-c','user.email=wiki-test@example.invalid','commit','-qm',message)
    def bind(self):return bind_products(self.root,self.repo,self.config,reviewed_inputs(self.repo,self.config),self.output)
    def check(self):return check_products(self.root,self.repo,self.config,self.output)

    def test_repeat_and_later_documentation_delivery_commit(self):
        first=self.bind();self.check();self.assertEqual(first,self.bind());self.check()
        self.git('add','wiki');self.commit('deliver documentation products')
        self.check();self.assertNotEqual(self.git('rev-parse','HEAD').strip(),self.config['commit'])
        self.bind();self.check()

    def test_unreviewed_changed_missing_and_added_sources_cannot_be_rebuilt(self):
        source=self.repo/'guide.md';original=source.read_bytes()
        for action in ('changed','missing','added'):
            with self.subTest(action=action):
                if action=='changed':source.write_text('unreviewed change')
                elif action=='missing':source.unlink()
                else:
                    (self.repo/'inputs').mkdir();(self.repo/'inputs/new.md').write_text('new relevant input')
                for operation in (self.check,self.bind):
                    with self.assertRaisesRegex(ValueError,'unreviewed source mismatch'):operation()
                source.write_bytes(original)

    def test_stale_missing_wiki_and_product(self):
        guide=self.root/'chapters/guide.md';original=guide.read_bytes()
        guide.write_text('new chapter')
        with self.assertRaisesRegex(ValueError,'wiki authoring'):self.check()
        guide.unlink()
        with self.assertRaisesRegex(ValueError,'missing wiki'):self.check()
        guide.write_bytes(original);self.check()
        self.output.write_text('stale output')
        with self.assertRaisesRegex(ValueError,'stale HTML'):self.check()
        self.output.unlink()
        with self.assertRaisesRegex(ValueError,'HTML'):self.check()

    def test_newline_equivalence_preserves_capture_for_source_and_authoring(self):
        source=self.repo/'guide.md';wiki=self.root/'chapters/guide.md'
        source.write_bytes(b'alpha\nbeta\ngamma\n');self.git('add','guide.md');self.commit('review newline fixture')
        self.config['commit']=self.git('rev-parse','HEAD').strip();wiki.write_bytes(source.read_bytes())
        captured=self.bind()
        for raw in (b'alpha\nbeta\ngamma\n',b'alpha\r\nbeta\r\ngamma\r\n',b'alpha\r\nbeta\ngamma\r'):
            source.write_bytes(raw);wiki.write_bytes(raw)
            self.assertEqual(self.check(),captured)
            self.assertEqual(source.read_bytes(),raw);self.assertEqual(wiki.read_bytes(),raw)

    def test_binary_exact_bom_trailing_newline_and_complete_helper_membership(self):
        folder=self.repo/'inputs';folder.mkdir();binary=folder/'image.bin';binary.write_bytes(b'\x00a\r\nb')
        self.git('add','inputs');self.commit('review binary');self.config['commit']=self.git('rev-parse','HEAD').strip();self.bind()
        binary.write_bytes(b'\x00a\nb')
        with self.assertRaisesRegex(ValueError,'unreviewed source'):self.check()
        binary.write_bytes(b'\x00a\r\nb');self.check()
        source=self.repo/'guide.md';original=source.read_bytes()
        for value in (b'\xef\xbb\xbf'+original,original.rstrip(b'\r\n')):
            source.write_bytes(value)
            with self.assertRaisesRegex(ValueError,'unreviewed source'):self.check()
        source.write_bytes(original)
        helper=self.root/'test_wiki_inputs.py';original=helper.read_bytes();helper.write_bytes(original+b'changed')
        with self.assertRaisesRegex(ValueError,'wiki authoring'):self.check()
        helper.write_bytes(original);self.check();helper.unlink()
        with self.assertRaisesRegex(ValueError,'missing wiki'):self.check()
        helper.write_bytes(original);self.check()
        extra=self.root/'new_verification_helper.py';extra.write_text('new helper')
        with self.assertRaisesRegex(ValueError,'wiki authoring'):self.check()
        extra.unlink();self.check()


if __name__=='__main__':unittest.main()
