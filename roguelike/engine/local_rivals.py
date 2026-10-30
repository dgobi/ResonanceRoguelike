"""One active-scene intent for ordinary mobile actors. No off-scene simulation.

Individual numbers are lazy, map-owned, monotonic, and independent of game RNG.
The saved reference is data, never an object or a definition/name lookup.
"""
from __future__ import annotations
import re

TOKEN = re.compile(r'[a-z][a-z0-9_]{0,31}\Z')
IDENTITY = re.compile(r'\d{1,10},\d{1,10}/[A-Za-z0-9_-]{0,100}:\d{8,16}\Z')
OWNER = re.compile(r'\d{1,10},\d{1,10}/[A-Za-z0-9_-]{0,100}\Z')


def supported(actor):
    from components.ai import WanderingAI
    from engine.creature_abilities import ABILITY_REGISTRY
    from engine.effect_lifecycle import creature_id
    return (type(getattr(actor, 'ai', None)) is WanderingAI
            and getattr(actor, 'perception', None) is not None
            and getattr(actor, 'fighter', None) is not None
            and creature_id(actor) not in ABILITY_REGISTRY)


def owner(engine):
    return f'{engine.world_x},{engine.world_y}/{engine.current_submap_id or ""}'


def living(actor):
    f = getattr(actor, 'fighter', None)
    return bool(getattr(actor, 'is_alive', False) and f and f.hp > 0 and not f.is_dead)


def active(engine, actor):
    return (any(a is actor for a in engine.entities)
            and not any(a is actor for a, *_ in engine._live_pursuers)
            and not any(r['entity'] is actor for r in engine._pending_pursuer_arrivals))


def visible(engine, *actors):
    m = engine.local_map
    return all(m.in_bounds(a.x, a.y) and m.visible[a.x, a.y] for a in actors)


def allocate(engine, actors):
    """Canonical first-allocation order; later list reorder/movement is irrelevant."""
    m = engine.local_map
    sequence = getattr(m, '_rival_identity_sequence', 0)
    used = {getattr(a, '_individual_id', None) for a in engine.entities}
    for a in sorted(actors, key=lambda a: (getattr(a, '_creature_id', ''),
                                           a.ai.home_x, a.ai.home_y, a.x, a.y)):
        if getattr(a, '_individual_id', None) is None:
            while True:
                sequence += 1
                identity = f'{owner(engine)}:{sequence:08d}'
                if identity not in used:
                    break
            a._individual_id = identity
            used.add(identity)
    m._rival_identity_sequence = sequence


def clear(actor):
    from components.ai import AIState
    ai = actor.ai
    ai.local_target = None
    if ai.state == AIState.RIVAL:
        ai.state = AIState.WANDERING
        ai.target_x = ai.target_y = None


def retire_player(actor):
    actor._last_known_px = actor._last_known_py = None
    actor._pending_stair_use = None
    ai = actor.ai
    ai.pursuit_turns_without_contact = ai.memory_turns = 0
    ai.target_x = ai.target_y = None


def eligible(engine, observer, candidate):
    if candidate is observer or not living(candidate) or not active(engine, candidate):
        return False
    p = getattr(observer, 'perception', None)
    if p is None:
        return False
    if candidate is engine.player:
        return p.is_hostile_to('player')
    cp = getattr(candidate, 'perception', None)
    return bool(supported(candidate) and cp and p.is_hostile_to(cp.faction))


def revalidate(engine, actor):
    """Lifecycle only; safe on F9/return/disrupted skips, never acquires or acts."""
    target = getattr(actor.ai, 'local_target', None)
    if target is None:
        return None
    if (not supported(actor) or not active(engine, actor)
            or target['owner'] != owner(engine)
            or engine.world_time.turn > target['deadline']):
        clear(actor)
        return None
    matches = [a for a in engine.entities
               if getattr(a, '_individual_id', None) == target['id']]
    if len(matches) != 1 or not eligible(engine, actor, matches[0]):
        clear(actor)
        return None
    return matches[0]


