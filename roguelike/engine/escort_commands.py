"""Narrow physical command and passage affordances for registered local escorts."""
from __future__ import annotations
from engine.local_rivals import active, living, owner
from engine.spatial import melee_contact


def registered(actor):
    from engine.ai_profiles import local_only
    p = getattr(actor,'perception',None)
    return bool(local_only(actor) and actor.ai.profile['recipe']=='protective_escort'
                and p and p.faction=='player' and 'player' not in (p.hostile_to or []))


def owned(engine, actor):
    return (registered(actor) and living(actor) and active(engine,actor)
            and actor.ai.escort['owner'] in (None,owner(engine)))


def reachable(engine, actor):
    from engine.interaction_cursor import InteractionCursor
    return (owned(engine,actor) and (actor.x,actor.y)!=(engine.player.x,engine.player.y)
            and InteractionCursor.can_reach(engine,actor.x,actor.y)
            and bool(engine.normal_player_vision()['visible'][actor.x,actor.y])
            and not engine._decor_blocks_movement(actor.x,actor.y))


def at(engine,x,y):
    actors = [a for a in engine.entities if (a.x,a.y)==(x,y) and reachable(engine,a)]
    return actors[0] if len(actors)==1 else None


def offer(cursor,engine):
    a=at(engine,cursor.cursor_x,cursor.cursor_y)
    if a is None:
        return False
    import copy
    cursor._order_prompt=dict(actor=a,scene=engine.local_map,owner=owner(engine),
        player_position=(engine.player.x,engine.player.y),
        position=(a.x,a.y),identity=getattr(a,'_individual_id',None),
        order=a.ai.escort['order'],post=copy.deepcopy(a.ai.escort['post']),selected=0)
    return True


def confirm(cursor,engine):
    from engine.venom import fully_paralysed
    from components.protective_escort import set_order
    from engine.engine import GameMode
    from engine.palette import MSG_DEFAULT
    p=cursor._order_prompt
    cursor._order_prompt=None
    a=p['actor']
    if (fully_paralysed(engine.player) or not living(engine.player)
            or engine.local_map is not p['scene'] or owner(engine)!=p['owner']
            or (engine.player.x,engine.player.y)!=p['player_position']
            or (a.x,a.y)!=p['position'] or getattr(a,'_individual_id',None)!=p['identity']
            or not reachable(engine,a)
            or a.ai.escort['order']!=p['order'] or a.ai.escort['post']!=p['post']
            ):
        engine.log.add('That order cannot be given here.',MSG_DEFAULT)
        return False
    order=('follow','hold')[p['selected']]
    set_order(a.ai,a,engine,order)
    engine.log.add(f'The {a.name} will follow.' if order=='follow' else f'The {a.name} will hold here.',MSG_DEFAULT)
    engine._free_move_pending=False
    engine._log_scroll=0
    engine._advance_turn()  # Exactly one scheduler phase, never an extra AI call.
    engine.mode=GameMode.LOCAL
    return True


def physical(engine,actor,start,end,ignore=()):
    if not melee_contact(engine.local_map,*start,*end) or engine._decor_blocks_movement(*end):
        return False
    dx,dy=end[0]-start[0],end[1]-start[1]
    if dx and dy and all(not engine.local_map.walkable[x,y] or engine._decor_blocks_movement(x,y)
                         for x,y in ((end[0],start[1]),(start[0],end[1]))):
        return False
    if any(a is not actor and all(a is not b for b in ignore) and getattr(a,'blocks_movement',False)
           and (a.x,a.y)==end for a in engine.entities):
        return False
    if actor is not engine.player:
        raw=engine.data.entities.get(actor._creature_id,{})
        tid=str(engine.local_map.tiles[end]['terrain'])
        if not engine.data.terrain.get(tid,{}).get('creature_passable',True) and not raw.get('can_swim',False):
            return False
    return True


def yield_to_player(engine,actor):
    """Atomic two-actor legality before commitment; player entry uses normal effects.

    Creature entry uses the same capability/terrain contract as ordinary AI;
    ordinary creatures currently have no player-only tile-entered hooks.
    """
    from engine.effect_lifecycle import disrupted
    from engine.venom import movement_denial
    from engine.palette import MSG_DEFAULT
    player=engine.player; a=(actor.x,actor.y); p=(player.x,player.y)
    if (not owned(engine,actor) or not living(player) or engine._movement_denied()
            or not actor.fighter.can_move() or movement_denial(actor) or disrupted(actor,engine.local_map)
            or not physical(engine,player,p,a,ignore=(actor,))):
        engine.log.add('There is no room to pass.',MSG_DEFAULT)
        return False
    candidates=sorted([(a[0]+dx,a[1]+dy) for dx in (-1,0,1) for dy in (-1,0,1) if dx or dy],
        key=lambda q:(-max(abs(q[0]-p[0]),abs(q[1]-p[1])),q[1],q[0]))
    destination=next((q for q in candidates if q!=p and physical(engine,actor,a,q)),None)
    if destination is None and physical(engine,actor,a,p,ignore=(player,)):
        destination=p
    if destination is None:
        engine.log.add('There is no room to pass.',MSG_DEFAULT)
        return False
    actor.x,actor.y=destination
    player.x,player.y=a
    engine._update_fov()
    engine._on_player_step(*a)
    if bool(engine.normal_player_vision()['visible'][actor.x,actor.y]):
        engine.log.add(f'The {actor.name} steps aside.',MSG_DEFAULT)
    return True
