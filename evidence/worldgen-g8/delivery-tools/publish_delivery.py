"""Explicit G8 main/tag publication, immutable remote readback and wiki drift."""
import json
import os
import datetime
from pathlib import Path
import subprocess
import sys

os.environ.update(GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='never')
ROOT=Path.cwd();OUT=ROOT/'.baseline/worldgen-g8-delivery';OUT.mkdir(parents=True,exist_ok=True)
release=json.loads((ROOT/'evidence/worldgen-g8/final-b/release.json').read_text());assert release['passed']
sys.path.insert(0,str(ROOT/'tools'))
from verify_b3 import source_manifest
assert source_manifest()==release['source'],'tested inputs changed'
assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='main'
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip(),'uncommitted delivery files remain'
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();verified='checkpoint/worldgen-g8-verified-20261024-a'
present=subprocess.run(['git','rev-parse','--verify','refs/tags/'+verified],capture_output=True,text=True)
if present.returncode==0:assert present.stdout.strip()==head,'existing immutable tag points elsewhere'
else:subprocess.run(['git','tag',verified],check=True)
names=['start-20261024-a','authoring-protection-20261024-a','authoring-protection-20261024-b','wiki-integration-20261024-a','composition-20261024-a','lifecycle-20261024-a','authoring-docs-20261024-a','final-inputs-20261024-a','final-inputs-20261024-b','verified-20261024-a']
tags=['checkpoint/worldgen-g8-'+name for name in names]
expected={'refs/heads/main':head}
for name in tags:expected['refs/tags/'+name]=subprocess.check_output(['git','rev-parse','refs/tags/'+name],text=True).strip()
push_command=['git','push','origin','main',*tags];pushed=subprocess.run(push_command,capture_output=True,text=True,timeout=300)
(OUT/'push.txt').write_text(pushed.stdout+pushed.stderr,encoding='utf-8');assert pushed.returncode==0,pushed.stderr
query=['git','ls-remote','origin',*expected];readback=subprocess.check_output(query,text=True,timeout=60);actual={ref:oid for oid,ref in (line.split() for line in readback.splitlines())};assert actual==expected,(actual,expected)
drift_command=[sys.executable,'-X','utf8','Resonance_Wiki_Maintenance/build_wiki.py','--repo',str(ROOT),'--check-drift'];drift=subprocess.run(drift_command,capture_output=True,text=True,encoding='utf-8',timeout=60);assert drift.returncode==0,drift.stderr
receipt=dict(passed=True,readback_time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),delivered_commit=head,verified_tag=verified,frozen_input_commit=release['input_commit'],frozen_input_tag='checkpoint/worldgen-g8-final-inputs-20261024-b',branch='main',remote='origin',remote_url=subprocess.check_output(['git','remote','get-url','origin'],text=True).strip(),push_command=push_command,push_exit_code=pushed.returncode,push_stdout=pushed.stdout,push_stderr=pushed.stderr,readback_command=query,expected=expected,observed=actual,raw_readback=readback,source_unchanged_from_frozen_run=True,post_delivery_wiki_drift=dict(command=drift_command,exit_code=drift.returncode,result=json.loads(drift.stdout)),note='Stored outside committed content to avoid a self-referential delivery SHA. Only the named G8 checkpoint tags and existing main were published; no force push or PR.')
(OUT/'publication.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=True,delivered_commit=head,verified_tag=verified,remote_tags=len(tags),receipt=str(OUT/'publication.json')),indent=2))
