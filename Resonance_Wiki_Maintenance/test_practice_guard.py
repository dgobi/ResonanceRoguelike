"""Exercise exact recovery and fail-closed boundaries on disposable two-file roots."""
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent/'examples/guide1'))
from patch_guard import ENGINE,MODULE,apply,check,restore


class Recovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='guide-guard-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.root=self.base/'payload';p=self.root/ENGINE;p.parent.mkdir(parents=True)
        self.original=(Path(__file__).resolve().parent.parent/ENGINE).read_bytes()
        p.write_bytes(self.original);self.recovery=self.base/'recovery'

    def test_exact_restore_and_new_path_absence(self):
        check(self.root);apply(self.root,self.recovery)
        self.assertTrue((self.root/MODULE).is_file())
        manifest=json.loads((self.recovery/'manifest.json').read_text())
        self.assertEqual(base64.b64decode(manifest['files'][ENGINE]['original']),self.original)
        restore(self.recovery)
        self.assertEqual((self.root/ENGINE).read_bytes(),self.original)
        self.assertFalse((self.root/MODULE).exists())

    def test_incompatible_source_changes_nothing(self):
        changed=self.original+b'\n# owner change\n';(self.root/ENGINE).write_bytes(changed)
        with self.assertRaisesRegex(ValueError,'differs'):apply(self.root,self.recovery)
        self.assertEqual((self.root/ENGINE).read_bytes(),changed)
        self.assertFalse(self.recovery.exists());self.assertFalse((self.root/MODULE).exists())

    def test_conflict_preserves_every_path(self):
        apply(self.root,self.recovery);module=(self.root/MODULE).read_bytes()
        changed=(self.root/ENGINE).read_bytes()+b'\n# intervening work\n';(self.root/ENGINE).write_bytes(changed)
        with self.assertRaisesRegex(ValueError,'conflict'):restore(self.recovery)
        self.assertEqual((self.root/ENGINE).read_bytes(),changed)
        self.assertEqual((self.root/MODULE).read_bytes(),module)

    def test_corrupt_backup_preflight_changes_nothing(self):
        apply(self.root,self.recovery);before={name:(self.root/name).read_bytes() for name in (ENGINE,MODULE)}
        file=self.recovery/'manifest.json';m=json.loads(file.read_text());m['files'][ENGINE]['original_sha256']='0'*64;file.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'Corrupt'):restore(self.recovery)
        self.assertEqual(before,{name:(self.root/name).read_bytes() for name in before})

    def test_redirected_ancestor_refused(self):
        external=self.base/'outside';external.mkdir();(external/'engine.py').write_bytes(self.original)
        linked=self.base/'linked/roguelike';linked.mkdir(parents=True)
        result=subprocess.run(['powershell','-NoProfile','-Command',
          'New-Item -ItemType Junction -Path $args[0] -Target $args[1] | Out-Null',str(linked/'engine'),str(external)],capture_output=True)
        # Use a direct argument-safe PowerShell literal if its -Command parser
        # treats the following argv as source rather than $args on this host.
        if result.returncode:
            cmd="New-Item -ItemType Junction -Path '"+str(linked/'engine').replace("'","''")+"' -Target '"+str(external).replace("'","''")+"' | Out-Null"
            result=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True)
        if result.returncode:self.skipTest('Directory junction unavailable on this host')
        try:
            with self.assertRaisesRegex(ValueError,'reparse'):check(linked.parent)
            self.assertEqual((external/'engine.py').read_bytes(),self.original)
        finally:
            # Remove only the junction, not its target contents.
            (linked/'engine').rmdir()


if __name__=='__main__':unittest.main()
