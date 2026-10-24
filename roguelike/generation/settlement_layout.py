"""Bounded orthogonal town composition, resolved before asset selection.

Routes own geometry. Blocks are disjoint free rectangles derived from actual
road bands and public ground; they grant no reservation overlap permissions.
All coordinates are integer world tiles and rectangles are half open.
"""
import copy
import math
import random
from collections import Counter
from generation.context import GenerationError,stable_seed
from generation.placement import digest,NORMALS,entrance_cells


def require(ok,message):
    if not ok:raise GenerationError('settlement layout: '+message)


def validate(config,data=None):
    from generation.world_plan import bands,cells,intersect
    from generation.compounds import connected_cells
    require(isinstance(config,dict) and set(config)=={'version','alternative_limit','grid','roadside'},'expected complete version 1 layout settings')
    require(type(config['version']) is int and config['version']==1,'unsupported version')
    require(type(config['alternative_limit']) is int and 1<=config['alternative_limit']<=4,'alternative_limit must be 1..4')
    require(isinstance(config['grid'],list) and 1<=len(config['grid'])<=4,'declare 1..4 bounded grid alternatives')
    seen=set()
    for layout in config['grid']:
        require(set(layout)=={'id','form','weight','streets','common','civic_lot','frontage_tiles','minimum_depth','junction_clearance'},'incomplete grid layout')
        name=layout['id'];require(isinstance(name,str) and name and all(c.isalnum() or c in '-_' for c in name) and name not in seen,'duplicate/invalid layout ID');seen.add(name)
        require(layout['form']=='grid','only grid templates are supported')
        require(type(layout['weight']) in (int,float) and math.isfinite(layout['weight']) and 0<layout['weight']<=1000,name+': positive finite weight required')
        dimensions(layout)
        def rect(r):return isinstance(r,list) and len(r)==4 and all(type(v) is int for v in r) and 0<=r[0]<r[2]<=160 and 0<=r[1]<r[3]<=86
        def point(p):return isinstance(p,list) and len(p)==2 and all(type(v) is int for v in p) and 0<=p[0]<160 and 0<=p[1]<86
        require(isinstance(layout['streets'],list) and 4<=len(layout['streets'])<=8,name+': 4..8 streets required')
        names=set()
        for road in layout['streets']:
            require(set(road)=={'id','points'} and isinstance(road['id'],str) and road['id'] and road['id'] not in names,name+': invalid/duplicate street')
            names.add(road['id']);pts=road['points']
            require(isinstance(pts,list) and len(pts)==2 and all(point(p) for p in pts) and pts[0]!=pts[1] and (pts[0][0]==pts[1][0] or pts[0][1]==pts[1][1]),name+': street must be a nonempty orthogonal segment')
        common=layout['common'];require(set(common)=={'id','rect','surface','furnishing'},name+': common needs id, rect, surface, furnishing')
        require(isinstance(common['id'],str) and common['id'] and rect(common['rect']),name+': invalid common')
        require(common['surface'] in ('cobblestone','dirt_path','grass'),name+': surface must be cobblestone, dirt_path or grass')
        if data is not None:require(data.terrain.get(common['surface'],{}).get('walkable') is True,name+': public surface must be walkable')
        f=common['furnishing'];require(isinstance(f,list) and len(f)==2 and all(point(p) and tuple(p) in cells(common['rect']) for p in f) and f[1]==[f[0][0]+1,f[0][1]],name+': furnishing must be adjacent stone/prayer cells inside common')
        lot=layout['civic_lot'];require(set(lot)=={'bounds','join','normal','street'} and rect(lot['bounds']) and point(lot['join']) and lot['normal'] in NORMALS and lot['street'] in names,name+': invalid civic lot')
        require(not intersect(lot['bounds'],common['rect']),name+': civic private lot overlaps common')
        require(any(lot['bounds'][i]==common['rect'][j] for i,j in ((0,2),(2,0),(1,3),(3,1))) and bool(cells(lot['bounds']) & {(x+dx,y+dy) for x,y in cells(common['rect']) for dx,dy in NORMALS.values()}),name+': civic lot must sit beside common')
    dimensions(config['roadside'])
    require(set(config['roadside'])=={'id','frontage_tiles','minimum_depth','junction_clearance'} and isinstance(config['roadside']['id'],str) and config['roadside']['id'],'invalid roadside profile')
    result=copy.deepcopy(config);result['grid'].sort(key=lambda r:r['id'])
    for layout in result['grid']:layout['streets'].sort(key=lambda r:r['id'])
    return result


