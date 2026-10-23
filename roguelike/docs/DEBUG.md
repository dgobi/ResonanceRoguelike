# Debug System Reference

> Available only when `DEBUG_MODE = True` in `config.py`.
> The debug overlay (F1) shows a summary of available keys in-game.
> This document is the authoritative reference — update it when adding debug features.

---

## Activating Debug Mode

In `config.py`, set:
```python
DEBUG_MODE = True
```

Restart the game. The F1 overlay becomes available.

---

## Keyboard Shortcuts

### Navigation & Vision

| Key | Function | Notes |
|---|---|---|
| F2 | FOV visualization overlay | Shows the raw FOV radius and light map as a colour overlay on the local map |
| F3 | Reveal full local map | Marks all tiles as explored. Does not affect visibility — FOV still applies. |
| F4 | SubMap highlights on overmap | Cyan dots on the overmap marking every chunk with a registered SubMap |
| F10 | Teleport by coordinates | Prompts for wx,wy world coordinates, teleports to that chunk |

### World & Time

| Key | Function | Notes |
|---|---|---|
| F5 | Teleport to nearest SubMap | Generates the chunk, places player near the entrance structure |
| F6 | Set world time | Prompts for hour (0-23). Affects ambient light and moon phase. |
| F7 | Set needs / corruption | Prompts for hunger, thirst, corruption values (0.0-1.0 each) |
| F8 | Force chunk regeneration | Regenerates the current surface chunk. Deletes current chunk from cache. |

### Inspection

| Key | Function | Notes |
|---|---|---|
| F1 | Toggle debug GUI overlay | Shows this key list, current state, invincibility status |
| F9 | Full state dump | Prints to terminal: WorldMyth, SubMap state, equipment slots, chunk submaps, player location HP and impairments |
| F12 | Remap sprite tile | Prompts: `tile_id sheet col row`. Remaps a sprite at runtime without restart. Write to sprite_map.json manually after. |
| Shift+F8 | Toggle invincibility | Player takes no damage. Log confirms ON/OFF. Invincibility light shows in F1 overlay. |

### Destructive

| Key | Function | Notes |
|---|---|---|
| F11 | Wipe all save data | Deletes the entire `saves/` directory. Log confirms completion. Irreversible. |

---

## Debug Console

**Trigger:** Backtick key ( `` ` `` )

A text input opens at the bottom of the screen. Type a command and press Enter.

### Commands

| Command | Effect | Example |
|---|---|---|
| `spawn_creature <id>` | Spawns creature on nearest adjacent walkable tile | `spawn_creature bog_wraith` |
| `spawn_item <id>` | Drops item at player's current position | `spawn_item binding_knife` |
| `teach_word <word_id>` | Teach a deep tongue word to player | `teach_word vrath` |
| `list_known` | List all known deep tongue words by category | `list_known` |
| `show_lexicon` | Show full lexicon with known/unknown markers | `show_lexicon` |

**Valid creature IDs:**
```
bog_wraith, barrow_wight, hollow_knight, hollow_revenant, drowned_revenant,
grave_thing, heath_stalker, briar_lurker, stone_lurker, plague_crow,
highland_bandit
```

**Valid item IDs (current):**
```
crude_blade, heavy_blade, binding_knife, dissolution_blade,
leather_jack, leather_cap, tallow_torch, oil_lantern,
crow_jerky, water_flask, bitter_herb, moist_pebble
```

If an ID is not found, an error message appears in the log in red.

---

## F9 State Dump — What It Shows

Running F9 prints to the terminal (not the in-game log):
```
--- Player State ---
Position: (x, y) in chunk (wx, wy)
SubMap: sub_64_64_0 | surface (if on surface)
Surface return: (x, y)

--- Fighter ---
Body: body_player
Location HP: head=2/2, torso=8/8, right_arm=2/2 ...
Impairments: (none) or list of active impairments

--- Equipment ---
weapon:      crude_blade
armor_torso: leather_jack
light:       tallow_torch
belt_1:      moist_pebble
(empty slots omitted)

--- WorldMyth ---
Age:      The Age of [name]
God:      [name]
Shape:    [shape]
Sundering:[epithet]
Locus:    (wx, wy) — [chunk name]

--- Current Chunk ---
Name: [chunk name]
Region: forest | heath | plains ...
SubMaps (N):
  sub_64_64_0: type=laboratory layout=starting_lab generated=True
               entry=(39,41) surface=(40,33)

--- Needs ---
Hunger: 0.12  Thirst: 0.34  Corruption: 0.05 (Touched)
```

---

## Debug GUI Overlay (F1)

The F1 overlay renders as a full-screen panel (no fancy border — legibility over aesthetics).

**Layout:**
- Header: arcane rune sigil + "DEBUG REGISTRY" title + invincibility status + toggle button
- Left column: Navigation/Vision keys, Inspection keys
- Right column: World/Time keys, Destructive keys (in distinct styling)
- Full-width: Debug Console section with command reference
- Footer status bar: current mode, submap id, chunk coords, corruption state, turn number

The sigil in the top-left is procedurally drawn via `pygame.draw` — same approach as biome icons. It renders in steel_blue tones with a subtle glow. It does not change between sessions.

---

## Adding New Debug Features

1. Add the key handler to `engine/debug.py` `handle_key()`
2. If it's a console command, add to `_execute_input()` and the command reference table above
3. Update the F1 overlay key listing in `debug.py` `render()`
4. Update this document (`docs/DEBUG.md`)
5. Update CLAUDE.md debug system section

---

## Testing After Changes
```powershell
python main.py
# Press F1 — overlay shows, no crashes
# Press each modified key — correct behaviour
# Press ` then type spawn_creature heath_stalker — spawns adjacent
# Press F9 — terminal output readable
```
