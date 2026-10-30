# engine/save_manager.py
from __future__ import annotations
import json
import pickle
import math
import ast
import copy
from engine.save_components import (serialize_item, validate_item, restore_item,
    serialize_runtime, restore_runtime, validate_components, serialize_actor_runtime,
    validate_actor_runtime, restore_actor_runtime)
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
SAVE_VERSION = 2


class SaveFormatError(ValueError):
    """A required development-save field cannot be restored faithfully."""


def _validate_version(meta) -> None:
    version = meta.get("save_version") if isinstance(meta, dict) else None
    if type(version) is not int:
        raise SaveFormatError(f"Invalid save_version {version!r}; expected integer {SAVE_VERSION}")
    if version != SAVE_VERSION:
        raise SaveFormatError(f"Unsupported save version {version}; supported: {SAVE_VERSION}")


@dataclass(frozen=True)
class SceneAddress:
    world_x: int
    world_y: int
    submap_id: str | None

    @classmethod
    def from_player(cls, player, world):
        wx, wy = player.get("world_x"), player.get("world_y")
        if type(wx) is not int or type(wy) is not int:
            raise SaveFormatError("Scene world coordinates must be integers")
        if "current_submap_id" not in player:
            raise SaveFormatError("Missing current_submap_id scene field")
        sid = player["current_submap_id"]
        chunk = world.get("chunks", {}).get(f"{wx},{wy}")
        if chunk is None:
            raise SaveFormatError(f"Unknown scene world address ({wx}, {wy})")
        if sid is not None:
            if (not isinstance(sid, str) or not sid or
                    any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in sid)):
                raise SaveFormatError("Invalid submap_id")
            if sum(s.get("submap_id") == sid for s in chunk.get("submaps", [])) != 1:
                raise SaveFormatError(f"Submap {sid!r} does not belong to ({wx}, {wy})")
        return cls(wx, wy, sid)

    def store(self, cache, local_map, entities):
        if self.submap_id is None:
            cache.store(self.world_x, self.world_y, local_map, entities)
        else:
            cache.store_submap(self.submap_id, local_map, entities)

    def load(self, cache):
        return (cache.load(self.world_x, self.world_y) if self.submap_id is None
                else cache.load_submap(self.submap_id))


def _pending_destination(row: dict, player: dict) -> dict:
    """Additive v2 migration: old queues belonged to the saved active scene."""
    fields = ("destination_wx", "destination_wy", "destination_submap_id")
    present = [key in row for key in fields]
    if any(present) and not all(present):
        raise SaveFormatError("Incomplete pending-arrival destination")
    if all(present):
        return {key: row[key] for key in fields}
    return {"destination_wx": player["world_x"],
            "destination_wy": player["world_y"],
            "destination_submap_id": player.get("current_submap_id")}


