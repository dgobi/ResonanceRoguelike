"""Complete serial release gates against one frozen G7 input revision."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from verify_b3 import source_manifest

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=False)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();source=source_manifest()
    commands=[('guard',['tools/verify_g7_guard.py','--evidence',out/'guard/results']),
        ('focused',['tools/critical_fix_regressions/verify_fixes.py','--game','roguelike','--evidence',out/'focused/results']),
        ('browser',['tools/verify_structure_editor.py','--evidence',out/'browser/results']),
        ('authoring',['tools/verify_g7_authoring.py','--evidence',out/'authoring/results']),
        ('catalog',['tools/structure_authoring.py','--catalog','--output',out/'catalog/catalog.json']),
        ('catalog-check',['tools/structure_authoring.py','--check-editor-catalog']),
        ('diagnostic',['tools/worldgen_g7_diagnostic.py','--journey','--evidence',out/'diagnostic/results']),
        ('visuals',['tools/g6_visuals.py','--diagnostic',out/'diagnostic/results']),
        ('production',['tools/verify_d.py','--evidence',out/'production/results'])]
    results=[]
    for name,command in commands:
        print('START '+name,flush=True);argv=[sys.executable,'-X','utf8',str(ROOT/'tools/g7_evidence.py'),'--output',str(out/name),'--','python','-X','utf8',*map(str,command)]
        proc=subprocess.run(argv,cwd=ROOT);receipt=json.loads((out/name/'receipt.json').read_text())
        results.append(dict(gate=name,command=argv,exit_code=proc.returncode,receipt=str(out/name/'receipt.json'),committed_inputs_reconciled=receipt['committed_inputs_reconciled']))
        report=dict(input_commit=commit,source=source,source_stable=source==source_manifest(),results=results,passed=len(results)==len(commands) and all(r['exit_code']==0 and r['committed_inputs_reconciled'] for r in results) and source==source_manifest())
        (out/'release.json').write_text(json.dumps(report,indent=2)+'\n');print('END '+name+' '+str(proc.returncode),flush=True)
        if proc.returncode:return proc.returncode
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
