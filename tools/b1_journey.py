"""Bounded original Engine.run driver, exclusively Pygame's own event queue."""
from __future__ import annotations
import time
from pathlib import Path
from b1_support import gear, hashes, read, scene_state, seed_runtime
from b1_cases import setup_gear
from b1_characterize import needs_state


def run_journey(ev, custom_actions=None):
    import pygame
    from engine.engine import Engine
    from engine.save_manager import SaveManager
    from engine.debug import DebugOverlay
    import main
    variant = ev.job["variant"]
    original_run, original_get = Engine.run, pygame.event.get
    original_save, original_load = SaveManager.save, SaveManager.load
    original_configure = Engine._configure_player_needs
    tele, state_dump = DebugOverlay._teleport_to_nearest_submap, DebugOverlay._dump_state
    current, counters = {}, {"save": 0, "load": 0, "configure": 0, "teleport": 0, "dump": 0}
    started = time.monotonic()
    frame, sent, done = 0, 0, False
    out = Path(ev.job["result"]).parent
    def save(sm, e):
        counters["save"] += 1
        result = original_save(sm, e)
        # Captured at return from the real writer; no traversal in between.
        ev.record["checkpoint"] = hashes(sm.save_path)
        ev.record["expected"] = {"gear": gear(e), "address": [e.world_x, e.world_y, e.current_submap_id],
                                 "scene": scene_state(e.local_map, e.entities), "turn": e.world_time.turn}
        return result
    def load(sm, e):
        counters["load"] += 1
        return original_load(sm, e)
    def configure(e):
        counters["configure"] += 1
        return original_configure(e)
    def teleport(debug, e):
        counters["teleport"] += 1
        return tele(debug, e)
    def dumped(debug, e):
        counters["dump"] += 1
        return state_dump(debug, e)
    SaveManager.save, SaveManager.load = save, load
    Engine._configure_player_needs = configure
    DebugOverlay._teleport_to_nearest_submap, DebugOverlay._dump_state = teleport, dumped

    def key(k, unicode="", mods=0):
        return {"key": k, "unicode": unicode, "mod": mods}
    def capture(name):
        path = out / (name + ".png")
        pygame.image.save(pygame.display.get_surface(), str(path))
        ev.record.setdefault("captures", []).append(str(path))
    def setup(e, description):
        ev.record.setdefault("fixture_setup", []).append(description)
    def position(e, x, y):
        setup(e, f"Place player at walkable fixture ({x},{y}); clear nearby decor")
        e.player.x, e.player.y = x, y
        for tx in range(x-1, x+2):
            for ty in range(y-1, y+2):
                if e.local_map.in_bounds(tx, ty):
                    e.local_map.set_tile(tx, ty, "flagstone", True, True)
                    e.local_map.decor.pop((tx, ty), None)
        e._update_fov()
    def choose_inventory(e, item):
        for _ in range(60):
            if e.inventory_screen._selected_item() is item:
                return
            index = next(n for n, row in enumerate(e.inventory_screen._flat) if row[0] is item)
            yield key(pygame.K_DOWN if e.inventory_screen.selected < index else pygame.K_UP)
        raise AssertionError("Inventory selection event budget")

    def actions(e):
        if custom_actions is not None:
            yield from custom_actions(e, key, capture, choose_inventory)
            return
        if ev.job["phase"] == "read":
            expected = read(ev.job["expected"])["expected"]
            ev.check("E02", "fresh-process bootstrap exact gear", expected["gear"], gear(e))
            ev.check("E02", "fresh-process address", expected["address"], [e.world_x, e.world_y, e.current_submap_id])
            ev.check("E02", "fresh-process scene", expected["scene"], scene_state(e.local_map, e.entities))
            ev.check("E02", "fresh-process turn", expected["turn"], e.world_time.turn)
            yield None  # allow one original render
            capture("fresh-bootstrap")
            return
        if variant == "movement":
            ev.check("E01", "new lab", "sub_0_64_0", e.current_submap_id)
            turn = e.world_time.turn
            yield key(pygame.K_UP)
            ev.check("E01", "ordinary move", [15, 19, turn+1], [e.player.x, e.player.y, e.world_time.turn])
            yield key(pygame.K_DOWN)
            yield key(pygame.K_z, "z")
            ev.check("E01", "move back and wait", [15, 20, turn+3], [e.player.x, e.player.y, e.world_time.turn])
            yield key(pygame.K_i, "i")
            ev.check("E01", "inventory opens without turn", [True, turn+3], [e.inventory_screen.open, e.world_time.turn])
            capture("inventory")
            yield key(pygame.K_i, "i")
            ev.check("E01", "inventory modal closes without turn", [False, turn+3], [e.inventory_screen.open, e.world_time.turn])
            capture("laboratory")
            yield key(pygame.K_w, "W", pygame.KMOD_SHIFT)
            ev.check("E01", "get_mods branch activates sprint without a turn", [e.display.SPRINT_DURATION, turn+3],
                     [e.sprint_turns_remaining, e.world_time.turn])
        elif variant == "transfer":
            e.entities = [e.player]
            position(e, 20, 20)
            item = e.item_factory.create("crude_blade", 20, 20)
            e.local_map.floor_objects[(20, 20)] = [item]
            setup(e, "Factory crude_blade placed on floor at player; normal starting bag retained")
            turn = e.world_time.turn
            yield key(pygame.K_COMMA, ",")
            ev.check("E04", "pickup actual item and one turn", True,
                     any(i is item for i in e.player.inventory.items) and item not in e.local_map.floor_objects.get((20, 20), []) and e.world_time.turn == turn+1)
            yield key(pygame.K_i, "i")
            yield from choose_inventory(e, item)
            yield key(pygame.K_RETURN, "\r")
            ev.check("E04", "UI equips exact picked-up blade", True, e.player.equipment.slots["weapon"] is item and item.equipped)
            ev.check("E04", "equip turn cost", turn+2, e.world_time.turn)
            yield key(pygame.K_d, "d")
            ev.check("E04", "drop moves exact object to floor", True, item not in e.player.inventory.items and any(i is item for i in e.local_map.floor_objects[(20, 20)]))
            ev.check("E04", "drop turn cost", turn+3, e.world_time.turn)
            ev.check("E04", "equipped drop clears slot and flag", [None, False], [e.player.equipment.slots["weapon"], item.equipped])
            ev.check("E04", "dropped equipment permits a coherent save", True, e.save_manager.save(e))
            capture("dropped-equipped-blade")
            yield key(pygame.K_i, "i")
        elif variant == "combat":
            e.entities = [e.player]
            position(e, 20, 20)
            actor = e.creature_factory.spawn("hollow_revenant", 21, 20)
            actor.name = "B1 ordinary combat fixture"
            e.entities.append(actor)
            setup(e, "Ordinary hollow_revenant adjacent; unarmed starter player, no debug weapon or stat boost")
            hp, turn = actor.fighter.hp, e.world_time.turn
            for attempt in range(8):
                yield key(pygame.K_RIGHT)
                if actor.fighter.hp < hp:
                    break
            ev.check("E04", "ordinary bump causes damage", True, actor.fighter.hp < hp)
            ev.check("E04", "ordinary attack advances turns", True, e.world_time.turn > turn)
            ev.record["combat"] = {"target": actor._creature_id, "before_hp": hp, "after_hp": actor.fighter.hp, "turns": e.world_time.turn-turn}
            capture("ordinary-combat")
        elif variant == "text":
            e.entities = [e.player]
            candidates = [(pos, i) for pos, items in e.local_map.floor_objects.items() for i in items if i.text_id == "lab_label_sarcophagus"]
            ev.check("E04", "existing bound lab document found", True, bool(candidates))
            pos, item = candidates[0]
            setup(e, f"Move player to existing authored lab document at {pos}; no document insertion")
            e.player.x, e.player.y = pos
            e._update_fov()
            yield key(pygame.K_COMMA, ",")
            ev.check("E04", "bound document picked up", True, item in e.player.inventory.items)
            yield key(pygame.K_i, "i")
            yield from choose_inventory(e, item)
            turn = e.world_time.turn
            yield key(pygame.K_RETURN, "\r")
            ev.check("E04", "actual reader opens bound text", [True, "lab_label_sarcophagus"], [e.text_reader.open, e.text_reader._text_id])
            ev.check("E04", "reader contains definition body", e.data.texts[item.text_id]["pages"], e.text_reader._def["pages"])
            ev.check("E04", "read use advances one turn", turn+1, e.world_time.turn)
            capture("lab-document")
            ev.record["reader"] = {"text_id": item.text_id, "pages": e.text_reader._def["pages"], "surface_clip": list(pygame.display.get_surface().get_clip())}
            reader = e.text_reader
            seen = set(reader._visible_rows)
            for _ in range(100):
                if reader._scroll == reader._max_scroll:
                    break
                yield key(pygame.K_PAGEDOWN)
                seen.update(reader._visible_rows)
            drawn = "".join(f["text"] for row in reader._layout_rows for f in row)
            ev.check("E04", "complete warning accessible through bounded reader navigation", True,
                     "do not ring the bells." in drawn and seen == set(range(len(reader._layout_rows))))
            ev.check("E04", "reader navigation spends no further turns", turn+1, e.world_time.turn)
            yield key(pygame.K_ESCAPE)
            ev.check("E04", "reader closes", False, e.text_reader.open)
        elif variant == "processing":
            e.entities = [e.player]
            position(e, 20, 20)
            herb = e.item_factory.create("bitter_herb")
            assert e.player.inventory.add(herb)
            from generation.decor_utils import place_decor
            place_decor(e.local_map, 21, 20, "campfire_lit")
            setup(e, "Acquire one factory bitter_herb; place lit campfire at (21,20) for supported burning ambient; no result item inserted")
            turn = e.world_time.turn
            yield key(pygame.K_c, "c")
            for _ in range(80):
                flat = e.craft_screen._build_flat_items(e.craft_screen._get_recipes(e))
                index = next(n for n, row in enumerate(flat) if row.get("recipe", {}).get("id") == "dry_bitter_herb")
                if e.craft_screen.selected == index:
                    break
                yield key(pygame.K_DOWN if e.craft_screen.selected < index else pygame.K_UP)
            else:
                raise AssertionError("craft selection budget")
            yield key(pygame.K_RETURN, "\r")
            ev.check("E04", "recipe enters placement", "placement_cursor", e.mode.value)
            yield key(pygame.K_RETURN, "\r")
            ev.check("E04", "ingredient consumed by actual craft", False, herb in e.player.inventory.items)
            ev.check("E04", "processing placed", 1, len(e.local_map.processing_layer))
            ev.check("E04", "placement one turn", turn+1, e.world_time.turn)
            placement = next(iter(e.local_map.processing_layer))
            capture("processing-start")
            for _ in range(25):
                if not e.local_map.processing_layer:
                    break
                yield key(pygame.K_z, "z")
            ev.check("E04", "bounded processing finished", {}, e.local_map.processing_layer)
            outputs = [i.item_id for i in e.local_map.floor_objects.get(placement, [])]
            ev.check("E04", "crafted output at placement", ["dried_bitter_herb"], outputs)
            ev.check("E04", "processing total turns", turn+20, e.world_time.turn)
            ev.record["craft"] = {"ingredient": "bitter_herb", "output": outputs, "placement": list(placement), "turns": e.world_time.turn-turn}
            capture("processing-complete")
        elif variant == "stairs":
            sid, turn = e.current_submap_id, e.world_time.turn
            # Initial player_start is on the authored stairs_up for this seed.
            yield key(pygame.K_COMMA, "<", pygame.KMOD_SHIFT)
            ev.check("E01", "Unicode ascent", None, e.current_submap_id)
            ev.check("E01", "surface visible", True, bool(e.local_map.visible.any()))
            capture("surface")
            yield key(pygame.K_PERIOD, ">", pygame.KMOD_SHIFT)
            ev.check("E01", "Unicode descent", sid, e.current_submap_id)
            ev.check("E01", "lab visible and current stair turn policy", [True, turn], [bool(e.local_map.visible.any()), e.world_time.turn])
        elif variant == "boundary":
            e._ascend_from_submap()
            e.entities = [e.player]
            from world.local_map import LocalMap
            from config import MAP_WIDTH, MAP_HEIGHT
            destination = LocalMap(MAP_WIDTH, MAP_HEIGHT)
            destination.set_tile(0, 20, "grass", True, True)
            e.save_manager.cache.store(e.world_x+1, e.world_y, destination, [])
            position(e, MAP_WIDTH-1, 20)
            setup(e, "Near east boundary; neighbor persisted with walkable (0,20); actual crossing uses right movement")
            wx, wy, turn = e.world_x, e.world_y, e.world_time.turn
            yield key(pygame.K_RIGHT)
            ev.check("E04", "ordinary boundary crossing", [wx+1, wy, 0, 20], [e.world_x, e.world_y, e.player.x, e.player.y])
            ev.check("S03", "empty destination keeps exactly player", [e.player.name], [a.name for a in e.entities])
            ev.check("S03", "empty destination floor stays empty", {}, e.local_map.floor_objects)
            ev.check("E04", "boundary turn advances", True, e.world_time.turn > turn)
            capture("surface-boundary")
        elif variant == "debug":
            ev.check("E03", "unchanged debug config", True, e.debug is not None)
            yield key(pygame.K_F5)
            ev.check("E03", "F5 teleports", 1, counters["teleport"])
            yield key(pygame.K_F9)
            ev.check("E03", "F9 dumps", 1, counters["dump"])
            ev.check("E03", "debug keys never count as save/load", [0, 0], [counters["save"], counters["load"]])
        elif variant in ("nondebug", "needs_f9"):
            ev.check("E02" if variant == "nondebug" else "B01", "process-local DEBUG_MODE=False", None, e.debug)
            e.entities = [e.player]
            if variant == "needs_f9":
                e._ascend_from_submap()
                e.player.needs.hunger = 0.2
            else:
                setup_gear(e, "second")
                surface = e.save_manager.cache.load(e.world_x, e.world_y).local_map
                surface.set_tile(3, 3, "grass", True, True)
                e.save_manager.cache.store(e.world_x, e.world_y, surface, [])
                e.local_map.set_tile(3, 3, "flagstone", True, True)
            setup(e, "Persist controlled scene and gear through actual nondebug F5 event")
            yield key(pygame.K_F5)
            expected = gear(e)
            e.local_map.set_tile(3, 3, "mud", True, True)
            e.player.inventory.items.append(e.item_factory.create("crow_jerky"))
            configured = counters["configure"]
            yield key(pygame.K_F9)
            ev.check("B01", "F9 invokes Needs reconfiguration", configured+1, counters["configure"])
            ev.check("B01", "F9 Needs configured", True, e.player.needs._configured)
            ev.record["needs_f9"] = needs_state(e)
            if variant == "needs_f9":
                ev.check("B01", "F9 uses configured label", "Sated", e.player.needs.hunger_state)
                return
            ev.check("E02", "hotkeys reached actual save/load", [1, 1], [counters["save"], counters["load"]])
            ev.check("E02", "F9 exact duplicate gear", expected, gear(e))
            ev.check("E02", "F9 persisted map", "flagstone", str(e.local_map.tiles[3, 3]["terrain"]))
            yield key(pygame.K_COMMA, "<", pygame.KMOD_SHIFT)
            ev.check("E02", "paired surface survives", "grass", str(e.local_map.tiles[3, 3]["terrain"]))
            yield key(pygame.K_PERIOD, ">", pygame.KMOD_SHIFT)
            ev.check("E02", "paired lab survives", "flagstone", str(e.local_map.tiles[3, 3]["terrain"]))
            yield key(pygame.K_F5)  # final terminal writer for a fresh bootstrap
            capture("saved-duplicate-torch")
        else:
            raise ValueError(variant)

    def run(e):
        current["engine"] = e
        seed_runtime(e)
        current["turn_start"] = e.world_time.turn
        current["actions"] = actions(e)
        return original_run(e)

    def events(*args, **kwargs):
        nonlocal frame, sent, done
        e = current["engine"]
        if frame > 200 or time.monotonic()-started > 90 or e.world_time.turn-current["turn_start"] > 80:
            raise AssertionError("Journey frame/time/turn budget exceeded")
        ev.check("H02", "original loop dummy SDL", "dummy", pygame.display.get_driver())
        ev.check("E01", "paired release prevents repeats", None, e._held_key)
        ev.record["trace"].append({"frame": frame, "position": [e.player.x,e.player.y],
             "scene": [e.world_x,e.world_y,e.current_submap_id], "turn":e.world_time.turn,
             "mode": e.mode.value, "inventory":e.inventory_screen.open, "text":e.text_reader.open,
             "counters":dict(counters)})
        try:
            action = next(current["actions"])
        except StopIteration:
            done = True
            pygame.key.set_mods(0)
            ev.check("E01", "QUIT accepted", True, pygame.event.post(pygame.event.Event(pygame.QUIT)))
        else:
            if action is not None:
                pygame.key.set_mods(action["mod"])
                ev.record["trace"][-1]["event"] = {**action, "actual_mods": pygame.key.get_mods()}
                ev.check("E01", "app-local modifier state", action["mod"], pygame.key.get_mods())
                for kind in (pygame.KEYDOWN, pygame.KEYUP):
                    ev.check("E01", "event accepted", True, pygame.event.post(pygame.event.Event(kind, **action)))
                sent += 1
        frame += 1
        return original_get(*args, **kwargs)
    Engine.run, pygame.event.get = run, events
    try:
        main.main()
    except SystemExit as error:
        if not done or error.code not in (None, 0):
            raise
    finally:
        Engine.run, pygame.event.get = original_run, original_get
        SaveManager.save, SaveManager.load = original_save, original_load
        Engine._configure_player_needs = original_configure
        DebugOverlay._teleport_to_nearest_submap, DebugOverlay._dump_state = tele, state_dump
        if pygame.get_init():
            pygame.key.set_mods(0)
            pygame.event.clear()
        pygame.quit()
    ev.check("E01", "original loop completed bounded driver", True, done and frame > 0)
    ev.record.update(frames=frame, actions=sent, counters=counters,
                     elapsed_seconds=time.monotonic()-started, evidence_class="Original Engine.run, real event.post/get, original handlers and renderer")