def _validate_pending_arrivals(player: dict, world: dict) -> None:
    for row in player.get("pending_pursuer_arrivals", []):
        destination = _pending_destination(row, player)
        SceneAddress.from_player({
            "world_x": destination["destination_wx"],
            "world_y": destination["destination_wy"],
            "current_submap_id": destination["destination_submap_id"],
        }, world)
        if (type(row.get("delay")) is not int or row["delay"] < 0
                or type(row.get("entry_x")) is not int
                or type(row.get("entry_y")) is not int):
            raise SaveFormatError("Invalid pending-arrival delay or entry")


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
    """Mutable session overlay above an immutable checkpoint (or read-only legacy).

    Every hot entry is considered potentially dirty: map layers can mutate in
    place without going through store_hot_only. Full saves serialize all of them.
    """
    def __init__(self, save_path: Path, base_path=None) -> None:
        from engine.checkpoints import CheckpointStore, no_links
        import uuid
        self.save_path = no_links(Path(save_path))
        if base_path is None:
            store = CheckpointStore(self.save_path)
            candidates = store.candidates()
            base_path = candidates[0][1] if candidates else store.legacy()
        self.base_path = Path(base_path) if base_path is not None else None
        self.chunks_dir = self.save_path / '.sessions' / uuid.uuid4().hex / 'chunks'
        self.hot: dict[tuple[int, int], CachedChunk] = {}
        self.submap_hot: dict[str, CachedChunk] = {}
        self.HOT_RADIUS = 3

    def _chunk_path(self, wx, wy):
        if type(wx) is not int or type(wy) is not int:
            raise SaveFormatError('Scene coordinates must be integers')
        return self.chunks_dir / f'{wx}_{wy}.pkl'

    def _submap_path(self, submap_id):
        import re
        if (not isinstance(submap_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', submap_id)
                or re.fullmatch(r'-?\d+_-?\d+', submap_id)):
            raise SaveFormatError('Invalid or ambiguous submap_id')
        return self.chunks_dir / (submap_id + '.pkl')

    def _read_path(self, path):
        from engine.checkpoints import no_links
        if no_links(path).is_file():
            return path
        if self.base_path is not None:
            base = no_links(self.base_path / 'chunks' / path.name)
            if base.is_file():
                return base
        return None

    def has(self, wx, wy):
        return (wx, wy) in self.hot or self._read_path(self._chunk_path(wx, wy)) is not None

    @staticmethod
    def _cached(local_map, entities):
        return CachedChunk(local_map, [_serialize_entity(e) for e in entities if not _is_player(e)])

    @staticmethod
    def _read(path):
        cached = pickle.loads(path.read_bytes())
        from world.local_map import LocalMap
        if not isinstance(cached, CachedChunk) or not isinstance(cached.local_map, LocalMap):
            raise SaveFormatError(f'Missing or invalid active scene record: {path.name}')
        return cached

    def _write(self, path, cached):
        from engine.checkpoints import atomic_write
        atomic_write(path, pickle.dumps(cached, protocol=pickle.HIGHEST_PROTOCOL))

    def store(self, wx, wy, local_map, entities):
        cached = self._cached(local_map, entities)
        self._write(self._chunk_path(wx, wy), cached)
        self.hot[(wx, wy)] = cached

    def load(self, wx, wy):
        key = (wx, wy)
        if key not in self.hot:
            path = self._read_path(self._chunk_path(wx, wy))
            if path is None:
                return None
            self.hot[key] = self._read(path)
        return self.hot[key]

    def store_hot_only(self, wx, wy, local_map, entities):
        self._chunk_path(wx, wy)  # validate before changing the cache
        self.hot[(wx, wy)] = self._cached(local_map, entities)

    def evict_distant(self, player_wx, player_wy):
        for key in list(self.hot):
            if max(abs(key[0]-player_wx), abs(key[1]-player_wy)) > self.HOT_RADIUS:
                self._write(self._chunk_path(*key), self.hot[key])
                del self.hot[key]  # only after a successful durable overlay write

    def store_submap(self, submap_id, local_map, entities):
        cached = self._cached(local_map, entities)
        self._write(self._submap_path(submap_id), cached)
        self.submap_hot[submap_id] = cached

    def load_submap(self, submap_id):
        if submap_id not in self.submap_hot:
            path = self._read_path(self._submap_path(submap_id))
            if path is None:
                return None
            self.submap_hot[submap_id] = self._read(path)
        return self.submap_hot[submap_id]

    def snapshot(self, address, local_map, entities, data):
        from engine.checkpoints import no_links, SCENE
        payloads = {}
        # Cold checkpoint -> session disk -> hot -> active. Active actors are
        # serialized live; inactive hot actor rows belong to the cache owner.
        for directory in ([self.base_path / 'chunks'] if self.base_path else []) + [self.chunks_dir]:
            if directory.exists():
                for path in sorted(directory.iterdir()):
                    no_links(path)
                    if not path.is_file() or not SCENE.fullmatch(path.name):
                        raise SaveFormatError(f'Invalid scene cache member: {path.name}')
                    payloads['chunks/' + path.name] = path.read_bytes()
        for (wx, wy), cached in self.hot.items():
            payloads['chunks/' + self._chunk_path(wx, wy).name] = pickle.dumps(cached, protocol=pickle.HIGHEST_PROTOCOL)
        for sid, cached in self.submap_hot.items():
            payloads['chunks/' + self._submap_path(sid).name] = pickle.dumps(cached, protocol=pickle.HIGHEST_PROTOCOL)
        active = self._chunk_path(address.world_x, address.world_y) if address.submap_id is None else self._submap_path(address.submap_id)
        payloads['chunks/' + active.name] = pickle.dumps(self._cached(local_map, entities), protocol=pickle.HIGHEST_PROTOCOL)
        from world.local_map import LocalMap
        identities = set()
        for name, raw in payloads.items():
            cached = pickle.loads(raw)
            if not isinstance(cached, CachedChunk) or not isinstance(cached.local_map, LocalMap):
                raise SaveFormatError(f'Invalid scene: {name}')
            _validate_entities(cached.entities, data, cached.local_map)
            _claim_individuals(cached.entities, identities)
        return payloads


class SaveManager:
    """Whole-slot generations with bounded recovery and isolated working caches."""
    def __init__(self, slot: int = 0, *, save_root: Path | None = None) -> None:
        from engine.checkpoints import CheckpointStore
        if type(slot) is not int or not 0 <= slot <= 999:
            raise SaveFormatError('Slot must be an integer from 0 to 999')
        self.slot = slot
        self.save_path = Path(SAVE_DIR if save_root is None else save_root).absolute() / f'slot_{slot}'
        self.store = CheckpointStore(self.save_path)
        self.cache = ChunkCache(self.save_path)
        self.generation = None
        self.last_error = None
        self.recovery_notice = None
        self._head_token = self.store.token()
        self._needs_load = self.cache.base_path is not None or self._head_token is not None
        self._checkpoint_fault = lambda phase: None

    def _records(self, path):
        _validate_version(_read_json(path / 'meta.json'))
        world = _read_json(path / 'world.json')
        player = _read_json(path / 'player.json')
        if (not isinstance(world, dict) or type(world.get('seed')) is not int
                or type(world.get('width')) is not int or world['width'] <= 0
                or type(world.get('height')) is not int or world['height'] <= 0
                or not isinstance(world.get('chunks'), dict)):
            raise SaveFormatError('Invalid saved world record')
        address = SceneAddress.from_player(player, world)
        return world, player, address

    def _candidates(self):
        candidates = self.store.candidates()
        legacy = self.store.legacy()
        return candidates or ([(None, legacy)] if legacy else [])

    def startup_state(self):
        candidates = self._candidates()
        errors = list(self.store.errors)
        for generation, path in candidates:
            try:
                world, _, _ = self._records(path)
                return 'load', world['seed']
            except Exception as error:
                errors.append(str(error))
        sealed = any(p.is_dir() for p in (self.save_path / 'generations').glob('g-*'))
        if candidates or errors or sealed or any((self.save_path / n).exists() for n in ('HEAD.json', 'BACKUP.json')):
            raise SaveFormatError('No recoverable checkpoint: ' + '; '.join(errors))
        # Only a deliberate seed, session scratch, and our interrupted atomic
        # temporary files are benign before the first published checkpoint.
        files = {p.relative_to(self.save_path).as_posix() for p in self.save_path.rglob('*') if p.is_file()}
        durable = {n for n in files if not n.startswith(('.sessions/', 'generations/')) and not (n.startswith('.') and n.endswith('.tmp'))}
        if not durable:
            return 'new', None
        if durable == {'world.json'}:
            world = _read_json(self.save_path / 'world.json')
            if isinstance(world, dict) and set(world) == {'seed'} and type(world['seed']) is int:
                return 'new', world['seed']
        raise SaveFormatError('Incomplete save: missing meta.json or published checkpoint')

    def checkpoint_path(self):
        if self.generation:
            return self.store.validate(self.generation)
        candidates = self._candidates()
        if not candidates:
            raise SaveFormatError('No recoverable checkpoint: ' + '; '.join(self.store.errors))
        return candidates[0][1]

    def save(self, engine):
        from engine.checkpoints import encoded
        import datetime
        self.last_error = None
        try:
            if self._needs_load:
                raise SaveFormatError('Load the existing slot before saving; checkpoint ownership is not established')
            world_data = _serialize_world(engine.world_map)
            player_data = _serialize_player(engine)
            _validate_player_references(player_data, engine.data)
            address = SceneAddress.from_player(player_data, world_data)
            _validate_pending_arrivals(player_data, world_data)
            payloads = self.cache.snapshot(address, engine.local_map, engine.entities, engine.data)
            identities = set()
            for raw in payloads.values():
                _claim_individuals(pickle.loads(raw).entities, identities)
            for category in ('live_pursuers', 'pending_pursuer_arrivals'):
                for row in player_data.get(category, []):
                    _validate_entities([row['entity']], engine.data)
                    _validate_transfer_actor(row['entity'])
                    _claim_individuals([row['entity']], identities)
            payloads.update({'world.json': encoded(world_data), 'player.json': encoded(player_data),
                'meta.json': encoded(dict(save_version=SAVE_VERSION, saved_at=datetime.datetime.now().isoformat(),
                    world_x=engine.world_x, world_y=engine.world_y, turn=engine.world_time.turn,
                    moon_phase=engine.world_time.moon_phase_name))})
            generation, path, token = self.store.publish(payloads, self.generation, self._head_token, self._checkpoint_fault)
            self.generation = generation
            self._head_token = token
            self.cache.base_path = path
            self.recovery_notice = None
            engine.log.add('Progress preserved.', LIFE_GREEN)
            return True
        except Exception as error:
            self.last_error = str(error)
            engine.log.add(f'Save failed: {error}', FRESH_WOUND)
            return False

    def _prepare(self, engine, path):
        world_data, player_data, address = self._records(path)
        _validate_player_references(player_data, engine.data)
        _validate_pending_arrivals(player_data, world_data)
        cold_cache = ChunkCache(self.save_path, base_path=path)
        # All scenes belong to the checkpoint: validate even inactive owners
        # before installing any player/world/cache reference.
        identities = set()
        for scene in sorted((path / 'chunks').glob('*.pkl')):
            cached = cold_cache._read(scene)
            _validate_entities(cached.entities, engine.data, cached.local_map)
            _claim_individuals(cached.entities, identities)
            _deserialize_entities(cached.entities, engine)
        cached = address.load(cold_cache)
        if cached is None:
            raise SaveFormatError(f'Missing or invalid active scene record: {address}')
        if (type(player_data.get('x')) is not int or type(player_data.get('y')) is not int
                or not cached.local_map.in_bounds(player_data['x'], player_data['y'])):
            raise SaveFormatError('Invalid player position in active scene')
        for owner in ('live_pursuers', 'pending_pursuer_arrivals'):
            for row in player_data.get(owner, []):
                _validate_entities([row['entity']], engine.data)
                _validate_transfer_actor(row['entity'])
                _claim_individuals([row['entity']], identities)
        actors = _deserialize_entities(cached.entities, engine)
        from world.world_map import WorldMap
        world = WorldMap(world_data['width'], world_data['height'])
        _deserialize_world(world_data, world)
        from generation.wilderness import world_policy, provenance as surface_provenance
        world_policy(world, engine.data)
        if world.plan_mode=='shared-v1':
            from generation.world_plan import slice_plan
            import re
            for scene in sorted((path / 'chunks').glob('*.pkl')):
                match=re.fullmatch(r'(\d+)_(\d+)\.pkl',scene.name)
                if not match: continue
                wx,wy=map(int,match.groups());m=cold_cache._read(scene).local_map
                # Existing unversioned owner records remain authoritative. The
                # required-reference contract belongs to explicitly generated G3
                # surfaces, not generic LocalMaps used by other state systems.
                chunk=world.get(wx,wy)
                if chunk is None: raise SaveFormatError('surface owner has no world Chunk: '+scene.name)
                map_revision=getattr(m,'generation_revision',None)
                chunk_revision=getattr(chunk,'generation_revision',None)
                if map_revision not in ('wg3','wg4','wg5','wg6','wg7','wg8','wg9') and chunk_revision not in ('wg3','wg4','wg5','wg6','wg7','wg8','wg9'):
                    if map_revision not in (None,'legacy-unversioned','wg1','wg2') or chunk_revision not in (None,'legacy-unversioned','wg1','wg2'):
                        raise SaveFormatError('unsupported surface generation revision: '+scene.name)
                    continue
                if map_revision not in ('wg3','wg4','wg5','wg6','wg7','wg8','wg9') or chunk_revision!=map_revision:
                    raise SaveFormatError('missing/incoherent generated scene revision: '+scene.name)
                if getattr(m, 'surface_provenance', None) != surface_provenance(world, chunk):
                    raise SaveFormatError('incoherent surface policy provenance: '+scene.name)
                provenance=getattr(m,'plan_provenance',None)
                if not isinstance(provenance,dict) or provenance.get('mode')!='shared-v1': raise SaveFormatError('missing required shared scene references: '+scene.name)
                section=slice_plan(world.plan,wx,wy)
                for key in ('routes','crossings','placements'):
                    if sorted(provenance.get(key,[]))!=sorted(r['id'] for r in section[key]): raise SaveFormatError('corrupt G3 scene '+key+' references: '+scene.name)
                if world.plan['version']>=5:
                    for key,registry in (('paths','paths'),('compounds','sites')):
                        if sorted(provenance.get(key,[]))!=sorted(r['id'] for r in section[registry]):raise SaveFormatError('corrupt G7 scene '+key+' references: '+scene.name)
                if world.plan['version'] in (6,7) and sorted(provenance.get('public_spaces',[]))!=sorted(c['id'] for c in section['public_spaces']):
                    raise SaveFormatError('corrupt G8 public-space scene references: '+scene.name)
                if map_revision=='wg3' and world.plan['generation_revision']!='wg3':raise SaveFormatError('G3 scene cannot consume a G4 plan')
                if map_revision in ('wg4','wg5','wg6','wg7','wg8','wg9'):
                    from generation.placement import digest
                    from generation.scene_adapters import adapter
                    expected={'plan_revision':world.plan['generation_revision'],'plan_version':world.plan['version'],
                              'plan_identity':digest(world.plan),'dependency_projection':'structure-v1',
                              'adapter':adapter(map_revision,world.plan['version'])}
                    if any(provenance.get(k)!=v for k,v in expected.items()):raise SaveFormatError('incoherent plan/adapter provenance: '+scene.name)
        stage = copy.copy(engine)
        stage.player = copy.copy(engine.player)
        for component in ('fighter', 'needs', 'corruption', 'inventory', 'equipment', 'light_source', 'language', 'perks', 'level'):
            setattr(stage.player, component, None)
        stage.world_time = copy.copy(engine.world_time)
        stage.rng = copy.deepcopy(engine.rng)
        _deserialize_player(player_data, stage)
        # Preflight derived components without touching the old hook registry.
        stage.hooks = copy.deepcopy(engine.hooks)
        if stage.player.needs and stage.data.survival:
            stage.player.needs.configure(stage.data.survival)
        stage._register_player_perks()
        stage._update_warmth()
        return stage, world, cold_cache, cached.local_map, actors

    def load(self, engine, previous=False):
        self.last_error = None
        try:
            token = self.store.token()
            candidates = self._candidates()
        except Exception as error:
            self.last_error = 'Cannot read checkpoint: ' + str(error)
            engine.log.add('Load failed: ' + self.last_error, FRESH_WOUND)
            return False
        errors = list(self.store.errors)
        if not candidates and not errors:
            try:
                self.startup_state()
            except Exception as error:
                errors.append(str(error))
        if previous:
            refs = self.store.references()
            # Roll back relative to the published head, not the recovered list.
            candidates = [(g, p) for g, p in candidates if refs and g != refs[0]]
        selected = None
        for generation, path in candidates:
            try:
                selected = (generation, self._prepare(engine, path))
                break
            except Exception as error:
                errors.append(f'{generation or "legacy"}: {error}')
        if selected is None:
            self.last_error = 'No recoverable checkpoint: ' + '; '.join(errors or ['no published save'])
            engine.log.add('Load failed: ' + self.last_error, FRESH_WOUND)
            return False
        try:
            unchanged = self.store.token() == token
            comparison_error = 'Checkpoint changed during load; retry loading'
        except Exception as error:
            unchanged = False
            comparison_error = 'Cannot verify checkpoint after load: ' + str(error)
        if not unchanged:
            self.last_error = comparison_error
            engine.log.add('Load failed: ' + self.last_error, FRESH_WOUND)
            return False
        generation, (stage, world, cache, local_map, actors) = selected
        # Everything that may reject persisted data has completed independently.
        # Retain the player object's identity for other engine consumers.
        old_player = engine.player
        old_items = list(getattr(getattr(old_player, 'inventory', None), 'items', []))
        old_items += list(getattr(getattr(old_player, 'equipment', None), 'slots', {}).values())
        changes = {k: v for k, v in vars(stage).items() if k != 'player' and v is not vars(engine).get(k)}
        engine.__dict__.update(changes)
        old_player.__dict__.clear()
        old_player.__dict__.update(vars(stage.player))
        for item in old_items:
            if item is not None:
                item.equipped = False
        engine.world_map, engine.local_map = world, local_map
        engine.entities = [old_player] + actors
        engine._pending_transfer = []
        self.cache = cache
        self.generation = generation
        self._head_token = token
        self._needs_load = False
        refs = self.store.references()
        recovered = bool(errors or (refs and generation != refs[0]))
        self.recovery_notice = ('Previous checkpoint restored.' if previous else 'Recovered an earlier complete checkpoint.') if (previous or recovered) else None
        engine._restore_loaded_state()
        engine._update_fov()
        engine.log.add(self.recovery_notice or 'The world reassembles itself around you.', LIFE_GREEN)
        return True

    def save_exists(self):
        return bool(self._candidates())

    def delete_slot(self):
        self.store.delete()
        self.cache = ChunkCache(self.save_path)
        self.generation = self._head_token = None
        self._needs_load = False


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
        "waystone_pos":    list(td.waystone_pos) if td.waystone_pos is not None else None,
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
            "generation_revision": getattr(chunk, "generation_revision", None),
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
                        "width": getattr(c, "width", 0),
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
        "generation_revision": getattr(world_map, "generation_revision", "legacy-unversioned"),
        "plan_mode": getattr(world_map, "plan_mode", "legacy"),
        "plan": getattr(world_map, "plan", None),
        "surface_schema": getattr(world_map, "surface_schema", 0),
        "surface_policy": getattr(world_map, "surface_policy", None),
        "vukh_x":         world_map.vukh_x,
        "vukh_y":         world_map.vukh_y,
        "start_wx":       world_map.start_wx,
        "start_wy":       world_map.start_wy,
        "capital_chunks": sorted(world_map.capital_chunks),
        "town_chunks":    sorted(world_map.town_chunks),
        "road_tiles":     [[k[0], k[1], v] for k, v in sorted(world_map.road_tiles.items())],
        "chunks":         chunks,
        "myth":           world_map.myth.to_dict() if world_map.myth else None,
        "town_groups":    {str(k): v for k, v in world_map.town_groups.items()},
        "town_chunk_ids": [[k[0], k[1], v] for k, v in sorted(world_map.town_chunk_ids.items())],
        "chunk_names":    [[k[0], k[1], v] for k, v in sorted(world_map.chunk_names.items())],
    }


