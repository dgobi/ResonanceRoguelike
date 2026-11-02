"""Version-6 local player ward. Sight evidence is separate from hostile intent.

Only granted ordinary opportunities move or strike. Commands never call this
executor; inspection and restoration never observe. No cross-scene participant.
"""
from __future__ import annotations
from dataclasses import asdict
import hashlib
from components.ai import _creature_can_see_player, _monster_attack_result
from engine.spatial import melee_attack_legal, terrain_conceals
from engine.sound import clear_interest

RETURN_BUDGET, FAILURES, RETRY = 32, 8, 12


def initialize(ai):
    ai.escort = dict(owner=None, order=ai.profile['initial_order'], post=None,
        ward=None, area=None, phase='wait', pursuit_left=0, rejoin_left=RETURN_BUDGET,
        failures=0, retry=0, route=None, retired=[], reason=None, defence=False,
        return_told=False)


def distance(p, x, y):
    return max(abs(x-p[0]), abs(y-p[1]))


def bound(ai, engine, actor):
    from engine.local_rivals import owner, allocate
    t = ai.escort
    if t['owner'] is None:
        allocate(engine, [actor])
        t.update(owner=owner(engine), area=[actor.x, actor.y])
        if t['order'] == 'hold':
            t['post'] = [actor.x, actor.y]
    return t['owner'] == owner(engine)


def sees_ward(ai, engine, actor, ambient):
    from engine.local_rivals import living, active
    ward = engine.player
    if not living(ward) or not active(engine, ward):
        return False
    if terrain_conceals(ward, engine.local_map, engine.data.terrain):
        bonus = engine.weather.get_mechanic('creature_alert_radius_bonus', 0) if engine.weather else 0
        if (ward.x-actor.x)**2+(ward.y-actor.y)**2 > max(1, actor.perception.sight_radius+bonus-2)**2:
            return False
    return _creature_can_see_player(actor, ward, engine.local_map, ambient, engine=engine)


def reference(ai):
    t = ai.escort
    if t['order'] == 'hold':
        return t['post']
    return [t['ward']['x'], t['ward']['y']] if t['ward'] else t['area']


def permits(ai, a, b):
    ref = reference(ai)
    if ref is None:
        return False
    r = ai.profile['excursion_radius']
    return (distance(ref, *b) <= r or
            (ai.target is None and distance(ref, *a) > r and distance(ref, *b) <= distance(ref, *a)))


def route_signature(ai, engine, actor):
    ref = reference(ai)
    if ref is None:
        return None
    m = engine.local_map; r = ai.profile['excursion_radius']
    occupied = {(a.x,a.y) for a in engine.entities if a is not actor and getattr(a,'blocks_movement',False)}
    cells = [(x,y,str(m.tiles[x,y]['terrain']),bool(m.walkable[x,y]),
              bool(engine._decor_blocks_movement(x,y)),(x,y) in occupied)
             for x in range(max(0,ref[0]-r),min(m.width,ref[0]+r+1))
             for y in range(max(0,ref[1]-r),min(m.height,ref[1]+r+1))]
    return hashlib.sha256(repr(cells).encode()).hexdigest()


def retire(ai, reason):
    t = ai.escort
    if ai.target:
        old = ai.target
        t['retired'] = [r for r in t['retired'] if r['id'] != old['id']][-15:] + [
            dict(id=old['id'], x=old['x'], y=old['y'], route=t['route'], lost=False)]
    t.update(phase='return', pursuit_left=0, rejoin_left=RETURN_BUDGET,
             failures=0, retry=0, reason=reason, return_told=False, defence=False)
    if reason == 'scene_departure':
        t.update(ward=None, retired=[], route=None, phase='wait')


def refresh(ai, engine, actor, ambient):
    from engine.local_rivals import owner
    t = ai.escort
    if not bound(ai, engine, actor):
        return
    if sees_ward(ai, engine, actor, ambient):
        w = t['ward']; p = engine.player
        changed = w is None or (w['x'],w['y']) != (p.x,p.y)
        now = engine.world_time.turn
        t['ward'] = dict(role='player', id=None, owner=owner(engine), x=p.x, y=p.y,
                         seen=now, deadline=now+ai.profile['pursuit_timeout'], provenance='sight')
        if changed and t['order'] == 'follow' and ai.target is None:
            t.update(rejoin_left=RETURN_BUDGET, failures=0, retry=0, phase='return')
    elif t['ward'] and engine.world_time.turn > t['ward']['deadline']:
        t['ward'] = None
        if t['order'] == 'follow':
            ai.cancel(actor, 'ward_evidence_expired')
    target = ai.resolve_target(engine, actor)
    if target is not None:
        if ai.sees(engine, actor, target, ambient):
            ai._remember(engine, target)
            if distance(reference(ai), ai.target['x'], ai.target['y']) > ai.profile['excursion_radius']:
                ai.cancel(actor, 'observed_beyond_excursion')
        elif engine.world_time.turn > ai.target['deadline']:
            ai.cancel(actor, 'threat_evidence_expired')
    clear_interest(ai)  # Anonymous sound never supplies a ward or threat identity.


