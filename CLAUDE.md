> **Arc A status:** Historical source retained below. Creative intent remains a design reference; technical claims need the [current implementation and authority map](roguelike/docs/owner/STATUS.md). This banner does not resolve open design decisions.

# Roguelike Project — Claude Context Document

> This file is the canonical project brief for both Claude Code and Claude chat sessions.
> Update the "Current State" and "Known Issues" sections after each session.
> Claude Code reads this automatically. Paste relevant sections when starting a new chat.

---

## Project Identity

A dark medieval new weird open-world turn-based traditional roguelike.
Working title: untitled. No genre-standard framing — this is its own thing.

**Location:** `G:\GameDev\RoguelikeProject\roguelike\`
**Entry point:** `main.py`
**Python:** 3.13.5
**Key deps:** pygame 2.6.1, tcod 19.3.0, numpy

---

## Aesthetic & Tone — Non-Negotiable

- Post-apocalyptic. The apocalypse is over. The silence after it is what the player inhabits.
- Dark medieval new weird. References: Vermis, Kill Six Billion Demons, 36 Lessons of Vivec,
  Kirkbride, Morrowind. Town references: Red City (KSBD), Yarnham (Bloodborne),
  Mahabre (Fear & Hunger).
- Gods are real and strange. Some dead, mad, missing, usurped.
- Ornate archaic prose for ancient things. Flat terse prose for mundane things.
- No standard monsters — everything is weird and specific.
- Corruption is transformation, not penalty. It opens doors.
- Rituals work through correct conditions, not flags.
- Unreliable narrators throughout. No text is authoritative.

**What this means for code decisions:**
- Message text must reflect the tone. "You are hungry" is wrong. "Hunger moves through you" is closer.
- No generic fantasy naming. Every creature, place, item has a specific strange identity.
- Mechanics should feel like they emerge from the world's logic, not from game convention.
- The world is layered and ancient. Newer things sit on older things that sit on older things still.
- **Juice is imperative.** Every action must feel satisfying and tactile. Particles, shake,
  callouts, visual fx are not polish — they are part of the design.
- **Data-driven by default.** Every system that can be defined in JSON should be.
  New content should not require code changes.

---

## Gameplay Loop — Core Design Intent

This is a scavenge-and-grow exploration roguelike in the vein of Cataclysm: Dark Days Ahead.
The world is a giant interactive object. Every tile potentially contains something.
Every item has weight, use, and context. Power comes from knowing the world deeply.

**The loop:**
Explore ruins and wilderness → find/harvest raw materials → process into useful things
→ grow stronger and better-equipped → explore further and deeper.

**What this means in practice:**
- Buildings are not backdrop. They are spaces where someone lived — readable, searchable,
  contextually furnished. A storehouse smells different from a shrine.
- Item granularity matters. Not "loot" — specific objects placed because someone put them there.
  A shelf, a cold hearth, a box under a bed. Loot tables think at room-level, not building-level.
- Containers are furniture: shelves, sacks, coffers, rubble piles, cold hearths.
  The decorative layer is the foundation for this.
- Weight and encumbrance will matter. Every item has a weight field from day one, even unstated.
- Crafting is discovery, not a skill tree. You don't unlock recipes — you learn through
  experimentation and found texts. The alchemy system never shows a recipe list.
- The silence is the content. You walk into a house and reconstruct the last day
  from object placement. Found texts, container contents, and building layouts deliver this.

**NPCs are incidental, not a pillar.** Finding one should feel like finding something
that wasn't meant to be found. They speak obliquely. No conversations.
The world speaks through objects, spaces, and texts — not through characters.

---

## World Scenario — The Apocalypse

The world was already dying — layered, ancient, fading, the latest iteration of a
civilisation built on the ruins of previous ones. Then something completed its function.

### The Mechanism — The Stones and the Bells

The cold grey stone found everywhere carries resonant properties.
Every settlement bell was tuned to resonate with local stones — correct craft,
ancient guild knowledge. The bells tuned the stones. The stones tuned the people.
Generations of resonance accumulated in human bone.
The final tone discharged everything at once.

**Key facts for all content generation:**
- Intact bells are the most dangerous environmental hazard in the world
- Even a cracked bell disturbed by wind can trigger partial discharge
- Bodies are oriented toward the nearest stone at the moment of death
- Resonance and corruption are related systems
- Transformed creatures: resonance discharged inward — not undead, transformed
- The sarcophagus material (non-resonant) is rare and significant
- Animals now avoid grey stones
- Waystones everywhere — roads, crossroads, field boundaries, town centres.
  All grey stone. All still resonant. Coldbell flowers cluster near them.
- The mechanism was always visible, purpose always misunderstood

### The Aftermath

Almost no one is left. The player is in the silence after the apocalypse.

**What remains:**
- Transformed survivors — people who didn't die cleanly, changed instead
- Opportunistic wilderness creatures expanding into the vacuum
- Remnant bound entities — bargains broken, containment unmaintained
- The rare human survivor — dangerous for human reasons

**Environmental storytelling — these principles drive all content:**
- Meals on tables, work half-done, letters mid-sentence
- Bodies oriented toward stones — transfigured, not strewn
- No corpses for loot — the dead have changed into something else
- Transfigured bodies are environmental objects, not loot containers
- Infrastructure still running with no one operating it
- Festival squares still decorated, offering bowls still with coins

### Player Origin

- Awakens in stone sarcophagus in underground laboratory
- Lab was studying the resonance phenomenon
- Player starts Touched — something happened before the discharge
- Two mysteries: what happened to the world, what happened to them

---

## Corruption States — Canonical Progression

```
Unmarked → Touched → Stained → Marked → Consumed → Vessel
```

Player starts **Touched**. Each state changes how the world perceives and responds to the player.
At **Vessel**: bells no longer harm. Something else hears.

Corruption is a path, not a meter. Each threshold opens something. Nothing closes.

---

## Gods — Canon

- **The Void-That-Precedes** — what was before. Not absent. Waiting.
- **The Burning Throne** — empty. What sat there matters more than its absence.
- **The Dreaming** — still dreaming. Effects bleed into the waking world.
- **The Measuring / The Architect** — built the resonance systems. May still be maintaining them.
- **The Prior Claimant / The Hollow King** — barrows, bone, the honoured dead. Usurped or diminished.
- **The Consistent Omission / The Unspoken** — present in what is left out of every text.
- **The Broken Ones** — pre-human fragments. Not a single god. Shards of something older.

Gods are real and strange. Some dead, some mad, some missing, some usurped.
The mechanism may have been their instrument or their undoing.

---

## Moon Phases — Canonical

```
Dark Seal → Thin Knife → Half Truth → Swelling Eye →
Full Witness → Dimming Eye → Half Lie → Waning Knife
```

Ritual moons: **The Waning Knife**, **The Half Lie**.
Moon phase drives surface night FOV via a lookup table with smooth dusk/dawn interpolation.

---

## Historical Strata

**Era 1 — The Deep Ones**
Master terraformers and resonance engineers. Stone and bone only — no metal.
Geometrically precise construction. Their ruins still hum. Their mechanisms still run.
Destroyed themselves in an earlier resonance apocalypse — not the current one.
Two apocalypses layered in history. VUKH is their sacred mountain.

**Era 2 — The Valdric (Middle Folk)**
Rome analogue. Built on Deep One foundations without understanding them.
Sophisticated metallurgy, fitted stone. Scientific view of the bells — instruments, not sacred.
Capital (Valdremor) sprawled around VUKH. Fell to expansion and accumulated resonance effects.
Their ruins are the grandest structures remaining.

**Era 3 — Those Who Remain**
Medieval-dark successor culture. Rustic furniture in Valdric stone halls.
Religious view of the bells. Treat the Valdric as a golden age.
Scattered across the world in small towns.

**Era 4 — Now (post-apocalypse)**
The bells have fired. Most of Those Who Remain are gone or transformed.
The player navigates the silence.

---

## Visual System

### Spritesheet — Urizen (current)
**Active sheet:** `assets/sprites/urizen_onebit_tileset__v2d0-Sheet.png`
- 10,300 tiles, single row, each 12×12px
- White sprites on transparent background (RGBA)
- `col` = tile index 0-10299, `row` = always 0
- `ZOOM_LEVEL = 2` in config.py → 24px display tiles
- Reference sheets: `sprite_ref.py` utility generates them from any PNG

**Sprite mode:** `use_sprite_tint = False` in `display_config.py`
- Full-colour mode: sprites rendered as-is, lighting applied as brightness overlay
- Torch warmth: 60% neutral brightness + 40% light colour tint
- Memory tiles: darkened to ~15% brightness

**Blank sprite detection:** SpriteSheet.get_tile() checks bounding rect after extraction.
Completely transparent tiles return None, triggering ASCII fallback in renderer.
Every tile in tiles.json MUST have an "ascii" field.

### Palette — AAP-64 (current)
**Single source of truth:** `engine/palette.py`
All 64 AAP-64 colours defined with world-appropriate names.
Semantic aliases section maps roles to colours (UI, Combat, Resonance, Status, etc.)
No raw RGB tuples anywhere in .py files outside palette.py.
RGBA tuples use spread syntax: `(*OLD_GOLD, 60)`

**Key semantic aliases:**
```python
UI_BACKGROUND, UI_PANEL_DARK, UI_BORDER, UI_TEXT_BRIGHT, UI_TEXT_MID, UI_TEXT_DIM
COMBAT_OUTGOING (hollow_blue), COMBAT_INCOMING (dusty_rose)
COMBAT_CRIT (resonance_gold), COMBAT_CRIT_DANGER (fresh_wound)
RESONANCE_LOW/MID/HIGH/CRITICAL, CORRUPTION_COLOUR, BELL_COLOUR
MSG_DEFAULT, MSG_COMBAT_OUT, MSG_COMBAT_IN, MSG_LORE, MSG_DANGER, MSG_ANCIENT
BLOOD_RED, BLOOD_BONE_DUST, BLOOD_ECTOPLASM, BLOOD_ICHOR, BLOOD_VERDIGRIS
WEATHER_RAIN, WEATHER_STORM, WEATHER_FOG, WEATHER_SNOW
BIOME_FOREST, BIOME_PLAINS, ... (all biomes)
OVERMAP_RIVER, OVERMAP_ROAD_PRI, OVERMAP_ROAD_SEC, OVERMAP_CAPITAL, OVERMAP_VUKH
```

**Adding new colours:** Add to palette.py only. Use a world-appropriate name.
Add a semantic alias if the colour has a recurring role.

### UI Layout
- Primary font: Junicode (Regular/Bold/BoldItalic/Italic)
- All font sizes in `engine/display_config.py` init() only
- Callout fonts in DisplayConfig.CALLOUT_FONTS: damage=13pt, status=12pt, creature=11pt, crit=18pt bold
- Viewport inset: UI_PANEL_INSET (24px border) + MAP_INSET (2px breathing room)
- Map fills to border on all four sides — no dead space
- Status bar: HP bar, hunger, thirst, corruption bar, resonance bar (when >0.05)
- Debug mode status bar: extended line showing pos/chunk/turn/corruption/exposure/weather

### Tile Visual Effects (visual_fx field in terrain.json)
Data-driven. Defined effects: `sparkle`, `pulse_glow`, `pulse_dim`, `flicker`, `gas_overlay` (stub).
Creature JSON may also carry `visual_fx`.

---

## Architecture Overview

```
main.py                 Entry point. World gen, _start_in_lab(), engine run.
                        Places 2 waystones near player start on new game.
                        SystemExit(2) = new game request (loop in main).

