"""Combat effect ownership and explicit turn/contact boundaries.

Player durations include the consuming action (the existing timer convention).
Actor effects cover the next N simulated world turns; they age after AI, once per
live instance. Cold scene records do not simulate. Zone clocks follow hot maps.
"""
from __future__ import annotations
from engine.palette import MSG_DEFAULT, UI_TEXT_DIM, RESONANCE_MID, STONE_BLUE


def creature_id(actor):
    return getattr(actor, '_creature_id', actor.tile)


def in_disruption_zone(actor, local_map):
    return any(z['turns_remaining'] > 0 and
               (actor.x-z['x'])**2 + (actor.y-z['y'])**2 <= z['radius']**2
               for z in getattr(local_map, 'disruption_zones', []))


def disrupted(actor, local_map):
    return getattr(actor, '_disrupted_turns', 0) > 0 or in_disruption_zone(actor, local_map)


def ability_enabled(actor, local_map):
    return (getattr(actor, 'is_alive', True)
            and getattr(actor, '_ability_suppressed_turns', 0) <= 0
            and not disrupted(actor, local_map))


def knight_disruption(engine):
    """Aggregate all current sources; a far/dead/suppressed knight cannot clear another."""
    p = engine.player
    active = any(creature_id(a) == 'hollow_knight' and ability_enabled(a, engine.local_map)
                 and (a.x-p.x)**2+(a.y-p.y)**2 <= 25
                 for a in engine.entities if a is not p)
    p._hollow_knight_disruption = active
    return active


def live_actors(engine):
    rows = list(engine.entities) + [r[0] for r in engine._live_pursuers]
    rows += [r['entity'] for r in engine._pending_pursuer_arrivals]
    return list({id(a):a for a in rows if a is not engine.player}.values())


def refresh_wraith_aura(engine, *, advance=False):
    """Derive the active aura from durable per-source exposure.

    Only a simulated turn increments exposure. FOV refresh and restoration may
    rebind fresh actor objects or remove an ineligible source without spending
    a turn, restarting its drain, or replaying the first-exposure message.
    """
    active_ids = {id(a) for a in engine.entities if a is not engine.player}
    ability_range = engine.data.entities.get('bog_wraith', {}).get('ability_range', 8)
    px, py = engine.player.x, engine.player.y
    active = {}
    for actor in live_actors(engine):
        if creature_id(actor) != 'bog_wraith':
            continue
        eligible = (id(actor) in active_ids and ability_enabled(actor, engine.local_map)
                    and abs(actor.x - px) + abs(actor.y - py) <= ability_range)
        if not eligible:
            actor._wraith_exposure_turns = 0
            continue
        turns = getattr(actor, '_wraith_exposure_turns', 0)
        if advance:
            turns += 1
            actor._wraith_exposure_turns = turns
            if turns == 1:
                engine.callouts.add('Sight dims.', float(px), float(py) - 1.0,
                                    STONE_BLUE, lifetime=1.2, font_size='status')
                engine.log.add('Sight dims.', STONE_BLUE)
        if turns > 0:
            active[id(actor)] = turns
    engine._wraith_aura_state = active
    return active


def reset_wraith_aura(engine):
    """Leaving a scene ends exposure before its actors are cached."""
    for actor in live_actors(engine):
        if creature_id(actor) == 'bog_wraith':
            actor._wraith_exposure_turns = 0
    engine._wraith_aura_state = {}


def age_actor(engine, actor):
    """Age before serialization when a live owner retires during this turn."""
    aged = getattr(engine, '_effect_aged_ids', None)
    if aged is None or id(actor) in aged:
        return
    aged.add(id(actor))
    for field in ('_ability_suppressed_turns', '_disrupted_turns'):
        count = getattr(actor, field, 0)
        if count > 0:
            setattr(actor, field, count - 1)


def finish_turn(engine, actors):
    # Include departed owners, newly promoted owners and aliases exactly once.
    for a in {id(a):a for a in actors + live_actors(engine)}.values():
        age_actor(engine, a)
    engine._effect_aged_ids = None
    maps = [engine.local_map]
    cache = engine.save_manager.cache
    maps += [c.local_map for c in list(cache.hot.values()) + list(cache.submap_hot.values())]
    for m in {id(m):m for m in maps}.values():
        zones = getattr(m, 'disruption_zones', [])
        for z in zones:
            z['turns_remaining'] -= 1
        m.disruption_zones = [z for z in zones if z['turns_remaining'] > 0]
    knight_disruption(engine)


def armor_contact(engine, result):
    """The last charge protects this hit; dodge/invincibility spend no charge."""
    if not result.hit or result.dodged:
        return
    torso = engine.player.equipment.slots.get('armor_torso')
    if torso is not None and getattr(torso, '_temp_av_hits', 0) > 0:
        torso._temp_av_hits -= 1
        if torso._temp_av_hits == 0:
            torso._temp_av_bonus = 0
            from engine.item_system import _recompute_effective_av
            _recompute_effective_av(engine.player, engine.data)
            engine.log.add('The marrow seal wears away.', UI_TEXT_DIM)


