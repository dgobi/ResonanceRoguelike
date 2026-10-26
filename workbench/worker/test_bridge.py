"""Process-level W0 contract and production-coordinate regression checks."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "workbench/worker/bridge.py"
ASSET = "roguelike/data/layouts/starting_lab.json"
PYTHON = os.environ.get("RESONANCE_PYTHON", sys.executable)


def invoke(op="identify", root=ROOT, python=PYTHON, raw=None, extra_flags=(), **kwargs):
    request = {"protocol": 4, "id": "test-correlation", "op": op, **kwargs}
    completed = subprocess.run([python, "-I", "-B", *extra_flags, str(BRIDGE), "--root", str(root)],
                               input=raw if raw is not None else json.dumps(request), text=True,
                               capture_output=True, timeout=20, creationflags=0x08000000 if os.name == "nt" else 0)
    if completed.returncode:
        raise AssertionError(completed.stderr)
    response = json.loads(completed.stdout)
    assert response["protocol"] == 4
    if raw is None:
        assert response["id"] == request["id"]
    return response


class BridgeTests(unittest.TestCase):
    def test_current_source_handshake(self):
        response = invoke()
        self.assertTrue(response["ok"], response)
        r = response["result"]
        self.assertEqual(r["contract"], "g2-2")
        self.assertEqual(r["runtime"]["dependencies"]["tcod"], "19.3.0")
        self.assertEqual(len(r["source"]["game_source_sha256"]), 64)
        self.assertIn("layout editing/saving", r["unavailable"])

    def test_catalog_and_shipped_validation(self):
        r = invoke("describe")["result"]
        self.assertIn(ASSET, [a["path"] for a in r["assets"]])
        inspected = invoke("inspect", asset=ASSET)["result"]
        self.assertTrue(inspected["valid"])
        self.assertEqual((inspected["width"], inspected["height"]), (60, 16))
        self.assertEqual(inspected["special_count"], 17)
        self.assertIn("INACTIVE_FIELD", [d["code"] for d in inspected["diagnostics"]])

    def test_invalid_disposable_uses_production_diagnostic(self):
        r = invoke("inspect", asset=ASSET, invalid_fixture=True)["result"]
        self.assertFalse(r["valid"])
        d = next(d for d in r["diagnostics"] if d["code"] == "DIMENSION")
        self.assertEqual(d["field"], "width")
        self.assertIn("61", d["message"])
        self.assertFalse(Path(d["path"]).exists(), "Disposable fixture leaked")

    def test_byte_exact_open_refresh_close_reopen(self):
        source = ROOT / ASSET
        before = source.read_bytes(); stat = source.stat()
        for _ in range(2):
            r = invoke("inspect", asset=ASSET)["result"]
            self.assertEqual(r["sha256"], hashlib.sha256(before).hexdigest())
            self.assertEqual(r["mtime_ns"], str(stat.st_mtime_ns))
        after = source.stat()
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual((stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns), (after.st_size, after.st_mtime_ns, after.st_ctime_ns))

    def test_production_map_coordinates_and_repeatability(self):
        a = invoke("preview", asset=ASSET, seed=20261023)["result"]
        b = invoke("preview", asset=ASSET, seed=20261023)["result"]
        self.assertEqual((a["width"], a["height"]), (80, 43))
        self.assertEqual(len(a["terrain"]), 43)
        self.assertTrue(all(len(row) == 80 for row in a["terrain"]))
        self.assertEqual(a["origin"], [10, 13]); self.assertEqual(a["spawn"], [15, 20])
        self.assertEqual(a["terrain"][20][15], "stairs_up")
        self.assertEqual(a["terrain"][16][67], "door_open")
        self.assertEqual(a["terrain"][0][79], "wall")
        self.assertEqual(a["terrain"][42][0], "wall")
        self.assertTrue(a["passed"])
        self.assertIn((26, 17), [(r["x"], r["y"]) for r in a["containers"]])
        for key in ("terrain_sha256", "terrain", "items", "containers", "actors", "decor", "scene_seed"):
            self.assertEqual(a[key], b[key], key)

    def test_malformed_protocol_and_unsupported_requests(self):
        cases = [("not json", "MALFORMED_REQUEST"), ("[]", "MALFORMED_REQUEST"),
                 ('{"id":"x","protocol":1,"op":"identify"}', "PROTOCOL_MISMATCH"),
                 ('{"id":"x","protocol":4,"op":"execute","code":"bad"}', "MALFORMED_REQUEST"),
                 ('{"id":"x","protocol":true,"op":"identify"}', "PROTOCOL_MISMATCH")]
        for raw, code in cases:
            with self.subTest(raw=raw):
                r = invoke(raw=raw); self.assertFalse(r["ok"]); self.assertEqual(r["error"]["code"], code)

    def test_dependency_absence_structured(self):
        r = invoke(extra_flags=("-S",))
        # Embeddable runtime explicitly lists site-packages even with -S; use
        # the development interpreter for this negative control.
        if "runtime" in str(PYTHON):
            self.skipTest("Run missing-dependency control with the development interpreter")
        self.assertFalse(r["ok"]); self.assertEqual(r["error"]["code"], "MISSING_DEPENDENCY")

    def test_invalid_root_and_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(invoke(root=directory)["error"]["code"], "INVALID_PROJECT")
        for path in ("../secrets.json", "roguelike/data/layouts/../../saves/test.json", "C:/private.json", "roguelike/data/layouts/a\\b.json"):
            r = invoke("inspect", asset=path)
            self.assertFalse(r["ok"])
            self.assertIn(r["error"]["code"], ("PATH_ESCAPE", "UNSUPPORTED_ASSET"))

    def test_readonly_guard_rejects_source_write_and_save_read(self):
        code = '''import importlib.util,pathlib,sys
p=pathlib.Path(__import__('sys').argv[1]); spec=importlib.util.spec_from_file_location('bridge',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
r=pathlib.Path(sys.argv[2]); s=r/'scratch';s.mkdir();(r/'roguelike/saves').mkdir(parents=True);f=r/'roguelike/saves/personal';f.write_text('private')
m.install_guard(r,s)
for action in (lambda: (r/'content.json').write_text('bad'),lambda: f.read_bytes()):
 try: action()
 except PermissionError: pass
 else: raise AssertionError('guard failed')
(s/'allowed').write_text('temporary')
'''
        # All fixture files are created outside the real repository.
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([PYTHON, "-B", "-c", code, str(BRIDGE), directory], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
