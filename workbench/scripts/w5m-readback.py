"""Verify committed W5M artifact bytes, source binding and exact remote main."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(raw):return hashlib.sha256(raw).hexdigest()
receipt=json.loads(git('show','HEAD:workbench/docs/w5m-verification.json'))
checked=[]
def artifact(row):
    path=row['path'];assert sha(git('show','HEAD:'+path))==row['sha256'],path;checked.append(path)
for key in ('environment','inventory','observations','gates','preservation'):artifact(receipt[key])
for row in receipt['accepted_fixtures'].values():artifact(row)
observations=json.loads(git('show','HEAD:'+receipt['observations']['path']))
for row in observations['screenshots'].values():artifact(row)
for path,expected in receipt['source_hashes'].items():
    assert sha(git('show','HEAD:'+path))==expected['committed_sha256'],path
    assert sha((ROOT/path).read_bytes())==expected['working_sha256'],path
for row in [*receipt['package'].values(),*receipt['runtime'].values()]:assert sha((ROOT/row['path']).read_bytes())==row['sha256']
local=git('rev-parse','HEAD').decode().strip();remote=git('ls-remote','origin','refs/heads/main').decode().split()[0]
assert local==remote,(local,remote);assert git('branch','--show-current').decode().strip()=='main'
result=dict(passed=True,local_main=local,remote_main=remote,match=True,committed_artifacts=len(checked),source_files=len(receipt['source_hashes']))
out=ROOT/'workbench/.artifacts/w5m/remote-readback.json';out.write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps(result))
