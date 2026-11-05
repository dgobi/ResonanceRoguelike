"""Two opt-in enemy reactions. Information delivery never grants an action.

Separate from historical recipe profiles; absent attachments serialize nothing.
WorldTime.turn is the charged-phase clock. Route/failed-step budgets spend only
granted ordinary decisions. No target information is carried by an incident.
"""
from __future__ import annotations
import copy
import re

CALL = 'alarm_call_on_sight'
ANSWER = 'investigate_allied_alarm'
REGISTRY = {
    CALL: dict(cooldown_phases=24, rearm_unseen_phases=12, strength=12),
    ANSWER: dict(expiry_phases=16, opportunity_budget=12, failure_budget=2),
}
BOUNDS = {
    CALL: dict(cooldown_phases=(12, 120), rearm_unseen_phases=(6, 60), strength=(6, 18)),
    ANSWER: dict(expiry_phases=(4, 32), opportunity_budget=(1, 24), failure_budget=(1, 4)),
}
RECIPES = ('strike_and_withdraw', 'territorial_guard')
RECEIPT_COOLDOWN = 8
INCIDENT = re.compile(r'(.+):(\d{8,16})@(\d{1,16})\Z')


def alignment(perception):
    from engine.local_rivals import TOKEN
    p = perception
    if (not isinstance(p, dict) or not isinstance(p.get('faction'), str)
            or not TOKEN.fullmatch(p['faction']) or p['faction'] == 'player'
            or not isinstance(p.get('hostile_to'), list) or 'player' not in p['hostile_to']
            or len(p['hostile_to']) > 16
            or any(not isinstance(v, str) or not TOKEN.fullmatch(v) for v in p['hostile_to'])
            or len(set(p['hostile_to'])) != len(p['hostile_to'])):
        raise ValueError('enemy_responses: explicit non-player faction and distinct hostile_to including player required')


def configuration(value, profile, perception, *, complete=False):
    if value is None:
        return None
    if (not isinstance(value, dict) or set(value) != {'version', 'modules'}
            or type(value['version']) is not int or value['version'] not in (1, 2)
            or not isinstance(value['modules'], list) or not 0 <= len(value['modules']) <= 2):
        raise ValueError('enemy_responses: version 1 or 2 and at most two registered modules required')
    from engine.enemy_components import RECIPES as EXPANDED_RECIPES
    if profile['recipe'] not in (RECIPES if value['version']==1 else EXPANDED_RECIPES):
        raise ValueError('enemy_responses: v1 supports strike_and_withdraw/territorial_guard; v2 supports hostile recipes v1-v5')
    alignment(perception)
    result = []
    used = set()
    for row in value['modules']:
        if (not isinstance(row, dict) or not isinstance(row.get('id'), str)
                or row['id'] not in REGISTRY or row['id'] in used):
            raise ValueError('enemy_responses: unknown or duplicate module')
        key = row['id']; defaults = REGISTRY[key]
        if set(row) - {'id', *defaults} or complete and set(row) != {'id', *defaults}:
            raise ValueError('enemy_responses: unsupported or incomplete module fields')
        effective = {'id':key, **defaults, **{k:v for k,v in row.items() if k != 'id'}}
        for k, (lo, hi) in BOUNDS[key].items():
            if type(effective[k]) is not int or not lo <= effective[k] <= hi:
                raise ValueError(f'enemy_responses.{key}.{k}: integer {lo}..{hi} required')
        used.add(key); result.append(effective)
    return dict(version=value['version'], modules=result)


def initial():
    return dict(owner=None, prepared=None, called=False, unseen_since=None,
                cooldown_until=0, sequence=0, interest=None, recent=[], receipt_until=0)


def initialize(ai, config):
    ai.response_config = copy.deepcopy(config)
    ai.responses = initial() if config else None
    ai.response_trace = []


def module(ai, identifier):
    return next((m for m in (ai.response_config or {}).get('modules', []) if m['id'] == identifier), None)


