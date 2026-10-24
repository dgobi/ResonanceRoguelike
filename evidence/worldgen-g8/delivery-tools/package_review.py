"""Package committed G8 review artifacts and external publication readback."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
import zlib

ROOT=Path.cwd();OUT=ROOT/'evidence/worldgen-g8';BASE='8e56d36d72537e8b32c3666dd5d19723d1afdf3a'
TEXT={'.py','.js','.css','.json','.md','.html','.txt','.hex','.patch','.svg','.gitignore'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--publication',type=Path,required=True);p.add_argument('--zip',type=Path,required=True);a=p.parse_args()
    assert not a.zip.exists(),'immutable review archive already exists';pub=json.loads(a.publication.read_text());assert pub['passed']
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert head==pub['delivered_commit']
    selected={};omitted=[]
    for base in (OUT,ROOT/'Resonance_Wiki_Maintenance'):
        for f in sorted(base.rglob('*')):
            if not f.is_file():continue
            name=f.relative_to(ROOT).as_posix()
            if 'saves' in f.relative_to(base).parts or '__pycache__' in f.parts or f.suffix in ('.pyc','.pyo'):
                omitted.append(dict(path=name,bytes=f.stat().st_size,reason='disposable worker save or generated Python cache'));continue
            selected[name]=f
    changed=subprocess.check_output(['git','diff','--name-only','--diff-filter=ACMR',BASE,head,'--','roguelike','tools','docs','README.md','AGENTS.md','layout_painter.html'],text=True).splitlines()
    for name in changed:
        f=ROOT/name
        if f.is_file():selected[name]=f
    selected['publication.json']=a.publication
    blobs={}
    blobs['REVIEW_README.md']=f'''# Resonance G8 review package

Open `Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html` directly in a browser.
Read `docs/owner/WORLDGEN_G8.md`, then `evidence/worldgen-g8/INDEX.md` and `index.json`.

Delivered commit: `{head}`.
Frozen test inputs: `{pub['frozen_input_commit']}`.
Verified delivery tag: `{pub['verified_tag']}`.
`publication.json` contains actual remote commit/tag readback.

This is a review bundle, not another development checkout. It contains the changed
source files, intentional historical fixtures, editable wiki, standalone HTML and
G8 evidence. Use the published repository for the full source at the stated commit.
Original pre-change outcomes, development failures, controlled examples and final
ordinary runs remain distinctly labeled. Paths inside command receipts identify
their original execution machine; archive paths are portable and relative.

`MANIFEST.json` lists size, SHA-256, canonical-LF text SHA-256 and CRC32 for every
payload member, plus omitted disposable file inventories. The manifest excludes
itself to avoid recursive hashing; the adjacent delivery receipt hashes the whole
ZIP. Binary payloads are exact. `zipfile.testzip()` and independent member hash/CRC
readback validate the completed archive. Personal campaigns, dependencies, browser
profiles and unchanged full source are neither enumerated nor included.
'''.encode()
    entries=[]
    for name in sorted(set(selected)|set(blobs)):
        raw=blobs[name] if name in blobs else selected[name].read_bytes()
        text=Path(name).suffix.lower() in TEXT
        entries.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),canonical_lf_sha256=hashlib.sha256(raw.replace(b'\r\n',b'\n').replace(b'\r',b'\n')).hexdigest() if text else None,crc32=f'{zlib.crc32(raw)&0xffffffff:08x}'))
    manifest=dict(schema=1,delivered_commit=head,reviewed_start=BASE,selected_source='Only changed source files between reviewed start and delivery; complete repository remains at published immutable commit.',text_normalization='Raw bytes retained. Canonical-LF digest normalizes CRLF and CR to LF only; binary files exact.',entries=entries,omitted=omitted,omitted_bytes=sum(v['bytes'] for v in omitted),not_enumerated=['personal campaigns','dependency installations','browser profiles','unchanged full source'],self='MANIFEST.json is excluded from its own hash list; whole archive hash is in adjacent delivery receipt.')
    blobs['MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    a.zip.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.zip,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,f in sorted(selected.items()):z.write(f,name)
        for name,raw in sorted(blobs.items()):z.writestr(name,raw)
    with zipfile.ZipFile(a.zip) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(selected)|set(blobs)
        for row in entries:
            raw=z.read(row['path']);assert hashlib.sha256(raw).hexdigest()==row['sha256'];assert f'{z.getinfo(row["path"]).CRC:08x}'==row['crc32'];assert len(raw)==row['bytes']
    result=dict(passed=True,archive=str(a.zip.resolve()),bytes=a.zip.stat().st_size,sha256=hashlib.sha256(a.zip.read_bytes()).hexdigest(),payload_members=len(entries),archive_members=len(selected)+len(blobs),crc_and_hash_readback=True,omitted_files=len(omitted),omitted_bytes=manifest['omitted_bytes'],publication=pub)
    receipt=a.zip.with_suffix('.delivery.json');receipt.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='publication'},indent=2))


if __name__=='__main__':main()
