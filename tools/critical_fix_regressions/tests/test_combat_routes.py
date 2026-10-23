"""Real-engine regressions for the shared normal/moveset melee pipeline.

Factories, data, item instances, fighters, hooks, death rewards and floor
placement are real. Resolver spies make contact outcomes deterministic when
testing route boundaries; the final test also runs the actual resolver.
Only temporary checkpoint roots are used, never the supplied game saves.
"""
from __future__ import annotations

import copy
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from test_effect_persistence import load_data, make_engine
from engine.combat import CombatResult
from engine.hooks import HookEvent


class CombatRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="resonance-combat-test-")
        self.addCleanup(temp.cleanup)
        save_patch = patch("engine.save_manager.SAVE_DIR",
                           Path(temp.name) / "saves")
        save_patch.start()
        self.addCleanup(save_patch.stop)

    def combat_case(self, creature="hollow_revenant", weapon="severance_blade"):
        engine = make_engine(self.data)
        engine.debug = None
        engine.rng = random.Random(29417)
        target = engine.creature_factory.spawn(creature, 13, 12)
        self.assertIsNotNone(target)
        engine.entities.append(target)
        item = engine.item_factory.create(weapon)
        self.assertIsNotNone(item)
        self.assertTrue(engine.player.inventory.add(item))
        engine.player.equipment.equip(item, "weapon")
        item.temporary_essence = [
            {"essence": "Dissolution", "strength": 0.8, "hits_remaining": 3}
        ]
        events = []
        for event in (HookEvent.ON_CRITICAL_HIT, HookEvent.ON_DAMAGE_DEALT,
                      HookEvent.ON_ENTITY_KILLED):
            def record(payload, event=event):
                events.append((event, dict(payload)))
            engine.hooks.register(event, record)
        return engine, target, item, events

    def attack(self, engine, target, route, key=None):
        if route == "normal":
            engine._player_attack(target)
        else:
            self.assertTrue(engine._try_moveset_action(
                engine.display.MOVESET_KEY_1 if key is None else key))

    @staticmethod
    def contact(*, damage=2, critical=False, hit=True, dodged=False):
        def resolve(**kwargs):
            fighter = kwargs["defender_fighter"]
            actual = fighter.take_damage(damage) if hit and not dodged else 0
            return CombatResult(
                hit=hit, dodged=dodged, damage_raw=damage + 2,
                damage_raw_post_essence=damage + 3,
                damage_dealt=actual, damage_number=actual,
                is_crit=critical, defender_dead=fighter.is_dead,
                location_id="torso", essence_applied="Dissolution")
        return resolve

    def test_both_routes_apply_modifiers_and_damage_critical_hooks_once(self):
        for route in ("normal", "moveset"):
            with self.subTest(route=route):
                engine, target, item, events = self.combat_case()
                target.tile = "grass"  # presentation is not creature identity
                original_def = copy.deepcopy(self.data.items[item.item_id])
                engine.player.fighter.corruption_damage_bonus = 2
                engine.player.fighter.corruption_channel_bonus = 3
                before_hp = target.fighter.hp
                with patch("engine.combat.resolve_attack",
                           side_effect=self.contact(critical=True)) as resolve:
                    self.attack(engine, target, route)
                resolve.assert_called_once()
                weapon = resolve.call_args.kwargs["weapon"]
                self.assertEqual(weapon["damage_bonus"],
                                 original_def.get("damage_bonus", 0) + 5)
                self.assertEqual(weapon["essences"], [
                    {"name": "Severance", "strength": 0.6},
                    {"name": "Dissolution", "strength": 0.8},
                ])
                self.assertEqual(resolve.call_args.kwargs["creature_essence_mods"],
                                 self.data.entities["hollow_revenant"]["essence_modifiers"])
                self.assertEqual(self.data.items[item.item_id], original_def)
                self.assertEqual(item.temporary_essence[0]["hits_remaining"], 2)
                self.assertEqual(target.fighter.hp, before_hp - 2)
                self.assertEqual([event for event, _ in events],
                                 [HookEvent.ON_CRITICAL_HIT, HookEvent.ON_DAMAGE_DEALT])
                for _, payload in events:
                    self.assertEqual(payload["damage"], 2)
                    self.assertEqual(payload["weapon_id"], item.item_id)
                    self.assertIs(payload["target"], target)
                self.assertEqual(events[0][1]["raw_damage"], 5)
                self.assertEqual(events[1][1]["essence"], "Dissolution")
                self.assertEqual(len(engine._pending_blood), 1)
                self.assertTrue(engine._pending_blood[0].get("is_crit"))
                self.assertEqual(engine.local_map.decor[(13, 12)], "bone_dust")

    def test_miss_or_dodge_never_fires_damage_hooks_or_spends_coating(self):
        for route in ("normal", "moveset"):
            for dodged in (False, True):
                with self.subTest(route=route, dodged=dodged):
                    engine, target, item, events = self.combat_case()
                    before_hp = target.fighter.hp
                    with patch("engine.combat.resolve_attack", side_effect=
                               self.contact(hit=False, dodged=dodged)):
                        self.attack(engine, target, route)
                    self.assertEqual(target.fighter.hp, before_hp)
                    self.assertEqual(item.temporary_essence[0]["hits_remaining"], 3)
                    self.assertEqual(events, [])
                    self.assertEqual(engine._pending_blood, [])

    def test_deflected_contact_spends_one_charge_but_no_damage_hooks(self):
        for route in ("normal", "moveset"):
            with self.subTest(route=route):
                engine, target, item, events = self.combat_case()
                with patch("engine.combat.resolve_attack", side_effect=
                           self.contact(damage=0, critical=True)):
                    self.attack(engine, target, route)
                self.assertEqual(item.temporary_essence[0]["hits_remaining"], 2)
                self.assertEqual(events, [])
                self.assertEqual(engine._pending_blood, [])

    def test_rejected_impairment_spends_no_turn_cooldown_or_coating(self):
        engine, target, item, events = self.combat_case()
        before = (engine.world_time.turn, engine._move_debt,
                  copy.deepcopy(item.temporary_essence))
        with patch.object(engine.player.fighter, "can_attack", return_value=False), \
                patch("engine.combat.resolve_attack") as resolve:
            engine._player_attack(target)
            engine._handle_key_local(engine.display.MOVESET_KEY_1)
        resolve.assert_not_called()
        self.assertEqual((engine.world_time.turn, engine._move_debt,
                          item.temporary_essence), before)
        self.assertEqual(engine.moveset_cooldowns, {})
        self.assertEqual(events, [])

    def test_dead_fighter_target_is_rejected_before_any_attack_spend(self):
        engine, target, item, events = self.combat_case()
        target.fighter.take_damage(target.fighter.hp)
        self.assertTrue(target.is_alive)  # finalization has not run yet
        turn = engine.world_time.turn
        with patch("engine.combat.resolve_attack") as resolve:
            engine._player_attack(target)
            engine._handle_key_local(engine.display.MOVESET_KEY_1)
        resolve.assert_not_called()
        self.assertEqual(engine.world_time.turn, turn)
        self.assertEqual(engine.moveset_cooldowns, {})
        self.assertEqual(item.temporary_essence[0]["hits_remaining"], 3)
        self.assertEqual(events, [])

    def test_critical_blood_marks_this_contact_not_previous_queued_hit(self):
        for route in ("normal", "moveset"):
            with self.subTest(route=route):
                engine, target, item, events = self.combat_case()
                for critical in (False, True):
                    engine.moveset_cooldowns.clear()
                    with patch("engine.combat.resolve_attack", side_effect=
                               self.contact(damage=1, critical=critical)):
                        self.attack(engine, target, route)
                self.assertEqual(len(engine._pending_blood), 2)
                self.assertFalse(engine._pending_blood[0].get("is_crit", False))
                self.assertTrue(engine._pending_blood[1].get("is_crit", False))
                self.assertEqual([event for event, _ in events], [
                    HookEvent.ON_DAMAGE_DEALT, HookEvent.ON_CRITICAL_HIT,
                    HookEvent.ON_DAMAGE_DEALT,
                ])

    def test_reveal_uses_disguised_creature_identity_and_persists_knowledge_key(self):
        engine, target, item, events = self.combat_case(
            "stone_lurker", "revelation_lens")
        target.tile = "grass"
        with patch("engine.combat.resolve_attack",
                   side_effect=self.contact(damage=1)):
            self.attack(engine, target, "moveset")
        self.assertEqual(engine.creature_knowledge, {
            "stone_lurker": {"revealed_weaknesses": ["Dissolution"],
                             "revealed_strengths": []}
        })
        engine._reveal_creature_knowledge(target)
        self.assertEqual(engine.creature_knowledge["stone_lurker"]
                         ["revealed_weaknesses"], ["Dissolution", "Revelation"])
        self.assertNotIn("grass", engine.creature_knowledge)

    def test_disguised_death_rewards_and_corpse_finalize_once_in_both_routes(self):
        # Difficulty is an existing supported schema field. Shipped definitions
        # presently omit it; this fixture guards that latent identity consumer.
        definition = dict(self.data.entities["stone_lurker"], difficulty="easy")
        with patch.dict(self.data.entities, {"stone_lurker": definition}):
            for route in ("normal", "moveset"):
                with self.subTest(route=route):
                    engine, target, item, events = self.combat_case("stone_lurker")
                    target.tile = "grass"
                    with patch("engine.combat.resolve_attack", side_effect=
                               self.contact(damage=target.fighter.hp)):
                        self.attack(engine, target, route)
                    corpses = engine.local_map.floor_objects[(13, 12)]
                    self.assertEqual(len(corpses), 1)
                    self.assertEqual(corpses[0].item_id, "corpse")
                    self.assertEqual(corpses[0].source_creature, "stone_lurker")
                    self.assertEqual(corpses[0].decay_timer, 300)
                    self.assertEqual(engine.player.level.exp, 36)
                    self.assertFalse(target.is_alive)
                    self.assertTrue(target._death_finalized)
                    killed = [payload for event, payload in events
                              if event == HookEvent.ON_ENTITY_KILLED]
                    self.assertEqual(len(killed), 1)
                    self.assertEqual(killed[0]["entity_id"], "stone_lurker")
                    self.assertEqual(killed[0]["blood_type"], "none")
                    engine._on_entity_death(target)
                    engine._player_attack(target)
                    engine.moveset_cooldowns.clear()
                    self.assertFalse(engine._try_moveset_action(engine.display.MOVESET_KEY_1))
                    self.assertEqual(engine.player.level.exp, 36)
                    self.assertEqual(len(engine.local_map.floor_objects[(13, 12)]), 1)
                    self.assertEqual(sum(event == HookEvent.ON_ENTITY_KILLED
                                         for event, _ in events), 1)

    def test_disguised_ephemeral_death_clears_aura_and_creates_no_corpse(self):
        engine, target, item, events = self.combat_case("bog_wraith")
        target.tile = "grass"
        target._wraith_exposure_turns = 4
        engine._update_fov()
        self.assertIn(id(target), engine._wraith_aura_state)
        with patch("engine.combat.resolve_attack", side_effect=
                   self.contact(damage=target.fighter.hp)):
            self.attack(engine, target, "normal")
        self.assertEqual(engine.local_map.floor_objects.get((13, 12), []), [])
        self.assertEqual(engine._wraith_aura_state, {})
        self.assertEqual(target._wraith_exposure_turns, 0)
        self.assertEqual(engine._wraith_overcorrect_turns, 3)
        self.assertEqual(sum(event == HookEvent.ON_ENTITY_KILLED
                             for event, _ in events), 1)

    def test_briar_retaliates_once_in_both_routes_and_respects_suppression(self):
        for route in ("normal", "moveset"):
            for suppression in (None, "actor", "zone"):
                with self.subTest(route=route, suppression=suppression):
                    engine, target, item, events = self.combat_case("briar_lurker")
                    target.tile = "grass"
                    if suppression == "actor":
                        target._ability_suppressed_turns = 2
                    elif suppression == "zone":
                        engine.local_map.disruption_zones.append({
                            "x": 13, "y": 12, "radius": 1, "turns_remaining": 2})
                    hp = engine.player.fighter.hp
                    with patch("engine.combat.resolve_attack", side_effect=
                               self.contact(damage=1)), \
                            patch.object(engine.rng, "randint", return_value=2):
                        self.attack(engine, target, route)
                    self.assertEqual(engine.player.fighter.hp,
                                     hp - (2 if suppression is None else 0))
                    messages = sum(m.count for m in engine.log.messages
                                   if m.text == "The briars find thee as thou strikest.")
                    self.assertEqual(messages, 1 if suppression is None else 0)

    def test_disconnect_suppresses_retaliation_and_disrupts_same_stable_type(self):
        engine, target, item, events = self.combat_case("briar_lurker")
        target.tile = "grass"
        same = engine.creature_factory.spawn("briar_lurker", 14, 12)
        same.tile = "stone_lurker"
        other = engine.creature_factory.spawn("hollow_revenant", 14, 13)
        other.tile = "grass"
        engine.entities.extend([same, other])
        hp = engine.player.fighter.hp
        with patch("engine.combat.resolve_attack", side_effect=self.contact(damage=1)):
            self.attack(engine, target, "moveset", engine.display.MOVESET_KEY_2)
        self.assertEqual(target._ability_suppressed_turns, 5)
        self.assertEqual(same._disrupted_turns, 3)
        self.assertEqual(getattr(other, "_disrupted_turns", 0), 0)
        self.assertEqual(engine.player.fighter.hp, hp)
        self.assertEqual(engine.moveset_cooldowns["disconnect"], 20)

    def test_real_resolver_integration_delivers_one_damage_hook_and_one_charge(self):
        for route in ("normal", "moveset"):
            with self.subTest(route=route):
                engine, target, item, events = self.combat_case("stone_lurker")
                engine.player.fighter.corruption_damage_bonus = 5
                engine.rng = random.Random(8)
                hp = target.fighter.hp
                self.attack(engine, target, route)
                damage = [payload for event, payload in events
                          if event == HookEvent.ON_DAMAGE_DEALT]
                self.assertEqual(len(damage), 1)
                self.assertGreater(damage[0]["damage"], 0)
                self.assertEqual(hp - target.fighter.hp, damage[0]["damage"])
                self.assertEqual(item.temporary_essence[0]["hits_remaining"], 2)
                self.assertEqual(damage[0]["essence"], "Dissolution")


if __name__ == "__main__":
    unittest.main()