def _deserialize_world(data: dict, world_map: "WorldMap") -> None:
    from world.world_map import Chunk, RegionType, SubMap, ConnectorType
    from generation.world_plan import validate_plan
    mode=data.get('plan_mode','legacy')
    if mode not in ('legacy','shared-v1'):
        raise SaveFormatError('unsupported world plan mode')
    if mode=='shared-v1':
        validate_plan(data.get('plan'),data['width'],data['height'])
        if data['plan']['seed']!=data['seed']: raise SaveFormatError('world/plan seed mismatch')
    elif data.get('plan') is not None or data.get('generation_revision') in ('wg3','wg4','wg5','wg6','wg7','wg8','wg9'):
        raise SaveFormatError('missing required G3 plan mode or unexpected legacy plan')
    world_map.plan_mode=mode
    world_map.plan=data.get('plan')
    world_map.surface_schema=data.get('surface_schema',0)
    world_map.surface_policy=data.get('surface_policy')
    from generation.wilderness import world_policy
    world_policy(world_map)

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
            world_seed          = data.get("seed", 0),
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
        chunk.generation_revision = cdata.get("generation_revision")
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
                waystone_pos    = tuple(td_raw['waystone_pos']) if td_raw.get('waystone_pos') is not None else None,
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
                    width=c.get("width", 0),
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

    world_map.generation_revision = data.get("generation_revision", "legacy-unversioned")
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
    if mode=='shared-v1':
        from generation.plan_integrity import world_membership
        world_membership(world_map)

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
    if inv is None:
        raise SaveFormatError("Player inventory component is required")
    # Object identity is used only to build this snapshot's row references.
    # Every row is serialized; invalid definitions fail, never compact the list.
    rows = {id(item): index for index, item in enumerate(inv.items)}
    if len(rows) != len(inv.items):
        raise SaveFormatError("Inventory contains the same object more than once")
    equipment = {}
    for slot, item in p.equipment.slots.items():
        if item is not None and id(item) not in rows:
            raise SaveFormatError(f"Equipment {slot} refers to an item outside inventory")
        equipment[slot] = ({"inventory_index": rows[id(item)], "item_id": item.item_id}
                           if item is not None else None)

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
        "component_state": serialize_runtime(engine),
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
            "whisper_cooldown": corrupt._whisper_cooldown,
        } if corrupt else None,
        "inventory": {
            "capacity": inv.capacity,
            "items": [serialize_item(i) for i in inv.items],
        },
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
            "shown_lexicon_hint": p.language.shown_lexicon_hint,
        } if getattr(p, "language", None) else None,
        "perks": {
            "acquired":        list(p.perks.acquired),
            "perk_state":      p.perks.perk_state,
            "affinity_scores": p.perks.affinity_scores,
        } if getattr(p, "perks", None) else None,
        "equipment": equipment,
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
            "pull_thresholds": list(getattr(engine, "_pull_thresholds_fired", set())),
        },
        "weather": getattr(engine, "weather", None) and engine.weather.to_dict(),
        "live_pursuers": [
            {"entity": _serialize_entity(e), "wx": wx, "wy": wy, "submap_id": sub_id}
            for e, wx, wy, sub_id in getattr(engine, "_live_pursuers", [])
        ],
        "pending_pursuer_arrivals": [
            {"entity": _serialize_entity(pa["entity"]),
             "entry_x": pa["entry_x"], "entry_y": pa["entry_y"],
             "delay": pa["delay"],
             **_pending_destination(pa, {
                 "world_x": engine.world_x, "world_y": engine.world_y,
                 "current_submap_id": engine.current_submap_id})}
            for pa in getattr(engine, "_pending_pursuer_arrivals", [])
        ],
        "sprint_turns_remaining":    getattr(engine, "sprint_turns_remaining", 0),
        "sprint_cooldown_remaining": getattr(engine, "sprint_cooldown_remaining", 0),
        "player_move_accumulator":   getattr(engine, "player_move_accumulator", 0.0),
        "moveset_cooldowns":         getattr(engine, "moveset_cooldowns", {}),
        "creature_knowledge":        getattr(engine, "creature_knowledge", {}),
    }


