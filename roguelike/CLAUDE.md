> **Arc A status:** Historical source retained below. Creative intent remains a design reference; technical claims need the [current implementation and authority map](docs/owner/STATUS.md). This banner does not resolve open design decisions.

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

### Spritesheets — Multi-Sheet System (current)
`ZOOM_LEVEL = 2` in config.py. Source tiles 16×16px → 32px display tiles.

All sprite sheets are defined in `data/sprites/sprite_map.json` under a `"sheets"` block.
Every tile entry uses `{"sheet": "<name>", "col": N, "row": N}` — true 2D grid coordinates.
24 columns wide on all authored sheets. Sprites are full-colour on transparent backgrounds.

**Primary authored sheets (where new work goes):**
```
terrain.png   — terrain tiles, flora, walls, roads, water, bells, blood, overmap icons
objects.png   — items, tools, weapons, armour, consumables, documents
creatures.png — all creature sprites and player sprite
```

**Legacy sheets (still referenced, pending migration to primary sheets):**
```
urizen    — ash, ancient_floor, grey_stone, wall_pillar, cobblestone_cracked,
            cobblestone_mossy, debris_scatter, all 5 decor_* tiles (placeholder cols)
pixel     — wall (only entry)
```
Urizen entries use single-row index convention: `"col": N, "row": 0`.
When migrating a tile off urizen, update sprite_map.json with true 2D col/row and
correct sheet name. The `tile_w`/`tile_h` for all sheets including urizen is 16 in
sprite_map.json — the renderer handles all sheets uniformly.

**hexany_creatures** sheet is defined but not currently assigned to any tile.

**Pending visual work:**
- All 5 `decor_*` tiles are on urizen with placeholder column indices — need
  sprites authored in objects.png and sprite_map.json updated
- `cobblestone_cracked`, `cobblestone_mossy`, `debris_scatter` on urizen —
  pending migration to terrain.png
- `ash`, `ancient_floor`, `grey_stone`, `wall_pillar` on urizen — pending migration

**Adding a new sprite:**
1. Author the sprite in the appropriate sheet (terrain/objects/creatures)
2. Note the col/row coordinates (0-indexed, 24 columns wide)
3. Add entry to `data/sprites/sprite_map.json` under `"tiles"`:
   `"tile_id": {"sheet": "terrain", "col": N, "row": N}`
4. Ensure `data/tiles.json` has an `"ascii"` fallback field for this tile ID
5. Verify in-game with F12 remap tool if needed

**Rendering:**
- Full-colour sprites rendered as-is
- Lighting applied as brightness overlay
- Torch warmth: 60% neutral brightness + 40% light colour tint
- Memory tiles: darkened to ~15% brightness
- Blank sprite detection: completely transparent extractions return None → ASCII fallback
- Every tile in tiles.json MUST have an "ascii" field

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
Data-driven. Defined effects: `sparkle`, `pulse_glow`, `pulse_dim`, `flicker`, `gas_overlay` (stub),
`embers`, `flame_low`, `flame_med`, `flame_high`, `smoke_incense`.
Flame types route to their particle factory in the engine emitter block at different frame cadences.
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
                        55+ layouts across 7 categories.
  decoratives.json      68 entries (16 containers, 52 decorative).
                        Original containers: barrel, crate, sack, coffer.
                        New containers: cold_hearth, wooden_shelf, stone_coffer,
                        offering_bowl, rubble_pile, writing_desk, medicine_chest,
                        bone_box, iron_chest, clay_pot_cluster, tool_rack, grain_sack_open.
                        Environmental storytelling decor: meal_on_table, overturned_chair,
                        wound_cloth, child_toy, dried_herbs, tallow_dip, offering_coins,
                        measuring_stone, bell_rope, warning_mark, bile_stain,
                        shattered_vessel, salt_block, inscription_stone, worn_mat,
                        iron_hook, carved_post, standing_water, web_cluster,
                        oriented_remains.
                        Blood/bells/campfire/processing/terrain-to-decor/plants unchanged.
                        Each entry: id, ascii, blocks_movement, blocks_sight,
                        description, optional: interactable, visual_fx, light_emit,
                        resonance_emit, container, harvestable, harvest_item, depleted_id.
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
  loot_pools/           11 pool files: commoner_kitchen, commoner_bedroom,
                        storage_general, storage_tools, shrine_offering,
                        shrine_equipment, ruins_scatter, wilderness_cache,
                        alchemist_shop, alchemist_reagents, noble_generic.
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

**Decor-layer tiles (former terrain):**
- waystone_plinth: blocks_movement, interactable, resonance_emit 0.20, pulse_dim, light_emit 1
- stele: blocks_movement, interactable, resonance_emit 0.05, pulse_dim
- street_lamp_working/sputtering/dead: blocks_movement, light_emit (5/3/0)
- All 10 plant/flower/mushroom tiles (5 harvestable + 5 depleted)
- bell_dead: interactable (examine_dead_bell)

**Decor properties wired:**
- `blocks_movement` — checked in `_decor_blocks_movement()` (engine.py)
- `light_emit` — scanned in FOV update (engine.py)
- `visual_fx` — particles (engine.py) + brightness rendering (renderer.py)
- `resonance_emit` — resonance scan, pulse timers, sparkles, look mode, debug
- `interactable` — dispatch priority 1st (before terrain)
- `harvestable` — `_try_harvest()` checks decor, depletes to `depleted_id`

**Converting a terrain tile to decor:**
1. Add entry to `data/decoratives.json` with full properties
2. Add terrain_id to `_DECOR_TERRAIN_IDS` in layout_stamper.py (auto-redirects during stamping)
3. For plant tiles: add to `PLANT_DECOR_IDS` in rendering/decor.py (auto-redirects in set_tile)
4. Mark terrain.json entry as deprecated (keep for save compat, never written)
5. Update any direct `set_tile()` calls to use `place_decor()` instead

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

### Creature Speed System
- `speed` field on creature JSON (float, default 1.0). 1.0 = every turn. 0.5 = half speed.
- `move_accumulator` on AI component (float, serialised). Each turn: accumulator += speed.
  Skip turn if accumulator < 1.0. Subtract 1.0 per step. Max 2 steps/turn for speed > 1.0.
- Applied in ai_system.py process() loop AND _tick_live_pursuers() live pursuer movement.
- Speed values: plague_crow 1.3, heath_stalker 1.2, highland_bandit 1.0, bog_wraith 0.9,
  hollow_revenant 0.8, drowned_revenant 0.75, sewer_thing 0.7, barrow_wight 0.6,
  grave_thing 0.6, hollow_knight 0.5, stone_lurker 0.5, briar_lurker 0.45.

### Sprint System
- **Keybind:** Shift+W only (SPRINT_KEY in display_config.py). Shift+arrow does nothing.
  Sprint is a mode — once active, all directional moves consume sprint turns without Shift held.
- **Accumulator model:** `player_move_accumulator` gates whether `_advance_turn()` fires.
  Each sprint move: budget += 1.0, cost = 1.0/SPRINT_SPEED_MULT (0.5).
  AI ticks only when budget >= 1.0 — at speed 2.0, AI ticks every 2 player moves.
  Non-movement actions (wait, interact, inventory) always tick AI normally (cost 1.0).
- `sprint_turns_remaining` decrements per player MOVE, not per AI tick.
- **Combat penalty:** -25% pre-armour damage while sprinting (SPRINT_HIT_PENALTY).
- **Constants** in display_config.py: SPRINT_KEY (pygame.K_w), SPRINT_DURATION (8),
  SPRINT_COOLDOWN (30), SPRINT_SPEED_MULT (2.0), SPRINT_HIT_PENALTY (-0.25).
- **State:** engine.sprint_turns_remaining, sprint_cooldown_remaining,
  player_move_accumulator. All serialised in save.
- **Visual feedback:**
  - Pulsing SPRINT pip badge (bottom-right of status bar) with ●/○ duration pips.
    Sin-wave brightness oscillation (~1s period). Disappears cleanly on expiry.
  - "SPRINT" callout above player on activation (status font, RESONANCE_LOW).
  - "—" callout on expiry (UI_TEXT_DIM). No message log entries for sprint start/end.
  - Streak particles (4-6 world-space streaks, RESONANCE_LOW, ~6 frames) on every sprint move.
  - "shift-w: sprint" hint text (UI_TEXT_DIM) shown bottom-right when sprint available
    (cooldown == 0, not active). Hidden on cooldown. Derived from SPRINT_KEY at render time.
- **Cooldown** ticks in `_advance_turn()` (world time), not player moves.
  During sprint, world turns pass at half rate relative to player moves.

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

### World Age & Escalation — Design Canon

The world does not scale to the player. But it does change over time.

