# components/ai.py
from __future__ import annotations
import random
import enum
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from entities.actor import Actor
    from world.local_map import LocalMap
    from engine.message_log import MessageLog


class AIState(enum.Enum):
    DORMANT    = "dormant"
    WANDERING  = "wandering"
    ALERTED    = "alerted"
    HUNTING    = "hunting"
    FLEEING    = "fleeing"
    ATTACKING  = "attacking"
    WAITING    = "waiting"


class AI:
    """
    Base AI component. Subclassed per creature archetype.
    Each subclass defines behaviour appropriate to its nature.

    The state machine is simple and data-driven:
      DORMANT    → not yet aware
      WANDERING  → moving randomly in territory
      ALERTED    → heard something, investigating last known position
      HUNTING    → pursuing target
      ATTACKING  → adjacent to target, striking
      FLEEING    → running from threat
      WAITING    → intentionally still (ambush)
    """

    def __init__(
        self,
        state:           AIState = AIState.WANDERING,
        wander_radius:   int     = 8,
        alert_memory:    int     = 10,
    ) -> None:
        self.state           = state
        self.wander_radius   = wander_radius
        self.alert_memory    = alert_memory   # turns before forgetting alert

        self.home_x:         int | None = None
        self.home_y:         int | None = None
        self.target_x:       int | None = None
        self.target_y:       int | None = None
        self.memory_turns:   int        = 0
        self.pursuit_turns_without_contact: int = 0
        self.move_accumulator: float = 0.0

    def set_home(self, x: int, y: int) -> None:
        self.home_x = x
        self.home_y = y

    def take_turn(
        self,
        actor:     Actor,
        local_map: LocalMap,
        entities:  list[Actor],
        player:    Actor,
        log:       MessageLog,
        rng:       random.Random,
        ambient_light: float,
        engine=None,
    ) -> None:
        """
        Process one AI turn. Subclasses override
        specific state behaviours.
        """
        _prev_state = self.state
        self._update_state(actor, local_map, player, ambient_light, engine=engine)
        if engine is not None:
            _fire_creature_callout(actor, engine, _prev_state, self.state)
        self._act(actor, local_map, entities, player, log, rng, engine=engine)

    # ------------------------------------------------------------------ #
    #  State transitions
    # ------------------------------------------------------------------ #

    def _update_state(
        self,
        actor:         Actor,
        local_map:     LocalMap,
        player:        Actor,
        ambient_light: float,
        engine=None,
    ) -> None:
        perception = getattr(actor, "perception", None)
        if not perception:
            return

        can_see_player = _creature_can_see_player(actor, player, local_map, ambient_light, engine=engine)

        dist = _distance(actor, player)

        if can_see_player:
            # Reset pursuit timeout — entity has eyes on player
            self.pursuit_turns_without_contact = 0
            # Update last known player position
            actor._last_known_px  = player.x
            actor._last_known_py  = player.y
            self.target_x         = player.x
            self.target_y         = player.y
            self.memory_turns     = self.alert_memory
            if dist <= 1.5:
                self.state = AIState.ATTACKING
            else:
                self.state = AIState.HUNTING

        elif getattr(actor, "_last_known_px", None) is not None:
            lkx = actor._last_known_px
            lky = actor._last_known_py

            # Pursuit timeout — increment when chasing without LOS
            if self.state in (AIState.HUNTING, AIState.ALERTED, AIState.ATTACKING):
                _increment = 1
                if engine is not None:
                    _lm = getattr(engine, "local_map", None)
                    if _lm is not None:
                        try:
                            _ptile = str(_lm.tiles["terrain"][player.x, player.y])
                            _tdef = engine.data.terrain.get(_ptile, {})
                            if _tdef.get("secondary_effect") == "concealment":
                                _increment = int(
                                    engine.data.ai_config.get(
                                        "concealment_timeout_multiplier", 2.0
                                    )
                                )
                        except Exception:
                            pass
                self.pursuit_turns_without_contact += _increment
                _timeout = 20
                if engine is not None:
                    _cdef = getattr(engine, "data", None)
                    if _cdef is not None:
                        _timeout = _cdef.entities.get(actor.tile, {}).get(
                            "pursuit_timeout", 20
                        )
                if self.pursuit_turns_without_contact >= _timeout:
                    self.pursuit_turns_without_contact = 0
                    actor._last_known_px = None
                    actor._last_known_py = None
                    self.state = AIState.WANDERING
                    return

            # Pursue toward last known player position
            at_edge = (
                actor.x <= 1 or actor.x >= local_map.width - 2 or
                actor.y <= 1 or actor.y >= local_map.height - 2
            )
            if actor.x == lkx and actor.y == lky:
                # Check if creature should follow player through a stair
                _used_stair = False
                if engine is not None:
                    _lm2 = getattr(engine, "local_map", None)
                    if _lm2 is not None:
                        try:
                            _stile = str(_lm2.tiles["terrain"][actor.x, actor.y])
                            _cdef2 = engine.data.entities.get(actor.tile, {})
                            if _stile in ("stairs_down", "stairs_up") and _cdef2.get("can_use_stairs", False):
                                actor._pending_stair_use = _stile
                                _used_stair = True
                        except Exception:
                            pass
                if not _used_stair:
                    _at_boundary = (
                        actor.x <= 0 or actor.x >= local_map.width - 1 or
                        actor.y <= 0 or actor.y >= local_map.height - 1
                    )
                    _can_cross_bdry = False
                    if engine is not None and _at_boundary:
                        _cdb = engine.data.entities.get(actor.tile, {})
                        _can_cross_bdry = _cdb.get("can_cross_chunks", False)
                    if not _can_cross_bdry:
                        # Reached last known position — trail lost
                        actor._last_known_px = None
                        actor._last_known_py = None
                        self.state = AIState.WANDERING
                    # else: at boundary, can cross — engine detects and transfers
            elif at_edge and not can_see_player:
                # Only abandon if last known position is also near the edge,
                # meaning the player crossed into a different chunk.
                # If last known is in the interior, keep pursuing.
                _lk_near_edge = (
                    lkx <= 2 or lkx >= local_map.width - 3 or
                    lky <= 2 or lky >= local_map.height - 3
                )
                if _lk_near_edge:
                    _can_cross_edge = False
                    if engine is not None:
                        _cde = engine.data.entities.get(actor.tile, {})
                        _can_cross_edge = _cde.get("can_cross_chunks", False)
                    if not _can_cross_edge:
                        actor._last_known_px = None
                        actor._last_known_py = None
                        self.state = AIState.WANDERING
                    # else: continue pursuing — engine detects boundary crossing
                else:
                    self.target_x = lkx
                    self.target_y = lky
                    self.state    = AIState.ALERTED
            else:
                self.target_x = lkx
                self.target_y = lky
                self.state    = AIState.ALERTED

        else:
            self.pursuit_turns_without_contact = 0
            if self.state in (AIState.ALERTED,
                              AIState.HUNTING,
                              AIState.ATTACKING):
                self.state = AIState.WANDERING


    # ------------------------------------------------------------------ #
    #  Actions
    # ------------------------------------------------------------------ #

    def _act(
        self,
        actor:     Actor,
        local_map: LocalMap,
        entities:  list[Actor],
        player:    Actor,
        log:       MessageLog,
        rng:       random.Random,
        engine=None,
    ) -> None:
        if self.state == AIState.DORMANT:
            return

        elif self.state == AIState.WANDERING:
            self._wander(actor, local_map, entities, rng)

        elif self.state == AIState.ALERTED:
            dist_to_player = _distance(actor, player)
            if dist_to_player <= 1.5:
                self._attack(actor, player, log, engine=engine)
            else:
                terrain_data = getattr(engine, "data", None)
                terrain_data = getattr(terrain_data, "terrain", None) if terrain_data else None
                self._move_toward(
                    actor, local_map, entities,
                    self.target_x or actor.x,
                    self.target_y or actor.y,
                    player=player,
                    terrain_data=terrain_data,
                    engine=engine,
                )

        elif self.state == AIState.HUNTING:
            dist_to_player = _distance(actor, player)
            if dist_to_player <= 1.5:
                self._attack(actor, player, log, engine=engine)
            else:
                terrain_data = getattr(engine, "data", None)
                terrain_data = getattr(terrain_data, "terrain", None) if terrain_data else None
                # Clamp target to map bounds: live pursuer phantom may have out-of-bounds coords.
                # TCOD pathfinding crashes on negative or oversized targets.
                _htx = max(0, min(local_map.width - 1, player.x))
                _hty = max(0, min(local_map.height - 1, player.y))
                self._move_toward(
                    actor, local_map, entities,
                    _htx, _hty,
                    player=player,
                    terrain_data=terrain_data,
                    engine=engine,
                )

        elif self.state == AIState.ATTACKING:
            # Guard: don't attack a phantom outside map bounds (live pursuer virtual target).
            if 0 <= player.x < local_map.width and 0 <= player.y < local_map.height:
                self._attack(actor, player, log, engine=engine)
            else:
                terrain_data = getattr(engine, "data", None)
                terrain_data = getattr(terrain_data, "terrain", None) if terrain_data else None
                _atx = max(0, min(local_map.width - 1, player.x))
                _aty = max(0, min(local_map.height - 1, player.y))
                self._move_toward(actor, local_map, entities, _atx, _aty,
                                  player=player, terrain_data=terrain_data, engine=engine)

        elif self.state == AIState.FLEEING:
            self._flee(actor, local_map, entities, player, rng)

        elif self.state == AIState.WAITING:
            pass

    # ------------------------------------------------------------------ #
    #  Movement helpers
    # ------------------------------------------------------------------ #

    def _wander(
        self,
        actor:     Actor,
        local_map: LocalMap,
        entities:  list[Actor],
        rng:       random.Random,
    ) -> None:
        """Move randomly, staying within wander_radius of home."""
        if rng_chance(0.5):
            return   # creatures don't move every turn while wandering

        candidates = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = actor.x + dx, actor.y + dy
                if not local_map.in_bounds(nx, ny):
                    continue
                if not local_map.walkable[nx, ny]:
                    continue
                if _blocked_by_entity(nx, ny, entities, actor):
                    continue
                # Stay within wander radius of home
                if self.home_x is not None:
                    if _distance_xy(nx, ny,
                                    self.home_x,
                                    self.home_y) > self.wander_radius:
                        continue
                candidates.append((nx, ny))

        if candidates:
            nx, ny = rng.choice(candidates)
            actor.x, actor.y = nx, ny

    def _move_toward(
        self,
        actor:        Actor,
        local_map:    LocalMap,
        entities:     list[Actor],
        tx:           int,
        ty:           int,
        player:       "Actor | None" = None,
        terrain_data: "dict | None"  = None,
        engine=None,
    ) -> None:
        """Step one tile toward (tx, ty) using tcod pathfinding."""
        import tcod.path

        if actor.x == tx and actor.y == ty:
            return

        cost = local_map.walkable.astype("int8")

        # Apply terrain move cost (multiply by 10, floor 1) for pathfinding preference
        if terrain_data:
            for tx2 in range(cost.shape[0]):
                for ty2 in range(cost.shape[1]):
                    if cost[tx2, ty2] == 0:
                        continue
                    t = local_map.tiles[tx2, ty2]["terrain"]
                    if isinstance(t, bytes):
                        t = t.decode()
                    entry = terrain_data.get(str(t), {})
                    mc = entry.get("move_cost", 1.0)
                    cost[tx2, ty2] = max(1, int(mc * 10))

        # forgetting_fog: random per-tile noise disrupts pathfinding
        weather = getattr(engine, "weather", None)
        if weather and weather.state == "forgetting_fog":
            noise_range = int(weather.get_mechanic("pathfind_noise", 3))
            _entity_id  = getattr(actor, "entity_id", id(actor))
            _turn       = getattr(engine, "turn", 0)
            _noise_rng  = random.Random(_entity_id + _turn)
            for _nx in range(cost.shape[0]):
                for _ny in range(cost.shape[1]):
                    if cost[_nx, _ny] == 0:
                        continue
                    cost[_nx, _ny] = max(1, int(cost[_nx, _ny]) + _noise_rng.randint(-noise_range, noise_range))

        # Mark other blocking entities as impassable
        for e in entities:
            if e is actor:
                continue
            if player is not None and e is player:
                continue  # target tile must remain reachable
            if getattr(e, "blocks_movement", True):
                if 0 <= e.x < cost.shape[0] and 0 <= e.y < cost.shape[1]:
                    cost[e.x, e.y] = 0

        graph  = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
        pf     = tcod.path.Pathfinder(graph)
        pf.add_root((actor.x, actor.y))
        path   = pf.path_to((tx, ty)).tolist()

        if len(path) >= 2:
            next_x, next_y = path[1]
            if not _is_tile_occupied(entities, next_x, next_y, exclude=actor):
                actor.x, actor.y = next_x, next_y

    def _flee(
        self,
        actor:     Actor,
        local_map: LocalMap,
        entities:  list[Actor],
        player:    Actor,
        rng:       random.Random,
    ) -> None:
        """Move away from player."""
        import math
        best      = None
        best_dist = -1.0

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = actor.x + dx, actor.y + dy
                if not local_map.in_bounds(nx, ny):
                    continue
                if not local_map.walkable[nx, ny]:
                    continue
                if _blocked_by_entity(nx, ny, entities, actor):
                    continue
                d = math.sqrt((nx - player.x)**2 + (ny - player.y)**2)
                if d > best_dist:
                    best_dist = d
                    best      = (nx, ny)

        if best:
            actor.x, actor.y = best

    def _attack(
        self,
        actor:  Actor,
        target: Actor,
        log:    MessageLog,
        engine=None,
    ) -> None:
        fighter        = getattr(actor,  "fighter", None)
        target_fighter = getattr(target, "fighter", None)

        if not fighter or not target_fighter:
            return

        # Full resolve_attack path when engine is available
        if engine is not None:
            _monster_attack_entity(actor, target, engine)
            return

        # Legacy fallback (no engine context)
        from engine.message_log import MSG_DANGER
        damage = max(0, fighter.power - target_fighter.defense)
        if damage == 0:
            log.add(
                f"The {actor.name} strikes but cannot penetrate.",
                WORN_STONE,
            )
            return

        actual = target_fighter.take_damage(fighter.power)
        target.took_damage_this_turn = True

        if target.name == "Player":
            log.add_danger(
                f"The {actor.name} strikes you for {actual} damage."
            )
        else:
            log.add(
                f"The {actor.name} strikes {target.name} "
                f"for {actual} damage.",
                MSG_DANGER,
            )

        if target_fighter.is_dead:
            target.is_alive = False