def note(ai, engine, reason, **facts):
    ai.response_trace.append(dict(turn=engine.world_time.turn, reason=reason, **facts))
    ai.response_trace = ai.response_trace[-16:]


def finish(ai, actor, reason):
    """Release reported position; a displaced idle guard physically returns."""
    s = ai.responses
    if not s or s['interest'] is None:
        return
    s['interest'] = None
    if (ai.profile['recipe'] == 'territorial_guard' and ai.target is None
            and ai.territory['phase'] not in ('return', 'blocked')):
        ai.cancel(actor, 'alarm_' + reason)


def cancel(ai):
    if ai.responses:
        ai.responses['prepared'] = None
        ai.responses['interest'] = None


def refresh(ai, engine, actor, ambient):
    if not ai.responses:
        return
    from engine.local_rivals import owner, active, living, allocate
    from engine.effect_lifecycle import ability_enabled
    from engine.venom import fully_paralysed
    s = ai.responses; now = engine.world_time.turn
    if s['owner'] is None:
        allocate(engine, [actor]); s['owner'] = owner(engine)
    valid = active(engine, actor) and living(actor) and s['owner'] == owner(engine)
    if not valid:
        cancel(ai)
        return
    sight = ai.sees(engine, actor, engine.player, ambient)
    if ai.response_config['version'] == 2:
        from engine.enemy_components import windows
        flags = windows(ai, engine, actor)
        if s['prepared'] is not None and not flags['approach']:
            s['prepared'] = None
            note(ai, engine, flags['reason'], own_sight=sight)
        if s['interest'] and not flags['idle']:
            finish(ai, actor, 'host_priority')
    c = module(ai, CALL)
    if c:
        if sight:
            s['unseen_since'] = None
        else:
            if s['unseen_since'] is None:
                s['unseen_since'] = now
            if now >= s['cooldown_until'] and now - s['unseen_since'] >= c['rearm_unseen_phases']:
                s['called'] = False
        if s['prepared'] is not None and (not sight or not ability_enabled(actor, engine.local_map)
                or fully_paralysed(actor) or not actor.fighter.can_attack()):
            s['prepared'] = None
            note(ai, engine, 'preparation_cancelled', own_sight=sight)
    i = s['interest']
    if i:
        reason = ('incompatible_recipient' if not module(ai, ANSWER)
                  or actor.perception.faction != i['incident']['faction']
                  or not actor.perception.is_hostile_to('player') else
                  'expired' if now > i['deadline'] or i['incident']['owner'] != owner(engine) else None)
        if reason:
            finish(ai, actor, reason); note(ai, engine, reason)


def accepts(ai, actor, incident, engine):
    from engine.local_rivals import active, living, owner
    p = getattr(actor, 'perception', None); now = engine.world_time.turn
    if not module(ai, ANSWER): return 'no_response_module'
    if not active(engine, actor) or not living(actor): return 'inactive'
    if not p or p.faction != incident['faction'] or not p.is_hostile_to('player') or p.faction == 'player': return 'faction'
    if incident['owner'] != owner(engine) or incident['emitted'] != now: return 'foreign_or_expired'
    s = ai.responses
    if incident['id'] in s['recent']: return 'duplicate'
    if s['interest'] or now < s['receipt_until']: return 'response_busy'
    if ai.target is not None: return 'own_commitment'
    if ai.response_config['version'] == 2:
        from engine.enemy_components import windows
        flags = windows(ai, engine, actor)
        if not flags['idle']: return flags['reason']
        if ai.maneuvers and ai.maneuvers['current']: return 'maneuver_commitment'
    if ai.profile['recipe'] == 'territorial_guard':
        from components.territorial import distance
        t = ai.territory; anchor = t['anchor'] or [ai.home_x, ai.home_y]
        if t['phase'] != 'guard': return 'territorial_commitment'
        if distance(anchor, incident['x'], incident['y']) > ai.profile['defended_radius']: return 'outside_domain'
    return None


