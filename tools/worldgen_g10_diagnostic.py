"""Bounded three-seed preservation, production comparisons and author workflow."""
import argparse
import contextlib
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
BEFORE=ROOT/'evidence/worldgen-g10/before'


def write(out,name,value):
    (out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def workflow(out, policy_identity):
    commands=[]
    def invoke(args,expect=0):
        command=[sys.executable,'-X','utf8',str(ROOT/'tools/wilderness_preview.py'),*map(str,args)]
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120)
        commands.append(dict(command=command,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        assert result.returncode==expect,commands[-1]
    with tempfile.TemporaryDirectory(prefix='resonance-g10-install-rehearsal-',dir=out) as temp:
        tmp=Path(temp);data=tmp/'data';shutil.copytree(ROOT/'roguelike/data',data)
        installed=data/'generation/wilderness_profiles.json';backup=installed.read_bytes()
        draft=json.loads(backup);draft['profiles']['forest']['scale']=28
        candidate=tmp/'draft.json';candidate.write_text(json.dumps(draft))
        args=['--chunk','73','99','--size','2','1']
        invoke([*args,'--profile',candidate,'--output',out/'draft-preview.json'])
        installed.write_bytes(candidate.read_bytes())
        invoke([*args,'--data-root',data,'--output',out/'installed-preview.json'])
        a=json.loads((out/'draft-preview.json').read_text());b=json.loads((out/'installed-preview.json').read_text())
        assert a['policy_identity']==b['policy_identity']!=policy_identity
        for left,right in zip(a['scenes'],b['scenes']):
            assert left['complete_terrain_identity']==right['complete_terrain_identity']
            assert left['decor']==right['decor'] and left['native_ids']==right['native_ids']
        assert (out/'draft-preview.png').read_bytes()==(out/'installed-preview.png').read_bytes()
        installed.write_bytes(backup)
        invoke([*args,'--data-root',data,'--output',out/'recovered-preview.json'])
        assert json.loads((out/'recovered-preview.json').read_text())['policy_identity']==policy_identity
        # All collision negatives exercise the public CLI before generation.
        invoke([*args,'--profile',candidate,'--output',candidate],1)
        invoke([*args,'--output',ROOT/'roguelike/data/generation/wilderness_profiles.json'],1)
        report=tmp/'collision.json';image=tmp/'collision.png';report.write_text('owner artifact');os.link(report,image)
        invoke([*args,'--output',report,'--image',image],1)
        assert report.read_text()=='owner artifact'
        alias=tmp/'installed-alias.json';os.link(ROOT/'roguelike/data/generation/wilderness_profiles.json',alias)
        invoke([*args,'--output',alias],1)
        symlink=None
        try:
            link=tmp/'linked-data';os.symlink(data,link,target_is_directory=True)
        except OSError as error:
            symlink=dict(symbolic_link_created=False,symbolic_link_error=str(error))
            if os.name=='nt':
                command=['powershell','-NoProfile','-Command',
                    'New-Item -ItemType Junction -Path $env:G10_LINK -Target $env:G10_TARGET -ErrorAction Stop | Out-Null']
                junction=subprocess.run(command,env=dict(os.environ,G10_LINK=str(link),G10_TARGET=str(data)),capture_output=True,text=True,timeout=20)
                assert junction.returncode==0,junction.stderr
                assert link.resolve()==data.resolve()
                invoke([*args,'--data-root',data,'--output',link/'generation/wilderness_profiles.json'],1)
                symlink.update(exercised=True,junction_created=True,junction_rejected=True)
            else:raise
        else:
            invoke([*args,'--data-root',data,'--output',link/'generation/wilderness_profiles.json'],1)
            symlink=dict(exercised=True,symbolic_link_created=True,rejected=True)
        write(out,'workflow.json',dict(passed=True,draft_installed_identical=True,backup_recovery=True,
            output_collisions_rejected=4,symlink=symlink,commands=commands,
            controls='Intentional install/recovery performed only in a disposable data catalog. No runtime/code checkout copied and no installed owner input changed.'))


def run(out, include_workflow=True):
    from test_effect_persistence import load_data,make_engine
    from world.world_map import WorldMap
    from generation.world_gen import generate_world
    from generation.context import GenerationContext
    from generation.placement import digest
    from generation.wilderness import materialize,sample
    from generation.region_gen import generate_region
    from engine.save_manager import _serialize_world
    from engine.scene_generation import create_surface
    from wilderness_preview import scene_summary,render_area
    from g10_play import render
    from g1_support import fingerprint
    import numpy as np
    baseline=json.loads((BEFORE/'baseline.json').read_text());data=load_data();runs=[]
    out.mkdir(parents=True,exist_ok=True)
    for seed in (0,20261023,29417):
        prior=next(r for r in baseline['runs'] if r['seed']==seed)
        w=WorldMap(128,128);w.seed=seed;started=time.perf_counter();generate_world(w,data,random.Random(seed));planning=time.perf_counter()-started
        original=json.loads(gzip.decompress((BEFORE/f'world-{seed}.json.gz').read_bytes()))
        current=_serialize_world(w);current.pop('surface_schema');current.pop('surface_policy')
        assert json.loads(json.dumps(current))==original
        assert digest(w.plan)==prior['plan_identity'] and not any(c.visited for c in w.chunks.values())
        row=dict(seed=seed,complete_G9_plan_preserved=True,coarse_geography_and_owners_exact=True,
            plan_identity=digest(w.plan),plan_bytes=len(json.dumps(w.plan,separators=(',',':')).encode()),
            policy_bytes=len(json.dumps(w.surface_policy,separators=(',',':')).encode()),policy_identity=w.surface_policy['identity'],
            scenes_at_plan_completion=0,planning_seconds=planning,preedit_planning_seconds=prior['planning_seconds'],scenes=[])
        if seed==20261023:
            e=make_engine(data);e.world_map=w;legacy=copy.copy(w);legacy.surface_schema=0;legacy.surface_policy=None
            for old in prior['scenes']:
                xy=old['chunk'];ch=w.get(*xy);context=GenerationContext(w.seed,ch.seed,(*xy,None))
                # Pair old and new base + complete costs serially on this machine.
                base=copy.deepcopy(ch);base.submaps=[];base.town_data=None;base.edges={k:[] for k in base.edges}
                t=time.perf_counter();generate_region(base,80,43,data.terrain,data=data,context=context,base_only=True);oldbase=time.perf_counter()-t
                t=time.perf_counter();m,_=materialize(w,ch,data,context);newbase=time.perf_counter()-t
                t=time.perf_counter();before=create_surface(legacy,ch,data,e.item_factory,e.creature_factory,80,43);oldtime=time.perf_counter()-t
                assert fingerprint(before.local_map,before.actors)==old['fingerprint']
                t=time.perf_counter();r=create_surface(w,ch,data,e.item_factory,e.creature_factory,80,43);newtime=time.perf_counter()-t
                e.local_map=r.local_map;e.entities=[e.player,*r.actors];e.player.x,e.player.y=r.spawn;e.world_x,e.world_y=xy
                image=f'{old["biome"]}-{xy[0]}-{xy[1]}-after.png';render(e,out/image,f'G10 {old["biome"]} {xy}',revealed=True)
                row['scenes'].append(dict(chunk=xy,biome=old['biome'],before_image=str((BEFORE/old['image']).relative_to(ROOT)),after_image=image,
                    before_fingerprint=old['fingerprint'],after_fingerprint=fingerprint(r.local_map,r.actors),before_terrain=old['terrain'],
                    costs=dict(preedit_complete_seconds=old['seconds'],paired_legacy_base_seconds=oldbase,paired_new_base_seconds=newbase,
                               paired_legacy_complete_seconds=oldtime,paired_new_complete_seconds=newtime),**scene_summary(r,data)))
            areas=[]
            for name,xy in [('forest-open',(73,99)),('wet-dry',(78,105)),('ash-edge',(72,102)),('rocky',(63,63))]:
                left=render_area(legacy,data,*xy,2,2,image_path=out/f'{name}-before.png',label='G9')
                right=render_area(w,data,*xy,2,2,image_path=out/f'{name}-after.png',label='G10')
                reference=sample(w,w.surface_policy,xy[0]*80,xy[1]*43,160,86)
                for dx,dy in ((0,0),(1,0),(0,1),(1,1)):
                    independent=sample(w,w.surface_policy,(xy[0]+dx)*80,(xy[1]+dy)*43)
                    for key in ('terrain','biome','cover','patch','wet','moisture','elevation'):
                        np.testing.assert_array_equal(independent[key],reference[key][80*dx:80*(dx+1),43*dy:43*(dy+1)])
                areas.append(dict(name=name,origin=xy,size=[2,2],before=left,after=right,base_field_crop_equal=True,
                    before_image=f'{name}-before.png',after_image=f'{name}-after.png'))
            write(out,'areas.json',dict(passed=True,areas=areas,visibility='Controlled complete reveal for comparison, actual populated production renderer. Natural tile pixels touch across both axes.'))
            if include_workflow:workflow(out,w.surface_policy['identity'])
        runs.append(row)
    report=dict(passed=True,runs=runs,cost_scope='Serial same-machine G9/new-policy base and complete scene pairs; pre-edit timings also retained. No allocation or iteration over explored scene caches in the sampler, fixed maximum rectangle and one-chunk metadata halo; no recursive materialization.',
                declared_halo=1,reference_crop_continuity=True)
    write(out,'run.json',report)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--skip-workflow',action='store_true');a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    with (out/'output.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):run(out,not a.skip_workflow)
    print(json.dumps(dict(passed=True,evidence=str(out))))


if __name__=='__main__':main()
