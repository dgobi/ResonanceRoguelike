"""Bounded JSON composition over the shared building fitter; no scene ownership.

Slots are an intentional ordered schedule, required slots first. Memberships and
rotation sets are unordered. Coordinates are tile cells, rectangles half-open.
"""
import copy
import math
import random
from collections import deque
from generation.context import GenerationError,stable_seed
from generation.placement import NORMALS,entrance_cells,transform


def require(ok,context,message):
    if not ok:raise GenerationError(f'compound {context}: {message}')


def connected_cells(points,start):
    points=set(points);start=tuple(start)
    reached={start} if start in points else set();queue=deque(reached)
    while queue:
        x,y=queue.popleft()
        for dx,dy in NORMALS.values():
            q=x+dx,y+dy
            if q in points and q not in reached:reached.add(q);queue.append(q)
    return reached


def validate_recipe(raw,data):
    from generation.world_plan import cells,intersect
    from generation.poi_selection import require_usable_goal
    name=raw.get('id','unknown') if isinstance(raw,dict) else 'unknown'
    check=lambda ok,msg:require(ok,name,msg)
    check(isinstance(raw,dict) and set(raw)=={'version','id','size','rotations','gate','paths','slots','fit_budget'},'expected complete version-one recipe')
    check(type(raw['version']) is int and raw['version']==1,'unsupported recipe version')
    check(isinstance(name,str) and name and all(c.isalnum() or c in '_-' for c in name),'invalid recipe ID')
    size=raw['size'];check(isinstance(size,list) and len(size)==2 and all(type(v) is int and 4<=v<=80 for v in size),'size must be two integer bounds 4..80')
    w,h=size;outer=[0,0,w,h]
    def rect(r):return isinstance(r,list) and len(r)==4 and all(type(v) is int for v in r) and 0<=r[0]<r[2]<=w and 0<=r[1]<r[3]<=h
    def point(p):return isinstance(p,list) and len(p)==2 and all(type(v) is int for v in p) and 0<=p[0]<w and 0<=p[1]<h
    turns=raw['rotations'];check(isinstance(turns,list) and turns and all(type(v) is int and v in (0,90,180,270) for v in turns) and len(set(turns))==len(turns),'rotations must be unique quarter turns')
    check(all((h<=80 and w<=43) if r%180 else (w<=80 and h<=43) for r in turns),'envelope cannot fit one 80x43 chunk in declared rotation')
    check(type(raw['fit_budget']) is int and 2<=raw['fit_budget']<=256,'fit_budget must be integer 2..256 actual child transform trials')
    paths=raw['paths'];check(isinstance(paths,list) and 1<=len(paths)<=8,'declare 1..8 named paths')
    names=set();path_cells={}
    for path in paths:
        check(isinstance(path,dict) and set(path)=={'id','rects','joins'},'path needs id, rects and joins')
        pid=path['id'];check(isinstance(pid,str) and pid and pid not in names,'duplicate/invalid path ID');names.add(pid)
        check(isinstance(path['rects'],list) and 1<=len(path['rects'])<=16 and all(rect(r) for r in path['rects']),pid+': path outside envelope or empty/unbounded geometry')
        pts=set().union(*(cells(r) for r in path['rects']));path_cells[pid]=pts
        check(connected_cells(pts,min(pts))==pts,pid+': disconnected common path (corner contact is insufficient)')
        check(isinstance(path['joins'],list) and all(isinstance(v,str) for v in path['joins']) and len(set(path['joins']))==len(path['joins']),pid+': invalid joins')
    for path in paths:
        for other in path['joins']:
            check(other in names and other!=path['id'],path['id']+': unknown/self path join')
            check(path['id'] in next(p['joins'] for p in paths if p['id']==other),path['id']+': nonreciprocal path join')
            pts=path_cells[path['id']]|path_cells[other]
            check(connected_cells(pts,min(pts))==pts,path['id']+': declared join is disconnected')
    gate=raw['gate'];check(isinstance(gate,dict) and set(gate)=={'id','x','y','normal','width','path'},'gate needs id, x, y, normal, width and path')
    check(isinstance(gate['id'],str) and gate['id'] and gate['normal'] in NORMALS and gate['path'] in names,'invalid gate identity/normal/path')
    check(type(gate['width']) is int and 1<=gate['width']<=5 and point([gate['x'],gate['y']]),'invalid gate coordinates/width')
    gc=entrance_cells(gate)
    check(all(point(list(p)) and {'S':p[1]==h-1,'N':p[1]==0,'E':p[0]==w-1,'W':p[0]==0}[gate['normal']] for p in gc),'full gate span must face outward at envelope edge')
    all_paths=set().union(*path_cells.values());pts=all_paths|set(gc)
    check(connected_cells(pts,gc[0])==pts,'gate or required circulation disconnected')
    declared={gate['path']};queue=[gate['path']]
    for name_path in queue:
        for other in next(p['joins'] for p in paths if p['id']==name_path):
            if other not in declared:declared.add(other);queue.append(other)
    check(declared==names,'paths need declared joins to the gate path')
    slots=raw['slots'];check(isinstance(slots,list) and 2<=len(slots)<=3,'declare two required slots and at most one optional slot')
    ids=set();optional=False
    for slot in slots:
        check(isinstance(slot,dict) and set(slot)=={'id','role','required','buildable','path','join','normal','rotations','assets'},'slot fields incomplete')
        sid=slot['id'];check(isinstance(sid,str) and sid and all(c.isalnum() or c in '_-' for c in sid) and sid not in ids,'invalid/duplicate slot ID');ids.add(sid)
        check(isinstance(slot['role'],str) and slot['role'] and type(slot['required']) is bool,sid+': invalid role/required')
        check(not (optional and slot['required']),sid+': required slots must precede optional slot');optional|=not slot['required']
        check(rect(slot['buildable']),sid+': buildable outside envelope')
        check(not cells(slot['buildable'])&all_paths,sid+': private buildable region consumes common circulation')
        check(slot['path'] in names and point(slot['join']) and tuple(slot['join']) in path_cells.get(slot['path'],set()) and slot['normal'] in NORMALS,sid+': unknown path or join outside its circulation')
        rotations=slot['rotations'];check(isinstance(rotations,list) and rotations and all(type(r) is int and r in (0,90,180,270) for r in rotations) and len(set(rotations))==len(rotations),sid+': invalid base child rotations')
        check(isinstance(slot['assets'],list) and 1<=len(slot['assets'])<=16,sid+': empty/unbounded child membership')
        seen=set()
        for rule in slot['assets']:
            check(isinstance(rule,dict) and set(rule)=={'asset','weight'},sid+': child membership needs asset and weight')
            aid=rule['asset'];check(isinstance(aid,str) and aid not in seen and aid in data.structures,sid+': unknown/duplicate child '+str(aid));seen.add(aid)
            check(type(rule['weight']) in (int,float) and math.isfinite(rule['weight']) and 0<rule['weight']<=1000,sid+': finite positive child weight required')
            p=data.structures[aid].get('placement',{})
            check('compound' in p.get('contexts',[]) and p.get('road_relation') in ('frontage','spur'),sid+': '+aid+' needs explicit connected compound context')
            require_usable_goal(data.structures[aid],f'compound {raw["id"]} child slot {sid}')
        for turn in turns:
            check(any(any((r+turn)%360 in data.structures[a['asset']]['placement']['rotations'] for r in rotations) for a in slot['assets']) or not slot['required'],sid+': forbidden effective child transform for parent '+str(turn))
    check(sum(s['required'] for s in slots)==2,'exactly two required child slots')
    for i,s in enumerate(slots):
        check(not any(intersect(s['buildable'],t['buildable']) for t in slots[i+1:]),s['id']+': sibling private buildable regions overlap')
    result=copy.deepcopy(raw);result['rotations'].sort();result['paths'].sort(key=lambda p:p['id'])
    for path in result['paths']:path['rects'].sort();path['joins'].sort()
    for slot in result['slots']:slot['assets'].sort(key=lambda r:r['asset']);slot['rotations'].sort()
    return result


