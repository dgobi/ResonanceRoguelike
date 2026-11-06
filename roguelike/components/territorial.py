"""Fixed-place v5 objective around CompositeAI's shared tactical executor.

All counters use granted ordinary opportunities. Sight expiry alone uses charged
world phases. No path/diagnostic cache is saved and no hidden prey position is read.
"""
from __future__ import annotations
from dataclasses import asdict
import hashlib
from components.ai import AIState, _monster_attack_result
from engine.spatial import melee_attack_legal, melee_contact
from engine.sound import clear_interest, current_interest

RETRY = 12
RETURN_BUDGET = 32
FAILURES = 8


def initialize(ai):
    ai.territory = dict(anchor=None, owner=None, phase='guard', pursuit_left=0,
        return_left=0, failures=0, retry=0, resting=None, retired=[], route=None,
        reason=None, defence=False, investigation_left=0, return_told=False)


def distance(anchor, x, y):
    return max(abs(x-anchor[0]), abs(y-anchor[1]))


def permits(ai, a, b):
    t = ai.territory
    anchor = t['anchor']
    if anchor is None:
        return False
    outer = ai.profile['excursion_radius']
    # External displacement recovery alone may start outside. No outward step,
    # and every later step after entering the domain remains inside it.
    return (distance(anchor, *b) <= outer or
            (t['phase'] == 'return' and distance(anchor, *a) > outer
             and distance(anchor, *b) <= distance(anchor, *a)))


def signature(ai, engine, actor):
    """Bounded local route conditions, independent of sight and own movement."""
    ax, ay = ai.territory['anchor']; r = ai.profile['excursion_radius']
    m = engine.local_map
    occupied = {(a.x, a.y) for a in engine.entities if a is not actor and getattr(a, 'blocks_movement', False)}
    cells = [(x, y, str(m.tiles[x,y]['terrain']), bool(m.walkable[x,y]),
              bool(engine._decor_blocks_movement(x,y)), (x,y) in occupied)
             for x in range(max(0,ax-r), min(m.width,ax+r+1))
             for y in range(max(0,ay-r), min(m.height,ay+r+1))]
    return hashlib.sha256(repr(cells).encode()).hexdigest()


def retire(ai, actor, reason):
    """Called by shared cancellation, before its target/counters are cleared."""
    t = ai.territory
    if ai.target:
        key = 'player' if ai.target['role'] == 'player' else ai.target['id']
        row = dict(key=key, x=ai.target['x'], y=ai.target['y'], route=t['route'], lost=False)
        t['retired'] = [r for r in t['retired'] if r['key'] != key][-15:] + [row]
    if t['phase'] not in ('return', 'blocked'):
        t.update(phase='return', return_left=RETURN_BUDGET, failures=0,
                 resting=None, retry=0, return_told=False, defence=False)
    t.update(pursuit_left=0, investigation_left=0, reason=reason)


def refresh(ai, engine, actor, ambient):
    from engine.local_rivals import owner
    t = ai.territory
    if t['anchor'] is None:
        t['anchor'] = [ai.home_x, ai.home_y]
        t['owner'] = owner(engine)
    if t['owner'] != owner(engine):
        if ai.target:
            ai.cancel(actor, 'foreign_scene')
        return
    if distance(t['anchor'], actor.x, actor.y) > ai.profile['excursion_radius'] and t['phase'] not in ('return','blocked'):
        ai.cancel(actor, 'external_displacement')
    target = ai.resolve_target(engine, actor)
    if target is None:
        return
    if ai.sees(engine, actor, target, ambient):
        ai._remember(engine, target)
        if distance(t['anchor'], ai.target['x'], ai.target['y']) > ai.profile['excursion_radius']:
            ai.cancel(actor, 'observed_beyond_excursion')
    elif engine.world_time.turn > ai.target['deadline']:
        ai.cancel(actor, 'evidence_expired')
    if ai.target:
        clear_interest(ai)