def _validate_player_references(saved: dict, data) -> None:
    from components.equipment import SLOTS
    validate_components(saved)
    inv = saved.get("inventory")
    if not isinstance(inv, dict) or not isinstance(inv.get("items"), list):
        raise SaveFormatError("inventory must be an object with capacity and items array")
    capacity = inv.get("capacity")
    if type(capacity) not in (int, float) or not math.isfinite(capacity) or capacity <= 0:
        raise SaveFormatError("inventory.capacity must be a positive finite number")
    for index, row in enumerate(inv["items"]):
        item_id = row.get("item_id") if isinstance(row, dict) else None
        if not isinstance(item_id, str) or item_id not in data.items:
            raise SaveFormatError(f"inventory row {index}: unknown item definition {item_id!r}")
        validate_item(row, f"inventory row {index}")
    equipment = saved.get("equipment")
    if not isinstance(equipment, dict):
        raise SaveFormatError("equipment must be an object")
    for slot, ref in equipment.items():
        if slot not in SLOTS:
            raise SaveFormatError(f"Unknown equipment slot {slot!r}")
        if ref is None:
            continue
        if not isinstance(ref, dict):
            raise SaveFormatError(f"Equipment {slot}: expected inventory reference object or null")
        index = ref.get("inventory_index")
        if type(index) is not int or not 0 <= index < len(inv["items"]):
            raise SaveFormatError(f"Equipment {slot}: invalid inventory_index {index!r}")
        if ref.get("item_id") != inv["items"][index]["item_id"]:
            raise SaveFormatError(f"Equipment {slot}: item_id does not match inventory row {index}")
    light = saved.get("light_source")
    if light is not None:
        if not isinstance(light, dict) or type(light.get("active")) is not bool:
            raise SaveFormatError("light_source must be null or a light object with boolean active")
        if light["active"]:
            offhand = equipment.get("offhand")
            if offhand is None or not data.items[offhand["item_id"]].get("light"):
                raise SaveFormatError("Active item light requires an equipped offhand light")
            row = inv["items"][offhand["inventory_index"]]
            if "light_data" in row and not row["light_data"]:
                raise SaveFormatError("Active item light requires restored offhand light_data")