engine/
  engine.py             Core loop. Hook dispatch at 6 sites. Reality bubble.
                        _pending_blood, _pending_callouts deferred lists.
                        _shake_frames, _shake_intensity for screen shake.
                        resonance_exposure, corruption, wind_turn.
                        _waystone_pulse_timers, _fog_surface cache fields.
                        particle_system, callouts, weather instances.
  palette.py            ALL colour definitions. Single source of truth.
                        64 AAP-64 colours + semantic aliases.
  hooks.py              HookEvent enum (9 events), HookRegistry, _merge_effects.
                        Events: ON_TURN, ON_DAMAGE_TAKEN, ON_DAMAGE_DEALT,
                        ON_TILE_ENTERED, ON_ENTITY_KILLED, ON_ITEM_EQUIPPED,
                        ON_STATUS_APPLIED, ON_CHUNK_ENTERED, ON_CRITICAL_HIT.
  perk_handlers.py      Handler functions + HANDLER_MAP.
                        system_exp_on_kill (permanent, not a perk handler).
                        BLOOD_COLORS dict. make_crit_impact_sparkles().
  resonance_system.py   ON_TURN: exposure decay/accumulation, wind check,
                        corruption conversion, tier messages.
                        ON_TILE_ENTERED: bell adjacency check.
                        ON_CHUNK_ENTERED: bell_sense threshold warning.
  discharge.py          trigger_discharge(): exposure spike, corruption,
                        creature alert, discharge ring particle, screen flash.
  weather.py            WeatherSystem: 10 states, tick(), discharge_push(),
                        force_state(), to_dict()/from_dict().
  display_config.py     Fonts, sizes, CALLOUT_FONTS dict.
  ai_system.py          process() gates on reality_bubble.is_active(chunk).
  data_loader.py        biomes, buildings, perks, resonance_spawns, weather_defs,
                        decoratives.
  reality_bubble.py     RealityBubble: active_chunks set, update(), is_active().
  save_manager.py       Serializes all fields including resonance state,
                        weather, corruption thresholds.

rendering/
  renderer.py           _draw_map_to(): autotile walls + roads, visual_fx brightness.
                        _draw_decor_to(): decorative layer pass (above terrain,
                        below entities). _draw_weather_overlay(): data-driven
                        precipitation grid.
                        draw_fog_vignette(): cached smooth radial gradient.
  coords.py             world_to_screen() canonical helper. Debug viewport assertion.
  particles.py          ParticleSystem: adaptive cap (100-800), scratch surface.
                        Shapes: circle, streak, ring, square, sparkle.
  callouts.py           CalloutSystem: floating text above world entities.
  perk_screen.py        K key. Browse/purchase perks.
  death_screen.py       "YOU ARE UNDONE."

engine/
  interaction_cursor.py InteractionCursor: GameMode.INTERACTION_CURSOR.
                        Shift+G cursor for multi-candidate adjacent interact.
                        Reuses look_mode.render_cursor(x=, y=) override params.
                        _get_interaction_candidates() + _try_open_interaction_cursor()
                        live in engine.py.

