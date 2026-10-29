> **Arc A status:** Historical source retained below. Creative intent remains a design reference; technical claims need the [current implementation and authority map](owner/STATUS.md). This banner does not resolve open design decisions.

# Decorative Tile System

Decoratives are a second visual layer rendered above terrain and below entities.
The map owns their IDs and positions; cached/saved maps preserve them. Some
definitions participate in blocking, light, interaction or system-owned state.
Direct authored-room admission is narrower than registry membership; see the
[current furnishing contract](STRUCTURE_AUTHORING.md#w5l-furnish-an-underground-room).

---

## What Decoratives Are

| Property | Value |
|---|---|
| Storage | `local_map.decor: dict[tuple[int,int], str]` — keyed by `(lx, ly)`, value is `decor_id` |
| Render order | Above terrain, below entities |
| Surface | `pygame.SRCALPHA` — background is transparent, floor shows through |
| Persistence | Map/cache/save owned; current catalogue supplies properties and behavior. |
| Collision | Movement uses `blocks_movement`; `blocks_sight` is declared, while FOV uses terrain transparency |
| Sprite | Registered in `data/sprites/sprite_map.json` — same Urizen sheet as tiles |

---

## How to Add a Decorative

### Step 1 — Define the tile in `data/decoratives.json`

```json
{
  "id": "decor_my_thing",
  "ascii": "?",
  "blocks_movement": false,
  "blocks_sight": false
}
```

**Field reference:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique identifier. Convention: `decor_` prefix. |
| `ascii` | string | yes | Single character fallback when no sprite available. |
| `blocks_movement` | bool | yes | Whether entities cannot walk through this tile. |
| `blocks_sight` | bool | yes | Whether this tile blocks FOV line of sight. |

### Step 2 — Add a sprite in `data/sprites/sprite_map.json`

Under the `"tiles"` object, add:

```json
"decor_my_thing": {"sheet": "urizen", "col": 0, "row": 0}
```

Replace `col` with the correct Urizen tile index. Use `sprite_ref.py` to generate
coordinate reference sheets from the spritesheet PNG:

```
python sprite_ref.py assets/sprites/urizen_onebit_tileset__v2d0-Sheet.png 12 12
```

You can also remap a tile in-game with `F12` to find the right column without restarting.

### Step 3 — Place it

**Option A — from a building layout (`decor_layer` field):**

Add a `decor_layer` array to your building JSON. Same dimensions as `layers`.
Each cell is either `null` (no decor) or a `decor_id` string.

```json
"layers": [
  "######",
  "#....#",
  "##+#+#"
],
"decor_layer": [
  [null,null,null,null,null,null],
  [null,null,"decor_candle",null,null,null],
  [null,null,null,null,null,null]
]
```

`_stamp_building_at()` in `town_gen.py` reads `decor_layer` automatically and calls
`place_decor()` for each non-null entry.

**Option B — from generation code:**

```python
from generation.decor_utils import place_decor

place_decor(local_map, lx, ly, "decor_my_thing")
```

Import `clear_decor` if you need to remove one:

```python
from generation.decor_utils import clear_decor

clear_decor(local_map, lx, ly)
```

**Option C — from the debug console:**

```
place_decor decor_my_thing
```

Places at the player's current position. `place_decor clear` removes at player position.

---

## Visual Effects (visual_fx field)

A decorative entry may carry a `visual_fx` field. This tells the engine emitter block
to generate particles at the tile's screen position on the appropriate frame cadence.

```json
"visual_fx": "flame_low"
```

**Implemented types:**

| Effect | Cadence | Description | Recommended use |
|---|---|---|---|
| `sparkle` | 4 frames | Small bright sparkle burst | Resonant ground, magical objects |
| `pulse_glow` | — | Brightness oscillates up | Low-intensity glow emitters |
| `pulse_dim` | — | Brightness oscillates down | Dimming, fading energy |
| `flicker` | — | Random brightness jitter | Unstable light sources, dying flames |
| `embers` | 3 frames | Slow orange drift particles | Dying campfires, hot ash |
| `flame_low` | 4 frames | Dim amber flicker, 1 particle | Candles, small flames |
| `flame_med` | 3 frames | Warm orange glow, 1–2 particles | Campfire lit, hearths |
| `flame_high` | 2 frames | Bright fire burst, 2–3 particles | Bonfires, large flames |
| `smoke_incense` | 5 frames | Pale grey wisp drifting up | Incense, ritual smoke, extinguishing |

`sparkle`, `pulse_glow`, `pulse_dim`, and `flicker` are brightness-layer effects handled
in `rendering/renderer.py`. The five flame/smoke types are particle emitters routed
through the `_FLAME_FUNCS` dispatch table in `engine/engine.py`.

Multiple visual effects can be applied to terrain via a list in `terrain.json`:
`"visual_fx": ["sparkle", "pulse_dim"]` — only terrain supports this; decoratives
take a single string value.

---

## Constraints

- **One decor per tile.** Writing a second decor to the same coordinate replaces the first.
- **Never write to `local_map.decor` directly** outside `generation/decor_utils.py`.
  Always go through `place_decor()` — it performs bounds checking.
- **Not serialized.** Decoratives placed by generation are re-created each time the
  chunk is generated. Decoratives placed at runtime (e.g. by perks) vanish on chunk
  unload. Do not use decoratives to track game state.
- **Terrain still renders beneath.** The decor layer uses SRCALPHA — the floor tile
  beneath is always visible. Decoratives are surface details, not replacements.
- **Sprite fallback.** If no sprite is registered for a decor_id, the renderer falls
  back to the `ascii` character from `decoratives.json`. Ensure `ascii` is always set.

---

## Current Decoratives

| ID | ASCII | Blocks Move | Blocks Sight | Used In |
|---|---|---|---|---|
| `decor_candle` | `*` | no | no | bell_warden_post_a, starting lab |
| `barrel` | `o` | yes | no | storehouse_a, market_stall_b (container) |
| `decor_bone_pile` | `%` | no | no | collapsed_shrine_a |
| `decor_flower_pot` | `"` | no | no | (available) |
| `decor_hanging_cloth` | `\|` | no | no | (available) |

---

## Renderer Integration

`_draw_decor_to()` in `rendering/renderer.py` handles all decor rendering.
Called in `render()` between terrain and entity draw passes.

The decor surface is `pygame.SRCALPHA` so only non-transparent pixels composite
over terrain. The per-tile brightness is computed identically to terrain — decor
inherits the local_map light level at its position. Memory tiles are dimmed to ~15%.

`data_loader.py` exposes `engine.data.decoratives` — a `dict[str, dict]` keyed
by `decor_id`. Renderer and placement code look up entries here to validate IDs.



# How to create a new decorative:

Add entry to data/decoratives.json with all properties (blocks_movement, blocks_sight, description, interactable, visual_fx, light_emit etc.)
Add sprite entry to data/sprites/sprite_map.json pointing to the correct sheet/col/row
In generation code, call place_decor(chunk, lx, ly, "your_decor_id") — this writes to chunk.decor[(lx,ly)], not to local_map.tiles
The renderer reads chunk.decor and draws above terrain automatically

# How to convert a terrain tile to decor (why dead_bell overrides the tile beneath):
The tile is being written to local_map.tiles[y][x] which replaces whatever terrain was there — that's what terrain tiles do. To make it decor:

Keep or deprecate the data/terrain.json entry (keep for backward compat)
Add entry to data/decoratives.json
Keep sprite in data/sprites/sprite_map.json (same coords, different key name if needed)
Find every place in generation/town_gen/local_gen that writes this tile ID to local_map.tiles[y][x] and replace with place_decor(chunk, lx, ly, decor_id) — the floor tile beneath is now preserved
Find every engine reference that reads this as terrain and update to check chunk.decor