"""The existing one-level special-tile format, shared by buildings and layouts."""
from __future__ import annotations
import math
from generation.context import GenerationError

SUPPORTED = frozenset({'item', 'container', 'scene', 'empty'})
DEFERRED = frozenset({'body', 'stele'})


def resolve_special(spec, rng, source):
    """Return a fresh record; the enclosing coordinates always own the transform."""
    if not isinstance(spec, dict):
        raise GenerationError(f'{source}: special must be an object')
    kind = spec.get('type', spec.get('kind'))
    chosen = spec
    if kind == 'weighted':
        table = spec.get('spawn_table')
        if not isinstance(table, list) or not table:
            raise GenerationError(f'{source}: weighted spawn_table must be nonempty')
        weights = []
        for index, row in enumerate(table):
            if not isinstance(row, dict) or row.get('type', row.get('kind')) not in SUPPORTED:
                raise GenerationError(f'{source}: weighted choice {index} has unsupported type')
            weight = row.get('weight', 1)
            if (type(weight) not in (int, float) or not math.isfinite(weight) or weight < 0):
                raise GenerationError(f'{source}: weighted choice {index} needs a finite nonnegative weight')
            weights.append(weight)
        if not math.isfinite(sum(weights)) or sum(weights) <= 0:
            raise GenerationError(f'{source}: weighted spawn_table needs a positive finite total')
        chosen = rng.choices(table, weights=weights, k=1)[0]
        kind = chosen.get('type', chosen.get('kind'))
    if kind not in SUPPORTED | DEFERRED:
        raise GenerationError(f'{source}: unsupported special type {kind!r}')
    result = dict(chosen, kind=kind, x=spec.get('x', 0), y=spec.get('y', 0), source=source)
    result.pop('type', None)
    return result


def transformed_specials(specials, context, asset, ox, oy, height, flip_v=False):
    result = []
    for index, spec in enumerate(specials):
        source = f'{asset} special[{index}]'
        row = resolve_special(spec, context.rng('weighted-special', asset, ox, oy, index), source)
        x, y = row['x'], row['y']
        if type(x) is not int or type(y) is not int:
            raise GenerationError(f'{source}: coordinates must be integers')
        row['x'], row['y'] = ox + x, oy + (height - 1 - y if flip_v else y)
        result.append(row)
    return result
