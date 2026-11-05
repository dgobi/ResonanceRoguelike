"""Finite, sight-owned lateral approach and wounded regroup attachments.

Routes are transient. Each choice spends the host's one ordinary opportunity;
charged expiry also ages when a higher priority or physical denial prevents it.
"""
from __future__ import annotations
import copy
from engine.enemy_components import RECIPES

LATERAL = 'seek_lateral_approach'
REGROUP = 'regroup_when_wounded'
REGISTRY = {
    LATERAL: dict(opportunity_budget=8, expiry_phases=16),
    REGROUP: dict(wounded_percent=50, rearm_percent=75, opportunity_budget=6,
                  hold_opportunities=2, expiry_phases=16),
}
BOUNDS = {
    LATERAL: dict(opportunity_budget=(2,12), expiry_phases=(4,32)),
    REGROUP: dict(wounded_percent=(10,70), rearm_percent=(50,95),
                  opportunity_budget=(2,12), hold_opportunities=(0,3), expiry_phases=(4,32)),
}
QUIET_REARM = 24


def configuration(value, profile, perception, *, complete=False):
    from engine.enemy_responses import alignment
    if value is None:
        return None
    if (not isinstance(value, dict) or set(value) != {'version','modules'}
            or type(value['version']) is not int or value['version'] != 1
            or not isinstance(value['modules'], list) or len(value['modules']) > 2):
        raise ValueError('enemy_maneuvers: version 1 and at most two registered modules required')
    if profile['recipe'] not in RECIPES:
        raise ValueError('enemy_maneuvers: requires an ordinary hostile recipe v1-v5')
    alignment(perception)
    result, used = [], set()
    for row in value['modules']:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or row['id'] not in REGISTRY or row['id'] in used:
            raise ValueError('enemy_maneuvers: unknown or duplicate module')
        key = row['id']; defaults = REGISTRY[key]
        if set(row)-{'id', *defaults} or complete and set(row) != {'id', *defaults}:
            raise ValueError('enemy_maneuvers: unsupported or incomplete fields')
        effective = dict(defaults, **row)
        for name, (lo, hi) in BOUNDS[key].items():
            if type(effective[name]) is not int or not lo <= effective[name] <= hi:
                raise ValueError(f'enemy_maneuvers.{key}.{name}: integer {lo}..{hi} required')
        if key == REGROUP and effective['rearm_percent'] <= effective['wounded_percent']:
            raise ValueError('enemy_maneuvers: rearm_percent must exceed wounded_percent')
        result.append(effective); used.add(key)
    return dict(version=1, modules=result)


def initial():
    return dict(owner=None, current=None, flank_spent=False, regroup_spent=False,
                quiet_phases=0, last_phase=None)


def initialize(ai, config):
    ai.maneuver_config = copy.deepcopy(config)
    ai.maneuvers = initial() if config is not None else None
    ai.maneuver_trace = []
    ai.attachment_steps = []


def module(ai, identifier):
    return next((r for r in (ai.maneuver_config or {}).get('modules',[]) if r['id'] == identifier), None)


def note(ai, engine, reason, **facts):
    ai.maneuver_trace.append(dict(turn=engine.world_time.turn, reason=reason, **facts))
    ai.maneuver_trace = ai.maneuver_trace[-16:]


def cancel(ai):
    if ai.maneuvers is not None:
        ai.maneuvers['current'] = None
        ai.maneuvers['quiet_phases'] = 0
        # Departure, target switch and interruption never restore spent credit.


def release(ai, engine, reason):
    if ai.maneuvers['current']:
        note(ai, engine, reason, kind=ai.maneuvers['current']['kind'])
        ai.maneuvers['current'] = None


def reconcile_position(ai, engine, actor):
    """Mandatory host movement may leave a paid hold, never buy more travel."""
    c = ai.maneuvers and ai.maneuvers['current']
    if c and c['left'] <= 0 and [actor.x, actor.y] != c['goal']:
        release(ai, engine, 'exhausted_hold_displaced')


