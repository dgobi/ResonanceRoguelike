"""Optional G9 augmentation of a complete, validated G8 baseline.

Bounded A* proposes macro corridors using actual 80/43-tile traversal costs and
Manhattan admissible heuristic. It does not claim a terrain-respecting optimum.
Exact construction union, physical distances and normal reservations admit them.
"""
import copy
import heapq
import math
import time
from itertools import combinations
from generation.context import GenerationError,stable_seed
from generation.placement import digest
from generation.network_metrics import terminals,pair_id,centerline_edges,road_cells,physical_cells,distances,pair_rows

DEFAULT=dict(version=1,max_shortcuts=2,max_added_fraction=0.25,min_saved_steps=500,min_relative_improvement=0.25,
             candidate_pair_limit=8,search_expansion_limit=8192,world_expansion_budget=32768)
ROLE='country-shortcut-v1'


def require(ok,message):
    if not ok:raise GenerationError('country network: '+message)


def policy(raw):
    require(isinstance(raw,dict) and set(raw)==set(DEFAULT),'expected complete version 1 policy; unknown/missing fields')
    for name,lo,hi in [('version',1,1),('max_shortcuts',0,2),('min_saved_steps',1,100000),('candidate_pair_limit',1,32),('search_expansion_limit',1,16384),('world_expansion_budget',1,65536)]:
        require(type(raw[name]) is int and lo<=raw[name]<=hi,f'{name} must be integer {lo}..{hi}, not boolean')
    for name,lo,hi in [('max_added_fraction',0,0.25),('min_relative_improvement',0.01,1)]:
        require(type(raw[name]) in (int,float) and math.isfinite(raw[name]) and lo<=raw[name]<=hi,f'{name} must be finite {lo}..{hi}')
    return copy.deepcopy(raw)


def baseline(plan):
    """Recover the exact original records, never regenerate geometry or content."""
    q=dict(plan);ids={r['route'] for r in plan.get('network',{}).get('accepted',[])}
    for key,field in [('routes','id'),('crossings','road'),('reservations','owner')]:q[key]=[r for r in plan[key] if r[field] not in ids]
    q.pop('network',None);q['version']=6;q['generation_revision']='wg8';q['settings']=dict(q['settings'],version=3);q['settings'].pop('country_network_version',None)
    return q


def identities(plan):return {k:digest(v) for k,v in sorted(plan.items())}


