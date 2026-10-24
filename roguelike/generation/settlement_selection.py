"""Versioned selection intent, separate from consumed structure geometry."""
import copy
import math
import random
from collections import Counter
from generation.context import GenerationError, stable_seed


def validate(config, data=None):
    def require(ok, message):
        if not ok: raise GenerationError('settlement selection: '+message)
    def positive(value): return type(value) in (int,float) and math.isfinite(value) and 0<value<=1000
    require(isinstance(config,dict) and set(config)=={'version','profiles'} and type(config['version']) is int and config['version']==1,'expected version 1 profiles')
    require(isinstance(config['profiles'],dict) and set(config['profiles'])=={'grid','roadside','landmark'},'declare grid, roadside and landmark profiles')
    for context,p in config['profiles'].items():
        require(isinstance(p,dict) and set(p)=={'id','roles','minimum','schedule','repeat_multiplier','required_fit_budget'},context+': incomplete profile')
        require(isinstance(p['id'],str) and bool(p['id']),context+': missing identity')
        roles={'landmark'} if context=='landmark' else {'residential','commercial','support'}|({'civic'} if context=='grid' else set())
        require(isinstance(p['roles'],dict) and set(p['roles'])==roles,context+': unsupported/missing roles')
        require(isinstance(p['minimum'],dict) and set(p['minimum'])==roles,context+': incomplete minima')
        require(type(p['repeat_multiplier']) in (int,float) and math.isfinite(p['repeat_multiplier']) and 0<p['repeat_multiplier']<=1,context+': repeat_multiplier must be in (0,1]')
        require(type(p['required_fit_budget']) is int and 1<=p['required_fit_budget']<=4096,context+': required_fit_budget must be 1..4096')
        require(isinstance(p['schedule'],list) and bool(p['schedule']) and all(r in roles-{'civic'} for r in p['schedule']),context+': invalid optional schedule')
        seen=set()
        for role,rows in p['roles'].items():
            require(type(p['minimum'][role]) is int and 0<=p['minimum'][role]<=8,role+': minimum must be 0..8')
            require(isinstance(rows,list) and bool(rows),role+': empty eligible pool')
            for row in rows:
                keys={'asset','weight','max_per_settlement'}|({'base_weight'} if data is None else set())
                require(isinstance(row,dict) and set(row)==keys,role+': incomplete asset rule')
                aid=row['asset'];require(isinstance(aid,str) and aid and aid not in seen,role+': duplicate/invalid membership');seen.add(aid)
                require(positive(row['weight']) and (data is not None or positive(row['base_weight'])),aid+': finite positive weights required')
                require(type(row['max_per_settlement']) is int and 1<=row['max_per_settlement']<=128,aid+': integer cap must be 1..128')
                if data is not None:
                    raw=data.structures.get(aid); required_context='civic' if role=='civic' else context
                    require(raw is not None and required_context in raw.get('placement',{}).get('contexts',[]),aid+': missing explicit '+required_context+' context')
                    require(raw['placement']['road_relation']!='remote',aid+': connected role cannot use remote relation')
            require(sum(r['max_per_settlement'] for r in rows)>=p['minimum'][role],role+': minimum exceeds hard caps')
        if context!='landmark':
            require(p['minimum']['residential']>=1 and p['minimum']['commercial']>=1,context+': residential and commercial minima must be positive')
        if context=='grid':require(p['minimum']['civic']==1 and [r['asset'] for r in p['roles']['civic']]==['bell_tower_a'],'grid requires exactly one spent-bell civic anchor')
        if context=='landmark':require(p['minimum']=={'landmark':1},'exactly one landmark site is supported')
    return config


def resolve(data):
    config=copy.deepcopy(validate(data.settlement_profiles,data))
    for profile in config['profiles'].values():
        for rows in profile['roles'].values():
            rows.sort(key=lambda row:row['asset'])
            for row in rows:row['base_weight']=data.structures[row['asset']]['placement']['weight']
    return validate(config)


def pools(selection):
    result={c:[] for c in ('grid','roadside','civic','landmark')}
    for context,p in selection['profiles'].items():
        for role,rows in p['roles'].items():
            result['civic' if role=='civic' else context].extend(r['asset'] for r in rows)
    return {c:sorted(set(rows)) for c,rows in result.items()}


def profile_for(plan, owner):
    context='landmark' if owner=='landmark' else next(s['form'] for s in plan['settlements'] if s['id']==owner)
    return plan['selection']['profiles'][context]


def eligible(plan, owner, role, slot_order):
    """Only accepted occupants consume caps. Neighbor is stable spatial order."""
    profile=profile_for(plan,owner)
    plots=[p for p in plan['plots'] if p['owner']==owner and p['placement']]
    placements={p['id']:p for p in plan['placements']}
    counts=Counter(placements[p['placement']]['asset'] for p in plots)
    neighbor=min(plots,key=lambda p:(abs(p['slot_order']-slot_order),p['slot_order'])) if plots else None
    previous=placements[neighbor['placement']]['asset'] if neighbor else None
    rows=[];excluded=[]
    for rule in sorted(profile['roles'][role],key=lambda row:row['asset']):
        aid=rule['asset']
        if counts[aid]>=rule['max_per_settlement']:
            excluded.append(dict(asset=aid,rotation=None,mirror=None,reason='hard per-settlement cap reached'))
        else:rows.append((aid,rule['base_weight']*rule['weight']*(profile['repeat_multiplier'] if aid==previous else 1),aid==previous))
    return rows,excluded


