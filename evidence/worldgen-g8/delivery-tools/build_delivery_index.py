"""Build review metadata from completed receipts; never changes game inputs."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path.cwd();OUT=ROOT/'evidence/worldgen-g8';FINAL=OUT/'final-b'


def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def ref(p):return p.relative_to(ROOT).as_posix()
def binding(p):return dict(path=ref(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)


release=read(FINAL/'release.json');assert release['passed'] and release['source_stable']
gates=[]
for entry in release['results']:
    p=Path(entry['receipt']);r=read(p);assert r['passed'] and r['committed_inputs_reconciled'] and r['input_commit']==release['input_commit']
    gates.append(dict(name=entry['gate'],**binding(p),seconds=r['seconds'],exit_code=r['exit_code'],timeout=r['timeout'],input_commit=r['input_commit'],raw_and_lf_hashes=ref(p.parent/'inputs.json')))
focused=read(FINAL/'focused/results/run.json');assert focused['passed'];tests=re.search(r'Ran (\d+) tests in ([\d.]+)s',(FINAL/'focused/results/focused-tests.txt').read_text(encoding='utf-8'))
parent=read(FINAL/'focused/results/parent.json');assert parent['inherited_pythonpath'] is None
production_paths=list((FINAL/'production/results').glob('*/results.json'));assert len(production_paths)==1;production=read(production_paths[0])
browser=read(FINAL/'browser/results/summary.json');assert browser['passed']
authoring=read(FINAL/'authoring/results/workflows.json');assert authoring['passed']
wiki=read(FINAL/'wiki/results/edition.json');assert wiki['passed']
diagnostic=read(FINAL/'diagnostic/results/run.json');assert diagnostic['passed']
matrix=[]
for line in (ROOT/'docs/owner/WORLDGEN_G8.md').read_text(encoding='utf-8').splitlines():
    if line.startswith('| G8-'):
        _,identifier,source,evidence,_=line.split('|');matrix.append(dict(id=identifier.strip(),status='complete',source_or_contract=source.strip(),evidence_description=evidence.strip()))
assert len(matrix)==19
attempts=[]
for p in sorted(OUT.rglob('receipt.json')):
    if p.is_relative_to(FINAL):continue
    r=read(p);attempts.append(dict(path=ref(p),passed=r.get('passed'),exit_code=r.get('exit_code'),source_stable=r.get('source_stable'),committed_inputs_reconciled=r.get('committed_inputs_reconciled'),seconds=r.get('seconds'),classification='development or historical pre-change receipt; never substituted for final frozen gates'))
comparisons=[]
for row in diagnostic['g8_composition']:
    seed=row['seed'];old=read(OUT/f'before/baseline/results/plan-{seed}.json');new=read(FINAL/f'diagnostic/results/plan-{seed}.json');cost=row['cost_comparison'];oldrun=next(r for r in read(OUT/'before/baseline/results/run.json')['runs'] if r['seed']==seed);newrun=next(r for r in diagnostic['runs'] if r['seed']==seed)
    comparisons.append(dict(seed=seed,country_routes_exact=row['country_routes_exact'],cost=cost,g7_settlement_seconds=oldrun['settlement_planning_seconds'],g8_settlement_seconds=newrun['settlement_planning_seconds'],g7_town_lots=sum(len(s['plots']) for s in old['settlements']),g8_town_lots=sum(len(s['plots']) for s in new['settlements']),towns=row['settlements'],subtree_bytes=row['subtree_bytes']))
write(OUT/'metrics-comparison.json',dict(sample_size=3,source=release['input_commit'],units='plan bytes compact UTF-8 JSON; time seconds; local travel four-neighbour tile steps; area tile cells',limits='Same machine/interpreter, serial samples. G7 has no resolved block/common registry or per-fit work counters; those baseline fields are unavailable, not inferred as G8 geometry. No universal performance or frequency claim.',seeds=comparisons))
index=dict(schema=1,milestone='G8',status='complete',original_source='8e56d36d72537e8b32c3666dd5d19723d1afdf3a',reviewed_wiki_source=read(ROOT/'Resonance_Wiki_Maintenance/wiki-config.json')['commit'],frozen_input_commit=release['input_commit'],frozen_input_tag='checkpoint/worldgen-g8-final-inputs-20261024-b',verified_delivery_tag='checkpoint/worldgen-g8-verified-20261024-a',publication='Actual delivered commit/tag and remote readback are recorded in the portable archive publication.json and its adjacent delivery receipt, outside self-referential committed content.',matrix=matrix,final_gates=gates,focused=dict(tests=int(tests[1]),seconds=float(tests[2]),inherited_pythonpath=None,unfiltered=True),production=dict(receipt=ref(production_paths[0]),totals=production.get('totals'),only=production.get('only'),case=production.get('case'),negative_controls=len(production.get('runner_negative_controls',[]))),browser=dict(runs=browser['runs'],playwright=browser['playwright'],driver=browser['driver']),authoring=dict(g8_top_level_workflows=6,inherited='G7 workflows with nested G6/G5; nested counts not added as independent G8 workflows'),wiki=dict(edition='1.2',html=binding(ROOT/'Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html'),integrity=ref(FINAL/'wiki/results/integrity.json'),reader=ref(FINAL/'wiki/results/reader/reader.json'),input_binding=ref(ROOT/'Resonance_Wiki_Maintenance/source-manifest.json')),journey=dict(steps=diagnostic['journey']['steps'],checkpoint={k:v for k,v in diagnostic['journey']['explored_checkpoint'].items() if k not in ('surface_fingerprints','inventory_ids')},worst_transition_seconds=diagnostic['journey']['worst_transition_seconds']),metrics=ref(OUT/'metrics-comparison.json'),visual_inspection=ref(OUT/'visual-inspection.json'),attempts=attempts,retained_failures=['Frozen final-a: diagnostic comparison report had one unmatched parenthesis; corrected and executed all ordinary metric paths before full final-b rerun.','Original CLI collisions overwrite disposable inputs before protection.','Authoring development a: valid roadside draft unselected at former demonstration seed; documented seed 0 positive.','Authoring development b: valid landmark draft unselected; explicit complete demonstration policy now selects the draft.','Authoring development c: stale editor catalog detected before refresh.','Wiki development a/b: Firefox native loader could not resolve logical Windows LocalAppData; same resolved-path policy as established editor harness fixes it.','Early authoring protection iterations retain cross-volume hard-link skip and diagnostic wording failure; final same-volume checks execute successfully.'],limits=['Windows symlinks unavailable; historical Linux receipt preserved and local same-file hard-link cases executed.','Controlled grid schedules demonstrate all cardinal directions; ordinary seed matrix is separate.','Journey uses stationary actors, paused AI/survival and invincibility; separate lifecycle tests run ordinary native updates.','Production screenshots use revealed visibility. Headless wiki checks do not constitute an assistive-technology audit or OS clipboard readback.','Existing broad explored-checkpoint cost is measured; no storage compaction or G9 work.'])
write(OUT/'index.json',index)
lines=['# G8 evidence index','',f"Frozen input: `{release['input_commit']}` (`checkpoint/worldgen-g8-final-inputs-20261024-b`).",'',f"All {len(gates)} serial frozen gates passed. Focused discovery: {tests[1]} tests, no inherited PYTHONPATH. The production gate is unfiltered; its exact worker/check totals remain in the linked receipt.",'','| Gate | Seconds | Receipt |','|---|---:|---|']
lines += [f"| {g['name']} | {g['seconds']:.3f} | [{g['name']}]({Path(g['path']).relative_to('evidence/worldgen-g8').as_posix()}) |" for g in gates]
lines += ['','[Machine-readable matrix and limitations](index.json) · [G7/G8 measures](metrics-comparison.json) · [Owner report](../../../docs/owner/WORLDGEN_G8.md) · [Offline wiki](../../../Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html)','','Development failures, historical receipts, controlled examples and final ordinary runs remain distinct in the JSON index. The portable archive manifest inventories retained files and omitted disposable saves. `publication.json` records delivered commit/tag and remote readback outside the committed self-reference.','']
(OUT/'INDEX.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(dict(gates=len(gates),focused_tests=int(tests[1]),production=production.get('totals'),matrix=len(matrix)),indent=2))