def geometry(recipe,rotation):
    """Transform recipe cells/spans, never silently expand child permissions."""
    from generation.world_plan import bounds,cells
    w,h=recipe['size']
    def xy(x,y):return ((x,y),(h-1-y,x),(w-1-x,h-1-y),(y,w-1-x))[rotation//90]
    def rect(r):return bounds([xy(x,y) for x,y in cells(r)])
    def normal(n):return 'NESW'[('NESW'.index(n)+rotation//90)%4]
    gate=recipe['gate'];gc=[xy(x,y) for x,y in entrance_cells(gate)]
    return dict(size=[h,w] if rotation%180 else [w,h],
                gate=dict(gate,x=min(x for x,y in gc),y=min(y for x,y in gc),normal=normal(gate['normal'])),
                paths=[dict(p,rects=[rect(r) for r in p['rects']]) for p in recipe['paths']],
                slots=[dict(s,buildable=rect(s['buildable']),join=list(xy(*s['join'])),normal=normal(s['normal'])) for s in recipe['slots']])


def fit(plan,authority,data,recipe,candidate,sid,rotation,remaining):
    """One staged parent trial, bounded backtracking within its child budget."""
    from generation.world_plan import staged,_plot,address,intersect,bounds,cells
    q,a=staged(plan,authority);q['paths']=list(plan.get('paths',[]))
    moved=geometry(recipe,rotation);gate=moved['gate'];normal=gate['normal']
    counters=dict(child_trials=0,budget_exhausted=False,rejections=[])
    def failed(message):
        counters['rejections'].append(dict(parent=sid,rotation=rotation,reason=message));return None,counters
    if normal!=candidate['normal']:return failed('parent rotation has incompatible gate normal')
    wx,wy,_,_=address(*candidate['join']);chunk=[wx*80,wy*43,(wx+1)*80,(wy+1)*43]
    road=next(r for r in plan['routes'] if r['id']==candidate['road']);nx,ny=NORMALS[normal];jx,jy=candidate['join']
    half=0
    while half<=plan['settings']['max_spur_tiles'] and any(r[0]<=jx-nx*(half+1)<r[2] and r[1]<=jy-ny*(half+1)<r[3] for r in road['rects']):half+=1
    length=half+plan['settings']['setback_tiles']+1
    ox,oy=jx-nx*length-gate['x'],jy-ny*length-gate['y']
    def translated(r):return [r[0]+ox,r[1]+oy,r[2]+ox,r[3]+oy]
    outer=[ox,oy,ox+moved['size'][0],oy+moved['size'][1]]
    gate=dict(gate,x=gate['x']+ox,y=gate['y']+oy,path=sid+'-path-'+gate['path'])
    gc=entrance_cells(gate);approach=bounds(gc+[(x+nx*length,y+ny*length) for x,y in gc])
    if length>plan['settings']['max_spur_tiles']:return failed('external approach exceeds bounded spur length')
    if intersect(outer,chunk)!=outer or intersect(approach,chunk)!=approach:return failed('parent envelope or full external approach spans a storage chunk')
    if any(intersect(r,g) for c in plan.get('crossings',[]) for r in c['approaches'] for g in (outer,approach)):return failed('bridge deck or approach clearance')
    paths=[dict(id=sid+'-path-'+p['id'],owner=sid,name=p['id'],rects=[translated(r) for r in p['rects']],joins=[sid+'-path-'+v for v in p['joins']]) for p in moved['paths']]
    members=[sid]+[p['id'] for p in paths]+[sid+'-slot-'+s['id']+'-building' for s in moved['slots']]
    try:
        a.add(sid,'envelope',outer,members=members,gate=bounds(gc))
        # Declared path joins alone may share actual circulation cells.
        for p in paths:
            for r in p['rects']:
                a.add(p['id'],'path',r,(p['id'],*p['joins']),container=sid)
        a.add(sid,'approach',approach,public_road=road['id'],public_rects=road['rects'],container=sid,shared_path=gate['path'])
    except GenerationError as error:return failed(str(error))
    q['paths'].extend(paths)
    budget=min(recipe['fit_budget'],remaining)
    def search(p,b,index,slots):
        if index==len(moved['slots']):return p,b,slots
        s=moved['slots'][index];original=recipe['slots'][index];path=sid+'-path-'+s['path']
        options=[];rng=random.Random(stable_seed('wg7',plan['seed'],sid,s['id'],'children'))
        weighted=list(s['assets'])
        while weighted:
            rule=rng.choices(weighted,weights=[r['weight']*data.structures[r['asset']]['placement']['weight'] for r in weighted],k=1)[0];weighted.remove(rule)
            raw=data.structures[rule['asset']];turns=[(r+rotation)%360 for r in s['rotations'] if (r+rotation)%360 in raw['placement']['rotations']];rng.shuffle(turns)
            for turn in turns:
                transformed=transform(raw,turn,False)
                entrances=sorted((e for e in transformed['placement']['entrances'] if e['required'] and e['normal']==s['normal']),key=lambda e:(e['role']!='main',e['id']))
                if entrances:options.append((rule['asset'],turn,False,transformed,entrances[0]))
            if not turns:options.append((rule['asset'],None,None,None,None))
        slot=dict(id=s['id'],role=s['role'],required=s['required'],buildable=translated(s['buildable']),path=path,normal=s['normal'],
                  assets=copy.deepcopy(s['assets']),effective_rotations=sorted({(r+rotation)%360 for r in s['rotations']}),placement=None,plot=None,omission=None)
        for option in options:
            if counters['child_trials']>=budget:counters['budget_exhausted']=True;break
            counters['child_trials']+=1;pp,bb=staged(p,b)
            join=[ox+s['join'][0],oy+s['join'][1]]
            # Entrance spans have positive-axis anchors. Rotate the whole span,
            # including its anchor reversal, rather than only the first cell.
            tangent=(1,0) if original['normal'] in 'NS' else (0,1)
            for _ in range(rotation//90):tangent=(-tangent[1],tangent[0])
            if option[4] and min(tangent)<0:
                join[0]+=min(tangent[0],0)*(option[4]['width']-1);join[1]+=min(tangent[1],0)*(option[4]['width']-1)
            plot=_plot(pp,bb,data,sid,'compound',wx,wy,join[0]-wx*80,join[1],s['normal'],None,
                       role=s['role'],slot_order=index,option=option,explicit_bounds=slot['buildable'],
                       internal_access=dict(kind='internal',parent=sid,path=path),identity=sid+'-slot-'+s['id'])
            if not plot['placement']:
                counters['rejections'].append(dict(parent=sid,slot=s['id'],asset=option[0],rotation=option[1],failures=plot['rejected']));counters['rejections']=counters['rejections'][-24:];continue
            placement=pp['placements'][-1];placement.update(required=True,parent=sid,slot=s['id']);plot.update(required=True,slot=s['id'])
            selected=dict(slot,placement=placement['id'],plot=plot['id'],join=placement['join'],goals=[i for i,t in enumerate(placement['targets']) if t['required']])
            found=search(pp,bb,index+1,slots+[selected])
            if found:return found
            if counters['budget_exhausted']:break
        if not s['required']:
            return search(p,b,index+1,slots+[dict(slot,join=[ox+s['join'][0],oy+s['join'][1]],goals=[],omission='child fit budget exhausted' if counters['budget_exhausted'] else 'all enumerated child alternatives exhausted')])
        return None
    found=search(q,a,0,[])
    if found is None:return failed('required-child fit budget exhausted; feasibility unresolved' if counters['budget_exhausted'] else 'required-child alternatives exhausted')
    q,a,slots=found
    parent=dict(id=sid,kind='compound',profile=plan['poi_policy']['id'],recipe=recipe['id'],recipe_version=recipe['version'],chunk=[wx,wy],node=sid,
                origin=[ox,oy],size=moved['size'],rotation=rotation,envelope=outer,gate=gate,approach=approach,paths=[p['id'] for p in paths],slots=slots,
                attachment=dict(candidate,frontage=gate['id']),fit=dict(budget=recipe['fit_budget'],trials=counters['child_trials']))
    allowed=[sid]+parent['paths']+[s['placement'] for s in slots if s['placement']]
    a.rows=[dict(r,members=allowed) if r['owner']==sid and r['purpose']=='envelope' else r for r in a.rows]
    return (q,a,parent),counters


def certify(recipe,data,settings):
    """Reject unfit mandatory capacity independently of country location trials."""
    from generation.world_plan import Reservations,bands
    for rotation in recipe['rotations']:
        normal=geometry(recipe,rotation)['gate']['normal'];vertical=normal in 'EW'
        points=[[40,0],[40,42]] if vertical else [[0,21],[79,21]]
        road=dict(id='certification-road',kind='country',width=settings['road_width_tiles'],points=points,rects=bands(points,settings['road_width_tiles']))
        p=dict(seed=0,settings=settings,routes=[road],crossings=[],paths=[],plots=[],placements=[],dependencies={},poi_policy=dict(id='certification'))
        a=Reservations()
        for r in road['rects']:a.add(road['id'],'road',r)
        candidate=dict(join=[40,21],normal=normal,road=road['id'],segment=0,tangent=[0,1] if vertical else [1,0],side={'N':'south','S':'north','E':'west','W':'east'}[normal])
        found,work=fit(p,a,data,recipe,candidate,'certification',rotation,recipe['fit_budget'])
        require(found is not None,recipe['id'],f'unfit mandatory child capacity/forbidden transform at rotation {rotation}: {work}')
    return recipe
