"""Enforced autonomous gate on production main; never copies game source."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from b1_support import ENV, SEED, dump, read, hashes
from verify_b1 import validate_worker

ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'roguelike'
FAULTS=('stage_created','first_scene','payload:meta.json','payload:player.json','payload:world.json',
        'manifest_written','generation_ready','backup_written','head_written','published')


def source_manifest():
    result = {}
    json_roots = (GAME/'data', GAME/'docs/examples',
                  ROOT/'tools/critical_fix_regressions/fixtures')
    for base in ('roguelike', 'tools'):
        for p in (ROOT/base).rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts or 'saves' in p.parts:
                continue
            included = p.suffix in ('.py', '.js', '.css') or (
                p.suffix == '.json' and any(p.is_relative_to(root) for root in json_roots))
            if included:
                result[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    painter = ROOT/'layout_painter.html'
    result[painter.relative_to(ROOT).as_posix()] = hashlib.sha256(painter.read_bytes()).hexdigest()
    corrections = ROOT/'evidence/worldgen-g2/data-corrections.json'
    result[corrections.relative_to(ROOT).as_posix()] = hashlib.sha256(corrections.read_bytes()).hexdigest()
    return result


def main(include_c=False, include_d=False):
    include_c = include_c or include_d
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only',choices=['b3','b1','b2','diagnostic'] + (['c'] if include_c else []) + (['d'] if include_d else []))
    ap.add_argument('--case',help='Optional single scenario/variant; partial runs never certify completion')
    args=ap.parse_args()
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    prefix='d' if include_d else ('c' if include_c else 'b3')
    run=ROOT/'.baseline'/(prefix+'-'+stamp+'-'+uuid.uuid4().hex[:8]);run.mkdir(parents=True)
    dump(run/'disposable-b3.json',{'kind':'test saves and evidence only','production_source':str(GAME)})
    report=dict(run_id=run.name,source=source_manifest(),workers=[],checks=[],only=args.only,case=args.case,
                source_policy='All workers import production main in place; only disposable save data is cloned.',
                command=sys.argv,python=sys.version,branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
                base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    assert report['branch']=='main','B3 must run against production main'
    writers=[]
    def check(case,name,expected,observed):
        report['checks'].append(dict(case=case,property=name,expected=expected,observed=observed,passed=expected==observed))
    if not args.only and not args.case:
        for mode in ('zero','missing','stale','phase','crash','timeout','false'):
            control=dict(run_id=run.name,scenario='runner-negative',phase=mode,flavor='selfcheck')
            output=run/('negative-'+mode+'.json')
            command=[sys.executable,str(ROOT/'tools/verify_b1.py'),'--selfcheck-child',mode,str(output),json.dumps(control)]
            try:
                proc=subprocess.run(command,cwd=run,capture_output=True,text=True,timeout=.2 if mode=='timeout' else 10)
                code,timeout,stdout,stderr=proc.returncode,False,proc.stdout,proc.stderr
            except subprocess.TimeoutExpired as error:
                code,timeout,stdout,stderr=None,True,str(error.stdout),str(error.stderr)
            error=validate_worker(read(output) if output.exists() else None,control,code,timeout)
            validation_command=[sys.executable,str(ROOT/'tools/verify_b1.py'),'--validate-evidence',str(output),json.dumps(control),str(code),str(timeout)]
            validated=subprocess.run(validation_command,cwd=run,capture_output=True,text=True,timeout=10)
            check('H03',mode+' returns a failed acceptance process',1,validated.returncode)
            check('H03',mode+' names the failure',True,bool(error) and error in validated.stdout)
            report.setdefault('runner_negative_controls',[]).append(dict(mode=mode,command=command,cwd=str(run),exit_code=code,
                timeout=timeout,stdout=stdout,stderr=stderr,validation_command=validation_command,validation_exit_code=validated.returncode,reason=error))
    def execute(suite,scenario,variant,phase,writer=None,legacy=False):
        if args.only and args.only!=suite:return None
        if args.case and args.case not in (scenario,scenario+'/'+variant):return None
        key='-'.join((suite,scenario,variant.replace(':','_'),phase))
        work=run/key;work.mkdir();saves=work/'saves';slot=saves/'slot_0'
        job=dict(run_id=run.name,suite=suite,scenario=scenario,variant=variant,phase=phase,flavor='candidate',
                 run_root=str(run),game=str(GAME),save_root=str(saves),result=str(work/'result.json'),
                 debug=(suite=='b1' and scenario=='journey' and variant not in ('nondebug','needs_f9')) or variant=='debug-delete')
        if writer:
            wjob,wresult=writer
            shutil.copytree(Path(wjob['save_root'])/'slot_0',slot)
            check('B3-H',key+' exact writer bytes',hashes(Path(wjob['save_root'])/'slot_0'),hashes(slot))
            job['expected']=wjob['result']
            if suite=='diagnostic' and variant=='lurker':job['payload']=str(Path(wjob['result']).parent/'lurker.json')
        elif legacy:
            slot.mkdir(parents=True)
            with zipfile.ZipFile(ROOT/'evidence/b3-before/legacy-b2.zip') as z:
                for name in z.namelist():
                    assert not Path(name).is_absolute() and '..' not in Path(name).parts
                z.extractall(slot)
            check('B3-H','real preserved B2 legacy bytes',read(ROOT/'evidence/b3-before/result.json')['legacy_checkpoint'],hashes(slot))
        else:
            slot.mkdir(parents=True)
            dump(slot/'world.json',{'seed':SEED})
        dump(work/'job.json',job)
        cmd=[sys.executable,str(ROOT/'tools/b3_worker.py'),str(work/'job.json')]
        started=time.monotonic()
        try:
            proc=subprocess.run(cmd,cwd=GAME,env=dict(os.environ,**ENV),capture_output=True,text=True,timeout=180)
            process=dict(command=cmd,cwd=str(GAME),environment=ENV,exit_code=proc.returncode,
                         stdout=proc.stdout,stderr=proc.stderr,seconds=time.monotonic()-started)
        except subprocess.TimeoutExpired as error:
            process=dict(command=cmd,cwd=str(GAME),exit_code=None,timeout=True,seconds=time.monotonic()-started,
                         stdout=str(error.stdout),stderr=str(error.stderr))
        result=read(work/'result.json') if (work/'result.json').exists() else {}
        crash=phase=='crash'
        error=validate_worker(result or None,job,process['exit_code'],process.get('timeout',False)) if not crash else None
        valid=(process['exit_code']==91 and result.get('expected_exit')==91 and bool(result.get('crash_point')) and bool(result.get('imported_sources'))) if crash else (
            error is None and result.get('passed') is True and all(c.get('expected')==c.get('observed') for c in result.get('checks',[])))
        valid=valid and all(result.get(k)==job[k] for k in ('run_id','suite','scenario','variant','phase','flavor'))
        if result.get('imported_sources'):
            for row in result['imported_sources'].values():
                valid=valid and row['sha256']==report['source'].get('roguelike/'+row['relative']) and Path(row['path']).is_relative_to(GAME)
        else: valid=False
        if writer and result.get('pid'):
            check('B3-H',key+' independent process',True,result['pid']!=writer[1].get('pid'))
        report['workers'].append(dict(key=key,job=job,process=process,result=result,valid=valid,validation_error=error))
        check('B3-H',key+' completed bounded contract',True,valid)
        print(key, 'PASS' if valid else 'FAIL', result.get('error',''),flush=True)
        dump(run/'progress.json',dict(completed=len(report['workers']),failed=[w['key'] for w in report['workers'] if not w['valid']]))
        if not valid:
            dump(run/'results.json',report)
            return None
        if phase=='write':writers.append((job,hashes(slot)))
        return job,result
    for suite,groups in (
        ('b1',(('scenes',('surface','submap')),('gear',('empty','jerky','gear','first','second','reordered','inactive','burnout')),
               ('lurker',('dormant','awake','pending','owners')))),
        ('b2',(('components',('filled','empty')),('items',('distinct',)),('actors',('modified',))))):
        for scenario,variants in groups:
            for variant in variants:
                writer=execute(suite,scenario,variant,'write')
                if writer:execute(suite,scenario,variant,'read',writer)
                execute(suite,scenario,variant,'same')
    for variant in ('versions','fields','scenes','bootstrap'):execute('b1','format',variant,'same')
    execute('b2','processing','owners','same')
    execute('b2','format','contract','same')
    for variant in ('movement','transfer','combat','text','processing','stairs','boundary','debug','needs_f9'):
        execute('b1','journey',variant,'loop')
    for suite,variants in (('b1',('nondebug',)),('b2',('effects','needs','rain','processing'))):
        for variant in variants:
            writer=execute(suite,'journey',variant,'write')
            if writer:execute(suite,'journey',variant,'read',writer)
    for variant in ('scenes','empty','empty_slots','equipped','lurker'):
        writer=execute('diagnostic','original',variant,'write')
        if writer:execute('diagnostic','original',variant,'read',writer)
    writer=execute('b3','coherence','owners','write')
    if writer:execute('b3','coherence','owners','read',writer)
    execute('b3','coherence','owners','same')
    writer=execute('b3','fault','canonical','write')
    for point in FAULTS:
        if writer:
            crash=execute('b3','fault',point,'crash',writer)
            if crash:execute('b3','fault',point,'read',crash)
    for point in ('stage_created','head_written','published'):
        crash=execute('b3','initial-fault',point,'crash')
        if crash:execute('b3','initial-fault',point,'read',crash)
    for variant in ('pointer','active','inactive','manifest','semantic','rollback','all-bad'):
        execute('b3','recovery',variant,'same')
    for scenario in ('io','slots','concurrency','journey'):execute('b3',scenario,'contract','loop' if scenario=='journey' else 'same')
    execute('b3','journey','debug-delete','loop')
    execute('b3','legacy','b2','read',legacy=True)
    if include_c:
        for variant in ('ownership','containers','crafting','production'):
            execute('c','contract',variant,'same')
        writer=execute('c','roundtrip','owners','write')
        if writer:execute('c','roundtrip','owners','read',writer)
        execute('c','roundtrip','owners','same')
        for variant in ('equipment','take-all','container','craft'):
            execute('c','journey',variant,'loop')
    if include_d:
        for variant in ('armor','coating','suppression','disruption','auras','confirmation','targeting','movement','owners'):
            execute('d','contract',variant,'same')
        writer=execute('d','roundtrip','effects','write')
        if writer:execute('d','roundtrip','effects','read',writer)
        execute('d','roundtrip','effects','same')
        for variant in ('confirmation','throw','movement','combat'):
            execute('d','journey',variant,'loop')
    for job,before in writers:
        check('B3-H',job['scenario']+job['variant']+' canonical writer immutable',before,hashes(Path(job['save_root'])/'slot_0'))
    check('B3-H','source stayed unchanged throughout gate',report['source'],source_manifest())
    before=read(ROOT/'evidence/b3-before/result.json')
    check('H01','two B3 defects reproduced before implementation',True,before['passed'] and len(before['checks'])>=5)
    if include_c:
        c_before=read(ROOT/'evidence/c-before/result.json')
        drop_before=read(ROOT/'evidence/c-before/equipped-drop.json')
        check('C-01','accepted B3 equipped-drop defect actually reproduced',True,
              drop_before['selected_tests_passed'] and any(d['id']=='C-DROP-EQUIPPED' for d in drop_before['deferred']))
        check('C-02','additional ownership defects actually reproduced before edits',True,
              c_before['passed'] and len(c_before['checks'])>=5 and c_before['commit']==drop_before['base_commit'])
    if include_d:
        before_d=read(ROOT/'evidence/d-before/result.json')
        check('D-01','accepted C defects reproduced before edits',True,
              before_d['passed'] and len(before_d['checks'])==8 and before_d['commit']=='288c70bb2105fc7770fa2c311cb983617bed933c')
    if not args.only and not args.case:
        required=[]
        for suite,scenario,variants in (
            ('b1','scenes',('surface','submap')),('b1','gear',('empty','jerky','gear','first','second','reordered','inactive','burnout')),
            ('b1','lurker',('dormant','awake','pending','owners')),('b2','components',('filled','empty')),
            ('b2','items',('distinct',)),('b2','actors',('modified',)),('b3','coherence',('owners',))):
            required += [(suite,scenario,v,p) for v in variants for p in ('write','read','same')]
        required += [('b1','format',v,'same') for v in ('versions','fields','scenes','bootstrap')]
        required += [('b1','journey',v,'loop') for v in ('movement','transfer','combat','text','processing','stairs','boundary','debug','needs_f9')]
        required += [(s,'journey',v,p) for s,vs in (('b1',('nondebug',)),('b2',('effects','needs','rain','processing'))) for v in vs for p in ('write','read')]
        required += [('b2','processing','owners','same'),('b2','format','contract','same')]
        required += [('diagnostic','original',v,p) for v in ('scenes','empty','empty_slots','equipped','lurker') for p in ('write','read')]
        required += [('b3','fault','canonical','write')]
        required += [('b3','fault',v,p) for v in FAULTS for p in ('crash','read')]
        required += [('b3','initial-fault',v,p) for v in ('stage_created','head_written','published') for p in ('crash','read')]
        required += [('b3','recovery',v,'same') for v in ('pointer','active','inactive','manifest','semantic','rollback','all-bad')]
        required += [('b3',s,'contract','loop' if s=='journey' else 'same') for s in ('io','slots','concurrency','journey')]
        required += [('b3','journey','debug-delete','loop'),('b3','legacy','b2','read')]
        if include_c:
            required += [('c','contract',v,'same') for v in ('ownership','containers','crafting','production')]
            required += [('c','roundtrip','owners',p) for p in ('write','read','same')]
            required += [('c','journey',v,'loop') for v in ('equipment','take-all','container','craft')]
        if include_d:
            required += [('d','contract',v,'same') for v in ('armor','coating','suppression','disruption','auras','confirmation','targeting','movement','owners')]
            required += [('d','roundtrip','effects',p) for p in ('write','read','same')]
            required += [('d','journey',v,'loop') for v in ('confirmation','throw','movement','combat')]
        actual=[tuple(w['job'][k] for k in ('suite','scenario','variant','phase')) for w in report['workers']]
        check('H03','all independently enumerated required workers executed',sorted(required),sorted(actual))
        # C now has a positive drop oracle. Retain the separate UI observation.
        prior=read(ROOT/'evidence/b2-deferred-results.json')
        wanted={d['id']:d['symptom'] for d in prior if d['id'] == 'UI-TEXT-HEIGHT'}
        current={d['id']:d['symptom'] for w in report['workers'] for d in w['result'].get('defects',[])}
        check('H03','unchanged out-of-scope defect signatures',wanted,current)
        check('B02','checkpoint generation defect repaired',True,all(w['valid'] for w in report['workers'] if w['job']['scenario']=='coherence'))
        check('B03','dirty hot-owner defect repaired',True,all(w['valid'] for w in report['workers'] if w['job']['scenario']=='coherence'))
        check('B2-09','complete B1 parameter regression set',57,sum(w['job']['suite']=='b1' and w['valid'] for w in report['workers']))
        check('B2-H','all current worker source/phase/assertion bindings pass',True,all(w['valid'] for w in report['workers']))
    checks=report['checks']+[c for w in report['workers'] if w['job']['phase']!='crash' for c in w['result'].get('checks',[])]
    if not args.only and not args.case:
        required_ids={c['id'] for c in read(ROOT/'tools/b1_acceptance_matrix.json')['cases']}
        required_ids |= {'B3-'+str(n).zfill(2) for n in range(1,10)} | {'B3-H'}
        required_ids |= {'B2-'+str(n).zfill(2) for n in range(1,10)} | {'B2-H'}
        if include_c:
            required_ids |= {'C-'+str(n).zfill(2) for n in range(1,9)}
        if include_d:
            required_ids |= {'D-'+str(n).zfill(2) for n in range(1,12)}
        check('H03','every required case collected nonzero evidence',[],sorted(required_ids-{c['case'] for c in checks}))
        check('H01','original diagnostic properties still pass',32,sum(c['case']=='original' and c['passed'] for c in checks))
        checks=report['checks']+[c for w in report['workers'] if w['job']['phase']!='crash' for c in w['result'].get('checks',[])]
    report['totals']=dict(checks=len(checks),passed=sum(c['passed'] for c in checks),failed=sum(not c['passed'] for c in checks),workers=len(report['workers']))
    report['coverage']={k:dict(checks=sum(c['case']==k for c in checks),passed=all(c['passed'] for c in checks if c['case']==k)) for k in sorted({c['case'] for c in checks})}
    report['deferred']=[d for w in report['workers'] for d in w['result'].get('defects',[])]
    selected=bool(report['workers']) and all(w['valid'] for w in report['workers']) and all(c['passed'] for c in checks)
    report['selected_tests_passed']=selected
    report['passed']=selected and not args.only and not args.case
    dump(run/'results.json',report)
    dump(ROOT/('evidence/'+prefix+'-latest.json'),dict(result=str(run/'results.json'),passed=report['passed'],selected_tests_passed=selected))
    print(json.dumps(dict(result=str(run/'results.json'),passed=report['passed'],selected_tests_passed=selected,totals=report['totals'])),flush=True)
    return 0 if selected else 1


if __name__=='__main__':raise SystemExit(main())
