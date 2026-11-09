# How Resonance works

Follow seven questions when a creative idea becomes code: **definition → construction → activation → state owner → time → persistence → feedback**. These are investigation questions, not a claim that every feature uses one universal pipeline. The current runtime includes different mechanisms built at different times. This atlas names their actual boundaries at the reviewed SYS-5 source.

## Startup and repository

`roguelike/main.py` builds the ordinary game using `config.py`, `DataLoader`, factories, player setup and `Engine`. Relative asset paths make the game working directory important. The guide launcher sets it explicitly and supplies a save owner before construction. `tools/play_disposable.py` isolates saves while using production data; it does not isolate content writes. Workbench captured rooms instead freeze their input payload and use a separate writable session root. Logs are the terminal's output and the in-game log; the handbook launcher retains each child's stdout/stderr beside its receipt.

Use [setup](#learning-path) and [L01](#L01) first. Check `requirements-baseline.txt` rather than installing arbitrary latest libraries. The checked Windows target is CPython 3.11.0 with the recorded game pins. Source under another directory is not selected by choosing an old environment's Python executable.

## Python foundations at the point of use

A **module** is a `.py` file imported by name, such as `engine.item_system`. An import locates code through `sys.path`; the practice launcher deliberately puts the captured production source first. A **function** receives values and returns a result. A **method** also receives its owning object as `self`: `ItemFactory.create('guide1_ration')` uses that factory's `data` catalogue.

JSON objects become Python dictionaries. `definition['id']` requires a key; `definition.get('weight', 0.1)` provides a default. A default is a compatibility decision, not a substitute for rejecting malformed values. Python `True` is also an integer subtype; strict persisted counters use `type(value) is int` to reject it.

An **instance** is one object, even if another object has the same ID. `a is b` tests identity; `a.item_id == b.item_id` tests a shared definition name. Mutable dictionaries/lists can be shared by reference. `copy.deepcopy` or a deliberate serialized snapshot prevents a later mutation changing your supposed “before” observation. L12 demonstrates this distinction for saved state.

Return values have local contracts. `False` from an item-use handler can mean a successful reusable action; inspect `last_use_committed` too. An exception stops the current operation unless caught. Hook dispatch catches handler exceptions, so save validation must happen before dispatch and before live replacement. A small test should ask an observable question: “does rejection leave the same object, resources and turn?” Merely comparing a helper's output with its own formula proves little.

## Runtime, input and time

`Engine.run` processes Pygame events and renders frames. `_handle_key` gives modals priority: readers, inventory, perks, crafting, interaction/placement cursors, then local/world input. `Engine._advance_turn` coordinates a paid simulation phase. It fires `ON_TURN` before `world_time.advance`, then advances needs, AI and owned lifecycle work. Frame count is not a gameplay clock.

Movement opportunities, weapon action phase credit, work phases and animation time differ. `_weapon_action_phases` accounts for weapon cost; a rejected moveset does not commit it. A successful ordinary item use charges through inventory; immediate crafting currently has no extra phase, while passive confirmation pays the first phase. Full paralysis gates physical action and active defense while allowing bounded inspection. Death guards prevent a second action after dying. [L09](#L09)–[L12](#L12) record accepted/rejected deltas; [controls](#controls) is the input reference. The historical `TurnQueue` architecture description is not the current coordinator.

## Definitions and identity

`DataLoader` creates startup catalogues from JSON. `StructureCatalog` strictly compiles eligible structures; not every ordinary dictionary loader has identical duplicate/error behavior. Stable IDs connect definition references; filenames and source class also determine authoring eligibility. A file in an unscanned directory is inert. A parsed extra field can remain inert even in a loaded dictionary.

`ItemFactory` makes physical items; `CreatureFactory.spawn` assembles actors/components and effective AI profiles. A new instance is not enrolled in a loot table or scene automatically. Some runtime lookups still use current session definitions, while lights, doses, AI commitments and other physical state are captured. Follow the consumer instead of assuming all fields are copied or all are dynamically looked up. [L02](#L02), [authoring reference](#authoring-reference) and the embedded catalogues separate these questions.

## Inventory, equipment and ownership

`components/inventory.py` uses exact object membership. `engine/item_transfers.py` centralizes safe exchanges and consumption; an inventory, floor, container or processing job should own an item once. Same-ID siblings are not interchangeable in a pending selection. Equipment keeps references to owned objects, and carrying reductions are derived from active equipment and definitions rather than permanently written into every item's weight.

Read `Inventory.bind_carrying`, `ItemSystem.use`, `vessel_menu.py` and transfer helpers before adding an action. Preflight capacity and outputs before spending inputs; revalidate pending UI selections at commitment. Remains and flesh have depletion state, not an endless loot button. [L04](#L04) and [L12](#L12) explain exact materials/tools and the transfer into owned work.

## Combat and abilities

Ordinary attacks flow through engine attack methods and `combat.resolve_attack`, with fighter/body, armour, essence, dodge and effects contributing. A weapon moveset is data interpreted by `movesets.execute_moveset`; the engine consumes the result. The current Q/R route selects the nearest eligible living blocking fighter passing melee legality. A large `range` value does not make an arbitrary ranged targeting UI. Cooldowns share the action ID namespace.

An item capability selects an implemented `_use_…` method. Perks need definitions, a real `HookEvent` firing site, `HANDLER_MAP` registration and a consumer for returned effects. Legacy `creature_abilities.ABILITY_REGISTRY` contains exact-ID behavior that copying a creature does not inherit. Generic `add_status`/`remove_status` branches in engine `_apply_effects` are unimplemented. `pool_turns` and `on_kill_only` moveset results are parsed without the broad lifecycle their names suggest. Use [the ability route](#task-index--add-an-ability), [L09](#L09), [L10](#L10) and [L11](#L11), not a fictional universal ability system.

## AI and perception

`CreatureFactory` selects a registered host; basic AI types coexist with `CompositeAI`. `ai_profiles.py` validates supported recipe/host bindings. Composite attachments add bounded response, maneuver, escort, alarm, venom or scavenging behavior where the source class permits them. A new recipe or first attachment often requires a new ordinary composite ID. Cross-chunk/stair support is explicit, not inferred from a name.

Sight uses geometry and shared illumination; hearing uses discrete sound evidence and bounded interest. Do not give a behavior the player's hidden location merely because a test fixture knows it. Paid opportunities advance commitments; saved effective profiles and tactical state persist according to their own rules. `spawn_zones` metadata is not an active spawn enrollment by itself. [L05](#L05) supplies an independently runnable guard, while [creatures and AI](#creatures-ai) covers ordinary source fields.

## Conditions and transformations

The working venom lifecycle is victim-owned on the fighter. A qualifying damaging nonlethal contact can capture a dose and source provenance. `effect_lifecycle.finish_turn` ages each live owner through `venom.age`; the captured phase identity prevents double aging. Warning → full physical paralysis → recovery → absent is a concrete state machine with validation and restore. Treatment has its own exact ownership and action gate.

This is not equivalent to writing an arbitrary string into a generic status list. Corruption/exposure and temporary speed/sight use other explicit consumers and persistence fields. Extending a condition requires its delivery, time boundary, action/defense gates, feedback, schema, defaults and removal behavior. Preserve full paralysis semantics when experimenting. [L11](#L11) contrasts the new event response with this delivered lifecycle; unsupported generalized magic/quest systems remain proposals.

## Materials and processes

`crafting.plan_craft` allocates distinct physical materials/tools against keyword and conjunction requirements. `requires_ambient` describes a nonconsuming environmental condition. Protected items are excluded from automatic material choice but can be explicitly selected; tools are retained because of their role. A held light can provide burning, but passive processing also needs a stationary fire.

Passive cooking consumes selected materials and creates an output-ID/timer job in `LocalMap.processing_layer`, advancing on paid phases. Vessel jobs additionally retain the physical vessel with its exact UUID, water quantity, busy ownership, output delivery and abandonment. Material-sensitive washes capture a dose from the selected material's tier; a generic output ID alone does not describe that dose. Harvesting and SYS-5 scavenging compete over finite remains/flesh. [L04](#L04), [L12](#L12), and the current authoritative `PRACTICAL_VESSELS.md`, `MATERIAL_WEAPON_PREPARATIONS.md`, `LOCAL_SCAVENGING.md` explain the distinct routes.

## World structure and lifetimes

The coarse `WorldMap` owns chunks and submap metadata. A local map owns generated terrain, decor, physical contents and jobs. The engine selects an active scene; save/cache ownership preserves generated scenes through leave/reentry. A submap ID, layout ID and physical scene identity answer different questions.

An underground assignment is chosen during new-world generation, saved as metadata, then constructed lazily. A same-ID room edit can affect an assigned but unbuilt room. Once generated, its saved scene wins. Planned surfaces capture dependencies and may refuse pending construction if required definitions drift; they do not silently rebuild everything. Missing owned cache is not permission to regenerate depleted contents. [L07](#L07) demonstrates selection and construction separately; [saves](#saves-and-state) explains checkpoints versus working cache.

## Places and generation policy

Buildings have local geometry plus placement contracts: footprint, transforms, buffers, approach, frontage, entrances and required targets. Town membership selects eligible assets within layout/role policy. Compounds group members and their internal access; POIs, rural sites, roads and country connections operate at other layers. WFC is one ground-palette mechanism where invoked, not the entire generator.

Use `generation/world_gen.py`, `world_plan.py`, `settlement_selection.py`, `country_network.py`, `poi_selection.py`, `data/generation/` and the current structure chapters for source changes beyond Workbench's seven editable settlement membership lists. Preserve explicit civic/layout rules unless your commissioned change includes them. Use external candidates and `tools/structure_authoring.py` for geometry/orientations/planned context, then generate a new world and inspect actual selected placement. Workbench's missing control is not evidence the runtime has no capability. [L06](#L06) and [L07](#L07) provide both room and surface examples.

## Lore, reading and knowledge

A physical carrier points to a text ID. Text definitions hold prose/pages/damage spans; language and recovered-text knowledge live on the player. A reader open is a committed nonconsuming use, while paging/scrolling is inspection. Known glyphs and teaching text have specific language consumers; arbitrary `type`, `reads_as`, `lacunae` or page `damaged` declarations do not establish extra mechanics.

Workbench permits ordinary new variants and bounded location-report roles, not arbitrary same-ID text replacement or special Deep Tongue teaching edits. Same-ID damaged-prose changes can conflict with stored page/span identity. Stable knowledge identity matters independently of carrier object identity. [L03](#L03) uses ordinary text; [texts](#texts-loot-scenes) and the source `language_system.py` explain the specialized routes. A lore note alone does not create a quest trigger.

## Needs and progression

Food/water JSON commonly uses integer units; `Needs` normalizes against maxima, with 0 full and 1 critical. Legacy values at or below 1 can be treated as fractions. Paid needs ticks can include biome multipliers. Observe the effect plus phase cost, avoiding clamps when comparing quantities.

Levels and perk points are explicit player components. The perk purchase screen checks acquired status, affordability and paralysis; not every broader unlock declaration is enforced there. Hooks are rebuilt after acquisition/load. A descriptor, UI label or definition's aspiration is not a proof of an active gate. [L01](#L01) makes units visible; [L11](#L11) tests real purchase and dispatch; [survival](#survival-progression) gives tuning routes.

## Light, weather and resonance

SYS-2 is shared illumination. `illumination.py` builds finite obstructed footprints from terrain, decor and owned held lights; perception and display consume shared samples. Rendering can add cosmetic modulation without advancing gameplay. Held-light fuel/settings belong to the physical item and survive reconstruction; an inactive or unowned object is not a free light source.

Weather selection and weather consumers are separate: a JSON name alone does not guarantee a mechanical modifier. Resonance accumulation, corruption and discharge have implemented engine/system consumers; inspect those before inventing a new effect. `weather.py`, `resonance_system.py`, `held_light.py` and `illumination.py` are change routes. [weather](#weather-and-atmosphere), [terrain/decor](#terrain-decor-and-variation) and [L08](#L08) separate atmospheric appearance from gameplay evidence.

## Art and interface

`data/sprites/sprite_map.json` maps keys to sheets/cells. A key can have many users; changing a shared cell changes all of them. Registered sheet cell dimensions and displayed game zoom differ. Confirm actual resources, native size, alpha and neighboring cells before painting. A new source image does nothing until a key/consumer uses it.

`DisplayConfig`, typography roles, palette and screen renderers define the interface. Typography edits select project TTF resources at retained nominal sizes; they do not redesign every panel. Screens cache initialized fonts. Unknown language glyph generation is separate from the known proportional font. [L08](#L08) changes a role and captures the actual reader; [sprites](#sprites-and-atlases) explains atlas registration and [display](#display-ui-and-palette) the UI routes.

## Saves and compatibility

`SaveManager` serializes explicit player/world/scene records, validates references and schemas, reconstructs staged objects, then replaces live state. `save_components.py` specifies captured fields/defaults; adding a Python attribute is insufficient. The outer `Perks.perk_state` dictionary already persists, but a new inner schema needs explicit validation before replacement.

Specify optional absence separately from malformed presence. A legacy default must not accidentally reinitialize a modern intentionally absent vessel. Do not replay an ON_TURN effect while merely restoring derived bonuses. Check same-process save/load, fresh process with registrations installed, then continued behavior and scene leave/reentry. [L12](#L12) supplies those checks and explains integration for an entirely new component. Personal saves are never compatibility scratch files.

## Workbench internals

The React document/edit views present bounded schema controls and source. Rust owns verified project paths, publication, recovery and captured runtime lifecycle. The Python worker loads the selected project's adapters and validates a candidate in temporary **data** staging; it does not overlay arbitrary Python. Contracts and hashes connect these boundaries. [Workbench internals](#workbench-internals) shows the route for adding a supported field and what must be checked at each boundary.

## Testing, diagnosis and sustainable maintenance

Start with a prediction and the smallest input that distinguishes two causes. A syntax check proves syntax; a factory probe proves construction; a direct handler check proves a seam; actual app-local events prove dispatch; world-generation receipts prove enrollment; cold continuation proves reconstruction of the tested state. Keep these labels in reports.

Search with `rg`, inspect the traceback's first relevant project frame, compare before/after state, then repair the owning layer. Do not add a new wrapper just to make a test bypass the broken input path. [L14](#L14) and [troubleshooting](#troubleshooting) give diagnosis exercises. [Maintenance](#maintenance) explains main/checkpoints, scoped diffs, safe reversal, page edits and source/topic drift. Wiki upkeep is separately commissioned or deliberately manual; feature work still updates its affected authoritative guide.

## Evidence and status language

**Current implementation** means inspected code. **Executed example** names a run and input. **Historical source** retains an earlier account. **Partial/unsupported** names a boundary and nearest route. **Proposal** means future work. Consult `source-map.json` and the [edition evidence](#coverage) for bindings. Source fingerprints detect changes; they do not prove prose correctness or human learning.