generation/
  world_gen.py          Full 11-step pipeline.
  town_gen.py           3×3 plaza-anchored footprint. District zoning.
                        Multi-row zone packer. _split_zone_by_streets().
                        Road-exclusion in _plot_is_clear(). flip_v for south zones.
                        Corner scatter with path connector.
  decor_utils.py        place_decor(chunk, lx, ly, id) and clear_decor().
                        Only write paths to local_map.decor.
  wfc.py                Generic WFC solver. Used sparingly — only where it
                        genuinely enhances game feel.

world/
  local_map.py          Numpy tile array + light_map.
                        decor: dict — decorative layer, (lx,ly)→decor_id.
                        Serialised with chunk.

components/
  fighter.py / equipment.py / needs.py / corruption.py / inventory.py
  light_source.py / ai.py / perception.py / language.py / perks.py
  level.py              LevelComponent: exp, level, perk_points.

data/
  tiles.json / terrain.json
  biomes/               Biome JSONs with AAP-64 overmap_color values.
  buildings/            residential, commercial, civic, religious,
                        storage, ruins, wilderness — all in layers format.
                        24+ layouts across 7 categories.
  decoratives.json      5 entries: candle, barrel, bone_pile, flower_pot,
                        hanging_cloth. Each has id, sprite_sheet, col, row,
                        ascii, blocks_movement, blocks_sight, description.
  perks/                hardened_step, carrion_eye, marrow_drink, attuned,
                        the_indifference, lithic_seep.
  wfc/                  town_plaza.json, town_block.json.
  weather.json          Data-driven precipitation definitions.
  resonance_spawns.json Terrain and creature spawns per pulse type.
  items/weapons/        crude_blade, heavy_blade, binding_knife,
                        dissolution_blade, severance_blade, revelation_lens,
                        debug_blade (100d100, all essences).
  items/armor/          leather_jack, leather_cap.
  items/tools/          moist_pebble (belt slot).
  items/consumables/    perk_vessel.json.
  loot/                 dungeon_weapons.json, world text loot tables.
  zones/                Zone spawn tables per biome.
  entrances/            6 entrance type JSONs.
  layouts/              starting_lab.json (needs redesign pass).
  texts/                40+ found texts (lab/, world/).
  sprites/sprite_map.json   Live coordinates. sprite_map_draft.json = draft only.

tools/
  sprite_ref.py         Generates reference sheets from any spritesheet PNG.
  tile_mapper.py        Draft output only — never writes to live sprite_map.json.

docs/
  LAYOUT_AUTHORING.md   Full layout creation guide.
  DECORATIVES.md        Decorative tile authoring guide.
  DEBUG.md              Full debug feature reference.
```

---

## Key Systems

### Palette (engine/palette.py)
Single source of truth. `from engine.palette import *`. No raw RGB anywhere else.

### SubMap System
- Dungeons are SubMaps in surface Chunks — not surface tiles
- BSP submaps: perimeter sealed, 2-4 found texts placed per dungeon
- Stair traversal: `>` descend, `<` ascend
- `engine.current_submap_id` — None on surface, set underground
- Stair return position tracked: `_stair_return_x/y` on descend

### FOV System
- Underground base = 1
- Surface day = 40
- Surface night = moon phase table with smooth dusk/dawn interpolation
- Three-layer permanent failsafe prevents silent corruption:
  Layer 1: surface guard at top of _update_fov()
  Layer 2: unconditional clear if not submap
  Layer 3: logging on any deviation
- Bog wraith aura: proximity FOV drain via `_wraith_aura_state` dict
- Generation functions NEVER write engine.is_underground — this caused the recurring bug

### Combat System
- `resolve_attack()`: hit location, armour layers, essence, CombatResult
- Hit-location multipliers: head ×1.5, torso ×1.0, limbs ×0.8
- Single HP pool per entity with consolidated AV
- Dodge (5% base), block (shield/offhand)
- Critical hits: 5% base + weapon crit_chance. ×2.5 multiplier pre-armour
- ON_CRITICAL_HIT hook. Screen shake: 4px player crit, 5px creature crit
- Unarmed: UNARMED_PROFILE (1d4), full pipeline
- Three learnable feedback states (never name the formula):
  - Ineffective (<0.4): "This thing resists [essence]. The blow finds no purchase."
  - Neutral (0.6–1.4): standard messages
  - Effective (>1.8): higher numbers + "It recoils." / "Something in it comes apart."

### Equipment System
```
Slots: weapon, offhand, armor_head, armor_torso, armor_arms, armor_legs,
       light, talisman_1, talisman_2, talisman_3
```
- Armor layers prepended outermost on equip, stripped by name on unequip
- Duplicate guard prevents layer doubling across save/load
- Light slot activates/deactivates LightSource component
- All items have essence field — nothing is metaphysically neutral
- Equipment save/load fully restored

### Essence Canon
```
Dissolution  — corrodes, rots, breaks down structure
Binding      — preserves form, holds together, constrains
Quickening   — alive, animates, accelerates change
Consumption  — feeds or is fed upon, drains
Revelation   — exposes the true, things that hide
Severance    — cuts connections, severs links

