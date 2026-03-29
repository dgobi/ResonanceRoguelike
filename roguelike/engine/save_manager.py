# engine/save_manager.py
from __future__ import annotations
import json
import pickle
from pathlib import Path
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine
    from world.local_map import LocalMap
    from world.world_map import WorldMap
    from entities.actor import Actor


SAVE_DIR = Path("saves")


@dataclass
class CachedChunk:
    """
    Stored state for a visited chunk.
    local_map holds the full tile grid including explored flags.
    entities is a list of serializable dicts, not Actor objects.
    """
    local_map: "LocalMap"
    entities:  list[dict] = field(default_factory=list)


class ChunkCache:
    """
    In-memory + on-disk cache for visited chunks.
    Fixes the explored tile reset problem.

    hot:  chunks near the player, kept in memory
    cold: all other visited chunks, stored on disk
    """

    def __init__(self, save_path: Path) -> None:
        self.save_path   = save_path
        self.chunks_dir  = save_path / "chunks"
        self.hot:  dict[tuple[int,int], CachedChunk] = {}
        self.submap_hot: dict[str, CachedChunk]      = {}
        self.HOT_RADIUS  = 3   # keep this many chunks around player in memory

    def has(self, wx: int, wy: int) -> bool:
        if (wx, wy) in self.hot:
            return True
        return self._chunk_path(wx, wy).exists()

    def store(
        self,
        wx:        int,
        wy:        int,
        local_map: "LocalMap",
        entities:  list["Actor"],
    ) -> None:
        """Serialize current chunk state into the cache."""
        entity_dicts = [
            _serialize_entity(e) for e in entities
            if not _is_player(e)
        ]
        cached = CachedChunk(
            local_map = local_map,
            entities  = entity_dicts,
        )
        self.hot[(wx, wy)] = cached
        self._write_to_disk(wx, wy, cached)

    def load(
        self,
        wx: int,
        wy: int,
    ) -> CachedChunk | None:
        """Load a cached chunk. Returns None if not cached."""
        if (wx, wy) in self.hot:
            return self.hot[(wx, wy)]

        path = self._chunk_path(wx, wy)
        if path.exists():
            try:
                with open(path, "rb") as f:
                    cached = pickle.load(f)
                self.hot[(wx, wy)] = cached
                return cached
            except Exception as e:
                print(f"Warning: failed to load chunk ({wx},{wy}): {e}")
                return None

        return None

    def store_hot_only(
        self,
        wx:        int,
        wy:        int,
        local_map: "LocalMap",
        entities:  list["Actor"],
    ) -> None:
        """Update hot cache only — no disk write. Used for adjacent-chunk ticking."""
        entity_dicts = [
            _serialize_entity(e) for e in entities
            if not _is_player(e)
        ]
        self.hot[(wx, wy)] = CachedChunk(
            local_map = local_map,
            entities  = entity_dicts,
        )

    def evict_distant(self, player_wx: int, player_wy: int) -> None:
        """
        Move chunks far from the player out of hot cache to disk.
        Called on chunk transition to keep memory bounded.
        """
        to_evict = []
        for (wx, wy) in self.hot:
            dist = max(abs(wx - player_wx), abs(wy - player_wy))
            if dist > self.HOT_RADIUS:
                to_evict.append((wx, wy))

        for key in to_evict:
            cached = self.hot.pop(key)
            self._write_to_disk(key[0], key[1], cached)

    def store_submap(
        self,
        submap_id: str,
        local_map: "LocalMap",
        entities:  list,
    ) -> None:
        """Cache a submap's state by its string ID."""
        entity_dicts = [
            _serialize_entity(e) for e in entities
            if not _is_player(e)
        ]
        cached = CachedChunk(local_map=local_map, entities=entity_dicts)
        self.submap_hot[submap_id] = cached
        path = self._submap_path(submap_id)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "wb") as f:
                pickle.dump(cached, f)
        except Exception as e:
            print(f"Warning: failed to write submap {submap_id}: {e}")

    def load_submap(self, submap_id: str) -> "CachedChunk | None":
        """Load a cached submap by ID. Returns None if not cached."""
        if submap_id in self.submap_hot:
            return self.submap_hot[submap_id]
        path = self._submap_path(submap_id)
        if path.exists():
            try:
                with open(path, "rb") as f:
                    cached = pickle.load(f)
                self.submap_hot[submap_id] = cached
                return cached
            except Exception as e:
                print(f"Warning: failed to load submap {submap_id}: {e}")
        return None

    def _chunk_path(self, wx: int, wy: int) -> Path:
        return self.chunks_dir / f"{wx}_{wy}.pkl"

    def _submap_path(self, submap_id: str) -> Path:
        return self.chunks_dir / f"{submap_id}.pkl"

    def _write_to_disk(
        self,
        wx:     int,
        wy:     int,
        cached: CachedChunk,
    ) -> None:
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        path = self._chunk_path(wx, wy)
        try:
            with open(path, "wb") as f:
                pickle.dump(cached, f)
        except Exception as e:
            print(f"Warning: failed to write chunk ({wx},{wy}): {e}")