def set_order(ai, actor, engine, order):
    """Caller owns physical reach and stale-confirmation validation."""
    bound(ai, engine, actor)
    ai.cancel(actor, 'local_order')
    t = ai.escort
    t.update(order=order, phase='return', area=[actor.x,actor.y],
             post=[actor.x,actor.y] if order == 'hold' else t['post'])


def rejoin(ai, actor, engine, route):
    t = ai.escort; ref = reference(ai)
    if ref is None:
        return 'wait', 'no_lawful_reference', None
    spacing = ai.profile['follow_spacing'] if t['order'] == 'follow' and t['ward'] else 0
    goal = lambda x,y: distance(ref,x,y) <= spacing
    if goal(actor.x,actor.y):
        t.update(phase='wait', failures=0, retry=0, area=[actor.x,actor.y])
        return 'wait', 'at_hold_post' if t['order'] == 'hold' else 'at_follow_reference', None
    if t['phase'] == 'blocked':
        t['retry'] = max(0,t['retry']-1)
        if route == t['route'] and t['retry']:
            return 'wait', 'bounded_retry', None
        t.update(phase='return', retry=0, failures=0, rejoin_left=RETURN_BUDGET)
    if not t['rejoin_left']:
        t.update(phase='blocked', retry=RETRY, route=route)
        return 'wait', 'rejoin_exhausted', None
    t['rejoin_left'] -= 1
    step, _ = ai._route(engine, actor, goal)
    moved = ai._move(engine, actor, step)
    t['failures'] = 0 if moved else min(FAILURES,t['failures']+1)
    if moved and not t['return_told']:
        ai._tell(engine, actor, 'returns to its place' if t['order']=='hold' else 'moves to rejoin you', current_vision=True)
        t['return_told'] = True
    if t['failures'] >= FAILURES or not t['rejoin_left']:
        t.update(phase='blocked', retry=RETRY, route=route)
    return ('move' if moved else 'wait'), 'return_to_post' if t['order']=='hold' else 'rejoin_last_sight', None


def take_turn(ai, actor, engine, ambient):
    from engine.venom import movement_denial
    t = ai.escort
    if not bound(ai, engine, actor):
        return
    refresh(ai, engine, actor, ambient)
    ai.opportunities += 1
    before = t['phase']
    observed = [a for a in ai._observed(engine, actor, ambient) if a is not engine.player]
    route = route_signature(ai, engine, actor)
    for r in t['retired']:
        if not any(ai._key(engine,a)==r['id'] for a in observed):
            r['lost'] = True
    target = ai.resolve_target(engine, actor)
    ref = reference(ai)
    if ai.target and (ref is None or distance(ref,actor.x,actor.y)>ai.profile['excursion_radius']):
        ai.cancel(actor, 'ward_moved_beyond_excursion'); target = None
    contacts = [a for a in observed if melee_attack_legal(engine.local_map,actor,a)]
    action,reason,result = 'wait','holding',None
    denied = movement_denial(actor)
    if denied:
        reason = denied
    else:
        # Committed return wins over fresh acquisition. Contact defence alternates
        # with physical return and never starts or replenishes a pursuit.
        if contacts and (target not in contacts) and not t['defence']:
            t['defence'] = True
            action,reason,result = 'melee','contact_defence',_monster_attack_result(actor,contacts[0],engine,defensive=True)
            if ai.target:
                t['pursuit_left'] = max(0,t['pursuit_left']-1)
        else:
            t['defence'] = False
            if ai.target is None and t['phase'] not in ('return','blocked') and ref and (t['order']=='hold' or t['ward']):
                for a in observed:
                    if distance(ref,a.x,a.y)>ai.profile['protection_radius']:
                        continue
                    retired = next((r for r in t['retired'] if r['id']==ai._key(engine,a)),None)
                    if retired and not (retired['lost'] or (retired['x'],retired['y'])!=(a.x,a.y) or retired['route']!=route):
                        continue
                    target = a; ai._remember(engine,a)
                    t.update(phase='protect', pursuit_left=ai.profile['pursuit_budget'], failures=0)
                    break
            if ai.target:
                t['pursuit_left'] = max(0,t['pursuit_left']-1)
                if target in observed and melee_attack_legal(engine.local_map,actor,target):
                    action,reason,result = 'melee','protect',_monster_attack_result(actor,target,engine)
                else:
                    tx,ty = ai.target['x'],ai.target['y']
                    from engine.spatial import melee_contact
                    goal = ((lambda x,y: melee_contact(engine.local_map,x,y,tx,ty)) if target in observed
                            else (lambda x,y: (x,y)==(tx,ty)))
                    step,_ = ai._route(engine,actor,goal)
                    moved = ai._move(engine,actor,step)
                    t['failures'] = 0 if moved else min(FAILURES,t['failures']+1)
                    action,reason = ('move' if moved else 'wait'),'observed_threat' if target in observed else 'threat_last_sight'
                    if target not in observed and (actor.x,actor.y)==(tx,ty):
                        ai.cancel(actor,'empty_threat_trail')
            else:
                action,reason,result = rejoin(ai,actor,engine,route)
        if ai.target and (not t['pursuit_left'] or t['failures']>=FAILURES or result and result.target_dead):
            ai.cancel(actor,'target_dead' if result and result.target_dead else 'pursuit_exhausted')
    if t['phase']!='blocked':
        t['route'] = route
    ai.trace.append(dict(opportunity=ai.opportunities,turn=engine.world_time.turn,
        phase_before=before,phase=t['phase'],action=action,reason=reason,
        result=asdict(result) if result else None))
    ai.trace = ai.trace[-16:]


