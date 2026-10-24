"""Five complete safe G9 workflows plus separately counted inherited consumers."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--skip-inherited',action='store_true',help='Development only; partial result is not a final release gate');a=p.parse_args();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True);rows=[]
    def run(argv,expected=0,workflow=None):
        args=list(map(str,argv));r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=900)
        rows.append(dict(workflow=workflow,command=args,cwd=str(ROOT),exit_code=r.returncode,expected=expected,timeout_seconds=900,stdout=r.stdout,stderr=r.stderr));assert r.returncode==expected,r.stdout+r.stderr
    def cli(options,name,workflow,expected=0):
        target=out/(name+'.json');run([sys.executable,'-X','utf8',ROOT/'tools/structure_authoring.py',*options,'--output',target],expected,workflow);return json.loads(target.read_text()) if target.exists() else None
    def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    try:
        original=cli(['--network-preview'],'ordinary',1);assert original['plan']['network']['accepted'] and original['materialized_scenes']==0
        sandbox=ROOT/'.baseline/g9-authoring';sandbox.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=sandbox) as temporary:
            temp=Path(temporary);draft=temp/'draft';cli(['--init-network',draft],'init',2);path=draft/'g9_country_network.json';policy=json.loads(path.read_text())
            tuned=dict(policy,max_added_fraction=.1);write(path,tuned);edited=path.read_bytes();cli(['--init-network',draft],'repeat-init',2);assert path.read_bytes()==edited
            reduced=cli(['--network-preview','--network-policy',path],'reduced',2);assert not reduced['plan']['network']['accepted']
            write(path,dict(policy,max_shortcuts=0));disabled=cli(['--network-preview','--network-policy',path],'disabled',3)
            assert disabled['plan']['version']==7 and disabled['status']=='disabled' and disabled['comparison']['baseline_identity']==original['comparison']['baseline_identity']
            assert disabled['comparison']['added_unique_centerline_steps']==0
            no_benefit=cli(['--network-preview','--seed','0'],'no-benefit',4);assert not no_benefit['plan']['network']['accepted']
            write(path,dict(policy,world_expansion_budget=1));exhausted=cli(['--network-preview','--network-policy',path],'exhausted',4);assert exhausted['status']=='global expansion budget exhausted'
            # All reports and images participate in the existing same-file,
            # hardlink/symlink, initializer and staged catalog preflight rules.
            before=path.read_bytes();run([sys.executable,ROOT/'tools/structure_authoring.py','--network-preview','--network-policy',path,'--output',path],1,4);assert path.read_bytes()==before
            for extension in ('.svg','.png'):
                alias=out/('collision'+extension);alias.hardlink_to(path)
                catalog=temp/('catalog'+extension+'.js');catalog.write_text('catalog sentinel');prior=catalog.read_bytes()
                run([sys.executable,ROOT/'tools/structure_authoring.py','--network-preview','--network-policy',path,'--refresh-editor-catalog','--editor-catalog',catalog,'--output',out/'collision.json'],1,4)
                assert path.read_bytes()==before and catalog.read_bytes()==prior and not (out/'collision.json').exists();alias.unlink()
            fresh=temp/'fresh';run([sys.executable,ROOT/'tools/structure_authoring.py','--init-network',fresh,'--output',fresh/'g9_country_network.json'],1,4);assert not fresh.exists()
            data=temp/'data';shutil.copytree(ROOT/'roguelike/data',data);installed=data/'generation/country_network.json';original_bytes=installed.read_bytes()
            sentinel=data/'g9-preserve-sentinel.txt';sentinel.write_bytes(b'unrelated authoring data')
            unchanged={p.relative_to(data).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in data.rglob('*') if p.is_file() and p!=installed}
            write(installed,dict(policy,max_shortcuts=0));off=cli(['--data-root',data,'--network-preview'],'installed-disabled',5);assert off['status']=='disabled'
            installed.write_bytes(original_bytes);on=cli(['--data-root',data,'--network-preview'],'reverted',5);assert on['plan']==original['plan']
            assert all(hashlib.sha256((data/name).read_bytes()).hexdigest()==value for name,value in unchanged.items())
            catalog=temp/'catalog.js';cli(['--data-root',data,'--refresh-editor-catalog','--editor-catalog',catalog],'catalog-refresh',5);cli(['--data-root',data,'--check-editor-catalog','--editor-catalog',catalog],'catalog-check',5)
            rows.append(dict(workflow=5,installed_reverted_exactly=True,unrelated_preserved=unchanged))
        if not a.skip_inherited:run([sys.executable,'-X','utf8',ROOT/'tools/verify_g8_authoring.py','--evidence',out/'inherited-g8'],workflow='inherited G8; its G5-G7 subruns counted separately')
        passed=True;error=None
    except Exception as exc:passed=False;error=str(exc)
    write(out/'workflows.json',dict(passed=passed,error=error,g9_top_level_workflows=5,inherited_executed=not a.skip_inherited,release_complete=passed and not a.skip_inherited,records=rows))
    print(json.dumps(dict(passed=passed,error=error)));return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