def dimensions(layout):
    for key,lo,hi in [('frontage_tiles',14,32),('minimum_depth',8,20),('junction_clearance',1,8)]:
        require(type(layout.get(key)) is int and lo<=layout[key]<=hi,key+f' must be integer {lo}..{hi}')


def primary_arrival(route,outer):
    """First entry while walking the actual incoming route in its saved direction."""
    from generation.world_plan import cells
    for segment,(a,b) in enumerate(zip(route['points'],route['points'][1:])):
        dx=(b[0]>a[0])-(b[0]<a[0]);dy=(b[1]>a[1])-(b[1]<a[1])
        for n in range(abs(b[0]-a[0])+abs(b[1]-a[1])+1):
            xy=[a[0]+dx*n,a[1]+dy*n]
            if outer[0]<=xy[0]<outer[2] and outer[1]<=xy[1]<outer[3]:
                return dict(road=route['id'],segment=segment,position=xy,direction=next(k for k,v in NORMALS.items() if v==(dx,dy)))
    raise GenerationError('incoming country road never enters settlement')


def local_connectivity(routes,outer):
    from generation.world_plan import cells,intersect,member_chunks
    from generation.compounds import connected_cells
    for wx,wy in member_chunks(outer):
        chunk=[wx*80,wy*43,(wx+1)*80,(wy+1)*43]
        points=set().union(*(cells(hit) for road in routes for r in road['rects'] if (hit:=intersect(r,chunk))))
        require(bool(points) and connected_cells(points,min(points))==points,f'road slice {wx},{wy} must connect inside its member chunk; leaving and re-entering is unsupported')


def free_blocks(outer,obstacles):
    """Canonical horizontal runs merged over identical adjacent rows."""
    from generation.world_plan import cells,intersect,member_chunks
    result=[]
    for wx,wy in member_chunks(outer):
        chunk=[wx*80+1,wy*43+1,(wx+1)*80-1,(wy+1)*43-1]
        blocked=set().union(*(cells(hit) for r in obstacles if (hit:=intersect(r,chunk))))
        active={}
        for y in range(chunk[1],chunk[3]+1):
            runs=[];start=None
            for x in range(chunk[0],chunk[2]+1):
                free=y<chunk[3] and x<chunk[2] and (x,y) not in blocked
                if free and start is None:start=x
                if not free and start is not None:runs.append((start,x));start=None
            for span in list(active):
                if span not in runs:result.append(active.pop(span))
            for left,right in runs:
                if (left,right) in active:active[left,right][3]=y+1
                else:active[left,right]=[left,y,right,y+1]
    return sorted(result)


def frontage_sides(block,routes,clearance):
    """One exact straight segment and a trimmed tangent span for each usable side."""
    from generation.world_plan import bands
    result=[]
    for road in sorted(routes,key=lambda r:r['id']):
        for segment,(a,b) in enumerate(zip(road['points'],road['points'][1:])):
            r=bands([a,b],road['width'])[0]
            options=[('S',block[3]==r[1],0,a[1]),('N',block[1]==r[3],0,a[1])] if a[1]==b[1] else [('E',block[2]==r[0],1,a[0]),('W',block[0]==r[2],1,a[0])]
            for normal,adjacent,axis,line in options:
                if not adjacent:continue
                lo=max(block[axis],r[axis]+clearance);hi=min(block[axis+2],r[axis+2]-clearance)
                # Corner parcels are trimmed at perpendicular bands, including
                # coincident country/street geometry. This never changes routes.
                for other in routes:
                    for u,v in zip(other['points'],other['points'][1:]):
                        if (u[1]==v[1])==(a[1]==b[1]):continue
                        cr=bands([u,v],other['width'])[0]
                        if cr[1-axis]<=line<cr[3-axis]:
                            if cr[axis+2]<=lo:lo=max(lo,cr[axis+2]+clearance)
                            elif cr[axis]>=hi:hi=min(hi,cr[axis]-clearance)
                            elif cr[axis]<hi and cr[axis+2]>lo:hi=min(hi,cr[axis]-clearance)
                if hi-lo>=8:result.append(dict(road=road['id'],segment=segment,normal=normal,span=[lo,hi],axis=axis,line=line))
    return result


