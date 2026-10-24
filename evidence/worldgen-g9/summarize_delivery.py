"""Summarize retained G9 receipts and inventory omissions; does not run game tests."""
import hashlib
import json
from pathlib import Path
import pstats
import subprocess

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/worldgen-g9'


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    release=read(E/'final-b/release.json');assert release['passed'] and release['source_stable']
    gates=[]
    for row in release['results']:
        path=E/'final-b'/row['gate']/'receipt.json';receipt=read(path)
        assert receipt['passed'] and receipt['source_stable'] and receipt['committed_inputs_reconciled']
        assert receipt['input_commit']==release['input_commit'] and not receipt['timeout']
        gates.append(dict(gate=row['gate'],seconds=receipt['seconds'],command=receipt['command'],
                          receipt=path.relative_to(E).as_posix(),sha256=digest(path),passed=True))
    diagnostic=read(E/'final-b/diagnostic/results/run.json');ordinary=[]
    for row in diagnostic['g9_network']:
        seed=row['seed'];plan=read(E/f'final-b/diagnostic/results/plan-{seed}.json');old=read(E/f'final-b/diagnostic/results/baseline-plan-{seed}.json')
        compact=lambda v:len(json.dumps(v,separators=(',',':')).encode())
        ordinary.append(dict(seed=seed,costs=row['costs'],network_seconds=row['network']['seconds'],
             baseline_compact_bytes=compact(old),g9_compact_bytes=compact(plan),network_compact_bytes=compact(plan['network']),
             primary_pairs=plan['network']['primary_pair_count'],pairs_examined=plan['network']['pairs_examined'],pairs_unexamined=plan['network']['pairs_unexamined'],
             expansions=plan['network']['expansions'],outcome=plan['network']['outcome'],added_links=len(plan['network']['accepted']),
             touched_scenes=len(row['touched_scenes']),touched_scene_seconds=sum(x['seconds'] for x in row['touched_scenes']),
             required_scene_count=len(next(x for x in diagnostic['runs'] if x['seed']==seed)['scenes'])))
    production_path=next((E/'final-b/production/results').glob('*/results.json'));production=read(production_path)
    assert production['passed'] and production['only'] is None and production['case'] is None
    summary=dict(schema=1,input_commit=release['input_commit'],passed=True,unified_inputs=len(release['source']),gates=gates,
        focused=dict(tests=229,child_seconds=813.781,clean_parent=read(E/'final-b/focused/results/parent.json')['inherited_pythonpath'] is None),
        browsers=[{k:v for k,v in read(E/f'final-b/browser/results/{name}.json').items() if k in ('browser','version','passed')}|dict(checks=len(read(E/f'final-b/browser/results/{name}.json')['checks'])) for name in ('chromium','firefox')],
        authoring=dict(g9=read(E/'final-b/authoring/results/workflows.json')['g9_top_level_workflows'],g8=read(E/'final-b/authoring/results/inherited-g8/workflows.json')['g8_top_level_workflows'],
                       g7=read(E/'final-b/authoring/results/inherited-g8/inherited-g7/commands.json')['workflow_ids'],
                       inherited_g6='final-b/authoring/results/inherited-g8/inherited-g7/inherited-g6/commands.json',
                       inherited_g5='final-b/authoring/results/inherited-g8/inherited-g7/inherited-g6/g5-recipes/commands.json',scope='Nested levels counted separately; command records are not additional top-level G9 workflows.'),
        production=dict(path=production_path.relative_to(E).as_posix(),totals=production['totals'],deferred=production.get('deferred',[])),ordinary=ordinary,
        journey={k:v for k,v in diagnostic['journey'].items() if k in ('steps','checkpoint_bytes','checkpoint_scene_count','restore_seconds','worst_transition_seconds','g9_country','f9_restored_explored_checkpoint')},
        explored_checkpoint={k:v for k,v in diagnostic['journey']['explored_checkpoint'].items() if k!='surface_fingerprints'},
        preedit_g8_journey={k:v for k,v in diagnostic['preedit_g8_journey'].items() if k in ('steps','checkpoint_bytes','checkpoint_scene_count','restore_seconds','worst_transition_seconds')},
        preedit_g8_checkpoint={k:v for k,v in diagnostic['preedit_g8_journey']['explored_checkpoint'].items() if k!='surface_fingerprints'})
    write(E/'release-summary.json',summary)
    profiles=[]
    wanted={('country_network.py','search'),('country_network.py','augment'),('country_network.py','check_geometry'),('country_network.py','validate_resolved'),('network_metrics.py','distances'),('network_metrics.py','topology'),('world_plan.py','validate_plan'),('world_gen.py','generate_world')}
    for seed in (0,20261023,29417):
        root=E/f'cost-investigation/seed-{seed}';receipt=read(root/'receipt.json');assert receipt['passed'] and receipt['source_stable'] and receipt['committed_inputs_reconciled']
        stats=pstats.Stats(str(root/'profile.pstats'));functions=[]
        for (file,line,function),(primitive,calls,self_time,cumulative,callers) in stats.stats.items():
            if (Path(file).name,function) in wanted:functions.append(dict(file=file.replace('\\','/').split('/roguelike/')[-1],line=line,function=function,calls=calls,self_seconds=self_time,cumulative_seconds=cumulative))
        profiles.append(dict(seed=seed,input_commit=receipt['input_commit'],receipt=f'seed-{seed}/receipt.json',total_profiled_seconds=stats.total_tt,functions=functions))
    write(E/'cost-investigation/summary.json',dict(profiles=profiles,scope='Three serial existing network-preview CLI invocations under Python cProfile after the complete release. Instrumentation adds overhead. Inclusive/cumulative function times overlap and must not be summed. CLI includes planning, validation, graph reporting and image export; use final-b diagnostic for unprofiled planning wall time.',finding='Physical distance evaluation and normal plan validation dominate the instrumented CLI; bounded macro search is a smaller share. This investigates the material planning increase without changing frozen runtime inputs.'))
    files=[]
    for p in sorted(E.rglob('*')):
        if p.is_file() and 'saves' in p.relative_to(E).parts:files.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=digest(p)))
    tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0'))
    assert all(row['path'] not in tracked for row in files)
    write(E/'omitted-disposable-saves.json',dict(schema=1,scope='Only disposable saves under evidence/worldgen-g9; no personal campaign or dependency/profile directories inspected.',files=files,file_count=len(files),bytes=sum(r['bytes'] for r in files),
         omission='Excluded by the task-local .gitignore and archive builder. Absence is not a test result; passing behavior is established by retained raw receipts, explored-scene fingerprints and checkpoint measures.',
         temporary_sessions='Journey and focused TemporaryDirectory sessions were cleaned by their existing harness. Per-file hashes cannot be recaptured after cleanup; their retained results report exact plan/scene fingerprints and checkpoint counts/bytes. Genuine historical checkpoint archives are intentional fixtures and are included.'))
    print(json.dumps(dict(gates=len(gates),production=summary['production']['totals'],ordinary=[{k:r[k] for k in ('seed','baseline_compact_bytes','g9_compact_bytes','network_compact_bytes')} for r in ordinary],omitted_files=len(files),omitted_bytes=sum(r['bytes'] for r in files)),indent=2))


if __name__=='__main__':main()
