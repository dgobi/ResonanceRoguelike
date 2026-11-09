"""Create and read back the finite GUIDE-1 offline handbook release bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from wiki_inputs import check_products


def main():
    root=Path(__file__).resolve().parent;repo=root.parent
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=root/'releases/Resonance_Creators_Handbook_GUIDE-1.zip')
    a=p.parse_args();output=a.output.resolve()
    if output.is_relative_to(repo/'roguelike'):p.error('Release output must be outside game data/saves')
    config=json.loads((root/'wiki-config.json').read_text())
    binding=check_products(root,repo,config,root/'Resonance_Owner_Wiki.html')
    evidence=repo/'evidence/guide-1'
    for path in ('final-practice/practice.json','final-edition/edition.json','workbench/index.json'):
        if not json.loads((evidence/path).read_text(encoding='utf-8')).get('passed'):
            p.error('Required final acceptance receipt is missing or failed: '+path)
    practice=json.loads((evidence/'final-practice/practice.json').read_text(encoding='utf-8'))
    expected={f.relative_to(root/'examples/guide1').as_posix():hashlib.sha256(f.read_bytes()).hexdigest()
              for f in (root/'examples/guide1').rglob('*') if f.is_file() and '__pycache__' not in f.parts}
    if {r['lesson'] for r in practice['runs']}!={f'L{n:02}' for n in range(1,15)}:
        p.error('Final receipt must cover all fourteen lessons')
    for run in practice['runs']:
        if not run['passed'] or run['solution_fingerprints']!=expected or run['source_revision']!=config['commit']:
            p.error('Stale or failed lesson evidence: '+run['lesson'])
    edition=json.loads((evidence/'final-edition/edition.json').read_text(encoding='utf-8'))
    if edition['html_sha256']!=hashlib.sha256((root/'Resonance_Owner_Wiki.html').read_bytes()).hexdigest():
        p.error('Final browser/build evidence is for different HTML bytes')
    if json.loads((evidence/'workbench/index.json').read_text())['source_revision']!=config['commit']:
        p.error('Native Workbench evidence is for a different source revision')
    files={('Resonance_Wiki_Maintenance/'+name):root/name for name in binding['wiki']}
    for name in ('Resonance_Owner_Wiki.html','source-manifest.json','build-report.json','GUIDE_1_PROGRESS.md'):
        files['Resonance_Wiki_Maintenance/'+name]=root/name
    for directory in ('audit','templates'):
        for file in (root/directory).rglob('*'):
            if file.is_file():files['Resonance_Wiki_Maintenance/'+file.relative_to(root).as_posix()]=file
    for directory in ('final-practice','final-edition','workbench'):
        for file in (evidence/directory).rglob('*'):
            if file.is_file():files['evidence/guide-1/'+file.relative_to(evidence).as_posix()]=file
    for name in ('commission.md','acceptance.json','review.md'):
        file=evidence/name
        if file.is_file():files['evidence/guide-1/'+name]=file
    manifest={name:dict(bytes=file.stat().st_size,sha256=hashlib.sha256(file.read_bytes()).hexdigest()) for name,file in sorted(files.items())}
    payload=dict(edition=config['edition'],commission='GUIDE-1',source_revision=config['commit'],files=manifest,
      open='Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html',
      limits='Offline reading is self-contained. Exercises require an existing compatible game checkout and Windows/Python 3.11 dependencies; pass --repo when unpacked elsewhere.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,file in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,9,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,file.read_bytes())
        archive.writestr('BUNDLE-MANIFEST.json',json.dumps(payload,indent=2)+'\n')
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name,record in manifest.items():
            data=archive.read(name)
            assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256']
    receipt=dict(passed=True,files=len(files),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),output=str(output),all_members_read_back=True)
    output.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':main()
