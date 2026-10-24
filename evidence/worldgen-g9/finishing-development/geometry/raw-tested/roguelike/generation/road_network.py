"""Disposable full-width physical roads. Four-neighbour cells, unit tile distance.

Only occupied bands/decks/access are allocated; never a world-sized grid. Shared
cells and orthogonal adjacency connect, diagonal corner contact does not. Canonical
routes remain the only saved road authority. This is not the movement/interaction
graph of a populated scene.
"""
from collections import deque
from generation.context import GenerationError

MAX_CELLS = 2_000_000
STEPS = ((0,-1),(-1,0),(1,0),(0,1))


def project_cells(plan,include_access=True):
    """Exact sparse cells without eagerly labelling components for BFS callers."""
    cells=set();rectangles=[r for route in plan['routes'] for r in route['rects']]
    rectangles.extend(r for crossing in plan.get('crossings',[]) for r in crossing['deck'])
    if include_access:
        rectangles.extend(p['approach'] for p in plan.get('placements',[]))
        rectangles.extend(r for path in plan.get('paths',[]) for r in path['rects'])
        rectangles.extend(s['approach'] for s in plan.get('sites',[]) if s['kind']=='compound')
    for x,y,x1,y1 in sorted(set(map(tuple,rectangles))):
        if (x1-x)*(y1-y)>MAX_CELLS:raise GenerationError('physical road projection exceeds sparse cell budget')
        cells.update((a,b) for a in range(x,x1) for b in range(y,y1))
        if len(cells)>MAX_CELLS:raise GenerationError('physical road projection exceeds sparse cell budget')
    return cells


class PhysicalRoads:
    def __init__(self, plan, include_access=True):
        self.cells=project_cells(plan,include_access)
        self.labels={};sizes=[]
        for start in sorted(self.cells):
            if start in self.labels:continue
            number=len(sizes);self.labels[start]=number;queue=deque([start]);count=0
            while queue:
                x,y=queue.popleft();count+=1
                for dx,dy in STEPS:
                    q=x+dx,y+dy
                    if q in self.cells and q not in self.labels:
                        self.labels[q]=number;queue.append(q)
            sizes.append(count)
        self.component_sizes=sizes

    def connected(self,a,b):
        a,b=tuple(a),tuple(b)
        return a in self.labels and self.labels.get(a)==self.labels.get(b)

    def path(self,start,goal):
        start,goal=tuple(start),tuple(goal)
        if not self.connected(start,goal):raise GenerationError(f'physical road disconnected: {start} -> {goal}')
        parent={start:None};queue=deque([start])
        while queue and goal not in parent:
            x,y=queue.popleft()
            for dx,dy in STEPS:
                q=x+dx,y+dy
                if q in self.cells and q not in parent:parent[q]=(x,y);queue.append(q)
        path=[];q=goal
        while q is not None:path.append(q);q=parent[q]
        return list(reversed(path))

    def validate_destinations(self,plan):
        start=next(n['xy'] for n in plan['nodes'] if n['id']=='start')
        for n in plan['nodes']:
            if n['required'] and not self.connected(start,n['xy']):
                raise GenerationError(f'{n["id"]}: required destination is outside connected physical road system')
        for site in plan.get('sites',[]):
            selected=([p for p in plan['placements'] if p.get('parent')==site['id']] if site['kind']=='compound' else [next(p for p in plan['placements'] if p['id']==site['placement'])])
            rectangles=[p['approach'] for p in selected]
            if site['kind']=='compound':rectangles+=[site['approach']]+[r for path in plan['paths'] if path['owner']==site['id'] for r in path['rects']]
            for x,y,x1,y1 in rectangles:
                if any(not self.connected(start,(a,b)) for a in range(x,x1) for b in range(y,y1)):
                    raise GenerationError(f'{site["id"]}: parent {site["attachment"]["road"]} has disconnected complete access')
        return dict(cells=len(self.cells),components=len(self.component_sizes),component_sizes=self.component_sizes,
                    connected_sites=len(plan.get('sites',[])),adjacency='shared cells or four-neighbour unit tile steps')


def corners(path):
    """Lossless cardinal compression for production-handler road traversal."""
    if len(path)<3:return [list(p) for p in path]
    result=[path[0]]
    for a,b,c in zip(path,path[1:],path[2:]):
        if (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):result.append(b)
    return [list(p) for p in result+[path[-1]]]
