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
            'command':[sys.executable,*sys.argv],'cwd':str(Path.cwd()),'python':sys.version,'revision':'wg7'}
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
            if plan['version']>=4:
                from generation.road_network import PhysicalRoads
                from generation.poi_selection import distance,extent_distance
                t=time.perf_counter();network=PhysicalRoads(plan)
                row['physical_network']=network.validate_destinations(plan);row['physical_graph_seconds']=time.perf_counter()-t
                origin=next(n['xy'] for n in plan['nodes'] if n['id']=='start')
                row['physical_network']['shortest_start_distances']={n['id']:len(network.path(origin,n['xy']))-1 for n in plan['nodes'] if n['id'] in ('landmark','capital-gateway') or n['id'].startswith('site-')}
                row['physical_network']['distance_units']='shortest four-neighbour tile steps on full-width road/deck/access union'
                row['sites']=dict(minimum=plan['poi_policy']['minimum'],featured=1,**metrics['sites'],records=[])
                for site in plan['sites']:
                    if site['kind']=='compound':
                        children=[p for p in plan['placements'] if p.get('parent')==site['id']]
                        row['sites']['records'].append(dict(**site,children=children,paths_resolved=[p for p in plan['paths'] if p['owner']==site['id']]))
                        continue
                    placement=next(p for p in plan['placements'] if p['id']==site['placement'])
                    row['sites']['records'].append(dict(**site,asset=placement['asset'],rotation=placement['rotation'],mirror=placement['mirror'],
                        access_length=max(placement['approach'][2]-placement['approach'][0],placement['approach'][3]-placement['approach'][1])-1,
                        nearest_other_join=min((distance(placement['join'],s['attachment']['join']) for s in plan['sites'] if s!=site),default=None),
                        town_extent_distance=min(extent_distance(placement['join'],s['bounds']) for s in plan['settlements'])))
                row['sites']['single_asset_counts']=dict(Counter(p['asset'] for p in plan['placements'] if p.get('role')=='site'))
                row['sites']['child_asset_counts']=dict(Counter(p['asset'] for p in plan['placements'] if p.get('parent')))
                row['sites']['recipe_counts']=dict(Counter(s['recipe'] for s in plan['sites'] if s['kind']=='compound'))
                row['sites']['accepted_children']=sum(s['placement'] is not None for p in plan['sites'] if p['kind']=='compound' for s in p['slots'])
                row['sites']['omitted_slots']=[dict(parent=p['id'],slot=s['id'],reason=s['omission']) for p in plan['sites'] if p['kind']=='compound' for s in p['slots'] if s['placement'] is None]
                row['sites']['metadata_bytes']=len(json.dumps({k:plan[k] for k in ('sites','poi_policy','site_selection')+ (('paths',) if plan['version']>=5 else ())},separators=(',',':')).encode())
            row['asset_repetition']=dict(Counter(p['asset'] for p in plan['placements']))
            row['plot_occupancy']=len(plan['placements'])/len(plan['plots'])
            row['metric_definitions']={'plot_occupancy':'occupied/all proposed plots including required landmark; historical frontage_coverage was the same number and is deprecated',
                                     'per_edge_detour_ratio':'polyline length / endpoint Manhattan distance; not shortest travel on the physical network'}
            row['per_edge_detour_ratio']={r['id']:sum(abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(r['points'],r['points'][1:]))/max(1,abs(r['points'][-1][0]-r['points'][0][0])+abs(r['points'][-1][1]-r['points'][0][1])) for r in plan['routes'] if r['kind']=='country'}
            from worldgen_g4_diagnostic import conditional_counts,detail_svg
            row['conditional_counts']=conditional_counts(plan,data)
            if 'selection' in plan:
                row['composition']=[]
                byid={p['id']:p for p in plan['placements']}
                for s in plan['settlements']:
                    plots=[p for p in plan['plots'] if p['owner']==s['id']]
                    chosen=[byid[p['placement']] for p in plots if p['placement']]
                    counts=Counter(p['asset'] for p in chosen);profile=plan['selection']['profiles'][s['form']]
                    row['composition'].append(dict(settlement=s['id'],form=s['form'],profile=s['selection_profile'],
                        slots=len(plots),accepted=len(chosen),vacancies=len(plots)-len(chosen),distinct_assets=len(counts),
                        most_used_share=max(counts.values())/len(chosen),assets=dict(counts),
                        roles={role:dict(eligible_slots=sum(p['role']==role for p in plots),accepted=sum(p['role']==role for p in chosen),
                            minimum=profile['minimum'][role],eligible_assets=[r['asset'] for r in rows]) for role,rows in profile['roles'].items()},
                        cap_exclusions=sum('cap reached' in r['reason'] for p in plots for r in p['rejected']),
                        soft_repetition=[dict(plot=p['id'],reason=p['repetition']) for p in plots if 'repetition' in p],
                        denominator='most_used_share = maximum accepted asset count / accepted placements in this settlement; slots include vacancies'))
            row['timed_scene_scope']='starting surface, every town member, landmark, capital gateway; required crossing checked separately'
            keys={(world.start_wx,world.start_wy)}|{tuple(xy) for s in plan['settlements'] for xy in s['members']}|{tuple(n['chunk']) for n in plan['nodes'] if n['id'] in ('landmark','capital-gateway')}
            keys.update(tuple(s['chunk']) for s in plan.get('sites',[]))
            for xy in sorted(keys):
                t=time.perf_counter()
                with contextlib.redirect_stdout(log):result=create_surface(world,world.get(*xy),data,ItemFactory(data),CreatureFactory(data),80,43)
                row['scenes'].append({'chunk':xy,'seconds':time.perf_counter()-t,'actors':len(result.actors),'items':sum(map(len,result.local_map.floor_objects.values())),
                                      'native_context':getattr(result.local_map,'native_generation_context',None),
                                      'functional_passes':result.local_map.functional_generation})
                for site in (s for s in plan.get('sites',[]) if tuple(s['chunk'])==xy):
                    from worldgen_g6_diagnostic import site_svg
                    children=[p for p in plan['placements'] if p.get('parent')==site['id']] if site['kind']=='compound' else [next(p for p in plan['placements'] if p['id']==site['placement'])]
                    row['scenes'][-1]['site_goals']={p['id']:p['targets'] for p in children};row['scenes'][-1]['site_id']=site['id']
                    view=snapshot(result.local_map,result.actors,data);view['access']=[]
                    (out/f'{seed}-{site["id"]}-scene.svg').write_text(render_svg(view),encoding='utf-8')
                    (out/f'{seed}-{site["id"]}-plan.svg').write_text(site_svg(plan,site),encoding='utf-8')
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
                old=json.loads(gzip.decompress((ROOT/'tools/critical_fix_regressions/fixtures/g5/g4_plan_20261023.json.gz').read_bytes()))
                for form in ('grid','roadside'):
                    settlement=next(s for s in plan['settlements'] if s['form']==form)
                    (out/(form+'-plan.svg')).write_text(detail_svg(plan,settlement),encoding='utf-8')
                    (out/(form+'-before-plan.svg')).write_text(detail_svg(old,next(s for s in old['settlements'] if s['form']==form)),encoding='utf-8')
            (out/f'plan-{seed}.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
            (out/f'plan-{seed}.svg').write_text(plan_svg(plan),encoding='utf-8')
            crossing=next(r for r in plan['routes'] if r['id']=='road-1')['points'][1];xy=(crossing[0]//80,crossing[1]//43)
            with contextlib.redirect_stdout(log):result=create_surface(world,world.get(*xy),data,ItemFactory(data),CreatureFactory(data),80,43)
            from generation.access import reachable
            row['required_crossing']={'chunk':xy,'all_road_cells_reachable':result.local_map.road_cells<=reachable(result.local_map,result.spawn,data)}
            assert row['required_crossing']['all_road_cells_reachable']
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
