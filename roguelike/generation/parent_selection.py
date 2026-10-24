"""Policy v2: one bounded weighted selection of single and compound parents."""
import copy
import math
import random
import time
from collections import Counter
from generation.context import GenerationError,stable_seed
from generation.placement import NORMALS,entrance_cells,frontage_entrance
from generation.compounds import validate_recipe,certify,fit,geometry,connected_cells


def key(row):return row['kind'],row['asset'] if row['kind']=='single' else row['recipe']


def check(ok,message):
    if not ok:raise GenerationError('POI parent: '+message)


def validate(policy,data=None):
    from generation.poi_selection import FIELDS,validate as legacy,require_usable_goal
    check(isinstance(policy,dict) and set(policy)==(FIELDS-{'assets'})|{'choices','kind_minimum'},'expected complete version-two policy')
    check(type(policy['version']) is int and policy['version']==2,'unsupported policy version')
    # Reuse the established common range/budget contract, without consulting an
    # asset or changing its historical saved-policy behavior.
    common={k:v for k,v in policy.items() if k not in ('choices','kind_minimum')}
    legacy(dict(common,version=1,assets=[dict(asset='range-check',base_weight=1,weight=1,cap=8)]))
    minima=policy['kind_minimum'];check(isinstance(minima,dict) and set(minima)=={'single','compound'} and all(type(n) is int and 0<=n<=8 for n in minima.values()),'kind_minimum must explicitly declare single and compound integer minima 0..8')
    check(sum(minima.values())<=policy['minimum'],'kind minima exceed total minimum')
    choices=policy['choices'];check(isinstance(choices,list) and 1<=len(choices)<=32,'empty/unbounded parent choices')
    seen=set();capacity=Counter()
    for row in choices:
        check(isinstance(row,dict) and row.get('kind') in ('single','compound'),'choice kind must be single or compound')
        field='asset' if row['kind']=='single' else 'recipe'
        check(set(row)=={'kind',field,'weight','cap'}|({'base_weight'} if data is None else set()),'incomplete kind-tagged choice')
        check(isinstance(row[field],str) and row[field] and key(row) not in seen,'duplicate/invalid parent choice');seen.add(key(row))
        check(type(row['weight']) in (int,float) and math.isfinite(row['weight']) and 0<row['weight']<=1000,'finite positive parent weight required')
        check(type(row['cap']) is int and 1<=row['cap']<=8,'cap must be integer 1..8');capacity[row['kind']]+=row['cap']
        if data is None:
            check(type(row['base_weight']) in (int,float) and math.isfinite(row['base_weight']) and 0<row['base_weight']<=1000,'invalid resolved base weight')
            if row['kind']=='compound':check(row['base_weight']==1,'compound base weight must be one')
        elif row['kind']=='single':
            raw=data.structures.get(row[field]);p=raw.get('placement',{}) if raw else {}
            check('landmark' in p.get('contexts',[]) and p.get('road_relation') in ('frontage','spur'),row[field]+': needs explicit connected landmark context')
            require_usable_goal(raw,'additional rural-site candidate')
        else:
            check(row[field] in data.compounds,row[field]+': unknown compound recipe')
            from generation.world_plan import settings
            certify(validate_recipe(data.compounds[row[field]],data),data,settings(data))
    check(sum(capacity.values())>=policy['minimum'],'eligible parent cap total cannot satisfy minimum')
    check(all(capacity[k]>=n for k,n in minima.items()),'eligible kind caps cannot satisfy kind minimum')
    return policy


def resolve(data):
    policy=copy.deepcopy(validate(data.poi_profiles,data));policy['choices'].sort(key=key);policy['locations'].sort()
    for row in policy['choices']:row['base_weight']=data.structures[row['asset']]['placement']['weight'] if row['kind']=='single' else 1
    return validate(policy)


def parent_key(site,placements):
    return ('compound',site['recipe']) if site['kind']=='compound' else ('single',placements[site['placement']]['asset'])