Pip strength (drawn circles):
0.2=●○○○○  0.4=●●○○○  0.6=●●●○○  0.8=●●●●○  1.0=●●●●●
```
Every object and creature has an essence relationship. Nothing neutral.

### Decorative Layer
- `local_map.decor`: dict mapping `(lx, ly)` → decor_id string
- Render pass: above terrain, below entities, blood, particles
- Sprites use same extraction path as terrain tiles
- Same FOV/torch lighting applied as terrain at that position
- Only write paths: `place_decor(chunk, lx, ly, id)` and `clear_decor(chunk, lx, ly)`
  from `generation/decor_utils.py` — never write to `chunk.decor` directly
- Building layouts may include a `decor_layer` field (same grid format)
- Look mode surfaces decorative descriptions: flat/terse tone per CLAUDE.md
- See `docs/DECORATIVES.md` for full authoring guide

### Resonance & Bell System
```python
engine.resonance_exposure: float  # 0.0–1.5, decays 0.008/turn
engine.corruption:          float  # 0.0–1.0, never decays
engine.wind_turn:           int    # 40-turn wind cycle
```
Corruption thresholds (fire once each):
```
0.15  threshold_resonance_sight  — examine shows resonance_emit values
0.25  threshold_bell_sense       — chunk entry warns of bells nearby
0.40  threshold_waystone_glyph   — stub
0.55  threshold_presence_sense   — stub
0.70  threshold_deep_tongue      — stub
0.85  threshold_creature_shift   — stub
```

### Weather System
10 states: clear, overcast, light_rain, heavy_rain, fog, wind,
resonance_storm, forgetting_fog, dead_calm, bone_snow.

All visual definitions in `data/weather.json`. No hardcoded weather values anywhere.

**Mechanical effects (wired):**
- dead_calm: bells carry further, creatures more active
- bone_snow: corruption per step accumulation
- resonance_storm: cracked bell discharge probability increased
- forgetting_fog: creature pathfinding altered, FOV reduced

### Perk Hook Architecture
9 events: ON_TURN, ON_DAMAGE_TAKEN, ON_DAMAGE_DEALT, ON_TILE_ENTERED,
ON_ENTITY_KILLED, ON_ITEM_EQUIPPED, ON_STATUS_APPLIED, ON_CHUNK_ENTERED, ON_CRITICAL_HIT.

Handlers are pure functions. Never crashes on handler error — logs and continues.
Permanent system handlers (never cleared): system_exp_on_kill, system_resonance_*.

**Perk Affinities (design canon):**
The Hollow Road, The Witnessing, The Green Patience, The Bound Name,
The Unmarked Way, The Consuming, The Sutured Work, The Red Accounting.

Perks open ontological doors. Never +x% to stats. Acquisition: ritual, research,
corruption threshold, specific events — not automatic level-up.

### Chunk Transitions
- `chunk_dx` derived purely from which bounds violated, not movement direction
- Diagonal transition only valid when both x AND y simultaneously out of bounds
- Exit position mirrored to entry position correctly

### Difficulty & Resonance Gradient

Difficulty is a spatial property of the world, not a leveling curve.
The world doesn't scale to the player — the player learns to read the resonance.

**Resonance tiers:** very_low → low → moderate → high → very_high → bell_proximity → intact_bell

**Calculation factors:**
- Biome base: forest=0.15, heath=0.25, swamp=0.30, mountain=0.35, town=0.50
- Distance from world centre: 0.5× at centre, 1.0× at edge
- Bell state modifier: intact=2.0×, cracked=1.6×, spent=1.1×
- Underground SubMaps: inherits surface + depth modifier

**Difficulty radiates from:** town/city centres, waystones on roads, world map edge,
underground (always higher than surface), intact bells (local spike).

Zone entry messages fire on resonance tier change. Register sensory impression,
not UI readout. Colour warms toward danger. Messages vary by corruption state.

---

## World Structure — Canonical

### VUKH — The Mountain
Full deep tongue: Vukh-Skral-Zhal ("The True-Song-Bell")
Always at world centre. 2×2 chunk minimum surface area.
Most dangerous zone. Source of primary river system.
Deep One sacred site — most ancient stratum visible here.

### The Capital — Valdremor
Valdric capital city. 3-5 chunk uneven ring around VUKH.
Highest difficulty outside VUKH itself.
Most layered architecture — Deep One foundation, Valdric stone, Remnant squatters.

### World Generation Pipeline
```
1.  VUKH placement (world centre, 2×2 deep_mountain)
2.  Elevation map (radiates from VUKH, noise variation)
3.  Moisture map (noise + rain shadow from elevation)
4.  River generation (4 primary cardinal + 2 tributaries, separation-aware walker)
5.  Biome assignment (elevation × moisture matrix, river adjacency bonus)
6.  Resonance calculation (biome base × distance modifier × river modifier)
7.  Capital placement (ring around VUKH, 3-5 chunk radius, irregular)
8.  Player start (forest chunk, ≥60% max distance from VUKH)
9.  Town placement (5-8 towns, 3×3 footprint, quadrant-balanced, min 8 chunk separation)
10. Road generation (curved winding paths: towns→capital + town↔town + distant pairs)
11. Difficulty band calculation (biome × distance × town/capital/river mods)
```

### Biomes (data/biomes/*.json)
```
forest        elev 0.15-0.75  moist 0.4-1.0   resonance 0.15  diff 0.20
heath         elev 0.10-0.50  moist 0.1-0.5   resonance 0.25  diff 0.25
plains        elev 0.10-0.50  moist 0.3-0.7   resonance 0.20  diff 0.15
swamp         elev 0.00-0.30  moist 0.7-1.0   resonance 0.30  diff 0.30
mountain      elev 0.70-1.00  moist 0.0-1.0   resonance 0.35  diff 0.50
deep_mountain elev 0.85-1.00  moist 0.0-1.0   resonance 0.80  diff 0.95
drowned_wood  elev 0.05-0.35  moist 0.6-1.0   resonance 0.35  diff 0.40
ash_wastes    elev 0.00-0.40  moist 0.0-0.2   resonance 0.60  diff 0.70
capital       special placement                resonance 0.70  diff 0.85
town          special placement                resonance 0.50  diff 0.45
```
**Planned expansions:** resonance_scar, bone_heath, deep_wood, salt_flat.
Adding a biome = one JSON file. No code changes needed.

---

## Town & City Design Canon

### Feel
Red City (KSBD) + Yarnham (Bloodborne) + Mahabre (Fear & Hunger).
Beauty that has become wrong. The city still follows its own rules.
The festival is still decorated. The bells are still in their towers.
Towns are more dangerous than wilderness — bell density, foe strength, resonance.

### Scale (current implementation)
- **Towns** — 3×3 chunks. Market, residential, bell tower, central waystone.
  One primary chunk contains waystone square + bell tower.
  Adjacent chunks are different districts, sharing TownData.
  Streets continue seamlessly across chunk boundaries.

### Districts
```
Market Quarter    — stalls mid-setup, goods scattered, weighing stones
Residential       — dense housing, personal effects, family shrines
Bell District     — tower(s), most dangerous, resonance active, bell still present
Waystone Square   — central grey stone, festival square, folk saint alcoves
                    (stone niches: ceremonial skeleton, talismans, readable prayers,
                    candles burned to nothing, coins in offering bowls)
Ossuary District  — mortuary temples, bone pits, urns, graveyards,
                    layered funeral tradition, many gods evidenced
The Tangle        — magic area, twisted alleys, spires, confusing geometry
The Old Foundation— deepest stratum, dangerous grey stone, pre-human architecture
Gatehouse/Walls   — outer perimeter, guard posts, watchtowers
```

### Architectural Layering
```
Stratum 1 (newest):  Wood + plaster + fired brick. Warm, human-scale.
Stratum 2 (older):   Local limestone/sandstone. Dressed stone, mortar visible.
Stratum 3 (ancient): Cold grey resonant stone. Unnaturally regular, no mortar,
                     slightly wrong proportions. Bell towers, waystones, foundations.
