"""Archive completed G7 review artifacts; never a game or release-gate input."""
import argparse
from collections import Counter
import hashlib
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'evidence/worldgen-g7'


def sha(blob):return hashlib.sha256(blob).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def package(name,folders,expanded):
    destination=OUT/(name+'.zip');members=[];excluded=[]
    assert not destination.exists()
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for folder in folders:
            assert folder.resolve().is_relative_to(OUT.resolve()) and folder.resolve()!=OUT.resolve()
            for path in sorted(folder.rglob('*')):
                if not path.is_file():continue
                relative=path.relative_to(OUT).as_posix()
                if 'saves' in path.relative_to(OUT).parts or path.suffix in ('.pkl','.lock'):
                    excluded.append(dict(path=relative,bytes=path.stat().st_size,reason='disposable worker save payload; not retained or byte-verified in archive'))
                    continue
                payload=path.read_bytes();archive.writestr(relative,payload)
                members.append(dict(path=relative,bytes=len(payload),sha256=sha(payload)))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for row in members:
            payload=archive.read(row['path']);assert len(payload)==row['bytes'] and sha(payload)==row['sha256']
    write(OUT/(name+'-inventory.json'),dict(archive=destination.name,bytes=destination.stat().st_size,sha256=sha(destination.read_bytes()),members=members,excluded=excluded,verified=True))
    for folder in folders:
        target=expanded/folder.relative_to(OUT)
        assert target.resolve().is_relative_to((ROOT/'.baseline').resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(folder),str(target))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--final',required=True);args=parser.parse_args()
    final=OUT/args.final;release=read(final/'release.json');assert release['passed']
    sys.path.insert(0,str(ROOT/'tools'))
    from verify_b3 import source_manifest
    from g7_evidence import reconciliation
    current=source_manifest();assert current==release['source']
    comparisons=reconciliation(current,release['input_commit'],OUT/'source-raw')
    assert all(v['raw_manifest_matches'] and v['relation'] in ('exact','line endings only') for v in comparisons.values())
    receipts=[]
    for row in release['results']:
        receipt=read(final/row['gate']/'receipt.json')
        assert receipt['passed'] and receipt['committed_inputs_reconciled'] and receipt['source']==current and receipt['input_commit']==release['input_commit']
        receipts.append(dict(gate=row['gate'],**{k:receipt[k] for k in ('passed','exit_code','seconds','source_stable','input_commit','committed_inputs_reconciled')}))
    write(OUT/'source-reconciliation.json',dict(tested_input=release['input_commit'],delivery_reference='checkpoint/worldgen-g7-verified-20261024-a',canonical_rule='CRLF to LF, then remaining CR to LF; no other normalization; binary exact',manifest_equal_for_all_final_gates=True,counts=dict(Counter(v['relation'] for v in comparisons.values())),files=comparisons))
    views=OUT/'views';views.mkdir(exist_ok=True)
    for source in list((final/'diagnostic/results').glob('*.png'))+list((final/'focused/results').glob('g7-*-production.png'))+list((final/'browser/results').glob('*compound-editor.png')):
        shutil.copyfile(source,views/source.name)
    for name in ('g7-independent-children.json','g7-authentic-g6-restore.json','g7-native-views.json','g7-late-child-rollback.json'):
        shutil.copyfile(final/'focused/results'/name,OUT/name)
    diagnostic=read(final/'diagnostic/results/run.json');diagnostic.pop('source',None)
    production=read(Path(read(final/'production/results/latest.json')['result']))
    browser=read(final/'browser/results/summary.json');browser.pop('source',None);browser.pop('runtime_source',None)
    focused=(final/'focused/results/focused-tests.txt').read_text(encoding='utf-8')
    authoring=read(final/'authoring/results/commands.json')
    commands=[r for r in authoring['records'] if 'argv' in r]
    summary=dict(tested_input=release['input_commit'],final_gates=receipts,focused_summary=focused[focused.rfind('\nRan '):].strip(),diagnostic=diagnostic,browser=browser,
        authoring=dict(passed=authoring['passed'],workflows=authoring['workflow_ids'],commands=len(commands),expected_negatives=sum(r['expected_negative'] for r in commands),nested_g6='separate records in final archive; outer command count includes wrapper once'),
        production=dict(passed=production['passed'],totals=production['totals'],coverage=production['coverage'],deferred=production['deferred'],valid_workers=sum(w['valid'] for w in production['workers']),runner_negatives=production['runner_negative_controls']))
    compact=lambda value:len(json.dumps(value,separators=(',',':')).encode())
    components=[]
    for run in diagnostic['runs']:
        plan=read(final/f'diagnostic/results/plan-{run["seed"]}.json')
        parents={s['id'] for s in plan['sites'] if s['kind']=='compound'}
        values=dict(parent_registry=plan['sites'],shared_paths=plan['paths'],child_placements=[p for p in plan['placements'] if p.get('parent') in parents],
                    child_plots=[p for p in plan['plots'] if p['owner'] in parents],compound_reservations=[r for r in plan['reservations'] if r['owner'] in parents or r.get('container') in parents],policy=plan['poi_policy'],selection=plan['site_selection'])
        components.append(dict(seed=run['seed'],compact_subtree_bytes={k:compact(v) for k,v in values.items()},note='Named persisted subtree sizes; not an attribution of all whole-plan growth. Other nodes, dependencies and outer JSON syntax remain outside these subtrees.'))
    old=json.loads(gzip.decompress((ROOT/'tools/critical_fix_regressions/fixtures/g7/g6_plan_20261023.json.gz').read_bytes()))
    new=read(final/'diagnostic/results/plan-20261023.json')
    summary['plan_component_bytes']=components
    summary['g6_plan_comparison']=dict(seed=20261023,authentic_g6_bytes=compact(old),g7_bytes=compact(new),net_growth=compact(new)-compact(old),note='Actual captured G6 plan; composition also changed. No timing-regression or isolated per-compound growth claim.')
    write(OUT/'final-results.json',summary)
    supplied=Path('C:/Users/dango/Downloads/Resonance_G7_Codex_Brief.zip')
    with zipfile.ZipFile(supplied) as archive:
        assert archive.testzip() is None
        manifest=json.loads(archive.read('MANIFEST.json'))
        for row in manifest['members']:
            payload=archive.read(row['path']);assert len(payload)==row['bytes'] and sha(payload)==row['sha256']
    write(OUT/'input-package.json',dict(path=str(supplied),bytes=supplied.stat().st_size,sha256=sha(supplied.read_bytes()),verified_manifest=manifest))
    expanded=ROOT/'.baseline'/('g7-expanded-'+args.final);expanded.mkdir(parents=True,exist_ok=False)
    package('development-evidence',[OUT/'development'],expanded)
    package('final-evidence',[final],expanded)
    # Opening provenance and authentic fixture stay in place. Only disposable
    # untracked campaign payloads move into the explicitly named review root.
    excluded=[]
    for folder in (OUT/'before/capture/saves',OUT/'before/synthetic-outside-allowed'):
        assert folder.resolve().is_relative_to(OUT.resolve()) and folder.resolve()!=OUT.resolve()
        for path in sorted(folder.rglob('*')):
            if path.is_file():excluded.append(dict(path=path.relative_to(OUT).as_posix(),bytes=path.stat().st_size,reason='disposable opening capture/guard runtime file; authentic checkpoint retained separately in source fixture'))
        target=expanded/folder.relative_to(OUT);assert target.resolve().is_relative_to((ROOT/'.baseline').resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(folder),str(target))
    write(OUT/'opening-disposable-omissions.json',dict(scope='Only disposable runtime files; original capture receipt and authentic source fixture remain retained',files=excluded))
    assert source_manifest()==current
    print(json.dumps(dict(passed=True,expanded=str(expanded),input_commit=release['input_commit'])))


if __name__=='__main__':main()