class SaveManager:
    """
    Handles full game save and load.
    Coordinates ChunkCache, world map, and player state.
    """

    def __init__(self, slot: int = 0) -> None:
        self.slot      = slot
        self.save_path = SAVE_DIR / f"slot_{slot}"
        self.cache     = ChunkCache(self.save_path)

    def save(self, engine: "Engine") -> None:
        """
        Full save. Writes world, player, current chunk,
        and all cached chunks to disk.
        """
        self.save_path.mkdir(parents=True, exist_ok=True)

        # Store current chunk before saving
        self.cache.store(
            engine.world_x,
            engine.world_y,
            engine.local_map,
            engine.entities,
        )

        # World map
        world_data = _serialize_world(engine.world_map)
        _write_json(self.save_path / "world.json", world_data)

        # Player state
        player_data = _serialize_player(engine)
        _write_json(self.save_path / "player.json", player_data)

        # Meta
        import datetime
        meta = {
            "save_version": 1,       # increment when save format changes
            "saved_at":   datetime.datetime.now().isoformat(),
            "world_x":    engine.world_x,
            "world_y":    engine.world_y,
            "turn":       engine.world_time.turn,
            "moon_phase": engine.world_time.moon_phase_name,
        }
        _write_json(self.save_path / "meta.json", meta)

        engine.log.add("Progress preserved.", LIFE_GREEN)

    def load(self, engine: "Engine") -> bool:
        meta_path = self.save_path / "meta.json"
        if meta_path.exists():
            meta = _read_json(meta_path)
            if meta.get("save_version", 0) < 1:
                engine.log.add(
                    "Save file is outdated and cannot be loaded.",
                    FRESH_WOUND
                )
                return False
        """
        Full load. Restores world, player, and chunk cache.
        Returns True on success.
        """
        if not self.save_path.exists():
            engine.log.add(
                "No save found.", BLOOD_STONE
            )
            return False

        try:
            # World map
            world_data = _read_json(self.save_path / "world.json")
            _deserialize_world(world_data, engine.world_map)

            # Player state
            player_data = _read_json(self.save_path / "player.json")
            _deserialize_player(player_data, engine)

            # Load the player's current chunk from cache
            cached = self.cache.load(engine.world_x, engine.world_y)
            if cached:
                engine.local_map = cached.local_map
                engine.entities  = [engine.player]
                engine.entities += _deserialize_entities(
                    cached.entities, engine
                )
            else:
                # Chunk not cached — regenerate
                from generation.region_gen import generate_region
                from config import MAP_WIDTH, MAP_HEIGHT
                chunk = engine.world_map.get(
                    engine.world_x, engine.world_y
                )
                if chunk:
                    new_map, _ = generate_region(
                        chunk, MAP_WIDTH, MAP_HEIGHT,
                        engine.data.terrain
                    )
                    engine.local_map = new_map
                    engine.entities  = [engine.player]

            engine._update_fov()
            engine.log.add(
                "The world reassembles itself around you.",
                LIFE_GREEN
            )
            return True

        except Exception as e:
            print(f"Load failed: {e}")
            import traceback
            traceback.print_exc()
            engine.log.add(
                f"Load failed: {e}", FRESH_WOUND
            )
            return False

    def save_exists(self) -> bool:
        return (self.save_path / "player.json").exists()


# ------------------------------------------------------------------ #
#  Serialization helpers
# ------------------------------------------------------------------ #

