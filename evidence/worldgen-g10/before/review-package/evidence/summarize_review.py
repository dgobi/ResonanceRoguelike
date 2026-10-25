"""Compare fresh G9 review output with retained release results."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def read(path):
    return json.loads(path.read_text())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args();repo=a.repo.resolve();root=a.evidence.resolve()
    fresh=root/'diagnostic/results';old=repo/'evidence/worldgen-g9/final-b/diagnostic/results'
    f,o=read(fresh/'run.json'),read(old/'run.json')
    rows=[]
    for row in f['g9_network']:
        seed=row['seed'];name=f'plan-{seed}.json'
        fb,ob=(fresh/name).read_bytes(),(old/name).read_bytes()
        prev=next(v for v in o['g9_network'] if v['seed']==seed)
        fingerprints={tuple(v['chunk']):v['fingerprint'] for v in row['touched_scenes']}
        oldprints={tuple(v['chunk']):v['fingerprint'] for v in prev['touched_scenes']}
        rows.append(dict(seed=seed,plan_identity=row['plan_identity'],
            plan_sha256=hashlib.sha256(fb).hexdigest(),retained_raw_sha256=hashlib.sha256(ob).hexdigest(),
            raw_plan_equal=fb==ob,newline_normalized_plan_equal=fb.replace(b'\r\n',b'\n')==ob.replace(b'\r\n',b'\n'),
            complete_plan_equal=json.loads(fb)==json.loads(ob),
            complete_baseline_preserved=row['complete_baseline_preserved'],
            scenes_at_plan_completion=row['scenes_at_plan_completion'],
            boundary_continuity=row['boundary_continuity'],
            touched_scene_count=len(fingerprints),touched_fingerprints_equal=fingerprints==oldprints,
            costs=row['costs']))
    fj,oj=f['journey'],o['journey'];fe,oe=fj['explored_checkpoint'],oj['explored_checkpoint']
    receipts={name:read(root/name/'receipt.json') for name in ('g9-tests','diagnostic')}
    before=read(root/'g9-tests/source-before.json')
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=repo).decode().split('\0')
    after={n:hashlib.sha256((repo/n).read_bytes()).hexdigest() for n in paths if n and (repo/n).is_file()}
    status=subprocess.check_output(['git','status','--short'],cwd=repo,text=True)
    result=dict(source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
        receipts=receipts,passed=f['passed'],failures=f['failures'],plans=rows,
        journey=dict(passed=fj['passed'],steps=fj['steps'],boundary_transitions=len(fj['crossings']),
            destination_count=len(fj['destinations']),materialized_surface_scenes_before_f9=fj['materialized_scenes_before_f9'],
            checkpoint_scene_count=fe['scene_count'],checkpoint_bytes=fe['bytes'],
            save_seconds=fe['save_seconds'],cold_load_seconds=fe['cold_load_seconds'],f9_seconds=fe['f9_seconds'],
            worst_boundary_seconds=fj['worst_transition_seconds'],
            f9_restored_explored_checkpoint=fj['f9_restored_explored_checkpoint'],
            explored_surface_fingerprints_equal=fe['surface_fingerprints']==oe['surface_fingerprints'],
            native_controls=fj['fixture'],country=fj['g9_country']),
        source_preservation=dict(tracked_file_count=len(before),source_stable=before==after,
            changed_tracked_paths=sorted(n for n in before.keys()|after.keys() if before.get(n)!=after.get(n)),git_status=status))
    (root/'review-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'] and not result['failures'] and result['source_preservation']['source_stable'] and not status
    assert all(r['complete_plan_equal'] and r['newline_normalized_plan_equal'] and r['touched_fingerprints_equal'] for r in rows)
    assert result['journey']['explored_surface_fingerprints_equal']
    print(json.dumps(dict(plans=[{k:v for k,v in row.items() if k!='costs'} for row in rows],
        journey={k:v for k,v in result['journey'].items() if k not in ('country',)},
        source_preservation=result['source_preservation']),indent=2))


if __name__=='__main__':main()