def _deserialize_player(data: dict, engine: "Engine") -> None:
    from components.fighter import Fighter
    from components.needs import Needs
    from components.corruption import Corruption
    from components.inventory import Inventory
    from components.light_source import LightSource

    _validate_player_references(data, engine.data)
    p            = engine.player
    # Replacement is independent of the pre-load player component graph.
    for component in ("fighter", "needs", "corruption", "language", "perks", "level"):
        setattr(p, component, None)
    engine._attuned_bonus_active = False
    # Clear flags even on old objects held by callers; then replace belongings.
    old_items = list(getattr(getattr(p, "inventory", None), "items", []))
    old_items += list(getattr(getattr(p, "equipment", None), "slots", {}).values())
    for old in old_items:
        if old is not None:
            old.equipped = False
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

    if data.get("fighter") is not None:
        f = data["fighter"]
        p.fighter              = Fighter(f["max_hp"], f["power"], f["defense"])
        p.fighter.body_id      = f.get("body_id", "body_player")
        p.fighter.hp           = f.get("hp", f["max_hp"])
        p.fighter._dead        = p.fighter.hp <= 0
        p.is_alive             = not p.fighter._dead
        p.fighter.effective_av = f.get("effective_av", 0)

    if data.get("needs") is not None:
        n = data["needs"]
        p.needs        = Needs()
        p.needs.hunger = n["hunger"]
        p.needs.thirst = n["thirst"]

    if data.get("corruption") is not None:
        c = data["corruption"]
        p.corruption       = Corruption()
        p.corruption.value = c["value"]
        p.corruption._whisper_cooldown = c.get("whisper_cooldown", 0)

    if data.get("inventory"):
        from engine.item_factory import ItemFactory
        inv_data = data["inventory"]
        p.inventory = Inventory(capacity=inv_data["capacity"])
        factory = ItemFactory(engine.data)
        for idata in inv_data["items"]:
            item_id = idata["item_id"]
            item = factory.create(item_id, p.x, p.y)
            if item is None:
                raise SaveFormatError(f"Cannot reconstruct inventory item {item_id!r}")
            restore_item(item, idata)
            # Restoration is not acquisition. Preserve rows even if current
            # definitions make the saved bag overweight (capacity policy: B2).
            p.inventory.items.append(item)

    p.light_source = None
    if data.get("light_source"):
        ls = data["light_source"]
        p.light_source = LightSource(
            radius  = ls["radius"],
            color   = tuple(ls["color"]),
            falloff = ls["falloff"],
            flicker = ls["flicker"],
            active  = ls["active"],
        )

    if data.get("language") is not None:
        from components.language import Language
        ld   = data["language"]
        lang = Language()
        lang.known_deep_words   = set(ld.get("known_deep_words", []))
        lang.translation_events = ld.get("translation_events", {})
        lang.taught_texts       = set(ld.get("taught_texts", []))
        lang.recovered_spans    = set(tuple(s) for s in ld.get("recovered_spans", []))
        lang.recovered_text     = {
            tuple(ast.literal_eval(k)): v
            for k, v in ld.get("recovered_text", {}).items()
        }
        lang.shown_lexicon_hint = ld.get("shown_lexicon_hint", False)
        p.language = lang

    if data.get("perks") is not None:
        from components.perks import Perks
        pd     = data["perks"]
        perks  = Perks()
        perks.acquired        = set(pd.get("acquired", []))
        perks.perk_state      = pd.get("perk_state", {})
        perks.affinity_scores = pd.get("affinity_scores", {})
        p.perks = perks

    if data.get("level") is not None:
        from components.level import LevelComponent
        ld = data["level"]
        lc = LevelComponent()
        lc.level               = ld.get("level", 1)
        lc.exp                 = ld.get("exp", 0)
        lc.exp_to_next         = ld.get("exp_to_next", 100)
        lc.perk_points         = ld.get("perk_points", 0)
        lc.total_levels_gained = ld.get("total_levels_gained", 0)
        p.level = lc

    # Missing optional records reset; they never inherit unsaved session values.
    r = data.get("resonance") or {}
    engine.resonance_exposure = r.get("exposure", 0.0)
    engine.corruption = r.get("corruption", 0.0)
    engine._corruption_thresholds = set(r.get("thresholds", []))
    engine._pull_thresholds_fired = set(r.get("pull_thresholds", []))
    from engine.weather import WeatherSystem
    engine.weather = (WeatherSystem.from_dict(data["weather"], engine.rng)
                      if data.get("weather") else WeatherSystem(engine.rng))
    engine.weather.load_mechanics(engine.data.weather_defs)
    restore_runtime(engine, data)

    # Live pursuers
    engine._live_pursuers = []
    for lp in data.get("live_pursuers", []):
        ents = _deserialize_entities([lp["entity"]], engine)
        if ents:
            engine._live_pursuers.append((ents[0], lp["wx"], lp["wy"], lp.get("submap_id")))

    # Pending pursuer arrivals
    engine._pending_pursuer_arrivals = []
    for pa in data.get("pending_pursuer_arrivals", []):
        ents = _deserialize_entities([pa["entity"]], engine)
        if ents:
            engine._pending_pursuer_arrivals.append({
                "entity":  ents[0],
                "entry_x": pa["entry_x"],
                "entry_y": pa["entry_y"],
                "delay":   pa["delay"],
                **_pending_destination(pa, data),
            })

    # Sprint state
    engine.sprint_turns_remaining    = data.get("sprint_turns_remaining", 0)
    engine.sprint_cooldown_remaining = data.get("sprint_cooldown_remaining", 0)
    engine.player_move_accumulator   = data.get("player_move_accumulator", 0.0)
    engine.moveset_cooldowns         = data.get("moveset_cooldowns", {})
    engine.creature_knowledge        = data.get("creature_knowledge", {})

    # Restore equipped items after inventory is fully reconstructed
    _restore_equipment(p, data.get("equipment", {}), engine.data)
    p.inventory.bind_carrying(p.equipment, engine.data.items)


