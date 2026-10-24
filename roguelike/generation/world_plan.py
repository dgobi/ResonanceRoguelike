"""Finite, compact, world-owned initial composition. No tiles or live owners here.

Rectangles are [left,top,right,bottom), polylines are cardinal world-tile points.
All published records are JSON values. Slice indexes are derived, never saved.
"""
from __future__ import annotations
import copy
import heapq
import math
import random
from config import MAP_WIDTH as W, MAP_HEIGHT as H
from generation.context import GenerationError, stable_seed
from generation.placement import transform, entrance_cells, NORMALS, dependencies, digest

VERSION=2
MODE='shared-v1'


def world_xy(wx,wy,lx,ly): return wx*W+lx,wy*H+ly
def address(x,y): return x//W,y//H,x%W,y%H
def intersect(a,b):
    r=[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
    return r if r[0]<r[2] and r[1]<r[3] else None
def expand(r,n): return [r[0]-n,r[1]-n,r[2]+n,r[3]+n]
def cells(rect): return {(x,y) for x in range(rect[0],rect[2]) for y in range(rect[1],rect[3])}
def bounds(points): return [min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points)+1,max(p[1] for p in points)+1]
def member_chunks(rect): return [[x,y] for x in range(rect[0]//W,(rect[2]-1)//W+1) for y in range(rect[1]//H,(rect[3]-1)//H+1)]


def bands(points,width):
    result=[]; half=width//2
    for a,b in zip(points,points[1:]):
        if a[0]!=b[0] and a[1]!=b[1]: raise GenerationError('route contains diagonal segment')
        if a[1]==b[1]: r=[min(a[0],b[0]),a[1]-half,max(a[0],b[0])+1,a[1]+width-half]
        else: r=[a[0]-half,min(a[1],b[1]),a[0]+width-half,max(a[1],b[1])+1]
        result.append(r)
    for x,y in points[1:-1]: result.append([x-half,y-half,x+width-half,y+width-half])
    return result


def settings(data,override=None):
    c=copy.deepcopy(override if override is not None else data.g3_config)
    expected={'version','settlement_count','minimum_separation_chunks','near_start_radius_chunks','forms','road_width_tiles','street_width_tiles','plot_spacing_tiles','setback_tiles','max_spur_tiles','route_search_nodes','site_search_limit','pools'}
    if not isinstance(c,dict) or set(c)!=expected or c['version']!=1: raise GenerationError('G3 settings: expected complete version-one configuration')
    count=c['settlement_count']
    if not isinstance(count,list) or len(count)!=2 or any(type(n) is not int for n in count) or not 2<=count[0]<=count[1]<=8: raise GenerationError('G3 settings: inclusive settlement_count must be 2..8')
    ranges={'minimum_separation_chunks':(3,128),'near_start_radius_chunks':(2,128),'road_width_tiles':(1,5),'street_width_tiles':(1,5),'plot_spacing_tiles':(14,40),'setback_tiles':(1,8),'max_spur_tiles':(2,24),'route_search_nodes':(16,65536),'site_search_limit':(1,16384)}
    for k,(lo,hi) in ranges.items():
        if type(c[k]) is not int or not lo<=c[k]<=hi: raise GenerationError(f'G3 settings: {k} must be integer {lo}..{hi}')
    if c['forms']!=['grid','roadside']: raise GenerationError('G3 settings: forms must include grid then roadside; extra settlements alternate')
    if not isinstance(c['pools'],dict) or set(c['pools'])!={'grid','roadside','civic','landmark'}: raise GenerationError('G3 settings: declare all four pools')
    for context,ids in c['pools'].items():
        if not isinstance(ids,list) or not ids or len(set(ids))!=len(ids): raise GenerationError(f'G3 settings: empty/duplicate {context} pool')
        for asset in ids:
            raw=data.structures.get(asset)
            if not raw or context not in raw.get('placement',{}).get('contexts',[]): raise GenerationError(f'G3 settings: {asset} lacks explicit {context} eligibility')
            if raw['placement']['road_relation']=='remote': raise GenerationError(f'G3 settings: {asset} is deliberately remote and cannot satisfy a required connected pool')
    return c


class Reservations:
    def __init__(self): self.rows=[]; self.index={}
    def conflicts(self,rect,compatible=(),*,public_road=None,public_rects=()):
        ids={i for key in member_chunks(rect) for i in self.index.get(tuple(key),[])}
        result=[]
        for i in sorted(ids):
            row=self.rows[i]; hit=intersect(rect,row['rect'])
            if row['owner'] in compatible or not hit: continue
            share=(row['purpose']=='road' or (row['purpose']=='approach' and row.get('public_road')==public_road))
            if public_road and share and all(any(r[0]<=x<r[2] and r[1]<=y<r[3] for r in public_rects) for x,y in cells(hit)): continue
            result.append(row)
        return result
    def add(self,owner,purpose,rect,compatible=(),*,public_road=None,public_rects=()):
        conflicts=self.conflicts(rect,compatible,public_road=public_road,public_rects=public_rects)
        if conflicts: raise GenerationError(f'{owner}: {purpose} conflicts with {conflicts[0]["owner"]} ({conflicts[0]["purpose"]})')
        row=dict(id=f'reservation-{len(self.rows)}',owner=owner,purpose=purpose,rect=rect)
        if public_road: row['public_road']=public_road
        i=len(self.rows); self.rows.append(row)
        for key in member_chunks(rect): self.index.setdefault(tuple(key),[]).append(i)
        return row


def _astar(world,start,goal,budget,roads=()):
    start,goal=tuple(start),tuple(goal); queue=[(0,0,start)]; costs={start:0}; parent={}; expanded=0
    while queue and expanded<budget:
        _,g,p=heapq.heappop(queue)
        if g!=costs[p]: continue
        expanded+=1
        if p==goal:
            path=[p]
            while p!=start: p=parent[p]; path.append(p)
            return list(reversed(path)),expanded
        for dx,dy in ((0,-1),(-1,0),(1,0),(0,1)):
            q=p[0]+dx,p[1]+dy; c=world.get(*q)
            if c is None or c.biome_id=='deep_mountain' or (c.is_capital and q!=goal): continue
            step=1+(5 if c.is_river else 0)+(3 if c.biome_id in ('swamp','drowned_wood') else 0)+int(c.elevation*4)
            if q in roads: step=1
            ng=g+step
            if ng<costs.get(q,float('inf')):
                costs[q]=ng; parent[q]=p
                heapq.heappush(queue,(ng+abs(q[0]-goal[0])+abs(q[1]-goal[1]),ng,q))
    raise GenerationError(f'required road {start}->{goal}: no legal route within {budget} expanded nodes (observed {expanded})')


def _river_records(world):
    from world.world_map import ConnectorType
    from generation.ports import resolve_mouth
    records=[]
    for (wx,wy),c in sorted(world.chunks.items()):
        for edge,ports in sorted(c.edges.items()):
            for port in ports:
                if port.connector_type!=ConnectorType.RIVER: continue
                _,width,center=resolve_mouth(edge,port.position,port.width,W,H,'river')
                endpoint={'north':(center,0),'south':(center,H-1),'west':(0,center),'east':(W-1,center)}[edge]
                hub=(W//2,H//2)
                bend=(center,hub[1]) if edge in ('north','south') else (hub[0],center)
                points=[world_xy(wx,wy,*p) for p in (endpoint,bend,hub)]
                rects=bands(points,width)
                # Clip this arm to its storage chunk; boundary mouths are reciprocal.
                chunkrect=[wx*W,wy*H,(wx+1)*W,(wy+1)*H]
                rects=[r for b in rects if (r:=intersect(b,chunkrect))]
                records.append(dict(id=f'water-{wx}-{wy}-{edge}',feature=port.feature_id,rects=rects,width=width,travel_class='water'))
    return records


def build_plan(world,data,override=None,metrics=None):
    """Build a candidate without modifying the world. Publication is a separate step."""
    import time
    c=settings(data,override); rng=random.Random(stable_seed('wg3',world.seed,'sites'))
    plan=dict(version=VERSION,mode=MODE,generation_revision='wg4',dependency_projection='structure-v1',seed=world.seed,map_size=[W,H],world_size=[world.width,world.height],settings=c,
              nodes=[],routes=[],waters=_river_records(world),crossings=[],settlements=[],plots=[],placements=[],reservations=[],dependencies={},diagnostics=[])
    authority=Reservations(); chosen=[]; count=rng.randint(*c['settlement_count']); start=(world.start_wx,world.start_wy)
    reserved={p for p,ch in world.chunks.items() if ch.submaps or ch.is_capital or ch.biome_id=='deep_mountain'}
    def suitable(p):
        x,y=p
        return all((ch:=world.get(x+dx,y+dy)) is not None and (x+dx,y+dy) not in reserved and not ch.is_river
                   and ch.biome_id not in ('swamp','drowned_wood','mountain','deep_mountain') for dx in (0,1) for dy in (0,1))
    candidates=[p for p in sorted(world.chunks) if suitable(p)]
    def sep(a,b): return math.dist(a,b)
    near=[p for p in candidates if sep(p,start)<=c['near_start_radius_chunks'] and sep(p,start)>=2]
    near.sort(key=lambda p:(sep(p,start),stable_seed(world.seed,'near',p)))
    if not near: raise GenerationError('infeasible near-start settlement within configured radius; no eligible two-by-two footprint')
    chosen.append(near[0])
    ordered=sorted(candidates,key=lambda p:stable_seed(world.seed,'site',p))[:c['site_search_limit']]
    for p in ordered:
        if all(sep(p,q)>=c['minimum_separation_chunks'] for q in chosen): chosen.append(p)
        if len(chosen)==count: break
    if len(chosen)!=count: raise GenerationError(f'infeasible settlement count/separation: requested {count}, found {len(chosen)}')
    # Required river traversal chooses a straight channel using actual geography.
    bridge_candidates=[]
    for p,ch in sorted(world.chunks.items()):
        if p in reserved or not ch.is_river: continue
        sides={edge for edge,ports in ch.edges.items() if any(port.connector_type.value=='river' for port in ports)}
        if sides not in ({'north','south'},{'east','west'}): continue
        axis=(1,0) if sides=={'north','south'} else (0,1)
        a=p[0]-axis[0],p[1]-axis[1]; b=p[0]+axis[0],p[1]+axis[1]
        if all(world.get(*q) is not None and q not in reserved and not world.get(*q).is_river for q in (a,b)):
            bridge_candidates.append((sep(start,p),p,a,b))
    if not bridge_candidates: raise GenerationError('infeasible required crossing: no straight river with two available banks')
    _,bridge,a,b=min(bridge_candidates)
    capital=min(world.capital_chunks,key=lambda p:(sep(p,chosen[-1]),p))
    landmark_candidates=[p for p in candidates if all(sep(p,q)>=4 for q in chosen) and sep(p,start)>=3]
    if not landmark_candidates: raise GenerationError('infeasible separate landmark')
    landmark=min(landmark_candidates,key=lambda p:(sep(p,chosen[0]),p))
    destinations=[('start',start),('crossing-near',a),('crossing-far',b)] + [(f'settlement-{i}',p) for i,p in enumerate(chosen)] + [('capital-gateway',capital),('landmark',landmark)]
    for identifier,p in destinations: plan['nodes'].append(dict(id=identifier,chunk=list(p),xy=list(world_xy(*p,W//2,H//2)),required=True))
    roads=set()
    for i,((aid,ap),(bid,bp)) in enumerate(zip(destinations,destinations[1:])):
        if bid=='landmark': aid,ap='settlement-0',chosen[0]
        if aid=='crossing-near' and bid=='crossing-far': path=[ap,bridge,bp]; searches=0
        else: path,searches=_astar(world,ap,bp,c['route_search_nodes'],roads)
        roads.update(path)
        points=[list(world_xy(*p,W//2,H//2)) for p in path]
        route=dict(id=f'road-{i}',a=aid,b=bid,required=True,travel_class='player-and-creature',kind='country',width=c['road_width_tiles'],points=points,rects=bands(points,c['road_width_tiles']),search_nodes=searches)
        plan['routes'].append(route)
    # Route the backbone through each roadside site's two-chunk straight section.
    # This road exists before its frontage plots and has one identity for both slices.
    for i,p in enumerate(chosen):
        if c['forms'][i%2]!='roadside': continue
        sid=f'settlement-{i}'; road=next(r for r in plan['routes'] if r['a']==sid)
        goal=next(n['chunk'] for n in plan['nodes'] if n['id']==road['b'])
        east=(p[0]+1,p[1]); tail,searches=_astar(world,east,goal,c['route_search_nodes'],roads)
        road['points']=[list(world_xy(*q,W//2,H//2)) for q in [p]+tail]
        road['rects']=bands(road['points'],road['width']); road['search_nodes']=searches
    # One reservation authority; road-road junctions and assigned water crossings
    # are the only overlapping infrastructure overlays.
    for water in plan['waters']:
        for r in water['rects']:
            owners=[x['owner'] for x in authority.conflicts(expand(r,2)) if x['purpose']=='water']
            authority.add(water['id'],'water',expand(r,2),owners)
    for route in plan['routes']:
        water_hits={}
        for r in route['rects']:
            conflicts=authority.conflicts(r)
            for row in conflicts:
                if row['purpose']=='water': water_hits.setdefault(row['owner'],[]).append(intersect(r,row['rect']))
            authority.add(route['id'],'road',r,[v['owner'] for v in conflicts])
        for water,rects in sorted(water_hits.items()):
            plan['crossings'].append(dict(id=f'crossing-{len(plan["crossings"])}',road=route['id'],water=water,kind='bridge',travel_class='player-and-creature',deck=rects,approaches=[expand(r,2) for r in rects]))
    for i,p in enumerate(chosen):
        started=time.perf_counter()
        form=c['forms'][i%2]; sid=f'settlement-{i}'; x,y=world_xy(*p,0,0)
        # The roadside settlement consumes a real existing country-road segment.
        incoming=next(r for r in plan['routes'] if r['b']==sid)
        if form=='roadside':
            segments=[(u,v) for r in plan['routes'] for u,v in zip(r['points'],r['points'][1:])
                      if u[1]==v[1] and abs(u[0]-v[0])==W
                      and (min(u[0],v[0])//W,u[1]//H)==p]
            if not segments: raise GenerationError(f'{sid}: no existing straight country-road segment for roadside form')
            u,v=min(segments,key=lambda pair:(math.dist(address(*pair[0])[:2],p),pair))
            x=min(u[0],v[0])//W*W; y=u[1]//H*H
            incoming=next(r for r in plan['routes'] if any(aa==u and bb==v for aa,bb in zip(r['points'],r['points'][1:])))
            rect=[x,y,x+2*W,y+H]; street_ids=[incoming['id']]
        else:
            rect=[x,y,x+2*W,y+2*H]; street_ids=[]
            for axis in ('horizontal','vertical'):
                for n in range(2):
                    points=([[x+3,y+n*H+H//2],[x+2*W-4,y+n*H+H//2]] if axis=='horizontal' else [[x+n*W+W//2,y+H//2],[x+n*W+W//2,y+H+H//2]])
                    rid=f'{sid}-street-{axis}-{n}'; street_ids.append(rid)
                    route=dict(id=rid,a=sid,b=sid,required=True,travel_class='player-and-creature',kind='street',width=c['street_width_tiles'],points=points,rects=bands(points,c['street_width_tiles']),search_nodes=0)
                    for r in route['rects']:
                        conflicts=authority.conflicts(r)
                        if any(v['purpose']=='water' for v in conflicts): raise GenerationError(f'{sid}: street crosses unassigned water')
                        authority.add(rid,'road',r,[v['owner'] for v in conflicts])
                    plan['routes'].append(route)
        settlement=dict(id=sid,form=form,bounds=rect,members=member_chunks(rect),incoming=incoming['id'],streets=street_ids,plots=[],civic=None)
        plan['settlements'].append(settlement)
        for wx,wy in settlement['members']:
            line_y=wy*H+H//2
            rid=next((r['id'] for r in plan['routes'] if r['id'] in street_ids and any(a[1]<=line_y<a[3] and a[0]<=wx*W+W//2<a[2] for a in r['rects'])),None)
            if rid is None: continue
            for lx in range(8,W-12,c['plot_spacing_tiles']):
                for normal in ('S','N'):
                    context='civic' if form=='grid' and settlement['civic'] is None else form
                    placed=_plot(plan,authority,data,sid,context,wx,wy,lx,line_y,normal,rid,required=context=='civic')
                    settlement['plots'].append(placed['id'])
                    if context=='civic' and placed['placement']: settlement['civic']=dict(placement=placed['placement'],bell_state='spent')
        if metrics is not None: metrics.setdefault('settlements',{})[sid]=time.perf_counter()-started
    # Landmark uses a declared bounded spur to its assigned country route.
    wx,wy=landmark; route=next(r for r in plan['routes'] if r['b']=='landmark')
    found=False
    for normal in ('S','N','E','W'):
        for lx,ly in ((W//2,H//2),(W//2,10),(W//2,H-11),(16,H//2),(W-17,H//2)):
            plot=_plot(plan,authority,data,'landmark','landmark',wx,wy,lx,wy*H+ly,normal,route['id'])
            if plot['placement']:
                plot['required']=True; plan['placements'][-1]['required']=True; found=True; break
            plan['diagnostics'].append(dict(kind='landmark-alternative',rejected=plot['rejected']))
            plan['plots'].pop()
        if found: break
    if not found: raise GenerationError('essential landmark has no legal bounded spur/footprint: '+str(plan['diagnostics'][-1]))
    plan['reservations']=authority.rows
    from generation.settlement_context import semantics
    for settlement in plan['settlements']:
        settlement['semantics']=semantics(world,settlement,data,plan)
    validate_plan(plan,world.width,world.height)
    return plan


def _plot(plan,authority,data,owner,context,wx,wy,lx,line_y,normal,road_id,required=False):
    c=plan['settings']; pid=f'{owner}-plot-{len(plan["plots"])}'; chosen=None; rejected=[]
    pool=c['pools'][context]; candidates=[]
    road=next((r for r in plan['routes'] if r['id']==road_id),None)
    if road is None: raise GenerationError(f'{pid}: unknown assigned road {road_id}')
    for asset in sorted(pool):
        raw=data.structures[asset]; p=raw['placement']
        orientations=[]
        for rotation in sorted(set(p['rotations'])):
            for mirror in ((False,True) if p['mirror_x'] else (False,)):
                transformed=transform(raw,rotation,mirror)
                e=next(iter(sorted((e for e in transformed['placement']['entrances'] if e['required'] and e['normal']==normal),key=lambda e:(e['role']!='main',e['id']))),None)
                if e: orientations.append((asset,rotation,mirror,transformed,e))
        if orientations: candidates.append((asset,p['weight'],orientations))
        else: rejected.append(dict(asset=asset,rotation=None,mirror=None,reason='no eligible permitted transform for entrance normal'))
    rng=random.Random(stable_seed('wg3',plan['seed'],pid,'asset'))
    ordered=[]
    while candidates:
        selected=rng.choices(candidates,weights=[r[1] for r in candidates],k=1)[0]; candidates.remove(selected)
        orientations=list(selected[2]); rng.shuffle(orientations); ordered.extend(orientations)
    for asset,rotation,mirror,raw,e in ordered:
        p=raw['placement']; width,height=raw['width'],raw['height']
        setback=max(c['setback_tiles'],p['approach'])
        nx,ny=NORMALS[normal]
        # Measure the assigned band's actual boundary toward this building.
        half=0
        while half<=c['max_spur_tiles'] and any(r[0]<=wx*W+lx-nx*(half+1)<r[2] and r[1]<=line_y-ny*(half+1)<r[3] for r in road['rects']): half+=1
        ox=wx*W+lx-nx*(half+setback+1)-e['x']; oy=line_y-ny*(half+setback+1)-e['y']
        footprint=[ox,oy,ox+width,oy+height]; clearance=expand(footprint,p['buffer'])
        ec=[(ox+x,oy+y) for x,y in entrance_cells(e)]
        join=[wx*W+lx,line_y]
        approach=bounds(ec+[(x+nx*(half+setback+1),y+ny*(half+setback+1)) for x,y in ec])
        chunkrect=[wx*W,wy*H,(wx+1)*W,(wy+1)*H]
        spacing=c['plot_spacing_tiles']//2
        buildable=([max(chunkrect[0],join[0]-spacing),chunkrect[1]+1,min(chunkrect[2],join[0]+spacing),line_y-half-setback+1] if normal=='S' else
                   [max(chunkrect[0],join[0]-spacing),line_y+half+setback,min(chunkrect[2],join[0]+spacing),chunkrect[3]-1] if normal=='N' else chunkrect)
        try:
            if intersect(clearance,chunkrect)!=clearance or intersect(approach,chunkrect)!=approach: raise GenerationError('building, buffer or full approach spans a storage chunk')
            if intersect(footprint,buildable)!=footprint: raise GenerationError('footprint does not fit assigned buildable plot')
            conflicts=authority.conflicts(clearance)
            if conflicts: raise GenerationError(f'footprint/buffer conflicts with {conflicts[0]["owner"]}')
            conflicts=authority.conflicts(approach,public_road=road_id,public_rects=road['rects'])
            if conflicts: raise GenerationError(f'approach conflicts with {conflicts[0]["owner"]}')
            if not any(r[0]<=join[0]<r[2] and r[1]<=join[1]<r[3] for r in road['rects']): raise GenerationError('assigned road has no frontage at join; a different nearby road is insufficient')
            if max(approach[3]-approach[1],approach[2]-approach[0])-1>c['max_spur_tiles']: raise GenerationError('approach exceeds bounded spur length')
            placement=dict(id=pid+'-building',asset=asset,context=context,rotation=rotation,mirror=mirror,origin=[ox,oy],footprint=footprint,clearance=clearance,approach=approach,road=road_id,join=join,entrances=[dict(e,x=ox+e['x'],y=oy+e['y']) for e in raw['placement']['entrances']],targets=[dict(t,x=ox+t['x'],y=oy+t['y']) for t in raw['placement']['targets']],required=required,dependency=asset)
            authority.add(placement['id'],'structure',clearance)
            authority.add(placement['id'],'approach',approach,(placement['id'],),public_road=road_id,public_rects=road['rects'])
            plan['dependencies'].setdefault(asset,dependencies(data.structures[asset],data)); plan['placements'].append(placement); chosen=placement['id']; break
        except GenerationError as error: rejected.append(dict(asset=asset,rotation=rotation,mirror=mirror,reason=str(error)))
    plot=dict(id=pid,owner=owner,road=road_id,normal=normal,buildable=buildable if ordered else [wx*W,wy*H,(wx+1)*W,(wy+1)*H],setback=c['setback_tiles'],placement=chosen,status='occupied' if chosen else 'vacant-garden',required=required,rejected=rejected)
    plan['plots'].append(plot)
    if required and not chosen: raise GenerationError(f'{pid}: essential placement failed: {rejected}')
    return plot


def validate_plan(plan,width,height):
    try:
        return _validate_plan(plan,width,height)
    except (KeyError,TypeError,IndexError,AttributeError) as error:
        raise GenerationError(f'malformed saved plan record: {error}') from error


def _validate_plan(plan,width,height):
    """Durable structure/reference checks; never demand unmodified saved scene tiles."""
    if not isinstance(plan,dict) or type(plan.get('version')) is not int or (plan.get('version'),plan.get('generation_revision')) not in ((1,'wg3'),(2,'wg4')) or plan.get('mode')!=MODE: raise GenerationError('missing/corrupt required shared plan header')
    if plan['version']==2 and plan.get('dependency_projection')!='structure-v1': raise GenerationError('G4 dependency projection missing or unsupported')
    if plan.get('map_size')!=[W,H] or plan.get('world_size')!=[width,height]: raise GenerationError('G3 plan dimensions disagree')
    registries={}
    for name in ('nodes','routes','waters','crossings','settlements','plots','placements','reservations'):
        rows=plan.get(name)
        if not isinstance(rows,list): raise GenerationError('missing G3 registry '+name)
        ids=[r.get('id') for r in rows if isinstance(r,dict)]
        if len(ids)!=len(rows) or any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids): raise GenerationError('invalid/duplicate G3 '+name+' identities')
        registries[name]={r['id']:r for r in rows}
    from generation.plan_integrity import records
    records(plan,registries,width,height)
    def rect(r):
        if not isinstance(r,list) or len(r)!=4 or any(type(n) is not int for n in r) or not (0<=r[0]<r[2]<=width*W and 0<=r[1]<r[3]<=height*H): raise GenerationError('G3 rectangle outside integer world bounds')
    def point(p):
        if not isinstance(p,list) or len(p)!=2 or any(type(n) is not int for n in p) or not (0<=p[0]<width*W and 0<=p[1]<height*H): raise GenerationError('G3 point outside integer world bounds')
    if type(plan.get('seed')) is not int: raise GenerationError('G3 seed must be integer')
    for n in plan['nodes']:
        point(n['xy'])
        if n['chunk']!=list(address(*n['xy'])[:2]) or type(n['required']) is not bool: raise GenerationError('G3 node membership/status invalid')
    for route in plan['routes']:
        if type(route['width']) is not int or not 1<=route['width']<=5 or len(route['points'])<2: raise GenerationError('G3 road width/geometry invalid')
        for p in route['points']: point(p)
        if route['a'] not in registries['nodes'] or route['b'] not in registries['nodes'] or route['rects']!=bands(route['points'],route['width']): raise GenerationError('G3 route geometry or endpoints disagree')
        if route['kind']=='country' and (route['points'][0]!=registries['nodes'][route['a']]['xy'] or route['points'][-1]!=registries['nodes'][route['b']]['xy']): raise GenerationError('G3 counted country route does not physically reach assigned endpoint')
        for r in route['rects']: rect(r)
    for water in plan['waters']:
        for r in water['rects']: rect(r)
    for crossing in plan['crossings']:
        if crossing['road'] not in registries['routes'] or crossing['water'] not in registries['waters'] or crossing['kind']!='bridge' or crossing['travel_class']!='player-and-creature': raise GenerationError('G3 crossing references/class invalid')
        road=registries['routes'][crossing['road']];water=registries['waters'][crossing['water']]
        for r in crossing['deck']:
            rect(r)
            if not any(intersect(r,b)==r for b in road['rects']) or not any(intersect(r,expand(b,2))==r for b in water['rects']): raise GenerationError('G3 crossing deck does not belong to assigned road/channel')
    for s in plan['settlements']:
        rect(s['bounds'])
        if s['members']!=member_chunks(s['bounds']) or s['incoming'] not in registries['routes'] or any(p not in registries['plots'] for p in s['plots']): raise GenerationError('G3 settlement membership invalid')
    for p in plan['placements']:
        for key in ('footprint','clearance','approach'): rect(p[key])
        if len(member_chunks(p['clearance']))!=1 or member_chunks(p['clearance'])!=member_chunks(p['approach']): raise GenerationError('G3 placement spans chunks')
        if p['dependency'] not in plan['dependencies'] or p['road'] not in registries['routes']: raise GenerationError('G3 placement reference invalid')
        point(p['origin']);point(p['join'])
        if p['origin']!=p['footprint'][:2]: raise GenerationError('G3 placement origin mismatch')
        road=registries['routes'][p['road']]
        if not any(r[0]<=p['join'][0]<r[2] and r[1]<=p['join'][1]<r[3] for r in road['rects']): raise GenerationError('G3 placement join misses assigned frontage')
        for entrance in p['entrances']:
            for x,y in entrance_cells(entrance):
                if not (p['footprint'][0]<=x<p['footprint'][2] and p['footprint'][1]<=y<p['footprint'][3]): raise GenerationError('G3 entrance span leaves footprint')
        for t in p['targets']:
            point([t['x'],t['y']])
            if not (p['footprint'][0]<=t['x']<p['footprint'][2] and p['footprint'][1]<=t['y']<p['footprint'][3]): raise GenerationError('G3 target leaves footprint')
    for plot in plan['plots']:
        if plot['placement'] is None:
            if plot['required'] or plot['status']!='vacant-garden': raise GenerationError('G3 required plot silently became vacant')
        elif plot['placement'] not in registries['placements'] or plot['status']!='occupied': raise GenerationError('G3 plot placement reference invalid')
    owners=set(registries['routes'])|set(registries['waters'])|set(registries['placements'])
    for r in plan['reservations']:
        # River banks may meet the world border; clipped at realization.
        if r['owner'] not in owners or r['purpose'] not in ('water','road','structure','approach'): raise GenerationError('G3 reservation owner/purpose invalid')
    from collections import Counter
    expected=[]
    for water in plan['waters']: expected.extend((water['id'],'water',tuple(expand(r,2))) for r in water['rects'])
    for road in plan['routes']: expected.extend((road['id'],'road',tuple(r)) for r in road['rects'])
    for p in plan['placements']: expected.extend([(p['id'],'structure',tuple(p['clearance'])),(p['id'],'approach',tuple(p['approach']))])
    actual=[(r['owner'],r['purpose'],tuple(r['rect'])) for r in plan['reservations']]
    if Counter(expected)!=Counter(actual): raise GenerationError('G3 reservation geometry does not match owner')
    authority=Reservations()
    for r in plan['reservations']:
        conflicts=authority.conflicts(r['rect'])
        if r['purpose']=='water': compatible=[v['owner'] for v in conflicts if v['purpose']=='water']
        elif r['purpose']=='road':
            compatible=[v['owner'] for v in conflicts if v['purpose'] in ('water','road')]
            for water in (v for v in conflicts if v['purpose']=='water'):
                hit=intersect(r['rect'],water['rect'])
                if not any(c['road']==r['owner'] and c['water']==water['owner'] and any(intersect(hit,d)==hit for d in c['deck']) for c in plan['crossings']): raise GenerationError('G3 road/channel intersection has no owned crossing')
        elif r['purpose']=='approach':
            owner=registries['placements'][r['owner']]; road=registries['routes'][owner['road']]
            authority.add(r['owner'],r['purpose'],r['rect'],(r['owner'],),public_road=road['id'],public_rects=road['rects'])
            continue
        else: compatible=[]
        authority.add(r['owner'],r['purpose'],r['rect'],compatible)
    if not isinstance(plan.get('dependencies'),dict) or any(not isinstance(rows,dict) or any(not isinstance(v,str) or len(v)!=64 for v in rows.values()) for rows in plan['dependencies'].values()): raise GenerationError('G3 semantic dependency manifest malformed')
    reached={'start'}
    while True:
        old=len(reached)
        for r in plan['routes']:
            if r['a'] in reached or r['b'] in reached: reached.update((r['a'],r['b']))
        if len(reached)==old: break
    if any(n['required'] and n['id'] not in reached for n in plan['nodes']): raise GenerationError('G3 mandatory graph disconnected')
    return True


def publish_plan(world,plan):
    from world.world_map import RegionType,ConnectorType
    validate_plan(plan,world.width,world.height)
    world.plan_mode=MODE; world.plan=plan
    for i,s in enumerate(plan['settlements']):
        members=[tuple(p) for p in s['members']]; world.town_groups[i]=members
        for p in members:
            ch=world.get(*p); ch.region_type=RegionType.TOWN; ch.biome_id='town'; ch.town_id=i; ch.town_role='planned'
            if plan['version']==2:
                semantic=s['semantics']; member=next(m for m in semantic['members'] if m['chunk']==list(p))
                ch.name=semantic['name']; ch.town_role=member['role']; ch.zones=copy.deepcopy(member['zones'])
                ch.difficulty=member['difficulty']; ch.resonance=member['resonance']
                world.chunk_names[p]=ch.name
            world.town_chunks.add(p); world.town_chunk_ids[p]=i
    for route in plan['routes']:
        for r in route['rects']:
            for p in member_chunks(r): world.road_tiles[tuple(p)]={'type':'primary','connections':[]}
        for a,b in zip(route['points'],route['points'][1:]):
            if a[1]==b[1]:
                pairs=[((x,a[1]//H),(x+1,a[1]//H),'east','west',a[1]%H,H,'E','W') for x in range(min(a[0],b[0])//W,max(a[0],b[0])//W)]
            else:
                pairs=[((a[0]//W,y),(a[0]//W,y+1),'south','north',a[0]%W,W,'S','N') for y in range(min(a[1],b[1])//H,max(a[1],b[1])//H)]
            for p,q,edge,back,center,length,direction,reverse in pairs:
                for key,side,d in ((p,edge,direction),(q,back,reverse)):
                    ch=world.get(*key)
                    if not any(c.feature_id==route['id'] for c in ch.edges[side]):
                        ch.add_connector(side,ConnectorType.ROAD,(center-1+1e-7)/(length-2),route['id'],width=route['width'])
                    road=world.road_tiles.setdefault(key,{'type':'primary','connections':[]})
                    if d not in road['connections']: road['connections'].append(d)


def slice_plan(plan,wx,wy):
    rect=[wx*W,wy*H,(wx+1)*W,(wy+1)*H]
    result={'routes':[],'waters':[],'crossings':[],'placements':[]}
    for name,key in (('routes','rects'),('waters','rects'),('crossings','deck')):
        for row in plan[name]:
            clipped=[r for r0 in row[key] if (r:=intersect(r0,rect))]
            if clipped: result[name].append(dict(row,**{key:clipped}))
    result['placements']=[p for p in plan['placements'] if p['origin'][0]//W==wx and p['origin'][1]//H==wy]
    return result