def coated_weapon(weapon, item):
    """Build an attack snapshot without mutating the shared definition."""
    active = [r for r in getattr(item, 'temporary_essence', []) if r.get('hits_remaining',0)>0]
    if not active:
        return weapon
    result = dict(weapon or {})
    base = list(result.get('essences', []))
    if not base and result.get('essence'):
        base = [{'name':result['essence'], 'strength':result.get('essence_strength',0)}]
    result['essences'] = base + [{'name':r['essence'], 'strength':r['strength']} for r in active]
    result.pop('essence', None);result.pop('essence_strength', None)
    return result


def coating_contact(engine, item, result):
    if item is None or not result.hit or result.dodged:
        return
    rows = getattr(item, 'temporary_essence', [])
    if not rows:
        return
    for row in rows:
        row['hits_remaining'] = max(0, row.get('hits_remaining',0)-1)
    item.temporary_essence = [r for r in rows if r['hits_remaining']>0]
    if not item.temporary_essence:
        engine.log.add('The coating has worn off the blade.', UI_TEXT_DIM)
        if getattr(engine.display, 'CALLOUT_STATUS_EFFECTS', False):
            engine.callouts.add('coating gone',float(engine.player.x),float(engine.player.y),UI_TEXT_DIM,font_size='status')


def confirm_consume(engine, key):
    import pygame
    pending = engine._pending_consume
    if key not in (pygame.K_y, pygame.K_n, pygame.K_ESCAPE):
        return
    engine._pending_consume = None
    if key != pygame.K_y:
        engine.log.add('You decide against it.', MSG_DEFAULT)
        return
    item = pending['item']
    from engine.item_transfers import consume
    if not engine.player.inventory.contains(item) or item.on_use != 'consume_wight_concentrate':
        engine.log.add('The preparation is no longer here.', MSG_DEFAULT)
        return
    definition = pending['item_def']
    consume(engine, item)
    engine.resonance_exposure = min(1.0, engine.resonance_exposure + definition.get('resonance_add',.4))
    engine.player.corruption.value = min(1.0, engine.player.corruption.value + definition.get('corruption_add',.05))
    engine.true_sight_turns = max(engine.true_sight_turns, definition.get('true_sight_turns',20))
    engine.player.true_sight = engine.true_sight_turns > 0
    engine.log.add(definition.get('use_message','Something opens in you.'), RESONANCE_MID)
    engine._advance_turn()


def valid_throw(engine, x, y):
    pending = engine._pending_throw
    if not pending or pending['map'] is not engine.local_map:
        return False
    if not engine.player.inventory.contains(pending['item']):
        return False
    m, p = engine.local_map, engine.player
    reach = pending['item_def'].get('throw_range',6)
    if (not m.in_bounds(x,y) or not m.walkable[x,y] or not m.visible[x,y]
            or (x-p.x)**2+(y-p.y)**2 > reach**2):
        return False
    from tcod.los import bresenham
    from engine.spatial import melee_contact
    ray = bresenham((p.x,p.y),(x,y)).tolist()
    return all(m.transparent[tx,ty] for tx,ty in ray[1:]) and all(
        melee_contact(m,*a,*b) for a,b in zip(ray,ray[1:]))


def throw_key(engine, key):
    import pygame
    from engine.engine import MOVE_KEYS, GameMode
    pending = engine._pending_throw
    if key in MOVE_KEYS:
        dx,dy = MOVE_KEYS[key]
        m=engine.local_map
        engine._placement_cursor_x = max(0,min(m.width-1,engine._placement_cursor_x+dx))
        engine._placement_cursor_y = max(0,min(m.height-1,engine._placement_cursor_y+dy))
        return
    if key == pygame.K_ESCAPE:
        engine._pending_throw = None
        engine._placement_mode = 'campfire'
        engine.mode = GameMode.LOCAL
        engine.log.add('You keep the pellet.', MSG_DEFAULT)
        return
    if key not in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return
    x,y=engine._placement_cursor_x,engine._placement_cursor_y
    if not valid_throw(engine,x,y):
        engine.log.add('You cannot throw there.', MSG_DEFAULT)
        return
    from engine.item_transfers import consume
    if not consume(engine,pending['item']):
        return
    definition=pending['item_def']
    m=engine.local_map
    m.disruption_zones = list(getattr(m,'disruption_zones',[])) + [dict(
        x=x,y=y,radius=definition.get('zone_radius',3),turns_remaining=definition.get('zone_turns',6))]
    engine._pending_throw = None
    engine._placement_mode = 'campfire'
    engine.mode = GameMode.LOCAL
    engine.log.add(definition.get('use_message','The pellet shatters.'), MSG_DEFAULT)
    engine._emit_placement_burst(x,y)
    engine._advance_turn()