**Core principle:** The world is in a slow process of settling into its new state.
Scavengers move in. Transformed things spread. Bargains deteriorate.
The longer the player is in the world, the further this process has advanced.
This is not difficulty scaling — it is ecology. The world does not know the player is there.

**`world_age`** — a counter on the world state, incremented each in-game day.
Stored in world save, serialised like `world_seed`.

**`escalation_tier`** — derived from `world_age`, 0–4:
```
Tier 0  days 0–6    Immediate aftermath. Stunned silence.
Tier 1  days 7–20   Scavengers and survivors moving in.
Tier 2  days 21–50  Territorial establishment. Danger concentrates.
Tier 3  days 51–99  Something has organised. Old bargains fully broken.
Tier 4  days 100+   The new order. The player either understands it or does not.
```

**`data/escalation.json`** — the data file. Not yet authored. Planned fields:
- `tier_thresholds`: day counts per tier
- `spawn_modifiers`: per-tier creature density multipliers by zone
- `terrain_decay`: per-tier probability of terrain state changes (cracked walls, flooded cellars)
- `text_variants`: message overrides for zone entry at each tier

**`age_tier_min` on creature JSON** — optional int field. Creature will not spawn
below this escalation tier. Used for creatures that only appear as the world degrades further.

**What this is NOT:**
- Not a difficulty ramp. Tier 4 is not 'hard mode'. It is a different world state.
- Not gated content. The player can reach higher-tier zones at any time.
- Not announced. No UI readout of world age or tier. The world just is what it is.
- Not implemented yet. Design canon only.

**Implementation order when this becomes Tier 3 work:**
1. `world_age` on world state, increment in `_advance_turn()` on day rollover
2. `escalation_tier` property derived from `world_age`
3. `data/escalation.json` authored
4. `age_tier_min` guard in creature factory spawn check
5. Zone entry messages pull from escalation-tier variants

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
- 55+ building layouts across 7 categories (residential=12, commercial=7, civic=7,
  religious=8, storage=7, ruins=8, wilderness=6), plus 2 plaza layouts
- 1-tile clearance buffer enforced between all building placements.
  Eliminates cross-building wall junction autotile artifacts.
  Side effect: natural alleyways between structures. Plaza exempt.
  Extension point: `allow_adjacent: true` in layout JSON suppresses buffer.
- Density: 10-15 buildings per chunk across seeds (reduced from 18-25 by buffer)
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

| Creature | Damage | Key Armor | Special Ability | Blood | Speed |
|---|---|---|---|---|---|
| Barrow Wight | 1d6+1 | Resonance AV2, bone AV3 | Corruption adjacency | bone_dust | 0.6 |
| Hollow Knight | 1d8+2 | Plate AV6, helm AV5 | Resonant disruption | bone_dust | 0.5 |
| Hollow Revenant | 1d4+1 | Shell AV1 | — | bone_dust | 0.8 |
| Drowned Revenant | 1d4+1 | Flesh AV1 | — | red | 0.75 |
| Grave Thing | 1d6 | Bone AV4, tissue AV2 | — | bone_dust | 0.6 |
| Heath Stalker | 1d6 | Hide AV2, muscle AV1 | — | red | 1.2 |
| Briar Lurker | 1d4 | Thornmass AV3 | Retaliating thorns | none | 0.45 |
| Stone Lurker | 1d8+2 | Carapace AV6, inner AV4 | Hibernation ambush | none | 0.5 |
| Bog Wraith | 1d4 | Mist AV3 | FOV drain | ectoplasm | 0.9 |
| Plague Crow | 1d3 | Feathers AV0 | Sickness on hit | red | 1.3 |
| Highland Bandit | 1d6+1 | None | — | red | 1.0 |

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

### Vine Network System (`engine/vine_system.py`)
Not a mobile entity — a growing decor pattern managed by a spread system.

**Decor tiles:** `vine_growth` (walkable, interactable:vine), `vine_eyestalk` (blocks_movement,
  interactable:vine), `vine_spore_vent` (visual_fx:gas_overlay).
**Terrain:** `vine_growth` in terrain.json (move_cost 1.5, walkable).
**Config:** `data/entities/creatures/vine_network.json` — spread_interval(5), spread_chance(0.7),
  eyestalk_threshold(8), spore_threshold(20), max_tiles(50), eyestalk_attack_range(3),
  eyestalk_damage_dice(1d3), spore_damage_per_turn(2), spore_player_range(2).

**State:** `local_map.vine_networks: list[dict]` — each: {tiles, eyestalks, spore_vents, origin, age}.
  Serialised with chunk via pickle.

**Spread:** `tick_vine_networks(engine)` called from `_advance_turn()` every `spread_interval` turns.
  Orthogonal expansion onto walkable non-road non-water terrain. Capped at max_tiles.
  Eyestalk spawns at threshold (farthest tile from origin). Spore vent spawns at threshold (near centre).

**Combat:** Eyestalk attacks player within range (resolve_attack with 1d3). Spore vent deals
  HP damage per turn to player within 2 tiles ("The air chokes." MSG_DANGER). Gas damage
  deduplicated across vents per turn.

**Interaction:** E key on vine tile → cutting weapon check. vine_growth: cutting≥1, vine_eyestalk:
  cutting≥2. Calls `destroy_vine_tile()` — removes tile from network, clears decor. Empty
  network auto-removed.

**Spawning:** After resonance discharge, 20% chance in swamp/drowned_wood/forest biomes.
  Silent — no message. Creates single vine_growth decor at random walkable position.

**Particles:** Green sparkle on spread, streak from eyestalk on attack, gas puff at spore vent.

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

### Weapon Movesets (IMPLEMENTED)
**Keys:** Q (MOVESET_KEY_1) and R (MOVESET_KEY_2) in display_config.py.
**Framework:** `engine/movesets.py` — MovesetResult dataclass, execute_moveset(),
  get_moveset_action(), apply_damage_mult(). Pure functions.
**Engine state:** `moveset_cooldowns: dict[str, int]` — decremented each AI tick.
  `creature_knowledge: dict[str, dict]` — revealed weaknesses/strengths per creature type.
  Both serialised in save.
**HUD:** Bottom-left of status bar shows [Q] name (cooldown) and [R] name (cooldown).
  Greyed (UI_TEXT_DIM) on cooldown, weapon essence colour when ready.

**Weapon Actions (all 6 weapons):**
```
crude_blade:       Q Hack (1.3× dmg, no cd)        R Desperate Slash (1.5× dmg, cd 8, ≤50% HP gate)
heavy_blade:       Q Press (free move on kill, cd 3) R Rending Strike (destroy armour, cd 6, shake 3)
binding_knife:     Q Connection Cut (suppress 5t, cd 15) R Slip Past (ignore armour, behind pos, cd 5)
dissolution_blade: Q Corrode (reduce AV -1, cd 8)   R Seep (dissolution pool on kill, cd 12)
severance_blade:   Q Severing Cut (1.2× dmg, cd 10) R Disconnect (suppress + AoE disrupt 6 tiles, cd 20)
revelation_lens:   Q Reveal (reveal weakness, no cd) R True Strike (ignore armour+dodge, cd 6)
```

**MovesetResult effects:**
damage_mult, ignore_armour, ignore_dodge, free_move (on kill), destroy_armour,
reduce_av, suppress_ability (turns), reveal_knowledge, aoe_disrupt_range/turns,
place_pool (decor on kill), hp_gate, screen_shake, positioning ("behind").

**creature_knowledge:** Populated by revelation_lens Reveal action. Stores
revealed_weaknesses and revealed_strengths per creature_id. Shown in examine
popup when player has carrion_eye perk, threshold_resonance_sight, or DEBUG_MODE.

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

### Language Component (`components/language.py`)
```python
known_deep_words:   set[str]          # word IDs the player has learned (lowercase)
translation_events: dict[str, int]    # word_id → turn learned (for visual effect)
taught_texts:       set[str]          # text_ids that have already taught words
recovered_spans:    set[tuple]        # (text_id, page_idx, span_idx) for Witnessing recovery
recovered_text:     dict[tuple, str]  # recovered span content
shown_lexicon_hint: bool              # True after "Press [L]" fires once
```
Methods: `knows(word)`, `learn(word, turn) → bool`, `recover_span(...)`, `is_recovered(...)`.
All fields serialised in save_manager.py (player.json).

### Lexicon Data (`data/deep_tongue.json`)
**318 words** across 9 categories + 1 special word.
Word entry fields: `id, deep, common, concept, category, tier, glyph_seed, learn_sources`.
```
action: 40    cosmic: 40    body: 40    people: 41    time: 40
essence: 40   number: 30    ominous: 30   legacy: 17
```
**Tier distribution:** T1=147, T2=111, T3=38, T4=22.
**Tier 1:** place, number, legacy, concrete body/time/people/action — waystone learnable.
**Tier 2:** specialist vocabulary — internal body, abstract time, metaphysical people,
  ritual action, all essence (except dangerous), most cosmic phenomena.
  Learnable from shrines, alchemical texts, medical records, specialist sources.