def _return(ai, actor, engine, observed, route):
    t = ai.territory
    clear_interest(ai)  # ignored sounds never queue behind a committed return
    if t['phase'] == 'blocked':
        t['retry'] = max(0, t['retry']-1)
        if route == t['route'] and t['retry']:
            return 'wait', 'blocked_return', None
        t.update(phase='return', return_left=RETURN_BUDGET, failures=0, retry=0)
    contacts = [a for a in observed if melee_attack_legal(engine.local_map, actor, a)]
    # Contact defence can spend a normal action, never start a tactical cycle.
    # Alternate with route opportunities so continuous contact cannot pin return.
    if contacts and not t['defence']:
        t['defence'] = True
        return 'melee', 'return_contact_defence', _monster_attack_result(actor, contacts[0], engine, defensive=True)
    t['defence'] = False
    anchor = tuple(t['anchor'])
    nearby = sorted([(anchor[0]+dx, anchor[1]+dy) for dx in (-1,0,1) for dy in (-1,0,1)],
                    key=lambda p: (distance(anchor,*p), p[1], p[0]))
    occupied = {(a.x,a.y) for a in engine.entities if a is not actor and getattr(a,'blocks_movement',False)}
    can_swim = engine.data.entities.get(actor._creature_id,{}).get('can_swim',False)
    result = (None, None, None)
    outside = distance(anchor,actor.x,actor.y) > ai.profile['excursion_radius']
    if outside:
        # Far displacement need not fit a complete home route in the shared
        # 16-step search. Recover toward the domain, never toward an opponent.
        current = distance(anchor,actor.x,actor.y)
        step,length = ai._route(engine,actor,lambda x,y: distance(anchor,x,y)<current)
        result = step,length,None
    for goal in (() if outside else nearby):
        if (not engine.local_map.in_bounds(*goal) or goal in occupied
                or not engine.local_map.walkable[goal] or engine._decor_blocks_movement(*goal)
                or not (engine.data.terrain.get(str(engine.local_map.tiles[goal]['terrain']),{}).get('creature_passable',True) or can_swim)):
            continue
        step, length = ai._route(engine, actor, lambda x,y: (x,y) == goal)
        if length is not None:
            result = step, length, goal
            break
    step, length, goal = result
    if length == 0:
        t.update(phase='guard', resting=list(goal), failures=0, return_left=0, route=route)
        return 'wait', 'at_post' if goal == anchor else 'nearby_post', None
    t['return_left'] = max(0,t['return_left']-1)
    moved = ai._move(engine, actor, step)
    t['failures'] = 0 if moved else min(FAILURES,t['failures']+1)
    if moved and not t['return_told']:
        ai._tell(engine, actor, 'walks back toward its familiar place', current_vision=True)
        t['return_told'] = True
    if t['failures'] >= FAILURES or t['return_left'] == 0:
        t.update(phase='blocked', retry=RETRY, route=route)
    elif moved and (actor.x,actor.y) == goal:
        t.update(phase='guard', resting=list(goal), failures=0, return_left=0, route=route)
    return ('move' if moved else 'wait'), 'returning_to_post', None