def _restore_equipment(player, saved_equipment: dict, data) -> None:
    """Replace all slots, then link only exact validated inventory rows."""
    from components.equipment import Equipment
    from engine.item_system import _recompute_effective_av

    for item in getattr(getattr(player, "equipment", None), "slots", {}).values():
        if item is not None:
            item.equipped = False
    player.equipment = Equipment()
    for item in player.inventory.items:
        item.equipped = False
    for slot, ref in saved_equipment.items():
        if ref is not None:
            item = player.inventory.items[ref["inventory_index"]]
            player.equipment.equip(item, slot)

    light = player.light_source
    offhand = player.equipment.slots["offhand"]
    if light is not None and offhand is not None and offhand.light_data:
        light._item_ref = offhand
        light._item_id = offhand.item_id
        light._burn_turns = offhand.burn_turns or 600
        light._turns_used = offhand.turns_lit
    _recompute_effective_av(player, data)


def _serialize_entity(entity: "Actor") -> dict:
    """Convert an Actor to a serializable dict."""
    fighter = getattr(entity, "fighter",    None)
    ai      = getattr(entity, "ai",         None)
    percep  = getattr(entity, "perception", None)
    creature_id = getattr(entity, "_creature_id", None)
    if getattr(entity, "is_alive", True) and not creature_id:
        raise SaveFormatError(f"Actor {entity.name!r} has no stable _creature_id")

    return {
        "type":            "actor",
        **({"individual_id": entity._individual_id} if getattr(entity, '_individual_id', None) is not None else {}),
        **({"local_target": copy.deepcopy(ai.local_target)} if getattr(ai, 'local_target', None) is not None else {}),
        "id":              creature_id,
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
        "component_state": serialize_actor_runtime(entity),
        "ai_type":  type(ai).__name__ if ai else None,
        "ai_state": ai.state.value    if ai else None,
        "home_x":   ai.home_x         if ai else None,
        "home_y":   ai.home_y         if ai else None,
        "pursuit_turns_without_contact": ai.pursuit_turns_without_contact if ai else 0,
        "move_accumulator": ai.move_accumulator if ai else 0.0,
        "faction":  percep.faction    if percep else None,
        "hostile_to": percep.hostile_to if percep else None,
        "sight_radius":   percep.sight_radius   if percep else 8,
        "hearing_radius": percep.hearing_radius if percep else 5,
        "sees_in_dark":   percep.sees_in_dark   if percep else False,
        "wander_radius":  ai.wander_radius      if ai else 8,
        # Null hibernating means the first ability tick has not initialized it.
        "lurker": {
            "hibernating": getattr(entity, "_hibernating", None),
            "ambush_ready": getattr(entity, "_ambush_ready", False),
            "ai_triggered": getattr(ai, "_triggered", False),
        } if creature_id == "stone_lurker" else None,
    }