```
Buildings show age through visible stratigraphy. A shop built into an ancient arch.
A cellar revealing grey stone walls the family never removed.

### Street Lamps (current implementation)
Three states: working (15%), sputtering (25%), dead (60%).
Working: LightSource radius 4, warm amber.
Sputtering: LightSource radius 2-3, flicker=True.
Dead: lamp post tile only, no light.
Placement: intersections, every 8-10 tiles on primary streets.
Bell district lamps: all dead (discharge hit hardest there).

### Town Generator — Current Technical State
- 3×3 plaza-anchored footprint with district zoning
- Multi-row zone packer working south→north, zones split by actual street positions
- Road tiles excluded from `_plot_is_clear()`; south zones use flip_v
- Corner scatter with path connectors to nearest road
- 24+ building layouts across 7 categories (residential, commercial, civic,
  religious, storage, ruins, wilderness), minimum 4 per category
- Density: 18-25 buildings per chunk across seeds consistently
- Per-chunk diagnostic log active in DEBUG_MODE

---

## Generation Layering Model

```
Layer 0 — Terrain base (BSP, WFC, noise)        — IMPLEMENTED
Layer 1 — Zone features (feature pools)          — Tier 3
Layer 2 — Special rooms (room pools)             — Tier 3
Layer 3 — Scripted placements (special_tiles)    — IMPLEMENTED
Layer 4 — Loot/creatures (loot tables, zones)    — PARTIAL
```
Layer 4 partial: found texts in BSP dungeons wired.
WFC used sparingly — only where it genuinely enhances game feel.
Dungeon void tiles (Tier 3): uncarved space = `void` tile (pure black), not wall.

---

## Enemy Roster — Full Reference

| Creature | Damage | Key Armor | Special Ability | Blood |
|---|---|---|---|---|
| Barrow Wight | 1d6+1 | Resonance AV2, bone AV3 | Corruption adjacency | bone_dust |
| Hollow Knight | 1d8+2 | Plate AV6, helm AV5 | Resonant disruption | bone_dust |
| Hollow Revenant | 1d4+1 | Shell AV1 | — | bone_dust |
| Drowned Revenant | 1d4+1 | Flesh AV1 | — | red |
| Grave Thing | 1d6 | Bone AV4, tissue AV2 | — | bone_dust |
| Heath Stalker | 1d6 | Hide AV2, muscle AV1 | — | red |
| Briar Lurker | 1d4 | Thornmass AV3 | Retaliating thorns | none |
| Stone Lurker | 1d8+2 | Carapace AV6, inner AV4 | Hibernation ambush | none |
| Bog Wraith | 1d4 | Mist AV3 | FOV drain | ectoplasm |
| Plague Crow | 1d3 | Feathers AV0 | Sickness on hit | red |
| Highland Bandit | 1d6+1 | None | — | red |

| Creature | Decisive (2.5+) | Weak (1.5-2.4) | Resists | Near-immune |
|---|---|---|---|---|
| Barrow Wight | — | Quickening 2.2, Revelation 2.0 | Dissolution 0.4 | Consumption 0.3 |
| Hollow Knight | Severance 2.5 | Quickening 1.8, Revelation 1.5 | Dissolution 0.5 | — |
| Hollow Revenant | Severance 2.5 | Binding 2.0, Revelation 1.8 | — | Dissolution 0.2 |
| Drowned Revenant | — | Binding 2.2, Severance 1.8 | Consumption 0.5 | — |
| Grave Thing | — | Revelation 2.8 | Dissolution 0.7 | — |
| Heath Stalker | — | Consumption 1.3 | — | — |
| Briar Lurker | — | Dissolution 2.0, Severance 1.8 | Binding 0.6 | — |
| Stone Lurker | — | Dissolution 1.8, Revelation 1.6 | Severance 0.7 | Consumption 0.3 |
| Bog Wraith | Binding 3.0, Severance 2.5 | — | Quickening 0.8 | Dissolution 0.3 |
| Plague Crow | — | Consumption 1.5 | — | — |
| Highland Bandit | fully neutral | — | — | — |

**Bog wraith has NO callout sounds. Never add them.**

**Current weapons:**
- crude_blade (Dissolution 0.2)
- heavy_blade (Dissolution 0.3)
- binding_knife (Binding 0.6 — decisive vs bog wraith)
- dissolution_blade (Dissolution 0.5)
- severance_blade (Severance 0.6 — decisive vs Hollow Knight/Revenant)
- revelation_lens (Revelation 0.7 — decisive vs Grave Thing)
- debug_blade `the Arbiter` — 100d100, all 6 essences, strength 3.0

Stone lurker crit_chance: 0.15. Binding knife: 0.08. Severance blade: 0.06.

---

## Systems Design Reference — Tier 3

### Crafting / Alchemy / Magic — Unified Model

All three operate through the essence system — same substrate, different expression.
```
Crafting:  material selection + process = essence property transfer
Alchemy:   extraction + combination = essence preparation
Magic:     resonance + intention (bells) = essence effect at scale
```
Material provenance matters. Process matters. Knowledge gates options.
The player learns by noticing results — not through tutorials.
The same action (craft a blade) produces different results based on material source,
process quality, and knowledge applied. The variables are discoverable.

**Depth without complexity.** No recipe lists. No skill trees. No unlocks.

### Wildcraft Chain
```
Tracking → Hunting → Killing → Butchering → Processing → Cooking/Carving
```
Killing method affects yield. Bone carries resonance. Source material matters.
Everything has provenance. The world remembers what things came from.

### Herblore & Wildcrafting
Wild herbs, fungi, flowers, and liquids (resins, waters, animal fluids) are
the primary reagent sources. The chain:
- **Harvest** — from living plant tiles in the world (plant tile → depleted state, item added)
- **Identify** — through experimentation, found texts, or corruption-granted perception
- **Dry / Render / Grind / Steep** — processing steps, each requiring specific equipment
- **Distil into essences** — the bridge between wildcrafting and alchemy

Known harvestable sources (expand as terrain is authored):
- coldbell_flower → coldbell_cutting (resonance-adjacent, Binding)
- shroom_sulphur_cap → sulphur_cap_fragment (Dissolution)
- shroom_prophets_eye → prophets_eye_cap (Revelation)
- flower_murk_violet → murk_violet_stem (Consumption)
- flower_pilgrims_woe → pilgrims_woe_petals (Quickening)

Bone carries resonance from its source creature — provenance tracked on item.
Reagents from resonant sources produce more volatile preparations.

### Alchemy Equipment
Physical tools required. Cannot brew without tools.

```
Tier 1 (portable/craftable):
  campfire        — entry point. Crafted from wood + flint.
                    Also: warmth, shelter anchor, light, cooking hub.
  clay pot        — basic preparations, heat-required
  iron cauldron   — larger batches, sturdier essences

Tier 2 (found, fixed in world):
  alembic         — distillation, essence extraction
  resonance bowl  — bell-adjacent preparations, volatile
  grinding stone  — reduction, powder preparation

Tier 3 (world objects, unmovable, one or few per world):
  moonwater basin — near locus only (1 per world). Lunar-phase sensitive.
  bone crucible   — crafted from resonant bone. Dangerous.
  the still       — Bellwright or guild ruins only.
