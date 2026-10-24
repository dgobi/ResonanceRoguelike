"""Read-only G8 route alternatives under conservative current macro constraints.

Reconstructs three current worlds in memory (no scenes or saves). Compares saved
road/deck/access-union travel with independently searched candidate corridors.
These are planning counterexamples, not materialized G9 or production journeys.
"""
from collections import deque
from contextlib import redirect_stdout
from hashlib import sha256
from pathlib import Path
import argparse
import heapq
import io
import json
import os
import random
import sys


def physical(plan):
    rects=[r for route in plan['routes'] for r in route['rects']]
    rects += [r for c in plan['crossings'] for r in c['deck']]
    rects += [p['approach'] for p in plan['placements']]
    rects += [r for p in plan.get('paths',[]) for r in p['rects']]
    rects += [s['approach'] for s in plan.get('sites',[]) if s['kind']=='compound']
    return {(x,y) for a,b,c,d in rects for x in range(a,c) for y in range(b,d)}


def physical_distance(cells,start,goal):
    queue=deque([start]);d={start:0}
    while queue:
        p=queue.popleft()
        if p==goal:return d[p]
        for dx,dy in ((0,-1),(-1,0),(1,0),(0,1)):
            q=p[0]+dx,p[1]+dy
            if q in cells and q not in d:d[q]=d[p]+1;queue.append(q)
    return None


def shortest(world,plan,start,goal,protect_existing_places=True):
    edges=set();old_cells=set()
    for r in plan['routes']:
        if r['kind']!='country':continue
        for a,b in zip(r['points'],r['points'][1:]):
            aa=a[0]//80,a[1]//43;bb=b[0]//80,b[1]//43
            assert abs(aa[0]-bb[0])+abs(aa[1]-bb[1])==1
            edges.add(frozenset((aa,bb)));old_cells.update((aa,bb))
    blocked=set()
    if protect_existing_places:
        blocked={tuple(q) for s in plan['settlements'] for q in s['members']}
        blocked.update(tuple(s['chunk']) for s in plan.get('sites',[]))
        blocked.update((p['origin'][0]//80,p['origin'][1]//43) for p in plan['placements'])
        blocked.update(world.capital_chunks)
    parent={};cost={start:0};heap=[(0,start)];expanded=0
    while heap:
        g,p=heapq.heappop(heap)
        if g!=cost[p]:continue
        expanded+=1
        if p==goal:
            path=[p]
            while p in parent:p=parent[p];path.append(p)
            return list(reversed(path)),expanded,g
        for dx,dy,step in ((0,-1,43),(-1,0,80),(1,0,80),(0,1,43)):
            q=p[0]+dx,p[1]+dy;c=world.get(*q)
            if c is None or c.biome_id=='deep_mountain' or (c.is_capital and q!=goal):continue
            old=frozenset((p,q)) in edges
            # Avoid every new water crossing, every new intrusion through a
            # settlement/rural-owner chunk, and every new chunk with a submap.
            if (c.is_river or world.get(*p).is_river) and not old:continue
            if (q in blocked or p in blocked) and not old:continue
            if c.submaps and q not in old_cells and q!=goal:continue
            ng=g+step
            if ng<cost.get(q,float('inf')):cost[q]=ng;parent[q]=p;heapq.heappush(heap,(ng,q))
    return None,expanded,None


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--metrics',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    repo=args.repo.resolve();sys.path[:0]=[str(repo/'roguelike'),str(repo/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONDONTWRITEBYTECODE='1')
    from test_effect_persistence import load_data
    from generation.world_gen import generate_world
    from world.world_map import WorldMap
    from generation.placement import digest
    result=dict(schema=1,scope=__doc__,admissibility='Existing macro hard exclusions (out of world, deep_mountain, capital except destination), plus no new river crossings, no new entry/exit edges through any settlement/rural owner/building/capital chunk (including endpoints), and no new chunks with submaps. Costs are exact tile lengths (E/W 80; N/S 43); biome/elevation preferences are not part of this shortest-distance witness. Existing road edges may be reused through protected chunks.',limits='Candidate centerline routes are not fitted/populated or accepted world plans. They demonstrate an available conservative macro corridor, not guaranteed final G9 feasibility or production movement timing. Existing union distances ignore off-road movement and transient actors.',python=sys.version,plans=[])
    data=load_data()
    for row in json.loads(args.metrics.read_text())['plans']:
        seed=row['seed'];plan=json.loads((repo/row['source_path']).read_text());w=WorldMap(128,128);w.seed=seed
        with redirect_stdout(io.StringIO()):generate_world(w,data,random.Random(seed))
        assert digest(w.plan)==digest(plan)
        pair=row['max_pair'];nodes={n['id']:n for n in plan['nodes']};start=tuple(nodes[pair['a']]['chunk']);goal=tuple(nodes[pair['b']]['chunk'])
        path,expanded,distance=shortest(w,plan,start,goal)
        union=physical(plan);real=physical_distance(union,tuple(pair['a_xy']),tuple(pair['b_xy']))
        route_points=[[80*x+40,43*y+21] for x,y in path] if path else []
        oldedges={frozenset(((a[0]//80,a[1]//43),(b[0]//80,b[1]//43))) for r in plan['routes'] if r['kind']=='country' for a,b in zip(r['points'],r['points'][1:])}
        new=[(a,b) for a,b in zip(path,path[1:]) if frozenset((a,b)) not in oldedges]
        new_length=sum(80*abs(a[0]-b[0])+43*abs(a[1]-b[1]) for a,b in new)
        from generation.world_plan import bands,cells
        candidate_cells=set().union(*(cells(r) for r in bands(route_points,3)))
        country_cells=set().union(*(cells(r) for route in plan['routes'] if route['kind']=='country' for r in route['rects']))
        result['plans'].append(dict(seed=seed,a=pair['a'],b=pair['b'],source_plan_sha256=row['source_sha256'],plan_reproduced_exactly=True,visited_scenes=sum(bool(getattr(c,'visited',False)) for c in w.chunks.values()),manhattan_tiles=pair['manhattan_tiles'],country_centerline_tiles=pair['country_centerline_tiles'],physical_union_tiles=real,physical_manhattan_stretch=real/pair['manhattan_tiles'],candidate_centerline_tiles=distance,candidate_expanded_nodes=expanded,existing_union_to_candidate_ratio=real/distance if distance else None,candidate_new_unique_centerline_tiles=new_length,candidate_reused_centerline_tiles=distance-new_length,candidate_new_centerline_fraction_of_existing=new_length/row['country_unique_edge_tiles'],candidate_new_road_cells=len(candidate_cells-country_cells),existing_country_road_cells=len(country_cells),candidate_chunk_path=path,candidate_tile_points=route_points))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    for p in result['plans']:print(json.dumps({k:v for k,v in p.items() if k not in ('candidate_chunk_path','candidate_tile_points')}))


if __name__=='__main__':main()
