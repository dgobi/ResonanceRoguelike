"""Verify committed W5M artifact bytes, source binding and exact remote main."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(raw):return hashlib.sha256(raw).hexdigest()
receipt=json.loads(git('show','HEAD:workbench/docs/w5m-verification.json'))
checked=[]
def artifact(row):
    path=row['path'];assert sha(git('show','HEAD:'+path))==row['sha256'],path;checked.append(path)
for key in ('environment','inventory','package_source_inputs','observations','gates','preservation'):artifact(receipt[key])
package_inputs=json.loads(git('show','HEAD:'+receipt['package_source_inputs']['path']))
for path,expected in package_inputs['files'].items():
    assert sha(git('show',package_inputs['revision']+':'+path))==expected['committed_sha256'],path
    assert sha(git('show','HEAD:'+path))==expected['committed_sha256'],path
    assert sha((ROOT/path).read_bytes())==expected['working_sha256'],path
for row in receipt['accepted_fixtures'].values():artifact(row)
observations=json.loads(git('show','HEAD:'+receipt['observations']['path']))
for row in observations['screenshots'].values():artifact(row)
artifact(observations['accepted_satchel_diff'])
for path,expected in receipt['source_hashes'].items():
    assert sha(git('show','HEAD:'+path))==expected['committed_sha256'],path
    assert sha((ROOT/path).read_bytes())==expected['working_sha256'],path
for row in [*receipt['package'].values(),*receipt['runtime'].values()]:assert sha((ROOT/row['path']).read_bytes())==row['sha256']
local=git('rev-parse','HEAD').decode().strip();local_only=sys.argv[1:]==['--local-only']
remote=None if local_only else git('ls-remote','origin','refs/heads/main').decode().split()[0]
if not local_only:assert local==remote,(local,remote)
assert git('branch','--show-current').decode().strip()=='main'
result=dict(passed=True,local_main=local,remote_main=remote,match=None if local_only else True,remote_verification_deferred=local_only,committed_artifacts=len(checked),source_files=len(receipt['source_hashes']),package_source_files=len(package_inputs['files']))
out=ROOT/'workbench/.artifacts/w5m'/('committed-readback.json' if local_only else 'remote-readback.json');out.write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps(result))
