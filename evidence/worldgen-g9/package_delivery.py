"""Build and independently verify the portable G9 review ZIP; no game checkout copy."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[2]
BASE='b94a0b0db3685f7484632701f0486f3b0b79101e'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--publication',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists(),'Use a new archive path; preserve prior deliveries'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    members={}
    for name in names:
        if not name:continue
        if name.startswith(('evidence/worldgen-g9/','Resonance_Wiki_Maintenance/','tools/critical_fix_regressions/fixtures/')) or name in ('docs/owner/WORLDGEN_G9.md','roguelike/docs/COUNTRY_NETWORK.md','roguelike/docs/STRUCTURE_AUTHORING.md','README.md','AGENTS.md'):
            assert '/saves/' not in name and '/__pycache__/' not in name,name
            members[name]=(ROOT/name).read_bytes()
    # A base-relative binary patch is reviewable/reconstructable source without
    # duplicating an entire game/dependency checkout. Exact raw tested identities
    # and any nonreconstructable mixed-newline bytes are in retained receipts.
    members['source/G9-from-reviewed-G8.patch']=subprocess.check_output(['git','diff','--binary',BASE,head,'--','roguelike','tools','layout_painter.html','README.md','AGENTS.md','docs'],cwd=ROOT)
    publication=json.loads(a.publication.read_text());assert publication['main']==head and publication['passed']
    members['publication.json']=a.publication.read_bytes()
    members['README-review.txt']=(f'Resonance G9 portable review\nBase: {BASE}\nDelivery: {head}\n'
        'Start: docs/owner/WORLDGEN_G9.md and evidence/worldgen-g9/index.json.\n'
        'Offline reader: Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html.\n'
        'Source patch applies to the reviewed G8 commit, not to a second bundled checkout.\n'
        'Historical fixture archives are intentional. Personal/disposable saves, interpreter dependencies and browser profiles are excluded.\n'
        'MANIFEST.json inventories every other member, with uncompressed size, SHA256 and CRC32. Its own external archive identity is in the adjacent receipt.\n').encode()
    inventory={n:dict(bytes=len(raw),sha256=sha(raw),crc32=f'{zlib.crc32(raw)&0xffffffff:08x}') for n,raw in sorted(members.items())}
    members['MANIFEST.json']=(json.dumps(dict(schema=1,base_commit=BASE,delivery_commit=head,members=inventory,scope='Every member except this manifest; external ZIP receipt identifies the complete archive.'),indent=2)+'\n').encode()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,raw in sorted(members.items()):z.writestr(n,raw)
    with zipfile.ZipFile(a.output) as z:
        assert z.testzip() is None
        assert sorted(z.namelist())==sorted(members) and len(z.namelist())==len(set(z.namelist()))
        saved=json.loads(z.read('MANIFEST.json'));assert saved['members']==inventory
        for n,v in inventory.items():
            raw=z.read(n);info=z.getinfo(n)
            assert dict(bytes=len(raw),sha256=sha(raw),crc32=f'{info.CRC:08x}')==v
            assert info.file_size==len(raw) and (zlib.crc32(raw)&0xffffffff)==info.CRC
    receipt=dict(passed=True,archive=str(a.output.resolve()),bytes=a.output.stat().st_size,sha256=sha(a.output.read_bytes()),members=len(members),inventory_members=len(inventory),crc_verified=True,delivery_commit=head,base_commit=BASE)
    a.output.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
