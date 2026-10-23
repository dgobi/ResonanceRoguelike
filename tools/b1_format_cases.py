"""Synthetic development-format rejection and bootstrap controls."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pickle
from b1_support import dump, gear, hashes, read
from b1_cases import setup_gear


def format_cases(e, ev):
    from engine.engine import Engine
    from engine.save_manager import ChunkCache, _serialize_player, _deserialize_player, _serialize_entity, _deserialize_entities
    import main
    setup_gear(e, "second")
    e.save_manager.save(e)
    slot = e.save_manager.save_path
    original_files = {p.relative_to(slot): p.read_bytes() for p in slot.rglob("*") if p.is_file()}
    base_player = read(slot / "player.json")
    base_world = read(slot / "world.json")
    base_meta = read(slot / "meta.json")
    def restore_files():
        # Only this worker's verified disposable slot is touched.
        assert slot.resolve().is_relative_to(Path(ev.job["game"]).resolve())
        for p in slot.rglob("*"):
            if p.is_file() and p.relative_to(slot) not in original_files:
                p.unlink()
        for rel, content in original_files.items():
            (slot / rel).parent.mkdir(parents=True, exist_ok=True)
            (slot / rel).write_bytes(content)
    def reject(case, name, edit, diagnostic):
        restore_files()
        # Deliberately warm both routes BEFORE removing/invalidating disk records.
        e.save_manager.cache = ChunkCache(slot)
        e.save_manager.cache.load(e.world_x, e.world_y)
        e.save_manager.cache.load_submap(e.current_submap_id)
        edit()
        before = hashes(slot)
        for cache_mode in ("hot", "cold"):
            if cache_mode == "cold":
                e.save_manager.cache = ChunkCache(slot)
            refs = [e.world_map, e.player.inventory, e.local_map, e.save_manager.cache, e.entities]
            state = gear(e)
            ev.check(case, name + " " + cache_mode + " fails", False, e.save_manager.load(e))
            ev.check(case, name + " diagnostic", True, diagnostic in e.save_manager.last_error)
            ev.check(case, name + " leaves live references", True,
                     all(a is b for a, b in zip(refs, [e.world_map, e.player.inventory, e.local_map, e.save_manager.cache, e.entities])))
            ev.check(case, name + " leaves live belongings", state, gear(e))
            ev.check(case, name + " file hashes unchanged", before, hashes(slot))
        entered, descents, writes = [], [], []
        orig_run, orig_lab = Engine.run, main._start_in_lab
        save = type(e.save_manager).save
        def run(engine):
            entered.append(True)
        def lab(*args, **kwargs):
            descents.append(True)
            return orig_lab(*args, **kwargs)
        def saved(*args, **kwargs):
            writes.append(True)
            return save(*args, **kwargs)
        Engine.run, main._start_in_lab, type(e.save_manager).save = run, lab, saved
        code = None
        try:
            main.main()
        except SystemExit as error:
            code = error.code
        finally:
            Engine.run, main._start_in_lab, type(e.save_manager).save = orig_run, orig_lab, save
        ev.check(case, name + " startup exits nonzero", 1, code)
        ev.check(case, name + " never enters play/new-game/save", [[], [], []], [entered, descents, writes])
        ev.check(case, name + " bootstrap preserves bytes", before, hashes(slot))
    variant = ev.job["variant"]
    if variant == "versions":
        reject("F02", "missing metadata", lambda: (slot / "meta.json").unlink(), "meta.json")
        for version in ("absent", None, True, "2", 2.5, 1, 3, 999):
            meta = dict(base_meta)
            if version == "absent":
                meta.pop("save_version")
            else:
                meta["save_version"] = version
            case = "F03" if type(version) is int and version == 1 else "F04" if type(version) is int else "F02"
            reject(case, repr(version), lambda m=meta: dump(slot / "meta.json", m), "version")
    elif variant == "fields":
        for key in ("inventory", "equipment"):
            for value in ("absent", None, [], "bad"):
                p = copy.deepcopy(base_player)
                if value == "absent":
                    p.pop(key)
                else:
                    p[key] = value
                reject("F05", f"{key}={value!r}", lambda p=p: dump(slot / "player.json", p), key)
        for field, value in (("capacity", True), ("capacity", 0), ("capacity", -1), ("capacity", "20"), ("items", None)):
            p = copy.deepcopy(base_player)
            p["inventory"][field] = value
            reject("F05", f"inventory.{field}={value!r}", lambda p=p: dump(slot / "player.json", p), "inventory")
        for index in (-1, True, 1.5, "1", 90, None):
            p = copy.deepcopy(base_player)
            p["equipment"]["offhand"]["inventory_index"] = index
            reject("F06", f"index={index!r}", lambda p=p: dump(slot / "player.json", p), "inventory_index")
        for name in ("mismatch", "unknown-earlier-row", "unknown-selected-row", "unknown-slot"):
            p = copy.deepcopy(base_player)
            if name == "mismatch":
                p["equipment"]["offhand"]["item_id"] = "crow_jerky"
            elif name.startswith("unknown-") and name.endswith("row"):
                p["inventory"]["items"][0 if name == "unknown-earlier-row" else 1]["item_id"] = "B1_missing_definition"
            else:
                p["equipment"]["B1_unknown"] = None
            reject("F06", name, lambda p=p: dump(slot / "player.json", p), "item" if name != "unknown-slot" else "slot")
        # Missing optional known slot means empty. Empty equipment object is also replacement.
        restore_files()
        for equipment in ({}, {"weapon": None}):
            p = copy.deepcopy(base_player)
            p["equipment"], p["light_source"] = equipment, None
            _deserialize_player(p, e)
            ev.check("F05", "optional slots are empty", True, all(v is None for v in e.player.equipment.slots.values()))
        # Serializer must reject invalid earlier rows instead of filtering and shifting.
        e.player.inventory.items[0].item_id = ""
        try:
            e.save_manager.save(e)
        except ValueError as error:
            ev.check("F06", "invalid serialized row diagnosed", True, "row 0" in str(error))
        else:
            ev.check("F06", "invalid row rejected", True, False)
    elif variant == "scenes":
        for name, sid in (("unknown", "B1_unknown"), ("wrong-world", e.current_submap_id)):
            p = copy.deepcopy(base_player)
            if name == "unknown":
                p["current_submap_id"] = sid
            else:
                p["world_x"] += 1
            reject("F07", name, lambda p=p: dump(slot / "player.json", p), "Submap")
        for surface in (False, True):
            restore_files()
            p = copy.deepcopy(base_player)
            if surface:
                p["current_submap_id"] = None
            active = (slot / "chunks" / (f"{e.world_x}_{e.world_y}.pkl" if surface else f"{p['current_submap_id']}.pkl"))
            def missing(p=p, active=active):
                dump(slot / "player.json", p)
                active.unlink()
            reject("F07", f"missing active surface={surface}", missing, "active scene")
            def malformed(p=p, active=active):
                dump(slot / "player.json", p)
                active.write_bytes(pickle.dumps({"invalid": "scene"}))
            reject("F07", f"invalid active surface={surface}", malformed, "active scene")
        for bad in (None, "rock", "B1_unknown"):
            restore_files()
            active = slot / "chunks" / f"{base_player['current_submap_id']}.pkl"
            cached = pickle.loads(original_files[active.relative_to(slot)])
            a = e.creature_factory.spawn("stone_lurker", 60, 30)
            row = _serialize_entity(a)
            if bad is None:
                row.pop("id")
            else:
                row["id"] = bad
            cached.entities = [row]
            reject("K01", f"invalid actor identity {bad!r}", lambda c=cached: active.write_bytes(pickle.dumps(c)), "creature identity")
    elif variant == "bootstrap":
        for removed in (("player.json", "meta.json"), ("player.json",), ("meta.json",)):
            def partial(removed=removed):
                for name in removed:
                    (slot / name).unlink()
            # direct missing-player/meta errors vary by which required read fails first
            reject("F05", f"partial full world {removed}", partial, "meta.json" if "meta.json" in removed else "player.json")
        # Exact seed-only shape is required even with a generic session marker.
        for payload in ({"seed": True}, {"seed": "1"}, {"seed": 1, "chunks": {}}):
            restore_files()
            def not_seed(payload=payload):
                for p in slot.rglob("*"):
                    if p.is_file():
                        p.unlink()
                dump(slot / "world.json", payload)
            reject("F05", f"not seed-only {payload}", not_seed, "meta.json")
        for seed_only in (False, True):
            restore_files()
            for p in slot.rglob("*"):
                if p.is_file():
                    p.unlink()
            if seed_only:
                dump(slot / "world.json", {"seed": 0})
            entered = []
            original = Engine.run
            def new_run(engine):
                entered.append([engine.current_submap_id is not None, engine.world_map.seed])
            Engine.run = new_run
            try:
                main.main()
            finally:
                Engine.run = original
            ev.check("F05", f"genuine new game seed_only={seed_only}", True, len(entered) == 1 and entered[0][0])
            if seed_only:
                ev.check("F05", "integer zero is valid seed", 0, entered[0][1])
    else:
        raise ValueError(variant)
