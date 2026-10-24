# WFC ground palettes and the legacy town route

Wave Function Collapse (WFC) is present as a bounded tile-adjacency solver and as ground fill in the preserved legacy town generator. **It is not the active ground-composition step for fresh G8 shared-plan towns.** The planned surface path builds base terrain, infrastructure and structures directly, then applies its final dressing rules. Changing a legacy town WFC file may therefore have no visible effect in a fresh planned settlement.

This page documents the current solver and call boundary so you can work on an existing palette or identify the code integration needed for a new use. It does not present the older WFC guide's aesthetic descriptions as observed current behavior.

## Existing files and the consumer

The palette files are `roguelike/data/wfc/town_plaza.json`, `town_block.json` and `town_outskirts.json`. The solver is `roguelike/generation/wfc.py`; the legacy caller `_apply_wfc_fill` is in `generation/town_gen.py`.

A palette has:

```json
{
  "tiles":[
    {"name":"earth","terrain":"packed_earth","weight":3},
    {"name":"path","terrain":"dirt_path","weight":1}
  ],
  "adjacency":{
    "earth":{"N":["earth","path"],"E":["earth","path"],"S":["earth","path"],"W":["earth","path"]},
    "path":{"N":["earth","path"],"E":["earth","path"],"S":["earth","path"],"W":["earth","path"]}
  },
  "fallback":"earth"
}
```

This is an illustrative two-logical-tile palette, not an installed replacement. `name` is the solver's logical ID; `terrain` describes the intended terrain binding. The actual legacy caller supplies a separate logical-ID-to-terrain map. **The solver does not automatically paint the JSON's `terrain` value.** Adding a logical tile also requires its active caller's mapping to be correct.

## Adjacency and weights

Each logical tile has directional allowed-neighbor lists for N/E/S/W. A final solution is validated in both directions for every pair. If A permits B to its east but B does not permit A to its west, that pair cannot appear in a valid result. Directional asymmetry can express useful patterns, but reciprocal pair compatibility still matters.

Weights influence choice among still-possible logical tiles. Adjacency constraints and collapse order affect the final distribution. A weight of one does not mean exactly one occurrence, at most one occurrence or a fixed one-in-N average across a finished map. The historical guide's claim that a low-weight waystone occurs “at most once” is unsupported by this solver; it has no global uniqueness constraint.

Use known logical IDs in adjacency lists, complete all four directions, and keep weights finite and nonnegative with some positive available choice. The WFC JSON loader is less strict than the structure compiler, so do not assume `--catalog` validates a palette's entire adjacency design.

## Solver output and fallback

`WFCSolver.solve(width,height,fixed=None)` returns an **x-major** grid: access a cell as `result[x][y]`. It returns `None` after ten unsuccessful attempts. A supplied `fixed` mapping uses `(x,y)` keys and logical tile names. Unknown fixed tile names are ignored by this implementation, so verify the IDs yourself instead of assuming a typo constrains the solve.

The solver's stored `fallback` is a logical tile name. The legacy `_apply_wfc_fill` caller separately receives a terrain fallback for a failed solve or unmapped logical ID. Those are different values. In the current caller, a failed or invalid result is logged with palette, rectangle, seed/revision and reason before eligible ground is filled with the explicit terrain fallback.

Protected structures, roads, stairs, objects and functional decor are excluded from that fallback painting. The historical G1 74 × 37 outskirts sample recorded bounded fallbacks, not successful solves. Do not increase retries and describe that alone as a verified palette repair.

## Check a palette in isolation

From the repository root, this small check uses the real solver without starting a campaign:

```powershell
@'
import random
import sys
sys.path.insert(0, "roguelike")
from generation.wfc import WFCSolver

solver = WFCSolver.from_json("roguelike/data/wfc/town_block.json", random.Random(20261023))
grid = solver.solve(6, 6)
if grid is None:
    raise SystemExit("No solution within the solver's ten attempts")
assert solver.valid(grid, 6, 6)
print("Solved and adjacency-validated:", len(grid), "x", len(grid[0]))
'@ | & $ResonancePython -
```

Small-grid success establishes one bounded solve, not success at the production rectangle. Test representative actual dimensions and several declared seeds if you are changing the palette's logic. Record failures as failures and inspect which pair or fixed constraint caused the contradiction.

## Add a new palette to an active use

Creating a JSON file alone does not schedule the solver. Identify the target generation route, its intended rectangle, protected-cell handling, logical-to-terrain mapping and explicit fallback. Add or change that call deliberately. For fresh planned G8 towns, incorporating WFC would be a code change to the planned pipeline, with final road/door/contents access preserved and appropriate tests. It is outside routine palette tuning.

Keep gameplay-critical waystones or stairs under their explicit ownership/placement rules. A low-probability decorative sampler cannot guarantee a required unique interactive destination.

## Sources

- [Current solver, attempts and final directional validation](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/wfc.py)
- [Legacy fill call and fallback protection](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/town_gen.py)
- [Fresh planned surface route](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/planned_scene.py)
- [Historical WFC sample and its declared limits](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/docs/owner/WORLDGEN_G1.md)