def refresh(ai, engine, actor, ambient):
    if ai.maneuvers is None:
        return
    from engine.local_rivals import owner, active, living, allocate
    s = ai.maneuvers; now = engine.world_time.turn
    if s['owner'] is None:
        allocate(engine, [actor]); s['owner'] = owner(engine)
    if not active(engine, actor) or not living(actor) or s['owner'] != owner(engine):
        cancel(ai); return
    from engine.effect_lifecycle import disrupted
    if disrupted(actor,engine.local_map):
        cancel(ai); return
    if s['current'] and now > s['current']['deadline']:
        release(ai, engine, 'charged_expiry')
    if s['last_phase'] == now:
        return
    quiet = (ai.target is None and s['current'] is None
             and not (ai.responses and ai.responses['interest'])
             and not ai._observed(engine, actor, ambient))
    s['quiet_phases'] = (min(QUIET_REARM, s['quiet_phases']+1)
                         if quiet and s['last_phase'] is not None and now == s['last_phase']+1 else 0)
    s['last_phase'] = now
    if s['quiet_phases'] == QUIET_REARM:
        s['flank_spent'] = s['regroup_spent'] = False
    config = module(ai, REGROUP)
    if config and s['current'] is None and 100*actor.fighter.hp > config['rearm_percent']*actor.fighter.max_hp:
        s['regroup_spent'] = False


def supporters(ai, engine, actor, ambient):
    """Own sensory visibility, not hostile-only target eligibility or ally secrets."""
    from engine.local_rivals import living, active, allocate
    from components.ai import _creature_can_see_player
    from engine.spatial import terrain_conceals
    p = actor.perception; found = []
    for other in engine.entities:
        q = getattr(other, 'perception', None)
        if (other is actor or other is engine.player or not living(other) or not active(engine, other)
                or not q or not getattr(other, 'ai', None) or q.faction != p.faction
                or p.is_hostile_to(q.faction) or q.is_hostile_to(p.faction)):
            continue
        if terrain_conceals(other, engine.local_map, engine.data.terrain):
            radius = p.sight_radius + (engine.weather.get_mechanic('creature_alert_radius_bonus',0) if engine.weather else 0)
            if (other.x-actor.x)**2+(other.y-actor.y)**2 > max(1,radius-2)**2:
                continue
        if _creature_can_see_player(actor, other, engine.local_map, ambient, engine=engine):
            found.append(other)
    allocate(engine, [actor]+found)
    return sorted(found, key=lambda a: (max(abs(a.x-actor.x),abs(a.y-actor.y)), a._individual_id))


def _start(ai, engine, actor, kind, supporter, goal):
    c = module(ai, kind); s = ai.maneuvers; now = engine.world_time.turn
    key = None if ai.target is None else ('player' if ai.target['role']=='player' else ai.target['id'])
    prey = None if ai.target is None else [ai.target['x'], ai.target['y']]
    if kind == REGROUP:
        if ai.profile['recipe'] == 'patient_venom_hunt' and ai.target:
            ai._retire_target(actor, 'wounded_hunt_retired')
        from engine.enemy_responses import cancel as cancel_responses
        from engine.sound import clear_interest
        cancel_responses(ai); clear_interest(ai)
    s['current'] = dict(kind=kind, supporter=supporter._individual_id,
        support=[supporter.x,supporter.y], seen=now, goal=list(goal),
        target=key, prey=prey, begun=now, deadline=now+c['expiry_phases'],
        left=c['opportunity_budget'], hold_left=c.get('hold_opportunities',0))
    s['quiet_phases'] = 0
    s['flank_spent' if kind == LATERAL else 'regroup_spent'] = True
    note(ai, engine, 'started', **copy.deepcopy(s['current']))
    if kind == REGROUP:
        ai._tell(engine, actor, 'draws toward its kin', current_vision=True)