def _is_player(entity: "Actor") -> bool:
    return entity.name == "Player"


def _validate_transfer_actor(row):
    if row.get('local_target') is not None:
        raise SaveFormatError('Local rival intent cannot own a player-pursuer transfer')


def _claim_individuals(rows, identities):
    for row in rows:
        identity = row.get('individual_id')
        if identity is not None:
            if identity in identities:
                raise SaveFormatError('Duplicate individual_id across scene/transfer owners')
            identities.add(identity)


def _validate_entities(rows, data, local_map=None) -> None:
    if not isinstance(rows, list):
        raise SaveFormatError("Scene entities must be an array (possibly empty)")
    from engine.local_rivals import validate_row
    identities = set()
    if local_map is not None:
        sequence = getattr(local_map, '_rival_identity_sequence', 0)
        if type(sequence) is not int or not 0 <= sequence < 10**16:
            raise SaveFormatError('Invalid rival identity sequence')
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SaveFormatError(f"Actor row {index} must be an object")
        validate_row(row, local_map)
        individual = row.get('individual_id')
        if individual is not None:
            if individual in identities:
                raise SaveFormatError('Duplicate individual_id in owning scene')
            identities.add(individual)
        if not row.get("is_alive", True):
            continue  # Existing corpse representation; broader remains state: B2.
        identity = row.get("id")
        if not isinstance(identity, str) or identity not in data.entities:
            raise SaveFormatError(f"Actor row {index}: invalid stable creature identity {identity!r}")
        validate_actor_runtime(row, local_map)
        if identity == "stone_lurker":
            state = row.get("lurker")
            if (not isinstance(state, dict) or "hibernating" not in state
                    or (state["hibernating"] is not None and type(state["hibernating"]) is not bool)
                    or type(state.get("ambush_ready")) is not bool
                    or type(state.get("ai_triggered")) is not bool):
                raise SaveFormatError(f"Actor row {index}: invalid stone_lurker lifecycle")


