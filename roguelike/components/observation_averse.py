"""Registered v2 policy, using CompositeAI's perception, routes and melee authority.

Observation is a narrow supernatural exposure sense. It does not identify prey.
All counters spend ordinary opportunities; markers use charged world phases.
"""
from __future__ import annotations
import copy
import hashlib
import json
from dataclasses import asdict

FIELDS = ('phase', 'target', 'cover_goal', 'conceal_left', 'pursuit_left',
          'no_progress', 'best_distance', 'failed_entries', 'environment', 'context_origin',
          'evidence_key', 'retired_evidence', 'blocked_cover', 'bonus_phase',
          'reaction_phase', 'covered_phase', 'opportunities')


def initialize(ai):
    ai.phase, ai.target, ai.cover_goal = 'idle', None, None
    ai.conceal_left = ai.profile['concealment_budget']
    ai.pursuit_left = ai.profile['pursuit_budget']
    ai.no_progress, ai.best_distance = 0, None
    ai.failed_entries = []
    ai.environment = ai.evidence_key = ai.retired_evidence = None
    ai.context_origin = None
    ai.blocked_cover = False
    ai.bonus_phase = ai.reaction_phase = ai.covered_phase = None
    ai.per_step_reactions = True


def snapshot(ai):
    return dict(profile=copy.deepcopy(ai.profile),
                state={k: copy.deepcopy(getattr(ai, k)) for k in FIELDS})


def validate_state(s, p, local_map):
    from config import MAP_WIDTH, MAP_HEIGHT
    w, h = (local_map.width, local_map.height) if local_map else (MAP_WIDTH, MAP_HEIGHT)
    def cell(v):
        return (isinstance(v, list) and len(v) == 2 and type(v[0]) is int
                and type(v[1]) is int and 0 <= v[0] < w and 0 <= v[1] < h)
    def fail(message):
        raise ValueError('composite.state: ' + message)
    if not isinstance(s, dict) or set(s) != set(FIELDS):
        fail('complete observation-averse state required')
    if s['phase'] not in ('idle', 'conceal', 'covered', 'pursue', 'cower'):
        fail('unsupported observation phase')
    if s['cover_goal'] is not None and not cell(s['cover_goal']):
        fail('invalid cover destination')
    if s['context_origin'] is not None and not cell(s['context_origin']):
        fail('invalid exposure context origin')
    if (s['phase'] in ('conceal', 'covered') and s['cover_goal'] is None
            or s['phase'] == 'conceal' and s['conceal_left'] == 0
            or s['phase'] == 'pursue' and s['target'] is None):
        fail('phase requires its commitment')
    for k, hi in (('conceal_left', p['concealment_budget']),
                  ('pursuit_left', p['pursuit_budget']), ('no_progress', 8),
                  ('opportunities', 2**63-1)):
        if type(s[k]) is not int or not 0 <= s[k] <= hi:
            fail('invalid bounded counter ' + k)
    for k in ('bonus_phase', 'reaction_phase', 'covered_phase', 'best_distance'):
        if s[k] is not None and (type(s[k]) is not int or not 0 <= s[k] < 2**63):
            fail('invalid phase/progress marker ' + k)
    if (not isinstance(s['failed_entries'], list) or len(s['failed_entries']) > 8
            or not all(cell(v) for v in s['failed_entries'])
            or len({tuple(v) for v in s['failed_entries']}) != len(s['failed_entries'])):
        fail('invalid bounded failed entries')
    for k in ('environment', 'evidence_key', 'retired_evidence'):
        v = s[k]
        if v is not None and (not isinstance(v, str) or len(v) != 64
                              or any(c not in '0123456789abcdef' for c in v)):
            fail('invalid rearm fingerprint ' + k)
    if type(s['blocked_cover']) is not bool:
        fail('invalid cover rearm state')


def evidence_key(t):
    if t is None:
        return None
    # Sight at the same point cannot renew a failed encounter's patience.
    return hashlib.sha256(json.dumps([t[k] for k in ('role', 'id', 'owner', 'x', 'y')]).encode()).hexdigest()


