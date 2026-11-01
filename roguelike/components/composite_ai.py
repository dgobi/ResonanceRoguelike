"""Shared perception, legal positioning and ordinary action authority for recipes."""
from __future__ import annotations
from collections import deque
import copy
from dataclasses import asdict
from components.ai import AI, AIState, _creature_can_see_player, _monster_attack_result
from engine.spatial import melee_contact, melee_attack_legal


class CompositeAI(AI):
    def __init__(self, wander_radius=8, *, profile):
        super().__init__(wander_radius=wander_radius)
        from engine.ai_profiles import saved_profile
        self.profile = saved_profile(profile)
        self.phase = 'idle'
        self.target = None
        self.withdraw_left = self.hold_left = self.approach_left = self.no_progress = 0
        self.best_distance = None
        self.suppressed = None
        self.route_blocked = False
        self.opportunities = 0
        self.trace = []  # privileged bounded diagnostics; never definition/save data
        self.last_cancellation = None
        if self.profile['recipe'] == 'observation_averse':
            from components.observation_averse import initialize
            initialize(self)

    def snapshot(self):
        if self.profile['recipe'] == 'observation_averse':
            from components.observation_averse import snapshot
            return snapshot(self)
        keys = ('phase', 'target', 'withdraw_left', 'hold_left', 'approach_left',
                'no_progress', 'best_distance', 'suppressed', 'route_blocked', 'opportunities')
        return dict(profile=copy.deepcopy(self.profile), state={k: copy.deepcopy(getattr(self, k)) for k in keys})

    def cancel(self, actor, reason, *, keep_sound=False):
        from engine.local_rivals import retire_player
        from engine.sound import clear_interest
        interest = self.sound_interest if keep_sound else None
        self.phase, self.target = 'idle', None
        self.withdraw_left = self.hold_left = self.approach_left = self.no_progress = 0
        self.best_distance = None
        self.route_blocked = False
        self.local_target = None
        retire_player(actor)
        clear_interest(self)
        self.state = AIState.WANDERING
        self.sound_interest = interest
        self.last_cancellation = reason
        if self.profile['recipe'] == 'observation_averse':
            from components.observation_averse import initialize
            spent = self.bonus_phase, self.reaction_phase
            initialize(self)
            self.bonus_phase, self.reaction_phase = spent
        for field in ('_surface_exit_x', '_surface_exit_y', '_surface_exit_wx', '_surface_exit_wy'):
            setattr(actor, field, None)
        actor._arrival_cooldown, actor._just_arrived = 0, False

    def resolve_target(self, engine, actor):
        """Lifecycle validation only; no observation, coordinates, clocks or actions."""
        from engine.local_rivals import owner, active, eligible, living
        t = self.target
        if t is None:
            return None
        if not living(actor) or not active(engine, actor) or t['owner'] != owner(engine):
            self._retire_target(actor, 'foreign_scene')
            return None
        matches = ([engine.player] if t['role'] == 'player' else
                   [a for a in engine.entities if getattr(a, '_individual_id', None) == t['id']])
        if len(matches) != 1 or not eligible(engine, actor, matches[0]):
            self._retire_target(actor, 'invalid_target')
            return None
        return matches[0]

    def _retire_target(self, actor, reason, *, keep_sound=False):
        if self.profile['recipe'] == 'observation_averse':
            from components.observation_averse import retire_prey
            retire_prey(self, actor, reason, keep_sound=keep_sound)
        else:
            self.cancel(actor, reason, keep_sound=keep_sound)

    def _observed(self, engine, actor, ambient):
        from engine.local_rivals import eligible, allocate
        from engine.spatial import terrain_conceals
        found = []
        for candidate in engine.entities:
            if not eligible(engine, actor, candidate):
                continue
            if candidate is not engine.player and terrain_conceals(candidate, engine.local_map, engine.data.terrain):
                sight = actor.perception.sight_radius + (engine.weather.get_mechanic('creature_alert_radius_bonus', 0) if engine.weather else 0)
                if (candidate.x-actor.x)**2 + (candidate.y-actor.y)**2 > max(1, sight-2)**2:
                    continue
            if _creature_can_see_player(actor, candidate, engine.local_map, ambient, engine=engine):
                found.append(candidate)
        allocate(engine, [actor] + [a for a in found if a is not engine.player])
        return sorted(found, key=lambda a: ((a.x-actor.x)**2+(a.y-actor.y)**2, self._key(engine, a)))

    @staticmethod
    def _key(engine, target):
        return 'player' if target is engine.player else target._individual_id

    def _remember(self, engine, target):
        from engine.local_rivals import owner
        now = engine.world_time.turn
        self.target = dict(role='player' if target is engine.player else 'creature',
                           id=None if target is engine.player else target._individual_id,
                           owner=owner(engine), x=target.x, y=target.y, seen=now,
                           deadline=now+self.profile['pursuit_timeout'], provenance='sight')

    def refresh_evidence(self, engine, actor, ambient_light):
        """Charged-phase observation/expiry, even without a granted decision.

        This never acquires prey, selects an action or spends tactical counters.
        Current sight may refresh a retained trail; recovery/holding alone cannot.
        """
        target = self.resolve_target(engine, actor)
        if target is None:
            return
        if target in self._observed(engine, actor, ambient_light):
            self._remember(engine, target)
        elif engine.world_time.turn > self.target['deadline']:
            self._retire_target(actor, 'evidence_expired', keep_sound=True)
        if self.target is not None:
            from engine.sound import clear_interest
            clear_interest(self)

    def _route(self, engine, actor, goal, *, forbidden=()):
        """At most 512 cells and 16 steps. BFS permits initially nearer/lateral steps.

        Occupancy, terrain capability and sealed diagonal rules are shared by
        planning and final movement. Routes are transient and rechecked per action.
        """
        m = engine.local_map
        start = (actor.x, actor.y)
        occupied = {(a.x, a.y) for a in engine.entities if a is not actor and getattr(a, 'blocks_movement', False)}
        cdef = engine.data.entities.get(actor._creature_id, {})
        def legal(a, b):
            return (m.in_bounds(*b) and b not in occupied and b not in forbidden and melee_contact(m, *a, *b)
                    and (self.profile['recipe'] != 'observation_averse' or not engine._decor_blocks_movement(*b))
                    and (engine.data.terrain.get(str(m.tiles[b]['terrain']), {}).get('creature_passable', True) or cdef.get('can_swim', False)))
        queue, parents, depth = deque([start]), {start: None}, {start: 0}
        while queue:
            here = queue.popleft()
            if goal(*here):
                if here == start:
                    return None, 0
                step = here
                while parents[step] != start:
                    step = parents[step]
                return step, depth[here]
            if depth[here] >= 16:
                continue
            for dx, dy in ((0,-1),(-1,0),(1,0),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)):
                p = here[0]+dx, here[1]+dy
                if len(parents) < 512 and p not in parents and legal(here, p):
                    parents[p], depth[p] = here, depth[here]+1
                    queue.append(p)
        return None, None

    def _move(self, engine, actor, step):
        if step is None or not actor.fighter.can_move():
            return False
        # Revalidate at commitment through the same movement predicate.
        selected, _ = self._route(engine, actor, lambda x,y: (x,y) == step)
        if selected != step:
            return False
        actor.x, actor.y = step
        return True

    def _tell(self, engine, actor, text, *, current_vision=False):
        from engine.local_rivals import visible
        from engine.palette import UI_TEXT_DIM
        if (bool(engine.normal_player_vision()['visible'][actor.x,actor.y]) if current_vision else visible(engine, actor)):
            engine.log.add(f'The {actor.name} {text}.', UI_TEXT_DIM)

    def take_turn(self, actor, local_map, entities, player, log, rng, ambient_light, engine=None):
        from engine.local_rivals import active
        from engine.sound import current_interest, clear_interest, investigate
        from engine.effect_lifecycle import disrupted
        from engine.venom import movement_denial
        if (engine is None or player is not engine.player or local_map is not engine.local_map
                or not active(engine, actor) or disrupted(actor, local_map)):
            return
        if self.profile['recipe'] == 'observation_averse':
            from components.observation_averse import take_turn
            return take_turn(self, actor, engine, ambient_light)
        self.opportunities += 1
        before = self.phase
        action, reason, result = 'wait', 'idle', None
        observed = self._observed(engine, actor, ambient_light)
        target = self.resolve_target(engine, actor)
        if target in observed:
            self._remember(engine, target)
        if self.target is not None and engine.world_time.turn > self.target['deadline']:
            self.suppressed = self._key(engine, target) if target else None
            self.cancel(actor, 'evidence_expired', keep_sound=True)
            target = None
            reason = 'evidence_expired'
        if self.suppressed and all(self._key(engine, a) != self.suppressed for a in observed):
            self.suppressed = None  # later genuinely new observed encounter
        if self.target is None:
            candidates = [a for a in observed if self._key(engine, a) != self.suppressed]
            if candidates:
                target = candidates[0]
                self._remember(engine, target)
                self.phase, self.approach_left = 'approach', 32
                self.no_progress, self.best_distance = 0, None
        if self.target is not None:
            clear_interest(self)
            tx, ty = self.target['x'], self.target['y']
            distance = lambda x,y: max(abs(x-tx), abs(y-ty))
            far = lambda x,y: distance(x,y) >= self.profile['retreat_distance']
            seen = target in observed
            if self.phase == 'withdraw' and far(actor.x, actor.y):
                self.phase = 'hold' if self.hold_left else 'return'
            if self.phase == 'cornered':
                step, _ = self._route(engine, actor, far)
                usable = bool(step)  # temporary paralysis is never route failure
                if usable and self.route_blocked:
                    # A newly useful route is the only same-encounter rearm.
                    self.phase = 'withdraw'
                    self.withdraw_left = self.profile['withdrawal_budget']
                    self.hold_left = self.profile['hold_opportunities']
                    self.route_blocked = False
                elif not usable:
                    self.route_blocked = True
            if self.phase in ('withdraw', 'hold'):
                hold = self.phase == 'hold'
                if hold:
                    self.hold_left -= 1
                if not far(actor.x, actor.y) and movement_denial(actor):
                    action, reason = 'wait', movement_denial(actor)
                elif not far(actor.x, actor.y):
                    self.withdraw_left = max(0, self.withdraw_left-1)
                    step, _ = self._route(engine, actor, far)
                    moved = self._move(engine, actor, step)
                    action, reason = ('move' if moved else 'wait'), 'holding_reposition' if hold else 'withdrawal'
                    if not far(actor.x, actor.y) and self.withdraw_left == 0:
                        self.phase, reason = 'cornered', 'withdrawal_exhausted'
                        self.route_blocked = not bool(step)
                    elif not hold and far(actor.x, actor.y):
                        self.phase = 'hold' if self.hold_left else 'return'
                else:
                    reason = 'holding_distance'
                if hold and self.hold_left == 0 and self.phase != 'cornered':
                    self.phase, self.approach_left = 'return', 32
                    self.no_progress, self.best_distance = 0, None
            elif self.phase == 'cornered':
                contacts = [a for a in observed if melee_attack_legal(local_map, actor, a)]
                defender = target if seen and target in contacts else (contacts[0] if contacts else None)
                if defender:
                    result = _monster_attack_result(actor, defender, engine, defensive=True)
                    action, reason = 'melee', 'cornered_defensive'
                else:
                    self.suppressed = self._key(engine, target)
                    self.cancel(actor, 'cornered_abandon')
                    reason = 'cornered_abandon'
            elif seen and melee_attack_legal(local_map, actor, target):
                result = _monster_attack_result(actor, target, engine)
                action, reason = 'melee', 'engage'
                if result.target_dead:
                    self.cancel(actor, 'target_dead')
                elif result.committed and (bool(result.application and result.application.accepted)
                        if self.profile['trigger'] == 'accepted_application' else
                        (self.profile['trigger'] == 'committed_attack' or result.hit)):
                    self.phase = 'withdraw'
                    self.withdraw_left = self.profile['withdrawal_budget']
                    self.hold_left = self.profile['hold_opportunities']
                    self.approach_left, self.no_progress, self.best_distance = 32, 0, None
                    self._tell(engine, actor, 'strikes and draws away')
            else:
                if not seen and (actor.x, actor.y) == (tx, ty):
                    self.cancel(actor, 'empty_trail')
                    reason = 'empty_trail'
                elif movement_denial(actor):
                    action, reason = 'wait', movement_denial(actor)
                else:
                    self.approach_left = max(0, self.approach_left-1)
                    goal = (lambda x,y: melee_contact(local_map,x,y,tx,ty)) if seen else (lambda x,y: (x,y)==(tx,ty))
                    step, length = self._route(engine, actor, goal)
                    progress = length is not None and (self.best_distance is None or length < self.best_distance)
                    self.no_progress = 0 if progress else min(8, self.no_progress+1)
                    if length is not None:
                        self.best_distance = length
                    if self.approach_left == 0 or self.no_progress >= 8:
                        self.suppressed = self._key(engine, target)
                        self.cancel(actor, 'approach_exhausted')
                        reason = 'approach_exhausted'
                    else:
                        action = 'move' if self._move(engine, actor, step) else 'wait'
                        reason = 'approach' if seen else 'last_seen_search'
                        if not seen and (actor.x, actor.y) == (tx, ty):
                            self.cancel(actor, 'empty_trail')
                            reason = 'empty_trail'
        else:
            interest = current_interest(self, engine.world_time.turn)
            if interest:
                self.state = AIState.INVESTIGATING
                investigate(self, actor, local_map, entities)
                action, reason = 'investigate', 'anonymous_sound'
        if before != 'return' and self.phase == 'return':
            self._tell(engine, actor, 'closes in again')
        if result and result.target_dead:
            self.resolve_target(engine, actor)
        self.trace.append(dict(opportunity=self.opportunities, turn=engine.world_time.turn,
                               phase_before=before, phase=self.phase, action=action, reason=reason,
                               result=asdict(result) if result else None))
        self.trace = self.trace[-16:]