def populate_settlement(plan, authority, data, settlement, slots):
    """Reserve minima first with bounded backtracking; then fill optional slots.

    Slot order follows distance from the original civic/arrival slot. Required
    trials use the same fitter. A failed branch owns no accepted counts/space.
    """
    from generation.world_plan import _plot,plot_options,staged
    profile=profile_for(plan,settlement['id']);sid=settlement['id']
    required=[role for role in ('civic','commercial','residential','support') for _ in range(profile['minimum'].get(role,0))]
    attempts=0; failures=[]; exhausted=False
    def fit(p,a,slot,role,option=None):
        wx,wy,lx,line_y,normal,rid,order=slot
        return _plot(p,a,data,sid,'civic' if role=='civic' else settlement['form'],wx,wy,lx,line_y,normal,rid,
                     role=role,slot_order=order,option=option)
    def search(p,a,remaining,index):
        nonlocal attempts,exhausted
        if index==len(required):return p,a,remaining
        role=required[index]
        for slot in remaining:
            options,_,_=plot_options(p,data,sid,'civic' if role=='civic' else settlement['form'],slot[4],role=role,slot_order=slot[-1])
            for option in options:
                if attempts>=profile['required_fit_budget']:exhausted=True;return None
                attempts+=1;q,b=staged(p,a);plot=fit(q,b,slot,role,option=option)
                if not plot['placement']:
                    failures.append(dict(role=role,slot=slot[-1],asset=option[0],rejected=plot['rejected']));failures[:]=failures[-16:];continue
                plot['required']=True;q['placements'][-1]['required']=True
                found=search(q,b,[s for s in remaining if s!=slot],index+1)
                if found:return found
                if exhausted:return None
        return None
    found=search(plan,authority,slots,0)
    if found is None:
        reason='budget exhausted; feasibility unresolved' if exhausted else 'all enumerated alternatives exhausted; infeasible'
        raise GenerationError(f'{sid}: required role minima infeasible within bounded search: {reason}; {attempts}/{profile["required_fit_budget"]} transform fit trials; minima={profile["minimum"]}; last={failures[-3:]}')
    chosen,used,remaining=found
    for key in ('plots','placements','dependencies'):plan[key]=chosen[key]
    authority.rows=used.rows;authority.index=used.index
    plan['diagnostics'].append(dict(kind='required-role-search',owner=sid,attempts=attempts,budget=profile['required_fit_budget'],budget_unit='one transform fit or empty-frontage asset trial',rejected=failures))
    for slot in remaining:
        role=profile['schedule'][slot[-1]%len(profile['schedule'])]
        fit(plan,authority,slot,role)
    settlement['plots']=[p['id'] for p in plan['plots'] if p['owner']==sid]
    civic=next((p for p in plan['plots'] if p['owner']==sid and p['role']=='civic'),None)
    settlement['civic']=dict(placement=civic['placement'],bell_state='spent') if civic else None
    settlement['selection_profile']=profile['id']


def validate_resolved(plan):
    """Saved policy is self-contained: no dependency on today's editable file."""
    validate(plan['selection'])
    placed={p['id']:p for p in plan['placements']}
    for owner in [s['id'] for s in plan['settlements']]+['landmark']:
        profile=profile_for(plan,owner);counts=Counter();roles=Counter();orders=set()
        if owner!='landmark':
            s=next(s for s in plan['settlements'] if s['id']==owner)
            if s['selection_profile']!=profile['id']:raise GenerationError(owner+': selection profile identity disagrees')
        for plot in (p for p in plan['plots'] if p['owner']==owner):
            role=plot['role'];order=plot['slot_order']
            if role not in profile['roles'] or type(order) is not int or order<0 or order in orders:
                raise GenerationError(owner+': invalid resolved role/slot order')
            orders.add(order)
            if not plot['placement']:continue
            p=placed[plot['placement']]
            rule=next((r for r in profile['roles'][role] if r['asset']==p['asset']),None)
            context='civic' if role=='civic' else 'landmark' if owner=='landmark' else s['form']
            if rule is None or p['role']!=role or p['context']!=context or type(p.get('frontage_entrance')) is not str:
                raise GenerationError(owner+': contradictory resolved role/asset/frontage')
            counts[p['asset']]+=1;roles[role]+=1
            if counts[p['asset']]>rule['max_per_settlement']:raise GenerationError(owner+': hard asset cap exceeded')
        if any(roles[r]<n for r,n in profile['minimum'].items()):raise GenerationError(owner+': required role minimum missing')