**Tier 3:** rare/dangerous — ominous category exclusively (30 words) + 6 dangerous
  essence/cosmic words + 2 mechanism words. Corruption threshold (0.70) teaches
  2-3 ominous words. Other T3 words require specific text sources.
**Tier 4:** irreducibly deep-one — 22 words. Bell tuning terminology, discharge mechanism,
  deep one self-designations, VUKH function, god-fragment names, the apocalypse name.
  Glyphs only in rendering — never resolve to translation. Archaeology system gates
  these (Tier 4 stretch goal). Includes `vukhar` (`learn_sources: ["bellwright"]`).
**Phoneme system:** 268 unique phonemes in `data/deep_tongue_phonemes.json`.
Grammar: CVC/CCVC/CVCC. Clusters: vr, sk, gr, kr, zh, dr.

### Word Teaching API (`engine/language_system.py`)
All pure functions — no engine state imports.
- `learn_word(word_id, source, language, all_words, rng) → (bool, str)`:
  Learns specific word. If already known, falls back to `learn_from_category` with same category/tier.
  Validates source against word's `learn_sources` list.
- `learn_from_category(category, tier, source, language, all_words, rng) → (bool, str)`:
  Picks random unknown word from category+tier pool. Fallback: any unknown Tier 1 word.
  Excludes `known_deep_words`. Never duplicates.
- `learn_from_text(text_def, language, all_words, rng) → list[str]`:
  Reads text's `teach_words` block (`{count, categories, tier}`). Teaches one word from
  first category via `learn_from_category`. Returns list of 0 or 1 learned word_ids.
- `validate_deep_tongue_text(body, all_words) → list[str]`: Content validation — finds
  tokens not in lexicon. Used by data_loader in DEBUG_MODE.
- `get_unknown_words_in_text(text_body, language, all_words) → list[str]`:
  Returns unlearned deep tongue words in a text body. Used by text reader rendering.

### Learning Restrictions
- **Tier 1-2:** returned by `get_learnable_words()` / `learn_from_category()` normally.
- **Tier 3 (ominous):** excluded from `get_learnable_words()` (tier >= 3 filter).
  Corruption 0.70 threshold bypasses this — directly selects ominous words.
  Ominous words also excluded from waystone learning (`source == "waystone"` filter).
- **Tier 4:** never returned by any automatic learning function.
  Glyphs only in rendering — never resolve. Archaeology system gates these.
  `vukhar` requires explicit `learn_word("vukhar", "bellwright")` (not yet wired).
- **Legacy category:** no restriction, learnable from all sources (all tier 1).

### Active Learning Sources

**1. Waystone examination** (E key on waystone_plinth decor)
- **Function:** `_interactable_examine_waystone()` in engine.py
- **Trigger:** First examine of waystone at (x, y)
- **Gate:** `(x, y) not in local_map.interacted_waystones` (once per waystone)
- **Category:** Biome-weighted — `_WAYSTONE_CATEGORIES[biome_id]` maps each biome
  to 3 preferred categories, one chosen randomly:
  ```
  forest: place/body/action     heath: time/essence/cosmic
  swamp: body/time/cosmic       mountain: place/cosmic/number
  plains: action/people/time    drowned_wood: body/time/cosmic
  ash_wastes: essence/cosmic/number   town: people/action/place
  capital: people/action/cosmic  deep_mountain: cosmic/essence/number
  Default: action/cosmic/place
  ```
- **Words per trigger:** 1 (tier 1, source "waystone")
- **Message:** "Something stirs in the bone. A word surfaces — [{deep}]: {common}."
  (DEEP_TONGUE_COLOUR)
- **Also triggers:** `_maybe_show_lexicon_hint()` (first word → "Press [L]" in UI_TEXT_DIM)

