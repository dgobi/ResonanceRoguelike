"""Real Engine.run, Pygame event.post/get and renderer, entirely offscreen."""
import copy
from pathlib import Path
import time
from b1_support import gear, hashes, read, seed_runtime
from b2_cases import component_snapshot, setup_components, quiet, plain


def state(e):
    return {"components": component_snapshot(e), "gear": gear(e),
            "address": [e.world_x, e.world_y, e.current_submap_id],
            "weather": e.weather.to_dict(),
            "processing": {str(k): dict(v) for k, v in e.local_map.processing_layer.items()}}


def run_journey(ev):
    import pygame
    import main
    from engine.engine import Engine
    from engine.save_manager import SaveManager
    run, get = Engine.run, pygame.event.get
    save, load = SaveManager.save, SaveManager.load
    counters = {"save": 0, "load": 0}
    current = {}
    frames, done = 0, False
    started = time.monotonic()
    variant = ev.job["variant"]
    def saved(sm, e):
        value = save(sm, e)
        counters["save"] += 1
        ev.record["checkpoint"] = hashes(sm.save_path)
        ev.record["expected"] = state(e)
        return value
    def loaded(sm, e):
        counters["load"] += 1
        return load(sm, e)
    def key(k, unicode="", mod=0):
        return {"key": k, "unicode": unicode, "mod": mod}
    def capture(name):
        path = Path(ev.job["result"]).parent / (name + ".png")
        pygame.image.save(pygame.display.get_surface(), str(path))
        ev.record.setdefault("captures", []).append(str(path))
    def select(e, item):
        for _ in range(40):
            if e.inventory_screen._selected_item() is item:
                return
            index = next(n for n, row in enumerate(e.inventory_screen._flat) if row[0] is item)
            yield key(pygame.K_DOWN if e.inventory_screen.selected < index else pygame.K_UP)
        raise AssertionError("Inventory selection budget")
    def actions(e):
        ev.check("B2-08", "test-local nondebug configuration", None, e.debug)
        if ev.job["phase"] == "read":
            expected = read(ev.job["expected"])["expected"]
            ev.check("B2-08", "fresh bootstrap exact component, gear and processing state", expected, state(e))
            yield None
            capture("fresh-" + variant)
            if variant == "effects":
                old = e.player.fighter.hp
                turns = e.player_speed_bonus_turns
                yield key(pygame.K_z, "z")
                ev.check("B2-08", "first real wait consumes restored duration", turns-1, e.player_speed_bonus_turns)
                ev.check("B2-08", "first real wait applies healing hook once", min(e.player.fighter.max_hp, old+1), e.player.fighter.hp)
                for _ in range(turns-1):
                    yield key(pygame.K_z, "z")
                ev.check("B2-08", "used salve expires on restored schedule", [0, 0.0], [e.player_speed_bonus_turns, e.player_speed_bonus])
                # Place one difficult tile, then use ordinary movement to prove
                # the restored tile-entered perk affects the actual action path.
                e.local_map.set_tile(e.player.x+1, e.player.y, "mud", True, True)
                e.local_map.decor.pop((e.player.x+1, e.player.y), None)
                e._move_debt = 0.0
                old_turn, old_x = e.world_time.turn, e.player.x
                yield key(pygame.K_RIGHT)
                ev.check("B2-08", "restored Hardened Step changes real mud movement", [old_x+1, old_turn+1, 0.7],
                         [e.player.x, e.world_time.turn, round(e._move_debt, 6)])
            elif variant == "needs":
                hp, turn = e.player.fighter.hp, e.world_time.turn
                yield key(pygame.K_z, "z")
                ev.check("B2-08", "configured critical needs drain real wait", [turn+1, hp-3, "Collapsing", "Desiccating"],
                         [e.world_time.turn, e.player.fighter.hp, e.player.needs.hunger_state, e.player.needs.thirst_state])
            elif variant == "rain":
                old_weather = e.weather.turns_remaining
                yield key(pygame.K_z, "z")
                ev.check("B2-08", "rain resumes at final collection wait", [0, 0, 1, old_weather-1],
                         [e.rain_collection_progress, sum(i.item_id == "empty_water_skin" for i in e.player.inventory.items),
                          sum(i.item_id == "water_skin" for i in e.player.inventory.items), e.weather.turns_remaining])
            elif variant == "processing":
                yield key(pygame.K_z, "z")
                ev.check("B2-08", "processing first real wait", 1, e.local_map.processing_layer[(6, 6)]["turns_remaining"])
                yield key(pygame.K_z, "z")
                ev.check("B2-08", "processing completes on second real wait", [False, ["dried_bitter_herb"]],
                         [(6, 6) in e.local_map.processing_layer, [i.item_id for i in e.local_map.floor_objects[(6, 6)]]])
            capture("after-" + variant)
            return
        ev.record["fixture_setup"] = ["No hostiles; controlled status/component values on a walkable lab tile. Real UI, waits and F5/F9 are outcomes."]
        if variant == "effects":
            setup_components(e)
            salve = e.item_factory.create("stalker_unguent")
            e.player.inventory.items.append(salve)
            yield key(pygame.K_i, "i")
            yield from select(e, salve)
            turn = e.world_time.turn
            yield key(pygame.K_RETURN, "\r")
            ev.check("B2-08", "inventory uses actual salve and consumes one turn", [False, turn+1, 14, 0.2],
                     [salve in e.player.inventory.items, e.world_time.turn, e.player_speed_bonus_turns, e.player_speed_bonus])
            yield key(pygame.K_i, "i")
        elif variant == "needs":
            quiet(e)
            e.player.needs.hunger = e.player.needs.thirst = 1.0
            e.world_time.turn = 9
            e.player.fighter.hp = 40
        elif variant == "rain":
            e._ascend_from_submap()  # fixture navigation; normal stairs covered in B1 gate
            quiet(e)
            e.weather.state, e.weather.intensity, e.weather.turns_remaining = "heavy_rain", 0.6, 40
            e.rain_collection_progress = 3
            e.player.inventory.items.append(e.item_factory.create("empty_water_skin"))
        elif variant == "processing":
            quiet(e)
            e.local_map.processing_layer[(6, 6)] = {"item_id": "dried_bitter_herb", "turns_remaining": 2,
                                                     "decor_id": "", "source": "drying"}
        yield key(pygame.K_F5)
        expected = copy.deepcopy(state(e))
        e.player.needs.hunger = 0.7
        e.player.perks.acquired.clear()
        e._register_player_perks()
        e.true_sight_turns = e.player_speed_bonus_turns = 99
        e.player_speed_bonus = 0.9
        e.rain_collection_progress = 99
        e.local_map.processing_layer.clear()
        ev.record["unsaved_mutation"] = state(e)
        yield key(pygame.K_F9)
        ev.check("B2-08", "real F9 replaces mutated components", expected, state(e))
        ev.check("B2-08", "actual load handler reached", 1, counters["load"])
        capture("restored-" + variant)
        yield key(pygame.K_F5)  # terminal checkpoint; writer exits before any next turn
    def wrapped(e):
        seed_runtime(e)
        current.update(engine=e, actions=actions(e), turn=e.world_time.turn)
        return run(e)
    def events(*args, **kwargs):
        nonlocal frames, done
        e = current["engine"]
        if frames > 200 or time.monotonic()-started > 90 or e.world_time.turn-current["turn"] > 80:
            raise AssertionError("B2 loop budget exceeded")
        ev.check("B2-08", "SDL remains headless", "dummy", pygame.display.get_driver())
        ev.check("B2-08", "keys released", None, e._held_key)
        ev.record["trace"].append({"frame": frames, "turn": e.world_time.turn, "mode": e.mode.value,
                                  "position": [e.player.x, e.player.y], "counters": dict(counters)})
        try:
            action = next(current["actions"])
        except StopIteration:
            done = True
            pygame.key.set_mods(0)
            ev.check("B2-08", "quit event posted", True, pygame.event.post(pygame.event.Event(pygame.QUIT)))
        else:
            if action:
                pygame.key.set_mods(action["mod"])
                ev.record["trace"][-1]["event"] = action
                for kind in (pygame.KEYDOWN, pygame.KEYUP):
                    ev.check("B2-08", "app-local event posted", True, pygame.event.post(pygame.event.Event(kind, **action)))
        frames += 1
        return get(*args, **kwargs)
    Engine.run, pygame.event.get = wrapped, events
    SaveManager.save, SaveManager.load = saved, loaded
    try:
        main.main()
    except SystemExit as error:
        if not done or error.code not in (None, 0):
            raise
    finally:
        Engine.run, pygame.event.get = run, get
        SaveManager.save, SaveManager.load = save, load
        if pygame.get_init():
            pygame.key.set_mods(0)
            pygame.event.clear()
        pygame.quit()
    ev.check("B2-08", "original loop completed", True, done and frames > 0)
    ev.record.update(evidence_class="Original Engine.run and real app-local events, handlers and renderer",
                     frames=frames, counters=counters, elapsed_seconds=time.monotonic()-started)
