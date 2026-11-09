"""Explicitly regenerate the fixed lesson patch after reviewing a solution edit.

Never repins the baseline. Never writes into the game. Run from the repository
root with --repo . and --accept-reviewed-solution after inspecting the diff.
"""
import argparse
import difflib
import json
from pathlib import Path
from patch_guard import HERE, ENGINE, MODULE, SUFFIX, canonical, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--accept-reviewed-solution',action='store_true',required=True)
    a=p.parse_args()
    contract=json.loads((HERE/'patch-baseline.json').read_text())
    original=canonical((a.repo.resolve()/ENGINE).read_bytes())
    if sha(original)!=contract['engine_canonical_sha256']:
        p.error('Baseline changed; inspect the affected source. This command cannot bless a new engine baseline.')
    solution=(HERE/'solutions.py').read_bytes()
    compile(solution,str(HERE/'solutions.py'),'exec')
    engine_diff=''.join(difflib.unified_diff(original.decode().splitlines(True),
        (original+SUFFIX).decode().splitlines(True),fromfile='a/'+ENGINE,tofile='b/'+ENGINE))
    module_diff=''.join(difflib.unified_diff([],solution.decode().splitlines(True),
        fromfile='/dev/null',tofile='b/'+MODULE))
    (HERE/'installation.patch').write_text(engine_diff+module_diff,encoding='utf-8',newline='\n')
    contract['solution_sha256']=sha(solution)
    (HERE/'patch-baseline.json').write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(solution_sha256=sha(solution),patch_sha256=sha((HERE/'installation.patch').read_bytes()),game_files_changed=False)))


if __name__=='__main__':main()