def propose(plan,authority,settlement,layout,data):
    from generation.world_plan import bands,intersect,cells
    sid=settlement['id'];x,y=settlement['bounds'][:2];roads=[]
    def moved(r):return [r[0]+x,r[1]+y,r[2]+x,r[3]+y]
    if settlement['form']=='grid':
        for raw in sorted(layout['streets'],key=lambda r:r['id']):
            points=[[a+x,b+y] for a,b in raw['points']];rid=sid+'-street-'+raw['id'];width=plan['settings']['street_width_tiles']
            road=dict(id=rid,a=sid,b=sid,required=True,travel_class='player-and-creature',kind='street',width=width,points=points,rects=bands(points,width),search_nodes=0)
            require(all(intersect(r,settlement['bounds'])==r for r in road['rects']),layout['id']+': street band leaves fixed town bounds')
            for r in road['rects']:
                conflicts=authority.conflicts(r);require(all(v['purpose']=='road' for v in conflicts),'local street consumes protected non-road geometry')
                authority.add(rid,'road',r,[v['owner'] for v in conflicts])
            plan['routes'].append(road);roads.append(road)
        settlement['streets']=[r['id'] for r in roads]
    else:roads=[next(r for r in plan['routes'] if r['id']==settlement['incoming'])]
    local_routes=[r for r in plan['routes'] if any(intersect(b,settlement['bounds']) for b in r['rects'])]
    local_connectivity(local_routes,settlement['bounds'])
    settlement['layout']=dict(id=layout['id'],version=1,signature=digest(layout),frontage_tiles=layout['frontage_tiles'],minimum_depth=layout['minimum_depth'],junction_clearance=layout['junction_clearance'])
    incoming=next(r for r in plan['routes'] if r['b']==sid and r['kind']=='country')
    settlement['arrival']=primary_arrival(incoming,settlement['bounds'])
    settlement['blocks']=[];settlement['commons']=[];slots=[];obstacles=[r for road in local_routes for r in road['rects']]
    if settlement['form']=='grid':
        raw=layout['common'];rect=moved(raw['rect']);cid=sid+'-common-'+raw['id']
        require(not authority.conflicts(rect),layout['id']+': public common conflicts with incoming/outgoing country road or protected infrastructure')
        furnishing=[[a+x,b+y] for a,b in raw['furnishing']]
        public=dict(id=cid,owner=sid,purpose='civic-common',rects=[rect],surface=raw['surface'],surface_dependency=digest({k:data.terrain[raw['surface']].get(k,True) for k in ('walkable','transparent')}),furnishing=furnishing,civic=None)
        plan['public_spaces'].append(public);settlement['commons']=[cid];authority.add(cid,'common',rect)
        raw=layout['civic_lot'];bounds=moved(raw['bounds']);join=[raw['join'][0]+x,raw['join'][1]+y];rid=sid+'-street-'+raw['street']
        require(not authority.conflicts(bounds),'designated civic private lot conflicts with infrastructure')
        bid=sid+'-block-civic';pid=sid+'-'+layout['id']+'-lot-civic'
        block=dict(id=bid,owner=sid,bounds=bounds,purpose='civic-private',lots=[pid]);plan['blocks'].append(block);settlement['blocks'].append(bid)
        normal=raw['normal'];axis=0 if normal in ('N','S') else 1
        lot=dict(id=pid,block=bid,owner=sid,bounds=bounds,join=join,frontage=dict(road=rid,segment=0,span=[bounds[axis],bounds[axis+2]],normal=normal),civic=True)
        slots.append(lot);obstacles.extend([rect,bounds])
    for bounds in free_blocks(settlement['bounds'],obstacles):
        bx,by=bounds[0]-x,bounds[1]-y;bid=f'{sid}-block-{bx}-{by}'
        block=dict(id=bid,owner=sid,bounds=bounds,purpose='garden',lots=[]);plan['blocks'].append(block);settlement['blocks'].append(bid)
        sides=frontage_sides(bounds,roads,layout['junction_clearance'])
        sides=[f for f in sides if f['span'][1]-f['span'][0]>=14 and bounds[3-f['axis']]-bounds[1-f['axis']]>=layout['minimum_depth']]
        if not sides:continue
        # Alternating quadrant preference creates actual frontage on each axis;
        # all sides must still be geometrically legal and fitted by production.
        prefer_vertical=((bx//80+by//43+int(bx%80>30)+int(by%43>22))%2==0)
        side=min(sides,key=lambda f:((f['axis']==1)!=prefer_vertical,f['road'],f['segment'],f['normal']))
        axis=side['axis'];lo,hi=side['span'];count=max(1,(hi-lo)//layout['frontage_tiles'])
        for n in range(count):
            left=lo+(hi-lo)*n//count;right=lo+(hi-lo)*(n+1)//count
            private=list(bounds);private[axis]=left;private[axis+2]=right
            tangent=(left+right)//2;join=[tangent,side['line']] if axis==0 else [side['line'],tangent]
            pid=f'{sid}-{layout["id"]}-lot-{bx}-{by}-{side["normal"]}-{n}'
            lot=dict(id=pid,block=bid,owner=sid,bounds=private,join=join,frontage={k:side[k] for k in ('road','segment','normal')},civic=False)
            lot['frontage']['span']=[left,right];slots.append(lot);block['lots'].append(pid);block['purpose']='private-lots'
    anchor=settlement['arrival']['position']
    slots.sort(key=lambda s:(not s['civic'],abs(s['join'][0]-anchor[0])+abs(s['join'][1]-anchor[1]),s['id']))
    for order,lot in enumerate(slots):lot['order']=order
    return slots


def compose(plan,authority,data,sid,form,outer,incoming,metrics=None):
    """Whole alternatives stage routes, public ground, roles and dependencies."""
    from generation.world_plan import staged,member_chunks
    from generation.settlement_selection import populate_settlement
    config=validate(data.settlement_layouts,data)
    choices=sorted(config['grid'],key=lambda r:r['id']) if form=='grid' else [config['roadside']]
    rng=random.Random(stable_seed('wg8',plan['seed'],sid,'layout'));ordered=[]
    while choices:
        chosen=rng.choices(choices,weights=[r.get('weight',1) for r in choices],k=1)[0];choices.remove(chosen);ordered.append(chosen)
    budget=plan['selection']['profiles'][form]['required_fit_budget'];work=dict(attempts=0,budget=budget);failures=[]
    for layout in ordered[:config['alternative_limit']]:
        q,a=staged(plan,authority)
        for key in ('routes','settlements','blocks','public_spaces','diagnostics'):q[key]=list(plan[key])
        settlement=dict(id=sid,form=form,bounds=outer,members=member_chunks(outer),incoming=incoming['id'],streets=[incoming['id']],plots=[],civic=None)
        q['settlements'].append(settlement)
        try:
            lots=propose(q,a,settlement,layout,data)
            populate_settlement(q,a,data,settlement,lots,work=work)
            if form=='grid':
                common=next(c for c in q['public_spaces'] if c['id'] in settlement['commons']);common['civic']=settlement['civic']['placement'];settlement['civic']['common']=common['id']
            settlement['composition_work']=dict(required_trials=work['attempts'],optional_trials=sum(p['fit_trials'] for p in q['plots'] if p['owner']==sid and not p['required']),candidate_lots=len(lots),budget=budget,alternatives=len(failures)+1,rejected=failures)
            plan.update(q);authority.rows=a.rows;authority.index=a.index
            return settlement
        except GenerationError as error:
            failures.append(dict(layout=layout['id'],reason=str(error)))
            if work['attempts']>=budget:break
    reason='shared required-fit budget exhausted; feasibility unresolved' if work['attempts']>=budget else 'bounded layout alternatives exhausted'
    raise GenerationError(f'{sid}: {reason}; {work["attempts"]}/{budget} transform trials; {failures}')


def validate_resolved(plan,registries):
    """Reciprocal saved ownership and exact geometry, without current recipes."""
    from generation.world_plan import intersect,cells,member_chunks,bands
    from generation.compounds import connected_cells
    from generation.placement import frontage_entrance
    require(plan.get('layout_contract')==1 and (plan['version'],plan['settings']['version']) in ((6,3),(7,4)) and plan['settings']['settlement_layout_version']==1,'missing supported G8 layout contract')
    blocks=registries['blocks'];commons=registries['public_spaces'];plots=registries['plots'];placed=registries['placements'];routes=registries['routes']
    def rectangle(r):return isinstance(r,list) and len(r)==4 and all(type(n) is int for n in r) and 0<=r[0]<r[2]<=plan['world_size'][0]*80 and 0<=r[1]<r[3]<=plan['world_size'][1]*43
    all_blocks=[];all_common=[]
    for s in plan['settlements']:
        sid=s['id'];layout=s['layout']
        require(set(layout)=={'id','version','signature','frontage_tiles','minimum_depth','junction_clearance'} and layout['version']==1 and isinstance(layout['id'],str) and layout['id'] and len(layout['signature'])==64,sid+': invalid resolved layout')
        dimensions(layout)
        require(s['bounds'][2]-s['bounds'][0]==160 and s['bounds'][3]-s['bounds'][1]==(86 if s['form']=='grid' else 43),sid+': fixed settlement footprint changed')
        incoming=routes[s['arrival']['road']]
        require(incoming['b']==sid and incoming['kind']=='country',sid+': arrival road must retain its original destination')
        require(s['arrival']==primary_arrival(incoming,s['bounds']),sid+': arrival is not the actual canonical incoming entry')
        local_connectivity([r for r in plan['routes'] if any(intersect(b,s['bounds']) for b in r['rects'])],s['bounds'])
        require(len(s['blocks'])==len(set(s['blocks'])) and len(s['commons'])==int(s['form']=='grid'),sid+': duplicate blocks or missing common')
        all_blocks+=s['blocks'];all_common+=s['commons'];owned=[];listed=[]
        for bid in s['blocks']:
            b=blocks.get(bid);require(b is not None and b['owner']==sid,sid+': foreign/missing block')
            r=b['bounds'];require(rectangle(r) and intersect(r,s['bounds'])==r and len(member_chunks(r))==1,bid+': block outside owner/storage chunk')
            require(not any(intersect(r,other) for other in owned),bid+': overlapping private block bounds');owned.append(r)
            require(b['purpose'] in ('civic-private','private-lots','garden') and (b['purpose']=='garden')==(not b['lots']),bid+': contradictory block purpose')
            require(len(b['lots'])==len(set(b['lots'])),bid+': duplicate lot membership');listed+=b['lots']
            lot_bounds=[]
            for pid in b['lots']:
                p=plots.get(pid);require(p is not None and p.get('block')==bid and p['owner']==sid,bid+': foreign/missing lot')
                require(p['civic_lot']==(b['purpose']=='civic-private'),pid+': civic lot ownership mismatch')
                r=p['buildable'];require(intersect(r,b['bounds'])==r and not any(intersect(r,other) for other in lot_bounds),pid+': private lot outside block or overlapping sibling');lot_bounds.append(r)
                f=p['frontage'];require(set(f)=={'road','segment','normal','span'} and f['road']==p['road'] and p['road'] in s['streets'] and f['normal']==p['normal'],pid+': wrong frontage owner/route')
                road=routes[p['road']];segment=f['segment'];require(type(segment) is int and 0<=segment<len(road['points'])-1,pid+': wrong frontage segment')
                a,z=road['points'][segment:segment+2];axis=0 if p['normal'] in ('N','S') else 1
                require((a[1]==z[1])==(axis==0),pid+': frontage axis disagrees')
                band=bands([a,z],road['width'])[0];join=p['join'];span=f['span']
                require(isinstance(span,list) and len(span)==2 and all(type(v) is int for v in span) and band[axis]<=span[0]<span[1]<=band[axis+2],pid+': frontage span outside exact segment')
                require(isinstance(join,list) and len(join)==2 and all(type(v) is int for v in join) and tuple(join) in cells(band) and span[0]<=join[axis]<span[1],pid+': join outside assigned frontage')
                require(not any(intersect(r,part) for route in plan['routes'] for part in route['rects']),pid+': private lot consumes public road')
                if p['placement']:
                    building=placed[p['placement']];require(building['join']==join and intersect(building['clearance'],r)==building['clearance'],pid+': private buffer or join disagrees with lot')
                    e=frontage_entrance(building,p['normal'])
                    projected=[(u,join[1]) if axis==0 else (join[0],v) for u,v in entrance_cells(e)]
                    require(all(q in cells(band) and span[0]<=q[axis]<span[1] for q in projected),pid+': full doorway span misses segment')
        require(len(listed)==len(set(listed)) and set(listed)==set(s['plots']),sid+': missing or duplicate reciprocal lot membership')
        if s['form']=='grid':
            require({r['id'] for r in plan['routes'] if r['kind']=='street' and r['a']==sid and r['b']==sid}==set(s['streets']),sid+': street reverse ownership disagrees')
            c=commons.get(s['commons'][0]);require(c is not None and c['owner']==sid and c['purpose']=='civic-common',sid+': foreign/missing public geometry')
            require(s['civic'].get('common')==c['id'] and c['civic']==s['civic']['placement'],sid+': conflicting common/civic references')
            require(isinstance(c['rects'],list) and 1<=len(c['rects'])<=4 and all(rectangle(r) and intersect(r,s['bounds'])==r for r in c['rects']),sid+': public bounds invalid')
            public=set().union(*(cells(r) for r in c['rects']));furnishing=c['furnishing']
            require(len(furnishing)==2 and furnishing[1]==[furnishing[0][0]+1,furnishing[0][1]] and all(tuple(p) in public for p in furnishing),sid+': invalid native furnishing cells')
            building=placed[c['civic']];civic_plot=next(p for p in plots.values() if p['placement']==building['id'])
            require(civic_plot.get('civic_lot') is True,sid+': civic did not occupy designated private lot')
            require(all([p[0]//80,p[1]//43]==[building['origin'][0]//80,building['origin'][1]//43] for p in furnishing),sid+': furnishing outside civic member')
            require(c['surface'] in ('cobblestone','dirt_path','grass') and isinstance(c['surface_dependency'],str) and len(c['surface_dependency'])==64,sid+': invalid public surface contract')
            for b in owned:require(not any(intersect(b,r) for r in c['rects']),sid+': private block consumes common')
            require(bool(public & {(u+dx,v+dy) for u,v in cells(civic_plot['buildable']) for dx,dy in NORMALS.values()}),sid+': common is not beside civic lot')
            road_cells=set().union(*(cells(hit) for road in plan['routes'] for r in road['rects'] if (hit:=intersect(r,s['bounds']))))
            clear=public-set(map(tuple,furnishing));require(bool(clear) and connected_cells(clear|road_cells,min(road_cells))==clear|road_cells,sid+': common circulation is disconnected')
            stone=tuple(furnishing[0]);require(any((stone[0]+dx,stone[1]+dy) in road_cells for dx,dy in NORMALS.values()),sid+': native waystone must address a street')
        obstacles=[r for road in plan['routes'] for r in road['rects'] if intersect(r,s['bounds'])]
        obstacles.extend(r for c in plan['public_spaces'] if c['owner']==sid for r in c['rects'])
        obstacles.extend(blocks[b]['bounds'] for b in s['blocks'] if blocks[b]['purpose']=='civic-private')
        require(sorted(blocks[b]['bounds'] for b in s['blocks'] if blocks[b]['purpose']!='civic-private')==free_blocks(s['bounds'],obstacles),sid+': blocks do not match exact road/public free-space partition')
    require(len(all_blocks)==len(set(all_blocks)) and set(all_blocks)==set(blocks),'orphaned/foreign block registry')
    require(len(all_common)==len(set(all_common)) and set(all_common)==set(commons),'orphaned/foreign common registry')
