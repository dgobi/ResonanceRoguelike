"""Independent CLI preservation probes; never writes reviewed game inputs."""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
repo=Path('/workspace/scratch/1652b4369862/resonance-review')
out=Path('/workspace/scratch/1652b4369862/g8-review-evidence/wiki-authoring/collision-probes');out.mkdir()
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env.pop('PYTHONPATH',None)
rows=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(name,kind):
 d=out/name;d.mkdir();recipe=d/'g7_travellers_court.json';child=d/'g7_wayhouse.json'
 for p in (recipe,child,d/'g7_poi_example.json'):shutil.copyfile(repo/'roguelike/docs/examples'/p.name,p)
 base=['--compound',str(recipe),'--child',str(child),'--assigned-compound','S']
 report=d/'report.json'
 if kind=='same':args=base+['--output',str(recipe)]
 elif kind=='init':args=['--init-compound',str(d),'--output',str(child)]
 elif kind=='symlink-plan':
  (d/'report.svg').symlink_to(recipe);args=base+['--output',str(report)]
 elif kind=='symlink-scene':
  (d/'report-0.svg').symlink_to(child);args=base+['--refresh-editor-catalog','--editor-catalog',str(d/'catalog.js'),'--output',str(report)]
 elif kind=='positive':args=base+['--output',str(report)]
 else:raise ValueError(kind)
 before={p.name:digest(p) for p in d.iterdir() if p.is_file()}
 t=time.perf_counter();p=subprocess.run([sys.executable,'-X','utf8',str(repo/'tools/structure_authoring.py'),*args],cwd=repo,env=env,capture_output=True,text=True,timeout=90)
 after={x.name:digest(x) for x in d.iterdir() if x.is_file()}
 inputs_preserved=all(after.get(k)==v for k,v in before.items())
 row={'name':name,'command':[sys.executable,'-X','utf8',str(repo/'tools/structure_authoring.py'),*args],'exit_code':p.returncode,'seconds':time.perf_counter()-t,'input_hashes_before':before,'hashes_after':after,'input_bytes_preserved':inputs_preserved,'stdout':p.stdout,'stderr':p.stderr,'expected_rejection':kind!='positive','unexpected_writes':sorted(set(after)-set(before)) if kind!='positive' else [],'passed':inputs_preserved and ((p.returncode==0 and report.exists()) if kind=='positive' else p.returncode!=0 and 'conflict' in p.stderr.lower() and set(after)==set(before))}
 rows.append(row);(out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({k:row[k] for k in ('name','exit_code','seconds','input_bytes_preserved','passed')}),flush=True)
for a,b in [('report-recipe','same'),('init-existing-child','init'),('plan-symlink-recipe','symlink-plan'),('dynamic-scene-symlink-child-and-refresh','symlink-scene'),('distinct-output','positive')]:run(a,b)
(out/'matrix.json').write_text(json.dumps({'passed':all(r['passed'] for r in rows),'cases':rows},indent=2)+'\n')