**2. Stele examination** (E key on stele decor)
- **Function:** `_interactable_examine_stele()` in engine.py
- **Trigger:** First examine of stele at (x, y), AND text_id not in `taught_texts`
- **Gate:** `(x, y) not in local_map.examined_steles` AND `text_id not in lang.taught_texts`
- **Category:** From text's `teach_words.categories` list (first entry)
- **Words per trigger:** 1 (from text's teach_words block)
- **Message:** "Something stirs in the bone. A word surfaces — [{deep}]: {common}."
  (DEEP_TONGUE_COLOUR)

**3. Bell examination** (E key on cracked_bell / dead_bell decor)
- **Function:** `_interactable_examine_bell()` / `_interactable_examine_dead_bell()` in engine.py
- **Trigger:** First examine of bell at (x, y), text has teach_words, ins_id not in taught_texts
- **Gate:** `(x, y) not in local_map.examined_bells` AND `ins_id not in lang.taught_texts`
- **Category:** From bell inscription's `teach_words.categories` list
- **Words per trigger:** 1
- **Message:** "Something stirs. A word surfaces — [{deep}]: {common}." (DEEP_TONGUE_COLOUR)

**4. Corruption threshold** (corruption reaches 0.70)
- **Function:** `_learn_deep_tongue_from_corruption()` in resonance_system.py
- **Trigger:** Corruption crosses 0.70 (one-time threshold, never re-fires)
- **Gate:** Threshold system fires once per threshold per game
- **Category:** "ominous" only, tier 3. Bypasses `get_learnable_words()` tier gate —
  directly selects from ominous tier-3 pool with `source == "corruption"`.
- **Words per trigger:** 2-3 (random)
- **Message 1:** "Something presses through the bone. A shape that was not invited." (MSG_ANCIENT)
- **Message 2+:** "  [{deep}]: {common}." per word (MSG_ANCIENT) — intrusion tone
- **Does NOT trigger:** lexicon hint (that fires on first word learned, much earlier)

### Texts with teach_words Blocks (15 total)
- **Lab:** lab_inscription_entry (place/essence), lab_label_sarcophagus (cosmic/body),
  lab_stele_inscription (place/cosmic/essence)
- **Bells:** bell_inscription_a through bell_inscription_f (essence/cosmic/number combos)
- **Buildings:** text_guard_log (place/cosmic), text_residential_letter (place/cosmic),
  text_scholar_notes (place/legacy), text_shrine_inscription (essence/cosmic),
  text_storehouse_manifest (place/time)
- **Waystone:** waystone_prayer_a (place/cosmic)
All teach exactly 1 word, tier 1, on first read.

### Rendering Pipeline (`engine/text_reader.py`)
Per-word font switching in text reader:
1. Token split by whitespace, punctuation stripped.
2. Token in `all_words` dict? → Deep tongue word.
   - `language.knows(token)` → True: render italic translation (font_deep, DEEP_TONGUE_COLOUR).
   - `language.knows(token)` → False: render phoneme glyphs (glyph_gen, DEEP_TONGUE_COLOUR).
3. Token not in lexicon → render as normal text.
`DEEP_TONGUE_COLOUR = (162, 120, 218)` — legible purple for all deep tongue rendering.

**Lexicon screen (L):** known words only. Left panel: inline glyphs at GLYPH_SIZE_INLINE.
Right panel: full phoneme detail at GLYPH_SIZE_DETAIL, ziggurat border, auto-scales to fit.
Categories collapsible. No unknowns shown — discovery is opaque.
Hint row shows "N words known. The tongue runs deeper." (exact count, fixed flavour).

### Lexicon Screen (`rendering/lexicon_screen.py`)
- **Key:** L (toggle). Panel style: "polis_sanctuary".
- **Layout:** Two-panel (30/70 split). Left: categories with word counts (collapsible).
  Right: word detail with glyph rendering, translation, concept, category label.
- **Only shows learned words.** Unlearned words invisible in lexicon.
- **Rendering pipeline:** Left panel renders inline glyphs via `glyph_gen.draw_word()` at
  `GLYPH_SIZE_INLINE`. Right panel renders full phoneme sequence at `GLYPH_SIZE_DETAIL`
  (auto-scales 48→40→32→24 to fit panel width) inside a ziggurat-bordered inset box.
- **Interaction:** read-only. Arrow keys navigate, Enter collapses/expands category headers.
  PgUp/PgDn for fast scroll. L/ESC closes.
- **Categories displayed:** cosmic, body, time, place, people, action, essence, number,
  ominous, legacy. Each with descriptive subtitle. Category detail shows description + count.
- **Per-word detail:** deep form (bold), translation (italic quotes), concept (wrapped, centred),
  category label, learning turn number.

### Debug Tooling
Console commands (LANGUAGE group):
- `teach_word <word_id>` — teach a specific word (bypasses tier gates). Reports deep/common forms.
- `list_known` — print all known words grouped by category with tier info.
- `show_lexicon` — print full 318-word list with [✓]/[ ] known/unknown markers.
Other testing paths: F7 (set corruption to 0.70 for threshold), examine waystones/steles,
`grant_perk carrion_eye` for enhanced examine.

### Known Gaps / Deferred
- **Tier 3 unlock (`vukhar`):** learn_sources ["bellwright"] — requires Bellwright NPC interaction
  (NPC not yet designed). Explicit `learn_word("vukhar", "bellwright")` call needed.
- **No debug commands** for granting/revoking words or forcing learning events.
- **Recovered spans** (Witnessing perk line) — component fields exist, recovery logic is stub.
- **Deep tongue bitmap font** — Tier 4. Currently uses Junicode italic.
- **Deep tongue expansion** is content work — no code changes needed to add words.

**Lab inscription:** "Vrath sketh urath. Grath zhar keth."
= "The threshold remembers the dead. Ware ye the song of the stone."

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
LANGUAGE:   teach_word <word_id>, list_known, show_lexicon
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
- **No stealth system.** Concealment via terrain only (tall grass). No stealth stat, no stealth mode.
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
✓ Perk system (K screen, purchase, hook architecture, 13 live perks across 6 affinities)
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
✓ Look mode (surfaces terrain + decor + blood + entities, ENTER dispatches interactable handlers for stele/waystone)

✓ Survival system (data/survival.json, staged consequences, move penalty, hp drain, eat/drink)
✓ Harvestable plants (G key harvest, 5 plants, depleted tile variants, data-driven)
✓ Found texts on surface (16 texts, all building text_id refs resolve, TownData.item_spawns)
✓ Crafting foundation (engine/crafting.py pure functions, data/recipes/, C key craft_screen)
✓ Campfire (campfire_unlit/campfire_lit tiles, light/extinguish interactable, warmth system)
✓ Butchery system (corpse-as-decor, corpse_data/corpse_decay on LocalMap, decay tick, _interactable_butcher, 9 creature butcher_yield blocks, 18 butchery item JSONs)
✓ Fuel keyword system (burning→fuel rename, provides_burning field on torch/lantern, ambient_sources in can_craft/attempt_craft, craft_screen builds ambient sources from equipped light + nearby campfire_lit)
✓ Tiered flame particles (flame_low/flame_med/flame_high/smoke_incense in particles.py; engine emitter block handles all 4 + embers by fx type; decor_candle→flame_low, campfire_lit→flame_med)
✓ Waystone uniqueness guard (main.py and region_gen.py both check for existing plinth before placing)
✓ E key interaction cursor (rebind from Shift+G; E blocked in screen modes to avoid conflicts)
✓ Tall grass concealment free-hit (move_cost 1.5→2.5; position snapshot before ai_system.process; free _player_attack when creature enters concealment tile adjacent to player with weapon equipped)
✓ Structured butchery log (line 1: creature name + tool; one line per yield type; "nothing useful" if empty)
✓ Item decay_timer field (entities/item.py, int|None, default None — ready for future perishables)
✓ Inventory grouping by item_id (_flat_list groups within category; label "×N" for groups; renderer shows "(×N)" suffix)
✓ Essence scope reduction (essence/essence_strength removed from 33 non-combat item JSONs; weapons/armor/shields/talismans retain them)
✓ 10 new alchemy keywords (malleable, vessel, heatproof, alchemical, volatile, solvent, fixative, caustic, inert, aromatic) in keywords.json; existing items updated
✓ Clay deposit terrain (clay_deposit/clay_deposit_depleted in tiles.json+terrain.json+sprite_map.json; _scatter_clay B5 step in region_gen.py; clay_lump item)
✓ Clay pot recipe (result_item support in crafting.py+craft_screen.py; requires_ambient field checks environment without consuming; clay pot item with vessel+heatproof keywords)
✓ Passive processing queue (local_map.processing_queue; ticked in _advance_turn; data/processing_messages.json; craft screen dispatches passive_processing recipes to queue)
✓ Drying recipes (dried_coldbell, dried_pilgrims_woe, dried_murk_violet, dried_bitter_herb items + dry_* recipes; all passive 30-40 turns)
✓ Coldbell extract (recipe: resonant≥2 + vessel ambient + burning≥2; item: reduce_resonance_exposure 0.3; _build_ambient_sources extended to scan inventory keywords for reusable tool detection)
✓ Hungering oil (recipe: viscous + caustic + vessel + burning; apply_to_weapon handler; temporary_essence on Item entity; combat merges coating into essences list and decrements hits; expiry callout; save_manager serialises temporary_essence)
✓ Cooked meat (recipe: vital + burning ambient; passive 8 turns; 220 nutrition; cook_meat recipe uses cooking source from processing_messages.json)
✓ Containers (barrel/crate/sack/coffer, open/browse/take, decor-based state, 16 buildings with containers)
✓ Loot tables (11 loot pools, weighted sampling without replacement, roll_pools combiner)
✓ Satchel equipment slot (weight_reductions per category, 3 satchel items)
□ Alchemy foundation (distillation chain, herblore → essence)
✓ Status screen (H key) — replaced health screen concept. Bearing descriptor, HP bar, active conditions.
✓ Lexicon screen (L key) — glyph pipeline, category grouping, collapsible, read-only.
□ Resonance system full (bells decay, remaining 4 thresholds)
✓ Concealment (tall grass free-hit, move_cost 2.5 — stealth system cancelled, concealment via terrain only)
✓ Vine network system (spreading decor creature, eyestalk attack, spore vent gas, cutting interaction, resonance-triggered spawn)
✓ Weapon movesets (Q/R keys, 12 actions across 6 weapons, cooldowns, creature_knowledge, HUD)
□ Reality bubble full (stair transfer, density management)
□ More perks (all affinity categories)
  PERK — Resonant Wayfarer (The Witnessing affinity)
    Effect: Learn one additional word from each waystone interaction.
    Secondary effect: On second activation of the same waystone, the stone
      emits a cracked bell pulse (visual + sound callout). Player receives
      a warning prompt before the second activation fires:
      "The stone has already given. Draw from it again?"
      [Y] proceed — learn word, stone emits cracked pulse, resonance exposure +0.05
      [N] cancel
    Implementation notes:
      - Track per-waystone activation count in chunk.interacted_waystones
        (change from set to dict mapping (lx,ly) -> int)
      - Cracked bell pulse: existing pulse_dim visual_fx at elevated intensity
      - Warning prompt: inline yes/no in message log, not a new screen
    Status: DEFERRED — implement after perk content expansion pass
✓ Deep tongue learning through gameplay (318 words v2, glyph system, waystone/stele/corruption/text learning, L key lexicon screen, ominous/tier 3 restrictions)
✓ Text item map (data/texts/text_item_map.json, authoritative text_id→item_id mapping, wired into special tile processing)
✓ Probabilistic special tiles (weighted spawn tables + legend_weights for terrain variation)
✓ Decor layer expansion (waystone plinth, stele, street lamps, plants converted from terrain to decor; resonance_emit/visual_fx wired for decor)
✓ Dead bell interaction (examine_dead_bell: inscription + word teaching, no resonance pulse)
✓ Lexicon hint ("Press [L] to open the Lexicon." fires once on first word learned, tracked in language component)
✓ Starting waystone road-adjacent placement (nearest to road path within 8 tiles of chunk centre)
✓ Street lamp placement validation (must be walkable exterior tile, not in building footprint, not on existing decor)
✓ Resonance accumulation rate reduction (bell exam +0.02, passive -50%, corruption conversion -40%)
✓ Cross-chunk pursuit fix (re-extraction on back-and-forth transitions, arrival at _last_chunk_entry not mirrored position)
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
*Last updated: Decor layer expansion + text_item_map + pursuit fixes + resonance tuning session.*

### Working

**Deep Tongue Learning System:**
- `data/deep_tongue.json` v2 format: 318 words across 9 categories (cosmic, body, time, place, people, action, essence, number, ominous + legacy).
- Each word: id, deep, common, concept, category, tier, glyph_seed, learn_sources, notes.
- `data/deep_tongue_phonemes.json`: 268 unique phonemes extracted from 318 words, each with fixed glyph_seed.
- `rendering/glyph_gen.py`: procedural glyph generation from seed. GlyphDef dataclass. Grammar: primary axis, secondary arms, tertiary ticks, optional frame. Styles: standard/dense/open/ancient.
- `engine/language_system.py`: pure functions — `learn_word()`, `learn_from_category()`, `learn_from_text()`. Never duplicates, fallback to any unknown Tier 1 word.
- Learning events:
  - Waystone interaction (E key): `_interactable_examine_waystone()`. Biome-appropriate category. Once per waystone via `local_map.interacted_waystones` set.
  - Stele interaction (E key): `_interactable_examine_stele()`. Teaches from text's `teach_words` block. Once per stele via `local_map.examined_steles` set.
  - Corruption threshold 0.70: learns a body word from corruption source.
  - Reading texts with `teach_words` block: teaches count words from listed categories.
- `rendering/lexicon_screen.py`: L key. Two-panel polis_sanctuary style. Left: categories with word counts, collapsible. Right: glyph rendering + translation + concept. Only shows learned words.
- Text reader per-word rendering: deep tongue words in found texts render as phoneme glyphs (unlearned) or italic translation (learned). Alphabet render mode for debug note.
- Stele tile: walkable=false, transparent=true, visual_fx=pulse_dim, resonance_emit=0.05, interactable=examine_stele.
- Starting lab: stele at (2,2) in sarcophagus chamber with lab_inscription_entry text. Alphabet debug note at (19,2) in research area.
- 3 texts with teach_words: lab_inscription_entry (2 words: place/essence), lab_label_sarcophagus (1 word: cosmic/body), waystone_prayer_a (1 word: place/cosmic).
- `taught_texts: set[str]` on Language component — tracks text_ids that have already taught words. Prevents re-teaching on re-read.
- `DEEP_TONGUE_COLOUR = (162, 120, 218)` in palette.py — legible purple for all deep tongue rendering. Replaces DEEP_PURPLE for glyph/translation display.
- Text reader `panel_style` parameter — defaults to "weathered_temple", stele handler passes "ziggurat".
- Save/load: Language component serialised (known_deep_words, translation_events, taught_texts). interacted_waystones/examined_steles serialised with chunk via pickle.

**Butchery System:**
- Corpses live in the decor layer (`"corpse"` decor id) — same pipeline as blood_pool, campfire.
- `local_map.corpse_data: dict[(x,y) → creature_id]` — creature identity per tile.
- `local_map.corpse_decay: dict[(x,y) → int]` — decay counter, ticked in `_advance_turn`.
  On expiry: `clear_decor`, entries removed from both dicts.
- `ephemeral: true` in creature JSON → no corpse placed on death (bog_wraith).
- `butcher_yield` block in creature JSON: `decay_turns`, `tiers[]` each with `min_cutting_tier` and `yields[]`.
- `_interactable_butcher(x, y)`: reads `corpse_data`, finds highest qualifying tier by cutting tool level,
  rolls yields, adds to inventory, clears corpse. Turn cost: `max(1, 5 - (cutting_tier - min_tier_req))`.
- Shift+G interaction cursor auto-detects corpses (decor entry has `"interactable": "butcher"`).
- 9 creature butcher_yield blocks: plague_crow, heath_stalker, highland_bandit, grave_thing,
  barrow_wight, hollow_revenant, drowned_revenant, briar_lurker, stone_lurker.
- 18 butchery items in `data/items/butchery/`: meats (raw_meat_common, crow_meat, stalker_meat),
  animal materials (animal_bone, animal_sinew, crude_viscera), special parts (crow_bile,
  crow_flight_membrane, stalker_musk_gland), undead materials (grave_dust, compressed_marrow,
  resonant_bone_fragment, wight_essence_residue, revenant_husk), plant creature (fibrous_thorn_mass,
  briar_sap), stone creature (stone_carapace_fragment, inner_stone_core).
- Keywords on items use existing keyword system. `cutting` keyword on weapon enables butchery.
- `_load_dir("items")` recursively loads `data/items/butchery/` automatically — no code change needed.

**Survival System:**
- `data/survival.json` is single source of truth for all survival tuning.
- Hunger/thirst: 4 stages each (peckish/hungry/starving/collapsing, dry/thirsty/parched/desiccating).
  Data-driven messages, move_penalty, hp_drain per hp_drain_interval turns.
- Biome modifiers applied to tick rate each turn. Underground uses surface chunk biome.
- `W` key: prefers filling empty_water_skin over drinking directly from shallow_water.
  If empty_water_skin in inventory + drinkable terrain: fills flask ("Thou fillest the skin from the shallows.").
  If no flask: drinks directly as before. Underground: message, no hydration.
- Rain collection: waiting (space/./z) in light_rain (8 turns) or heavy_rain (4 turns) while
  holding empty_water_skin on surface → fills to water_skin. Resets on movement or weather change.
  State: `engine.rain_collection_progress: int`.
- water_skin → empty_water_skin on consume (drink handler checks `empty_form` field on item JSON).
- HP drain at stage 4: posts "Starvation takes from you." or "The thirst takes from you." (MSG_DANGER).
  Fires every hp_drain_interval (10) turns. Thirst drains 2 HP, hunger drains 1 HP.
- Move penalty at stage 3: +0.5 move_debt per step. Stage 4: +1.0. Wired in `_on_player_step()`.
- Status screen (H key): 6 hunger/thirst conditions (Hunger, Starving, Collapsing, Thirst,
  Parched, Desiccating) with archaic descriptions and colour-coded severity.

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

**Perk System:** 9-event hook architecture. 13 live perks across 6 affinities.
Original 6: hardened_step, carrion_eye, marrow_drink, attuned, the_indifference, lithic_seep.
New 7: bone_reader (max butchery yield), road_knowledge (road sprint bonus),
  resonant_wayfarer (extra waystone word + second activation pulse),
  deep_harvest (30% non-deplete harvest), growth_sense (highlight plants on chunk entry),
  resonance_sink (50% faster exposure decay), corruption_channel (+1/+2 damage at corruption thresholds).
Also: ear_pressed_to_stone, second_tongue, the_opened_page (design stubs, not wired).

**Screens:** Inventory (I), Perk (K), Status (H) — HP bar, bearing descriptor, active conditions (hunger, thirst, chilled, sickened, corruption), Lexicon (L) — known words grouped by category, collapsible, full glyph pipeline (inline + detail panel with phoneme sequences), Death, Look mode (;/x), Craft (C), Debug (F1-F12 + console).

**Health/Status Screen (H key):**
- `engine/health_screen.py`, class `HealthScreen`. Panel style: weathered_temple.
- Section 1 (STATUS): bearing label (Unmarked→Undone based on HP fraction), HP bar
  (full width, green/yellow/red transitions), AV display. Exact HP shown only with
  `true_sight` or DEBUG_MODE.
- Section 2 (ACTIVE CONDITIONS): each active status effect shown with name + wrapped
  archaic description text. Currently tracked conditions:
  - Hunger (≥0.5 or ≥0.85 critical) — from needs component
  - Thirst (≥0.5 or ≥0.85 critical) — from needs component
  - Chilled — from `player.chilled_turns > 0`
  - Sickened — from `player._sickness_turns > 0` (plague crow)
  - Corruption — from `engine.corruption >= 0.15`
- When no conditions active: displays "Unmarked." (archaic clean-state label).
- Condition descriptions in `_CONDITION_DESCS` dict — in-world voice, not mechanical.
- Footer: "H / ESC close". Input: H/ESC/K closes screen.

**Lexicon Screen (L key):**
- `rendering/lexicon_screen.py`, class `LexiconScreen`. Panel style: polis_sanctuary.
- Two-panel layout: left (30%) = category list with word counts, right (70%) = word detail.
- **Only shows learned words** — unlearned words invisible. Category headers show "v/> Label (N)".
  Enter collapses/expands categories.
- Left panel: inline glyph rendering via `glyph_gen.draw_word()` + "deep = common" text per word.
  Highlight rect on selected row. Scroll support with PgUp/PgDn.
- Right panel (word selected): ziggurat-bordered glyph inset box with phoneme sequence
  rendered at GLYPH_SIZE_DETAIL (auto-scales down to fit). Deep word in bold, translation
  in italic quotes, concept description wrapped and centred, category label, "Learned turn N".
- Right panel (category selected): category name + description + word count.
- Uses full glyph rendering pipeline: `_draw_glyph_word`, `_glyph_word_pw`, `_get_phonemes`
  from `rendering/glyph_gen.py`.
- 10 categories displayed: cosmic, body, time, place, people, action, essence, number,
  ominous, legacy. Each with descriptive subtitle.
- Footer: "^ v navigate   Enter expand   L/ESC close".

**Gathering & Crafting:**
- `G` key: harvest at player tile (plants) → gather gatherable terrain → fall through to pickup.
- `E`: 3×3+centre interaction cursor — harvestable, gatherable, interactable, items.
- Gatherable terrain: dead_wood (wood_bundle, 100%), flint_rock (flint_shard, 50%), clay_deposit (clay_lump, 80%).
- `C` key: craft_screen — recipes grouped by category, collapsible. Shows per-component "(have: N)" counts.
  Locked recipes shown dim with locked_hint. Ambiguous components trigger selection prompt.

**Crafting System (`engine/crafting.py`):**
- `can_craft(recipe, inv, keyword_data, ambient_sources) → (bool, missing_list)`
  Checks components (keyword+tier), requires_ambient (environmental tags), requires_single_item (multi-tag).
  Greedy lowest-tier-first claiming. Ambient sources never consumed.
- `attempt_craft(recipe, inv, ..., chosen_items)` — consumes ingredients, respects consumed_on_use.
- `_build_ambient_sources(engine)` in craft_screen: scans equipped light (provides_burning),
  nearby campfire_lit decor (3 tiles → burning tier 2), inventory reusable tools (keyword ambient).

**Recipe List (17 active, data/recipes/):**
```
CAMPFIRE/COOKING:
campfire          campfire    fuel≥1×2 + cutting≥1×1           → campfire_unlit (places_in_world)
clay_pot          campfire    malleable≥1×2 + [burning≥2]      → clay_pot (passive 12 turns)
cook_meat         cooking     vital≥1×1 + [burning≥2]          → cooked_meat (passive 8 turns)

WILDCRAFTING:
dry_bitter_herb   wildcraft   [bitter≥1+edible≥1]×1 + [burn≥1] → dried_bitter_herb (passive 20)
dry_resonant_herb wildcraft   [resonant≥1+edible≥1]×1 +[burn≥1]→ dried_resonant_herb (passive 20)
dry_soporific_herb wildcraft  [soporific≥1+edible≥1]×1+[burn≥1]→ dried_soporific_herb (passive 20)
dry_aromatic_herb wildcraft   [aromatic≥1+edible≥1]×1+[burn≥1] → dried_aromatic_herb (passive 20)
musk_pellet       wildcraft   [viscous≥1+purgative≥1]×1+[burn≥1]→ musk_pellet (passive 10)

ALCHEMY:
resonant_tincture alchemy     [resonant≥2]×1+solvent≥1+[burn≥1,heat≥1]→ resonant_tincture (passive 40)
hungering_oil     alchemy     viscous≥1+caustic≥1+[burn≥2,vessel≥1]→ hungering_oil (immediate)
bile_coating      alchemy     caustic≥1+viscous≥1+[burn≥1,vessel≥1]→ bile_coating (immediate)
bone_dust_draught alchemy     resonant≥1+bony≥1+[burn≥1,vessel≥1]→ bone_dust_draught (passive 25)
marrow_seal       alchemy     bony≥2+waxy≥1+[burn≥2]→ marrow_seal (passive 15)
wight_concentrate alchemy     [resonant≥3]×1+[burn≥2,vessel≥1]→ wight_concentrate (passive 40)
briar_binding_oil alchemy     [viscous≥2+binding≥2]×1+[burn≥1,vessel≥1]→ briar_binding_oil (immediate)
resonant_bone_tincture alchemy resonant≥2+bony≥2+[burn≥2,vessel≥1]→ resonant_bone_tincture (passive 35)
stalker_unguent   alchemy     vital≥1+fibrous≥1+binding≥1+[burn≥2,vessel≥1]→ stalker_unguent (passive 20)
```
[brackets] = requires_ambient. [tag+tag]×1 = requires_single_item.

**Keyword System (26 keywords in data/keywords.json):**
Physical: cutting, fuel, edible, drinkable, vital, fibrous, bony, waxy, malleable.
Essence-adjacent: resonant, corrosive, binding, viscous, caustic.
Alchemical: alchemical, volatile, solvent, fixative, inert, aromatic, soporific, purgative, bitter.
Equipment: vessel, heatproof. Special: burning (ambient-only, not in keywords.json).
Each keyword has: display_name, color (palette alias), description. Tier specified per-recipe component.

**Passive Processing (`local_map.processing_layer`):**
- Recipes with `passive_processing: true` enqueue: {item_id, turns_remaining, source, decor_id, on_fire}.
- Ticked in `_advance_turn()`. On completion: result item → inventory, decor cleared, message logged.
- Sources: drying, cooking, steeping, rendering. Messages in `data/processing_messages.json`.

**Temporary Essence Coating (hungering_oil):**
- `Item.temporary_essence`: `[{essence, strength, hits_remaining}]`
- `_use_apply_to_weapon()` merges charges onto equipped weapon.
- In combat: coating merged into essences list, hits decremented on connecting blow, expiry callout.
- Serialised in inventory item save dict.

**Alchemy Items (8 new butchery-sourced):**
- bile_coating — apply_to_weapon, Dissolution 0.4 ×6 hits (crow bile source)
- bone_dust_draught — reduce_resonance_exposure 0.25 (grave dust source)
- marrow_seal — apply_to_armor, +1 AV ×20 hits (compressed marrow source)
- wight_concentrate — true_sight 20 turns + resonance +0.4 + corruption +0.05 (wight residue)
- briar_binding_oil — apply_to_weapon, Binding 0.5 ×8 hits (briar sap source)
- musk_pellet — throw, 3-tile disruption zone ×6 turns (musk gland source)
- resonant_bone_tincture — learn 1 deep tongue word on consume (resonant bone source)
- stalker_unguent — speed +0.2 for 15 turns (stalker meat + sinew source)

**New item handlers** in item_system.py:
- `_use_learn_deep_word` — teaches random tier-1 word from waystone category pool
- `_use_apply_to_armor` — adds temp AV bonus to equipped torso armour
- `_use_consume_wight_concentrate` — warning prompt, then true_sight + resonance + corruption
- `_use_apply_stalker_unguent` — player_speed_bonus for N turns
- `_use_throw_musk_pellet` — target tile selection, creates disruption zone (stub — pending full wiring)

**Alchemy Status:** Preparation-tier expanded with butchery-sourced recipes. No distillation chain,
no alembic, no moonwater basin. Equipment tier 1 only (campfire + clay_pot).
Designed tiers 2-3 (alembic, resonance bowl, bone crucible) are canon but not implemented.

**Container System:**
- 4 container decor types in `data/decoratives.json`:
  - `barrel` (ascii "o") — "A barrel. Staved wood, iron-banded."
  - `crate` (ascii "[") — "A wooden crate."
  - `sack` (ascii "(") — "A sack, tied at the neck."
  - `coffer` (ascii "{") — "A coffer. Hinged and clasped."
  All have: `container: true`, `interactable: "container"`, `blocks_movement: true`.
- Container state: `local_map.container_state: dict[(lx,ly) → {state, items, decor_id}]`.
  States: `closed` → `open` → `looted`. Visual does not change — state tracked only.
- Container API in `generation/floor_object_utils.py`:
  - `place_container(local_map, lx, ly, decor_id, item_list)` — creates closed container
    with serialised items, places decor tile.
  - `open_container(local_map, lx, ly)` → bool — transitions closed → open.
  - `take_from_container(local_map, lx, ly, item)` — removes item by item_id match;
    sets state to looted when last item taken.
  - `get_container_items(local_map, lx, ly, item_factory)` → list[Item] — reconstructs
    Item objects from serialised `{item_id, text_id}` dicts.
- Runtime interaction via `_interactable_container()` in engine.py:
  - One ENTER press opens (if closed) AND shows browse selection prompt.
  - Archaic opening messages per container type (4 unique per type).
  - Archaic looted messages per container type (4 unique per type).
  - Selection prompt uses `"source": "container"` key; `_handle_container_take()`
    in interaction_cursor resolves take/take-all.
  - Looted containers return False (no turn spent).
- Serialisation: `container_state` pickled with LocalMap via chunk cache.
  Items stored as `{item_id, text_id}` dicts; recreated via item_factory on browse.
- 17 building layouts + starting lab have container special_tiles:
  - Storage: cellar_a, storehouse_a, root_cellar_a, warehouse_a
  - Residential: house_small_a, house_small_b, house_large_a, house_damaged_a, tenement_a
  - Commercial: market_stall_a, market_stall_b
  - Religious: bell_warden_post_a, collapsed_shrine_a
  - Ruins: collapsed_house_a, three_wall_remnant_a
  - Wilderness: waymarker_shelter_a
  - Layout: starting_lab.json (1 crate, storage_tools pool)
- **Deferred:** lock/stuck mechanics (Tier 3), container weight (Tier 3),
  two-panel transfer UI (Tier 4).

**Loot Pool System:**
- `data/loot_pools/*.json` — 11 pools, loaded by data_loader as `self.loot_pools`:
  - `commoner_kitchen` — [2,4] rolls: dried_provisions, water_skin, wood_bundle, etc.
  - `commoner_bedroom` — [1,2] rolls: pilgrims_woe_petals, tallow_torch, etc.
  - `storage_general` — [3,5] rolls: wood_bundle, flint_shard, clay_lump, etc.
  - `storage_tools` — [1,3] rolls: flint_shard, clay_pot, tallow_torch, crude_blade.
  - `shrine_offering` — [1,3] rolls: coldbell_cutting (high weight), moist_pebble, etc.
  - `shrine_equipment` — [1,2] rolls: tallow_torch, oil_lantern, leather_satchel.
  - `ruins_scatter` — [1,2] rolls: animal_bone, grave_dust, crow_jerky, etc.
  - `wilderness_cache` — [2,3] rolls: wood_bundle, flint_shard, bitter_herb, etc.
  - `alchemist_shop` — [3,5] rolls: dried herbs, coldbell_cutting, clay_pot, etc.
  - `alchemist_reagents` — [2,4] rolls: crow_bile, sulphur_cap_fragment, etc.
  - `noble_generic` — [2,3] rolls: oil_lantern, leather_satchel, dried_provisions, etc.
- Pool format: `{id, roll_count: [min, max], items: [{item_id, weight}]}`.
  Weighted sampling without replacement — each item drawn at most once per roll.
- `engine/loot_roller.py`: `roll_pool(pool_def, item_factory, rng)` → list[Item],
  `roll_pools(pool_ids, all_pools, item_factory, rng)` → list[Item] (combines multiple).
- Containers reference pools by ID in building JSON `special_tiles`:
  `{"type": "container", "decor_id": "barrel", "loot_pools": ["storage_general"]}`.
- Engine processes container specs at chunk load via `roll_pools()` → `place_container()`.

**Satchel Equipment Slot:**
- `"satchel"` slot in `components/equipment.py` SLOTS list.
- 3 satchel items (found, not starting equipment — player must find one):
  - `leather_satchel` — 10% weight reduction on all items (`"all"` key).
  - `herbalist_pouch` — 30% reduction on Consumables and Preparations categories.
  - `component_satchel` — 35% reduction on Components, 20% on Tools.
- Item JSON `weight_reductions` field: dict mapping category names → float multipliers.
  `"all"` key applies a flat reduction across all categories.
- Weight reductions applied at read time in `engine/inventory_screen.py` via `_effective_weight()`.
  Inventory header shows effective carry weight. Per-item weight display shows reduced value.

**Weight System:**
- Every item has a `weight` field (float) in its JSON definition. Default 0.0 if absent.
- Total carry weight summed in inventory_screen.py and displayed in header.
- Satchel equipment applies category-based weight reductions (see above).
- No encumbrance penalty currently implemented — weight is tracked for future use.
  Encumbrance effects (move_cost penalty, stamina drain) are planned Tier 3.

**Placement Cursor (GameMode.PLACEMENT_CURSOR):**
- Activated after crafting a `places_in_world` recipe. Stores tile_id + recipe in engine.
- Same 3×3 grid as interaction cursor. Arrow/vi-keys navigate, clamped.
- Valid tiles highlighted DISCHARGE_FLASH (yellow). Invalid tiles highlighted FRESH_WOUND (red).
- ENTER on player's own tile: "You cannot place it at your own feet." — no turn, cursor stays.
- ENTER on valid: place tile, spend turn, return to LOCAL. Emits OLD_GOLD burst (8-12 world-space circles) + expanding ring (0.75 tile radius, 0.6s).
- ENTER on invalid: "You cannot place it there." — no turn, cursor stays.
- ESC: return all ingredients to inventory, "You decide against it.", return to LOCAL.
- `placement_message` + `result_message` fields in recipe JSON drive log text.

**Campfire:**
- campfire_unlit and campfire_lit live in the DECOR layer (data/decoratives.json), not terrain.
  Entries have: blocks_movement:true, blocks_sight:false, interactable, warmth_radius (lit only), visual_fx (lit only).
- Placement cursor writes campfire_unlit via place_decor() — terrain beneath remains unchanged.
- Movement check reads decor.blocks_movement via engine._decor_blocks_movement(x, y).
- Interactable dispatch checks decor layer first, then terrain.
- _get_interaction_candidates checks decor for interactable field.
- Warmth: _update_warmth() scans decor entries for warmth_radius in addition to terrain tiles.
- Ember emitter: scans decor entries for visual_fx=="embers" in addition to terrain.
- Light/extinguish handlers use place_decor() to swap campfire_unlit ↔ campfire_lit.
- Campfire entries remain in tiles.json and terrain.json as ASCII/data fallbacks — NOT written to chunk.tiles.
- Campfire sprites are placeholder — need F12 visual audit.
- dead_wood uses authored sprite (terrain col 22 row 6). flint_rock uses authored sprite (terrain col 23 row 4).

**Terrain Light Sources:**
- Data-driven: any terrain entry with `light_emit > 0` participates automatically.
- Fields: light_emit (radius), light_mode ("steady"|"pulse"), light_color [R,G,B].
- Pulse fields: light_pulse_min, light_pulse_max, light_pulse_rate (Hz). Smooth sine, per-tile phase offset.
- street_lamp_working: light_emit:5, steady, amber [226,181,112].
- street_lamp_sputtering: light_emit:4, pulse min:2 max:4 rate:0.4Hz, warm [210,150,80].
- street_lamp_dead: no light fields.
- Light pass in _update_light_map() uses self.data.terrain (was using wrong self.registry._data).
- Same linear falloff as LightSource.apply_to_light_map.

**Bog Wraith:**
- sight_radius and ability_range both set to 8 in bog_wraith.json.
- _ability_bog_wraith() reads ability_range from data.entities — no hardcoded radius.
- _update_wraith_aura() reads same ability_range — awareness and FOV drain activate together.

**varied_grass:**
- region_gen.py was directly writing b"varied_grass" to tile array, bypassing set_tile().
  Fixed: now calls set_tile() which resolves to actual variant immediately at generation time.
- Plants (flowers, mushrooms) now placed as decor via set_tile → PLANT_DECOR_IDS check.
  Grass terrain remains underneath. Harvest system checks decor layer for harvestable property.

**Text Item Map:**
- `data/texts/text_item_map.json`: authoritative mapping from text_id to document item_id.
  Loaded as `self.text_item_map` in data_loader.py.
- Special tile processing (starting_location.py + engine.py item spawn sites) overrides
  item_id based on text_id lookup. Unknown text_ids default to "letter" with a log warning.
- 90+ entries covering all lab texts, building texts, bell inscriptions, waystone inscriptions,
  world texts (graffiti, sermons, official notices, letters, labels).

**Decor Layer Expansion:**
- Waystone plinth, stele, street lamps, and plants converted from terrain to decor layer.
- Decor `resonance_emit` wired into: resonance_system.py scan, engine.py pulse timers,
  engine.py sparkle emitter, look_mode.py examine popup, debug.py scan_resonance.
- Decor `visual_fx` wired into: renderer.py brightness effects (terrain visual_fx checked first,
  then decor), engine.py particle emission (already wired).
- Decor `harvestable` wired into: engine.py _try_harvest (checks decor for harvest_item/depleted_id),
  engine.py _get_interaction_candidates.
- `_DECOR_TERRAIN_IDS` set in layout_stamper.py and town_gen.py: tiles in this set are
  automatically redirected to place_decor() during layout stamping.
- `PLANT_DECOR_IDS` set in rendering/decor.py: tiles resolved from varied_grass that are
  in this set are placed as decor + grass terrain underneath in local_map.set_tile().
- Street lamp placement validates: walkable exterior tile, not inside building footprint,
  no existing decor at position. `_valid_lamp_pos()` in town_gen.py.

**Dead Bell Interaction:**
- `bell_dead` decor entry has `interactable: "examine_dead_bell"`.
- Handler: inscription + word teaching (same as examine_bell), no resonance pulse.
- Bell towers with spent/destroyed bell_state now place bell_dead decor for interaction.

**Probabilistic Special Tiles:**
- `"type": "weighted"` in special_tiles: roll from spawn_table with weighted selection.
  `"type": "empty"` entries mean nothing placed. Supported in starting_location.py and town_gen.py.
- `legend_weights` in layout JSON: per-symbol weight table for terrain tile variation.
  Checked in layout_stamper.py stamp_layout/stamp_layout_interior and starting_location.py _stamp.

**Cross-Chunk Pursuit Fixes:**
- `_check_entity_chunk_crossings` now uses `_last_chunk_entry` for arrival position
  (was using mirrored position, placing pursuers at wrong edge).
- Extraction in `_transition_chunk` no longer skips entities with `_arrival_cooldown`.
  This prevents losing pursuit on back-and-forth transitions.
- `[ARRIVE-POS]` debug print added to both arrival paths.

**Resonance Tuning:**
- Bell examination: +0.05 → +0.02 per examine.
- Passive accumulation near resonant terrain: 0.015 → 0.0075 per turn (50% reduction).
- Cracked bell proximity: +0.12 → +0.06 per step (50% reduction).
- Corruption conversion at high exposure: 0.002 → 0.0012 per turn (40% reduction).

### Known Issues

**Content:**
- Starting lab layout is placeholder — redesign pass needed.
- Universal placeholder sprite (terrain col 1 row 7) used for 24 tiles needing
  authored sprites: all container tiles, satchel tiles, drying_herb, cooking_meat,
  clay_deposit_depleted, old_wall, 5 legacy decor tiles, cobblestone variants,
  debris_scatter, ancient_floor, ash. No ASCII fallback renders — all show ? glyph.

**Systems Not Yet Wired:**
- Deep tongue tier 4 words locked pending archaeology system (Tier 4 stretch).
- Deep tongue: `vukhar` (tier 4) unlock condition not yet wired (bellwright NPC).
- Bell state has no mechanical effect beyond creature gating.
- VisualEventQueue wired but dormant.
- Corruption 0.85 threshold_creature_shift is a stub.
- resonant_wayfarer second activation (Y/N prompt) not yet wired.
- gas_overlay visual_fx type not yet implemented (vine spore vents use it).
- dissolution_pool timed decor tick (placed by seep moveset) not yet wired.
- Moveset particle effects (hack dissolution drips, corrode acid splash) stub only.

**Fixes Applied This Session:**
- Craft screen crash (requires_single_item list format) — fixed.
- Perk screen crash (requires[] dict entries) — fixed.
- Vine interval-based eyestalk/vent spawning, improved particles + callouts.
- bone_reader perk: butchery max yield bypass wired.
- deep_harvest perk: 30% non-deplete harvest wired.
- corruption_channel perk: +1/+2 flat damage wired via ON_TURN.
- Perk screen category descriptions (8 affinities with archaic text).
- Weapon equip fix (severance_blade + revelation_lens category/type fields).
- Callout viewport clamping.
- Water flask E-key interaction (drink_source terrain interactable).
- Rain collection FILLED callout + item name in message.
- Legacy water_flask transitions to empty_water_skin on drink.
- Remaining 3 corruption thresholds (0.40, 0.55, 0.85) are stubs.
- Impairments: only dominant_hand_lost and leg_lost have mechanical effect.
- Chilled has no mechanical effect.

**UI:**
- Inventory/examine popups centre on full screen not viewport.
- Status screen: status effect icons deferred. Procedural silhouette cancelled (hit location uses damage multipliers, not per-limb HP).
- Lexicon screen: no search/filter. Unknown words invisible (shows known count, not total). Read-only.
- Procedural creature icons in examine not yet built.

**Generation:**
- Entrance structures hard to find without F5 debug teleport.
- Chunk transition terrain visually abrupt across surface boundary.
- Locus chunk special content is Tier 3.
- Dungeon void tiles not implemented (auto-tiling artifacts).
- Deprecated terrain entries (waystone_plinth, stele, street_lamp_*, plant tiles) remain in
  terrain.json for save compat — never written to chunk.tiles by current generation code.

**Cross-chunk entity pursuit — live pursuer model:**
- `can_cross_chunks: true` on all 12 creatures — all follow player across chunk boundaries and through stairs.
- `self._live_pursuers: list[tuple[Actor, wx, wy, submap_id_or_None]]`.
  - `submap_id=None` → entity in surface chunk (wx,wy).
  - `submap_id=str` → entity in a submap; (wx,wy) is the surface chunk.
- **State-gated extraction:** `_transition_chunk()` extracts any HUNTING/ALERTED creature with
  `can_cross_chunks: true` into `_live_pursuers`. No distance threshold — `pursuit_timeout`
  handles true abandonment. Entities with arrival_cooldown are re-extracted (cooldown reset).
- **Race condition guard:** `_check_entity_chunk_crossings()` skips any entity currently in
  `_live_pursuers` or `_pending_pursuer_arrivals` — prevents the normal cross system from
  touching entities under live pursuer management.
- `_descend_to_submap()`: 1-tile proactive transfer (adjacent entities merged into submap), then non-adjacent pass extracts pursuing entities into `_live_pursuers` with `last_known = stair_pos`.
- `_ascend_from_submap()`: same pattern — non-adjacent pursuing submap entities extracted into `_live_pursuers` as `(entity, wx, wy, submap_id)`, stamped with `_surface_exit_x/y/wx/wy`.
- `_tick_live_pursuers()`: surface entities use virtual player via `dx/dy * MAP_WIDTH` formula. Submap entities use `last_known` (stair tile) as phantom. Stair detection triggers `_transfer_live_pursuer_through_stair()` or `_transfer_submap_pursuer_to_surface()`. Promoted pursuers pushed to `_pending_pursuer_arrivals` with delay (default 6, override via creature JSON `chunk_cross_delay`).
- `_pending_pursuer_arrivals`: list of deferred arrivals. Each turn, delay decremented; at 0 `_live_arrive()` places entity in border-constrained strip (max 3 tiles inward from crossing edge). Serialised in save.
- `_live_arrive()`: border-anchored placement — searches within a 3-tile-deep strip along the crossing edge before falling back to full shell search. Cleans entity from `_live_pursuers` on materialisation.
- `_check_entity_chunk_crossings()`: entities arriving in player's chunk placed at `_last_chunk_entry`, not mirrored position. Fix-2: before overwriting `_last_known_px/py` with boundary edge in third-chunk placement, checks if current value points at a stair tile — if so, preserves it.
- `_live_pursuers` serialised in `player.json` under `"live_pursuers"` (4-tuple, submap_id included).
- Debug logs: `[LIVE-EXTRACT]`, `[LIVE-EXTRACT-STAIR-DOWN]`, `[LIVE-EXTRACT-STAIR-UP]`, `[LIVE-PROMOTE]`, `[LIVE-CROSS]`, `[LIVE-PENDING]`, `[LIVE-ARRIVE-DEFERRED]`, `[LIVE-MOVE]`, `[LIVE-TIMEOUT]`, `[LIVE-DEAD]`.

**Deferred — reality bubble full implementation:**
- Entity stacking partial fix only.

**Deferred — container system:**
- Container item transfer UI (player inventory <-> container two-panel UI) — Tier 4
- Container lock/stuck mechanic (`"locked": true`, `"stuck": true` fields on container state) — Tier 3
- Container weight (heavy containers block movement until emptied) — Tier 3

**Deferred — language/archaeology:**
- Tier 4 deep tongue words: glyphs only, never resolve. Archaeology system required (Tier 4 stretch).
- `rune_fragment` item: weight=0.3, essence=Revelation, `rune_fragment: true` flag.
  Required for archaeology system. Do not implement yet — item definition only when system is ready.
- `vukhar` (tier 4) unlock via Bellwright NPC encounter — NPC not yet designed.

---

## Claude Code Usage Notes

> Read CLAUDE.md in full before touching any file.
> Dependency order: components → entities → engine → rendering → generation

**Before touching any UI file** (`engine/*_screen.py`, `rendering/*_screen.py`,
`engine/ui.py`, `engine/interaction_cursor.py`, `engine/look_mode.py`):
read `docs/UI_RULES.md` in full. No exceptions. The checklist at the bottom
of that document must be satisfied before any UI change is committed.

### Inviolable Rules
- `from engine.palette import *` — no raw RGB tuples anywhere else
- No hardcoded weather values — all precipitation in `data/weather.json`
- Generation functions NEVER write engine game-state fields
- Bog wraith has NO callout sounds
- Data-driven by default — new content must not require code changes
- Tone: flat/terse for mundane, strange/archaic for ancient
- Never "You are [state]." See tone rules.
- Targeted edits over rewrites. Read files before editing. Confirm signatures.
- **CLAUDE.md must be updated at the close of every session** to reflect all
  implemented systems, changed mechanics, and new data files. This is not optional.
  The close-of-session protocol requires it. Every system that is implemented must
  have a corresponding entry in CLAUDE.md — undocumented systems are invisible to
  future sessions and will be misunderstood, duplicated, or broken.

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
1. Author sprite in appropriate sheet (terrain.png for terrain tiles)
2. `data/sprites/sprite_map.json` — `"id": {"sheet": "terrain", "col": N, "row": N}`
3. `data/tiles.json` — ascii fallback required
4. `data/terrain.json` — move_cost, walkable, transparent, description.
   Optional: secondary_effect, resonance_emit, visual_fx

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
river_adjacent, generator, creature_zones, submap_types, entry_messages, resonance_messages,
waystone_inscriptions (list of text_ids), waystone_fallback_inscriptions (bool),
waystone_themes (list of theme strings — documentation for content authors).

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
