"""Execute the documented draft workflow; preserve edits and record exact commands."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    from verify_b3 import source_manifest
    source=source_manifest();records=[]
    def run(argv,files=(),cwd=ROOT):
        result=subprocess.run(argv,cwd=cwd,capture_output=True,text=True,encoding='utf-8',timeout=90)
        records.append(dict(argv=[str(v) for v in argv],cwd=str(cwd),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr,
                            output_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.exists()}))
        if result.returncode:raise AssertionError(result.stderr or result.stdout)
    try:
        with tempfile.TemporaryDirectory(prefix='g4-authoring-') as temporary:
            drafts=Path(temporary)/'authoring';drafts.mkdir()
            for asset,category,contexts,seed in [('author_frontage_a','residential',['grid','roadside'],20261023),('author_landmark_a','wilderness',['landmark'],29417)]:
                original=ROOT/f'roguelike/docs/examples/{asset}.json';draft=drafts/(asset+'.json')
                # Exact safe PowerShell initialization, executed both before and after editing.
                command=f"if (-not (Test-Path -LiteralPath '{draft}')) {{ Copy-Item -LiteralPath '{original}' -Destination '{draft}' }}"
                run(['powershell','-NoProfile','-Command',command],[draft])
                edited=json.loads(draft.read_text());edited['owner_sentinel']='G4 edited draft survives repeated initialization'
                draft.write_text(json.dumps(edited,indent=2)+'\n');before=draft.read_bytes()
                records.append(dict(action='edit/export fixture',path=str(draft),sha256=hashlib.sha256(before).hexdigest(),sentinel=edited['owner_sentinel']))
                run(['powershell','-NoProfile','-Command',command],[draft]);assert draft.read_bytes()==before
                output=out/(asset+'-orientations.json')
                run([sys.executable,'-X','utf8',str(ROOT/'tools/structure_authoring.py'),str(draft),'--route','ordinary_building','--category',category,'--orientations','--output',str(output)],[output])
                for context in contexts:
                    output=out/(asset+'-'+context+'.json')
                    run([sys.executable,'-X','utf8',str(ROOT/'tools/structure_authoring.py'),str(draft),'--planned','--category',category,'--context',context,'--seed',str(seed),'--output',str(output)],[output])
                assert draft.read_bytes()==before
            output=out/'world-plan.json'
            run([sys.executable,'-X','utf8',str(ROOT/'tools/structure_authoring.py'),'--world-plan','--seed','20261023','--output',str(output)],[output])
            output=out/'catalog.json'
            run([sys.executable,'-X','utf8',str(ROOT/'tools/structure_authoring.py'),'--catalog','--output',str(output)],[output])
            run([sys.executable,'-X','utf8',str(ROOT/'tools/structure_authoring.py'),'--check-editor-catalog'])
        report=dict(passed=True,records=records,source=source,source_stable=source==source_manifest())
    except Exception as error:report=dict(passed=False,error=str(error),records=records,source=source,source_stable=source==source_manifest())
    (out/'commands.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k in ('passed','error','source_stable')}))
    return 0 if report['passed'] and report['source_stable'] else 1


if __name__=='__main__':raise SystemExit(main())
