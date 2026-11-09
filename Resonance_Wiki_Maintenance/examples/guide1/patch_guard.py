"""Fixed two-file lesson patch, with exact-byte recovery and conflict refusal.

The handbook build never calls this. The practice launcher applies it only to a
newly captured payload. Manual apply/restore is an explicit author action.
"""
from __future__ import annotations
import argparse
import base64
import difflib
import hashlib
import json
import os
import stat
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = 'roguelike/engine/engine.py'
MODULE = 'roguelike/engine/guide1_practice.py'
SUFFIX = b'\n\n# GUIDE-1 opt-in teaching integration; remove with the supplied recovery guard.\nfrom engine.guide1_practice import install as _install_guide1\n_install_guide1()\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(raw):
    return raw.replace(b'\r\n',b'\n').replace(b'\r',b'\n')


def safe_path(path):
    path=Path(os.path.abspath(path))
    for ancestor in (path,*path.parents):
        if ancestor.exists() or ancestor.is_symlink():
            info=ancestor.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                raise ValueError('Linked/reparse patch path refused: '+str(ancestor))
    return path


def check(root):
    root = safe_path(root).resolve()
    for name in (ENGINE,MODULE):
        if not safe_path(root/name).resolve().is_relative_to(root):
            raise ValueError('Patch path escapes chosen root')
    contract = json.loads((HERE/'patch-baseline.json').read_text())
    engine = root/ENGINE
    if not engine.is_file() or sha(canonical(engine.read_bytes())) != contract['engine_canonical_sha256']:
        raise ValueError('GUIDE-1 patch refused: engine.py differs from the reviewed baseline. Preserve it and review/adapt the lesson; no file changed.')
    if (root/MODULE).exists():
        raise ValueError('GUIDE-1 patch refused: the lesson module already exists. Reconcile its recovery manifest; no overwrite.')
    if sha((HERE/'solutions.py').read_bytes()) != contract['solution_sha256']:
        raise ValueError('GUIDE-1 solution changed: review it and regenerate the patch contract before installing.')
    original=canonical(engine.read_bytes()).decode()
    solution=(HERE/'solutions.py').read_text(encoding='utf-8')
    expected=''.join(difflib.unified_diff(original.splitlines(True),(original+SUFFIX.decode()).splitlines(True),fromfile='a/'+ENGINE,tofile='b/'+ENGINE))
    expected+=''.join(difflib.unified_diff([],solution.splitlines(True),fromfile='/dev/null',tofile='b/'+MODULE))
    if canonical((HERE/'installation.patch').read_bytes())!=expected.encode():
        raise ValueError('Installation patch differs from the fixed reviewed changes; no file changed. Review and regenerate it.')
    return root


def apply(root, recovery):
    root = check(root)
    recovery = safe_path(recovery).resolve()
    if recovery.exists():
        raise ValueError('Recovery path already exists; choose a new named directory')
    if recovery.is_relative_to(root/'roguelike'):
        raise ValueError('Recovery must be outside the affected game paths')
    original = (root/ENGINE).read_bytes()
    changes = {ENGINE: canonical(original)+SUFFIX, MODULE:(HERE/'solutions.py').read_bytes()}
    records = {ENGINE:dict(existed=True, original=base64.b64encode(original).decode(), original_sha256=sha(original)),
               MODULE:dict(existed=False, original=None, original_sha256=None)}
    for name, raw in changes.items():
        records[name]['patched_sha256']=sha(raw)
    recovery.mkdir(parents=True)
    manifest = dict(root=str(root), patch_sha256=sha((HERE/'installation.patch').read_bytes()), files=records)
    (recovery/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    written=[]
    try:
        for name,raw in changes.items():
            (root/name).write_bytes(raw);written.append(name)
    except BaseException:
        restore(recovery, paths=written)
        raise
    return manifest


def restore(recovery, paths=None):
    recovery=safe_path(recovery).resolve()
    manifest=json.loads((recovery/'manifest.json').read_text())
    root=safe_path(manifest['root']).resolve()
    records=manifest['files']
    if set(records)!={ENGINE,MODULE}:
        raise ValueError('Unknown recovery paths; no restoration performed')
    chosen=paths if paths is not None else list(records)
    originals={}
    # Preflight every path before changing any. Preserve intervening owner edits.
    for name in chosen:
        path=safe_path(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha(path.read_bytes())!=records[name]['patched_sha256']:
            raise ValueError('Recovery conflict at '+name+'; intervening bytes preserved. Inspect manifest and reconcile manually.')
        if records[name]['existed']:
            raw=base64.b64decode(records[name]['original'],validate=True)
            if sha(raw)!=records[name]['original_sha256']:
                raise ValueError('Corrupt recovery original for '+name+'; no restoration performed')
            originals[name]=raw
    for name in chosen:
        record=records[name];path=root/name
        if record['existed']:
            raw=originals[name]
            path.write_bytes(raw)
            assert path.read_bytes()==raw
        else:
            path.unlink()
            assert not path.exists()
    return dict(restored=chosen,root=str(root))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['check','apply','restore'])
    p.add_argument('--root',type=Path)
    p.add_argument('--recovery',type=Path)
    a=p.parse_args()
    if a.action=='restore':
        if not a.recovery:p.error('--recovery is required')
        result=restore(a.recovery)
    else:
        if not a.root:p.error('--root is required')
        if a.action=='apply' and not a.recovery:p.error('--recovery is required')
        result=apply(a.root,a.recovery) if a.action=='apply' else dict(compatible=str(check(a.root)))
    if a.action=='apply':
        result=dict(applied=list(result['files']),recovery=str(a.recovery.resolve()),patch_sha256=result['patch_sha256'])
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
