"""Verify published evidence from Git bytes; optionally require remote main match."""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8').strip()
def blob(path):return subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)
receipt=json.loads(blob('workbench/docs/w5k-verification.json'))
checked={}
def walk(value):
    if isinstance(value,dict):
        if isinstance(value.get('path'),str) and value['path'].startswith('workbench/docs/evidence/w5k/') and 'sha256' in value:
            path=value['path'];actual=hashlib.sha256(blob(path)).hexdigest();assert actual==value['sha256'],path;checked[path]=actual
        for child in value.values():walk(child)
    elif isinstance(value,list):
        for child in value:walk(child)
walk(receipt)
observations=json.loads(blob(receipt['observations']['path']));walk(observations)
for path,row in receipt['source_hashes'].items():assert hashlib.sha256(blob(path)).hexdigest()==row['committed_sha256'],path
for row in receipt['w5j_portable_readback'].values():
    data=blob(row['path']);assert hashlib.sha256(data).hexdigest()==row['sha256']
    assert hashlib.sha256(data.replace(b'\n',b'\r\n')).hexdigest()==row['original_working_crlf_sha256']
local=git('rev-parse','HEAD');remote=None
if '--remote' in sys.argv:
    remote=git('ls-remote','origin','refs/heads/main').split()[0];assert local==remote,(local,remote)
result=dict(passed=True,local_main=local,remote_main=remote,match=local==remote if remote else None,
    accessible_artifacts_checked=len(checked),source_files_checked=len(receipt['source_hashes']),
    evidence_identity='Committed Git bytes; LF reports and exact -text accepted fixtures',owner_plan_untracked='RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md' in git('ls-files','--others','--exclude-standard').splitlines())
out=ROOT/'workbench/.artifacts/w5k'/('remote-readback.json' if remote else 'committed-readback.json')
out.write_bytes((json.dumps(result,indent=2)+'\n').encode('utf-8'))
print(json.dumps(result))