def _serialize_town_data(td) -> dict | None:
    if td is None:
        return None
    return {
        "name":            td.name,
        "size":            td.size,
        "districts":       td.districts,
        "bell_state":      td.bell_state,
        "is_festival":     td.is_festival,
        "waystone_pos":    list(td.waystone_pos),
        "bell_tower_pos":  list(td.bell_tower_pos) if td.bell_tower_pos else None,
        "buildings":       td.buildings,
        "creature_spawns": td.creature_spawns,
        "item_spawns":     td.item_spawns,
    }


def _serialize_world(world_map: "WorldMap") -> dict:
    chunks = {}
    for (wx, wy), chunk in world_map.chunks.items():
        chunks[f"{wx},{wy}"] = {
            "region_type":        chunk.region_type.value,
            "seed":               chunk.seed,
            "explored":           chunk.explored,
            "visited":            chunk.visited,
            "is_locus":           chunk.is_locus,
            "zones":              chunk.zones,
            "name":               chunk.name,
            "name_register":      chunk.name_register,
            "town_id":            chunk.town_id,
            "town_role":          chunk.town_role,
            "biome_id":           chunk.biome_id,
            "elevation":          chunk.elevation,
            "moisture":           chunk.moisture,
            "resonance":          chunk.resonance,
            "difficulty":         chunk.difficulty,
            "distance_from_peak": chunk.distance_from_peak,
            "is_river":           chunk.is_river,
            "is_capital":         chunk.is_capital,
            "river_connections":  chunk.river_connections,
            "edges": {
                edge: [
                    {
                        "connector_type": c.connector_type.value,
                        "position":       c.position,
                        "feature_id":     c.feature_id,
                        "entrance_type":  c.entrance_type,
                    }
                    for c in connectors
                ]
                for edge, connectors in chunk.edges.items()
            },
            "town_data": _serialize_town_data(chunk.town_data),
            "submaps": [
                {
                    "submap_id":   s.submap_id,
                    "submap_type": s.submap_type,
                    "name":        s.name,
                    "seed":        s.seed,
                    "layout_id":   s.layout_id,
                    "generated":   s.generated,
                    "entry_x":     s.entry_x,
                    "entry_y":     s.entry_y,
                    "surface_x":   s.surface_x,
                    "surface_y":   s.surface_y,
                    "depth":       s.depth,
                }
                for s in chunk.submaps
            ],
        }
    return {
        "width":          world_map.width,
        "height":         world_map.height,
        "seed":           world_map.seed,
        "vukh_x":         world_map.vukh_x,
        "vukh_y":         world_map.vukh_y,
        "start_wx":       world_map.start_wx,
        "start_wy":       world_map.start_wy,
        "capital_chunks": list(world_map.capital_chunks),
        "town_chunks":    list(world_map.town_chunks),
        "road_tiles":     [[k[0], k[1], v] for k, v in world_map.road_tiles.items()],
        "chunks":         chunks,
        "myth":           world_map.myth.to_dict() if world_map.myth else None,
        "town_groups":    {str(k): v for k, v in world_map.town_groups.items()},
        "town_chunk_ids": [[k[0], k[1], v] for k, v in world_map.town_chunk_ids.items()],
        "chunk_names":    [[k[0], k[1], v] for k, v in world_map.chunk_names.items()],
    }