def retire_prey(ai, actor, reason, *, keep_sound=False):
    from engine.enemy_maneuvers import cancel
    cancel(ai)
    from engine.enemy_responses import cancel
    cancel(ai)
    from engine.local_rivals import retire_player
    from engine.sound import clear_interest
    ai.retired_evidence = evidence_key(ai.target) or ai.retired_evidence
    ai.target = None
    ai.local_target = None
    retire_player(actor)
    if not keep_sound:
        clear_interest(ai)
    if ai.phase == 'pursue':
        ai.phase = 'idle'
    ai.last_cancellation = reason


def environment_key(engine, mask, origin):
    """Exposure/geometry only, independent of own position and hidden prey.

    No clock, explored bit, actor identity, target timestamp or camera state.
    Current occupancy is rechecked by routes, not a source of prey information.
    """
    m = engine.local_map
    x, y = origin
    area = (slice(max(0,x-16),min(m.width,x+17)), slice(max(0,y-16),min(m.height,y+17)))
    digest = hashlib.sha256(mask[area].tobytes())
    digest.update(m.walkable[area].tobytes())
    digest.update(m.transparent[area].tobytes())
    digest.update(m.tiles['terrain'][area].tobytes())
    return digest.hexdigest()


def ready(engine, actor):
    from engine.effect_lifecycle import disrupted
    from engine.local_rivals import active, living
    return (active(engine, actor) and living(actor) and engine.player.is_alive
            and not disrupted(actor, engine.local_map) and actor.fighter.can_move())


def step(ai, engine, actor, destination):
    old = actor.x, actor.y
    moved = ready(engine, actor) and ai._move(engine, actor, destination)
    reaction = False
    if moved and ai.reaction_phase != engine.world_time.turn:
        reaction = engine._grass_concealment_reaction(actor, old)
        if reaction:
            ai.reaction_phase = engine.world_time.turn
    mask = engine.normal_player_vision()['visible']
    watched = bool(mask[actor.x, actor.y])
    # Validate after consequences; no hidden position refresh occurs here.
    ai.resolve_target(engine, actor)
    return dict(from_cell=list(old), to_cell=[actor.x, actor.y], moved=bool(moved),
                observed=watched, reaction=bool(reaction), ready=bool(ready(engine, actor)))


def route_to_cover(ai, engine, actor, mask):
    if ai.cover_goal is not None:
        goal = tuple(ai.cover_goal)
        if not mask[goal]:
            nxt, length = ai._route(engine, actor, lambda x,y: (x,y) == goal)
            if length is not None:
                return nxt, goal
        ai.cover_goal = None
    destination = None
    def hidden(x, y):
        nonlocal destination
        if not mask[x, y]:
            destination = (x, y)
            return True
        return False
    nxt, length = ai._route(engine, actor, hidden)
    if length is not None:
        ai.cover_goal = list(destination)
    return nxt, destination


def fallback(ai, engine, actor, perceived, target):
    from engine.spatial import melee_attack_legal
    from components.ai import _monster_attack_result
    ai.phase, ai.cover_goal = 'cower', None
    if ai.profile['no_cover'] == 'defensive_melee':
        contacts = [a for a in perceived if melee_attack_legal(engine.local_map, actor, a)]
        defender = target if target in contacts else (contacts[0] if contacts else None)
        if defender is not None:
            return 'melee', 'no_cover_defensive', _monster_attack_result(actor, defender, engine, defensive=True)
    return 'wait', 'no_legal_cover' if ai.blocked_cover else 'concealment_exhausted', None