def eligible(plan,join):
    from generation.poi_selection import distance
    sites=plan['sites'];placements={p['id']:p for p in plan['placements']};policy=plan['poi_policy']
    counts=Counter(parent_key(s,placements) for s in sites);kinds=Counter(s['kind'] for s in sites)
    unmet={k for k,n in policy['kind_minimum'].items() if kinds[k]<n}
    nearest=min(sites,key=lambda s:(distance(join,s['attachment']['join']),s['id'])) if sites else None
    previous=parent_key(nearest,placements) if nearest else None
    return [(r,r['base_weight']*r['weight']*(policy['repeat_multiplier'] if key(r)==previous else 1),key(r)==previous)
            for r in sorted(policy['choices'],key=key) if counts[key(r)]<r['cap'] and (not unmet or r['kind'] in unmet)]


def populate(plan,authority,world,data,metrics=None,*,candidate_rows=None):
    from generation.poi_selection import candidates,junctions,distance,extent_distance
    from generation.world_plan import address,_plot,plot_options,staged,intersect
    started=time.perf_counter();policy=resolve(data);plan.update(poi_policy=policy,sites=[],paths=[])
    desired=random.Random(stable_seed('wg6',plan['seed'],'poi-count')).randint(policy['minimum'],policy['maximum'])
    rows,stats=candidates(plan,policy);bends=junctions(plan)
    if candidate_rows is not None:rows=sorted(candidate_rows,key=lambda r:(stable_seed('wg6',plan['seed'],'poi-candidate',r['join'],r['normal']),r['join'],r['normal']))[:policy['candidate_limit']]
    forbidden={tuple(n['chunk']) for n in plan['nodes']}|{tuple(xy) for s in plan['settlements'] for xy in s['members']}
    forbidden.update(xy for xy,c in world.chunks.items() if c.submaps or c.is_capital or c.is_locus)
    exclusions=Counter();examples=[];parent_trials=0;child_trials=0;tested=0;reason=None
    enumeration_seconds=time.perf_counter()-started;fit_started=time.perf_counter()
    def reject(candidate,message,details=None):
        exclusions[message]+=1
        if len(examples)<24:examples.append(dict(join=candidate['join'],normal=candidate['normal'],road=candidate['road'],reason=message,details=details))
    for candidate in rows:
        if len(plan['sites'])==desired:break
        tested+=1;join=candidate['join'];wx,wy,lx,ly=address(*join);chunk=world.get(wx,wy)
        if (wx,wy) in forbidden:reject(candidate,'protected anchor, town, featured or accepted parent chunk');continue
        if chunk is None or chunk.is_river or chunk.biome_id not in policy['locations']:reject(candidate,'disallowed rural biome or water chunk');continue
        if any(extent_distance(join,s['bounds'])<policy['town_clearance_tiles'] for s in plan['settlements']):reject(candidate,'town outer extent clearance');continue
        if any(distance(join,p)<policy['junction_clearance_tiles'] for p in bends):reject(candidate,'junction or bend clearance');continue
        if any(distance(join,s['attachment']['join'])<policy['spacing_tiles'] for s in plan['sites']):reject(candidate,'accepted parent join spacing');continue
        choices=eligible(plan,join)
        if not choices:reason='hard cohort caps exhausted';break
        sid=f'site-{wx}-{wy}-{lx}-{ly}-{candidate["normal"]}'
        rng=random.Random(stable_seed('wg7',plan['seed'],sid,'parent-choice'));ordered=[]
        while choices:
            selected=rng.choices(choices,weights=[r[1] for r in choices],k=1)[0];choices.remove(selected);ordered.append(selected)
        accepted=None
        for rule,weight,repeated in ordered:
            if rule['kind']=='single':
                weighted=[(rule['asset'],weight,repeated)]
                options,_,_=plot_options(plan,data,sid,'landmark',candidate['normal'],weighted_rows=weighted)
            else:
                recipe=validate_recipe(data.compounds[rule['recipe']],data)
                options=[r for r in recipe['rotations'] if geometry(recipe,r)['gate']['normal']==candidate['normal']] or [None]
                rng.shuffle(options)
            for option in options:
                if parent_trials+child_trials>=policy['fit_budget']:reason='fit budget exhausted';break
                parent_trials+=1
                if rule['kind']=='compound':
                    if option is None:reject(candidate,'no permitted parent transform for gate normal');continue
                    found,work=fit(plan,authority,data,recipe,candidate,sid,option,policy['fit_budget']-parent_trials-child_trials)
                    child_trials+=work['child_trials']
                    if found is None:
                        reject(candidate,'required child budget exhausted' if work['budget_exhausted'] else 'compound does not fit candidate',work);continue
                    q,a,site=found
                else:
                    q,a=staged(plan,authority)
                    plot=_plot(q,a,data,sid,'landmark',wx,wy,lx,join[1],candidate['normal'],candidate['road'],role='site',option=option,weighted_rows=weighted)
                    if not plot['placement']:
                        for failure in plot['rejected']:reject(candidate,failure['reason'])
                        continue
                    p=q['placements'][-1]
                    if any(intersect(r,g) for c in plan['crossings'] for r in c['approaches'] for g in (p['clearance'],p['approach'])):reject(candidate,'bridge deck or approach clearance');continue
                    plot['required']=p['required']=True
                    site=dict(id=sid,kind='single',profile=policy['id'],chunk=[wx,wy],node=sid,plot=plot['id'],placement=p['id'],goal=next(i for i,t in enumerate(p['targets']) if t['required']),attachment=dict(candidate,frontage=p['frontage_entrance']))
                accepted=q,a,site;break
            if accepted or reason:break
        if accepted:
            q,a,site=accepted
            for name in ('plots','placements','dependencies','paths'):
                if name in q:plan[name]=q[name]
            authority.rows=a.rows;authority.index=a.index
            plan['sites'].append(site);plan['nodes'].append(dict(id=sid,chunk=[wx,wy],xy=list(join),required=True));forbidden.add((wx,wy))
        if reason:break
    accepted=len(plan['sites']);kinds=Counter(s['kind'] for s in plan['sites'])
    if accepted<desired and reason is None:reason='bounded candidate enumeration exhausted' if stats['candidate_truncated'] or stats['enumeration_truncated'] else 'all sampled candidates exhausted'
    summary=dict(desired=desired,accepted=accepted,kinds={k:kinds[k] for k in ('single','compound')},shortfall_reason=reason,
                 fit_trials=parent_trials+child_trials,parent_trials=parent_trials,child_trials=child_trials,candidates_tested=tested,**stats,rejections=dict(sorted(exclusions.items())),examples=examples)
    plan['site_selection']=summary
    if accepted<policy['minimum'] or any(kinds[k]<n for k,n in policy['kind_minimum'].items()):
        raise GenerationError(f'POI minimum failure: accepted {accepted}/{policy["minimum"]}, kinds={dict(kinds)}, required={policy["kind_minimum"]}; {reason}; rejections={dict(exclusions)}')
    if metrics is not None:metrics['sites']=dict(enumeration_seconds=enumeration_seconds,fit_seconds=time.perf_counter()-fit_started,**summary)


