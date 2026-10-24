"""Bounded independent rural sites attached to immutable country-road segments."""
import copy
import math
import random
import time
from collections import Counter
from generation.context import GenerationError,stable_seed
from generation.placement import frontage_entrance,NORMALS

LOCATIONS={'plains','forest','heath'}
FIELDS={'version','id','minimum','maximum','assets','repeat_multiplier','spacing_tiles',
        'town_clearance_tiles','junction_clearance_tiles','locations','sample_step_tiles',
        'enumeration_limit','candidate_limit','fit_budget'}


def validate(policy,data=None):
    def require(ok,message):
        if not ok:raise GenerationError('POI policy: '+message)
    def positive(x):return type(x) in (int,float) and math.isfinite(x) and 0<x<=1000
    require(isinstance(policy,dict) and set(policy)==FIELDS,'expected complete version-one policy')
    require(type(policy['version']) is int and policy['version']==1,'unsupported version')
    require(isinstance(policy['id'],str) and bool(policy['id']),'missing profile ID')
    for key,lo,hi in [('minimum',0,8),('maximum',0,8),('spacing_tiles',1,4096),
            ('town_clearance_tiles',0,256),('junction_clearance_tiles',1,80),
            ('sample_step_tiles',8,80),('enumeration_limit',1,65536),('candidate_limit',1,4096),('fit_budget',1,4096)]:
        require(type(policy[key]) is int and lo<=policy[key]<=hi,f'{key} must be integer {lo}..{hi}')
    require(policy['minimum']<=policy['maximum'],'minimum exceeds maximum')
    require(positive(policy['repeat_multiplier']) and policy['repeat_multiplier']<=1,'repeat_multiplier must be in (0,1]')
    locations=policy['locations']
    require(isinstance(locations,list) and bool(locations) and all(type(v) is str and v in LOCATIONS for v in locations) and len(locations)==len(set(locations)),'locations must be unique plains/forest/heath IDs')
    require(isinstance(policy['assets'],list) and bool(policy['assets']),'empty asset pool')
    seen=set()
    for rule in policy['assets']:
        keys={'asset','weight','cap'}|({'base_weight'} if data is None else set())
        require(isinstance(rule,dict) and set(rule)==keys,'incomplete asset rule')
        aid=rule['asset']
        require(isinstance(aid,str) and aid and aid not in seen,'invalid or duplicate asset ID');seen.add(aid)
        require(positive(rule['weight']) and (data is not None or positive(rule['base_weight'])),aid+': finite positive weight required')
        require(type(rule['cap']) is int and 1<=rule['cap']<=8,aid+': cap must be integer 1..8')
        if data is not None:
            raw=data.structures.get(aid);p=raw.get('placement',{}) if raw else {}
            require('landmark' in p.get('contexts',[]) and p.get('road_relation') in ('frontage','spur'),aid+': needs explicit connected landmark context')
    require(sum(r['cap'] for r in policy['assets'])>=policy['minimum'],'eligible cap total cannot satisfy minimum')
    return policy


def resolve(data):
    policy=copy.deepcopy(validate(data.poi_profiles,data))
    policy['assets'].sort(key=lambda r:r['asset']);policy['locations'].sort()
    for r in policy['assets']:r['base_weight']=data.structures[r['asset']]['placement']['weight']
    return validate(policy)


def distance(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])


def extent_distance(xy,rect):
    return max(rect[0]-xy[0],0,xy[0]-rect[2]+1)+max(rect[1]-xy[1],0,xy[1]-rect[3]+1)


def segments(plan):
    from generation.world_plan import bands
    return [(r,i,a,b,bands([a,b],r['width'])[0]) for r in sorted(plan['routes'],key=lambda r:r['id'])
            if r['kind']=='country' for i,(a,b) in enumerate(zip(r['points'],r['points'][1:])) if a!=b]


def junctions(plan):
    """Perpendicular band intersections are bends/branches; collinear reuse isn't."""
    from generation.world_plan import intersect
    rows=segments(plan);points=set()
    horizontal=[r for r in rows if r[2][1]==r[3][1]]
    vertical=[r for r in rows if r[2][0]==r[3][0]]
    for _,_,a,b,rect in horizontal:
        for _,_,c,d,other in vertical:
            if intersect(rect,other):points.add((c[0],a[1]))
    return sorted(points)


