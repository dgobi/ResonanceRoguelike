"""Publish only the commissioned main and three immutable G10 checkpoints."""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
TAGS=('checkpoint/worldgen-g10-start-20261024-a',
      'checkpoint/worldgen-g10-terrain-20261024-a',
      'checkpoint/worldgen-g10-verified-20261024-a')


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()


def main():
    p=argparse.ArgumentParser();p.add_argument('--publication',type=Path,required=True);a=p.parse_args()
    assert not a.publication.exists(), 'preserve existing publication evidence'
    assert git('branch','--show-current')=='main' and not git('status','--porcelain')
    remote=git('remote','get-url','origin')
    assert remote=='https://github.com/dgobi/ResonanceRoguelike.git'
    index=json.loads((ROOT/'evidence/worldgen-g10/artifact-index.json').read_text());assert index['passed']
    sys.path.insert(0,str(ROOT/'tools'))
    from verify_g10 import inputs
    release=json.loads((ROOT/'evidence/worldgen-g10/final-b/release.json').read_text())
    assert release['passed'] and inputs()==release['source']
    head=git('rev-parse','HEAD');assert git('rev-parse',TAGS[-1]+'^{}')==head
    command=['git','push','--no-follow-tags','origin','main',*('refs/tags/'+tag for tag in TAGS)]
    result=subprocess.run(command,cwd=ROOT,env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never'),
                          capture_output=True,text=True,timeout=180)
    record=dict(passed=False,remote=remote,main=head,verified_tag=TAGS[-1],verified_commit=head,
        frozen_inputs=index['frozen_inputs'],command=command,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if result.returncode==0:
        refs=['refs/heads/main',*[name for tag in TAGS for name in ('refs/tags/'+tag,'refs/tags/'+tag+'^{}')]]
        read_command=['git','ls-remote','origin',*refs]
        raw=subprocess.check_output(read_command,cwd=ROOT,text=True,timeout=60)
        actual={line.split()[1]:line.split()[0] for line in raw.splitlines()}
        expected={'refs/heads/main':head}
        for tag in TAGS:
            expected['refs/tags/'+tag]=git('rev-parse',tag)
            expected['refs/tags/'+tag+'^{}']=git('rev-parse',tag+'^{}')
        record.update(readback_command=read_command,raw_readback=raw,expected=expected,actual=actual,
                      passed=expected==actual and inputs()==release['source'] and git('rev-parse','HEAD')==head)
    a.publication.parent.mkdir(parents=True,exist_ok=True)
    with a.publication.open('x',encoding='utf-8') as stream:stream.write(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('passed','main','verified_tag','exit_code')}))
    return 0 if record['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