def _deserialize_world(data: dict, world_map: "WorldMap") -> None:
    from world.world_map import Chunk, RegionType, SubMap, ConnectorType

    for key, cdata in data["chunks"].items():
        wx, wy = map(int, key.split(","))
        try:
            region_type = RegionType(cdata["region_type"])
        except ValueError:
            # Old save with a region type that no longer exists (e.g. "dungeon").
            # Treat as plains so the chunk is still accessible.
            region_type = RegionType.PLAINS
        chunk = Chunk(
            wx                  = wx,
            wy                  = wy,
            region_type         = region_type,
            seed                = cdata["seed"],
            explored            = cdata["explored"],
            visited             = cdata["visited"],
            is_locus            = cdata.get("is_locus",            False),
            zones               = cdata.get("zones",               []),
            name                = cdata.get("name",                ""),
            name_register       = cdata.get("name_register",       "common"),
            town_id             = cdata.get("town_id") if cdata.get("town_id") is not None else -1,
            town_role           = cdata.get("town_role") or "",
            biome_id            = cdata.get("biome_id",            "plains"),
            elevation           = cdata.get("elevation",           0.5),
            moisture            = cdata.get("moisture",            0.5),
            resonance           = cdata.get("resonance",           0.1),
            difficulty          = cdata.get("difficulty",          0.1),
            distance_from_peak  = cdata.get("distance_from_peak",  999.0),
            is_river            = cdata.get("is_river",            False),
            is_capital          = cdata.get("is_capital",          False),
            river_connections   = cdata.get("river_connections",   []),
        )
        # Restore town_data
        td_raw = cdata.get("town_data")
        if td_raw:
            from world.world_map import TownData
            chunk.town_data = TownData(
                name            = td_raw.get("name", ""),
                size            = td_raw.get("size", "small"),
                districts       = td_raw.get("districts", []),
                bell_state      = td_raw.get("bell_state", "spent"),
                is_festival     = td_raw.get("is_festival", False),
                waystone_pos    = tuple(td_raw.get("waystone_pos", [0, 0])),
                bell_tower_pos  = tuple(td_raw["bell_tower_pos"]) if td_raw.get("bell_tower_pos") else None,
                buildings       = td_raw.get("buildings", []),
                creature_spawns = td_raw.get("creature_spawns", []),
                item_spawns     = td_raw.get("item_spawns", []),
            )
        # Restore edge connectors
        for edge, connectors in cdata.get("edges", {}).items():
            for c in connectors:
                chunk.add_connector(
                    edge,
                    ConnectorType(c["connector_type"]),
                    c["position"],
                    c.get("feature_id",    ""),
                    c.get("entrance_type", ""),
                )
        # Restore submaps
        for s in cdata.get("submaps", []):
            sm = SubMap(
                submap_id   = s.get("submap_id", s.get("id", "")),
                submap_type = s["submap_type"],
                name        = s["name"],
                seed        = s["seed"],
                layout_id   = s.get("layout_id",  ""),
                generated   = s.get("generated",  False),
                entry_x     = s.get("entry_x",    0),
                entry_y     = s.get("entry_y",    0),
                surface_x   = s.get("surface_x",  0),
                surface_y   = s.get("surface_y",  0),
                depth       = s.get("depth",      1),
            )
            chunk.submaps.append(sm)
        world_map.chunks[(wx, wy)] = chunk

    world_map.seed           = data.get("seed",     0)
    world_map.vukh_x         = data.get("vukh_x",   world_map.width  // 2)
    world_map.vukh_y         = data.get("vukh_y",   world_map.height // 2)
    world_map.start_wx       = data.get("start_wx", world_map.width  // 2)
    world_map.start_wy       = data.get("start_wy", world_map.height // 2)
    world_map.capital_chunks = set(tuple(c) for c in data.get("capital_chunks", []))
    world_map.town_chunks    = set(tuple(c) for c in data.get("town_chunks",    []))
    world_map.road_tiles     = {(r[0], r[1]): r[2] for r in data.get("road_tiles", [])}
    world_map.town_groups    = {int(k): [tuple(coord) for coord in v]
                                for k, v in data.get("town_groups", {}).items()}
    world_map.town_chunk_ids = {(r[0], r[1]): r[2]
                                for r in data.get("town_chunk_ids", [])}
    world_map.chunk_names    = {(r[0], r[1]): r[2]
                                for r in data.get("chunk_names", [])}

    from world.world_myth import WorldMyth
    myth_data = data.get("myth")
    if myth_data:
        world_map.myth = WorldMyth.from_dict(myth_data)


def _serialize_player(engine: "Engine") -> dict:
    p       = engine.player
    fighter = getattr(p, "fighter",    None)
    needs   = getattr(p, "needs",      None)
    corrupt = getattr(p, "corruption", None)
    inv     = getattr(p, "inventory",  None)
    light   = getattr(p, "light_source", None)

    return {
        "x":         p.x,
        "y":         p.y,
        "world_x":   engine.world_x,
        "world_y":   engine.world_y,
        "tile":      p.tile,
        "name":      p.name,
        "current_submap_id":  engine.current_submap_id,
        "surface_return_x":   engine.surface_return_x,
        "surface_return_y":   engine.surface_return_y,
        "true_sight":   getattr(p, "true_sight",   False),
        "dodge_chance": getattr(p, "dodge_chance", 0.05),
        "turn":      engine.world_time.turn,
        "fighter": {
            "hp":           fighter.hp,
            "max_hp":       fighter.max_hp,
            "power":        fighter.power,
            "defense":      fighter.defense,
            "body_id":      fighter.body_id,
            "effective_av": fighter.effective_av,
        } if fighter else None,
        "needs": {
            "hunger": needs.hunger,
            "thirst": needs.thirst,
        } if needs else None,
        "corruption": {
            "value": corrupt.value,
        } if corrupt else None,
        "inventory": {
            "capacity": inv.capacity,
            "items": [
                {
                    "item_id":           i.item_id,
                    "name":              i.name,
                    "on_use":            i.on_use,
                    "turns_lit":         i.turns_lit,
                    "liquid":            i.liquid,
                    "liquid_volume":     i.liquid_volume,
                    "text_id":           getattr(i, "text_id", None),
                    "temporary_essence": getattr(i, "temporary_essence", []) or None,
                }
                for i in inv.items
                if getattr(i, "item_id", "")
            ],
        } if inv else None,
        "light_source": {
            "radius":  light.radius,
            "color":   list(light.color),
            "falloff": light.falloff,
            "flicker": light.flicker,
            "active":  light.active,
        } if light else None,
        "language": {
            "known_deep_words":   list(p.language.known_deep_words),
            "translation_events": p.language.translation_events,
            "taught_texts":       list(p.language.taught_texts),
            "recovered_spans":    [list(s) for s in p.language.recovered_spans],
            "recovered_text":     {str(k): v for k, v in p.language.recovered_text.items()},
        } if getattr(p, "language", None) else None,
        "perks": {
            "acquired":        list(p.perks.acquired),
            "perk_state":      p.perks.perk_state,
            "affinity_scores": p.perks.affinity_scores,
        } if getattr(p, "perks", None) else None,
        "equipment": {
            slot: item.item_id if item else None
            for slot, item in p.equipment.slots.items()
        } if getattr(p, "equipment", None) else None,
        "level": {
            "level":               p.level.level,
            "exp":                 p.level.exp,
            "exp_to_next":         p.level.exp_to_next,
            "perk_points":         p.level.perk_points,
            "total_levels_gained": p.level.total_levels_gained,
        } if getattr(p, "level", None) else None,
        "resonance": {
            "exposure":   engine.resonance_exposure,
            "corruption": engine.corruption,
            "thresholds": list(getattr(engine, "_corruption_thresholds", set())),
        },
        "weather": getattr(engine, "weather", None) and engine.weather.to_dict(),
        "live_pursuers": [
            {"entity": _serialize_entity(e), "wx": wx, "wy": wy, "submap_id": sub_id}
            for e, wx, wy, sub_id in getattr(engine, "_live_pursuers", [])
        ],
    }


def _deserialize_player(data: dict, engine: "Engine") -> None:
    from components.fighter import Fighter
    from components.needs import Needs
    from components.corruption import Corruption
    from components.inventory import Inventory
    from components.light_source import LightSource

    p            = engine.player
    p.x          = data["x"]
    p.y          = data["y"]
    engine.world_x            = data["world_x"]
    engine.world_y            = data["world_y"]
    engine.current_submap_id  = data.get("current_submap_id")
    engine.surface_return_x   = data.get("surface_return_x", 0)
    engine.surface_return_y   = data.get("surface_return_y", 0)
    p.true_sight   = data.get("true_sight",   False)
    p.dodge_chance = data.get("dodge_chance", 0.05)

    engine.world_time.turn = data.get("turn", 0)

    if data.get("fighter"):
        f = data["fighter"]
        p.fighter              = Fighter(f["max_hp"], f["power"], f["defense"])
        p.fighter.body_id      = f.get("body_id", "body_player")
        p.fighter.hp           = f.get("hp", f["max_hp"])
        p.fighter.effective_av = f.get("effective_av", 0)

    if data.get("needs"):
        n = data["needs"]
        p.needs        = Needs()
        p.needs.hunger = n["hunger"]
        p.needs.thirst = n["thirst"]

    if data.get("corruption"):
        c = data["corruption"]
        p.corruption       = Corruption()
        p.corruption.value = c["value"]

    if data.get("inventory"):
        from engine.item_factory import ItemFactory
        inv_data = data["inventory"]
        p.inventory = Inventory(capacity=inv_data["capacity"])
        factory = ItemFactory(engine.data)
        for idata in inv_data.get("items", []):
            item_id = idata.get("item_id", "")
            if not item_id:
                continue
            item = factory.create(item_id, p.x, p.y)
            if item is None:
                continue
            item.name          = idata.get("name",         item.name)
            item.on_use        = idata.get("on_use",        item.on_use)
            item.turns_lit     = idata.get("turns_lit",     0)
            item.liquid        = idata.get("liquid",        item.liquid)
            item.liquid_volume = idata.get("liquid_volume", item.liquid_volume)
            text_id = idata.get("text_id")
            if text_id:
                item.text_id = text_id
            te = idata.get("temporary_essence")
            if te:
                item.temporary_essence = list(te)
            p.inventory.add(item)

    if data.get("light_source"):
        ls = data["light_source"]
        p.light_source = LightSource(
            radius  = ls["radius"],
            color   = tuple(ls["color"]),
            falloff = ls["falloff"],
            flicker = ls["flicker"],
            active  = ls["active"],
        )

    if data.get("language"):
        from components.language import Language
        ld   = data["language"]
        lang = Language()
        lang.known_deep_words   = set(ld.get("known_deep_words", []))
        lang.translation_events = ld.get("translation_events", {})
        lang.taught_texts       = set(ld.get("taught_texts", []))
        lang.recovered_spans    = set(tuple(s) for s in ld.get("recovered_spans", []))
        lang.recovered_text     = {
            tuple(eval(k)): v
            for k, v in ld.get("recovered_text", {}).items()
        }
        p.language = lang

    if data.get("perks"):
        from components.perks import Perks
        pd     = data["perks"]
        perks  = Perks()
        perks.acquired        = set(pd.get("acquired", []))
        perks.perk_state      = pd.get("perk_state", {})
        perks.affinity_scores = pd.get("affinity_scores", {})
        p.perks = perks

    if data.get("level"):
        from components.level import LevelComponent
        ld = data["level"]
        lc = LevelComponent()
        lc.level               = ld.get("level", 1)
        lc.exp                 = ld.get("exp", 0)
        lc.exp_to_next         = ld.get("exp_to_next", 100)
        lc.perk_points         = ld.get("perk_points", 0)
        lc.total_levels_gained = ld.get("total_levels_gained", 0)
        p.level = lc

    # Resonance / corruption state
    if data.get("resonance"):
        r = data["resonance"]
        engine.resonance_exposure      = r.get("exposure", 0.0)
        engine.corruption              = r.get("corruption", 0.0)
        engine._corruption_thresholds  = set(r.get("thresholds", []))

    # Weather state
    if data.get("weather") and hasattr(engine, "weather"):
        from engine.weather import WeatherSystem
        engine.weather = WeatherSystem.from_dict(data["weather"], engine.rng)
        engine.weather.load_mechanics(engine.data.weather_defs)

    # Live pursuers
    engine._live_pursuers = []
    for lp in data.get("live_pursuers", []):
        ents = _deserialize_entities([lp["entity"]], engine)
        if ents:
            engine._live_pursuers.append((ents[0], lp["wx"], lp["wy"], lp.get("submap_id")))

    # Restore equipped items after inventory is fully reconstructed
    _restore_equipment(p, data.get("equipment", {}), engine.data)


def _restore_equipment(player, saved_equipment: dict, data) -> None:
    """
    Re-equip items after load by matching saved slot→item_id
    against the reconstructed inventory.
    """
    from components.equipment import Equipment
    from engine.item_system import _recompute_effective_av

    if not saved_equipment:
        return

    equipment = getattr(player, "equipment", None)
    if not equipment:
        player.equipment = Equipment()
        equipment = player.equipment

    inventory = getattr(player, "inventory", None)
    if not inventory:
        return

    for slot, item_id in saved_equipment.items():
        if not item_id:
            continue

        item = next(
            (i for i in inventory.items
             if getattr(i, "item_id", None) == item_id),
            None,
        )
        if not item:
            continue

        equipment.slots[slot] = item
        item.equipped = True

        item_def = data.items.get(item_id, {})

        if slot == "light":
            light_data = item_def.get("light", {})
            if light_data:
                from components.light_source import LightSource
                ls = LightSource(
                    radius  = light_data.get("radius",  6),
                    color   = tuple(light_data.get("color", [226, 181, 112])),
                    falloff = light_data.get("falloff", 1.5),
                    flicker = light_data.get("flicker", False),
                    active  = True,
                )
                ls._item_id    = item_id
                ls._item_ref   = item
                ls._burn_turns = item.burn_turns or 600
                ls._turns_used = item.turns_lit
                player.light_source = ls

    # Recompute effective_av from all equipped armor after everything is restored
    _recompute_effective_av(player, data)


def _serialize_entity(entity: "Actor") -> dict:
    """Convert an Actor to a serializable dict."""
    fighter = getattr(entity, "fighter",    None)
    ai      = getattr(entity, "ai",         None)
    percep  = getattr(entity, "perception", None)

    return {
        "type":            "actor",
        "id":              getattr(entity, "entity_id",
                                  entity.tile),
        "x":               entity.x,
        "y":               entity.y,
        "tile":            entity.tile,
        "name":            entity.name,
        "is_alive":        getattr(entity, "is_alive", True),
        "blocks_movement": entity.blocks_movement,
        "fighter": {
            "hp":           fighter.hp,
            "max_hp":       fighter.max_hp,
            "power":        fighter.power,
            "defense":      fighter.defense,
            "body_id":      fighter.body_id,
            "effective_av": fighter.effective_av,
        } if fighter else None,
        "ai_type":  type(ai).__name__ if ai else None,
        "ai_state": ai.state.value    if ai else None,
        "home_x":   ai.home_x         if ai else None,
        "home_y":   ai.home_y         if ai else None,
        "pursuit_turns_without_contact": ai.pursuit_turns_without_contact if ai else 0,
        "faction":  percep.faction    if percep else None,
        "hostile_to": percep.hostile_to if percep else None,
        "sight_radius":   percep.sight_radius   if percep else 8,
        "hearing_radius": percep.hearing_radius if percep else 5,
        "sees_in_dark":   percep.sees_in_dark   if percep else False,
        "wander_radius":  ai.wander_radius      if ai else 8,
    }


def _is_player(entity: "Actor") -> bool:
    return entity.name == "Player"


def _deserialize_entities(
    entity_dicts: list[dict],
    engine:       "Engine",
) -> list:
    """Reconstruct Actor objects from serialized dicts."""
    from engine.creature_factory import CreatureFactory
    factory  = CreatureFactory(engine.data)
    restored = []

    for d in entity_dicts:
        if not d.get("is_alive", True):
            # Restore corpse as Item
            from entities.item import Item
            corpse = Item(
                x    = d["x"],
                y    = d["y"],
                tile = "corpse",
                name = d["name"],
            )
            restored.append(corpse)
            continue

        # Try to spawn from creature definition
        creature_id = d.get("id", d.get("tile", ""))
        actor = factory.spawn(creature_id, d["x"], d["y"])

        if actor is None:
            continue

        # Restore fighter state from saved state
        fighter = getattr(actor, "fighter", None)
        if fighter and d.get("fighter"):
            fd = d["fighter"]
            fighter.body_id      = fd.get("body_id", "body_human")
            fighter.hp           = fd.get("hp", fighter.max_hp)
            fighter.effective_av = fd.get("effective_av", fighter.effective_av)

        # Restore AI state
        ai = getattr(actor, "ai", None)
        if ai and d.get("ai_state"):
            from components.ai import AIState
            try:
                ai.state = AIState(d["ai_state"])
            except ValueError:
                pass
            if d.get("home_x") is not None:
                ai.home_x = d["home_x"]
                ai.home_y = d["home_y"]
            ai.pursuit_turns_without_contact = d.get("pursuit_turns_without_contact", 0)

        restored.append(actor)

    return restored


# ------------------------------------------------------------------ #
#  File helpers
# ------------------------------------------------------------------ #

def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)