def take_turn(ai, actor, engine, ambient):
    from engine.local_rivals import owner
    ai.opportunities += 1
    before = ai.territory['phase']
    refresh(ai, engine, actor, ambient)
    from engine import enemy_scavenging as scavenging
    scavenging.refresh(ai,engine,actor,ambient)
    t = ai.territory
    action, reason, result = 'wait', 'guarding', None
    if t['owner'] != owner(engine):
        reason = 'foreign_scene'
    else:
        observed = ai._observed(engine, actor, ambient)
        route = signature(ai, engine, actor)
        seen_keys = {ai._key(engine,a) for a in observed}
        for row in t['retired']:
            if row['key'] not in seen_keys:
                row['lost'] = True
        if t['phase'] in ('return','blocked'):
            scavenging.retire(ai,'territorial_return')
            action, reason, result = _return(ai, actor, engine, observed, route)
        else:
            if (t['phase'] == 'guard' and (actor.x,actor.y) != tuple(t['anchor'])
                    and not (ai.responses and ai.responses['interest'])
                    and not (ai.scavenging_state and ai.scavenging_state['current'])):
                # A declared fallback holds until route conditions change.
                if t['resting'] != [actor.x,actor.y] or route != t['route']:
                    ai.cancel(actor,'displaced_or_post_changed')
            if t['phase'] not in ('return','blocked') and ai.target is None:
                for candidate in observed:
                    if distance(t['anchor'], candidate.x, candidate.y) > ai.profile['defended_radius']:
                        continue
                    key = ai._key(engine,candidate)
                    old = next((r for r in t['retired'] if r['key']==key),None)
                    if old and not (old['lost'] or (old['x'],old['y']) != (candidate.x,candidate.y) or old['route'] != route):
                        continue
                    t['retired'] = [r for r in t['retired'] if r['key'] != key]
                    ai._remember(engine,candidate)
                    ai.phase,ai.approach_left = 'approach',32
                    ai.best_distance,ai.no_progress = None,0
                    t.update(phase='engaged',pursuit_left=ai.profile['pursuit_budget'],investigation_left=0,reason=None)
                    clear_interest(ai)
                    break
            if t['phase']=='engaged' and not t['pursuit_left']:
                ai.cancel(actor,'pursuit_exhausted')
            from engine.enemy_components import choose
            reaction = choose(ai, engine, actor, observed, ambient)
            if reaction:
                scavenging.retire(ai,'higher_priority')
                action,reason,result = reaction
                if t['phase']=='engaged':
                    t['pursuit_left'] = max(0,t['pursuit_left']-1)
                    if not t['pursuit_left']: ai.cancel(actor,'pursuit_exhausted')
            elif t['phase'] == 'engaged':
                scavenging.retire(ai,'host_commitment')
                target = ai.resolve_target(engine,actor)
                if target is not None:
                    t['route'] = route
                    t['pursuit_left'] = max(0,t['pursuit_left']-1)
                    action,reason,result = ai._engage(engine,actor,target,observed)
                    if t['phase'] == 'engaged' and t['pursuit_left'] == 0:
                        ai.cancel(actor,'pursuit_exhausted')
                        reason = 'pursuit_exhausted'
            elif t['phase'] in ('guard','investigate'):
                interest = current_interest(ai,engine.world_time.turn)
                if interest and distance(t['anchor'],interest['x'],interest['y']) > ai.profile['defended_radius']:
                    clear_interest(ai);interest=None
                if interest:
                    scavenging.retire(ai,'anonymous_sound')
                    if t['phase'] != 'investigate':
                        t.update(phase='investigate',investigation_left=8,failures=0)
                    sx,sy = interest['x'],interest['y']
                    occupied = any(a is not actor and getattr(a,'blocks_movement',False) and (a.x,a.y)==(sx,sy) for a in engine.entities)
                    # A bell's nonwalkable source is anonymous information,
                    # not a combat endpoint. Reach a legal cardinal approach.
                    goal = (lambda x,y: abs(x-sx)+abs(y-sy)==1) if occupied or not engine.local_map.walkable[sx,sy] else (lambda x,y: (x,y)==(sx,sy))
                    step,length = ai._route(engine,actor,goal)
                    t['investigation_left'] = max(0,t['investigation_left']-1)
                    moved = ai._move(engine,actor,step)
                    action,reason = ('move' if moved else 'wait'),'anonymous_sound'
                    if moved and before != 'investigate':
                        ai._tell(engine,actor,'turns toward a disturbance',current_vision=True)
                    if length == 0 or goal(actor.x,actor.y) or not t['investigation_left']:
                        ai.cancel(actor,'sound_resolved')
                elif t['phase'] == 'investigate':
                    ai.cancel(actor,'sound_expired')
                else:
                    food_action=scavenging.choose(ai,engine,actor,ambient)
                    if food_action:action,reason,result=food_action
            # A newly committed return may begin on the next opportunity only.
            if t['phase'] in ('return','blocked'):
                clear_interest(ai)
        if t['phase'] not in ('blocked','guard'):
            t['route'] = route
    ai.trace.append(dict(opportunity=ai.opportunities,turn=engine.world_time.turn,
        phase_before=before,phase=t['phase'],engagement=ai.phase,action=action,reason=reason,
        result=asdict(result) if result else None))
    ai.trace = ai.trace[-16:]


