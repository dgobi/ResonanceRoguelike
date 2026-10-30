"""Local, unidentified pulses. No event queue, actor target or off-scene scan.

Cardinal travel costs one, closed doors four, solid walls block. A bell alone
may seed its nonwalkable origin. One bounded flood is shared by all listeners.
At reference hearing six, strength is the maximum open-path cost. Interest is
valid through emission turn + 12; the next charged phase expires it. Delivery
never schedules an action: later actors in this phase may react, earlier ones
wait for their next normal decision. Equal received strength prefers last delivery.
"""
from __future__ import annotations
from collections import deque
import heapq

OPEN_COST = 1
CLOSED_DOOR_COST = 4
REFERENCE_HEARING = 6
MAX_COST = 48
INTEREST_TURNS = 12
STRENGTH = dict(combat=8, dismantle=8, flint=6, musk=6,
                bell_cracked=10, bell_intact=18)
CARDINAL = ((0, -1), (-1, 0), (1, 0), (0, 1))


def clear_interest(ai):
    ai.sound_interest = None
    from components.ai import AIState
    if ai.state == AIState.INVESTIGATING:
        ai.state = AIState.WANDERING


def current_interest(ai, turn):
    interest = getattr(ai, 'sound_interest', None)
    if interest is not None and turn > interest['deadline']:
        clear_interest(ai)
        return None
    return interest


def eligible(actor):
    from components.ai import AI, WanderingAI, CirclingAI, AIState
    ai = getattr(actor, 'ai', None)
    # Ambushers (including awake Lurkers) and fleeing archetypes keep their
    # special behavior. Sound never initializes or triggers hibernation/ambush.
    return (type(ai) in (AI, WanderingAI, CirclingAI)
            and getattr(actor, 'is_alive', True)
            and not getattr(actor, '_hibernating', False)
            and ai.state not in (AIState.DORMANT, AIState.WAITING, AIState.FLEEING))


def propagation(local_map, x, y, budget, *, bell=False):
    if not local_map.in_bounds(x, y):
        return {}
    terrain = str(local_map.tiles['terrain'][x, y])
    if not local_map.walkable[x, y] and not (bell and terrain in ('bell_intact', 'bell_cracked')):
        return {}
    costs = {(x, y): 0}
    frontier = [(0, x, y)]
    while frontier:
        cost, ax, ay = heapq.heappop(frontier)
        if costs[ax, ay] != cost:
            continue
        for dx, dy in CARDINAL:
            bx, by = ax + dx, ay + dy
            if not local_map.in_bounds(bx, by):
                continue
            door = str(local_map.tiles['terrain'][bx, by]) == 'door_closed'
            if not door and not local_map.walkable[bx, by]:
                continue
            new = cost + (CLOSED_DOOR_COST if door else OPEN_COST)
            if new <= budget and new < costs.get((bx, by), budget + 1):
                costs[bx, by] = new
                heapq.heappush(frontier, (new, bx, by))
    return costs


def emit(engine, x, y, kind, *, maker=None):
    """Deliver once to active-scene listeners; return count for diagnostics only."""
    strength = STRENGTH[kind]
    listeners = []
    for actor in engine.get_active_entities():
        if actor is engine.player or actor is maker or not eligible(actor):
            continue
        hearing = getattr(getattr(actor, 'perception', None), 'hearing_radius', 0)
        if hearing > 0:
            listeners.append((actor, strength + hearing - REFERENCE_HEARING))
    if not listeners:
        return 0
    m = engine.local_map
    costs = propagation(m, x, y, min(MAX_COST, max(b for _, b in listeners)),
                        bell=kind.startswith('bell_'))
    turn = engine.world_time.turn
    received = 0
    from components.ai import AIState
    for actor, budget in listeners:
        ai = actor.ai
        old = current_interest(ai, turn)
        # Actual player trails always win. Ignored events cannot wait behind
        # genuine pursuit or refresh its memory. Sight is rechecked at decision.
        if (getattr(actor, '_last_known_px', None) is not None
                or getattr(ai, 'local_target', None) is not None
                or ai.state in (AIState.HUNTING, AIState.ALERTED, AIState.ATTACKING)):
            clear_interest(ai)
            continue
        cost = costs.get((actor.x, actor.y))
        if cost is None or cost > budget:
            continue
        salience = budget - cost + 1
        if old is not None and salience < old['strength']:
            continue
        ai.sound_interest = dict(x=x, y=y, deadline=turn + INTEREST_TURNS,
                                 strength=salience, kind=kind)
        received += 1
        # Receiving is information only. State/action changes wait for normal AI.
    return received


def investigate(ai, actor, local_map, entities):
    """One ordinary cardinal step to the source or its reachable approach.

    Unlike pursuit, an occupied source is never an attack target. This small
    BFS uses actual walkability/blockers and cannot cut a sealed diagonal.
    An unreachable source spends normal decisions until world-time expiry.
    """
    interest = ai.sound_interest
    sx, sy = interest['x'], interest['y']
    occupied = {(a.x, a.y) for a in entities if a is not actor
                and getattr(a, 'blocks_movement', False)}
    blocked = not local_map.walkable[sx, sy] or (sx, sy) in occupied
    goals = ({(sx + dx, sy + dy) for dx, dy in CARDINAL}
             if blocked else {(sx, sy)})
    goals = {p for p in goals if local_map.in_bounds(*p)
             and local_map.walkable[p] and p not in occupied}
    start = (actor.x, actor.y)
    if start in goals:
        clear_interest(ai)
        return
    if not actor.fighter or not actor.fighter.can_move():
        return
    queue = deque([start])
    parents = {start: None}
    while queue:
        here = queue.popleft()
        if here in goals:
            step = here
            while parents[step] != start:
                step = parents[step]
            actor.x, actor.y = step
            if step in goals:
                clear_interest(ai)
            return
        for dx, dy in CARDINAL:
            p = (here[0] + dx, here[1] + dy)
            if (p not in parents and local_map.in_bounds(*p)
                    and local_map.walkable[p] and p not in occupied):
                parents[p] = here
                queue.append(p)