def take_turn(ai, actor, engine, ambient):
    from engine.local_rivals import active
    from engine.effect_lifecycle import disrupted, ability_enabled
    from engine.sound import clear_interest, current_interest, investigate
    from components.ai import AIState, _monster_attack_result
    from engine.spatial import melee_contact, melee_attack_legal
    from engine.venom import movement_denial
    if not active(engine, actor) or not actor.is_alive or disrupted(actor, engine.local_map):
        return
    ai.opportunities += 1
    now, before = engine.world_time.turn, ai.phase
    action, reason, result, steps = 'wait', 'no_prey', None, []
    mask = engine.normal_player_vision()['visible']
    watched = bool(mask[actor.x, actor.y])
    if ai.context_origin is None:
        ai.context_origin = [actor.x, actor.y]
    context = environment_key(engine, mask, ai.context_origin)
    if context != ai.environment:
        ai.environment = context
        ai.conceal_left = ai.profile['concealment_budget']
        ai.pursuit_left = ai.profile['pursuit_budget']
        ai.no_progress, ai.best_distance = 0, None
        ai.failed_entries, ai.retired_evidence = [], None
        # A material change rearms patience, not a still-useful destination.
        # route_to_cover alone invalidates the commitment against fresh legality.
        ai.blocked_cover = False
    perceived = ai._observed(engine, actor, ambient)
    target = ai.resolve_target(engine, actor)
    if target in perceived:
        ai._remember(engine, target)
    if ai.target is not None and now > ai.target['deadline']:
        retire_prey(ai, actor, 'evidence_expired', keep_sound=True)
        target, reason = None, 'trail_expired'
    if ai.target is None:
        for candidate in perceived:
            ai._remember(engine, candidate)
            if evidence_key(ai.target) != ai.retired_evidence:
                target = candidate
                break
            ai.target = None
    key = evidence_key(ai.target)
    if key is not None and key != ai.evidence_key:
        ai.evidence_key = key
        ai.context_origin = [actor.x, actor.y]
        ai.environment = environment_key(engine, mask, ai.context_origin)
        ai.pursuit_left = ai.profile['pursuit_budget']
        ai.no_progress, ai.best_distance, ai.failed_entries = 0, None, []
    if ai.target is not None:
        clear_interest(ai)
    from engine.enemy_components import choose, windows
    flags = windows(ai, engine, actor)
    if flags['approach']:
        ai.phase = 'pursue'
    reaction = choose(ai, engine, actor, perceived, ambient)
    # Reaching cover commits the remainder of this charged phase, including fast AI.
    if reaction:
        # The adapter may have entered concealment after its single safe step.
        # That is next opportunity's obligation, never another move this time.
        action, reason, result = reaction
        steps.extend(ai.attachment_steps)
    elif not watched and ai.covered_phase == now:
        reason = 'covered_this_phase'
    elif watched or ai.phase == 'conceal':
        nxt, goal = route_to_cover(ai, engine, actor, mask)
        useful = goal is not None
        if ai.blocked_cover and useful and ready(engine, actor):
            # Newly legal cover after an actual blocked fallback, never own toggling.
            ai.conceal_left = ai.profile['concealment_budget']
            ai.blocked_cover = False
        if useful and ai.conceal_left > 0:
            if ai.phase != 'conceal' and watched:
                ai._tell(engine, actor, 'shudders in the light', current_vision=True)
            ai.phase = 'conceal'
            if goal == (actor.x, actor.y):
                ai.phase, ai.covered_phase = 'covered', now
                reason = 'cover_reached'
            elif movement_denial(actor):
                action, reason = 'wait', movement_denial(actor)
            else:
                ai.conceal_left -= 1
                outcome = step(ai, engine, actor, nxt)
                steps.append(outcome)
                action, reason = ('move' if outcome['moved'] else 'wait'), 'seek_concealment'
                if (actor.x, actor.y) == goal and not outcome['observed']:
                    ai.phase, ai.covered_phase = 'covered', now
                elif ai.conceal_left == 0:
                    ai.phase, ai.cover_goal, reason = 'cower', None, 'concealment_exhausted'
        else:
            ai.blocked_cover = not useful
            action, reason, result = fallback(ai, engine, actor, perceived, target)
    elif ai.target is not None:
        ai.phase = 'pursue'
        tx, ty = ai.target['x'], ai.target['y']
        if target in perceived and melee_attack_legal(engine.local_map, actor, target):
            result = _monster_attack_result(actor, target, engine)
            action, reason = 'melee', 'unseen_melee'
        elif (actor.x, actor.y) == (tx, ty):
            retire_prey(ai, actor, 'empty_trail')
            reason = 'empty_trail'
        elif movement_denial(actor):
            action, reason = 'wait', movement_denial(actor)
        else:
            exhausted = ai.pursuit_left == 0
            ai.pursuit_left = max(0, ai.pursuit_left-1)
            def pursuit_route():
                # A remembered cell can still be occupied. Route to legal contact
                # with that fixed evidence point, never through its occupant and
                # never toward the retained instance's hidden live coordinates.
                occupied_evidence = any(a is not actor and getattr(a, 'blocks_movement', False)
                    and (a.x,a.y)==(tx,ty) for a in engine.entities)
                goal = ((lambda x,y: melee_contact(engine.local_map,x,y,tx,ty))
                        if target in perceived or occupied_evidence else (lambda x,y: (x,y)==(tx,ty)))
                return ai._route(engine, actor, goal, forbidden={tuple(v) for v in ai.failed_entries})
            nxt, length = pursuit_route()
            progress = length is not None and (ai.best_distance is None or length < ai.best_distance)
            ai.no_progress = 0 if progress else min(8, ai.no_progress+1)
            if length is not None:
                ai.best_distance = length
            if exhausted or ai.no_progress >= 8 or len(ai.failed_entries) >= 8:
                retire_prey(ai, actor, 'pursuit_exhausted')
                reason = 'pursuit_exhausted'
            else:
                first = step(ai, engine, actor, nxt)
                steps.append(first)
                action, reason = ('move' if first['moved'] else 'wait'), 'unseen_pursuit'
                if first['moved'] and first['observed']:
                    if [actor.x, actor.y] not in ai.failed_entries:
                        ai.failed_entries.append([actor.x, actor.y])
                    ai.phase, reason = 'conceal', 'watched'
                    # A goal is selected next opportunity, without granting an action.
                    route_to_cover(ai, engine, actor, engine.normal_player_vision()['visible'])
                    if ai.cover_goal is None or ai.conceal_left == 0:
                        ai.phase = 'cower'
                elif first['reaction'] or not first['ready']:
                    reason = 'movement_interrupted'
                elif (first['moved'] and ai.target is not None and now <= ai.target['deadline']
                      and ai.profile['unseen_extra_step'] and ai.bonus_phase != now
                      and ability_enabled(actor, engine.local_map)):
                    # Movement-only continuation: reaching contact cannot select melee.
                    nxt, _ = pursuit_route()
                    if nxt is not None:
                        ai.bonus_phase = now
                        extra = step(ai, engine, actor, nxt)
                        steps.append(extra)
                        if extra['observed']:
                            if [actor.x, actor.y] not in ai.failed_entries:
                                ai.failed_entries.append([actor.x, actor.y])
                            ai.phase, reason = 'conceal', 'watched'
                            route_to_cover(ai, engine, actor, engine.normal_player_vision()['visible'])
                            if ai.cover_goal is None or ai.conceal_left == 0:
                                ai.phase = 'cower'
                        elif extra['reaction'] or not extra['ready']:
                            reason = 'movement_interrupted'
    else:
        ai.phase = 'covered' if ai.cover_goal and not watched else 'idle'
        interest = current_interest(ai, now)
        if interest and not watched:
            ai.state = AIState.INVESTIGATING
            old = actor.x, actor.y
            investigate(ai, actor, engine.local_map, engine.entities)
            if (actor.x, actor.y) != old:
                reaction = ai.reaction_phase != now and engine._grass_concealment_reaction(actor, old)
                if reaction:
                    ai.reaction_phase = now
                exposed = bool(engine.normal_player_vision()['visible'][actor.x, actor.y])
                steps.append(dict(from_cell=list(old), to_cell=[actor.x, actor.y], moved=True,
                                  observed=exposed, reaction=bool(reaction), ready=ready(engine, actor)))
            action, reason = 'investigate', 'anonymous_sound'
    if result and result.target_dead:
        ai.resolve_target(engine, actor)
    from engine.enemy_maneuvers import reconcile_position
    reconcile_position(ai, engine, actor)
    ai.trace.append(dict(opportunity=ai.opportunities, turn=now, phase_before=before,
        phase=ai.phase, observed=watched, observation_reason='normal_player_vision',
        action=action, reason=reason, result=asdict(result) if result else None,
        steps=steps, bonus_consumed=ai.bonus_phase == now,
        bonus_eligible=bool(not watched and ai.target is not None and ai.profile['unseen_extra_step']
                            and ai.bonus_phase != now and ability_enabled(actor, engine.local_map))))
    ai.trace = ai.trace[-16:]
