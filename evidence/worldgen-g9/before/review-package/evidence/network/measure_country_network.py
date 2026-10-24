"""Independent G8 country geometry measurement; no game imports or source writes.

Only complete retained final-b plans are read. Centerline edges merge intersections
and retracing, unlike route-record or full-width road-tile loop counts. Distances
are exact cardinal tile lengths along that centerline graph. Manhattan ratios
are descriptive lower-bound stretch, not proofs of avoidable terrain detour.
"""
from collections import Counter, deque
from hashlib import sha256
from itertools import combinations
from pathlib import Path
import argparse
import json
import statistics
import subprocess
import sys


def graph_for(routes):
    graph = {}
    multiplicity = Counter()
    for route in routes:
        for a, z in zip(route['points'], route['points'][1:]):
            assert a[0] == z[0] or a[1] == z[1]
            dx = (z[0] > a[0]) - (z[0] < a[0])
            dy = (z[1] > a[1]) - (z[1] < a[1])
            prev = tuple(a)
            graph.setdefault(prev, set())
            for i in range(1, abs(z[0]-a[0])+abs(z[1]-a[1])+1):
                q = (a[0]+dx*i, a[1]+dy*i)
                edge = tuple(sorted((prev, q)))
                multiplicity[edge] += 1
                graph.setdefault(prev, set()).add(q)
                graph.setdefault(q, set()).add(prev)
                prev = q
    return graph, multiplicity


def bfs(graph, start):
    dist = {start: 0}
    queue = deque([start])
    while queue:
        p = queue.popleft()
        for q in graph[p]:
            if q not in dist:
                dist[q] = dist[p]+1
                queue.append(q)
    return dist


def bridges(graph):
    # Iterative Tarjan, avoiding recursion length tied to world extent.
    order, low, parent, result = {}, {}, {}, set()
    for start in sorted(graph):
        if start in order:
            continue
        order[start] = low[start] = len(order)
        parent[start] = None
        stack = [(start, iter(sorted(graph[start])))]
        while stack:
            p, neighbours = stack[-1]
            try:
                q = next(neighbours)
            except StopIteration:
                stack.pop()
                par = parent[p]
                if par is not None:
                    low[par] = min(low[par], low[p])
                    if low[p] > order[par]:
                        result.add(tuple(sorted((par, p))))
                continue
            if q == parent[p]:
                continue
            if q in order:
                low[p] = min(low[p], order[q])
            else:
                parent[q] = p
                order[q] = low[q] = len(order)
                stack.append((q, iter(sorted(graph[q]))))
    return result


def measure(plan):
    country = [r for r in plan['routes'] if r['kind'] == 'country']
    cg, cm = graph_for(country)
    ag, am = graph_for(plan['routes'])
    remaining = set(cg)
    components = 0
    while remaining:
        remaining.difference_update(bfs(cg, min(remaining)))
        components += 1
    cb = bridges(cg)
    terminals = [n for n in plan['nodes'] if n['id'] == 'start' or n['id'].startswith('settlement-') or n['id'] in ('capital-gateway', 'landmark')]
    cd = {n['id']: bfs(cg, tuple(n['xy'])) for n in terminals}
    ad = {n['id']: bfs(ag, tuple(n['xy'])) for n in terminals}
    pairs = []
    for a, b in combinations(terminals, 2):
        lower = abs(a['xy'][0]-b['xy'][0])+abs(a['xy'][1]-b['xy'][1])
        distance = cd[a['id']][tuple(b['xy'])]
        all_distance = ad[a['id']][tuple(b['xy'])]
        pairs.append(dict(a=a['id'], b=b['id'], a_xy=a['xy'], b_xy=b['xy'],
                          manhattan_tiles=lower, country_centerline_tiles=distance,
                          all_roads_centerline_tiles=all_distance,
                          country_manhattan_stretch=distance/lower,
                          street_shortcut_savings_tiles=distance-all_distance))
    by_route = []
    for r in country:
        length = sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(r['points'],r['points'][1:]))
        lower = abs(r['points'][0][0]-r['points'][-1][0])+abs(r['points'][0][1]-r['points'][-1][1])
        by_route.append(dict(id=r['id'], a=r['a'], b=r['b'], length_tiles=length,
                             manhattan_tiles=lower, route_manhattan_stretch=length/lower,
                             search_nodes=r['search_nodes']))
    # Water crossing records are one route/water-arm ownership row, so don't
    # claim their count is a count of physical bridges.
    return dict(seed=plan['seed'], country_routes=len(country), country_vertices=len(cg),
                country_unique_edge_tiles=len(cm), country_summed_route_tiles=sum(cm.values()),
                country_retraced_edge_tiles=sum(cm.values())-len(cm),
                country_edges_used_by_multiple_routes=sum(v>1 for v in cm.values()),
                country_components=components, country_cycle_rank=len(cm)-len(cg)+components,
                country_cut_edge_tiles=len(cb), country_cut_edge_fraction=len(cb)/len(cm),
                raw_crossing_records=len(plan['crossings']),
                terminal_nodes=terminals, terminal_pairs=pairs,
                pair_count=len(pairs), median_pair_manhattan_stretch=statistics.median(p['country_manhattan_stretch'] for p in pairs),
                max_pair=max(pairs,key=lambda p:p['country_manhattan_stretch']),
                routes=by_route)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    repo=args.repo.resolve()
    result=dict(schema=1, source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
                method=__doc__, definitions=dict(unique_edge_tiles='Number of distinct cardinal unit centerline edges in country-route union.',
                retraced_edge_tiles='Summed country route centerline length minus union length; overlap may be desirable corridor reuse, not automatically wasted construction.',
                cut_edge='Graph-theoretic bridge of zero-width country centerline union. Not a claim that game terrain becomes impassable after a road edge failure.',
                pair_set='All unordered pairs of start, each settlement, capital gateway and featured landmark; crossing-near/far and later rural sites excluded.',
                stretch='Country centerline shortest distance divided by physical-tile Manhattan distance. This lower bound ignores terrain, so excess is descriptive, not a proof of avoidable detour.'), plans=[])
    for seed in (0,20261023,29417):
        path=repo/f'evidence/worldgen-g8/final-b/diagnostic/results/plan-{seed}.json'
        raw=path.read_bytes()
        row=measure(json.loads(raw))
        row['source_path']=str(path.relative_to(repo))
        row['source_sha256']=sha256(raw).hexdigest()
        result['plans'].append(row)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    for p in result['plans']:
        print(json.dumps({k:p[k] for k in ('seed','country_unique_edge_tiles','country_summed_route_tiles','country_retraced_edge_tiles','country_cycle_rank','country_cut_edge_fraction','pair_count','median_pair_manhattan_stretch','max_pair')}))


if __name__=='__main__':
    main()
