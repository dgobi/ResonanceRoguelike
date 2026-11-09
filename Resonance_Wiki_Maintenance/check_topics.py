"""Report source drift and potentially affected handbook topics. Never writes."""
import argparse
import json
from pathlib import Path
import subprocess
from wiki_inputs import included


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parent
    mapping=json.loads((root/'source-map.json').read_text())
    def git(*args):return subprocess.check_output(['git','-C',str(a.repo.resolve()),*args]).decode('utf-8').splitlines()
    # Compare reviewed revision with current index+working bytes; include additions.
    changed=set(git('diff','--name-only',mapping['reviewed_revision'],'--'))
    changed.update(git('ls-files','--others','--exclude-standard'))
    rows=[]
    for topic in mapping['topics']:
        hits=sorted(name for name in changed if included(name,topic['paths']))
        if hits:rows.append(dict(pages=topic['pages'],changed=hits,checks=topic['checks']))
    print(json.dumps(dict(reviewed_revision=mapping['reviewed_revision'],potentially_affected=rows,
        note='Impact hints only. No files changed and no new revision approved.'),indent=2))
    return 1 if rows else 0


if __name__=='__main__':raise SystemExit(main())