def lateral_route(ai,engine,actor,prey,goal):
    # Do not plan through an earlier melee contact on the direct side: the host
    # must attack there, which would erase the intended alternate approach.
    forbidden={(prey[0]+dx,prey[1]+dy) for dx in (-1,0,1) for dy in (-1,0,1)}-{tuple(goal)}
    return ai._route(engine,actor,lambda x,y:(x,y)==tuple(goal),forbidden=forbidden)


def _continue(ai, engine, actor, observed, ambient):
    from engine.enemy_components import move
    c = ai.maneuvers['current']; kind = c['kind']
    support = next((a for a in supporters(ai,engine,actor,ambient) if a._individual_id == c['supporter']), None)
    if support is None or [support.x,support.y] != c['support']:
        release(ai,engine,'support_lost_or_moved'); return None
    if kind == LATERAL:
        target = next((a for a in observed if ai._key(engine,a) == c['target']), None)
        if target is None or [target.x,target.y] != c['prey']:
            release(ai,engine,'prey_changed_or_unseen'); return None
    c['seen'] = engine.world_time.turn
    if (actor.x,actor.y) == tuple(c['goal']):
        if kind == REGROUP and c['hold_left']:
            c['hold_left'] -= 1
            note(ai,engine,'regroup_hold',remaining=c['hold_left'],used_action=True)
            if not c['hold_left']: release(ai,engine,'regroup_complete')
            return 'wait','regroup_hold',None
        release(ai,engine,'maneuver_arrived'); return None
    if c['left'] <= 0:
        release(ai,engine,'movement_exhausted'); return None
    if not actor.fighter.can_move():
        return 'wait','maneuver_movement_denied',None
    step,length = (lateral_route(ai,engine,actor,c['prey'],c['goal']) if kind==LATERAL else
                   ai._route(engine,actor,lambda x,y: (x,y)==tuple(c['goal'])))
    if step is None:
        release(ai,engine,'route_invalid'); return None
    c['left'] -= 1
    moved = move(ai,engine,actor,step)
    reason = 'lateral_approach' if kind == LATERAL else 'wounded_regroup'
    note(ai,engine,reason,goal=c['goal'],support=c['support'],own_sight=True,
         remaining=c['left'],used_action=True,moved=moved)
    arrived_for_hold = (kind == REGROUP and (actor.x,actor.y) == tuple(c['goal']) and c['hold_left'] > 0)
    if not moved or c['left'] == 0 and not arrived_for_hold:
        release(ai,engine,'movement_exhausted' if moved else 'movement_invalid')
    return ('move' if moved else 'wait'),reason,None


def regroup(ai, engine, actor, observed, ambient, flags):
    c = module(ai,REGROUP)
    if not c: return None
    if not flags['regroup']:
        note(ai,engine,flags['reason'],module=REGROUP,eligible=False); return None
    s = ai.maneuvers
    if s['current'] and s['current']['kind'] == REGROUP:
        return _continue(ai,engine,actor,observed,ambient)
    report = ai.responses and ai.responses['interest']
    encounter = ai.target is not None or bool(report and engine.world_time.turn > report['incident']['emitted'])
    if s['regroup_spent'] or not encounter or 100*actor.fighter.hp > c['wounded_percent']*actor.fighter.max_hp:
        note(ai,engine,'regroup_spent' if s['regroup_spent'] else 'no_own_encounter' if not encounter else 'above_wound_threshold',module=REGROUP,eligible=False)
        return None
    allies = supporters(ai,engine,actor,ambient)
    # A fixed supporter position, never a moving destination or another actor's
    # health/target/order. Mutual wounded retreat cannot perpetually chase.
    for ally in allies[:4]:
        if max(abs(ally.x-actor.x),abs(ally.y-actor.y)) > 8:
            continue
        candidates = [(ally.x+dx,ally.y+dy) for dx,dy in ((0,-1),(-1,0),(1,0),(0,1))]
        if ai.target:
            tx,ty = ai.target['x'],ai.target['y']
            candidates.sort(key=lambda p: (-max(abs(p[0]-tx),abs(p[1]-ty)),p))
        for goal in candidates:
            if ai.target and max(abs(goal[0]-ai.target['x']),abs(goal[1]-ai.target['y'])) < 2:
                continue
            step,length = ai._route(engine,actor,lambda x,y: (x,y)==goal)
            if length is not None and length <= c['opportunity_budget']:
                _start(ai,engine,actor,REGROUP,ally,goal)
                return _continue(ai,engine,actor,observed,ambient)
    if allies:
        s['regroup_spent'] = True
        note(ai,engine,'no_useful_regroup_route',eligible=False)
    else:
        note(ai,engine,'no_visible_support',module=REGROUP,eligible=False)
    return None