def emit(ai, engine, actor, config):
    from engine.local_rivals import owner, allocate
    from engine.sound import propagation, MAX_COST, REFERENCE_HEARING, clear_interest
    s = ai.responses; now = engine.world_time.turn
    s['sequence'] += 1
    incident = dict(id=f'{actor._individual_id}@{s["sequence"]}', source=actor._individual_id,
                    owner=owner(engine), faction=actor.perception.faction,
                    x=actor.x, y=actor.y, emitted=now)
    listeners = list(engine.get_active_entities())
    budgets = [config['strength'] + getattr(getattr(a, 'perception', None), 'hearing_radius', 0) - REFERENCE_HEARING for a in listeners]
    costs = propagation(engine.local_map, actor.x, actor.y, min(MAX_COST, max(budgets, default=0)))
    receipts = []
    for listener, budget in zip(listeners, budgets):
        if listener is actor: continue
        hearing = getattr(getattr(listener, 'perception', None), 'hearing_radius', 0)
        heard = hearing > 0 and costs.get((listener.x, listener.y), MAX_COST+1) <= budget
        if listener is engine.player:
            if heard and not engine.normal_player_vision()['visible'][actor.x,actor.y]:
                engine.log.add('A harsh cry rattles through the chamber.')
            continue
        other = getattr(listener, 'ai', None)
        if not getattr(other, 'response_config', None):
            receipts.append(dict(listener=getattr(listener,'_individual_id',None),reason='no_response_module' if heard else 'out_of_hearing'))
            continue
        reason = accepts(other, listener, incident, engine) if heard else 'out_of_hearing'
        if reason is None:
            allocate(engine, [listener])
            r = module(other, ANSWER); state = other.responses
            state['owner'] = owner(engine)
            state['interest'] = dict(incident=copy.deepcopy(incident), received=now,
                deadline=now+r['expiry_phases'], left=r['opportunity_budget'], failures=0)
            state['recent'] = (state['recent'] + [incident['id']])[-16:]
            state['receipt_until'] = now + RECEIPT_COOLDOWN
            clear_interest(other)
        note(other, engine, reason or 'accepted', incident=copy.deepcopy(incident), heard=heard)
        receipts.append(dict(listener=getattr(listener, '_individual_id', None), reason=reason or 'accepted'))
    ai._tell(engine, actor, 'lets out a harsh, rattling cry', current_vision=True)
    note(ai, engine, 'emitted', incident=incident, listeners=receipts[:16])


