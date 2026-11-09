# Look something up: current authoring families

The registry has eleven families. Eligibility belongs to the **original source class plus operation**, not just the candidate's fields. Unless noted otherwise, the common route is **Begin edit → Validate draft → Review & apply / Apply variant → Confirm apply one file → byte-checked reopen**. Validation checks a temporary candidate; publication writes one selected file. Save referenced dependencies first. A raw Source edit retains extra fields but cannot expand the supported contract.

This page is current implementation at SYS-5. Worked runs are linked separately; do not treat this inventory as a gameplay execution claim. Adapters are under `roguelike/engine/`; exact JSON is in the offline catalogues. [L01–L14](#learning-path) supply isolated practice and full local answers.

## Items

**Source/eligibility:** `data/items/**/*.json`, `item_authoring.py`, contract `expedition-items-6`. Eligible ordinary material/supply and food/drink/treatment definitions plus admitted equipment, held lights, single-essence coatings and vessels have edit/variant operations. Source capability fixes category/use class; arbitrary powers, multi-essence transforms and protected sources remain manual/read-only.

**Controls/retention:** Properties, References, Recipes, Use binding, Factory result; specialized equipment/light/vessel/dose controls. Equipment essence/movesets remain retained read-only. A new `on_use` string does not implement a handler. Validate strict numbers, references and the original source's entitlement. Factory result proves construction only.

**Publication/activation:** save a unique variant, then deliberately reference it from a room, container pool, recipe output, starter or debug acquisition. A new filename alone does not place it. `ItemFactory.create` constructs it; `ItemSystem.use` consumes capability. Exact physical ownership matters.

**State/lifetime:** restart for a new catalogue; fresh instances capture defaults; loaded items can retain physical fields, fuel, dose and vessel state. Some combat/carrying lookups still use definitions. Generated stock does not reroll. Unbuilt planned surfaces can reject captured dependency drift; a new world uses new selections. Example: [L02 ration](#L02), [L10 primitive](#L10). If it parses but does nothing, check capability → method → commitment before changing UI.

## Recipes

**Source/eligibility:** single-object `data/recipes/**/*.json`, `recipe_authoring.py`, `item-preparation-3`. Eligible immediate and passive sources support edit/variant; original execution class is fixed. Definitions containing deprecated, world-placement, `result_tile`, or `apply_turns` classes are outside this editor even if the candidate deletes that field.

**Controls/retention:** Requirements, Preparation, Output, Test requirements. Components and conjunctions allocate distinct materials; tools allocate distinct retained objects. `requires_ambient` is separate. Protected materials may require affirmative selection; a conjunction has no protected-material chooser. The preview's synthetic inventory probe distinguishes eligibility from commitment and passive output construction.

**Activation/state:** save outputs first, then recipe. Craft screen visibility/known status, eligible materials/tools, heat and placement must all reach the real runtime. Immediate exchange currently adds no phase; passive confirmation spends materials and first phase, then map-owned work finishes later. Cancel before commitment keeps materials/time; abandonment after commitment follows job rules. Jobs capture parameters/output ID rather than re-reading every edited recipe. Loaded/generated work continues captured state; new work reads new definitions. Example: [L04](#L04). If a torch seems insufficient, inspect stationary fire, exact allocation and quantity instead of inventing ambient ingredients.

## Creatures

**Source/eligibility:** single ordinary actor objects under `data/entities/creatures/`; `creature_authoring.py`, `creature-composite-10`. Edit/variant is source-specific. Player, NPC and configuration sources are excluded. Basic hosts and supported composite recipes/attachments are distinct. New recipes/first attachments often require a new local composite ID with explicit `can_cross_chunks:false`, `can_use_stairs:false`.

**Controls/retention:** stats, perception, admitted combat/harvest fields and entitled behavior controls; retained tile/components/special settings do not create controls for all code. Factory validates host obligations through `ai_profiles.py`. Legacy ability registry entries can bind exact IDs, so a clone may lose that special power.

**Activation/state:** save before room placement; direct authored-room creature records make actors. `spawn_zones` metadata alone is not enrollment. Perception/AI need actual opportunities and evidence. Saved physical injury/stats/perception and composite effective profiles/commitments persist; current description/attack/speed fields can still come from definitions. Existing generated scenes keep actors, while future construction uses fresh definitions. Example: [L05](#L05). Check factory profile, actual actor count, perception evidence and ID-bound registry before diagnosing “AI broken.”

## Texts

**Source/eligibility:** `data/texts/`, `text_authoring.py`, `ordinary-found-text-1`; ordinary found-text **variants only**. Active Deep Tongue, teaching blocks and special render modes are excluded, with two fixed location-report roles admitted separately. Same-ID text rewriting is not offered as safe editing.

**Controls/retention:** title, ordinary prose/pages, supported condition/damage spans and preview. `type`, `reads_as`, `lacunae`, page `damaged` can be retained without established additional runtime semantics. Preview uses actual reader routines but does not prove acquisition.

**Activation/state:** save text, bind `text_id` on an ordinary readable carrier or placement, then acquire/read. `_use_read` opens `TextReader`, commits use without consuming the carrier, and interacts with knowledge only through implemented rules. Page/span recovery identity lives on the player; it is separate from carrier identity. New variants preserve old knowledge meanings. Existing carriers retain their text reference; fresh room placements use the chosen ID; generated scenes keep their carriers. Example: [L03](#L03). Missing prose usually means wrong text ID, unsupported carrier use or stale catalogue, not a font problem.

## Loot pools

**Source/eligibility:** one object immediately under `data/loot_pools/<id>.json`, `pool_authoring.py`, `contextual-loot-1`; edit/variant, exact filename/ID match. Arrays/nested sources are excluded. Up to 64 ordered weighted entries; every branch/reference must validate, not only the randomly chosen one.

**Controls/retention:** description, roll range, weighted physical entries and references. Pool context is the actual caller; legacy `data/loot/` remains a separate mechanism. Unknown metadata is not a new loot condition.

**Activation/state:** save item dependencies, save pool, bind it to a room/container. A variant changes no incoming references automatically. New rolls use its weights; generated stock consists of physical saved objects and is not replenished by editing the pool. Planned surfaces can capture pool/item dependencies before construction. Example: `guide1_supplies.json` yields one guaranteed ration in the [L07](#L07) cottage. Diagnose no loot by checking binding and stock lifetime before random weights.

## Rooms

**Source/eligibility:** ordinary direct `data/layouts/*.json`, `room_authoring.py`, `authored-room-2`; edit/variant. The exact G17 source example is a variant-only template. Starting labs are protected by path and ID. Rectangular layers/legend, explicit start and admitted direct specials are supported; weighted/deferred nesting is outside the editor route.

**Controls/retention:** terrain grid/legend, items, actors, static decor/light, containers, access screens and remains; preview and captured Test room. Unknown metadata is retained, not guessed. Direct actors belong to authored submaps, not arbitrary surface specials. Validation checks geometry, consumers, dependencies and bounded access.

**Activation/state:** save dependencies and room. Test room constructs a controlled scene; ordinary discovery requires assignment enrollment. Reset keeps capture; latest uses new saved inputs. A pending room uses its selected layout on first construction; generated scene state, depletion and actors persist. Example: [L06](#L06). Wrong lifetime explains many “edit ignored” reports; verify capture ID and whether the room was already generated.

## Buildings

**Source/eligibility:** immediate `data/buildings/<supported-category>/<id>.json`; `building_authoring.py`, `surface-building-1`; edit/variant. Plazas, arrays and deeper nested sources are excluded. Category and placement contract constrain the route.

**Controls/retention:** geometry, admitted contents, footprint/frontage/access, rotations/mirroring and dependency preview. The production compiler transforms supported coordinates; it refuses unknown coordinate-bearing metadata instead of inventing transformations. Test every admitted orientation and required approach/target.

**Activation/state:** save then enroll in explicit settlement membership or the appropriate policy. A variant changes no explicit lists, **but legacy folder selection can discover it**, so a production file is not a sandbox. Existing plans retain selections and captured dependencies; pending construction may refuse incompatible drift; generated scenes retain state. New worlds rebuild policy. Example: [L07 cottage](#L07). Diagnose fitting separately from selection, and a nearby road separately from the assigned frontage.

## Underground assignment

**Source/eligibility:** fixed `data/generation/authored_submap_selection.json`, `assignment_authoring.py`; **edit only**. Fields include enabled, supported target type, conditional authored chance, saved layout IDs and positive relative weights. This is not an arbitrary all-biome spawn editor.

**Controls/validation:** choose saved eligible rooms, validate/reopen dependencies, then preview generated metadata. The sample calls real `generate_world` but constructs no rooms. One-file publication updates policy only.

**Activation/state:** new-world selection records the chosen `layout_id` on each submap. Editing policy does not reassign old worlds. A same-ID room edit can affect a selected but unbuilt room; already generated scenes keep saved contents. Example: [L07](#L07), using probability 1 solely to make route proof deterministic. For actual content choose a deliberate chance/weight and test multiple worlds. Missing appearance: inspect assignment metadata before looking for a local construction bug.

## Settlement selection

**Source/eligibility:** fixed `data/generation/settlement_profiles.json`, `selection_authoring.py`, `settlement-membership-1`; **edit only**. Seven tables: grid and roadside residential/commercial/support, plus landmark membership. Civic membership, schedules, minima, repeat multiplier and fit budget are protected.

**Controls/validation:** choose compatible saved buildings, relative weights and supported per-settlement limits. Validate actual source class, context and dependencies. Source edits beyond those lists require the manual world-policy route described in [the atlas](#system-atlas--places-and-generation-policy).

**Activation/state:** new plans choose among members; membership is not a guarantee of fit. Existing plans preserve chosen assets. Pending/generated surface rules match buildings. Example: [L07](#L07) uses a controlled residential list to demonstrate a newly selected cottage. A new town's layout, road connections and public-space policy involve additional source/configuration work; do not infer they are editable from this one form.

## Access profiles

**Source/eligibility:** immediate `data/access_profiles/<id>.json`, `access_authoring.py`, `access-profile-1`; edit/variant for bounded coffer/screen methods. This does not provide a universal lock/quest API.

**Controls/validation:** cutting threshold and careful work steps, force, Dissolution dose, exact screen salvage and host restrictions. Save profile before a supported coffer/screen placement. Validate both profile and target host; an arbitrary decor object is not necessarily a secured container.

**Activation/state:** `access_actions.py` rechecks ownership/resources and acts on a captured access object. Careful work pays each step; force pays one action with no salvage; dissolution spends one dose/action. Fresh hosts capture profile; partially worked/generated/saved objects retain it. Editing source does not reset progress. Example: inspect the shipped `sys4_access_room` in a captured Test room, then substitute a new admitted profile. Diagnose access target, exact method requirements, partial progress and stale selection separately.

## Typography

**Source/eligibility:** fixed `data/display/typography.json`, `typography_authoring.py`, `game-typography-1`; **edit only** for version-1 `game_typography` with thirteen string font assignments.

**Controls/validation:** role/resource selection and actual Pygame preview. Dependencies are project Fonts resources, with bounded file/path/glyph checks. Sizes remain in `engine/typography.py:ROLES`; arbitrary layout/Unicode completeness is not promised. Missing resources or functional glyphs need repair, not silently accepting a preview box.

**Activation/state:** publication replaces the active profile; next display initialization loads it. Screens cache fonts/metrics, no live swap or per-save theme. Running/loaded/generated worlds do not own a typography snapshot. Example: [L08](#L08) makes ordinary prose bold in the disposable payload and captures the reader. Diagnose profile/resource identity and reinitialization before changing every screen.

## Field status and lookup discipline

**Declared** means present in data/schema. **Retained** means preserved by the tool. **Consumed** means a runtime reader uses it. **Executed** means a named scenario exercised that use. The four are not synonyms. Use `rg -n 'field_name' roguelike workbench/src workbench/worker` to find both author and consumer; exclude generated `target/` and node modules from broad searches. The [task index](#task-index) routes you to integration steps and [source map](#source-evidence) to checked paths/receipts.