def validate_state(row, s, p, local_map):
    """Exact v6 schema, including binding and disjoint ward/threat references."""
    from engine.local_rivals import OWNER, IDENTITY
    from engine.ai_profiles import validate_target_and_intent, validate_escort_alignment
    from config import MAP_WIDTH, MAP_HEIGHT
    import re
    w,h = (local_map.width,local_map.height) if local_map else (MAP_WIDTH,MAP_HEIGHT)
    def point(v):
        return isinstance(v,list) and len(v)==2 and all(type(n) is int for n in v) and 0<=v[0]<w and 0<=v[1]<h
    def digest(v):
        return v is None or isinstance(v,str) and re.fullmatch('[a-f0-9]{64}',v) is not None
    if not isinstance(s,dict) or set(s)!={'escort','target','opportunities'}:
        raise ValueError('composite.escort: complete version-6 state required')
    t=s['escort']; template=type('Initial',(),{'profile':p})(); initialize(template)
    if not isinstance(t,dict) or set(t)!=set(template.escort):
        raise ValueError('composite.escort: incomplete/unknown state')
    validate_escort_alignment(dict(faction=row.get('faction'), hostile_to=row.get('hostile_to')))
    if (t['order'] not in ('follow','hold') or t['phase'] not in ('wait','protect','return','blocked')
            or not digest(t['route']) or not point([row.get('home_x'),row.get('home_y')])):
        raise ValueError('composite.escort: invalid order/phase/home/route')
    if t['owner'] is None:
        if t!=template.escort or s['target'] is not None or s['opportunities']!=0:
            raise ValueError('composite.escort: unbound state must be fresh')
    elif (not isinstance(t['owner'],str) or not OWNER.fullmatch(t['owner'])
            or not isinstance(row.get('individual_id'),str) or not IDENTITY.fullmatch(row['individual_id'])
            or not row['individual_id'].startswith(t['owner']+':') or not point(t['area'])
            or t['order']=='hold' and not point(t['post'])
            or t['post'] is not None and not point(t['post'])):
        raise ValueError('composite.escort: invalid owning scene/instance post')
    for k,hi in (('pursuit_left',p['pursuit_budget']),('rejoin_left',RETURN_BUDGET),('failures',FAILURES),('retry',RETRY)):
        if type(t[k]) is not int or not 0<=t[k]<=hi:
            raise ValueError('composite.escort: invalid counter '+k)
    if (type(s['opportunities']) is not int or not 0<=s['opportunities']<2**63
            or any(type(t[k]) is not bool for k in ('defence','return_told'))
            or t['reason'] is not None and (not isinstance(t['reason'],str) or len(t['reason'])>80)
            or (t['phase']=='protect') != (s['target'] is not None)
            or (t['phase']=='protect') != bool(t['pursuit_left'])
            or (t['phase']=='protect' and t['order']=='follow' and t['ward'] is None)
            or (t['phase']=='wait' and t['failures'] != 0)
            or (t['phase']=='return' and t['rejoin_left'] == 0)
            or (t['phase']=='blocked') != bool(t['retry'])):
        raise ValueError('composite.escort: contradictory commitment')
    # Reuse strict ordinary evidence and legacy-intent exclusion without changing
    # v1-v5 shapes. The player can occur only in the separate ward record.
    fake=dict(s,phase='idle',suppressed=None)
    validate_target_and_intent(row,fake,p,local_map,optional_target=True)
    for evidence,role in ((s['target'],'creature'),(t['ward'],'player')):
        if evidence is None: continue
        validate_target_and_intent(row,dict(fake,target=evidence),p,local_map,optional_target=True)
        if (evidence['role']!=role or evidence['owner']!=t['owner']
                or role=='creature' and not evidence['id'].startswith(t['owner']+':')):
            raise ValueError('composite.escort: foreign/invalid ward or threat identity')
    if not isinstance(t['retired'],list) or len(t['retired'])>16:
        raise ValueError('composite.escort: bounded retired threats required')
    used=set()
    for r in t['retired']:
        if (not isinstance(r,dict) or set(r)!={'id','x','y','route','lost'}
                or not isinstance(r['id'],str) or not IDENTITY.fullmatch(r['id'])
                or r['id']==row.get('individual_id') or t['owner'] is None
                or not r['id'].startswith(t['owner']+':') or r['id'] in used
                or not point([r['x'],r['y']]) or not digest(r['route']) or type(r['lost']) is not bool):
            raise ValueError('composite.escort: invalid retired threat')
        used.add(r['id'])
