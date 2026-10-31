"""Close evidence only after affected suites finish; never changes acceptance failures."""
import hashlib,json,re,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
root=Path.cwd().resolve();out=root/'evidence/gameplay-g22';final=out/'final-c'
sys.path.insert(0,str(root/'tools'))
from verify_g22 import inputs,git_binding
def read(p):return json.loads(p.read_bytes())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
b=read(out/'final-b/release.json');c=read(final/'release.json');frozen=read(final/'inputs.json')
assert c['scoped_verification_passed'] and c['source_stable'] and not c['passed'] and c['g22_acceptance']=='partial/blocked'
assert inputs()==frozen['source']
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert head==c['tested_revision']==frozen['head']=='22322cb98d0453a48e66625408e0772b03e80598'
assert git_binding(head,frozen['source'])==frozen['git_binding']
focused=(final/'focused/focused-tests.txt').read_text(encoding='utf-8');worker=(final/'workbench-worker-output.txt').read_text(encoding='utf-8')
assert re.search(r'Ran 439 tests in',focused) and re.search(r'\nOK\s*$',focused)
assert re.search(r'Ran 118 tests in',worker) and re.search(r'OK \(skipped=1\)\s*$',worker)
assert b['production']['passed'] and b['production']['totals']==dict(checks=3704,passed=3704,failed=0,workers=159)
response=read(final/'response/receipt.json');visual=read(final/'visual-audit.json')
assert response['finite_paid_treatment_passed'] and response['meaningful_followup'] and response['source_stable'] and not response['integrated_journey_passed']
assert not response['original_journey_process_passed'] and response['process_exit_code']==1
assert visual['passed'] and visual['driver_sha256']==digest(final/'visual-audit-driver.py')
assert response['driver_sha256']==digest(final/'response-conformance-driver.py')
assert frozen['driver']['sha256']==digest(final/'followup-driver.py')
assert digest(root/b['package']['executable']['path'])==b['package']['executable']['sha256']
shutil.copy2(__file__,final/'closure-driver.py')

def blob_binding(relative):
    raw=(root/relative).read_bytes()
    oid=subprocess.check_output(['git','hash-object','--path='+relative,relative],cwd=root,text=True).strip()
    def object_hash(value):return hashlib.sha1(('blob '+str(len(value))+'\0').encode()+value).hexdigest()
    canonical=raw if object_hash(raw)==oid else raw.replace(b'\r\n',b'\n')
    assert object_hash(canonical)==oid,relative
    return dict(working_sha256=hashlib.sha256(raw).hexdigest(),git_blob=oid,committed_sha256=hashlib.sha256(canonical).hexdigest(),match='exact' if canonical==raw else 'CRLF/LF only')

additional=['final-c/followup-driver.py','final-c/visual-audit-driver.py','final-c/response-conformance-driver.py','final-c/closure-driver.py','final-c/published-report-variant.json']
additional+=['recovery-input/'+n for n in ('treated.zip','continuation-context.json','provenance.json')]
additional+=['response-input/'+n for n in ('first-injury.zip','continuation-context.json','provenance.json')]
bindings={('evidence/gameplay-g22/'+p):blob_binding('evidence/gameplay-g22/'+p) for p in additional}
completion=dict(status='partial/blocked',g22_accepted=False,arc_exit_complete=False,implementation_contracts_verified=True,tested_revision=head,closed_utc=datetime.now(timezone.utc).isoformat(),baseline='98a5af7dd2653b1b9b9a34a57880a98f2d3599d7',baseline_frozen_matches=2864,source_input_count=len(frozen['source']),source_manifest='final-c/inputs.json',source_manifest_sha256=digest(final/'inputs.json'),additional_input_bindings=bindings,
    verification=dict(focused=dict(run=439,passed=439,unfiltered=True,receipt='final-c/focused/run.json'),production=b['production'],worker=dict(run=118,passed=117,skipped=1,skip='Dependency-absence negative control uses development interpreter and passes separately in final-b.',unfiltered=True),frontend=90,host=71,typecheck=True,clippy=True,windows_nsis=True,native=['hearing','rivals','reports'],historical=['g14','g16'],retained_original_loops=['g19','g20-sound','g21-native','g21-common','g21-conflict','g21-musk','g21-passive','g21-lethal','g21-revisit'],metadata_seeds=[20261023,29417,20261030],source_stable=True),
    exact_retention_boundary=c['retained_boundary'],
    wall_seconds=dict(final_b=b['final_wall_seconds'],final_c=c['final_wall_seconds'],note='Each release records elapsed wall time; concurrent durations are not summed. Response/visual probes occurred during the final-c suite interval.'),
    journey=dict(acceptance=False,fresh_read=True,ordinary_preparation_return=True,fresh_ward='Failed replay guard: turn1797 versus required1793, same HP57 and position48,18. No manufactured treatment save.',separate_current_response=response['treatment'],current_response_receipt='final-c/response/receipt.json',continued_exit=True,alive_home_return=False,spent_checkpoint_return_death=dict(turn=1966,hp=0,square=[69,99],home=[73,99]),first_injury_response_return_death=dict(turn=1945,hp=0,square=[69,99]),cold_revisit=True,assistance='Observation-limited local paths and declared geometric coarse policy, original Engine.run and app-local controls; no unaided human discovery claim. Independent whole-world checkpoint probes are not stitched to final-b.'),
    material_failures=[dict(attempt='final-a',status='failed/incomplete',failure='Genuine G14 exact fingerprint caught empty optional save keys. Corrected omission, original archive/assertion unchanged.'),dict(attempt='final-b',status='failed',failure='Focused9failures/4errors and worker2count failures, corrected only historical factory inputs/catalogue counts; full suites rerun in C. Fresh Ward guard and secondary missing-treatment evidence remain failed.'),dict(attempt='final-c',status='partial/blocked',failure='Both genuine continuation branches fail the alive home return. Paid treatment/meaningful exit and persistence pass separately; no complete acceptance.'),dict(attempt='development',status='diagnostic only',catalogue='development-summary.json',source_frozen=False)],
    metadata_note='The original response/receipt.json provenance field is one relative level short. Its authoritative provenance is evidence/gameplay-g22/response-input/provenance.json, bound above. Execution results are retained unchanged.',
    publication=dict(required=True,branch='main',force=False,final_checkpoint='checkpoint/gameplay-g22-partial-blocked-20261031-a',verified_complete_checkpoint=False,full_delivery_sha_and_remote_readback='.baseline/g22-publication.json (outside self-referencing commit)'),
    unrelated_owner_work=dict(path='RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md',sha256=digest(root/'RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md'),disposition='Preserved untracked; excluded from task commits.'))
(out/'completion.json').write_bytes((json.dumps(completion,indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(status=completion['status'],contracts_verified=True,tested_revision=head,source_inputs=completion['source_input_count'],focused=439,worker_run=118)))
