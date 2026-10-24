"""Review-only G7 authoring output probes. Uses disposable drafts, never game edits.

Usage: python probe_output_collisions.py --repo REPO --python INTERPRETER --out OUT
Each run records source/commands, exact before bytes, after hashes and short summaries.
Full after-preview payloads stay in the disposable work directory named in receipt.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--python', required=True)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='g7-output-probes-'))
    rows = []
    names = ('g7_travellers_court.json', 'g7_wayhouse.json', 'g7_poi_example.json')
    for case in ('recipe_report', 'child_report', 'initialization_report', 'derived_svg_hardlink'):
        root = work / case
        root.mkdir()
        for name in names:
            shutil.copyfile(repo / 'roguelike/docs/examples' / name, root / name)
        recipe, child, policy = (root / name for name in names)
        protected = child if case in ('child_report', 'initialization_report') else recipe
        before = {name: (root / name).read_bytes() for name in names}
        case_out = out / case
        case_out.mkdir(exist_ok=True)
        for name, payload in before.items():
            (case_out / name).write_bytes(payload)
        arguments = ['--compound', str(recipe), '--child', str(child), '--assigned-compound', 'S']
        if case == 'initialization_report':
            arguments = ['--init-compound', str(root)]
        output = protected
        if case == 'derived_svg_hardlink':
            output = root / 'review.json'
            (root / 'review.svg').hardlink_to(recipe)
        command = [args.python, '-X', 'utf8', str(repo / 'tools/structure_authoring.py'), *arguments, '--output', str(output)]
        result = subprocess.run(command, cwd=repo, text=True, capture_output=True, timeout=45)
        after = protected.read_bytes()
        summary = {
            'case': case,
            'argv': command,
            'cwd': str(repo),
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'protected_input': str(protected),
            'before_bytes': len(before[protected.name]),
            'after_bytes': len(after),
            'before_sha256': sha(before[protected.name]),
            'after_sha256': sha(after),
            'input_unchanged': before[protected.name] == after,
            'after_prefix': after[:160].decode('utf-8', errors='replace'),
            'all_input_changes': [name for name in names if (root / name).read_bytes() != before[name]],
        }
        (case_out / 'receipt.json').write_text(json.dumps(summary, indent=2) + '\n')
        rows.append(summary)
    report = {
        'reviewed_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
        'reviewed_cli_sha256': sha((repo / 'tools/structure_authoring.py').read_bytes()),
        'work_directory': str(work),
        'cases': rows,
        'scope': 'Disposable draft files only; no repository source edits or personal save access.',
    }
    (out / 'collision-matrix.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'work_directory': str(work), 'cases': [{k: row[k] for k in ('case', 'exit_code', 'input_unchanged', 'before_bytes', 'after_bytes')} for row in rows]}, indent=2))


if __name__ == '__main__':
    main()
