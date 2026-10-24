"""Disposable exact road projections; canonical plan records remain authoritative.

Centerline edges measure construction/topology. Full-width road/deck/access cells
measure four-neighbour physical travel, not off-road or actor-aware movement.
"""
from collections import deque
from itertools import combinations
from generation.context import GenerationError

STEPS=((0,-1),(-1,0),(1,0),(0,1))


def terminals(plan):
    return sorted((n for n in plan['nodes'] if n['id'] in ('start','capital-gateway','landmark') or n['id'].startswith('settlement-')),key=lambda n:n['id'])


def pair_id(a,b):return '|'.join(sorted((a,b)))


def centerline_edges(routes):
    edges=set()
    for route in routes:
        for a,b in zip(route['points'],route['points'][1:]):
            if a[0]!=b[0] and a[1]!=b[1]:raise GenerationError('network: diagonal centerline')
            dx=(b[0]>a[0])-(b[0]<a[0]);dy=(b[1]>a[1])-(b[1]<a[1]);p=tuple(a)
            for _ in range(abs(b[0]-a[0])+abs(b[1]-a[1])):
                q=p[0]+dx,p[1]+dy;edges.add(tuple(sorted((p,q))));p=q
    return edges


def road_cells(routes):
    return {(x,y) for r in routes for a,b,c,d in r['rects'] for x in range(a,c) for y in range(b,d)}


def physical_cells(plan):
    from generation.road_network import PhysicalRoads
    return PhysicalRoads(plan).cells


def distances(cells,nodes):
    """One bounded sparse BFS per source, stop once remaining endpoints are met."""
    result={};nodes=sorted(nodes,key=lambda n:n['id'])
    for i,a in enumerate(nodes[:-1]):
        targets={tuple(b['xy']):b['id'] for b in nodes[i+1:]}
        start=tuple(a['xy'])
        if start not in cells:raise GenerationError('network: primary endpoint outside physical roads')
        queue=deque([start]);seen={start};distance=0
        while queue and targets:
            for _ in range(len(queue)):
                p=queue.popleft()
                if p in targets:result[pair_id(a['id'],targets.pop(p))]=distance
                for dx,dy in STEPS:
                    q=p[0]+dx,p[1]+dy
                    if q in cells and q not in seen:seen.add(q);queue.append(q)
            distance+=1
        if targets:raise GenerationError('network: disconnected primary endpoints')
    return result


def pair_rows(plan,values):
    return [dict(id=pair_id(a['id'],b['id']),a=a['id'],b=b['id'],a_xy=a['xy'],b_xy=b['xy'],
                 manhattan_lower_bound=abs(a['xy'][0]-b['xy'][0])+abs(a['xy'][1]-b['xy'][1]),physical_steps=values[pair_id(a['id'],b['id'])])
            for a,b in combinations(terminals(plan),2)]


def topology(edges,meaningful=()):
    """Iterative cut-edge analysis and lossless runs, including rings/parallel runs."""
    graph={}
    for a,b in edges:graph.setdefault(a,set()).add(b);graph.setdefault(b,set()).add(a)
    order={};low={};parent={};cuts=[];components=[]
    for start in sorted(graph):
        if start in order:continue
        component=[];order[start]=low[start]=len(order);parent[start]=None;stack=[(start,iter(sorted(graph[start])))];component.append(start)
        while stack:
            p,adj=stack[-1]
            try:q=next(adj)
            except StopIteration:
                stack.pop();par=parent[p]
                if par is not None:
                    low[par]=min(low[par],low[p])
                    if low[p]>order[par]:cuts.append(tuple(sorted((par,p))))
                continue
            if q==parent[p]:continue
            if q in order:low[p]=min(low[p],order[q]);continue
            parent[q]=p;order[q]=low[q]=len(order);component.append(q);stack.append((q,iter(sorted(graph[q]))))
        components.append(component)
    anchors={p for p,adj in graph.items() if len(adj)!=2}|(set(map(tuple,meaningful))&set(graph))
    for component in components:
        if not anchors.intersection(component):anchors.add(min(component))
    walked=set();runs=[]
    for a in sorted(anchors):
        for b in sorted(graph[a]):
            edge=tuple(sorted((a,b)))
            if edge in walked:continue
            path=[a,b];walked.add(edge)
            while path[-1] not in anchors:
                q=next(q for q in graph[path[-1]] if q!=path[-2]);walked.add(tuple(sorted((path[-1],q))));path.append(q)
            runs.append(dict(a=a,b=path[-1],steps=len(path)-1,points=path))
    assert walked==edges
    return dict(vertices=len(graph),unique_centerline_steps=len(edges),components=len(components),cycle_rank=len(edges)-len(graph)+len(components),
                cut_edge_steps=len(cuts),cut_edge_fraction=len(cuts)/len(edges) if edges else 0,runs=runs)
