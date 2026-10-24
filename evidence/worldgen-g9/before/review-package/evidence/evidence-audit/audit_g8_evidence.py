"""Read-only independent audit of retained G8 frozen inputs and receipts."""
import collections,hashlib,json,pathlib,subprocess,zipfile
R=pathlib.Path('/workspace/scratch/1652b4369862/resonance-review')
O=pathlib.Path('/workspace/scratch/1652b4369862/g8-review-evidence/evidence-audit')
def sha(b):return hashlib.sha256(b).hexdigest()
def lf(b):return b.replace(b'\r\n',b'\n').replace(b'\r',b'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
def read(p):return json.loads((R/p).read_text())
def tree(rev):return {p.decode():h.decode() for row in git('ls-tree','-r','-z',rev).split(b'\0') if row for info,p in [row.split(b'\t',1)] for m,t,h in [info.split()]}
def relation(b,expected,n=None):
 if sha(b)==expected and (n is None or len(b)==n):return 'exact'
 for transformed in (lf(b),lf(b).replace(b'\n',b'\r\n')):
  if sha(transformed)==expected and (n is None or len(transformed)==n):return 'uniform-newline-reconstruction'
 return 'mismatch'
idx=read('evidence/worldgen-g8/index.json');head=git('rev-parse','HEAD').decode().strip();frozen=idx['frozen_input_commit'];ht,ft=tree(head),tree(frozen)
inputs=read('evidence/worldgen-g8/final-b/focused/inputs.json');sources=[]
for p,v in inputs.items():
 b=(R/p).read_bytes();blob=git('cat-file','blob',frozen+':'+p);raw_status=relation(b,v['raw_sha256'],v['bytes']);problems=[]
 if sha(blob)!=v['committed_raw_sha256']:problems.append('frozen blob differs from committed digest')
 if v['git_blob']!=ft[p]:problems.append('declared Git object differs')
 if ht.get(p)!=ft[p]:problems.append('HEAD changed since frozen gate')
 if b!=blob:problems.append('working bytes differ from frozen Git blob')
 if v['canonical_lf_sha256'] is not None and sha(lf(b))!=v['canonical_lf_sha256']:problems.append('canonical input differs')
 if raw_status=='mismatch':problems.append('tested raw bytes not reconstructable')
 sources.append(dict(path=p,git_blob=ft[p],raw_relation=raw_status,reported_relation=v['relation'],issues=problems))
gates=[]
for g in idx['final_gates']:
 p=g['path'];r=read(p);directory=(R/p).parent;outputs=[]
 for name,v in r['outputs'].items():
  q=directory/name
  outputs.append(dict(path=name,relation=relation(q.read_bytes(),v['sha256'],v['bytes']) if q.is_file() else 'not-retained',bytes=v['bytes']))
 inp=read(str(directory.relative_to(R)/'inputs.json'))
 gates.append(dict(name=g['name'],receipt=p,receipt_relation=relation((R/p).read_bytes(),g['sha256'],g['bytes']),input_commit=r['input_commit'],end_commit=r['end_commit'],passed=r['passed'],exit_code=r['exit_code'],timeout=r['timeout'],seconds=r['seconds'],source_stable=r['source_stable'],committed_inputs_reconciled=r['committed_inputs_reconciled'],identical_input_manifest=inp==inputs,identical_source_manifest=r['source']=={k:v['raw_sha256'] for k,v in inputs.items()},output_counts=dict(collections.Counter(x['relation'] for x in outputs)),outputs=outputs))
ziprows=[]
for p in sorted((R/'evidence/worldgen-g8').rglob('*.zip')):
 with zipfile.ZipFile(p) as z:
  bad=z.testzip();members=z.infolist();ziprows.append(dict(path=str(p.relative_to(R)),sha256=sha(p.read_bytes()),bytes=p.stat().st_size,members=len(members),bad_crc=bad,duplicate_members=len(members)-len({x.filename for x in members})))
prod=read(idx['production']['receipt']);browser={}
for name in ('chromium','firefox'):
 d=read('evidence/worldgen-g8/final-b/browser/results/'+name+'.json');browser[name]={k:v for k,v in d.items() if k not in ('checks','source','runtime_source')};browser[name]['check_count']=len(d.get('checks',[]))
missing=[(g['name'],x['path']) for g in gates for x in g['outputs'] if x['relation']=='not-retained']
fixture=R/'tools/critical_fix_regressions/fixtures/g8/authentic-g7-checkpoint.zip';witness=read('tools/critical_fix_regressions/fixtures/g8/g7-witness.json')
with zipfile.ZipFile(fixture) as z:
 manifest=json.loads(z.read('manifest.json'));fixture_issues=[]
 if set(z.namelist())!=set(witness['checkpoint_inventory']):fixture_issues.append('witness inventory differs')
 for name,record in witness['checkpoint_inventory'].items():
  b=z.read(name)
  if len(b)!=record['bytes'] or sha(b)!=record['sha256']:fixture_issues.append(name+' differs from witness')
  if name!='manifest.json' and manifest['files'].get(name)!=record:fixture_issues.append(name+' differs from checkpoint manifest')
 world=json.loads(z.read('world.json'));plan_identity=sha(json.dumps(world['plan'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
 if plan_identity!=witness['plan_identity']:fixture_issues.append('plan identity differs')
fixture_audit=dict(sha256=sha(fixture.read_bytes()),creator_commit=witness['head'],source_stable=witness['source_stable'],member_count=len(witness['checkpoint_inventory']),plan_identity=plan_identity,plan_version=world['plan']['version'],plan_revision=world['plan']['generation_revision'],visited=witness['visited'],pending=witness['pending'],compound=witness['compound'],rural_pending=witness['rural_pending'],issues=fixture_issues)
report=R/'docs/owner/WORLDGEN_G8.md';attachment=pathlib.Path('/workspace/scratch/1652b4369862/upload/Pasted text(6).txt')
summary=dict(schema=1,scope='Independent read-only verification of retained records; not a fresh execution of Windows gates.',head=head,frozen_input_commit=frozen,working_tree_status=git('status','--short').decode(),report=dict(attachment_exact=attachment.read_bytes()==report.read_bytes(),sha256=sha(report.read_bytes()),bytes=report.stat().st_size),source_counts=dict(count=len(sources),raw_relations=dict(collections.Counter(x['raw_relation'] for x in sources)),reported_relations=dict(collections.Counter(x['reported_relation'] for x in sources)),files_with_issues=sum(bool(x['issues']) for x in sources)),sources=sources,gates=gates,retained_zips=ziprows,production=dict(totals=prod['totals'],unfiltered=prod['only'] is None and prod['case'] is None,coverage=prod['coverage'],negative_controls=prod['runner_negative_controls'],passed=prod['passed']),browser={n:{k:d[k] for k in ('browser','version','passed','errors','codec_documents','check_count')} for n,d in browser.items()},omitted_outputs_scope=dict(count=len(missing),all_in_disposable_saves=all('/saves/' in p for g,p in missing)),authentic_g7_fixture=fixture_audit,first_final=dict(passed=read('evidence/worldgen-g8/final-a/release.json')['passed'],results=[dict(gate=x['gate'],exit_code=x['exit_code']) for x in read('evidence/worldgen-g8/final-a/release.json')['results']]),portable_review_archive='Not present in repository or supplied attachments; no claim of independent portable-delivery CRC/member/publication audit.')
(O/'audit.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('sources','gates','production','browser')},indent=2))
print('gate summary',json.dumps([{k:v for k,v in g.items() if k!='outputs'} for g in gates],indent=2))
print('production',prod['totals'],'coverage_count',len(prod['coverage']),'negative_controls',len(prod['runner_negative_controls']));print('browser',json.dumps(browser,indent=2)[:3000])