def protected_owners(plan):
    return ({tuple(xy) for s in plan['settlements'] for xy in s['members']}|
            {tuple(s['chunk']) for s in plan.get('sites',[])}|
            {(p['origin'][0]//80,p['origin'][1]//43) for p in plan['placements']}|
            {tuple(n['chunk']) for n in plan['nodes'] if n['id']=='capital-gateway'})


def macro_edges(plan):
    edges=set()
    for r in plan['routes']:
        if r['kind']!='country':continue
        for a,b in zip(r['points'],r['points'][1:]):
            p=a[0]//80,a[1]//43;q=b[0]//80,b[1]//43;dx=(q[0]>p[0])-(q[0]<p[0]);dy=(q[1]>p[1])-(q[1]<p[1])
            for _ in range(abs(q[0]-p[0])+abs(q[1]-p[1])):
                nxt=p[0]+dx,p[1]+dy;edges.add(tuple(sorted((p,nxt))));p=nxt
    return edges


def search(world,plan,a,b,budget):
    old=macro_edges(plan);protected=protected_owners(plan)|{xy for xy,ch in world.chunks.items() if ch.submaps or ch.is_capital}
    start=tuple(a['chunk']);goal=tuple(b['chunk']);heuristic=lambda p:80*abs(p[0]-goal[0])+43*abs(p[1]-goal[1])
    heap=[(heuristic(start),0,start)];cost={start:0};parent={};expanded=0
    while heap and expanded<budget:
        _,g,p=heapq.heappop(heap)
        if cost[p]!=g:continue
        expanded+=1
        if p==goal:
            path=[p]
            while p!=start:p=parent[p];path.append(p)
            return list(reversed(path)),expanded,'found'
        for dx,dy,step in ((0,-1,43),(-1,0,80),(1,0,80),(0,1,43)):
            q=p[0]+dx,p[1]+dy;ch=world.get(*q);reused=tuple(sorted((p,q))) in old
            if ch is None or ch.biome_id=='deep_mountain':continue
            if not reused and (p in protected or q in protected or ch.is_river or world.get(*p).is_river):continue
            ng=g+step
            if ng<cost.get(q,math.inf):cost[q]=ng;parent[q]=p;heapq.heappush(heap,(ng+heuristic(q),ng,q))
    return None,expanded,'search expansion limit' if heap else 'no legal macro corridor'


def touched(route):
    from generation.world_plan import member_chunks
    return sorted({tuple(xy) for r in route['rects'] for xy in member_chunks(r)})


def check_geometry(original,current,route,world=None):
    from generation.world_plan import cells,expand,intersect
    from generation.compounds import connected_cells
    new=road_cells([route])-road_cells(original['routes']);protected=protected_owners(original)
    if world is not None:protected|={xy for xy,ch in world.chunks.items() if ch.submaps or ch.is_capital}
    require(not any((x//80,y//43) in protected for x,y in new),'new full-width cells enter a protected owner chunk')
    if world is not None:
        require(all((ch:=world.get(x//80,y//43)) is not None and ch.biome_id!='deep_mountain' and not ch.is_river for x,y in new),'new cells enter excluded geography/water')
    candidate=road_cells([route]);decks={w['id']:set() for w in original['waters']}
    for c in original['crossings']:
        for rect in c['deck']:decks[c['water']]|=cells(rect)
    crossings=[]
    for water in original['waters']:
        hits=[]
        for r in route['rects']:
            for wr in water['rects']:
                hit=intersect(r,expand(wr,2))
                if hit:
                    require(cells(hit)<=decks[water['id']],'new road/water overlap outside an existing owned bridge deck')
                    hits.append(hit)
        if hits:
            hits=[list(r) for r in sorted(set(map(tuple,hits)))]
            crossings.append(dict(id=route['id']+'-'+water['id'],road=route['id'],water=water['id'],kind='bridge',travel_class='player-and-creature',deck=hits,approaches=[expand(r,2) for r in hits]))
    for r in original['reservations']:
        if r['purpose'] not in ('road','water'):require(not (new & cells(r['rect'])),'new band intersects private/common/access reservation '+r['owner'])
    # Index complete road cells once, then inspect each touched complete slice.
    chunks={xy:set() for xy in touched(route)}
    for x,y in road_cells(current['routes'])|candidate:
        key=x//80,y//43
        if key in chunks:chunks[key].add((x%80,y%43))
    for xy,points in chunks.items():require(points and connected_cells(points,min(points))==points,f'complete road slice {xy} disconnected locally')
    return crossings


def stage(original,current,route,world=None):
    crossings=check_geometry(original,current,route,world)
    q=dict(current,routes=current['routes']+[route],crossings=current['crossings']+crossings)
    rows=[dict(id=f'{route["id"]}-reservation-{i}',owner=route['id'],purpose='road',rect=r) for i,r in enumerate(route['rects'])]
    index=next((i for i,r in enumerate(current['reservations']) if r['purpose'] not in ('road','water')),len(current['reservations']))
    q['reservations']=current['reservations'][:index]+rows+current['reservations'][index:]
    return q


def augment(world,original,data,metrics=None):
    """Complete baseline in, immutable optional additions out; no scenes or RNG use."""
    from generation.world_plan import bands,validate_plan
    started=time.perf_counter();p=policy(data.country_network);nodes=terminals(original)
    base_edges=centerline_edges(r for r in original['routes'] if r['kind']=='country');limit=math.floor(len(base_edges)*p['max_added_fraction'])
    contract=dict(version=1,policy=p,baseline=identities(original),original_route_ids=[r['id'] for r in original['routes']],
                  baseline_unique_steps=len(base_edges),construction_limit_steps=limit,added_unique_steps=0,accepted=[],
                  primary_ids=[n['id'] for n in nodes],primary_pair_count=len(nodes)*(len(nodes)-1)//2,
                  pairs_examined=0,pairs_unexamined=len(nodes)*(len(nodes)-1)//2,expansions=0,outcome='disabled' if p['max_shortcuts']==0 else 'zero construction budget' if not limit else 'no qualifying candidate')
    current=original;trace=[];cache={};before=None;values=None
    if p['max_shortcuts'] and limit:
        values=distances(physical_cells(original),nodes);before=dict(values)
        candidates=[]
        for a,b in combinations(nodes,2):
            key=pair_id(a['id'],b['id']);lower=abs(a['xy'][0]-b['xy'][0])+abs(a['xy'][1]-b['xy'][1]);d=values[key]
            candidates.append((-(d/max(1,lower)),-(d-lower),stable_seed('wg9-network',original['seed'],key),key,a,b))
        candidates.sort();selected=candidates[:p['candidate_pair_limit']];contract['pairs_unexamined']=len(candidates)-len(selected)
        for turn in range(p['max_shortcuts']):
            choices=[];current_edges=centerline_edges(r for r in current['routes'] if r['kind']=='country')
            for _,__,___,key,a,b in selected:
                if any(r['pair']==key for r in contract['accepted']):continue
                record=dict(round=turn,pair=key)
                if key not in cache:
                    available=min(p['search_expansion_limit'],p['world_expansion_budget']-contract['expansions'])
                    if available<=0:record['reason']='global expansion budget exhausted';trace.append(record);continue
                    path,expanded,status=search(world,original,a,b,available);contract['expansions']+=expanded;contract['pairs_examined']+=1;cache[key]=(path,expanded,status)
                path,expanded,status=cache[key];record.update(expansions=expanded,search_status=status)
                if path is None:record['reason']=status;trace.append(record);continue
                points=[[80*x+40,43*y+21] for x,y in path]
                route=dict(id=f'network-shortcut-{turn}',a=a['id'],b=b['id'],required=False,travel_class='player-and-creature',kind='country',width=original['settings']['road_width_tiles'],points=points,rects=bands(points,original['settings']['road_width_tiles']),search_nodes=expanded,network_role=ROLE)
                edges=centerline_edges([route]);added=len(edges-current_edges);total=len((current_edges|edges)-base_edges)
                record.update(added_unique_steps=added,total_added_unique_steps=total,reused_steps=len(edges&current_edges),search_cost_tile_steps=sum(abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(points,points[1:])))
                if not added or total>limit:record['reason']='duplicate corridor' if not added else 'shared construction budget';trace.append(record);continue
                try:
                    staged=stage(original,current,route,world)
                    # Validate the ordinary G8 geometry authority before attaching
                    # the G9 metadata. No exemption or unchecked candidate publish.
                    validate_plan(staged,world.width,world.height)
                    after=distances(physical_cells(staged),nodes)
                    saved=values[key]-after[key];relative=saved/values[key]
                    record.update(before_steps=values[key],after_steps=after[key],saved_steps=saved,relative_improvement=relative)
                    if saved<p['min_saved_steps'] or relative<p['min_relative_improvement']:record['reason']='insufficient marginal physical benefit';trace.append(record);continue
                    require(all(after[k]<=values[k] for k in values),'augmentation increased physical travel')
                    aggregate=sum(values[k]-after[k] for k in values)
                    lowers={pair_id(x['id'],y['id']):max(1,abs(x['xy'][0]-y['xy'][0])+abs(x['xy'][1]-y['xy'][1])) for x,y in combinations(nodes,2)}
                    worst=max(values[k]/lowers[k] for k in values)-max(after[k]/lowers[k] for k in after)
                    score=(worst,aggregate/max(1,added),saved,-added)
                    record.update(aggregate_saved_steps=aggregate,worst_pair_detour_reduction=worst,score=list(score),reason='qualified')
                    choices.append((score,key,staged,after,record,route))
                except GenerationError as error:record['reason']='geometry rejected: '+str(error)
                trace.append(record)
            if not choices:break
            choices.sort(key=lambda c:(tuple(-v for v in c[0]),c[1]));_,key,current,values,record,route=choices[0]
            for other in choices[1:]:other[4]['reason']='ranked below accepted candidate'
            record['reason']='accepted: worst-pair reduction, aggregate saving per new step, named saving, construction, canonical pair'
            contract['accepted'].append(dict(route=route['id'],pair=key,a=route['a'],b=route['b'],before_steps=record['before_steps'],after_steps=record['after_steps'],added_unique_steps=record['added_unique_steps']))
            contract['added_unique_steps']=record['total_added_unique_steps'];contract['outcome']='augmented'
        contract['pairs_unexamined']=contract['primary_pair_count']-contract['pairs_examined']
        if not contract['accepted'] and contract['expansions']>=p['world_expansion_budget']:contract['outcome']='global expansion budget exhausted'
        elif not contract['accepted'] and any(c.get('search_status')=='search expansion limit' for c in trace):contract['outcome']='bounded search exhausted without qualifying candidate'
    current=dict(current,version=7,generation_revision='wg9',settings=dict(original['settings'],version=4,country_network_version=1),network=contract)
    validate_plan(current,world.width,world.height)
    if metrics is not None:metrics['network']=dict(seconds=time.perf_counter()-started,candidates=trace,before=before,after=values,contract=contract)
    return current


def validate_resolved(plan):
    """No current policy/recipes, replanning, scenes or duplicate durable graphs."""
    n=plan.get('network');require(isinstance(n,dict) and n.get('version')==1,'missing resolved version 1 contract')
    require(set(n)=={'version','policy','baseline','original_route_ids','baseline_unique_steps','construction_limit_steps','added_unique_steps','accepted','primary_ids','primary_pair_count','pairs_examined','pairs_unexamined','expansions','outcome'},'unknown/missing network contract fields')
    p=policy(n['policy']);require(plan['settings']['version']==4 and plan['settings']['country_network_version']==1,'settings/network version mismatch')
    original=baseline(plan);require(identities(original)==n['baseline'],'original baseline record removed or changed')
    require([r['id'] for r in original['routes']]==n['original_route_ids'],'original route identity/order changed')
    nodes=terminals(plan);require([r['id'] for r in nodes]==n['primary_ids'] and n['primary_pair_count']==len(nodes)*(len(nodes)-1)//2,'primary endpoint membership changed')
    for k in ('baseline_unique_steps','construction_limit_steps','added_unique_steps','pairs_examined','pairs_unexamined','expansions'):
        require(type(n[k]) is int and n[k]>=0,'invalid integer accounting '+k)
    require(n['pairs_examined']<=p['candidate_pair_limit'] and n['expansions']<=p['world_expansion_budget'] and n['pairs_examined']+n['pairs_unexamined']==n['primary_pair_count'],'search budget accounting')
    require(isinstance(n['accepted'],list) and len(n['accepted'])<=p['max_shortcuts'],'shortcut count exceeds policy')
    require(n['outcome'] in ('disabled','zero construction budget','no qualifying candidate','augmented','global expansion budget exhausted','bounded search exhausted without qualifying candidate'),'unknown outcome')
    require((n['outcome']=='disabled')==(p['max_shortcuts']==0),'disabled policy/outcome mismatch')
    base_edges=centerline_edges(r for r in original['routes'] if r['kind']=='country');limit=math.floor(len(base_edges)*p['max_added_fraction'])
    require(n['baseline_unique_steps']==len(base_edges) and n['construction_limit_steps']==limit,'forged baseline construction accounting')
    current=original;seen=set();total=0
    for i,accepted in enumerate(n['accepted']):
        require(set(accepted)=={'route','pair','a','b','before_steps','after_steps','added_unique_steps'},'unknown/missing accepted connection fields')
        rid=accepted['route'];require(rid==f'network-shortcut-{i}' and rid not in seen,'invalid/duplicate shortcut identity');seen.add(rid)
        route=next((r for r in plan['routes'] if r['id']==rid),None)
        require(route and route.get('network_role')==ROLE and route['kind']=='country' and route['required'] is False and route['width']==original['settings']['road_width_tiles'],'missing/foreign shortcut role or geometry')
        require(accepted['a']==route['a'] and accepted['b']==route['b'] and accepted['a']!=accepted['b'] and {accepted['a'],accepted['b']}<=set(n['primary_ids']) and accepted['pair']==pair_id(route['a'],route['b']),'shortcut endpoints disagree')
        next_plan=stage(original,current,route)
        require([c for c in plan['crossings'] if c['road']==rid]==[c for c in next_plan['crossings'] if c['road']==rid],'crossing reuse scope differs')
        require([r for r in plan['reservations'] if r['owner']==rid]==[r for r in next_plan['reservations'] if r['owner']==rid],'shortcut reservation scope differs')
        old_edges=centerline_edges(r for r in current['routes'] if r['kind']=='country');edges=centerline_edges([route]);added=len(edges-old_edges);total=len((old_edges|edges)-base_edges)
        require(added>0 and type(accepted['added_unique_steps']) is int and accepted['added_unique_steps']==added and total<=limit,'forged/over-budget added construction')
        pair=[r for r in nodes if r['id'] in (route['a'],route['b'])];key=accepted['pair']
        before=distances(physical_cells(current),pair)[key];after=distances(physical_cells(next_plan),pair)[key]
        require(type(accepted['before_steps']) is int and type(accepted['after_steps']) is int and (before,after)==(accepted['before_steps'],accepted['after_steps']),'forged physical benefit')
        require(before-after>=p['min_saved_steps'] and (before-after)/before>=p['min_relative_improvement'],'insufficient marginal benefit')
        current=next_plan
    require(total==n['added_unique_steps'],'total construction accounting differs')
    require(current['routes']==plan['routes'] and current['crossings']==plan['crossings'] and current['reservations']==plan['reservations'],'unreferenced new infrastructure or changed replay order')
    require((n['outcome']=='augmented')==bool(seen),'outcome disagrees with accepted roads')


def validate_world(world):
    if world.plan['version']!=7:return
    original=baseline(world.plan)
    for r in world.plan['routes']:
        if r.get('network_role')==ROLE:check_geometry(original,world.plan,r,world)