def lateral(ai, engine, actor, observed, ambient, flags):
    from engine.spatial import melee_attack_legal
    c = module(ai,LATERAL)
    if not c: return None
    s = ai.maneuvers
    if not flags['approach']:
        note(ai,engine,flags['reason'],module=LATERAL,eligible=False); return None
    target = next((a for a in observed if ai.target and ai._key(engine,a) == ('player' if ai.target['role']=='player' else ai.target['id'])),None)
    if target is None:
        if s['current'] and s['current']['kind']==LATERAL: release(ai,engine,'no_fresh_prey_sight')
        note(ai,engine,'no_fresh_prey_sight',module=LATERAL,eligible=False)
        return None
    if melee_attack_legal(engine.local_map,actor,target):
        if s['current'] and s['current']['kind']==LATERAL: release(ai,engine,'legal_melee_priority')
        note(ai,engine,'legal_melee_priority',module=LATERAL,eligible=False)
        return None
    if s['current']:
        return _continue(ai,engine,actor,observed,ambient) if s['current']['kind']==LATERAL else None
    if s['flank_spent']:
        note(ai,engine,'lateral_spent',module=LATERAL,eligible=False); return None
    ax,ay = actor.x-target.x,actor.y-target.y
    allies = [a for a in supporters(ai,engine,actor,ambient)
              if 0 < max(abs(a.x-target.x),abs(a.y-target.y)) < max(abs(ax),abs(ay))
              and ax*(a.x-target.x)+ay*(a.y-target.y)>0
              and abs(ax*(a.y-target.y)-ay*(a.x-target.x)) <= max(abs(ax),abs(ay))]
    if not allies:
        note(ai,engine,'no_useful_visible_support',module=LATERAL,eligible=False); return None
    # Stable identity flips side preference; all destinations still use occupancy
    # and final contact checks. One finite attempt prevents oscillating retries.
    side = 1 if int(actor._individual_id.rsplit(':',1)[-1]) % 2 else -1
    offsets = [(dx,dy) for dx,dy in ((0,-1),(-1,0),(1,0),(0,1))
               if abs(ax*dy-ay*dx) > abs(ax*dx+ay*dy)]
    offsets.sort(key=lambda p: (-side*(ax*p[1]-ay*p[0]),p))
    for dx,dy in offsets:
        goal = target.x+dx,target.y+dy
        step,length = lateral_route(ai,engine,actor,[target.x,target.y],goal)
        if length is not None and 0 < length <= min(c['opportunity_budget'],max(abs(ax),abs(ay))+4):
            _start(ai,engine,actor,LATERAL,allies[0],goal)
            return _continue(ai,engine,actor,observed,ambient)
    s['flank_spent'] = True
    note(ai,engine,'no_lateral_route',eligible=False)
    return None


