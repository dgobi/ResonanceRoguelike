"""Allocation regressions using real recipe JSON, ItemFactory, and inventory APIs.

Run with stdlib unittest. Set RESONANCE_GAME_ROOT when the game is elsewhere.
No game bootstrap, renderer, or saved campaign is used.
"""
from __future__ import annotations

import itertools
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


def game_root():
    configured = os.environ.get("RESONANCE_GAME_ROOT")
    if configured:
        return Path(configured)
    for parent in Path(__file__).resolve().parents:
        for relative in ("roguelike", "fullgame_review/roguelike"):
            candidate = parent / relative
            if (candidate / "engine/crafting.py").is_file():
                return candidate
    raise RuntimeError("Set RESONANCE_GAME_ROOT to the roguelike source directory")


GAME_ROOT = game_root()
sys.path.insert(0, str(GAME_ROOT))
from components.equipment import Equipment
from components.inventory import Inventory
from engine.crafting import attempt_craft, can_craft, commit_craft, plan_craft
from engine.item_factory import ItemFactory
from entities.item import Item


class CraftingAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        definitions = [json.loads(path.read_text(encoding="utf-8"))
                       for path in (GAME_ROOT / "data/items").rglob("*.json")]
        cls.data = SimpleNamespace(items={row["id"]: row for row in definitions})
        cls.factory = ItemFactory(cls.data)

    def recipe(self, name):
        return json.loads((GAME_ROOT / "data/recipes" / (name + ".json")).read_text(encoding="utf-8"))

    def item(self, item_id):
        item = self.factory.create(item_id)
        self.assertIsNotNone(item)
        return item

    @staticmethod
    def tagged(name, *tags, tier=1, consumed=True):
        item = Item(0, 0, "generic_item", name, name)
        item.keywords = [{"tag": tag, "tier": tier} for tag in tags]
        item.consumed_on_use = consumed
        return item

    @staticmethod
    def inventory(*items):
        inv = Inventory(100)
        inv.items = list(items)
        return inv

    def engine(self, inv):
        return SimpleNamespace(
            player=SimpleNamespace(inventory=inv, equipment=Equipment(), light_source=None),
            data=self.data,
        )

    def test_authored_hungering_oil_all_inventory_orders(self):
        recipe = self.recipe("hungering_oil")
        bile, viscera, irrelevant = (self.item(i) for i in
                                    ("crow_bile", "crude_viscera", "wood_bundle"))
        ambient = [{"tag": "burning", "tier": 2}, {"tag": "vessel", "tier": 1}]
        for order in itertools.permutations((bile, viscera, irrelevant)):
            with self.subTest(order=[i.item_id for i in order]):
                inv = self.inventory(*order)
                selected, missing = plan_craft(recipe, inv, ambient_sources=ambient)
                self.assertEqual([], missing)
                self.assertEqual([viscera, bile], selected)
                self.assertTrue(can_craft(recipe, inv, ambient_sources=ambient)[0])
                self.assertEqual(list(order), inv.items)

    def test_one_dual_tag_item_cannot_fill_two_physical_requirements(self):
        item = self.tagged("dual", "fuel", "cutting")
        item.count = 20  # This API's existing unit is an owned item instance.
        inv = self.inventory(item)
        recipe = {"components": [{"tag": "fuel"}, {"tag": "cutting"}]}
        self.assertFalse(can_craft(recipe, inv)[0])
        self.assertFalse(attempt_craft(recipe, inv))
        self.assertEqual([item], inv.items)

    def test_explicit_component_choice_is_not_silently_substituted(self):
        recipe = self.recipe("hungering_oil")
        bile, viscera, sulphur = (self.item(i) for i in
                                  ("crow_bile", "crude_viscera", "sulphur_cap_fragment"))
        ambient = [{"tag": "burning", "tier": 2}, {"tag": "vessel", "tier": 1}]
        selected, missing = plan_craft(recipe, self.inventory(bile, viscera),
                                      ambient_sources=ambient, chosen_items={0: "crow_bile"})
        self.assertTrue(missing)  # The requested bile cannot also supply caustic.
        selected, missing = plan_craft(recipe, self.inventory(sulphur, viscera, bile),
                                      ambient_sources=ambient, chosen_items={0: "crow_bile"})
        self.assertEqual([], missing)
        self.assertEqual([bile, sulphur], selected)
        self.assertEqual({0: "crow_bile"}, selected.choices)
        self.assertTrue(plan_craft(recipe, self.inventory(viscera, sulphur),
                                   ambient_sources=ambient, chosen_items={0: "crow_bile"})[1])

    def test_prefers_lowest_usable_tiers_without_inventory_order_ties(self):
        low_a = self.tagged("a", "fuel")
        low_b = self.tagged("b", "fuel")
        high = self.tagged("high", "fuel", tier=3)
        recipe = {"components": [{"tag": "fuel"}]}
        for order in itertools.permutations((high, low_b, low_a)):
            self.assertEqual([low_a], plan_craft(recipe, self.inventory(*order))[0])

    def test_quantity_and_reusable_tool_keep_distinct_owners(self):
        wood_a, wood_b, blade = (self.item(i) for i in
                                 ("wood_bundle", "wood_bundle", "crude_blade"))
        inv = self.inventory(blade, wood_b, wood_a)
        recipe = self.recipe("campfire")
        selected, missing = plan_craft(recipe, inv)
        self.assertEqual([], missing)
        self.assertEqual({id(i) for i in (wood_a, wood_b, blade)}, {id(i) for i in selected})
        self.assertTrue(attempt_craft(recipe, inv))
        self.assertEqual([blade], inv.items)

    def test_quantity_choice_requires_one_preferred_unit_and_uses_others(self):
        a, b = self.tagged("a", "fuel"), self.tagged("b", "fuel")
        recipe = {"components": [{"tag": "fuel", "quantity": 2}]}
        selected, missing = plan_craft(recipe, self.inventory(a, b), chosen_items={0: "b"})
        self.assertEqual([], missing)
        self.assertEqual([b, a], selected)

    def test_ambient_shortfall_does_not_steal_a_mandatory_material(self):
        dual = self.tagged("dual", "heat", "fuel")
        recipe = {"components": [{"tag": "heat"}, {"tag": "fuel"}]}
        selected, missing = plan_craft(recipe, self.inventory(dual),
                                      ambient_sources=[{"tag": "heat", "tier": 1}])
        self.assertEqual([], missing)
        self.assertEqual([dual], selected)

    def test_physical_materials_precede_ambient_shortfall_globally(self):
        dual = self.tagged("a_dual", "heat", "fuel")
        heat = self.tagged("b_heat", "heat")
        recipe = {"components": [{"tag": "heat"}, {"tag": "fuel"}]}
        selected, missing = plan_craft(recipe, self.inventory(dual, heat), ambient_sources=[
            {"tag": "heat", "tier": 1}, {"tag": "fuel", "tier": 1}])
        self.assertEqual([], missing)
        self.assertEqual([heat, dual], selected)

    def test_required_ambient_cannot_be_replaced_by_inventory(self):
        fire = self.tagged("fire", "burning", tier=3)
        recipe = {"requires_ambient": [{"tag": "burning", "min_tier": 2}]}
        selected, missing = plan_craft(recipe, self.inventory(fire))
        self.assertEqual([], selected)
        self.assertEqual([dict(tag="burning", min_tier=2, have=0, need=1, ambient=True)], missing)

    def test_single_item_conjunction_count_and_competing_component(self):
        dual = self.tagged("a_dual", "resonant", "edible", "solvent")
        herb = self.tagged("b_herb", "resonant", "edible")
        recipe = {"requires_single_item": [{"tag": "resonant"}, {"tag": "edible"}],
                  "components": [{"tag": "solvent"}]}
        self.assertEqual([herb, dual], plan_craft(recipe, self.inventory(dual, herb))[0])
        lone_resonance = self.tagged("resonance", "resonant")
        lone_food = self.tagged("food", "edible")
        self.assertFalse(can_craft(recipe, self.inventory(lone_resonance, lone_food, dual))[0])
        double = {"requires_single_item": {"tags": [{"tag": "resonant"}, {"tag": "edible"}],
                                           "max_quantity": 2}}
        self.assertFalse(can_craft(double, self.inventory(dual))[0])
        self.assertTrue(can_craft(double, self.inventory(dual, herb))[0])

    def test_stale_plan_and_output_capacity_fail_without_consuming(self):
        original, replacement, output = (self.item(i) for i in
                                         ("wood_bundle", "wood_bundle", "leather_jack"))
        inv = self.inventory(original)
        engine = self.engine(inv)
        recipe = {"components": [{"tag": "fuel"}]}
        selected, missing = plan_craft(recipe, inv)
        self.assertEqual([], missing)
        inv.items[:] = [replacement]
        self.assertFalse(commit_craft(engine, recipe, selected, outputs=[output]))
        self.assertEqual([replacement], inv.items)
        inv.items[:] = [original]
        inv.capacity = 0
        self.assertFalse(commit_craft(engine, recipe, selected, outputs=[output]))
        self.assertEqual([original], inv.items)
        inv.capacity = 100
        self.assertTrue(commit_craft(engine, recipe, selected, outputs=[output]))
        self.assertEqual([output], inv.items)

    def test_committed_choice_preserves_exact_tool_and_detaches_consumed_gear(self):
        blade = self.item("crude_blade")
        fuel = self.item("wood_bundle")
        extra = self.item("wood_bundle")
        inv = self.inventory(extra, blade, fuel)
        engine = self.engine(inv)
        engine.player.equipment.equip(blade, "weapon")
        recipe = {"components": [{"tag": "fuel"}, {"tag": "cutting"}]}
        selected, missing = plan_craft(recipe, self.inventory(fuel, blade), chosen_items={0: fuel.item_id})
        self.assertEqual([], missing)
        self.assertTrue(commit_craft(engine, recipe, selected))
        self.assertEqual([extra, blade], inv.items)
        self.assertIs(blade, engine.player.equipment.slots["weapon"])
        blade.consumed_on_use = True
        recipe = {"components": [{"tag": "cutting"}]}
        selected, missing = plan_craft(recipe, inv)
        self.assertEqual([], missing)
        self.assertFalse(attempt_craft(recipe, inv))  # No engine: cannot detach safely.
        self.assertTrue(commit_craft(engine, recipe, selected))
        self.assertEqual([extra], inv.items)
        self.assertFalse(blade.equipped)
        self.assertIsNone(engine.player.equipment.slots["weapon"])

    def test_duplicate_owned_instance_is_rejected(self):
        item = self.tagged("fuel", "fuel")
        inv = self.inventory(item, item)
        recipe = {"components": [{"tag": "fuel", "quantity": 2}]}
        self.assertFalse(attempt_craft(recipe, inv))
        self.assertEqual([item, item], inv.items)

    def test_small_allocations_against_exhaustive_independent_oracle(self):
        # All three-item/three-requirement tag graphs and ambient masks. The
        # oracle enumerates assignments, not the implementation's matching logic.
        recipe = {"components": [{"tag": str(n)} for n in range(3)]}
        assignments = list(itertools.product((0, 1, 2, None), repeat=3))
        for graph in range(1 << 9):
            items = [self.tagged(str(i), *(str(tag) for tag in range(3)
                                           if graph & (1 << (i * 3 + tag)))) for i in range(3)]
            for ambient_mask in range(8):
                best = -1
                for assignment in assignments:
                    physical = [i for i in assignment if i is not None]
                    if len(set(physical)) != len(physical):
                        continue
                    if all((ambient_mask & (1 << tag)) if item is None else
                           (graph & (1 << (item * 3 + tag)))
                           for tag, item in enumerate(assignment)):
                        best = max(best, len(physical))
                ambient = [{"tag": str(tag), "tier": 1} for tag in range(3)
                           if ambient_mask & (1 << tag)]
                order = list(reversed(items)) if graph & 1 else items
                selected, missing = plan_craft(recipe, self.inventory(*order), ambient_sources=ambient)
                self.assertEqual(best >= 0, not missing, (graph, ambient_mask, missing))
                if best >= 0:
                    self.assertEqual(best, len(selected), (graph, ambient_mask))
                    self.assertEqual(len(selected), len({id(i) for i in selected}))


if __name__ == "__main__":
    unittest.main()
