# I want to…

Choose the outcome, then follow its lesson/reference. Every recipe below states the integration edge that is easy to miss. Commands start at the repository root; routine practice uses [the isolated launcher](#learning-path). Intentional production authoring happens only after a reviewed candidate, named checkpoint and scoped diff.

## Change an existing property

**Outcome:** a fresh instance has a different measured value. **Prerequisites/files:** find its definition and factory/consumer with `rg`; use L01's ration to practice. **Tool/source:** supported Workbench Properties or the equivalent one-field JSON diff. **Activation:** restart the catalogue and construct a new instance. **State/time/persistence:** copied fields on saved instances may remain old; include the ordinary action's paid tick. **Evidence:** before/after values and rejected-action control. **Failure:** valid JSON in a stale session or unscanned folder. **Extend:** add a new variant and appearance route in [L02](#L02).

## Create food, drink, materials or supplies

**Outcome:** a useful new item using an existing capability. **Files:** `data/items/`, `item_authoring.py`, `ItemFactory.create`, `ItemSystem._use_eat/_use_drink`. **Tool/source:** clone an admitted original via Save as new variant; equivalent full JSON with unique ID and class retained. **Activation:** save, bind to room/pool/output, acquire/use. **State/time:** exact owned object; committed use and consumption differ, empty-form drinks preflight exchange. **Evidence:** [L02](#L02) pickup/use, need delta and one physical removal/replacement. **Failure:** unknown handler or no acquisition edge. **Extend:** use [L04](#L04) to make it a preparation output.

## Create equipment, a held light, coating or vessel

**Outcome:** a supported specialized physical item. **Files:** corresponding item source; `equipment_authoring.py`, `light_authoring.py`, `coating_doses.py`, `vessels.py`. **Tool/source:** start from an eligible original and use its bounded controls. Movesets/essence are retained read-only in equipment authoring; manual source route is [L09](#L09). **Activation:** acquire and use/equip via inventory, or select a vessel/dose through its real menu. **State/time:** owned light captures reach/fuel; coating captures dose; vessel owns UUID/water. **Evidence:** exact sibling unaffected, valid use, depleted/rejected state, save/cold restore. **Failure:** editing defaults on already owned objects or using cosmetic light radius as mechanical reach. **Extend:** [L12](#L12) explains persistent systems.

## Make an item appear

**Outcome:** reachable physical content. **Files:** item, `loot_pools/<id>.json`, room `special_tiles`, container binding, or deliberately changed `player_setup.py`. **Tool/source:** save dependencies first; weighted pool entry alone still needs a caller. **Activation:** new roll/new scene or new starter; debug spawn is construction-only. **State:** generated stock remains depleted; pending planned surfaces retain dependency checks. **Evidence:** inspect actual room/container and ordinary pickup, as [L02](#L02)/[L07](#L07). **Failure:** “why isn't my item appearing” usually means a missing reference or wrong lifetime. **Extend:** vary weights only after proving the route.

## Create a recipe or passive processing chain

**Outcome:** materials/tool/heat produce a usable output. **Files:** `data/recipes`, `crafting.plan_craft/commit_craft`, `CraftScreen._attempt_craft`, engine processing methods. **Tool/source:** admitted recipe variant; save output first, then distinct materials/tools/conjunctions and ambient conditions. **Activation:** craft screen, choose materials, confirm placement. **Time/state:** immediate exchange currently free; passive confirmation pays first tick, job owns work; tools retained, materials spent. **Evidence:** [L04](#L04) cancellation, first tick, cold unfinished work, completion/use. **Failure:** insufficient quantity, protected automatic material, or absent stationary fire. **Extend:** vessel batches/material-sensitive output, studied in [L12](#L12).

## Add a creature, compose behavior or harvest

**Outcome:** a deliberately different enemy with finite useful remains. **Files:** `data/entities/creatures`, `CreatureFactory.spawn`, `ai_profiles.py`, `enemy_components.py`, `enemy_maneuvers.py`, `enemy_scavenging.py`, `harvesting.py`. **Tool/source:** new admitted variant, supported recipe/attachments and harvest fields. **Activation:** direct authored-room actor or real spawn selector; `spawn_zones` is not enrollment. **State/time:** paid AI opportunities, saved effective profile/commitments, captured modern flesh depletion. **Evidence:** [L05](#L05) actual opportunities/profile restore; test harvest under real cutting/ownership requirements. **Failure:** cloned ID lost an entry in `creature_abilities.ABILITY_REGISTRY`, or inactive actor never received an opportunity. **Extend:** add a new behavior implementation only with host/perception/save integration.

## Write a readable text

**Outcome:** player acquires and reads your prose. **Files:** text definition, readable carrier `text_id`, placement; `ItemSystem._use_read`, `TextReader`, `language_system.py`. **Tool/source:** ordinary text variant, pages/spans and preview; special teaching routes remain manual/protected. **Activation:** bind and acquire carrier, then use it. **State/time:** reading commits without consumption; navigation free; recovered knowledge is player/text/page/span identity. **Evidence:** [L03](#L03) reader and cold carrier restore. **Failure:** wrong text ID or same-ID rewrite invalidating recovery meaning. **Extend:** a new clue needs an implemented gameplay gate to become a consequence.

## Build a playable room

**Outcome:** coherent geometry, threat, clue, useful contents, access and return. **Files:** direct `data/layouts/<id>.json`, `room_authoring.py`, `generation/authored_rooms.py`. **Tool/source:** ordinary room/template variant with supported direct specials. **Activation:** save dependencies, preview, captured Test room; enroll separately. **State/time:** room construction creates owned physical objects; depletion/actors persist. **Evidence:** [L06](#L06) reading, threat opportunities, ordinary stairs, cold/depleted scene. **Failure:** blocked return, deferred special, stale capture. **Extend:** [L07](#L07) natural selection; access profiles can add alternate work/force/dose approaches.

## Make a place appear naturally

**Outcome:** a new world selects and constructs your authored place. **Files:** underground `authored_submap_selection.json` versus surface building/`settlement_profiles.json`; `generate_world`, scene constructors. **Tool/source:** distinct Assignment and Selection editors or their exact JSON. **Activation:** create a new world; inspect selected metadata, then enter/build. **Lifetime:** old assignment stays; unbuilt underground can use edited room; generated scene stays; planned surfaces may refuse dependency drift. **Evidence:** [L07](#L07) real selection and construction, with controlled chance and disclosed initial player staging. **Failure:** a Test room pass was mistaken for discovery. **Extend:** test varied worlds and desired prevalence after proving the route.

## Create a building or a new town

**Outcome:** a useful surface structure with valid approach, or a deliberate new settlement policy. **Files:** `data/buildings`, `data/generation/settlement_profiles.json`, `settlement_layouts.json`, compounds/POI/road policies, `world_plan.py`. **Tool/source:** Building for geometry/transforms; Selection for seven membership lists; manual source route for protected civic/layout/world policy. **Activation:** new plan and real surface construction. **State:** existing plans retain choices/dependencies, generated scenes retain state. **Evidence:** orientations, required targets, planned context, selected placement and actual local map. **Failure:** eligible asset fails fit, a nearby road is not assigned frontage, or ID was never enrolled. **Extend:** [world generation](#world-generation), [compounds](#compounds), [L07](#L07).

## Add a sprite or change a display role

**Outcome:** readable actual appearance. **Files:** sprite sheet + `data/sprites/sprite_map.json` key + consuming definition, or `data/display/typography.json` + project TTF. **Tool/source:** register asset/key manually, or use Typography's bounded role assignment. **Activation:** new renderer/display initialization. **State:** shared cells affect every user; screen metrics cached, not campaign-owned. **Evidence:** [L08](#L08) real reader capture; inspect sprite at native/display sizes and both modes when claimed. **Failure:** unreferenced asset, wrong cell dimensions, missing glyph or stale initialization. **Extend:** deliberate UI layout/code change with screen-specific checks.

## Add an ability

Choose the mechanism before editing. **Weapon technique:** [L09](#L09), weapon JSON → `movesets.execute_moveset` → engine result consumer. **New item primitive:** [L10](#L10), `on_use` → implemented method → checked result/application → feedback/commit. **Event response:** [L11](#L11), real firing site → registered tagged handler → consumed effect → cleanup/restore. **Creature behavior:** [L05](#L05), supported host/profile or an actual new implementation. **Timed condition:** [L11](#L11)'s venom trace; implement delivery, gates, phase aging, removal and saved schema explicitly.

Prerequisites are the owning system's contract and a bounded fixture. Workbench cannot author arbitrary Python or currently edit equipment movesets/essence. Manual definitions must have unique action/handler IDs and a reachable input route. Evidence needs success, rejection, missed contact where relevant, phase/consumption and persistence. A parsed field, direct helper call or declared `add_status` is insufficient. Extend the smallest existing mechanism that fits; do not silently commission a generalized magic system.

## Save my new field or build a persistent subsystem

**Outcome:** a valid state machine continues after a cold load. **Files:** owning component, serializer/validator/defaults/restore in `save_components.py`/`save_manager.py`, actual action/hook callers. **Tool/source:** manual Python; [L12](#L12) reuses `Perks.perk_state` but adds strict inner validation. **Activation:** registrations installed before construction/load; ordinary use starts/inspects/cancels. **State/time:** define transitions and first tick; distinguish absent legacy state from malformed presence. **Evidence:** current-state identity unchanged on refusal, same/fresh process continuation, scene return and no render tick. **Failure:** arbitrary attribute omitted, validator alias missed, hook error swallowed, or callback never fired. **Extend:** use L12's additional integration checklist for a genuinely new owner.

## Diagnose an edit that does nothing

**Outcome:** locate the first broken edge. **Files:** definition → loader/factory → actual dispatch → state/feedback, found with `rg`. **Tool/source:** syntax check and minimal fixture before changing code. **Activation:** repeat the ordinary input, not only a helper. **State/time:** compare catalogue, instance, scene and checkpoint lifetimes; record exact phase deltas. **Evidence:** [L14](#L14) unknown handler and inert field controls; expected failure must distinguish causes. **Failure:** fixing a test by bypassing the intended route. **Extend:** add a regression at the broken boundary and update its authoritative guide.

## Keep, undo or maintain a change

**Outcome:** a reviewable scoped change and useful current reference. **Files:** only your intended paths; page/topic/source map if commissioned. **Tool/source:** `git status`, named checkpoint, `git diff -- path`, explicit `git add -- paths`, descriptive commit. **Activation:** push only with authorization; GUIDE-1 itself includes it. **State:** tags capture committed state, not uncommitted edits; preserve exact pre-edit bytes for practice patches. **Evidence:** focused checks, scoped diff, build/source drift and remote revision readback. **Failure:** blanket reset, staging unrelated art, or merely changing the handbook SHA. **Extend:** [L14](#L14) and [maintenance](#maintenance), without an LLM or automatic whole-wiki obligation.
