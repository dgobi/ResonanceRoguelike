"""Reproduce Arc A persistence observations with real imported game components.

Evidence class: actual-component / explicit-minimal-host. This script does NOT
bootstrap main.main, construct a full Engine, run its input/render loop, or prove
whole-slot persistence. It imports the real serializers, factories, components
and creature ability; the host supplies only the fields those calls need. Its
FOV callback records a call but does not compute visibility.

Only a private temporary ChunkCache is written. No game/personal save slot is
opened. The project may be either a repository root containing roguelike/ or the
roguelike directory itself. Output is JSON on stdout unless --output is given.

Example (use the project's installed Python environment):
    python persistence_component_probes.py --project /path/to/project \
        --output /path/to/evidence/component-probes.json --assert-baseline

--assert-baseline checks the *known failing-before observations*. Its success
must not be presented as B1 acceptance. Run without that flag to collect changed
observations on a candidate; use the separate B1 suite for acceptance.

This retained harness was reconstructed from the recorded component observations
and rechecked against the reviewed baseline. It is not a claim that the original
interactive heredoc was retained verbatim.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import traceback
from types import SimpleNamespace


class ProbeLog:
    """Minimal log sink; it records messages and supplies no gameplay behavior."""

    def __init__(self):
        self.messages = []

    def add(self, message, *args, **kwargs):
        self.messages.append(str(message))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_game(project: Path) -> Path:
    project = project.resolve()
    game = project / "roguelike" if (project / "roguelike").is_dir() else project
    for relative in ("engine/save_manager.py", "engine/data_loader.py", "data/items"):
        if not (game / relative).exists():
            raise ValueError(f"Not a game project: missing {game / relative}")
    return game


def load_components(game: Path):
    # No display is initialized, but keep any imported SDL-related code headless.
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    sys.path.insert(0, str(game))

    from components.equipment import Equipment
    from components.fighter import Fighter
    from components.inventory import Inventory
    from engine.creature_abilities import _ability_stone_lurker
    from engine.creature_factory import CreatureFactory
    from engine.data_loader import DataLoader
    from engine.item_factory import ItemFactory
    from engine.item_system import ItemSystem
    from engine import save_manager
    from entities.actor import Actor
    from world.local_map import LocalMap

    data = DataLoader(str(game / "data"))
    return SimpleNamespace(
        Equipment=Equipment, Fighter=Fighter, Inventory=Inventory,
        ability=_ability_stone_lurker, CreatureFactory=CreatureFactory,
        ItemFactory=ItemFactory, ItemSystem=ItemSystem,
        Actor=Actor, LocalMap=LocalMap, saves=save_manager, data=data,
    )


def make_host(api):
    player = api.Actor(x=0, y=0, tile="player", name="Player")
    player.fighter = api.Fighter(max_hp=60, power=5, defense=1)
    player.fighter.body_id = "body_player"
    player.inventory = api.Inventory(capacity=20.0)
    player.equipment = api.Equipment()
    host = SimpleNamespace(
        player=player, data=api.data, log=ProbeLog(),
        world_x=0, world_y=64, current_submap_id="sub_0_64_0",
        surface_return_x=10, surface_return_y=10,
        world_time=SimpleNamespace(turn=480),
        resonance_exposure=0.0, corruption=0.0,
        _live_pursuers=[], _pending_pursuer_arrivals=[], fov_callback_calls=0,
    )

    def record_fov_request():
        host.fov_callback_calls += 1

    host._update_fov = record_fov_request
    return host


def require_item(api, item_id):
    item = api.ItemFactory(api.data).create(item_id)
    if item is None:
        raise RuntimeError(f"Required real item definition missing: {item_id}")
    return item


def require_lurker(api):
    actor = api.CreatureFactory(api.data).spawn(
        "stone_lurker", 60, 30, rng=random.Random(20261020)
    )
    if actor is None:
        raise RuntimeError("Required real stone_lurker definition missing")
    return actor


def cache_probe(api, scratch_parent):
    with tempfile.TemporaryDirectory(
        prefix="arc-a-component-cache-", dir=scratch_parent
    ) as temp:
        cache = api.saves.ChunkCache(Path(temp))
        local_map = api.LocalMap(8, 8)
        local_map.set_tile(3, 3, "grass", True, True)
        cache.store(0, 64, local_map, [])
        cache_file = cache._chunk_path(0, 64)
        saved_hash = digest(cache_file)

        local_map.set_tile(3, 3, "flagstone", True, True)
        hot = cache.load(0, 64)
        cold = api.saves.ChunkCache(Path(temp)).load(0, 64)
        if hot is None or cold is None:
            raise RuntimeError("Real ChunkCache could not read its private fixture")
        return {
            "saved_marker": "grass",
            "mutated_active_marker": str(local_map.tiles[3, 3]["terrain"]),
            "same_cache_load_marker": str(hot.local_map.tiles[3, 3]["terrain"]),
            "fresh_cache_load_marker": str(cold.local_map.tiles[3, 3]["terrain"]),
            "hot_alias_same_object": hot.local_map is local_map,
            "disk_unchanged": digest(cache_file) == saved_hash,
        }


def lurker_state(actor):
    return {
        "tile": actor.tile,
        "hibernating": getattr(actor, "_hibernating", None),
        "ai_triggered": getattr(actor.ai, "_triggered", None),
        "ambush_ready": getattr(actor, "_ambush_ready", None),
    }


def lurker_probes(api):
    host = make_host(api)
    dormant = require_lurker(api)
    api.ability(dormant, host)
    dormant_payload = api.saves._serialize_entity(dormant)
    restored_dormant = api.saves._deserialize_entities([dormant_payload], host)
    dormant_result = {
        "stable_id": dormant._creature_id,
        "tile": dormant.tile,
        "hibernating": dormant._hibernating,
        "serialized_id": dormant_payload["id"],
        "restored_count": len(restored_dormant),
    }

    awake = require_lurker(api)
    awake._hibernating = False
    awake._ambush_ready = False
    awake.ai._triggered = True
    before = lurker_state(awake)
    awake_payload = api.saves._serialize_entity(awake)
    restored_awake = api.saves._deserialize_entities([awake_payload], host)
    if len(restored_awake) != 1:
        raise RuntimeError("Awake control did not reconstruct exactly one actor")
    actor = restored_awake[0]
    restored_before_tick = lurker_state(actor)
    api.ability(actor, host)
    awake_result = {
        "before": before,
        "restored_before_tick": restored_before_tick,
        "restored_after_distant_ability_tick": lurker_state(actor),
    }
    return dormant_result, awake_result


def player_probes(api):
    empty_host = make_host(api)
    empty_serialized = api.saves._serialize_player(empty_host)["inventory"]

    saved_host = make_host(api)
    saved_host.player.inventory.add(require_item(api, "crow_jerky"))
    saved_payload = api.saves._serialize_player(saved_host)

    prior_host = make_host(api)
    prior_torch = require_item(api, "tallow_torch")
    prior_host.player.inventory.add(prior_torch)
    # Real item-use route; the host's visibility callback is explicitly minimal.
    api.ItemSystem().use(prior_torch, prior_host)
    api.saves._deserialize_player(saved_payload, prior_host)
    restored_player = prior_host.player
    light = restored_player.light_source
    offhand = restored_player.equipment.slots.get("offhand")
    light_ref = getattr(light, "_item_ref", None)
    ghost_result = {
        "saved_light_source": saved_payload["light_source"],
        "saved_offhand": saved_payload["equipment"]["offhand"],
        "restored_inventory": [i.item_id for i in restored_player.inventory.items],
        "restored_offhand": offhand.item_id if offhand is not None else None,
        "light_still_active": bool(light is not None and light.active),
        "light_ref_is_prior_item": light_ref is prior_torch,
        "light_item_owned": any(light_ref is i for i in restored_player.inventory.items),
    }

    duplicate_host = make_host(api)
    first = require_item(api, "tallow_torch")
    second = require_item(api, "tallow_torch")
    first.turns_lit, second.turns_lit = 10, 90
    duplicate_host.player.inventory.add(first)
    duplicate_host.player.inventory.add(second)
    duplicate_host.player.equipment.equip(second, "offhand")
    duplicate_payload = api.saves._serialize_player(duplicate_host)
    reader_host = make_host(api)
    api.saves._deserialize_player(duplicate_payload, reader_host)
    items = reader_host.player.inventory.items
    equipped = reader_host.player.equipment.slots.get("offhand")
    duplicate_result = {
        "saved_equipped_turns_lit": second.turns_lit,
        "restored_inventory_turns_lit": [i.turns_lit for i in items],
        "restored_equipped_turns_lit": equipped.turns_lit if equipped else None,
        "equipped_is_restored_first_item": bool(items and equipped is items[0]),
    }
    return {
        "empty_inventory_serialized": empty_serialized,
        "ghost_light_and_equipment": ghost_result,
        "duplicate_definition_items": duplicate_result,
    }


def baseline_checks(result):
    observations = result["observations"]
    cache = observations["cache_alias"]
    dormant = observations["dormant_lurker"]
    awake = observations["awake_lurker"]
    player = observations["player"]
    pairs = [
        ("hot cache retains unsaved marker", "flagstone", cache["same_cache_load_marker"]),
        ("cold cache reads saved marker", "grass", cache["fresh_cache_load_marker"]),
        ("hot map aliases active map", True, cache["hot_alias_same_object"]),
        ("memory edit does not change disk", True, cache["disk_unchanged"]),
        ("dormant definition becomes presentation", "rock", dormant["serialized_id"]),
        ("dormant actor is dropped", 0, dormant["restored_count"]),
        ("awake state absent after reconstruction", None, awake["restored_before_tick"]["hibernating"]),
        ("awake trigger resets", False, awake["restored_before_tick"]["ai_triggered"]),
        ("distant next tick rehibernates", True, awake["restored_after_distant_ability_tick"]["hibernating"]),
        ("empty inventory serializes null", None, player["empty_inventory_serialized"]),
        ("ghost light retains unowned prior item", [True, True, False], [
            player["ghost_light_and_equipment"]["light_still_active"],
            player["ghost_light_and_equipment"]["light_ref_is_prior_item"],
            player["ghost_light_and_equipment"]["light_item_owned"],
        ]),
        ("duplicate slot selects first matching definition", 10,
         player["duplicate_definition_items"]["restored_equipped_turns_lit"]),
    ]
    return [{"observation": name, "expected_baseline": expected,
             "actual": actual, "baseline_reproduced": actual == expected}
            for name, expected, actual in pairs]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Optional JSON destination; default stdout")
    parser.add_argument("--scratch-dir", type=Path, help="Optional parent for a cleaned private temp cache")
    parser.add_argument("--assert-baseline", action="store_true")
    args = parser.parse_args()
    game = resolve_game(args.project)
    if args.scratch_dir and not args.scratch_dir.is_dir():
        parser.error("--scratch-dir must already be an existing directory")
    result = {
        "evidence_class": "actual-component / explicit-minimal-host; not full Engine bootstrap or input loop",
        "purpose": "Reproduce diagnostic baseline observations; not B1 acceptance",
        "python": sys.version,
        "project": str(game),
        "harness_completed": False,
        "limitations": [
            "Minimal host supplies only directly accessed fields, a message sink and a recorded FOV callback.",
            "No visibility, whole-save, bootstrap, event-loop or gameplay-journey guarantee.",
            "Only a cleaned private temporary cache is written; no project save slots are read.",
        ],
        "source_hashes": {},
        "versions": {},
    }
    source_paths = [
        "engine/save_manager.py", "engine/creature_factory.py",
        "engine/creature_abilities.py", "engine/item_factory.py",
        "engine/item_system.py", "engine/data_loader.py", "components/ai.py",
        "components/equipment.py", "components/inventory.py",
        "components/fighter.py", "world/local_map.py", "entities/actor.py",
    ]
    result["source_hashes"] = {relative: digest(game / relative) for relative in source_paths}
    result["probe_source_sha256"] = digest(Path(__file__))
    for name in ("pygame", "numpy", "tcod"):
        try:
            result["versions"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result["versions"][name] = None
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            api = load_components(game)
            cache = cache_probe(api, args.scratch_dir)
            dormant, awake = lurker_probes(api)
            player = player_probes(api)
        result["observations"] = {
            "cache_alias": cache, "dormant_lurker": dormant,
            "awake_lurker": awake, "player": player,
        }
        result["imported_module_origins"] = {
            name: str(Path(sys.modules[name].__file__).resolve())
            for name in ("engine.save_manager", "engine.creature_factory",
                         "engine.creature_abilities", "engine.item_system",
                         "components.inventory", "world.local_map")
        }
        for origin in result["imported_module_origins"].values():
            if not Path(origin).is_relative_to(game):
                raise RuntimeError(f"Imported source outside requested project: {origin}")
        result["harness_completed"] = True
        result["baseline_checks"] = baseline_checks(result)
        result["known_baseline_reproduced"] = all(
            check["baseline_reproduced"] for check in result["baseline_checks"]
        )
    except Exception as error:
        result["error"] = repr(error)
        result["traceback"] = traceback.format_exc()
    result["captured_game_stdout"] = captured.getvalue()
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        print(json.dumps({"output": str(args.output.resolve()),
                          "harness_completed": result["harness_completed"],
                          "known_baseline_reproduced": result.get("known_baseline_reproduced")}))
    else:
        print(encoded, end="")
    if not result["harness_completed"]:
        return 1
    if args.assert_baseline and not result["known_baseline_reproduced"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
