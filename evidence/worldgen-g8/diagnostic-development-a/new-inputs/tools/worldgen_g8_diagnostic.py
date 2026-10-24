"""Ordinary G8 destinations, bounded composition metrics and G7 comparison."""
import argparse
from collections import Counter,deque
import contextlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def bfs(graph,start,goal=None,omit=None):
    parent={start:None};q=deque([start])
    while q:
        a=q.popleft()
        if a==goal:break
        for b in sorted(graph.get(a,())):
            if b not in parent and frozenset((a,b))!=omit:parent[b]=a;q.append(b)
    if goal is None:return parent
    if goal not in parent:return []
    result=[goal]
    while parent[result[-1]] is not None:result.append(parent[result[-1]])
    return result[::-1]


def topology(plan,s):
    """Union exact unit centerline edges; crossing points and shared runs merge."""
    x,y,r,b=s['bounds'];graph={}
    for road in plan['routes']:
        for a,z in zip(road['points'],road['points'][1:]):
            dx=(z[0]>a[0])-(z[0]<a[0]);dy=(z[1]>a[1])-(z[1]<a[1]);prev=None
            for i in range(abs(z[0]-a[0])+abs(z[1]-a[1])+1):
                p=(a[0]+dx*i,a[1]+dy*i)
                if not (x<=p[0]<r and y<=p[1]<b):prev=None;continue
                graph.setdefault(p,set())
                if prev is not None:graph[p].add(prev);graph[prev].add(p)
                prev=p
    remain=set(graph);components=0
    while remain:remain-=set(bfs(graph,min(remain)));components+=1
    edges=sum(map(len,graph.values()))//2;anchors={p for p,adj in graph.items() if len(adj)!=2};walked=set();runs=[]
    for start in sorted(anchors):
        for nxt in sorted(graph[start]):
            if frozenset((start,nxt)) in walked:continue
            path=[start,nxt];walked.add(frozenset(path))
            while path[-1] not in anchors:
                v=next(v for v in graph[path[-1]] if v!=path[-2]);walked.add(frozenset((path[-1],v)));path.append(v)
            runs.append(path)
    # Current templates have junctions; any isolated all-degree-two ring would
    # remain explicitly visible in cycle rank, never silently count as zero.
    witness=None
    for path in runs:
        alt=bfs(graph,path[0],path[-1],frozenset(path[:2]))
        if alt and path[0]!=path[-1]:
            witness=dict(endpoints=[path[0],path[-1]],direct_centerline_steps=len(path)-1,alternate_centerline_steps=len(alt)-1,direct=path,alternate=alt);break
    return dict(unit_vertices=len(graph),unit_edges=edges,components=components,cycle_rank=edges-len(graph)+components,contracted_junctions=len(anchors),contracted_runs=len(runs),alternate=witness,definition='Exact zero-width centerline union clipped to town; crossings/shared runs reconciled; degree-two runs contracted. Cycle rank E-V+C. Witness removes first unit edge of a contracted run; no wide-road tile cycles or route a=b counts.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--journey',action='store_true');a=p.parse_args();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,'-X','utf8',str(ROOT/'tools/worldgen_g7_diagnostic.py'),'--evidence',str(out)]
    if a.journey:command.append('--journey')
    result=subprocess.run(command,cwd=ROOT,timeout=600)
    if result.returncode:return result.returncode
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    from test_effect_persistence import load_data
    from generation.world_gen import generate_world
    from generation.access import enterable
    from generation.placement import digest
    from generation.settlement_preview import diagram
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from world.world_map import WorldMap
    data=load_data();report=json.loads((out/'run.json').read_text());report['revision']='wg8';baseline=json.loads((ROOT/'evidence/worldgen-g8/before/baseline/results/run.json').read_text());details=[]
    with contextlib.redirect_stdout(io.StringIO()):
        for row in report['runs']:
            seed=row['seed'];plan=json.loads((out/f'plan-{seed}.json').read_text());old=json.loads((ROOT/f'evidence/worldgen-g8/before/baseline/results/plan-{seed}.json').read_text());oldcost=next(r for r in baseline['runs'] if r['seed']==seed)
            w=WorldMap(128,128);w.seed=seed;metrics={};generate_world(w,data,random.Random(seed),planning_metrics=metrics);assert digest(w.plan)==digest(plan)
            country_equal=[r for r in plan['routes'] if r['kind']=='country']==[r for r in old['routes'] if r['kind']=='country'];assert country_equal
            record=dict(seed=seed,plan_identity=digest(plan),country_routes_exact=country_equal,planning_metrics=metrics,subtree_bytes={k:len(json.dumps(plan[k],separators=(',',':')).encode()) for k in ('settlements','routes','blocks','public_spaces','plots','placements','reservations','dependencies')},settlements=[])
            record['cost_comparison']=dict(g7_planning_seconds=oldcost['planning_seconds'],g8_planning_seconds=row['planning_seconds'],g7_plan_bytes=oldcost['plan_bytes'],g8_plan_bytes=row['plan_bytes'],g7_scene_seconds=[r['seconds'] for r in oldcost['scenes']],g8_scene_seconds=[r['seconds'] for r in row['scenes']],scope='Same machine/interpreter, three ordinary seeds, serial gates; timings are samples, not a frame-time guarantee.')
            for s in plan['settlements']:
                plots=[p for p in plan['plots'] if p['owner']==s['id']];ids={p['placement'] for p in plots if p['placement']};chosen=[p for p in plan['placements'] if p['id'] in ids];cells=set()
                for xy in s['members']:
                    scene=create_surface(w,w.get(*xy),data,ItemFactory(data),CreatureFactory(data),80,43);blocked={(v.x,v.y) for v in scene.actors if v.blocks_movement}
                    cells.update((xy[0]*80+x,xy[1]*43+y) for x in range(80) for y in range(43) if (x,y) not in blocked and enterable(scene.local_map,(x,y),data))
                graph={q:{(q[0]+dx,q[1]+dy) for dx,dy in ((0,1),(1,0),(0,-1),(-1,0))}&cells for q in cells};arrival=tuple(s['arrival']['position']);assert arrival in graph
                travel=[]
                for role in ('civic','commercial','residential'):
                    candidates=sorted((p for p in chosen if p['role']==role),key=lambda p:(abs(p['join'][0]-arrival[0])+abs(p['join'][1]-arrival[1]),p['id']))
                    if not candidates:continue
                    p=candidates[0];entry=next(e for e in p['entrances'] if e['required']);end=(entry['x'],entry['y']);path=bfs(graph,arrival,end);assert path,(seed,s['id'],role,end)
                    travel.append(dict(role=role,placement=p['id'],arrival=arrival,entrance=end,steps=len(path)-1))
                commons=[c for c in plan['public_spaces'] if c['owner']==s['id']]
                area=lambda r:(r[2]-r[0])*(r[3]-r[1])
                record['settlements'].append(dict(id=s['id'],form=s['form'],layout=s['layout'],arrival=s['arrival'],normals=dict(Counter(p['normal'] for p in plots if p['placement'])),roles=dict(Counter(p['role'] for p in chosen)),assets=dict(Counter(p['asset'] for p in chosen)),blocks=sum(b['owner']==s['id'] for b in plan['blocks']),common_tiles=sum(area(r) for c in commons for r in c['rects']),private_lot_tiles=sum(area(p['buildable']) for p in plots),lots=len(plots),accepted=len(chosen),vacancies=[dict(id=p['id'],reason=p.get('rejected')) for p in plots if not p['placement']],fit_trials=sum(p.get('fit_trials',0) for p in plots),travel=travel,travel_units='Shortest four-neighbour tile steps across complete populated member terrain, including openable doors and excluding stationary blocking actors; endpoints actual saved arrival and selected required door. No diagonal distance.',g8_centerline=topology(plan,s),g7_centerline=topology(old,next(v for v in old['settlements'] if v['id']==s['id']))))
                (out/f'{seed}-{s["id"]}-layout.svg').write_text(diagram(plan,s),encoding='utf-8')
            details.append(record)
    report['g8_composition']=details;(out/'run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=True,seeds=len(details),composition='run.json')));return 0


if __name__=='__main__':raise SystemExit(main())
