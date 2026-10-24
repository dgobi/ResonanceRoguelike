"""Serial standalone edition build, integrity, repeat, drift and real-reader gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parent;repo=root.parent;html=root/'Resonance_Owner_Wiki.html';env=dict(os.environ);dev=Path(os.environ['LOCALAPPDATA'])/'ResonanceAuthoring/python';env['PYTHONPATH']=str(dev)+os.pathsep+env.get('PYTHONPATH','');rows=[]
    def run(name,args):
        command=[sys.executable,'-X','utf8',*map(str,args)];r=subprocess.run(command,cwd=repo,env=env,capture_output=True,text=True,encoding='utf-8',timeout=180)
        (out/(name+'.txt')).write_text(r.stdout+r.stderr,encoding='utf-8');rows.append(dict(name=name,argv=command,exit_code=r.returncode,timeout_seconds=180));assert r.returncode==0,r.stdout+r.stderr
    try:
        run('dependencies',['-c','import sys,importlib.metadata,json; print(json.dumps(dict(python=sys.version,interpreter=sys.executable,dependencies={n:importlib.metadata.version(n) for n in ("mistune","playwright","pygame","tcod","numpy")})))'])
        run('contract',[root/'test_wiki_inputs.py','-v'])
        example=root/'examples/owner_cottage_a.json'
        for name,options in [('direct',['--route','ordinary_building','--orientations']),('grid',['--planned','--context','grid']),('roadside',['--planned','--context','roadside'])]:
            run('example-'+name,[repo/'tools/structure_authoring.py',example,'--category','residential',*options,'--output',out/('example-'+name+'.json')])
        for name,network in [('wiki',root/'examples/g9_country_network.json'),('guide',repo/'roguelike/docs/examples/g9_country_network.json')]:
            run('example-network-'+name,[repo/'tools/structure_authoring.py','--network-preview','--network-policy',network,'--seed','20261023','--output',out/('example-network-'+name+'.json')])
        run('build-a',[root/'build_wiki.py','--repo',repo]);first=hashlib.sha256(html.read_bytes()).hexdigest()
        run('drift-a',[root/'build_wiki.py','--repo',repo,'--check-drift'])
        run('build-b',[root/'build_wiki.py','--repo',repo]);second=hashlib.sha256(html.read_bytes()).hexdigest();assert first==second
        run('drift-b',[root/'build_wiki.py','--repo',repo,'--check-drift'])
        run('integrity',[root/'validate_wiki.py','--html',html,'--repo',repo,'--report',out/'integrity.json'])
        run('reader',[root/'verify_reader.py','--evidence',out/'reader'])
        passed=True;error=None
    except Exception as exc:passed=False;error=str(exc)
    (out/'edition.json').write_text(json.dumps(dict(passed=passed,error=error,commands=rows,html_sha256=hashlib.sha256(html.read_bytes()).hexdigest(),source_manifest=json.loads((root/'source-manifest.json').read_text())),indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=passed,error=error)));return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
