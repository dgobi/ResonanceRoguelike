"""Sequential unfiltered G6 release gates against one frozen source identity."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from verify_b3 import source_manifest

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=False)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();source=source_manifest()
    commands=[
        ('focused',['tools/critical_fix_regressions/verify_fixes.py','--game','roguelike','--evidence',out/'focused/results']),
        ('browser',['tools/verify_structure_editor.py','--evidence',out/'browser/results']),
        ('authoring',['tools/verify_g6_authoring.py','--evidence',out/'authoring/results']),
        ('catalog',['tools/structure_authoring.py','--catalog','--output',out/'catalog/catalog.json']),
        ('catalog-check',['tools/structure_authoring.py','--check-editor-catalog']),
        ('diagnostic',['tools/worldgen_g6_diagnostic.py','--journey','--evidence',out/'diagnostic/results']),
        ('visuals',['tools/g6_visuals.py','--diagnostic',out/'diagnostic/results']),
        ('production',['tools/verify_d.py','--evidence',out/'production/results']),
        ('transform-after',['tools/critical_fix_regressions/fixtures/g6/probe_required_transform_search.py','--source',ROOT,'--output',out/'transform-after/result.json']),
        ('order-after',['tools/critical_fix_regressions/fixtures/g6/probe_selection_list_order.py','--source',ROOT,'--output',out/'order-after/result.json'])]
    results=[]
    for name,command in commands:
        print('START '+name,flush=True)
        argv=[sys.executable,'-X','utf8',str(ROOT/'tools/g6_evidence.py'),'--output',str(out/name),'--','python','-X','utf8',*map(str,command)]
        result=subprocess.run(argv,cwd=ROOT)
        results.append(dict(gate=name,argv=argv,exit_code=result.returncode,receipt=str(out/name/'receipt.json')))
        status=dict(input_commit=commit,source=source,source_stable=source==source_manifest(),results=results,
                    passed=len(results)==len(commands) and all(r['exit_code']==0 for r in results) and source==source_manifest())
        (out/'release.json').write_text(json.dumps(status,indent=2)+'\n')
        print('END '+name+' '+str(result.returncode),flush=True)
        if result.returncode:return result.returncode
    return 0 if status['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
