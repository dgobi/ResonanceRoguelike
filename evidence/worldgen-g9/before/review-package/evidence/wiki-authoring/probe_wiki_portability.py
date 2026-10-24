"""Read production checkout; exercise an isolated maintenance-only copy."""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
repo=Path('/workspace/scratch/1652b4369862/resonance-review')
out=Path('/workspace/scratch/1652b4369862/g8-review-evidence/wiki-authoring')
copy=out/'maintenance-copy'
if copy.exists():raise SystemExit('Refusing to replace existing isolated copy')
shutil.copytree(repo/'Resonance_Wiki_Maintenance',copy,ignore=shutil.ignore_patterns('__pycache__'))
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPATH']=str(out/'docs-deps')
rows=[]
def run(name,args):
 t=time.perf_counter();p=subprocess.run([sys.executable,'-X','utf8',*map(str,args)],cwd=repo,env=env,capture_output=True,text=True,timeout=120)
 (out/(name+'.stdout.txt')).write_text(p.stdout);(out/(name+'.stderr.txt')).write_text(p.stderr)
 row={'name':name,'command':[sys.executable,'-X','utf8',*map(str,args)],'exit_code':p.returncode,'seconds':time.perf_counter()-t,'stdout':name+'.stdout.txt','stderr':name+'.stderr.txt'};rows.append(row);print(json.dumps(row),flush=True)
 return p
initial_hash=hashlib.sha256((copy/'Resonance_Owner_Wiki.html').read_bytes()).hexdigest()
run('delivered-drift',[copy/'build_wiki.py','--repo',repo,'--check-drift'])
run('build-a',[copy/'build_wiki.py','--repo',repo])
first={f:hashlib.sha256((copy/f).read_bytes()).hexdigest() for f in ('Resonance_Owner_Wiki.html','source-manifest.json','build-report.json')}
run('drift-a',[copy/'build_wiki.py','--repo',repo,'--check-drift'])
run('validate-a',[copy/'validate_wiki.py','--repo',repo,'--html',copy/'Resonance_Owner_Wiki.html','--report',out/'integrity-a.json'])
run('build-b',[copy/'build_wiki.py','--repo',repo])
second={f:hashlib.sha256((copy/f).read_bytes()).hexdigest() for f in first}
run('drift-b',[copy/'build_wiki.py','--repo',repo,'--check-drift'])
result={'read_only_game_checkout':str(repo),'isolated_maintenance_copy':str(copy),'initial_html_sha256':initial_hash,'first':first,'second':second,'repeat_identical':first==second,'commands':rows}
(out/'wiki-rebuild-probe.json').write_text(json.dumps(result,indent=2)+'\n')
