"""Ordinary preserved G8/G9 plans, exact network evidence and real-handler journey."""
import argparse
from collections import deque
import contextlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def alternate_witness(plan):
    from generation.country_network import baseline,protected_owners
    from generation.network_metrics import centerline_edges,topology
    from generation.road_network import corners
    old=centerline_edges(r for r in baseline(plan)['routes'] if r['kind']=='country');edges=centerline_edges(r for r in plan['routes'] if r['kind']=='country');new=edges-old
    runs=topology(edges)['runs'];protected=protected_owners(plan)
    for run in sorted(runs,key=lambda r:(-r['steps'],r['a'],r['b'])):
        removed={tuple(sorted((a,b))) for a,b in zip(run['points'],run['points'][1:])}
        if len(removed)<80 or not removed<=new:continue
        graph={}
        for a,b in edges-removed:graph.setdefault(a,set()).add(b);graph.setdefault(b,set()).add(a)
        start,goal=tuple(run['a']),tuple(run['b']);parents={start:None};queue=deque([start])
        while queue and goal not in parents:
            p=queue.popleft()
            for q in sorted(graph.get(p,())):
                if q not in parents:parents[q]=p;queue.append(q)
        if goal not in parents:continue
        path=[goal]
        while parents[path[-1]] is not None:path.append(parents[path[-1]])
        path.reverse()
        assert not any((x//80,y//43) in protected for x,y in run['points'])
        return dict(passed=True,removed_new_run_steps=run['steps'],alternate_country_steps=len(path)-1,endpoints=[start,goal],removed_path=corners(run['points']),surviving_path=corners(path),
                    scope='Distinct zero-width country-centerline corridors, not road-width cycles or town circuits. Remove a complete newly constructed contracted run in a derived graph only; all original country edges survive.')
    return None


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--journey',action='store_true');a=p.parse_args();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,'-X','utf8',str(ROOT/'tools/worldgen_g3_diagnostic.py'),'--evidence',str(out)]
    if a.journey:command.append('--journey')
    with (out/'inherited-output.txt').open('w',encoding='utf-8') as log:r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=1500)
    if r.returncode:return r.returncode
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    from test_effect_persistence import load_data
    from generation.world_gen import generate_world
    from generation.country_network import baseline,touched
    from generation.network_preview import comparison,overlay_svg,overlay_png
    from generation.network_metrics import terminals,pair_id
    from generation.road_network import PhysicalRoads,corners
    from generation.placement import digest
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from world.world_map import WorldMap
    from g1_support import fingerprint
    report=json.loads((out/'run.json').read_text());preedit=json.loads((ROOT/'evidence/worldgen-g9/before/baseline/results/run.json').read_text());independent=json.loads((ROOT/'evidence/worldgen-g9/before/network-baseline.json').read_text());data=load_data();rows=[]
    with contextlib.redirect_stdout(io.StringIO()):
        for run in report['runs']:
            seed=run['seed'];plan=json.loads((out/f'plan-{seed}.json').read_text());old=baseline(plan)
            assert old==json.loads((ROOT/f'evidence/worldgen-g9/before/baseline/results/plan-{seed}.json').read_text())
            config=dict(data.g3_config,version=3);config.pop('country_network_version');historical=WorldMap(128,128);historical.seed=seed;t=time.perf_counter();generate_world(historical,data,random.Random(seed),planning_settings=config);baseline_seconds=time.perf_counter()-t
            assert digest(historical.plan)==digest(old)
            w=WorldMap(128,128);w.seed=seed;metrics={};t=time.perf_counter();generate_world(w,data,random.Random(seed),planning_metrics=metrics);seconds=time.perf_counter()-t
            assert digest(w.plan)==digest(plan) and not any(ch.visited for ch in w.chunks.values())
            t=time.perf_counter();measures=comparison(plan);graph_seconds=time.perf_counter()-t;assert measures['all_primary_distances_nonincreasing']
            prior=next(v for v in independent['plans'] if v['seed']==seed)
            assert measures['baseline_country']['unique_centerline_steps']==prior['country_unique_edge_tiles']
            assert measures['baseline_country']['cycle_rank']==prior['country_cycle_rank'] and measures['baseline_country']['cut_edge_steps']==prior['country_cut_edge_tiles']
            physical={row['id']:row['physical_steps'] for row in measures['before']}
            assert all(physical[pair_id(r['a'],r['b'])]==r['physical_steps'] for r in prior['terminal_pairs'])
            scenes=[];slices={}
            for xy in sorted({xy for r in plan['routes'] if r.get('network_role') for xy in touched(r)}):
                t=time.perf_counter();scene=create_surface(w,w.get(*xy),data,ItemFactory(data),CreatureFactory(data),80,43);elapsed=time.perf_counter()-t
                slices[xy]=scene.local_map.road_cells;scenes.append(dict(chunk=xy,seconds=elapsed,fingerprint=fingerprint(scene.local_map,scene.actors),actors=len(scene.actors),road_cells=len(scene.local_map.road_cells),provenance=scene.local_map.plan_provenance))
            for (x,y),cells in slices.items():
                if (x+1,y) in slices:assert {b for a,b in cells if a==79}=={b for a,b in slices[x+1,y] if a==0}
                if (x,y+1) in slices:assert {a for a,b in cells if b==42}=={a for a,b in slices[x,y+1] if b==0}
            witness=alternate_witness(plan)
            if plan['network']['accepted']:assert witness
            if seed==20261023:
                pair=pair_id('settlement-1','capital-gateway');after={r['id']:r['physical_steps'] for r in measures['after']};assert physical[pair]==23625 and after[pair]<=physical[pair]/2
                nodes={n['id']:n['xy'] for n in terminals(plan)};measures['required_witness_paths']={label:corners(PhysicalRoads(value).path(nodes['settlement-1'],nodes['capital-gateway'])) for label,value in [('baseline',old),('augmented',plan)]}
            old_cost=next(r for r in preedit['runs'] if r['seed']==seed)
            rows.append(dict(seed=seed,plan_identity=digest(plan),baseline_identity=digest(old),complete_baseline_preserved=True,scenes_at_plan_completion=0,comparison=measures,alternate=witness,network=metrics['network'],touched_scenes=scenes,boundary_continuity=True,
                             costs=dict(serial_baseline_planning_seconds=baseline_seconds,serial_g9_planning_seconds=seconds,diagnostic_graph_seconds=graph_seconds,preedit_g8_planning_seconds=old_cost['planning_seconds'],preedit_g8_scene_seconds=[v['seconds'] for v in old_cost['scenes']],subtree_bytes={k:len(json.dumps(v,separators=(',',':')).encode()) for k,v in plan.items()},scope='Three ordinary seeds. Serial current G8-settings/G9 planning uses identical preserved geography/content. Pre-edit G8 journey/scene timings retain their own raw source and concurrent lightweight docs-check disclosure. New wg9 scene randomness is allowed; no storage-engine change.')))
            (out/f'baseline-plan-{seed}.json').write_text(json.dumps(old,indent=2)+'\n',encoding='utf-8');(out/f'network-{seed}.svg').write_text(overlay_svg(plan),encoding='utf-8');(out/f'network-{seed}.png').write_bytes(overlay_png(plan))
    report.update(revision='wg9',g9_network=rows,preedit_g8_journey=preedit['journey']);(out/'run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'],seeds=len(rows),journey=bool(report['journey']),network='run.json')));return 0


if __name__=='__main__':raise SystemExit(main())