```

Preparation types:
```
Oils/Unguents  — applied to weapon/skin, temporary essence property transfer
Tinctures      — consumed, immediate internal effect
Burned         — area effect, 5-tile radius, N turns
```

### Magic System — The Bells
Five ringing requirements: bell material, tuning, conditions, the words, duration.

Bell material types:
```
Sounding silver  — Witnessing affinity
Cold iron        — Sutured Work (failing bindings)
Bone bell        — most dangerous, provenance-dependent
Greenwood bell   — Green Patience affinity
Grey stone bell  — DO NOT RING
```
Effects are essence-typed. Corruption state changes bell interaction at every stage.
Skill curve: timing + tuning + words + duration + corruption state.
All learnable through play and found text — no skill points. No spell list.

Bell magic is ritual magic. Correct conditions, not flags.

### Weapon Movesets
Defined in weapon JSON: moveset array with id, name, description, key, cost.
`engine/movesets.py` — pure functions, same pattern as combat.py.
```
Spear:        Reach (2-tile attack), Brace (free strike on approach)
Blunt:        Daze bash (target loses action), Structural strike
Knife:        Quick strike (2× at 0.6×), Slip past
Heavy blade:  Press (free move on kill), Rending strike (destroy armor layer)
Axe:          Cleave (free attack on kill), Chop (bonus vs organic)
Binding knife: Connection cut (disables creature special ability, 5 turns)
```

### Shelter System
Portable structure that grows with the player.
```
bare camp → rough shelter → field tent → workshop tent → established camp
```
Field tent and above: enters as SubMap (10×8+ interior, layout_id changes per tier).
Interior has equipment_slot tiles. Tent persists in chunk cache where deployed.
Deploying creates meaningful location decisions.

### Survival System
Hunger and thirst are tracked fields on the needs component.
Data-driven tick rates in `data/survival.json` — biome-modifiable.
Staged consequences: messages first, then move penalty, then HP drain at starvation.
Tone: "Hunger moves through you." Never "You are hungry."

### NPC Design — The Hollow Merchant (stretch target)
NPCs are events, not services. Finding one should feel like finding something
that wasn't meant to be found. No conversations. They speak obliquely.
They want strange things. They are dangerous in ways unrelated to combat.

**The Hollow Merchant** — carries unportable things. Prices in actions, not coins.
"Bring me the tone from that bell. Not the bell."
A wandering trader archetype. Rare. Significant. One encounter per world or fewer.

### Floating Callout System
Text above entities. Supplementary to log, never primary. Max 1-4 words.
Categories (user-configurable): damage_numbers, creature_sounds, status_effects, item_pickups.
Creature sounds in creature JSON: `callout_sounds: [{trigger, text, color}]`
Triggers: on_spot, on_attack (25%), on_death.
**Bog wraith: NO callout sounds. The silence is the design.**

### Procedural Iconography System
All glyphs share a common grammar: primary axis, secondary arms, tertiary tick marks,
optional frame, accent strokes. Variation from seed — same seed = same glyph always.
`rendering/glyph_gen.py` — GlyphDef dataclass + generate_glyph() + draw_glyph().
Styles: standard, dense, open, ancient.

Applications:
- Debug overlay sigil — IMPLEMENTED
- Deep tongue word glyphs (one per word, seeded from word index)
- Essence sigils (6 fixed, one per essence type)
- Faction markers (seeded from WorldMyth)
- Standing stone inscriptions (glyph sequences)
- Perk acquisition flash (affinity colour, 2 seconds)
- God symbols (7 fixed, hand-designed)

Coherence constraint: same grammar, same visual weight across all glyphs.

---

## Language System — Deep Tongue

Pre-human. Consonant-heavy, Assyrian/Sumerian register. Bells tuned using it.

**17 words (current):**
vrath=threshold, sketh=remembers, urath=the dead, quz=listen,
keth=stone, vrass=the pattern, dur=before, skur=open, zhal=the bell,
greth=binds, kur=the void, uthar=speaks, voss=bone, skral=truth,
mrath=the hollow, grath=ware, zhar=song

**Lab inscription:** "Vrath sketh urath. Grath zhar keth."
= "The threshold remembers the dead. Ware ye the song of the stone."

**Scale target:** 200-300 words across 8 categories.
Categories: cosmic, body, time, place, people, action, essence, number.
Phoneme grammar: CVC/CCVC/CVCC. Clusters: vr, sk, gr, kr, zh, dr.
Finals: th, ss, k, r, l. Avoid soft consonants alone, long vowels, English-adjacent sounds.

Each word has a `glyph_seed` (fixed int) — always produces the same glyph.
`data/deep_tongue.json` v2 format: deep, common, concept, category, glyph_seed, notes.

**Learning tiers:**
- Tier 1 (~50) — found texts and standing stones, learnable naturally
- Tier 2 (~100) — specialist sources (alchemical, medical, ritual)
- Tier 3 (~50) — rare, locked behind specific conditions
- Tier 4 (~rest) — appear in texts, never translatable, deliberately lost

Text rendering MUST support per-word font switching.
`font_deep` = Junicode italic in night_purple until Tier 4 bitmap font.
Deep tongue expansion is content work — no code changes needed to add words.

---

## Debug System

```
F1          Debug GUI overlay (grouped command listing + rune sigil)
F2          FOV visualization
F3          Reveal local map
F4          SubMap highlights on overmap
F5          Teleport to nearest SubMap
F6          Set time
F7          Set needs/corruption
F8          Force chunk regen
Shift+F8    Invincibility toggle (also freezes needs decay)
F9          Full state dump
F10         Teleport by coordinates
F11         Wipe save
F12         Remap sprite tile
`           Console
ESC         Two presses to quit. ESC while debug overlay → closes overlay only.
PgUp/PgDn  Scroll message log

Console commands:
RESONANCE:  set_exposure, set_corruption, pulse_bell, pulse_cracked,
            show_resonance, show_corruption_rate, scan_resonance
WEATHER:    set_weather, show_weather, force_weird_weather,
            test_rain [light|heavy|storm], test_fog [fog|forgetting],
            test_snow, stop_weather
VISUAL:     particle_stats, test_waystone_ring, clear_particles,
            toggle_callouts [damage|sounds|status|all]
ENTITIES:   spawn_creature <id>, spawn_item <id>
PERKS:      grant_perk <id>, remove_perk <id>, list_perks
MOVEMENT:   toggle_move_log
DECOR:      place_decor <id>, place_decor clear
SYSTEM:     give_debug_weapon, help
```
Full reference: `docs/DEBUG.md`

---

## Design Constraints — Never Violate

- **No +x% stat perks.** Perks open ontological doors.
- **No fire/water/electric damage.** Six essences only.
- **Combat weapon-driven.** Weapon properties over character skill.
- **Palette discipline.** AAP-64 via engine/palette.py. No raw RGB in code.
- **Tone discipline.** No generic RPG language. Never "You are [state]."
- **Rituals through conditions, not flags.**
- **Corruption as path, not meter.**
- **Text rendering must support per-word font switching.**
- **Entrance structures are locations, not doors.**
- **Tile mapper writes to draft only.**
- **Generation layering model preserved.**
- **Everything has an essence.** Nothing is neutral.
- **Bodies are not loot containers.** The transfigured dead are environmental.
- **Towns are more dangerous than wilderness.**
- **Never name a damage formula.** Let the feedback teach.
- **Generation functions never write engine game-state fields.**
  (This has caused the recurring FOV bug. Non-negotiable.)
- **Bog wraith has NO callout sounds.**
- **WFC is used sparingly.** Only where it genuinely enhances game feel.
- **Never hardcode colours.** `from engine.palette import *`, semantic aliases only.
- **Never hardcode weather values.** All precipitation in `data/weather.json`.
- **Data-driven by default.** New content should not require code changes.

---

## Tier Roadmap

### Tier 2 — World & Exploration ✓
```
✓ Entrance architecture, procedural names, WorldMyth
✓ Overmap sidebar with biome icons, scrollable
✓ SubMap system (dungeons underground, stair traversal)
✓ Starting location (lab submap, forest surface)
✓ Found text framework (40+ texts, BSP dungeons)
✓ UI redesign (Junicode, weathered temple panels)
✓ World generation (VUKH, elevation, hydrology, biomes, capital, towns, roads)
✓ Zone entry messages (resonance tier changes)
✓ Urizen spritesheet (12px, full-colour mode, autotile walls)
✓ Tile variant system
✓ Multi-chunk towns (3×3, seamless, WFC fill)
✓ Street lamps (working/sputtering/dead)
✓ Reality bubble scaffolding (chunk-set gate)
✓ River terrain (river_water/bank/stones)
✓ Road local terrain (edge-to-edge, winding, 3-wide)
✓ WFC foundation (solver, town_plaza, town_block tilesets)
✓ Terrain effects (move_cost, secondary effects)
✓ Waystones (guaranteed near start, road placement)
✓ Bell/resonance system (core mechanic live)
✓ Weather system (10 states, data-driven visuals + mechanics)
✓ Particle system (sparkle, blood, rings, adaptive cap)
✓ Callout system (damage numbers, creature sounds, crits)
✓ Critical hit system
✓ Perk system (K screen, purchase, hook architecture, 6 live perks)
✓ Leveling (EXP, level-up, health scaling, perk points)
✓ Palette unification (AAP-64)
✓ Death screen
✓ Decorative tile layer (chunk.decor, render pass, authoring guide)
✓ Town generator (3×3, districts, buildings, bells, consistent density)
```