def choose(ai, engine, actor, observed, ambient, *, call=False, idle=False):
    """Return an ordinary paid choice, or None to run the selected core recipe."""
    if not ai.responses: return None
    from engine.effect_lifecycle import ability_enabled
    from engine.venom import fully_paralysed
    from engine.sound import clear_interest
    refresh(ai, engine, actor, ambient)
    s = ai.responses; now = engine.world_time.turn
    c = module(ai, CALL)
    own_sight = engine.player in observed
    if ai.target is not None:
        clear_interest(ai)
        if s['interest']:
            finish(ai, actor, 'own_priority'); note(ai, engine, 'own_priority', own_sight=own_sight)
    if not call or not own_sight:
        if s['prepared'] is not None:
            s['prepared'] = None; note(ai, engine, 'priority_cancelled', own_sight=own_sight)
    elif (c and not s['called'] and now >= s['cooldown_until']
          and ability_enabled(actor, engine.local_map) and not fully_paralysed(actor) and actor.fighter.can_attack()):
        if s['prepared'] is None:
            s['prepared'] = now
            ai._tell(engine, actor, 'draws itself upright, jaw trembling', current_vision=True)
            note(ai, engine, 'prepare', own_sight=True, used_action=True)
            return 'alarm_prepare', 'alarm_prepare', None
        if now > s['prepared']:
            s.update(prepared=None, called=True, cooldown_until=now+c['cooldown_phases'])
            emit(ai, engine, actor, c)
            return 'alarm_call', 'alarm_emitted', None
        # Speed two cannot spend the other opportunity emitting or attacking
        # while maintaining the tell in its preparation phase.
        return 'wait', 'alarm_windup', None
    if s['interest']:
        if observed or not idle:
            finish(ai, actor, 'own_priority'); note(ai, engine, 'own_priority', own_sight=own_sight)
            return None
        i = s['interest']; clear_interest(ai)
        if now <= i['incident']['emitted']:
            return 'wait', 'alarm_delivery_phase', None
        if not actor.fighter.can_move():
            return 'wait', 'alarm_movement_denied', None
        sx,sy = i['incident']['x'],i['incident']['y']; m = engine.local_map
        occupied = any(a is not actor and getattr(a,'blocks_movement',False) and (a.x,a.y)==(sx,sy) for a in engine.entities)
        blocked = occupied or not m.walkable[sx,sy] or engine._decor_blocks_movement(sx,sy)
        goal = (lambda x,y: abs(x-sx)+abs(y-sy)==1) if blocked else (lambda x,y: (x,y)==(sx,sy))
        step,length = ai._route(engine, actor, goal)
        i['left'] -= 1
        if ai.response_config['version'] == 2:
            from engine.enemy_components import move
            moved = move(ai, engine, actor, step)
        else:
            moved = ai._move(engine, actor, step)
        i['failures'] = 0 if moved else i['failures']+1
        reason = ('arrived' if length==0 or goal(actor.x,actor.y) else
                  'exhausted' if i['left']==0 else
                  'unreachable' if i['failures']>=module(ai,ANSWER)['failure_budget'] else 'investigating')
        if ai.response_config['version']==2:
            from engine.enemy_components import windows
            if not windows(ai,engine,actor)['idle']:
                reason = 'host_priority'
        note(ai,engine,reason,used_action=True,remaining=i['left'],origin=[sx,sy])
        if reason != 'investigating': finish(ai, actor, reason)
        return ('move' if moved else 'wait'), 'alarm_'+reason, None
    return None