# ------------------------------------------------------------------ #
#  Subclass archetypes
# ------------------------------------------------------------------ #

class WanderingAI(AI):
    """
    Default AI. Wanders, hunts when it sees the player.
    Base behaviour for most creatures.
    """
    pass


class AmbushAI(AI):
    """
    Waits motionless until the player comes close,
    then attacks. Does not wander.
    Appropriate for things that hunt by stillness.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(state=AIState.WAITING, **kwargs)
        self._triggered = False

    def _update_state(self, actor, local_map, player, ambient_light, engine=None):
        perception = getattr(actor, "perception", None)
        if not perception:
            return

        dist = _distance(actor, player)

        if not self._triggered:
            # Only trigger when player is very close
            if dist <= perception.sight_radius * 0.5:
                self._triggered  = True
                self.target_x    = player.x
                self.target_y    = player.y
                self.memory_turns = self.alert_memory
                self.state       = AIState.HUNTING
        else:
            super()._update_state(
                actor, local_map, player, ambient_light, engine=engine
            )


class FleeingAI(AI):
    """
    Flees from the player on sight.
    For things that are dangerous but not aggressive —
    corrupted prey animals, fleeing civilians.
    """

    def _update_state(self, actor, local_map, player, ambient_light, engine=None):
        perception = getattr(actor, "perception", None)
        if not perception:
            return

        can_see = _creature_can_see_player(actor, player, local_map, ambient_light, engine=engine)
        if can_see:
            self.state = AIState.FLEEING
        else:
            if self.state == AIState.FLEEING:
                self.state = AIState.WANDERING


class CirclingAI(AI):
    """
    Maintains distance. Closes to attack, retreats after.
    Appropriate for things that strike and withdraw.
    """

    PREFERRED_DIST = 3

    def _update_state(self, actor, local_map, player, ambient_light, engine=None):
        super()._update_state(actor, local_map, player, ambient_light, engine=engine)

        dist = _distance(actor, player)
        if self.state == AIState.HUNTING:
            if dist <= self.PREFERRED_DIST:
                # Guard: don't attack a phantom outside map bounds (live pursuer virtual target).
                if 0 <= player.x < local_map.width and 0 <= player.y < local_map.height:
                    self.state = AIState.ATTACKING
        elif self.state == AIState.ATTACKING:
            if dist > self.PREFERRED_DIST + 1:
                self.state = AIState.HUNTING


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #

def _creature_can_see_player(entity, player, local_map, ambient_light: float = 1.0, engine=None) -> bool:
    """
    True if the creature can see the player.
    Checks sight_radius, ambient light / darkvision, and Bresenham LOS
    through local_map.transparent.  Does NOT read the player-facing
    'visible' flag — that is player-centric, not creature-centric.
    dead_calm weather adds creature_alert_radius_bonus to effective sight range.
    """
    import math
    dx   = player.x - entity.x
    dy   = player.y - entity.y
    dist = math.sqrt(dx * dx + dy * dy)

    perception = getattr(entity, "perception", None)
    sight      = perception.sight_radius if perception else 8

    weather = getattr(engine, "weather", None)
    if weather:
        sight += weather.get_mechanic("creature_alert_radius_bonus", 0)

    if dist > sight:
        return False

    # Darkvision: creatures without it have sharply reduced range in darkness
    if perception and not perception.sees_in_dark and ambient_light < 0.1:
        if dist > max(1, sight // 4):
            return False

    # Concealment: tall grass reduces effective sight by 2 tiles
    if getattr(player, "_in_concealment", False):
        if dist > max(1, sight - 2):
            return False

    # Bresenham LOS — walk the line, check every intermediate tile
    x0, y0   = entity.x, entity.y
    x1, y1   = player.x, player.y
    dx_abs   = abs(x1 - x0)
    dy_abs   = abs(y1 - y0)
    sx       = 1 if x0 < x1 else -1
    sy       = 1 if y0 < y1 else -1
    err      = dx_abs - dy_abs
    x, y     = x0, y0

    while True:
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy_abs:
            err -= dy_abs
            x   += sx
        if e2 < dx_abs:
            err += dx_abs
            y   += sy
        if x == x1 and y == y1:
            break
        if not local_map.in_bounds(x, y) or not local_map.transparent[x, y]:
            return False

    return True


def _distance(a: Actor, b: Actor) -> float:
    import math
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)


def _distance_xy(x1: int, y1: int, x2: int, y2: int) -> float:
    import math
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)


def _blocked_by_entity(
    x:        int,
    y:        int,
    entities: list,
    exclude:  object,
) -> bool:
    for e in entities:
        if e is exclude:
            continue
        if e.x == x and e.y == y and getattr(e, "blocks_movement", True):
            return True
    return False


def _is_tile_occupied(
    entities: list,
    x:        int,
    y:        int,
    exclude:  object = None,
) -> bool:
    """Return True if any blocking entity occupies (x, y)."""
    for e in entities:
        if e is exclude:
            continue
        if e.x == x and e.y == y and getattr(e, "blocks_movement", True):
            return True
    return False


def rng_chance(p: float) -> bool:
    import random
    return random.random() < p


# ------------------------------------------------------------------ #
#  Full combat resolution for monster → player (or entity) attacks
# ------------------------------------------------------------------ #

def _monster_attack_entity(monster, target, engine) -> None:
    """
    Resolve a monster attack using the full combat system.
    Called from AI._attack() when engine is available.
    """
    from engine.combat import resolve_attack
    import random as _random

    monster_fighter = getattr(monster, "fighter", None)
    target_fighter  = getattr(target,  "fighter", None)
    if not monster_fighter or not target_fighter:
        return

    is_player = (target is engine.player)

    # Line-of-sight check — don't attack through walls
    from engine.engine import Engine as _Engine
    if not _Engine._has_line_of_sight_adjacent(
        engine.local_map, monster.x, monster.y, target.x, target.y
    ):
        return

    # Build synthetic weapon from monster JSON
    monster_def = engine.data.entities.get(monster.tile, {})
    attack_verb = monster_def.get("attack_verb", "strikes at thee")

    # Check ranged attack conditions once — used on both the invincible path
    # and the normal path so the tween fires unconditionally.
    import math as _ra_m
    _ranged_def  = monster_def.get("ranged_attack")
    _do_ranged   = False
    _ranged_dist = 0.0
    if _ranged_def and hasattr(engine, "spawn_projectile"):
        _ranged_dist = _ra_m.sqrt(
            (target.x - monster.x) ** 2 + (target.y - monster.y) ** 2)
        if _ranged_dist >= _ranged_def.get("min_range", 2):
            _do_ranged = True

    # Invincibility check (player only)
    if is_player and getattr(engine, "player_invincible", False):
        from config import DEBUG_MODE as _DEBUG_MODE
        inv_msg = f"The {monster.name} {attack_verb} — thou art untouched."
        if _DEBUG_MODE:
            from engine.combat import roll_dice as _roll_dice
            _d_str = monster_def.get("damage_dice", "1d4")
            _d_bon = monster_def.get("damage_bonus", 0)
            _r     = _roll_dice(_d_str, _random.Random()) + _d_bon
            _suf   = f"+{_d_bon}" if _d_bon > 0 else (str(_d_bon) if _d_bon < 0 else "")
            inv_msg += f"  [{_d_str}{_suf} → {_r}] (invincible)"
        engine.log.add(inv_msg, STONE_BLUE)
        if _do_ranged:
            engine.spawn_projectile(
                float(monster.x), float(monster.y),
                float(target.x), float(target.y),
                _ranged_def.get("tile", monster.tile),
                id(monster),
                _ranged_def.get("duration", 0.45),
                on_hit=False,
            )
        return

    # Pre-attack announcement
    engine.log.add(f"The {monster.name} {attack_verb}.", WORN_STONE)

    weapon = {
        "damage_dice":      monster_def.get("damage_dice",              "1d4"),
        "damage_bonus":     monster_def.get("damage_bonus",             0),
        "essence":          monster_def.get("attack_essence",           None),
        "essence_strength": monster_def.get("attack_essence_strength",  0.0),
    }

    # Defender body def
    from engine.combat import get_body_def
    body_def = get_body_def(target_fighter, engine.data.bodies)

    # Defender essence mods (player has none for now)
    defender_essence_mods = {}
    if not is_player:
        defender_def = engine.data.entities.get(target.tile, {})
        defender_essence_mods = defender_def.get("essence_modifiers", {})

    defender_name = "thee" if is_player else target.name

    # Dodge chance
    if is_player:
        defender_dodge_chance = float(getattr(target, "dodge_chance", 0.05))
    else:
        defender_def2 = engine.data.entities.get(target.tile, {})
        defender_dodge_chance = float(defender_def2.get("dodge_chance", 0.0))

    # Shield (block) — only relevant when player is defending
    shield_def = None
    if is_player:
        equip = getattr(target, "equipment", None)
        if equip:
            offhand = equip.slots.get("offhand")
            if offhand:
                offhand_def = engine.data.items.get(getattr(offhand, "item_id", ""), {})
                if offhand_def.get("category") == "shield":
                    shield_def = offhand_def

    result = resolve_attack(
        attacker_name          = monster.name,
        defender_name          = defender_name,
        defender_fighter       = target_fighter,
        body_def               = body_def,
        weapon                 = weapon,
        creature_essence_mods  = defender_essence_mods,
        rng                    = _random.Random(),
        defender_dodge_chance  = defender_dodge_chance,
        shield_def             = shield_def,
    )

    # Log messages — incoming damage (creature→player/entity): dusty_rose family
    from config import DEBUG_MODE as _DEBUG_MODE
    _dbg_appended = False
    for msg, mtype in zip(result.messages, result.message_types):
        if mtype == "deflect":
            color = STONE_BLUE       # slate_mid — dim
        elif mtype == "impair":
            color = DUSTY_ROSE        # dusty_rose — player impaired
        else:                            # hit / death
            color = DUSTY_ROSE        # dusty_rose
        if _DEBUG_MODE and not _dbg_appended and result.debug_formula:
            msg = msg + "  " + result.debug_formula
            _dbg_appended = True
        engine.log.add(f"› {msg}", color)
    if _DEBUG_MODE and not _dbg_appended and result.debug_formula:
        engine.log.add(f"  {result.debug_formula}", OLD_GROWTH)
    if result.damage_number > 0:
        engine.log.add(f"  {result.damage_number} damage.", DUSTY_ROSE)  # bright red
        if is_player and getattr(engine.display, "CALLOUT_DAMAGE_NUMBERS", True):
            _num_y = target.y - 0.3 if result.is_crit else float(target.y)
            engine.callouts.add(str(result.damage_number),
                                target.x, _num_y, DUSTY_ROSE,
                                font_size="damage")
    elif result.damage_dealt == 0 and is_player and any(
            mt == "deflect" for mt in result.message_types):
        if getattr(engine.display, "CALLOUT_DAMAGE_NUMBERS", True):
            engine.callouts.add("—", target.x, float(target.y),
                                STONE_BLUE, font_size="creature")

    # Block callout — "BLOCKED" in muted colour above defender
    if result.blocked and is_player and getattr(engine.display, "CALLOUT_DAMAGE_NUMBERS", True):
        engine.callouts.add("BLOCKED", target.x, float(target.y) - 0.6,
                            STONE_BLUE, font_size="status")

    # Critical hit — creature crits deal "CRITICAL" in blood_rose + stronger shake
    if result.is_crit and result.damage_dealt > 0 and is_player:
        if getattr(engine.display, "CALLOUT_DAMAGE_NUMBERS", True):
            engine.callouts.add("CRITICAL", target.x, target.y - 0.8,
                                BLOOD_STONE, lifetime=1.2,
                                font_size="crit")
        engine.trigger_screenshake(5)

    if result.damage_dealt > 0 and is_player:
        target.took_damage_this_turn = True

    # Fire ON_DAMAGE_TAKEN hook when player is hit
    if result.damage_dealt > 0 and is_player:
        from engine.hooks import HookEvent
        from engine.engine import _apply_effects
        effects = engine.hooks.fire(HookEvent.ON_DAMAGE_TAKEN, {
            "damage":       result.damage_dealt,
            "raw_damage":   result.damage_raw,
            "essence":      result.essence_applied,
            "hit_location": result.location_id,
            "attacker":     monster,
            "player":       target,
            "engine":       engine,
        })
        _apply_effects(effects, engine)

    # Blood placement — player bleeds red when struck
    if result.damage_dealt > 0 and is_player:
        engine._place_blood_tile(target.x, target.y, "red")
        from rendering.particles import BLOOD_COLORS
        _bcolor = BLOOD_COLORS.get("red")
        if _bcolor is not None:
            engine._pending_blood.append({
                "defender_tile": (target.x, target.y),
                "attacker_tile": (monster.x, monster.y),
                "color": _bcolor,
            })

    # Plague crow sickness — 30% chance on hit
    if monster.tile == "plague_crow" and result.damage_dealt > 0 and is_player:
        if random.random() < 0.30:
            needs = getattr(engine.player, "needs", None)
            if needs:
                current = getattr(engine.player, "_sickness_turns", 0)
                engine.player._sickness_turns = max(current, 30)
                engine.log.add(
                    "The crow's touch carries something wrong. "
                    "Thy body knows it.",
                    DRIED_BLOOD,
                )

    if result.defender_dead:
        target.is_alive = False
        if is_player:
            engine._death_killer = monster.name

    # Ranged attack tween — fires on hit, miss, and deflect alike.
    if _do_ranged:
        engine.spawn_projectile(
            float(monster.x), float(monster.y),
            float(target.x), float(target.y),
            _ranged_def.get("tile", monster.tile),
            id(monster),
            _ranged_def.get("duration", 0.45),
            on_hit=result.damage_dealt > 0,
            blood_type="red",   # target (player) blood
        )


# ------------------------------------------------------------------ #
#  Callout helpers
# ------------------------------------------------------------------ #

def _fire_creature_callout(actor, engine, prev_state, new_state) -> None:
    """
    Fire a creature sound callout when an AI state transition occurs.
    Reads callout_sounds from the creature JSON via engine.data.
    """
    if not getattr(engine.display, "CALLOUT_CREATURE_SOUNDS", True):
        return

    creature_def   = engine.data.entities.get(actor.tile, {})
    callout_sounds = creature_def.get("callout_sounds", {})
    if not callout_sounds:
        return

    trigger = None
    if prev_state == AIState.WANDERING and new_state == AIState.HUNTING:
        trigger = "on_spot"
    elif (prev_state not in (AIState.ATTACKING,)
          and new_state == AIState.ATTACKING):
        trigger = "on_attack"

    if trigger is None:
        return

    entry = callout_sounds.get(trigger)
    if not entry:
        return

    engine._pending_callouts.append({
        "text":    entry.get("text", ""),
        "world_x": actor.x,
        "world_y": actor.y,
        "color":   tuple(entry.get("color", [200, 180, 150])),
        "lifetime": 2.0,
    })