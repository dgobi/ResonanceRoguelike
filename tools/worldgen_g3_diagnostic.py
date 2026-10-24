"""Bounded G3 production plans/scenes, measured G2-style legacy baseline and journey."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,default=ROOT/'evidence/worldgen-g4/diagnostic');p.add_argument('--journey',action='store_true');args=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    import config;config.DEBUG_MODE=False
    from test_effect_persistence import load_data
    from generation.world_gen import generate_world
    from generation.placement import digest
    from generation.plan_preview import plan_svg
    from generation.structure_preview import snapshot,render_svg
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from world.world_map import WorldMap
    from verify_b3 import source_manifest
    out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True);source=source_manifest()
    report={'declared_seeds':[0,20261023,29417],'sample_size':3,'source':source,'runs':[],'failures':[],'journey':None,
            'command':[sys.executable,*sys.argv],'cwd':str(Path.cwd()),'python':sys.version,'revision':'wg4'}
    data=load_data();log=io.StringIO()
    for seed in report['declared_seeds']:
        try:
            world=WorldMap(128,128);world.seed=seed;t=time.perf_counter();metrics={}
            with contextlib.redirect_stdout(log):generate_world(world,data,random.Random(seed),planning_metrics=metrics)
            elapsed=time.perf_counter()-t;plan=world.plan
            row={'seed':seed,'plan_identity':digest(plan),'planning_seconds':elapsed,'plan_bytes':len(json.dumps(plan,separators=(',',':')).encode()),'settlements':len(plan['settlements']),'placements':len(plan['placements']),'vacancies':sum(p['placement'] is None for p in plan['plots']),'crossings':len(plan['crossings']),'scenes_at_plan_completion':sum(c.visited for c in world.chunks.values()),'scenes':[]}
            report['runs'].append(row)
            from collections import Counter
            row['settlement_planning_seconds']=metrics['settlements']
            row['asset_repetition']=dict(Counter(p['asset'] for p in plan['placements']))
            row['plot_occupancy']=len(plan['placements'])/len(plan['plots'])
            row['metric_definitions']={'plot_occupancy':'occupied/all proposed plots including required landmark; historical frontage_coverage was the same number and is deprecated',
                                     'per_edge_detour_ratio':'polyline length / endpoint Manhattan distance; not shortest travel on the physical network'}
            row['per_edge_detour_ratio']={r['id']:sum(abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(r['points'],r['points'][1:]))/max(1,abs(r['points'][-1][0]-r['points'][0][0])+abs(r['points'][-1][1]-r['points'][0][1])) for r in plan['routes'] if r['kind']=='country'}
            from worldgen_g4_diagnostic import conditional_counts,detail_svg
            row['conditional_counts']=conditional_counts(plan,data)
            keys={(world.start_wx,world.start_wy)}|{tuple(xy) for s in plan['settlements'] for xy in s['members']}|{tuple(n['chunk']) for n in plan['nodes'] if n['id'] in ('landmark','capital-gateway')}
            for xy in sorted(keys):
                t=time.perf_counter()
                with contextlib.redirect_stdout(log):result=create_surface(world,world.get(*xy),data,ItemFactory(data),CreatureFactory(data),80,43)
                row['scenes'].append({'chunk':xy,'seconds':time.perf_counter()-t,'actors':len(result.actors),'items':sum(map(len,result.local_map.floor_objects.values())),
                                      'native_context':getattr(result.local_map,'native_generation_context',None),
                                      'functional_passes':result.local_map.functional_generation})
                if xy==tuple(next(n for n in plan['nodes'] if n['id']=='capital-gateway')['chunk']):
                    from generation.access import reachable
                    reached=reachable(result.local_map,result.spawn,data)
                    row['capital_gateway']={'chunk':xy,'arrival':result.spawn,'reachable_cells':len(reached),'all_road_cells_reachable':result.local_map.road_cells<=reached}
                    assert row['capital_gateway']['all_road_cells_reachable'] and (40,21) in reached
                if seed==20261023 and xy==tuple(plan['settlements'][0]['members'][0]):
                    view=snapshot(result.local_map,result.actors,data);view['access']=[]
                    (out/'grid-scene.svg').write_text(render_svg(view),encoding='utf-8')
                if seed==20261023 and xy==tuple(plan['settlements'][1]['members'][0]):
                    view=snapshot(result.local_map,result.actors,data);view['access']=[]
                    (out/'roadside-scene.svg').write_text(render_svg(view),encoding='utf-8')
            if seed==20261023:
                import gzip
                old=json.loads(gzip.decompress((ROOT/'tools/critical_fix_regressions/fixtures/g3_plan_20261023.json.gz').read_bytes()))
                for form in ('grid','roadside'):
                    settlement=next(s for s in plan['settlements'] if s['form']==form)
                    (out/(form+'-plan.svg')).write_text(detail_svg(plan,settlement),encoding='utf-8')
                    (out/(form+'-before-plan.svg')).write_text(detail_svg(old,next(s for s in old['settlements'] if s['form']==form)),encoding='utf-8')
            (out/f'plan-{seed}.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
            (out/f'plan-{seed}.svg').write_text(plan_svg(plan),encoding='utf-8')
            baseline=WorldMap(128,128);baseline.seed=seed;t=time.perf_counter()
            with contextlib.redirect_stdout(log):generate_world(baseline,data,random.Random(seed),plan_mode='legacy')
            row['legacy_macro_seconds']=time.perf_counter()-t
            xy=min(baseline.town_chunks);t=time.perf_counter()
            with contextlib.redirect_stdout(log):create_surface(baseline,baseline.get(*xy),data,ItemFactory(data),CreatureFactory(data),80,43)
            row['legacy_town_scene_seconds']=time.perf_counter()-t
        except Exception as error:report['failures'].append({'seed':seed,'error':str(error),'traceback':traceback.format_exc()})
    if args.journey:
        from g3_journey import journey
        old=Path.cwd()
        try:
            os.chdir(ROOT/'roguelike')
            with tempfile.TemporaryDirectory(prefix='g3-journey-') as temp,contextlib.redirect_stdout(log):report['journey']=journey(20261023,temp,out/'journey-progress.json')
        except Exception as error:report['failures'].append({'journey':20261023,'error':str(error),'traceback':traceback.format_exc()})
        finally:os.chdir(old)
    report['source_stable']=source==source_manifest();report['passed']=not report['failures'] and report['source_stable']
    (out/'run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');(out/'runtime-log.txt').write_text(log.getvalue(),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k in ('passed','failures','journey')},indent=2))
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