def validate_saved(value, row, profile, local_map):
    """Strict separate attachment; historical base-state schemas stay exact."""
    from engine.local_rivals import OWNER, IDENTITY, TOKEN
    from config import MAP_WIDTH, MAP_HEIGHT
    if not isinstance(value, dict) or set(value) != {'config','state'}:
        raise ValueError('enemy_responses: saved config and state required')
    config = configuration(value['config'],profile,dict(faction=row.get('faction'),hostile_to=row.get('hostile_to')),complete=True)
    if config is None: raise ValueError('enemy_responses: saved null attachment')
    s = value['state']; modules = {r['id']:r for r in config['modules']}
    if not isinstance(s,dict) or set(s) != set(initial()): raise ValueError('enemy_responses: exact saved state required')
    def integer(v,lo=0,hi=2**63-1): return type(v) is int and lo<=v<=hi
    for k in ('cooldown_until','sequence','receipt_until'):
        if not integer(s[k],hi=10**16-1): raise ValueError('enemy_responses: invalid '+k)
    if type(s['called']) is not bool or any(s[k] is not None and not integer(s[k]) for k in ('prepared','unseen_since')):
        raise ValueError('enemy_responses: invalid sight episode')
    if s['owner'] is None:
        if s != initial(): raise ValueError('enemy_responses: unbound must be fresh')
    elif (not isinstance(s['owner'],str) or not OWNER.fullmatch(s['owner'])
          or not isinstance(row.get('individual_id'),str) or row['individual_id'].rsplit(':',1)[0] != s['owner']):
        raise ValueError('enemy_responses: foreign actor/scene')
    if (CALL not in modules and any(s[k] != initial()[k] for k in ('prepared','called','unseen_since','cooldown_until','sequence'))
        or s['prepared'] is not None and (s['called'] or row['composite']['state']['target'] is None
                                        or row['composite']['state']['target']['role'] != 'player'
                                        or row['composite']['state']['phase'] not in (
                                            ('approach',) if config['version']==1 else
                                            ('pursue',) if profile['recipe']=='observation_averse' else
                                            ('approach','return') if profile['recipe']!='patient_venom_hunt' else ('approach',))
                                        or profile['recipe']=='patient_venom_hunt' and row['composite']['state']['hunt'] is not None
                                        or s['prepared'] > row['composite']['state']['target']['seen']
                                        or s['prepared'] < s['cooldown_until'])
        or bool(s['sequence']) != bool(s['cooldown_until']) or s['called'] and not s['sequence']):
        raise ValueError('enemy_responses: inconsistent caller state')
    def incident_id(v):
        if not isinstance(v,str): return False
        match=INCIDENT.fullmatch(v)
        return bool(match and OWNER.fullmatch(match[1]) and IDENTITY.fullmatch(v.split('@')[0]) and int(match[3])>0 and match[1]==s['owner'])
    if (not isinstance(s['recent'],list) or len(s['recent'])>16
        or any(not incident_id(v) for v in s['recent']) or len(set(s['recent']))!=len(s['recent'])):
        raise ValueError('enemy_responses: invalid bounded incident ledger')
    if bool(s['recent']) != bool(s['receipt_until']):
        raise ValueError('enemy_responses: receipt cooldown requires accepted history')
    if ANSWER not in modules and (s['interest'] is not None or s['recent'] or s['receipt_until']):
        raise ValueError('enemy_responses: response state without module')
    i=s['interest']
    if config['version']==2 and profile['recipe']=='observation_averse':
        base=row['composite']['state']
        if (s['prepared'] is not None or i is not None) and base['phase']=='conceal':
            raise ValueError('enemy_responses: concealment has priority')
    if config['version']==2 and profile['recipe']=='patient_venom_hunt' and i is not None:
        base=row['composite']['state']
        if base['hunt'] is not None or base['suppressed'] is not None:
            raise ValueError('enemy_responses: retained or retired hunt has priority')
    if i is None: return
    if not isinstance(i,dict) or set(i)!={'incident','received','deadline','left','failures'}:
        raise ValueError('enemy_responses: incomplete investigation')
    event=i['incident']; w,h=(local_map.width,local_map.height) if local_map else (MAP_WIDTH,MAP_HEIGHT)
    r=modules[ANSWER]
    if (not isinstance(event,dict) or set(event)!={'id','source','owner','faction','x','y','emitted'}
        or not incident_id(event['id']) or event['id'] not in s['recent']
        or event['source'] != event['id'].split('@')[0] or event['source']==row.get('individual_id')
        or event['owner']!=s['owner'] or event['faction']!=row.get('faction') or not TOKEN.fullmatch(event['faction'])
        or not integer(event['x'],hi=w-1) or not integer(event['y'],hi=h-1) or not integer(event['emitted'])
        or not integer(i['received']) or i['received']!=event['emitted']
        or not integer(i['deadline']) or i['deadline']!=i['received']+r['expiry_phases']
        or not integer(i['left'],1,r['opportunity_budget']) or not integer(i['failures'],hi=r['failure_budget']-1)
        or s['receipt_until'] != i['received']+RECEIPT_COOLDOWN
        or row['composite']['state']['target'] is not None
        or row.get('component_state',{}).get('ai',{}).get('sound_interest') is not None):
        raise ValueError('enemy_responses: inconsistent reported-position evidence')
    if profile['recipe']=='territorial_guard':
        from components.territorial import distance
        t=row['composite']['state']['territory']
        if t['phase']!='guard' or distance(t['anchor'] or [row['home_x'],row['home_y']],event['x'],event['y'])>profile['defended_radius']:
            raise ValueError('enemy_responses: incompatible territorial investigation')