def validate_resolved(plan,registries):
    """All relationships use saved resolution; today's recipe is never consulted."""
    from generation.poi_selection import distance,extent_distance,junctions
    from generation.world_plan import intersect,bounds,cells,address,bands
    policy=validate(plan['poi_policy']);sites=plan['sites'];summary=plan['site_selection'];placements=registries['placements'];plots=registries['plots'];paths=registries['paths']
    check(type(summary['desired']) is int and policy['minimum']<=summary['desired']<=policy['maximum'],'invalid desired count')
    check(type(summary['accepted']) is int and summary['accepted']==len(sites) and policy['minimum']<=len(sites)<=summary['desired'],'accepted parent count mismatch')
    kinds=Counter(s['kind'] for s in sites)
    check(all(kinds[k]>=v for k,v in policy['kind_minimum'].items()) and summary['kinds']=={k:kinds[k] for k in ('single','compound')},'kind minimum or summary mismatch')
    check((summary['shortfall_reason'] is None)==(len(sites)==summary['desired']) and summary['shortfall_reason'] in (None,'hard cohort caps exhausted','fit budget exhausted','bounded candidate enumeration exhausted','all sampled candidates exhausted'),'invalid shortfall reason')
    for field,limit in [('fit_trials',policy['fit_budget']),('parent_trials',policy['fit_budget']),('child_trials',policy['fit_budget']),('candidates_tested',policy['candidate_limit']),('enumerated',policy['enumeration_limit'])]:
        check(type(summary[field]) is int and 0<=summary[field]<=limit,'invalid bounded work '+field)
    check(summary['parent_trials']+summary['child_trials']==summary['fit_trials'],'work counter mismatch')
    occupied={tuple(xy) for s in plan['settlements'] for xy in s['members']};occupied.update(tuple(n['chunk']) for n in plan['nodes'] if n['id'] not in registries['sites'])
    counts=Counter();owned_plots=set();owned_paths=set();joins=[];bends=junctions(plan)
    check(sum(p['owner']=='landmark' for p in plan['plots'])==1,'featured landmark must remain exactly one independent owner')
    for site in sites:
        sid=site['id'];kind=site['kind'];check(kind in ('single','compound') and site['profile']==policy['id'] and sid==site['node'] and sid.startswith('site-'),sid+': invalid kind/profile/node')
        check(isinstance(site['chunk'],list) and len(site['chunk'])==2 and all(type(v) is int for v in site['chunk']),sid+': invalid chunk')
        chunk=tuple(site['chunk']);check(chunk not in occupied,sid+': illegal shared parent chunk');occupied.add(chunk)
        node=registries['nodes'][site['node']];a=site['attachment'];join=a['join'];normal=a['normal']
        check(set(a)=={'join','normal','road','segment','tangent','side','frontage'},sid+': invalid attachment fields')
        check(node['chunk']==site['chunk'] and node['xy']==join and node['required'],sid+': node/chunk/join mismatch')
        road=registries['routes'][a['road']];i=a['segment']
        check(road['kind']=='country' and type(i) is int and 0<=i<len(road['points'])-1,sid+': wrong parent road/segment')
        u,v=road['points'][i:i+2];band=bands([u,v],road['width'])[0]
        check(u!=v and band[0]<=join[0]<band[2] and band[1]<=join[1]<band[3],sid+': join outside actual country segment')
        horizontal=u[1]==v[1]
        check(normal in ('NS' if horizontal else 'EW') and a['tangent']==([1,0] if horizontal else [0,1]) and a['side']=={'N':'south','S':'north','E':'west','W':'east'}[normal],sid+': normal/tangent/side mismatch')
        check(all(distance(join,b)>=policy['junction_clearance_tiles'] for b in bends) and all(distance(join,j)>=policy['spacing_tiles'] for j in joins),sid+': junction/parent spacing violated');joins.append(join)
        check(all(extent_distance(join,s['bounds'])>=policy['town_clearance_tiles'] for s in plan['settlements']),sid+': town clearance violated')
        row=next((r for r in policy['choices'] if key(r)==parent_key(site,placements)),None);check(row is not None,sid+': parent absent from policy')
        counts[key(row)]+=1;check(counts[key(row)]<=row['cap'],sid+': parent cap exceeded')
        if kind=='single':
            check(set(site)=={'id','kind','profile','chunk','node','plot','placement','goal','attachment'},sid+': invalid single fields')
            p=placements[site['placement']];plot=plots[site['plot']];owned_plots.add(plot['id'])
            check(plot['owner']==sid and plot['placement']==p['id'] and p['required'] and plot['required'] and p['role']==plot['role']=='site' and p['context']=='landmark',sid+': single ownership/role mismatch')
            check(list(address(*p['origin'])[:2])==site['chunk'] and p['road']==plot['road']==a['road'] and p['join']==join and plot['normal']==normal,sid+': single frontage mismatch')
            check(type(site['goal']) is int and 0<=site['goal']<len(p['targets']) and p['targets'][site['goal']]['required'],sid+': invalid usable goal')
            gate=frontage_entrance(p,normal);approach=p['approach'];private=p['clearance']
            check(a['frontage']==p['frontage_entrance']==gate['id'],sid+': entrance identity mismatch')
        else:
            check(set(site)=={'id','kind','profile','recipe','recipe_version','chunk','node','origin','size','rotation','envelope','gate','approach','paths','slots','attachment','fit'},sid+': invalid compound fields')
            check(type(site['recipe_version']) is int and site['recipe_version']==1 and type(site['rotation']) is int and site['rotation'] in (0,90,180,270),sid+': invalid resolved recipe version/rotation')
            private=site['envelope'];origin=site['origin'];size=site['size'];gate=site['gate'];approach=site['approach']
            check(isinstance(size,list) and len(size)==2 and all(type(v) is int and v>0 for v in size) and private==[origin[0],origin[1],origin[0]+size[0],origin[1]+size[1]],sid+': envelope/origin/size mismatch')
            check(set(gate)=={'id','x','y','normal','width','path'} and gate['id']==a['frontage'] and gate['normal']==normal and type(gate['width']) is int and 1<=gate['width']<=5,sid+': invalid gate')
            gc=entrance_cells(gate)
            check(all(private[0]<=x<private[2] and private[1]<=y<private[3] and {'N':y==private[1],'S':y==private[3]-1,'W':x==private[0],'E':x==private[2]-1}[normal] for x,y in gc),sid+': gate outside envelope boundary')
            check(isinstance(site['paths'],list) and 1<=len(site['paths'])<=8 and len(set(site['paths']))==len(site['paths']) and gate['path'] in site['paths'],sid+': missing/duplicate gate paths')
            common=set();declared=set();queue=[gate['path']]
            for pid in site['paths']:
                path=paths[pid];check(set(path)=={'id','owner','name','rects','joins'} and path['owner']==sid and pid==sid+'-path-'+path['name'],sid+': foreign path ownership')
                check(path['rects'] and len(path['rects'])<=16 and all(intersect(r,private)==r for r in path['rects']),sid+': path outside envelope')
                pts=set().union(*(cells(r) for r in path['rects']));check(connected_cells(pts,min(pts))==pts,sid+': disconnected path')
                check(len(set(path['joins']))==len(path['joins']) and all(j in site['paths'] and j!=pid and pid in paths[j]['joins'] for j in path['joins']),sid+': invalid reciprocal path joins')
                for j in path['joins']:
                    union=pts|set().union(*(cells(r) for r in paths[j]['rects']));check(connected_cells(union,min(union))==union,sid+': disconnected declared join')
                common|=pts;owned_paths.add(pid)
            for pid in queue:
                if pid not in declared:declared.add(pid);queue.extend(j for j in paths[pid]['joins'] if j not in declared)
            check(declared==set(site['paths']) and connected_cells(common|set(gc),gc[0])==common|set(gc),sid+': disconnected common circulation/gate')
            slots=site['slots'];check(isinstance(slots,list) and 2<=len(slots)<=3 and sum(s['required'] for s in slots)==2 and len({s['id'] for s in slots})==len(slots),sid+': missing/duplicate required slots')
            for index,s in enumerate(slots):
                check(set(s)=={'id','role','required','buildable','path','normal','assets','effective_rotations','placement','plot','omission','join','goals'},sid+': invalid slot fields')
                check(type(s['required']) is bool and s['required']==(index<2) and isinstance(s['id'],str) and s['id'] and isinstance(s['role'],str) and s['role'],sid+': invalid slot identity/required/role')
                check(s['path'] in site['paths'] and s['normal'] in NORMALS and intersect(s['buildable'],private)==s['buildable'] and not cells(s['buildable'])&common,sid+': child region/path outside parent or private circulation overlap')
                check(not any(intersect(s['buildable'],t['buildable']) for t in slots[index+1:]),sid+': sibling private overlap')
                check(s['assets'] and len({r['asset'] for r in s['assets']})==len(s['assets']) and all(set(r)=={'asset','weight'} and isinstance(r['asset'],str) and type(r['weight']) in (int,float) and math.isfinite(r['weight']) and 0<r['weight']<=1000 for r in s['assets']),sid+': invalid child memberships')
                check(s['effective_rotations'] and len(set(s['effective_rotations']))==len(s['effective_rotations']) and all(type(r) is int and r in (0,90,180,270) for r in s['effective_rotations']),sid+': invalid effective transforms')
                if s['placement'] is None:
                    check(not s['required'] and s['plot'] is None and s['goals']==[] and s['omission'] in ('child fit budget exhausted','all enumerated child alternatives exhausted'),sid+': missing required child or invalid optional omission');continue
                p=placements[s['placement']];plot=plots[s['plot']];owned_plots.add(plot['id']);access=dict(kind='internal',parent=sid,path=s['path'])
                check(p['id']==sid+'-slot-'+s['id']+'-building' and plot['id']==sid+'-slot-'+s['id'] and plot['placement']==p['id'] and plot['owner']==sid and p['parent']==sid and p['slot']==plot['slot']==s['id'],sid+': reciprocal parent/child/slot/plot mismatch')
                check(p['access']==plot['access']==access and p['road'] is None and plot['road'] is None and p['context']=='compound',sid+': foreign internal access or false country frontage')
                check(p['required'] and plot['required'] and s['omission'] is None and p['role']==plot['role']==s['role'] and plot['slot_order']==index,sid+': committed child obligation mismatch')
                check(p['asset'] in {r['asset'] for r in s['assets']} and p['rotation'] in s['effective_rotations'] and p['mirror'] is False,sid+': child membership/effective transform mismatch')
                check(plot['buildable']==s['buildable'] and intersect(p['clearance'],s['buildable'])==p['clearance'] and intersect(p['approach'],private)==p['approach'],sid+': child escapes its buildable/envelope')
                check(p['join']==s['join'] and plot['normal']==s['normal'] and tuple(p['join']) in set().union(*(cells(r) for r in paths[s['path']]['rects'])),sid+': child join misses declared internal path')
                check(s['goals']==[i for i,t in enumerate(p['targets']) if t['required']] and s['goals'],sid+': required child goal references mismatch')
                e=frontage_entrance(p,s['normal']);dx=p['join'][0]-e['x'];dy=p['join'][1]-e['y'];nx,ny=NORMALS[s['normal']]
                check(dx*ny==dy*nx and 0<dx*nx+dy*ny<=plan['settings']['max_spur_tiles'] and p['approach']==bounds(entrance_cells(e)+[(x+dx,y+dy) for x,y in entrance_cells(e)]),sid+': internal full entrance approach mismatch')
            check(set(site['fit'])=={'budget','trials'} and type(site['fit']['budget']) is int and 2<=site['fit']['budget']<=256 and type(site['fit']['trials']) is int and 2<=site['fit']['trials']<=site['fit']['budget'],sid+': invalid child work')
        nx,ny=NORMALS[normal];dx=join[0]-gate['x'];dy=join[1]-gate['y'];gc=entrance_cells(gate)
        check(dx*ny==dy*nx and 0<dx*nx+dy*ny<=plan['settings']['max_spur_tiles'] and approach==bounds(gc+[(x+dx,y+dy) for x,y in gc]),sid+': full external attachment mismatch')
        chunkrect=[chunk[0]*80,chunk[1]*43,(chunk[0]+1)*80,(chunk[1]+1)*43]
        check(intersect(private,chunkrect)==private and intersect(approach,chunkrect)==approach,sid+': envelope/access outside owned chunk')
        check(not any(intersect(r,g) for c in plan['crossings'] for r in c['approaches'] for g in (private,approach)),sid+': bridge approach conflict')
    check(owned_plots=={p['id'] for p in plan['plots'] if p['owner'] in registries['sites']},'orphan/multiply-owned parent plots')
    check(owned_paths==set(paths),'orphan/multiply-owned canonical paths')
    check({n['id'] for n in plan['nodes'] if n['id'].startswith('site-')}==set(registries['sites']),'missing/orphan parent nodes')
