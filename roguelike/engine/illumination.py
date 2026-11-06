"""Finite, deterministic scene light; no exploration, observer or render input.

Ambient >= 0.1 or any obstructed source footprint is lit. Reach is Euclidean
tile radius, inclusive at its edge. OR composition cannot extend source reach.
The engine owns a single derived cache; no mask is saved in a scene.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import tcod
from tcod import libtcodpy
from engine.held_light import active_item, MAX_RADIUS
from engine.palette import BELL_BRASS

LIT_THRESHOLD = 0.1


def ambient(engine, *, world_x=None, world_y=None, submap_id=None, current=True):
    if current:
        world_x, world_y, submap_id = engine.world_x, engine.world_y, engine.current_submap_id
    chunk = engine.world_map.get(world_x, world_y)
    if submap_id is not None:
        matches = [s for s in getattr(chunk, 'submaps', ()) if s.submap_id == submap_id]
        zone = engine.data.zones.get(matches[0].submap_type, {}) if len(matches) == 1 else {}
        value = zone.get('ambient_light', 0.0)
        return engine.world_time.get_ambient_light(value, False)
    value, outdoor = 1.0, True
    for zone_id, _ in getattr(chunk, 'zones', ()):
        zone = engine.data.zones.get(zone_id)
        if zone:
            value, outdoor = zone.get('ambient_light', 1.0), zone.get('category') != 'dungeon'
            break
    return engine.world_time.get_ambient_light(value, outdoor)


def emission(kind, identifier, value):
    if kind == 'terrain' and identifier == 'campfire_lit' and type(value) is float and value == 0.7:
        return 5
    # Zero/absent is inactive. Unsupported data never reaches tcod radius=0.
    return value if type(value) is int and 0 < value <= MAX_RADIUS else 0


def geometry(local_map, data):
    result = local_map.transparent.copy()
    for (x, y), identifier in local_map.decor.items():
        if local_map.in_bounds(x, y) and data.decoratives.get(identifier, {}).get('blocks_sight', False):
            result[x, y] = False
    return result


def footprint(transparency, x, y, radius):
    if type(radius) is not int or radius <= 0:
        raise ValueError('source footprint requires positive finite tile reach')
    xs, ys = np.ogrid[:transparency.shape[0], :transparency.shape[1]]
    return (tcod.map.compute_fov(transparency, (x, y), radius=radius+1,
            light_walls=True, algorithm=libtcodpy.FOV_SYMMETRIC_SHADOWCAST)
            & ((xs-x)**2 + (ys-y)**2 <= radius**2))


@dataclass(frozen=True)
class SceneLight:
    ambient: float
    ambient_color: tuple
    lit: np.ndarray
    emitted: np.ndarray
    transparency: np.ndarray
    sources: tuple


def scene_light(engine, local_map=None, *, fallback_ambient=0.0):
    local_map = engine.local_map if local_map is None else local_map
    current = local_map is engine.local_map
    intensity, color = ambient(engine) if current else (fallback_ambient, (1.0, 1.0, 1.0))
    held = active_item(engine.player) if current else None
    held_key = (engine.player.x, engine.player.y, held.held_light['radius'],
                repr(held.light_data)) if held else None
    # Content keys cover direct legacy array/decor writes and loaded definitions.
    # Cache lifetime is one scene result, not a world light simulation.
    definitions = tuple((kind, k, repr(v)) for kind, table in
        (('terrain', engine.data.terrain), ('decor', engine.data.decoratives))
        for k, v in sorted(table.items()) if v.get('light_emit') or v.get('blocks_sight'))
    key = (id(local_map), local_map.transparent.tobytes(), local_map.tiles['terrain'].tobytes(),
           tuple(sorted(local_map.decor.items())), definitions, held_key, intensity, tuple(color))
    cached = getattr(engine, '_scene_light_cache', None)
    if cached is not None and cached[0] == key:
        return cached[1]
    transparent = geometry(local_map, engine.data)
    emitted = np.zeros(transparent.shape, dtype=bool)
    sources = []

    def add(kind, identifier, x, y, radius, raw):
        if not radius or not local_map.in_bounds(x, y):
            return
        mask = footprint(transparent, x, y, radius)
        emitted[:] |= mask
        mask.flags.writeable = False
        sources.append((kind, identifier, x, y, radius, raw, mask))

    for identifier in np.unique(local_map.tiles['terrain']):
        raw = engine.data.terrain.get(str(identifier), {})
        radius = emission('terrain', str(identifier), raw.get('light_emit'))
        if radius:
            for x, y in np.argwhere(local_map.tiles['terrain'] == identifier):
                add('terrain', str(identifier), int(x), int(y), radius, raw)
    for (x, y), identifier in sorted(local_map.decor.items()):
        raw = engine.data.decoratives.get(identifier, {})
        add('decor', identifier, x, y, emission('decor', identifier, raw.get('light_emit')), raw)
    if held:
        add('held', held.item_id, engine.player.x, engine.player.y, held.held_light['radius'], held.light_data)
    lit = emitted | (intensity >= LIT_THRESHOLD)
    for array in (lit, emitted, transparent): array.flags.writeable = False
    result = SceneLight(intensity, tuple(color), lit, emitted, transparent, tuple(sources))
    engine._scene_light_cache = (key, result)
    return result


def render(engine):
    import pygame
    field = scene_light(engine)
    local_map = engine.local_map
    visible = local_map.visible
    result = np.zeros_like(local_map.light_map)
    result[visible] = np.array(field.ambient_color) * field.ambient
    xs, ys = np.ogrid[:local_map.width, :local_map.height]
    for kind, _, x, y, radius, raw, mask in field.sources:
        tint = raw.get('color' if kind == 'held' else 'light_color', BELL_BRASS)
        falloff = raw.get('falloff', 1.8) if kind == 'held' else 1.0
        if type(falloff) not in (int, float) or not math.isfinite(falloff) or falloff <= 0:
            falloff = 1.0
        distance = np.sqrt((xs-x)**2 + (ys-y)**2)
        # A visible nonzero edge makes the inclusive mechanical boundary legible.
        strength = 0.25 + 0.75 * np.maximum(0, 1-(distance/radius)**falloff)
        if raw.get('flicker') or raw.get('light_mode') == 'pulse':
            strength *= .96 + .04 * math.sin(pygame.time.get_ticks()/180.0 + x*.37+y*.59)
        contribution = strength[..., None] * (np.array(tint)/255.0)
        result = np.maximum(result, np.where((mask & visible)[..., None], contribution, 0))
    local_map.light_map[:] = np.clip(result, 0, 1)
