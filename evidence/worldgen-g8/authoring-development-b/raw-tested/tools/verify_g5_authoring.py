"""Execute G5 recipes with guarded drafts and exact command/output receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from verify_b3 import source_manifest

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--evidence',type=Path,required=True);args=ap.parse_args()
    out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True);records=[];source=source_manifest()
    def run(command,files=(),expected=0,cwd=ROOT):
        result=subprocess.run(command,cwd=cwd,text=True,encoding='utf-8',capture_output=True,timeout=120)
        records.append(dict(argv=[str(v) for v in command],cwd=str(cwd),exit_code=result.returncode,expected_exit=expected,
            stdout=result.stdout,stderr=result.stderr,output_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.exists()}))
        if result.returncode!=expected:raise AssertionError(result.stdout+result.stderr)
    def cli(arguments,output=None,expected=0):
        command=[sys.executable,'-X','utf8',str(ROOT/'tools/structure_authoring.py'),*map(str,arguments)]
        if output:command+=['--output',str(output)]
        run(command,[output] if output else [],expected)
    try:
        with tempfile.TemporaryDirectory(prefix='g5-authoring-') as temporary:
            temp=Path(temporary);drafts=temp/'authoring';drafts.mkdir()
            for aid,category,contexts,seed in [('g5_service_house','residential',['grid','roadside'],20261023),
                    ('g5_workshop','commercial',['grid'],20261023),('g5_landmark','wilderness',['landmark'],29417)]:
                original=ROOT/f'roguelike/docs/examples/{aid}.json';draft=drafts/(aid+'.json')
                command=['powershell','-NoProfile','-Command',f"if (-not (Test-Path -LiteralPath '{draft}')) {{ Copy-Item -LiteralPath '{original}' -Destination '{draft}' }}"]
                run(command,[draft]);raw=json.loads(draft.read_text());raw['owner_sentinel']='G5 edit survives repeated initialization'
                draft.write_text(json.dumps(raw,indent=2)+'\n');before=draft.read_bytes()
                records.append(dict(action='deliberate draft metadata edit',path=str(draft),sha256=hashlib.sha256(before).hexdigest()))
                run(command,[draft]);run(command,[draft]);assert draft.read_bytes()==before
                cli([draft,'--route','ordinary_building','--category',category,'--orientations'],out/(aid+'-orientations.json'))
                for context in contexts:cli([draft,'--planned','--category',category,'--context',context,'--seed',0 if aid=='g5_service_house' and context=='roadside' else seed],out/(aid+'-'+context+'.json'))
                assert draft.read_bytes()==before
            # A real unsuccessful context, then the same unchanged draft succeeds
            # in its declared context above; no permissive geometry rewrite.
            cli([drafts/'g5_landmark.json','--planned','--category','wilderness','--context','grid'],expected=1)
            cli(['--world-plan','--selection-config',ROOT/'roguelike/docs/examples/g5_selection_example.json'],out/'tuned-world.json')
            # Deliberate installation is exercised in a disposable DATA catalog,
            # never in another game/source checkout or the owner's live assets.
            catalog=temp/'data';shutil.copytree(ROOT/'roguelike/data',catalog)
            destination=catalog/'buildings/residential/g5_service_house.json';shutil.copyfile(drafts/'g5_service_house.json',destination)
            policy=json.loads((catalog/'generation/settlement_profiles.json').read_text())
            policy['profiles']['grid']['roles']['residential'].append(dict(asset='g5_service_house',weight=1,max_per_settlement=4))
            (catalog/'generation/settlement_profiles.json').write_text(json.dumps(policy,indent=2)+'\n')
            records.append(dict(action='deliberate install and role registration in disposable data catalog',path=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
            cli(['--data-root',catalog,'--catalog'],out/'installed-catalog.json')
            cli(['--data-root',catalog,'--world-plan'],out/'installed-world.json')
            cli(['--catalog'],out/'catalog.json');cli(['--check-editor-catalog'])
        report=dict(passed=True,records=records,source=source,source_stable=source==source_manifest())
    except Exception as error:report=dict(passed=False,error=str(error),records=records,source=source,source_stable=source==source_manifest())
    (out/'commands.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k in ('passed','error','source_stable')}))
    return 0 if report['passed'] and report['source_stable'] else 1


if __name__=='__main__':raise SystemExit(main())