def take_turn(ai, actor, local_map, entities, player, log, rng, ambient_light, engine):
    """Return True when a rival intent spent this existing action opportunity."""
    from components.ai import AIState, _creature_can_see_player, _monster_attack_entity
    from engine.spatial import melee_attack_legal, terrain_conceals
    from engine.sound import clear_interest
    if (engine is None or player is not engine.player or local_map is not engine.local_map
            or not supported(actor) or not active(engine, actor)):
        return False
    p = actor.perception
    current = revalidate(engine, actor)
    observed = []
    for candidate in entities:
        if not eligible(engine, actor, candidate):
            continue
        # Same occupied-terrain concealment rule as the physical player. No
        # presentation mask, sound maker, or hidden registry coordinates identify it.
        if candidate is not player:
            concealed = terrain_conceals(candidate, local_map, engine.data.terrain)
            if concealed:
                sight = p.sight_radius + (engine.weather.get_mechanic('creature_alert_radius_bonus', 0)
                                          if engine.weather else 0)
                if (candidate.x-actor.x)**2+(candidate.y-actor.y)**2 > max(1, sight-2)**2:
                    continue
        if _creature_can_see_player(actor, candidate, local_map, ambient_light, engine=engine):
            observed.append(candidate)
    if any(a is not player for a in observed):
        allocate(engine, [actor] + [a for a in observed if a is not player])
    def order(a):
        return ((a.x-actor.x)**2+(a.y-actor.y)**2,
                '' if a is player else a._individual_id)
    observed.sort(key=order)
    # Existing player intent is explicit in its established pursuit state/trail.
    selected = current
    if selected is None and (getattr(actor, '_last_known_px', None) is not None
                            and p.is_hostile_to('player')):
        selected = player
    if selected not in observed:
        selected = observed[0] if observed else selected
    if selected in observed and not melee_attack_legal(local_map, actor, selected):
        contacts = [a for a in observed if melee_attack_legal(local_map, actor, a)]
        if contacts:
            selected = contacts[0]
    if selected is player:
        clear(actor)
        return False  # Preserve established player memory/transfer timing.
    if selected is None:
        if not p.is_hostile_to('player'):
            retire_player(actor)
            if ai.state in (AIState.HUNTING, AIState.ALERTED, AIState.ATTACKING):
                ai.state = AIState.WANDERING
        return False
    old = getattr(ai, 'local_target', None)
    if selected in observed:
        changed = old is None or old['id'] != selected._individual_id
        ai.local_target = dict(id=selected._individual_id, owner=owner(engine),
                               x=selected.x, y=selected.y,
                               deadline=engine.world_time.turn + ai.alert_memory)
        if changed and visible(engine, actor, selected):
            from engine.palette import UI_TEXT_DIM
            log.add(f'The {actor.name} turns on the {selected.name}.', UI_TEXT_DIM)
    trail = ai.local_target
    retire_player(actor)
    clear_interest(ai)
    ai.state = AIState.RIVAL
    if selected not in observed and (actor.x, actor.y) == (trail['x'], trail['y']):
        clear(actor)
        return True
    if selected in observed and melee_attack_legal(local_map, actor, selected):
        _monster_attack_entity(actor, selected, engine)
    else:
        ai._move_toward(actor, local_map, entities, trail['x'], trail['y'],
                        player=selected if selected in observed else None,
                        terrain_data=engine.data.terrain, engine=engine)
    return True


def validate_row(row, local_map=None):
    identity = row.get('individual_id')
    target = row.get('local_target')
    if identity is not None and (not isinstance(identity, str) or not IDENTITY.fullmatch(identity)):
        raise ValueError('Invalid individual_id')
    if target is None:
        if row.get('ai_state') == 'rival':
            raise ValueError('Rival state requires local_target')
        return
    from config import MAP_WIDTH, MAP_HEIGHT
    from engine.creature_abilities import ABILITY_REGISTRY
    w, h = (local_map.width, local_map.height) if local_map else (MAP_WIDTH, MAP_HEIGHT)
    if (not isinstance(target, dict) or set(target) != {'id','owner','x','y','deadline'}
            or identity is None or row.get('ai_state') != 'rival'
            or row.get('ai_type') != 'WanderingAI'
            or row.get('id') in ABILITY_REGISTRY
            or not isinstance(target['id'], str) or not IDENTITY.fullmatch(target['id'])
            or target['id'] == identity
            or not isinstance(target['owner'], str) or not OWNER.fullmatch(target['owner'])
            or type(target['x']) is not int or not 0 <= target['x'] < w
            or type(target['y']) is not int or not 0 <= target['y'] < h
            or type(target['deadline']) is not int or not 0 <= target['deadline'] < 2**63):
        raise ValueError('Invalid local_target')
    state = row.get('component_state', {})
    a, ai = state.get('actor', {}), state.get('ai', {})
    if (a.get('_last_known_px') is not None or a.get('_last_known_py') is not None
            or a.get('_pending_stair_use') is not None or ai.get('sound_interest') is not None
            or ai.get('target_x') is not None or ai.get('target_y') is not None
            or ai.get('memory_turns', 0) != 0 or row.get('pursuit_turns_without_contact', 0) != 0):
        raise ValueError('Conflicting rival intent')
