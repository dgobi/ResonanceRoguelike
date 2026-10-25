"""Package the committed, published G10 evidence with exact member identities."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[2]


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--publication',type=Path,required=True);a=p.parse_args()
    output=a.output.resolve();publication=json.loads(a.publication.read_text())
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert publication['passed'] and publication['main']==head and publication['verified_commit']==head
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
    sys.path.insert(0,str(ROOT/'tools'))
    from verify_g10 import inputs
    assert inputs()==json.loads((ROOT/'evidence/worldgen-g10/final-b/release.json').read_text())['source']
    index=json.loads((ROOT/'evidence/worldgen-g10/artifact-index.json').read_text());assert index['passed']
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    members={}
    for name in tracked:
        if name.startswith(('evidence/worldgen-g10/','tools/critical_fix_regressions/fixtures/g10/')) or name in (
            'docs/owner/WORLDGEN_G10.md','roguelike/docs/WILDERNESS_TERRAIN.md','roguelike/docs/examples/g10_wilderness_profiles.json','AGENTS.md'):
            if not name:continue
            assert 'saves' not in Path(name).parts
            members[name]=(ROOT/name).read_bytes()
    members['publication.json']=a.publication.read_bytes()
    members['SOURCES.patch']=subprocess.check_output(['git','diff','--binary','f9fe901417b360bc1fda84835e0a793eaac2f6df',head,'--','roguelike','tools','AGENTS.md','README.md'],cwd=ROOT)
    members['README.md']=(f'''# Resonance G10 delivery

Published main and verified checkpoint: {head}
Frozen runtime/test/authoring inputs: {index['frozen_inputs']}

Read docs/owner/WORLDGEN_G10.md and roguelike/docs/WILDERNESS_TERRAIN.md.
The authoritative final gates are evidence/worldgen-g10/final-b/release.json.
final-a was deliberately superseded; its aborted.json explains the arrival fix.
The development directory retains unsuccessful attempts and earlier observations.

All seven completion criteria are indexed in evidence/worldgen-g10/artifact-index.json.
Normal-FOV play captures are separate from explicitly REVEALED production views.
Genuine G9 and actual explored F5 checkpoint ZIPs are intentional compatibility
evidence. Disposable worker saves are omitted and inventoried; no campaigns,
dependencies, personal data, browser profiles or second checkout are bundled.

Use the published repository at the verified commit for reproduction. SOURCES.patch
also carries the scoped binary implementation/test patch against the reviewed G9
commit. The original supplied review and source bindings are retained under before/.
Historical source documents keep their original repository-relative link context.
Runtime paths in receipts are provenance, not required installation locations.
Raw tested hashes and canonical LF/Git blob reconciliation are in final-b/inputs.json.

Run the documented headless commands with the game's dependency environment.
For a fresh-process read of the exact explored checkpoint, run
evidence/worldgen-g10/cold_expedition.py with --expedition pointing to the final-b
g10/expedition directory and --output pointing to a new JSON evidence file.

publication.json verifies remote main and immutable checkpoint readback. MANIFEST.json
inventories every other archive member. The adjacent external archive receipt
records the complete ZIP hash and independent CRC/SHA-256 readback of its members.
The owner wiki remains at its existing separately commissioned edition. G11 is
outside this implementation.
''').encode()
    manifest=dict(version=1,published_commit=head,frozen_inputs=index['frozen_inputs'],
        members=[dict(path=name,bytes=len(raw),sha256=sha(raw),crc32=f'{zlib.crc32(raw)&0xffffffff:08x}') for name,raw in sorted(members.items())])
    members['MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(members.items()):z.writestr(name,raw)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert len(z.infolist())==len(members)
        for row in manifest['members']:
            raw=z.read(row['path']);assert len(raw)==row['bytes'] and sha(raw)==row['sha256'] and f'{zlib.crc32(raw)&0xffffffff:08x}'==row['crc32']
    receipt=dict(passed=True,archive=str(output),bytes=output.stat().st_size,sha256=sha(output.read_bytes()),members=len(members),
        manifest_sha256=sha(members['MANIFEST.json']),all_member_sha256_and_crc32_verified=True,published_commit=head,frozen_inputs=index['frozen_inputs'],publication=publication)
    receipt_path=output.with_suffix('.receipt.json');receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('passed','archive','bytes','sha256','members','published_commit')}))


if __name__=='__main__':main()
