"""Read-only audit of delivered G9 source and retained evidence identities.

Run with --repo and --output. Does not execute game, browser, or gate code.
"""
import argparse
import collections
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

ap=argparse.ArgumentParser()
ap.add_argument('--repo',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
a=ap.parse_args(); R=a.repo.resolve(); O=a.output.resolve(); O.mkdir(parents=True,exist_ok=True)
E=R/'evidence/worldgen-g9'
def sha(b):return hashlib.sha256(b).hexdigest()
def lf(b):return b.replace(b'\r\n',b'\n').replace(b'\r',b'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def tree(rev):return {p.decode():h.decode() for row in git('ls-tree','-r','-z',rev).split(b'\0') if row for info,p in [row.split(b'\t',1)] for m,t,h in [info.split()]}
def relation(b,expected,n=None):
    if sha(b)==expected and (n is None or len(b)==n):return 'exact'
    for transformed in (lf(b),lf(b).replace(b'\n',b'\r\n')):
        if sha(transformed)==expected and (n is None or len(transformed)==n):return 'uniform-newline-reconstruction'
    return 'mismatch'

idx=read(E/'index.json'); head=git('rev-parse','HEAD').decode().strip(); frozen=idx['frozen_input_commit']
ht,ft=tree(head),tree(frozen); inputs=read(E/'final-b/focused/inputs.json')
ids=sorted({ft[p] for p in inputs}); stream=io.BytesIO(subprocess.run(['git','cat-file','--batch'],cwd=R,input=('\n'.join(ids)+'\n').encode(),capture_output=True,check=True).stdout); blobs={}
for identifier in ids:
    header=stream.readline().decode().split(); blobs[identifier]=stream.read(int(header[2])); assert stream.read(1)==b'\n'
sources=[]
for p,v in inputs.items():
    b=(R/p).read_bytes(); blob=blobs[ft[p]]; raw_status=relation(b,v['raw_sha256'],v['bytes']); problems=[]
    if sha(blob)!=v['committed_raw_sha256']:problems.append('frozen blob differs from committed digest')
    if v['git_blob']!=ft[p]:problems.append('declared Git object differs')
    if ht.get(p)!=ft[p]:problems.append('HEAD changed since frozen gate')
    if b!=blob:problems.append('working bytes differ from frozen Git blob')
    if v['canonical_lf_sha256'] is not None and sha(lf(b))!=v['canonical_lf_sha256']:problems.append('canonical input differs')
    if raw_status=='mismatch':problems.append('tested raw bytes not reconstructable')
    sources.append(dict(path=p,git_blob=ft[p],raw_relation=raw_status,reported_relation=v['relation'],issues=problems))

release=read(E/'final-b/release.json'); summary=read(E/'release-summary.json'); gates=[]
for g in summary['gates']:
    p=E/g['receipt'];r=read(p); directory=p.parent; outputs=[]
    for name,v in r['outputs'].items():
        q=directory/name
        outputs.append(dict(path=name,relation=relation(q.read_bytes(),v['sha256'],v['bytes']) if q.is_file() else 'not-retained',bytes=v['bytes']))
    inp=read(directory/'inputs.json')
    gates.append(dict(name=g['gate'],receipt=str(p.relative_to(R)),receipt_relation=relation(p.read_bytes(),g['sha256']),input_commit=r['input_commit'],end_commit=r['end_commit'],passed=r['passed'],exit_code=r['exit_code'],timeout=r['timeout'],seconds=r['seconds'],source_stable=r['source_stable'],committed_inputs_reconciled=r['committed_inputs_reconciled'],identical_input_manifest=inp==inputs,identical_source_manifest=r['source']=={k:v['raw_sha256'] for k,v in inputs.items()},output_counts=dict(collections.Counter(x['relation'] for x in outputs)),outputs=outputs))
missing=[(g['name'],x['path']) for g in gates for x in g['outputs'] if x['relation']=='not-retained']

fixture=R/'tools/critical_fix_regressions/fixtures/g9/authentic-g8-checkpoint.zip'; witness=read(R/'tools/critical_fix_regressions/fixtures/g9/g8-witness.json')
fixture_issues=[]
with zipfile.ZipFile(fixture) as z:
    crc=z.testzip();manifest=read(E/'before/witness/g8-witness.json'); checkpoint_manifest=json.loads(z.read('manifest.json'))
    if set(z.namelist())!=set(witness['files']):fixture_issues.append('witness inventory differs')
    for name,record in witness['files'].items():
        b=z.read(name)
        if len(b)!=record['bytes'] or sha(b)!=record['sha256']:fixture_issues.append(name+' differs from witness')
        if name!='manifest.json' and checkpoint_manifest['files'].get(name)!=record:fixture_issues.append(name+' differs from checkpoint manifest')
    world=json.loads(z.read('world.json')); plan=world['plan']; plan_identity=sha(json.dumps(plan,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
    if plan_identity!=witness['plan_identity']:fixture_issues.append('plan identity differs')
    preserved=json.loads(gzip.decompress((R/'tools/critical_fix_regressions/fixtures/g9/g8-plan.json.gz').read_bytes()))
    if preserved!=plan:fixture_issues.append('compressed reference plan differs')
fixture_audit=dict(sha256=sha(fixture.read_bytes()),creator_commit=witness['head'],member_count=len(witness['files']),bad_crc=crc,plan_identity=plan_identity,plan_version=plan['version'],plan_revision=plan['generation_revision'],visited=witness['scenes'],pending=witness['pending'],country_pending=witness['country_pending'],mutations=witness['mutations'],controls=witness['controls'],before_copy_exact=fixture.read_bytes()==(E/'before/witness/authentic-g8-checkpoint.zip').read_bytes(),witness_copy_exact=read(E/'before/witness/g8-witness.json')==witness,issues=fixture_issues)

prod=read(E/summary['production']['path']); browser={}
for name in ('chromium','firefox'):
    d=read(E/f'final-b/browser/results/{name}.json');browser[name]={k:d.get(k) for k in ('browser','version','passed','errors','codec_documents')};browser[name]['check_count']=len(d.get('checks',[]))
report=R/'docs/owner/WORLDGEN_G9.md';attachment=R.parent/'upload/Pasted text(7).txt'
result=dict(schema=1,scope='Independent retained-record audit; not fresh execution of recorded Windows gates.',head=head,frozen_input_commit=frozen,working_tree_status=git('status','--short').decode(),report=dict(attachment_exact=attachment.read_bytes()==report.read_bytes(),sha256=sha(report.read_bytes()),bytes=report.stat().st_size),source_counts=dict(count=len(sources),raw_relations=dict(collections.Counter(x['raw_relation'] for x in sources)),reported_relations=dict(collections.Counter(x['reported_relation'] for x in sources)),files_with_issues=sum(bool(x['issues']) for x in sources)),sources=sources,release=dict(passed=release['passed'],source_stable=release['source_stable'],source_manifest_matches=release['source']=={k:v['raw_sha256'] for k,v in inputs.items()},gates_count=len(release['results'])),gates=gates,production=dict(totals=prod['totals'],unfiltered=prod['only'] is None and prod['case'] is None,coverage=prod['coverage'],negative_controls=prod['runner_negative_controls'],passed=prod['passed']),browser=browser,omitted_outputs_scope=dict(count=len(missing),all_in_disposable_saves=all('/saves/' in p for g,p in missing),by_gate=dict(collections.Counter(g for g,p in missing))),authentic_g8_fixture=fixture_audit,first_final=dict(passed=read(E/'final/release.json')['passed'],results=[dict(gate=x['gate'],exit_code=x['exit_code']) for x in read(E/'final/release.json')['results']]),portable_delivery='Original G9 portable archive/publication.json not supplied as attachment or retained at repository root; this audit makes no independent original delivery archive/member/publication assertion.')
(O/'audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('sources','gates','production','browser','authentic_g8_fixture')},indent=2))
print('GATES',json.dumps([{k:v for k,v in g.items() if k!='outputs'} for g in gates],indent=2))
print('PRODUCTION',prod['totals'],'coverage_count',len(prod['coverage']),'negative_controls',len(prod['runner_negative_controls']))
print('BROWSER',json.dumps(browser))
print('FIXTURE',json.dumps({k:v for k,v in fixture_audit.items() if k not in ('visited','mutations')}))
