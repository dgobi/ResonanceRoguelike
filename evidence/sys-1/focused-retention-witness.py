"""Repeat both complete affected modules after two exact SYS-1 expectations.

The full unfiltered run is retained unchanged. Only the commissioned successor
name and installed-candidate total may differ; all other input bytes must match.
This evidence artifact binds its own source separately from the consumed inputs.
"""
from datetime import datetime,timezone
import argparse,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from verify_sys_1 import inputs

REPLACEMENTS={
 'tools/critical_fix_regressions/tests/test_gameplay_g16.py':(
  b"row['asset']='workshop_d' if row['asset']=='workshop_a' else row['asset'][:-1]+'b'",
  b"row['asset']={'workshop_a':'workshop_d','apothecary_a':'apothecary_c','tool_shed_a':'tool_shed_b'}[row['asset']]"),
 'tools/critical_fix_regressions/tests/test_structure_access.py':(
  b"self.assertEqual(selected['preserved_installed_candidates'],62)",
  b"self.assertEqual(selected['preserved_installed_candidates'],63)")}
FAILURES={'test_live_roles_preserve_membership_order_and_native_primary_selection',
          'test_cottage_access_matches_actual_note_and_container_actions_both_mirrors'}


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--original',type=Path,required=True);ap.add_argument('--evidence',type=Path,required=True);a=ap.parse_args()
 original=a.original.resolve();out=a.evidence.resolve();assert out!=original
 out.mkdir(parents=True,exist_ok=True)
 assert not (out/'focused.json').exists()
 read=lambda p:json.loads(p.read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 release=read(original/'release.json');before=read(original/'inputs.json');frozen=inputs()
 assert release['finished_utc'] and release['source_stable'] and len(release['commands'])==15
 assert sha(original/'inputs.json')==release['inputs_sha256']
 assert [r['gate'] for r in release['commands'] if not r['passed']]==['focused']
 log=(original/'focused/focused-tests.txt').read_text(encoding='utf8')
 assert sha(original/'focused.log')==next(r['log_sha256'] for r in release['commands'] if r['gate']=='focused')
 assert log in (original/'focused.log').read_text(encoding='utf8')
 assert set(re.findall(r'^FAIL: (\w+) \(',log,re.M))==FAILURES
 assert not re.search(r'^ERROR:',log,re.M) and 'FAILED (failures=2)' in log
 changed=[p for p in sorted(set(before)|set(frozen)) if before.get(p)!=frozen.get(p)]
 assert changed==sorted(REPLACEMENTS),changed
 for path,(old,new) in REPLACEMENTS.items():
  raw=subprocess.check_output(['git','show',release['revision']+':'+path],cwd=ROOT)
  # Match the exact recorded working bytes, allowing Git's checkout EOL policy.
  candidates=[raw,raw.replace(b'\r\n',b'\n'),raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')]
  raw=next(b for b in candidates if hashlib.sha256(b).hexdigest()==before[path])
  assert raw.count(old)==1 and (ROOT/path).read_bytes()==raw.replace(old,new),path
 (out/'inputs.json').write_text(json.dumps(frozen,indent=2),encoding='utf8')
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 assert sys.version_info[:3]==(3,11,0) and sys.platform=='win32'
 env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',RESONANCE_GAME_ROOT=str(ROOT/'roguelike'),RESONANCE_TEST_EVIDENCE_DIR=str(out/'affected'))
 env['RESONANCE_TEST_TOOLS']=str(ROOT/'tools/critical_fix_regressions/historical_tools')
 env['PYTHONPATH']=os.pathsep.join(str(ROOT/p) for p in ('roguelike','tools','tools/critical_fix_regressions/tests'))
 modules=['test_gameplay_g16','test_structure_access']
 command=[sys.executable,'-X','utf8','-B','-m','unittest',*modules,'-v']
 started=datetime.now(timezone.utc).isoformat();begin=time.perf_counter();target=out/'affected.log'
 with target.open('w',encoding='utf8') as f:
  code=subprocess.run(command,cwd=ROOT/'roguelike',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200,creationflags=0x08000000).returncode
 text=target.read_text(encoding='utf8');stable=inputs()==frozen
 result=dict(passed=code==0 and stable,gate='focused',revision=head,runtime_content_editor_revision=release['revision'],
  started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-begin,
  command=command,cwd=str(ROOT/'roguelike'),exit_code=code,modules=modules,
  full_suite_tests=int(re.findall(r'Ran (\d+) tests?',log)[-1]),original_failed_expectations=sorted(FAILURES),
  repeated_module_tests=int(re.findall(r'Ran (\d+) tests?',text)[-1]),source_stable=stable,
  witness_sha256=sha(Path(__file__)),original_release_sha256=sha(original/'release.json'),original_focused_log_sha256=sha(original/'focused/focused-tests.txt'),inputs_sha256=sha(out/'inputs.json'),
  changed_inputs=[dict(path=p,before=before[p],after=frozen[p]) for p in changed],
  retained_gates=[r['gate'] for r in release['commands'] if r['passed']],log_sha256=sha(target),
  retention='Only the explicit current apothecary successor and preserved installed-candidate total changed. Both complete affected modules repeated; all remaining tests from the unfiltered suite and all other successful gates retain identical consumed inputs. No runtime, content, editor or verifier runner changed; all assertions remain, with only the two explicit expectations updated.')
 (out/'focused.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps(result,indent=2));return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
