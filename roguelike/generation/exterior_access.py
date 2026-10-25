"""Bounded reciprocal edge witnesses for access revision 1.

Read coarse metadata and narrow natural-field strips, never neighbor scenes.
Entrances cannot stamp boundary cells; reserve reciprocal natural edges from
later dressing. Authored footprints are excluded, while existing road decks
remain authoritative. No terrain is carved or diagonal rule changed.
"""
from config import MAP_WIDTH as W, MAP_HEIGHT as H
from generation.access import enterable, reachable
from generation.context import GenerationError
from generation.world_plan import slice_plan, expand
from generation.wilderness import eligible, sample


def _project_edge(world, chunk, policy, data, points, section=None):
    section = section if section is not None else slice_plan(world.plan, chunk.wx, chunk.wy)
    x0, y0 = chunk.wx*W, chunk.wy*H
    left, top = min(x for x,y in points), min(y for x,y in points)
    width = max(x for x,y in points)-left+1
    height = max(y for x,y in points)-top+1
    natural = sample(world, policy, x0+left, y0+top, width, height)['terrain'] if eligible(chunk) else None

    def inside(p, r):
        return r[0] <= p[0] < r[2] and r[1] <= p[1] < r[3]

    result = set()
    for x,y in points:
        p = x0+x, y0+y
        tid = str(natural[x-left,y-top]) if natural is not None else None
        # Same water/road overlay order as planned_scene; owned sites are
        # conservatively excluded rather than predicting their interiors.
        for water in section['waters']:
            for r in water['rects']:
                if inside(p, expand(r,2)): tid = 'river_bank'
                if inside(p, r): tid = 'river_water'
        if any(inside(p,r) for road in section['routes'] for r in road['rects']):
            if tid != 'river_water': tid = 'road_0'
        if any(inside(p,r) for crossing in section['crossings'] for r in crossing['deck']):
            tid = 'cobblestone'
        owned = any(inside(p, row[key]) for row in section['placements']
                    for key in ('clearance','approach','footprint'))
        owned |= any(inside(p,r) for row in section.get('public_spaces',[]) for r in row['rects'])
        owned |= any(inside(p,row['approach']) for row in section.get('sites',[]))
        owned |= any(inside(p,r) for row in section.get('paths',[]) for r in row['rects'])
        if not owned and data.terrain.get(tid,{}).get('walkable',False):
            result.add((x,y))
    return result


def bind_exterior(m, world, chunk, policy, data, spawn, section):
    """Select a real in-world edge and retain arrival, road and stair obligations."""
    pairs = {}
    edges = [((-1,0),[(0,y) for y in range(H)],[(W-1,y) for y in range(H)]),
             ((1,0),[(W-1,y) for y in range(H)],[(0,y) for y in range(H)]),
             ((0,-1),[(x,0) for x in range(W)],[(x,H-1) for x in range(W)]),
             ((0,1),[(x,H-1) for x in range(W)],[(x,0) for x in range(W)])]
    for (dx,dy), local, opposite in edges:
        neighbor = world.get(chunk.wx+dx,chunk.wy+dy)
        if neighbor is None: continue
        own = _project_edge(world,chunk,policy,data,local,section)
        other = _project_edge(world,neighbor,policy,data,opposite)
        for a,b in zip(local,opposite):
            if a in own and b in other and enterable(m,a,data):
                pairs.setdefault(a,dict(neighbor=[neighbor.wx,neighbor.wy], reciprocal=list(b)))
    # Reserve all eligible reciprocal edges so generation order cannot invalidate
    # another chunk's witness. This changes no natural field or painted tile.
    m.protected_cells.update(pairs)
    reached = reachable(m,spawn,data)
    available = reached & pairs.keys()
    if not available:
        # Water/ownership can split the original natural arrival component.
        # Reselect existing ground only; mandatory roads must still be connected.
        seen = set(); choices = []
        roads = set(m.required_access_anchors[1:])
        for edge in sorted(pairs):
            if edge in seen: continue
            component = reachable(m,edge,data); seen.update(component)
            if roads <= component:
                anchor = min(component,key=lambda p:(max(abs(p[0]-spawn[0]),abs(p[1]-spawn[1])),p))
                choices.append((-len(component),anchor,component))
        if not choices:
            raise GenerationError(f'wilderness {chunk.wx,chunk.wy} access revision 1: arrival {spawn} has no legal reciprocal exterior')
        _,spawn,reached = min(choices,key=lambda c:c[:2])
        m.required_access_anchors[0] = spawn
        available = reached & pairs.keys()
    witness = min(available,key=lambda p:(max(abs(p[0]-spawn[0]),abs(p[1]-spawn[1])),p))
    m.required_access_anchors.append(witness)
    m.wilderness_access = dict(revision=1,chunk=[chunk.wx,chunk.wy],arrival=list(spawn),
                              edge=list(witness),**pairs[witness])
    return spawn
