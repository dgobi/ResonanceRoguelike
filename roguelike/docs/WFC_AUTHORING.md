# WFC Tileset Authoring Guide

## Overview

The Wave Function Collapse (WFC) system generates varied ground texture within town blocks and plazas. Each WFC tileset is a JSON file in `roguelike/data/wfc/` that defines a set of logical tiles, their adjacency constraints, and their mapping to actual terrain types.

## File Structure

```json
{
  "tiles": [ ... ],
  "adjacency": { ... },
  "fallback": "tile_name"
}
```

### `tiles` array

Each entry defines a logical WFC tile:

```json
{"name": "cobble_clean", "terrain": "cobblestone", "weight": 30}
```

- `name` — internal WFC tile identifier (used in adjacency rules)
- `terrain` — the actual terrain type stamped into the local map (must exist in `data/terrain.json`)
- `weight` — relative probability of this tile being chosen during collapse (higher = more common)

### `adjacency` dict

Maps each tile name to a dict of cardinal directions (`N`, `E`, `S`, `W`), each containing a list of tile names that may appear in that direction:

```json
"cobble_clean": {
  "N": ["cobble_clean", "cobble_cracked"],
  "E": ["cobble_clean", "cobble_cracked"],
  "S": ["cobble_clean", "cobble_cracked"],
  "W": ["cobble_clean", "cobble_cracked"]
}
```

If a tile is not listed as a neighbour in a given direction, it will never appear adjacent to the source tile in that direction. Asymmetric rules are valid and intentional.

### `fallback`

The terrain name used if all WFC attempts fail (after `MAX_ATTEMPTS = 10` retries). Should always be a common, safe terrain type present in `data/terrain.json`.

## Adding a New Tileset

1. Create `roguelike/data/wfc/your_tileset.json` following the structure above.
2. Add any new terrain types referenced by `"terrain"` fields to `data/terrain.json` and `data/tiles.json`.
3. Add sprite entries for new terrain types to `data/sprites/sprite_map.json`.
4. In the generator (e.g. `generation/town_gen.py`), instantiate `WFCSolver.from_json(path, rng)` and call `solver.solve(width, height)`.
5. Map WFC tile names to terrain names using a local dict (see `PLAZA_TERRAIN` / `BLOCK_TERRAIN` in `town_gen.py`), then stamp with `_set_terrain()`.

## Adjacency Design Tips

- **Transitional tiles** (e.g. `cobble_cracked`) should appear in both strict and loose adjacency lists — they act as buffers between clean and degraded areas.
- **Rare tiles** (e.g. `waystone_base`) should only list very common neighbours to prevent isolation contradictions.
- **Keep weights realistic.** A waystone with weight 1 among tiles with weight 20-30 will appear roughly once per 300 tiles on average.
- **Avoid disconnected graphs.** If tile A can only appear next to B, and B cannot appear next to A, the solver will contradict immediately.
- **Test with small grids first.** A 6x6 grid will reveal contradiction-prone rulesets quickly.

## WFC Solver API

```python
from generation.wfc import WFCSolver
import random

rng = random.Random(seed)
solver = WFCSolver.from_json("data/wfc/town_plaza.json", rng)

# Basic solve
result = solver.solve(width, height)
# result: list[list[str]] of tile names (x-major), or None on failure

# With pre-collapsed cells
result = solver.solve(width, height, fixed={(3, 3): "waystone_base"})
```

## Existing Tilesets

### `town_plaza.json`

Used around the road crossing in the NW town quadrant. Produces a cobblestone plaza with organic weathering — clean cobbles near the centre, cracked and mossy variants toward edges, occasional puddles and debris. The waystone tile appears at most once due to its very low weight.

### `town_block.json`

Used to fill block interiors (areas between roads and building footprints). Produces packed earth with dirt paths, weedy cobblestone patches, mud, tall grass, and scattered debris. Gives a neglected urban-wilderness feel to back-lots and alleyways.