def validate_saved(value, row, profile, local_map):
    from engine.local_rivals import OWNER, IDENTITY
    from config import MAP_WIDTH, MAP_HEIGHT
    if not isinstance(value,dict) or set(value)!={'config','state'}:
        raise ValueError('enemy_maneuvers: saved config/state required')
    config = configuration(value['config'],profile,dict(faction=row.get('faction'),hostile_to=row.get('hostile_to')),complete=True)
    if config is None: raise ValueError('enemy_maneuvers: null saved attachment')
    s = value['state']; modules = {r['id']:r for r in config['modules']}
    def integer(v,lo=0,hi=2**63-1): return type(v) is int and lo <= v <= hi
    def fail(): raise ValueError('enemy_maneuvers: inconsistent bounded saved state')
    if not isinstance(s,dict) or set(s)!=set(initial()): fail()
    if (type(s['flank_spent']) is not bool or type(s['regroup_spent']) is not bool
            or not integer(s['quiet_phases'],hi=QUIET_REARM)
            or s['last_phase'] is not None and not integer(s['last_phase'])): fail()
    if s['owner'] is None:
        if s!=initial(): fail()
    elif (not isinstance(s['owner'],str) or not OWNER.fullmatch(s['owner'])
          or not isinstance(row.get('individual_id'),str) or row['individual_id'].rsplit(':',1)[0]!=s['owner']): fail()
    if LATERAL not in modules and s['flank_spent'] or REGROUP not in modules and s['regroup_spent']: fail()
    c = s['current']
    if c is None: return
    w,h = (local_map.width,local_map.height) if local_map else (MAP_WIDTH,MAP_HEIGHT)
    def cell(v): return isinstance(v,list) and len(v)==2 and integer(v[0],hi=w-1) and integer(v[1],hi=h-1)
    def identity(v): return isinstance(v,str) and bool(IDENTITY.fullmatch(v)) and v.rsplit(':',1)[0]==s['owner']
    if (not isinstance(c,dict) or set(c)!={'kind','supporter','support','seen','goal','target','prey','begun','deadline','left','hold_left'}
            or not isinstance(c['kind'],str) or c['kind'] not in modules): fail()
    cfg = modules[c['kind']]
    if (not identity(c['supporter']) or c['supporter']==row.get('individual_id')
            or not cell(c['support']) or not cell(c['goal'])
            or not integer(c['begun']) or not integer(c['seen'],lo=c['begun'])
            or not integer(c['deadline']) or c['deadline']!=c['begun']+cfg['expiry_phases']
            or c['seen']>c['deadline'] or s['last_phase'] is None or s['last_phase']<c['begun']
            or not integer(c['left'],0,cfg['opportunity_budget'])
            or not integer(c['hold_left'],hi=cfg.get('hold_opportunities',0))
            or c['target'] is not None and c['target']!='player' and not identity(c['target'])
            or (c['target'] is None)!=(c['prey'] is None) or c['prey'] is not None and not cell(c['prey'])
            or not s['flank_spent' if c['kind']==LATERAL else 'regroup_spent']): fail()
    base = row['composite']['state']
    if c['left'] == 0 and (c['kind'] != REGROUP or not c['hold_left']
                          or [row['x'],row['y']] != c['goal']): fail()
    anchor = c['prey'] if c['kind']==LATERAL else c['support']
    if anchor is None or s['quiet_phases'] or abs(c['goal'][0]-anchor[0])+abs(c['goal'][1]-anchor[1])!=1:
        fail()
    if c['kind']==LATERAL and (c['target'] is None or base['target'] is None
            or c['target']!=('player' if base['target']['role']=='player' else base['target']['id'])): fail()
    if c['kind']==REGROUP and (row['composite'].get('responses',{}).get('state',{}).get('prepared') is not None
            or row['composite'].get('responses',{}).get('state',{}).get('interest') is not None
            or profile['recipe']=='patient_venom_hunt' and base['hunt'] is not None): fail()
    if profile['recipe']=='territorial_guard':
        from components.territorial import distance
        t = base['territory']
        if t['phase']!='engaged' or distance(t['anchor'],*c['goal'])>profile['excursion_radius']: fail()
