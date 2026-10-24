"""Whole mouths shift into the non-corner interval without reducing legal width."""
from __future__ import annotations
import random
import math
from generation.context import GenerationError
from generation.context import GENERATION_REVISION, stable_seed

OFFSETS = {'north': (0, -1), 'south': (0, 1), 'east': (1, 0), 'west': (-1, 0)}
OPPOSITE = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}


def edge_key(wx, wy, edge):
    dx, dy = OFFSETS[edge]
    return tuple(sorted(((wx, wy), (wx + dx, wy + dy))))


def river_spec(world_seed, wx, wy, edge):
    key = edge_key(wx, wy, edge)
    # Geography is the preserved G8 baseline, independent of scene revisions.
    rng = random.Random(stable_seed('wg8', world_seed, 'river-edge', key))
    return round(rng.uniform(0.3, 0.7), 2), rng.choice((9, 11, 13)), f'river-edge-{key}'


def quantize(position, length):
    if type(position) not in (int, float) or not math.isfinite(position) or not 0 <= position <= 1:
        raise GenerationError(f'port position {position!r}: expected finite normalized value in [0, 1]')
    return max(1, min(length - 2, int(position * (length - 2)) + 1))


def resolve_mouth(edge, position, width, map_w, map_h, kind='road'):
    if edge not in OFFSETS:
        raise GenerationError(f'port edge {edge!r}: expected north/south/east/west')
    length = map_w if edge in ('north', 'south') else map_h
    if width is None or type(width) is int and width == 0:
        width = 9 if kind == 'river' else 3
    if type(width) is not int or not 1 <= width <= length - 2:
        raise GenerationError(f'{edge} port width {width!r}: expected 1..{length-2} (0/omitted uses feature default)')
    center = quantize(position, length)
    start = max(1, min(length - 1 - width, center - width // 2))
    return start, width, start + width // 2


def mouth(edge, position, width, map_w, map_h, depth=0, kind='road', bank=0):
    start, width, _ = resolve_mouth(edge, position, width, map_w, map_h, kind)
    length = map_w if edge in ('north', 'south') else map_h
    end = min(length - 1, start + width + bank)
    start = max(1, start - bank)
    for a in range(start, end):
        if edge == 'north': yield a, depth
        elif edge == 'south': yield a, map_h - 1 - depth
        elif edge == 'west': yield depth, a
        else: yield map_w - 1 - depth, a


def secondary_bands(world_seed, town_id, role, breadth):
    rng = random.Random(stable_seed(GENERATION_REVISION, world_seed, town_id, role, 'secondary-streets'))
    count = rng.randint(1, 2) if role in ('N', 'S') else rng.randint(2, 3)
    width, margin = 2, 3
    step = max(1, (breadth - 2 * margin - count * width) // (count + 1))
    return [(margin + step + i * (step + width), width) for i in range(count)]


def town_ports(world_seed, town_id, role, w, h):
    """The existing nine-role streets, expressed identically from either neighbour."""
    ports = {edge: [] for edge in OFFSETS}
    def band(edge, start, width):
        length = w if edge in ('north', 'south') else h
        # Small offset avoids roundoff below an integer during floor quantization.
        position = (start + width // 2 - 1 + 1e-7) / (length - 2)
        ports[edge].append((position, width))
    if role in ('C', 'N', 'S'):
        for edge in ('north', 'south'): band(edge, w // 2 - 1, 3)
    if role in ('C', 'E', 'W'):
        for edge in ('east', 'west'): band(edge, h // 2 - 1, 3)
    if role in ('N', 'S'):
        for start, width in secondary_bands(world_seed, town_id, role, h):
            for edge in ('east', 'west'): band(edge, start, width)
    elif role in ('E', 'W'):
        for start, width in secondary_bands(world_seed, town_id, role, w):
            for edge in ('north', 'south'): band(edge, start, width)
    elif role in ('NW', 'NE', 'SW', 'SE'):
        for start, width in secondary_bands(world_seed, town_id, role[0], h):
            band('east' if role[1] == 'W' else 'west', start, width)
        for start, width in secondary_bands(world_seed, town_id, role[1], w):
            band('south' if role[0] == 'N' else 'north', start, width)
    return ports