### Tier 3 — Systems Depth (CURRENT)
```
✓ Hit location + armor layer + essence systems
✓ Equipment system (10 slots + 3 talisman, save/load)
✓ Monster attacks through resolve_attack()
✓ Six creature special abilities
✓ Ghost / last-known position system
✓ Creature pursuit + aggression
✓ Essence resistance, essence profile in examine
✓ Severance + Revelation weapons
✓ Perk hook architecture (9 events, pure handlers)
✓ FOV rework (moon phase, failsafe, fog, wraith aura)
✓ Weather mechanics (all four wired)
✓ Chunk transition mirroring
✓ Look mode (surfaces terrain + decor + blood + entities)

✓ Survival system (data/survival.json, staged consequences, move penalty, hp drain, eat/drink, W key terrain drinking)
✓ Harvestable plants (G key harvest + Shift+G adjacent harvest, 5 plant items, depleted tile variants, data-driven via terrain.json)
✓ Found texts on surface (16 texts authored, all building text_id refs resolve, wired via building special_tiles + TownData.item_spawns)
□ Containers (interactable furniture — requires survival system first)
□ Loot tables (room-level, context-specific — requires containers)
✓ Crafting foundation (keyword system, data/keywords.json, can_craft/attempt_craft, C screen)
□ Alchemy foundation (distillation chain, herblore → essence)
□ Campfire (entry point for alchemy + warmth + cooking)
□ Health screen UI (H key, procedural silhouette)
□ Resonance system full (bells decay, remaining 4 thresholds)
□ Stealth system (tall grass concealment wiring)
□ Weapon movesets
□ Reality bubble full (stair transfer, density management)
□ More perks (all affinity categories)
□ Deep tongue learning through gameplay
□ Magic/bell system foundation
□ NPC: The Hollow Merchant (stretch target)
□ Generation Layers 1 + 2
□ Particle system full
□ SoundManager stub
□ Starting lab layout redesign
```

### Tier 4 — Polish
```
□ Merge tiles/sprite_map/terrain JSON
□ Multi-tile sprite support
□ Deep tongue bitmap font
□ Full sound implementation
□ Main menu + character creation
□ Layout editor tool
□ Mod support
□ Metaprogression (meta.json)
□ Home chunk (player base, crops — stretch goal)
```

---

## Current State
*Last updated: Cross-chunk entity pursuit session.*

### Working

**Survival System:**
- `data/survival.json` is single source of truth for all survival tuning.
- Hunger/thirst: 4 stages each, data-driven messages, move_penalty, hp_drain per N turns.
- Biome modifiers applied to tick rate each turn.
- `W` key drinks from drinkable terrain (shallow_water).
- Hunger/thirst UI bars with colour shift.
- Items: dried_provisions, water_skin, bitter_herb, coldbell_cutting + 4 new harvestable items.

**Keyword System:**
- `data/keywords.json` — 15 keywords: cutting, binding, burning, edible, drinkable, resonant,
  vital, corrosive, soporific, purgative, bitter, waxy, fibrous, bony, viscous.
  Each has: display name, color (palette alias string), description.
- `data_loader.py`: `self.keywords: dict` loads keywords.json.
- `entities/item.py`: `item.keywords: list` field, default [].
- `engine/item_factory.py`: assigns `item.keywords = defn.get("keywords", [])` on creation.
- All item JSONs (weapons, armor, tools, consumables, shields, talismans) have `keywords` field.
- Inventory detail panel shows keyword tags: `[display_name] ●●○○○` in keyword's colour.
  Colour resolved via `getattr(engine.palette_module, color_alias)`.

**Crafting Foundation:**
- `engine/crafting.py`: pure functions `can_craft(recipe, inv, kw_data) → (bool, missing_list)`
  and `attempt_craft(recipe, inv, kw_data)`. One-item-one-slot rule; greedy lowest-tier-first.
