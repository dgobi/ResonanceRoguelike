"""Whole genuine injury save; current native response, never a fresh acceptance witness."""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[3];out=Path(__file__).resolve().parent/'response'
out.mkdir(exist_ok=True)
sys.path.insert(0,str(root/'tools'))
from verify_g22 import inputs
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((out.parent/'inputs.json').read_text())['source'];assert inputs()==frozen
source=root/'.baseline/g22-development-20261031-a/journey-j/ward'
destination=root/'evidence/gameplay-g22/response-input';destination.mkdir(exist_ok=True)
for name in ('first-injury.zip','continuation-context.json'):shutil.copy2(source/name,destination/name)
provenance=dict(scope='Independent current paid-treatment/continued-action conformance. Restores the genuine development G22 world as a whole; no edited state or transplant into final-b, no new mistake, strategy, RNG seed or target search. Repeats its original cold response, not recovery from a later witnessed death. Never integrated fresh acceptance.',source_result=str(source/'result.json'),source_result_sha256=sha(source/'result.json'),source_frozen=False,inputs={p.name:sha(p) for p in destination.iterdir() if p.is_file()})
(destination/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
command=[sys.executable,'-X','utf8','-B',str(root/'tools/g22_journey.py'),'--stage','recover','--resume',str(destination/'first-injury.zip'),'--context',str(destination/'continuation-context.json'),'--evidence',str(out)]
env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
start=time.perf_counter()
with (out/'output.txt').open('w',encoding='utf-8') as log:process=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1000,creationflags=0x08000000)
result=json.loads((out/'recover/result.json').read_text());treatment=result.get('treatment',{})
labels=[r['label'] for r in result.get('ledger',[])]
treatment_passed=(treatment.get('turns')==1 and treatment.get('owned_after') is False and treatment.get('remaining') is False and 0<treatment.get('after_hp',0)-treatment.get('before_hp',0)<=12)
receipt=dict(tested_revision='22322cb98d0453a48e66625408e0772b03e80598',driver_sha256=sha(Path(__file__)),command=command,cwd=str(root),seconds=time.perf_counter()-start,process_exit_code=process.returncode,original_journey_process_passed=result.get('passed',False),finite_paid_treatment_passed=treatment_passed,treatment=treatment,meaningful_followup='withdrew from store alive' in labels,source_stable=inputs()==frozen,source_manifest='../inputs.json',provenance='../response-input/provenance.json',g22_acceptance='partial/blocked',integrated_journey_passed=False,result_sha256=sha(out/'recover/result.json'),log_sha256=sha(out/'output.txt'),limit='This branch verifies finite treatment and further ordinary action. Its failed full return remains failed, and no evidence is stitched to the separately generated final-b world.')
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert treatment_passed and receipt['meaningful_followup'] and receipt['source_stable'],receipt
print(json.dumps(receipt,indent=2))