def validate_state(row, s, p, local_map):
    """Exact v5 state only; validate before any staged save is installed."""
    from engine.ai_profiles import validate_target_and_intent
    from engine.local_rivals import OWNER, IDENTITY
    from config import MAP_WIDTH, MAP_HEIGHT
    import re
    w,h = (local_map.width,local_map.height) if local_map else (MAP_WIDTH,MAP_HEIGHT)
    keys = {'phase','target','withdraw_left','hold_left','approach_left','no_progress',
            'best_distance','suppressed','route_blocked','opportunities','territory'}
    if not isinstance(s,dict) or set(s)-{'withdrawal_told'} != keys:
        raise ValueError('composite.state: complete v5 territorial commitment required')
    if 'withdrawal_told' in s and type(s['withdrawal_told']) is not bool:
        raise ValueError('composite.state.withdrawal_told: expected boolean')
    t = s['territory']; template = type('Initial',(),{})(); initialize(template)
    if not isinstance(t,dict) or set(t) != set(template.territory):
        raise ValueError('composite.territory: incomplete or unknown fields')
    def point(value):
        return isinstance(value,list) and len(value)==2 and all(type(n) is int for n in value) and 0<=value[0]<w and 0<=value[1]<h
    def digest(value):
        return value is None or (isinstance(value,str) and re.fullmatch('[a-f0-9]{64}',value) is not None)
    if not point([row.get('home_x'),row.get('home_y')]):
        raise ValueError('composite.territory: legitimate saved home required')
    if t['anchor'] is None:
        if t != template.territory or s['target'] is not None or s['phase'] != 'idle':
            raise ValueError('composite.territory: unbound objective must be fresh')
    elif (not point(t['anchor']) or t['anchor'] != [row['home_x'],row['home_y']]
          or not isinstance(t['owner'],str) or not OWNER.fullmatch(t['owner'])
          or isinstance(row.get('individual_id'),str) and not row['individual_id'].startswith(t['owner']+':')):
        raise ValueError('composite.territory: invalid original anchor/scene')
    if t['phase'] not in ('guard','engaged','return','blocked','investigate') or not digest(t['route']):
        raise ValueError('composite.territory: invalid phase/route signature')
    if t['resting'] is not None and (not point(t['resting']) or t['anchor'] is None or distance(t['anchor'],*t['resting'])>1):
        raise ValueError('composite.territory: fallback must be adjacent to original post')
    if any(type(t[k]) is not bool for k in ('defence','return_told')) or (t['reason'] is not None and (not isinstance(t['reason'],str) or len(t['reason'])>80)):
        raise ValueError('composite.territory: invalid return commitment')
    for k,hi in (('pursuit_left',p['pursuit_budget']),('return_left',RETURN_BUDGET),('failures',FAILURES),('retry',RETRY),('investigation_left',8)):
        if type(t[k]) is not int or not 0<=t[k]<=hi:
            raise ValueError('composite.territory: invalid opportunity counter '+k)
    if (not isinstance(t['retired'],list) or len(t['retired'])>16):
        raise ValueError('composite.territory: bounded retirement list required')
    used=set()
    for r in t['retired']:
        if (not isinstance(r,dict) or set(r)!={'key','x','y','route','lost'} or not isinstance(r['key'],str)
            or (r['key']!='player' and not IDENTITY.fullmatch(r['key'])) or r['key'] in used
            or not point([r['x'],r['y']]) or not digest(r['route']) or type(r['lost']) is not bool):
            raise ValueError('composite.territory: invalid retired sight evidence')
        used.add(r['key'])
    if (s['phase'] not in ('idle','approach','withdraw','hold','return','cornered')
        or type(s['route_blocked']) is not bool or s['suppressed'] is not None and not isinstance(s['suppressed'],str)):
        raise ValueError('composite.state: invalid engagement')
    for k,hi in (('withdraw_left',p['withdrawal_budget']),('hold_left',p['hold_opportunities']),('approach_left',32),('no_progress',8),('opportunities',2**63-1)):
        if type(s[k]) is not int or not 0<=s[k]<=hi:
            raise ValueError('composite.state: invalid tactical counter '+k)
    if s['best_distance'] is not None and (type(s['best_distance']) is not int or not 0<=s['best_distance']<=16):
        raise ValueError('composite.state: invalid route progress')
    engaged = t['phase']=='engaged'
    if (engaged != (s['target'] is not None) or engaged != (s['phase']!='idle')
        or (engaged and not t['pursuit_left']) or (not engaged and t['pursuit_left'])
        or (t['phase']=='investigate') != bool(t['investigation_left'])
        or (t['phase']=='blocked' and not t['retry'])
        or (s['phase']=='hold' and not s['hold_left']) or (s['phase']=='withdraw' and not s['withdraw_left'])
        or (p['engagement']=='direct_melee' and s['phase'] not in ('idle','approach'))):
        raise ValueError('composite.territory: phase/counters disagree')
    validate_target_and_intent(row,s,p,local_map,optional_target=True)
    if s['target'] and s['target']['owner'] != t['owner']:
        raise ValueError('composite.territory: foreign target evidence')
    if (s['phase']=='idle' and any(s[k] for k in ('withdraw_left','hold_left','approach_left','no_progress'))
        or s['suppressed'] is not None and s['suppressed']!='player' and not IDENTITY.fullmatch(s['suppressed'])):
        raise ValueError('composite.state: invalid idle/retired intent')