def candidates(plan,policy):
    """Canonical global lattice, deduplicated by physical join/axis/side."""
    found={};examined=0;truncated=False;step=policy['sample_step_tiles']
    for road,index,a,b,_ in segments(plan):
        horizontal=a[1]==b[1];axis=0 if horizontal else 1
        lo,hi=sorted((a[axis],b[axis]))
        for v in range(((lo+step-1)//step)*step,hi+1,step):
            for normal in ('N','S') if horizontal else ('E','W'):
                if examined>=policy['enumeration_limit']:truncated=True;break
                examined+=1;join=(v,a[1]) if horizontal else (a[0],v)
                key=(*join,normal)
                found.setdefault(key,dict(join=list(join),normal=normal,road=road['id'],segment=index,
                    tangent=[1,0] if horizontal else [0,1],side={'N':'south','S':'north','E':'west','W':'east'}[normal]))
            if truncated:break
        if truncated:break
    ordered=[found[k] for k in sorted(found)]
    ordered.sort(key=lambda r:(stable_seed('wg6',plan['seed'],'poi-candidate',r['join'],r['normal']),r['join'],r['normal']))
    return ordered[:policy['candidate_limit']],dict(enumerated=examined,unique=len(found),enumeration_truncated=truncated,
        candidate_truncated=len(ordered)>policy['candidate_limit'])


def eligible(plan,join):
    policy=plan['poi_policy'];sites=plan['sites'];placed={p['id']:p for p in plan['placements']}
    counts=Counter(placed[s['placement']]['asset'] for s in sites)
    nearest=min(sites,key=lambda s:(distance(join,s['attachment']['join']),s['id'])) if sites else None
    previous=placed[nearest['placement']]['asset'] if nearest else None
    return [(r['asset'],r['base_weight']*r['weight']*(policy['repeat_multiplier'] if r['asset']==previous else 1),r['asset']==previous)
            for r in sorted(policy['assets'],key=lambda r:r['asset']) if counts[r['asset']]<r['cap']]


def populate(plan,authority,world,data,metrics=None,*,candidate_rows=None):
    from generation.world_plan import _plot,plot_options,staged,address,intersect
    started=time.perf_counter();policy=resolve(data);plan['poi_policy']=policy;plan['sites']=[]
    desired=random.Random(stable_seed('wg6',plan['seed'],'poi-count')).randint(policy['minimum'],policy['maximum'])
    options,stats=candidates(plan,policy);bends=junctions(plan)
    if candidate_rows is not None:
        # Assigned preview fixtures still use the ordinary eligibility/fitter.
        options=sorted(candidate_rows,key=lambda r:(stable_seed('wg6',plan['seed'],'poi-candidate',r['join'],r['normal']),r['join'],r['normal']))[:policy['candidate_limit']]
    forbidden={tuple(n['chunk']) for n in plan['nodes']}|{tuple(p) for s in plan['settlements'] for p in s['members']}
    forbidden.update(xy for xy,c in world.chunks.items() if c.submaps or c.is_capital or c.is_locus)
    exclusions=Counter();examples=[];fits=0;tested=0;reason=None
    enumeration_seconds=time.perf_counter()-started;fit_started=time.perf_counter()
    def reject(candidate,message):
        exclusions[message]+=1
        if len(examples)<24:examples.append(dict(join=candidate['join'],normal=candidate['normal'],parent=candidate['road'],reason=message))
    for candidate in options:
        if len(plan['sites'])==desired:break
        tested+=1;join=candidate['join'];wx,wy,lx,ly=address(*join);ch=world.get(wx,wy)
        if (wx,wy) in forbidden:reject(candidate,'protected anchor, town, featured or accepted site chunk');continue
        if ch is None or ch.is_river or ch.biome_id not in policy['locations']:reject(candidate,'disallowed rural biome or water chunk');continue
        if any(extent_distance(join,s['bounds'])<policy['town_clearance_tiles'] for s in plan['settlements']):reject(candidate,'town outer extent clearance');continue
        if any(distance(join,p)<policy['junction_clearance_tiles'] for p in bends):reject(candidate,'junction or bend clearance');continue
        if any(distance(join,s['attachment']['join'])<policy['spacing_tiles'] for s in plan['sites']):reject(candidate,'accepted site join spacing');continue
        rows=eligible(plan,join)
        if not rows:reason='hard cohort caps exhausted';break
        sid=f'site-{wx}-{wy}-{lx}-{ly}-{candidate["normal"]}'
        choices,_,_=plot_options(plan,data,sid,'landmark',candidate['normal'],weighted_rows=rows)
        for option in choices:
            if fits>=policy['fit_budget']:reason='fit budget exhausted';break
            fits+=1;q,a=staged(plan,authority)
            plot=_plot(q,a,data,sid,'landmark',wx,wy,lx,join[1],candidate['normal'],candidate['road'],
                       role='site',option=option,weighted_rows=rows)
            if not plot['placement']:
                for failure in plot['rejected']:reject(candidate,failure['reason'])
                continue
            p=q['placements'][-1]
            if any(intersect(r,g) for c in plan['crossings'] for r in c['approaches'] for g in (p['clearance'],p['approach'])):
                reject(candidate,'bridge deck or approach clearance');continue
            plot['required']=p['required']=True
            site=dict(id=sid,kind='rural',profile=policy['id'],chunk=[wx,wy],node=sid,plot=plot['id'],placement=p['id'],
                      goal=next(i for i,t in enumerate(p['targets']) if t['required']),
                      attachment=dict(candidate,frontage=p['frontage_entrance']))
            for key in ('plots','placements','dependencies'):plan[key]=q[key]
            authority.rows=a.rows;authority.index=a.index
            plan['sites'].append(site);plan['nodes'].append(dict(id=sid,chunk=[wx,wy],xy=list(join),required=True))
            forbidden.add((wx,wy));break
        if reason:break
    accepted=len(plan['sites'])
    if accepted<desired and reason is None:
        reason='bounded candidate enumeration exhausted' if stats['candidate_truncated'] or stats['enumeration_truncated'] else 'all sampled candidates exhausted'
    summary=dict(desired=desired,accepted=accepted,shortfall_reason=reason,fit_trials=fits,candidates_tested=tested,
                 **stats,rejections=dict(sorted(exclusions.items())),examples=examples)
    plan['site_selection']=summary
    if accepted<policy['minimum']:
        raise GenerationError(f'POI minimum failure: accepted {accepted}/{policy["minimum"]}, desired {desired}; {reason}; rejections={dict(exclusions)}')
    if metrics is not None:metrics['sites']=dict(enumeration_seconds=enumeration_seconds,fit_seconds=time.perf_counter()-fit_started,**summary)


def validate_resolved(plan,registries):
    """Saved self-contained policy and bidirectional ownership, no live selector."""
    from generation.world_plan import address,bands,bounds,intersect
    from generation.placement import entrance_cells
    def require(ok,message):
        if not ok:raise GenerationError('POI site: '+message)
    policy=validate(plan['poi_policy']);sites=plan['sites'];summary=plan['site_selection']
    require(type(summary['desired']) is int and policy['minimum']<=summary['desired']<=policy['maximum'],'invalid desired count')
    require(type(summary['accepted']) is int and summary['accepted']==len(sites) and policy['minimum']<=len(sites)<=summary['desired'],'missing accepted site or count mismatch')
    require((summary['shortfall_reason'] is None)==(len(sites)==summary['desired']),'shortfall reason mismatch')
    require(summary['shortfall_reason'] in (None,'hard cohort caps exhausted','fit budget exhausted','bounded candidate enumeration exhausted','all sampled candidates exhausted'),'invalid shortfall reason')
    for key,bound in [('fit_trials',policy['fit_budget']),('candidates_tested',policy['candidate_limit']),('enumerated',policy['enumeration_limit'])]:
        require(type(summary[key]) is int and 0<=summary[key]<=bound,'invalid bounded-work counter '+key)
    occupied={tuple(xy) for s in plan['settlements'] for xy in s['members']}
    occupied.update(tuple(n['chunk']) for n in plan['nodes'] if n['id'] not in registries['sites'])
    placements=registries['placements'];plots=registries['plots'];nodes=registries['nodes'];counts=Counter();joins=[]
    bends=junctions(plan)
    require(sum(p['owner']=='landmark' for p in plan['plots'])==1,'featured landmark must remain exactly one independent owner')
    for site in sites:
        sid=site['id']
        require(set(site)=={'id','kind','profile','chunk','node','plot','placement','goal','attachment'},sid+': invalid fields')
        require(site['kind']=='rural' and site['profile']==policy['id'] and sid==site['node'] and sid.startswith('site-'),sid+': invalid kind/profile/node')
        require(isinstance(site['chunk'],list) and len(site['chunk'])==2 and all(type(v) is int for v in site['chunk']),sid+': invalid chunk')
        chunk=tuple(site['chunk']);require(chunk not in occupied,sid+': illegal shared chunk');occupied.add(chunk)
        p=placements[site['placement']];plot=plots[site['plot']];node=nodes[site['node']];attachment=site['attachment']
        require(plot['owner']==sid and plot['placement']==p['id'] and p['required'] and plot['required'],sid+': plot/placement ownership mismatch')
        require(p['context']=='landmark' and p['role']==plot['role']=='site',sid+': invalid rural role/context')
        require(list(address(*p['origin'])[:2])==site['chunk']==node['chunk'] and node['xy']==p['join'] and node['required'],sid+': node/chunk/join mismatch')
        require(type(site['goal']) is int and 0<=site['goal']<len(p['targets']) and p['targets'][site['goal']]['required'],sid+': invalid usable goal')
        rule=next((r for r in policy['assets'] if r['asset']==p['asset']),None)
        require(rule is not None,sid+': asset absent from resolved profile');counts[p['asset']]+=1
        require(counts[p['asset']]<=rule['cap'],sid+': cohort cap exceeded')
        require(set(attachment)=={'join','normal','road','segment','tangent','side','frontage'},sid+': invalid attachment fields')
        require(attachment['road']==plot['road']==p['road'] and attachment['join']==p['join'],sid+': parent/join mismatch')
        road=registries['routes'][attachment['road']];index=attachment['segment']
        require(road['kind']=='country' and type(index) is int and 0<=index<len(road['points'])-1,sid+': wrong parent or segment')
        a,b=road['points'][index:index+2];rect=bands([a,b],road['width'])[0];x,y=p['join']
        require(a!=b and rect[0]<=x<rect[2] and rect[1]<=y<rect[3],sid+': join outside actual parent segment band')
        horizontal=a[1]==b[1];normal=attachment['normal']
        require(normal==plot['normal'] and normal in ('NS' if horizontal else 'EW'),sid+': frontage not perpendicular to parent')
        require(attachment['tangent']==([1,0] if horizontal else [0,1]) and attachment['side']=={'N':'south','S':'north','E':'west','W':'east'}[normal],sid+': tangent/side mismatch')
        entrance=frontage_entrance(p,normal);nx,ny=NORMALS[normal]
        require(attachment['frontage']==p['frontage_entrance']==entrance['id'],sid+': frontage identity mismatch')
        dx=x-entrance['x'];dy=y-entrance['y']
        require(dx*ny==dy*nx and 0<dx*nx+dy*ny<=plan['settings']['max_spur_tiles'],sid+': approach is not a bounded perpendicular connection')
        ec=entrance_cells(entrance)
        require(p['approach']==bounds(ec+[(ex+dx,ey+dy) for ex,ey in ec]),sid+': full access does not match frontage/join')
        require(all(distance(p['join'],b)>=policy['junction_clearance_tiles'] for b in bends),sid+': junction/bend clearance violated')
        require(not any(intersect(r,g) for c in plan['crossings'] for r in c['approaches'] for g in (p['clearance'],p['approach'])),sid+': bridge approach conflict')
        require(all(distance(p['join'],q)>=policy['spacing_tiles'] for q in joins),sid+': join spacing violated');joins.append(p['join'])
        require(all(extent_distance(p['join'],s['bounds'])>=policy['town_clearance_tiles'] for s in plan['settlements']),sid+': town extent clearance violated')
    require({p['id'] for p in plan['plots'] if p['owner'] in registries['sites']}=={s['plot'] for s in sites},'orphan or multiply-owned site plot')
    require({n['id'] for n in plan['nodes'] if n['id'].startswith('site-')}==set(registries['sites']),'missing/orphan site node')