def _deserialize_entities(
    entity_dicts: list[dict],
    engine:       "Engine",
) -> list:
    """Reconstruct Actor objects from serialized dicts."""
    from engine.creature_factory import CreatureFactory
    factory  = CreatureFactory(engine.data)
    restored = []
    _validate_entities(entity_dicts, engine.data)

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
        creature_id = d["id"]
        actor = factory.spawn(creature_id, d["x"], d["y"])

        if actor is None:
            raise SaveFormatError(f"Cannot reconstruct creature {creature_id!r}")

        actor.tile = d.get("tile", actor.tile)
        actor.name = d.get("name", actor.name)
        actor.blocks_movement = d.get("blocks_movement", actor.blocks_movement)
        if creature_id == "stone_lurker":
            state = d["lurker"]
            if state["hibernating"] is not None:
                actor._hibernating = state["hibernating"]
                # Dormant presentation follows the current ability's rule.
                actor.tile = "rock" if actor._hibernating else "stone_lurker"
            actor._ambush_ready = state["ambush_ready"]
            actor.ai._triggered = state["ai_triggered"]

        # Restore fighter state from saved state
        fighter = getattr(actor, "fighter", None)
        if fighter and d.get("fighter"):
            fd = d["fighter"]
            fighter.max_hp       = fd.get("max_hp", fighter.max_hp)
            fighter.power        = fd.get("power", fighter.power)
            fighter.defense      = fd.get("defense", fighter.defense)
            fighter.body_id      = fd.get("body_id", "body_human")
            fighter.hp           = fd.get("hp", fighter.max_hp)
            fighter.effective_av = fd.get("effective_av", fighter.effective_av)
            fighter._dead = fighter.hp <= 0

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
            ai.move_accumulator = d.get("move_accumulator", 0.0)

        if actor.perception is not None:
            for field in ("faction", "hostile_to", "sight_radius", "hearing_radius", "sees_in_dark"):
                if field in d and d[field] is not None:
                    setattr(actor.perception, field, copy.deepcopy(d[field]))
        if ai is not None:
            ai.wander_radius = d.get("wander_radius", ai.wander_radius)
        restore_actor_runtime(actor, d)
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
