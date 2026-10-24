"""Package completed G6 evidence; keep expanded review data in the ignored root.

This archival utility is not a game/test input. Run only after all gate writers
finish. Source fixtures remain in tools; disposable worker saves are not archived.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'evidence/worldgen-g6'


def sha(payload):return hashlib.sha256(payload).hexdigest()


def package(name,folders,expanded):
    destination=OUT/(name+'.zip');inventory=[];excluded=[]
    assert not destination.exists()
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for folder in folders:
            for path in sorted(folder.rglob('*')):
                if not path.is_file():continue
                relative=path.relative_to(OUT)
                if 'saves' in relative.parts or path.suffix in ('.pkl','.lock'):
                    excluded.append(dict(path=relative.as_posix(),bytes=path.stat().st_size,reason='disposable worker save payload'));continue
                payload=path.read_bytes();name_in_archive=relative.as_posix()
                archive.writestr(name_in_archive,payload)
                inventory.append(dict(path=name_in_archive,bytes=len(payload),sha256=sha(payload)))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for row in inventory:
            payload=archive.read(row['path']);assert len(payload)==row['bytes'] and sha(payload)==row['sha256']
    (OUT/(name+'-inventory.json')).write_text(json.dumps(dict(archive=destination.name,bytes=destination.stat().st_size,
        sha256=sha(destination.read_bytes()),members=inventory,excluded=excluded,verified=True),indent=2)+'\n')
    # All moves stay within the explicitly named repository review roots.
    for folder in folders:
        resolved=folder.resolve();assert resolved.is_relative_to(OUT.resolve()) and resolved!=OUT.resolve()
        target=expanded/folder.name;assert target.resolve().is_relative_to((ROOT/'.baseline').resolve())
        assert not target.exists();shutil.move(str(resolved),str(target))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--final',required=True);args=parser.parse_args()
    final=OUT/args.final;release=json.loads((final/'release.json').read_text());assert release['passed']
    sys.path.insert(0,str(ROOT/'tools'));from verify_b3 import source_manifest
    current=source_manifest();assert current==release['source']
    for row in release['results']:
        receipt=json.loads((final/row['gate']/'receipt.json').read_text())
        assert receipt['passed'] and receipt['source']==current and receipt['input_commit']==release['input_commit']
    comparisons=[]
    for path,expected in current.items():
        saved=subprocess.check_output(['git','show',release['input_commit']+':'+path],cwd=ROOT)
        live=(ROOT/path).read_bytes()
        status='byte-identical' if saved==live else 'line-ending-only' if saved.replace(b'\r\n',b'\n')==live.replace(b'\r\n',b'\n') else 'changed'
        assert status!='changed',path
        comparisons.append(dict(path=path,sha256=expected,git_sha256=sha(saved),comparison=status))
    (OUT/'source-reconciliation.json').write_text(json.dumps(dict(tested_input=release['input_commit'],files=comparisons,
        manifest_equal_for_all_final_gates=True),indent=2)+'\n')
    input_zip=Path('C:/Users/dango/Downloads/Resonance_G6_Codex_Brief.zip')
    with zipfile.ZipFile(input_zip) as archive:
        assert archive.testzip() is None;manifest=json.loads(archive.read('MANIFEST.json'))
        for row in manifest['files']:
            payload=archive.read(row['path']);assert len(payload)==row['bytes'] and sha(payload)==row['sha256']
    (OUT/'input-package.json').write_text(json.dumps(dict(path=str(input_zip),bytes=input_zip.stat().st_size,
        sha256=sha(input_zip.read_bytes()),verified_manifest=manifest),indent=2)+'\n')
    views=OUT/'views';views.mkdir(exist_ok=True)
    for source in list((final/'diagnostic/results').glob('*.png'))+list((final/'focused/results').glob('g6-*-production.png')):
        shutil.copyfile(source,views/source.name)
    for source in [final/'diagnostic/results/visuals.json',final/'focused/results/g6-independent-owners.json',final/'focused/results/g6-cohort.json']:
        shutil.copyfile(source,OUT/source.name)
    # Concise report outside archives, omitting large source and worker payloads.
    diagnostic=json.loads((final/'diagnostic/results/run.json').read_text());diagnostic.pop('source',None)
    production_root=Path(json.loads((final/'production/results/latest.json').read_text())['result'])
    production=json.loads(production_root.read_text())
    summary=dict(tested_input=release['input_commit'],final_gates=[dict(gate=r['gate'],**{k:v for k,v in json.loads((final/r['gate']/'receipt.json').read_text()).items() if k in ('passed','exit_code','seconds','source_stable','input_commit')}) for r in release['results']],
        diagnostic=diagnostic,production=dict(passed=production['passed'],totals=production['totals'],coverage=production['coverage'],deferred=production['deferred'],
            valid_workers=sum(w['valid'] for w in production['workers']),runner_negatives=production['runner_negative_controls']),
        browser=json.loads((final/'browser/results/summary.json').read_text()))
    summary['browser'].pop('runtime_source',None);summary['browser'].pop('source',None)
    transform_probe=json.loads((final/'transform-after/result.json').read_text())
    order_probe=json.loads((final/'order-after/result.json').read_text())
    summary['after_selection_probes']=dict(actual_tested_input=release['input_commit'],
        original_embedded_review_sha=transform_probe['source_commit'],
        all_same_seed_transform_cases_accepted=all(r['accepted'] for r in transform_probe['ordinary_rng_order']),
        legal_mirror_witness_accepted=transform_probe['feasible_transform_witness']['accepted'],
        equivalent_memberships_same_required_choices=order_probe['required_choices_equal'],
        note='Original probe bytes and historical narrative are preserved; actual tested source is the frozen command receipt.')
    comparisons=[]
    with zipfile.ZipFile(input_zip) as package_input:
        for row in diagnostic['runs']:
            seed=row['seed'];old_bytes=package_input.read(f'evidence/fixtures/g5_plan_{seed}.json.gz')
            old=json.loads(gzip.decompress(old_bytes));new=json.loads((final/f'diagnostic/results/plan-{seed}.json').read_text())
            compact=lambda value:len(json.dumps(value,separators=(',',':')).encode())
            comparisons.append(dict(seed=seed,g5_fixture_sha256=sha(old_bytes),g5_plan_bytes=compact(old),g6_plan_bytes=compact(new),
                net_growth=compact(new)-compact(old),site_registry_policy_diagnostics_bytes=compact({key:new[key] for key in ('sites','poi_policy','site_selection')}),
                caveat='Net growth also includes changed required-role composition; not an isolated per-site byte cost.'))
    summary['plan_size_comparison']=comparisons
    (OUT/'final-results.json').write_text(json.dumps(summary,indent=2)+'\n')
    expanded=ROOT/'.baseline'/('g6-expanded-'+args.final);expanded.mkdir(parents=True,exist_ok=False)
    assert expanded.resolve().is_relative_to(ROOT.resolve())
    folders=[p for p in OUT.iterdir() if p.is_dir() and p.name not in ('views',args.final)]
    package('development-evidence',folders,expanded)
    package('final-evidence',[final],expanded)
    print(json.dumps(dict(passed=True,expanded=str(expanded),final_commit=release['input_commit'])))


if __name__=='__main__':main()
