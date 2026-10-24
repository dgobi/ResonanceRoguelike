"""Durable plan relationships, independent of today's catalog and mutated maps."""
import math
from generation.context import GenerationError
from generation.placement import NORMALS, CONTEXTS, entrance_cells


def records(plan, registries, width, height):
    def require(ok, row, rule):
        if not ok: raise GenerationError(f'{row}: {rule}')
    def integer(n): return type(n) is int
    def identifier(n): return isinstance(n,str) and bool(n)
    def point(p, row, scale=(80,43)):
        require(isinstance(p,list) and len(p)==2 and all(integer(n) for n in p),row,'coordinates must be integer pairs (not booleans)')
        require(0<=p[0]<width*scale[0] and 0<=p[1]<height*scale[1],row,'point outside world')
    def rectangle(r,row,clipped=False):
        require(isinstance(r,list) and len(r)==4 and all(integer(n) for n in r),row,'rectangle must contain four integers')
        require(r[0]<r[2] and r[1]<r[3],row,'rectangle spans must be positive')
        if not clipped:require(0<=r[0]<r[2]<=width*80 and 0<=r[1]<r[3]<=height*43,row,'rectangle outside world')
    def inside(xy,r):return r[0]<=xy[0]<r[2] and r[1]<=xy[1]<r[3]
    def unique(values,row):require(len(values)==len(set(values)),row,'duplicate membership')
    for route in plan['routes']:
        rid=route['id']
        require(route['kind'] in ('country','street') and route['travel_class']=='player-and-creature',rid,'unsupported route kind/class')
        require(type(route['required']) is bool,rid,'required must be boolean')
    for water in plan['waters']:
        require(integer(water['width']) and water['width']>0 and water['travel_class']=='water',water['id'],'invalid water width/class')
        require(bool(water['rects']),water['id'],'empty water geometry')
    for crossing in plan['crossings']:
        require(bool(crossing['deck']) and len(crossing['approaches'])==len(crossing['deck']),crossing['id'],'missing crossing deck/approaches')
        for r in crossing['approaches']:rectangle(r,crossing['id'],clipped=True)
    owners={}; listed_plots={}
    for s in plan['settlements']:
        sid=s['id']; require(s['form'] in ('grid','roadside'),sid,'unsupported settlement form')
        require(sid in registries['nodes'],sid,'settlement lacks destination node')
        unique(s['plots'],sid); unique(s['streets'],sid)
        require(bool(s['streets']) and all(r in registries['routes'] for r in s['streets']),sid,'unknown assigned street')
        for xy in s['members']:
            point(xy,sid,(1,1)); key=tuple(xy)
            require(key not in owners,sid,'member belongs to multiple settlements'); owners[key]=sid
        for pid in s['plots']:
            require(pid not in listed_plots,sid,'plot belongs to multiple settlements'); listed_plots[pid]=sid
        if s['civic'] is not None:
            civic=s['civic']; p=registries['placements'].get(civic['placement'])
            require(p is not None and p['context']=='civic' and civic['bell_state']=='spent',sid,'invalid civic placement/state')
            require(any(registries['plots'].get(pid,{}).get('placement')==p['id'] for pid in s['plots']),sid,'civic belongs to another settlement')
        require((s['civic'] is not None)==(s['form']=='grid'),sid,'grid civic obligation or roadside policy invalid')
        if plan['version']==2:
            semantic=s.get('semantics'); require(isinstance(semantic,dict),sid,'missing G4 semantics')
            require(semantic['policy']=='native-town-v1' and identifier(semantic['name']),sid,'invalid semantic policy/name')
            require([m['chunk'] for m in semantic['members']]==s['members'],sid,'semantic member ownership mismatch')
            for member in semantic['members']:
                require(member['role'] in ('civic','market','residential') and member['district'] in ('bell_quarter','market_quarter','residential'),sid,'unsupported member role/district')
                require(type(member['waystone']) is bool and member['waystone']==(member['role']=='civic'),sid,'invalid functional member policy')
                for key in ('difficulty','resonance'):
                    value=member[key];require(type(value) in (int,float) and math.isfinite(value) and 0<=value<=1,sid,'invalid '+key)
                require(isinstance(member['zones'],list) and bool(member['zones']),sid,'missing zones')
                for zone,weight in member['zones']:
                    require(identifier(zone) and type(weight) in (int,float) and math.isfinite(weight) and 0<weight<=1,sid,'invalid zone policy')
    placement_plots={}
    for plot in plan['plots']:
        pid=plot['id']; owner=plot['owner']; rectangle(plot['buildable'],pid)
        require(type(plot['required']) is bool and plot['normal'] in NORMALS and integer(plot['setback']) and plot['setback']>=0,pid,'invalid plot normal/required/setback')
        require(plot['road'] in registries['routes'],pid,'unknown plot road')
        require(owner=='landmark' or owner in registries['settlements'],pid,'orphaned plot owner')
        if owner!='landmark':require(listed_plots.get(pid)==owner,pid,'plot/settlement reverse ownership mismatch')
        else:require('landmark' in registries['nodes'] and pid not in listed_plots,pid,'invalid landmark owner')
        if plot['placement'] is not None:
            placement=registries['placements'].get(plot['placement'])
            require(placement is not None,pid,'unknown placement')
            require(placement['id'] not in placement_plots,pid,'placement has multiple plots')
            placement_plots[placement['id']]=pid
            require(placement['road']==plot['road'] and placement['required']==plot['required'],pid,'placement/plot contract mismatch')
            chunk=(placement['origin'][0]//80,placement['origin'][1]//43)
            if owner=='landmark':
                require(placement['context']=='landmark' and list(chunk)==registries['nodes']['landmark']['chunk'],pid,'landmark membership mismatch')
            else:
                require(owners.get(chunk)==owner,pid,'placement outside owning settlement')
                require(placement['context'] in (registries['settlements'][owner]['form'],'civic'),pid,'placement context disagrees with settlement')
    require(set(listed_plots)=={p['id'] for p in plan['plots'] if p['owner']!='landmark'},'settlements','unknown or omitted owned plots')
    require(set(placement_plots)==set(registries['placements']),'placements','orphaned placement without exactly one plot')
    for p in plan['placements']:
        pid=p['id']; require(integer(p['rotation']) and p['rotation'] in (0,90,180,270),pid,'unsupported rotation')
        require(type(p['mirror']) is bool and type(p['required']) is bool,pid,'mirror/required must be boolean')
        require(p['context'] in CONTEXTS and identifier(p['asset']) and p['dependency']==p['asset'],pid,'invalid context/asset/dependency')
        for key in ('origin','join'):point(p[key],pid)
        for key in ('footprint','clearance','approach'):rectangle(p[key],pid)
        f=p['footprint']; c=p['clearance']
        require(c[0]<=f[0]<f[2]<=c[2] and c[1]<=f[1]<f[3]<=c[3],pid,'clearance does not contain footprint')
        require(inside(p['join'],p['approach']),pid,'join outside approach')
        require(isinstance(p['entrances'],list) and bool(p['entrances']),pid,'missing entrances')
        unique([e['id'] for e in p['entrances']],pid)
        for e in p['entrances']:
            require(identifier(e['id']) and e['normal'] in NORMALS and e['role'] in ('main','service'),pid,'invalid entrance identity/normal/role')
            point([e['x'],e['y']],pid); require(integer(e['width']) and 0<e['width']<=max(f[2]-f[0],f[3]-f[1]),pid,'invalid entrance width')
            require(type(e['required']) is bool,pid,'entrance required must be boolean')
            for xy in entrance_cells(e):
                require(inside(xy,f),pid,'entrance outside footprint')
                require({'N':xy[1]==f[1],'S':xy[1]==f[3]-1,'W':xy[0]==f[0],'E':xy[0]==f[2]-1}[e['normal']],pid,'entrance normal does not point outward')
                if e['required']:require(inside(xy,p['approach']),pid,'complete required entrance outside approach')
        require(any(e['required'] for e in p['entrances']),pid,'missing required entrance')
        for t in p['targets']:
            point([t['x'],t['y']],pid)
            require(type(t['required']) is bool and t['kind'] in ('floor','item','readable','container','stairs_up','stairs_down'),pid,'invalid target kind/required')
    for r in plan['reservations']:
        rectangle(r['rect'],r['id'],clipped=r['purpose']=='water')
        if 'public_road' in r:
            require(r['purpose']=='approach' and r['public_road']==registries['placements'][r['owner']]['road'],r['id'],'public approach assigned to wrong road')


def world_membership(world):
    """Check saved metadata, never recompute it or consult mutable definitions."""
    from world.world_map import RegionType
    plan=world.plan
    if world.generation_revision!=plan['generation_revision']: raise GenerationError('world origin disagrees with saved plan origin')
    expected={tuple(xy):i for i,s in enumerate(plan['settlements']) for xy in s['members']}
    groups={i:[tuple(xy) for xy in s['members']] for i,s in enumerate(plan['settlements'])}
    if world.town_chunks!=set(expected) or world.town_chunk_ids!=expected or world.town_groups!=groups:
        raise GenerationError('saved town registries disagree with settlement membership')
    actual={xy for xy,c in world.chunks.items() if c.region_type==RegionType.TOWN or c.town_id!=-1 or c.town_role}
    if actual!=set(expected): raise GenerationError('orphaned or omitted planned town Chunk')
    for xy,i in expected.items():
        c=world.get(*xy); s=plan['settlements'][i]
        if c is None or c.region_type!=RegionType.TOWN or c.biome_id!='town' or type(c.town_id) is not int or c.town_id!=i:
            raise GenerationError(f'{xy}: Chunk town identity disagrees with settlement')
        if plan['version']==1:
            if c.town_role!='planned':raise GenerationError(f'{xy}: unsupported G3 member role')
        else:
            policy=next(m for m in s['semantics']['members'] if m['chunk']==list(xy))
            if (c.name!=s['semantics']['name'] or c.town_role!=policy['role'] or
                [list(z) for z in c.zones]!=[list(z) for z in policy['zones']] or
                c.difficulty!=policy['difficulty'] or c.resonance!=policy['resonance']):
                raise GenerationError(f'{xy}: Chunk semantics disagree with saved policy')
            if c.town_data and (c.town_data.name!=c.name or c.town_data.districts!=[policy['district']]):
                raise GenerationError(f'{xy}: TownData disagrees with saved policy')
