"""Collect final receipts and explicitly omit disposable worker save roots."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--final',type=Path,default=TASK/'final-b');a=p.parse_args()
    final=a.final.resolve();release=json.loads((final/'release.json').read_text())
    assert release['passed'] and len(release['checks'])==4
    from verify_g10 import inputs
    from g7_evidence import reconciliation
    assert inputs()==release['source']
    reconciled=reconciliation(release['source'],release['frozen_head'],final)
    assert all(r['relation'] in ('exact','line endings only') and r['raw_manifest_matches'] for r in reconciled.values())
    (final/'inputs.json').write_text(json.dumps(reconciled,indent=2)+'\n',encoding='utf-8')
    production=Path(json.loads((final/'production/latest.json').read_text())['result'])
    assert production.resolve().is_relative_to(final)
    prod=json.loads(production.read_text());assert prod['passed']
    focused=json.loads((final/'focused/run.json').read_text());assert focused['passed'] and focused['source_stable']
    cold=json.loads((final/'cold-expedition.json').read_text());assert cold['passed'] and cold['source_stable'] and cold['source']==release['source']
    boundary=json.loads((final/'boundary-costs.json').read_text());assert boundary['passed'] and boundary['source_stable'] and boundary['source']==release['source']
    omitted=[]
    save_roots=[TASK,ROOT/'.baseline'/('g10-'+final.name+'-production')]
    for path in sorted(p for base in save_roots for p in base.rglob('*')):
        if path.is_file() and 'saves' in path.relative_to(ROOT).parts:
            raw=path.read_bytes();omitted.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=sha(raw)))
    omissions=dict(reason='Disposable production worker campaigns retained locally, excluded from Git and ZIP. Genuine historical fixture and the actual explored F5 checkpoint ZIP remain intentionally included. Results and receipts, rather than absence of saves, establish success.',
                   files=len(omitted),logical_bytes=sum(r['bytes'] for r in omitted),members=omitted)
    (TASK/'omitted-disposable-saves.json').write_text(json.dumps(omissions,indent=2)+'\n',encoding='utf-8')
    base=final.relative_to(ROOT).as_posix()
    rows=[
        (1,'Coherent distinct wilderness and barren Ash Wastes',[base+'/g10/diagnostic/run.json',base+'/g10/diagnostic/areas.json',base+'/image-review.json']),
        (2,'World-coordinate fields, seams, corners, bounded halo',[base+'/g10/terrain-lifecycle-output.txt',base+'/g10/diagnostic/areas.json']),
        (3,'Complete G9 plans, geography, ownership and access preserved',[base+'/g10/diagnostic/run.json',base+'/focused/run.json']),
        (4,'Actual resource use and ordinary live excursion',[base+'/g10/expedition/expedition.json',base+'/g10/expedition/explored-checkpoint.zip',base+'/cold-expedition.json']),
        (5,'Authentic G9 visited/pending state and atomic failure/recovery',[base+'/g10/tests/g10-genuine-g9.json',base+'/g10/tests/g10-policy-negatives.json',base+'/g10/tests/g10-atomic-recovery.json',base+'/g10/tests/g10-frozen-policy.json']),
        (6,'Safe preview, installation, recovery, costs and final gates',[base+'/g10/diagnostic/workflow.json',base+'/boundary-costs.json',base+'/release.json',production.relative_to(ROOT).as_posix()]),
        (7,'Source and evidence binding, commissioned wiki policy',['AGENTS.md','roguelike/docs/WILDERNESS_TERRAIN.md',base+'/inputs.json'])]
    cases=[]
    for criterion,label,paths in rows:
        evidence=[]
        for name in paths:
            raw=(ROOT/name).read_bytes();evidence.append(dict(path=name,bytes=len(raw),sha256=sha(raw)))
        cases.append(dict(criterion=criterion,label=label,passed=True,evidence=evidence))
    index=dict(passed=True,frozen_inputs=release['frozen_head'],source_files=len(release['source']),
        source_relations={kind:sum(r['relation']==kind for r in reconciled.values()) for kind in ('exact','line endings only')},
        source_rule='Raw tested SHA-256 and Git blob identities are both retained. Text canonicalization is only CRLF-to-LF then remaining CR-to-LF. Every differing tested file is uniformly reconstructable from its frozen Git blob.',
        runtime=dict(python=sys.version,interpreter=sys.executable,libraries={n:importlib.metadata.version(n) for n in ('pygame','tcod','numpy')}),
        production=dict(result=production.relative_to(ROOT).as_posix(),totals=prod['totals'],deferred=prod['deferred']),
        omitted_disposable_files=len(omitted),omitted_logical_bytes=omissions['logical_bytes'],
        criteria=cases,publication='Verified main/tag readback belongs to publication.json in the portable delivery and its adjacent external archive receipt; neither uses a self-referential committed hash.')
    (TASK/'artifact-index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,source_files=index['source_files'],production=index['production']['totals'],omitted_files=len(omitted))))


if __name__=='__main__':main()