- `data/recipes/campfire.json`: components-based format — `[burning ≥1 ×2] + [cutting ≥1 ×1]`.
- `C` key craft screen: lists all data/recipes/*.json, shows `[tag ≥ tier] × quantity`
  and `(have: N)` counts per slot. Locked recipe path shows `locked_hint` in MSG_LORE.
  Action hint shows ENTER only when craftable.

**Harvesting:**
- `G` key: checks harvestable terrain at player tile first; falls through to item pickup if not.
  Data-driven: terrain.json drives item + depleted tile. DEBUG_MODE logs tile/terrain on G press.
- `Shift+G`: builds candidate set of all 8 adjacent tiles with harvestable terrain or floor items.
  - 0 candidates → no turn spent, no message.
  - 1 candidate → interact immediately (harvest or pick up), spend 1 turn.
  - 2+ candidates → enter `GameMode.INTERACTION_CURSOR`: cursor on nearest candidate,
    arrow/vi-keys navigate between candidates, ENTER/G confirms, ESC cancels (no turn).
  Cursor reuses `LookMode.render_cursor` for highlight. One-line hint at bottom of viewport.
  Works from both LOCAL and LOOK mode (LOOK closes first).
- 5 harvestable terrain entries: coldbell_flower, flower_pilgrims_woe, flower_murk_violet,
  shroom_sulphur_cap, shroom_prophets_eye. Each has depleted variant.
- 5 harvest items: coldbell_cutting, pilgrims_woe_petals, murk_violet_stem,
  sulphur_cap_fragment, prophets_eye_cap.

**Surface Found Texts:**
- 16 texts authored for surface buildings (12 original + 4 new in this session).
  All text_id references in building special_tiles now resolve — zero broken refs.
- 4 new texts: world_graffiti_b (waystone plinth graffiti), world_official_a (belfry duty ledger),
  world_official_b (bell access restriction notice), world_sermon_a (folk saint alcove prayer).
- Building special_tiles wired: `_stamp_building_at` returns item specs, propagated via
  placed_buildings → TownData.item_spawns → engine processes at both chunk-enter sites.
- 10 building layouts have special_tiles. Waystone prayer spawned near waystone_pos.
- Save/load: item_spawns serialised in save_manager.py.

**Core:**
- Player starts in forest chunk far from VUKH.
- VUKH at world centre (2×2), capital ring, towns 3×3 quadrant-balanced.
- Rivers, roads, biomes, difficulty bands, resonance all working.
- Zone entry messages, chunk transitions (position-mirroring, no diagonal false positives).
- Overmap: scrollable, rivers/roads as bitmask lines, biome legends.
- Reality bubble: chunk-set gate.

**Combat:**
- Full pipeline: hit location, armour layers, 6 essences, CombatResult.
- Single HP pool, hit-location multipliers, dodge, block, Faceted Ward shield.
- Critical hits: ×2.5 pre-armour, screen shake, particles.
- All six creature special abilities working.
- Essence resistance messages. Three-state combat feedback.

**Equipment:** All 10 slots + 3 talisman slots. Full stat block in inventory. Save/load clean.

**Visual Systems:**
- AAP-64 palette unified in engine/palette.py.
- Particle system: blood, sparkle, ring, circle. Adaptive cap.
- Callout system: damage numbers, creature sounds, status, CRITICAL.
- Tile visual_fx: pulse_glow, pulse_dim, sparkle, flicker.
- Decorative layer: `chunk.decor`, render pass between terrain and entities.
  Same lighting. Same transparency. Authored via decor_utils API.
  5 decoratives live. Serialises with chunk. Look mode surfaces descriptions.
- Weather: fog (noise-perturbed gradient + wisps), rain/snow, resonance storm,
  forgetting fog. All driven by data/weather.json.

**FOV:**
- Underground=1, surface day=40, surface night=moon phase table.
- Three-layer failsafe. Bog wraith aura via _wraith_aura_state.
- FOV collapse bug confirmed fixed (root: stale current_submap_id in debug teleports).

**Town Generator:**
- 3×3 plaza-anchored footprint. District zoning. 24+ building layouts.
- Consistent 18-25 buildings/chunk across seeds.
- Road tiles excluded from placement. South zones flip_v.
- Corner scatter with path connectors.
- Look mode: terrain + decor + blood + entities all surfaced.

**Resonance & Bells:** Live. Exposure, corruption, wind trigger. Weather integration.

**Leveling:** EXP on kill, difficulty-delta scaled. Level up: HP ×1.08, perk point.

**Perk System:** 9-event hook architecture. 6 live perks across 4 categories.

**Screens:** Inventory (I), Perk (K), Health (H), Death, Look mode (;/x), Debug (F1-F12 + console).

### Known Issues

**Content:**
- Starting lab layout is placeholder — redesign pass needed.
- Sprite columns for decorative tiles are placeholder — need F12 visual audit.
- document/inscription sprite coords are placeholders.
- Depleted plant sprites use base plant sprite for now — distinct sprites needed.
- No containers/interactable furniture yet.

**Systems Not Yet Wired:**
- Deep tongue not learnable through gameplay.
- Bell state has no mechanical effect beyond creature gating.
- VisualEventQueue wired but dormant.
- Remaining 4 corruption thresholds are stubs.
- Impairments: only dominant_hand_lost and leg_lost have mechanical effect.
- Chilled has no mechanical effect.

**UI:**
- Inventory/examine popups centre on full screen not viewport.
- Health screen (H key, procedural silhouette) not yet built.
- Procedural creature icons in examine not yet built.

**Generation:**
- Entrance structures hard to find without F5 debug teleport.
- Chunk transition terrain visually abrupt across surface boundary.
- Locus chunk special content is Tier 3.
- Dungeon void tiles not implemented (auto-tiling artifacts).

**Cross-chunk entity pursuit:**
- `_pending_transfer: list` on Engine — hot entities removed from old chunk before cache, merged into new chunk after load.
- Hot criteria: `AIState.HUNTING` or `AIState.ALERTED`, alive, within 3 Chebyshev tiles of crossed boundary, `can_cross_chunks: true` in creature JSON.
- Entry placement: mirrors position to opposite edge of new chunk (same axis formula as player). Shell-search for unoccupied walkable, absolute fallback to `_find_walkable_near(max_radius=50)`.
- `_last_known_px/py` and `ai.target_x/y` set to player's new position. `ai.state` preserved (HUNTING/ALERTED).
- `can_cross_chunks: true` set on: highland_bandit, heath_stalker, plague_crow. All others default false.
- `pursuit_turns_without_contact: int` on AI component — increments each turn entity is chasing without LOS, resets on LOS. At `pursuit_timeout` (default 20, read from creature JSON) → transitions to WANDERING.
- `at_edge` abandonment gated: only fires if `last_known` is also near edge (prevents transferred entities abandoning pursuit from their entry position).
- Debug: `[TRANSFER]` lines in DEBUG_MODE on every chunk transition.
- Serialised: `pursuit_turns_without_contact` in `_serialize_entity` / `_deserialize_entities`.

**Deferred — reality bubble full implementation:**
- Entity stacking partial fix only.
- Entities do not follow across stairs (only surface chunk boundaries).

---

## Claude Code Usage Notes

> Read CLAUDE.md in full before touching any file.
> Dependency order: components → entities → engine → rendering → generation

### Inviolable Rules
- `from engine.palette import *` — no raw RGB tuples anywhere else
- No hardcoded weather values — all precipitation in `data/weather.json`
- Generation functions NEVER write engine game-state fields
- Bog wraith has NO callout sounds
- Data-driven by default — new content must not require code changes
- Tone: flat/terse for mundane, strange/archaic for ancient
- Never "You are [state]." See tone rules.
- Targeted edits over rewrites. Read files before editing. Confirm signatures.

### Mandatory Close-of-Session Protocol
1. `python main.py` — confirm no crash, no traceback
2. Descend to lab submap, ascend to surface — confirm FOV correct both ways
3. Output change summary in this format:

```
CHANGE SUMMARY
==============
Files modified:
  <filepath> — <one line: what changed and why>

Bugs / tasks addressed:
  <item> — confirmed fixed / partial / deferred, and why

Secondary issues noticed (do not fix without instruction):
  <observations>

Crash check: PASS / FAIL
Lab submap ascent: PASS / FAIL
```

### Adding Creatures
1. data/tiles.json + data/sprites/sprite_map.json (col/row from sprite_ref.py)
2. data/bodies/body_<id>.json
3. data/entities/creatures/id.json — required: body_id, essence_modifiers, damage_dice,
   sees_in_dark, attack_verb, blood_type, callout_sounds (omit for bog wraith)
4. data/zones/relevant_zone.json
5. Test: `` ` `` then `spawn_creature <id>`

### Adding Weapons
1. data/items/weapons/id.json — required: id, name, type, slot, damage_dice,
   essence OR essences[], essence_strength, description, weight
2. data/loot/dungeon_weapons.json
3. Multi-essence: `"essences": [{"type": "dissolution", "strength": 2.0}, ...]`

### Adding Terrain
tiles.json (ascii required) → terrain.json (move_cost, secondary_effect,
resonance_emit, visual_fx optional) → sprite_map.json

### Adding a Perk
1. data/perks/<id>.json — required: id, name, category, cost, description
   (project voice — no mechanics text), effects[] (mechanical plain language),
   hooks[], conflicts[], requires[]
2. engine/perk_handlers.py — handler function tagged _is_perk_handler=True
3. Add to HANDLER_MAP
4. Test: `grant_perk <id>`

### Adding a Decorative
Full guide: `docs/DECORATIVES.md`
Short form: entry in data/decoratives.json → verify sprite with F12 →
test with `place_decor <id>` in console

### Adding a Biome
data/biomes/id.json — fields: id, display_name, overmap_tile, overmap_color (AAP-64 RGB),
base_resonance, elevation_range, moisture_range, difficulty_base,
river_adjacent, generator, creature_zones, submap_types, entry_messages, resonance_messages.

### Adding Weather Visuals
data/weather.json only. Fields: type (streak/dot/glitch), spacing, speed_y, speed_x,
color, alpha, streak_len, width, intensity_scale, glitch_* for glitch type.

### Adding SubMap Layouts
See `docs/LAYOUT_AUTHORING.md`

### Tone Rules
- Flat/specific for mundane. Strange/archaic for ancient.
- Never "You are [state]." → "Chilled." not "You are chilled."
- Never "Level up!" → "Something shifts in you."
- Never "X exp gained." → "A weight settles. (+X)"
- Never "You have no perks." → "Nothing has taken root yet."
- Never name a damage formula.
