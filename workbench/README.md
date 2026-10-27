# Resonance Workbench · W4B

An independent, local Tauri 2 desktop application for inspecting Resonance and
safely editing ordinary buildings, contextual loot pools, inert component items,
one immediate recipe family and ordinary revenant variants. The game remains the
validation authority. No campaign, running game or Internet service is required.

## Author a creature variant

1. Choose **Creatures** in the existing content browser. This filters the loaded
   creature sources, including unsupported advanced definitions. The current
   catalogue contains 13 non-player creature records and one separate player
   record. Search by ID/name/path and use the support filter. `hollow_revenant`
   is currently the one writable source; players, NPC/other entities, special
   ability creatures, vine-network records and array sources remain read-only.
2. Open it to inspect the exact source, path, source hash, project revision,
   supported shape and diagnostics. **Begin edit** enables **Actor name** and
   **Effective HP**. Name is literal `Actor.name`. Effective HP changes both
   `base_hp` and `fighter.max_hp` in one undoable operation: the production
   `CreatureFactory` prefers `base_hp`, and `Fighter` starts current HP at that
   maximum. The explicit authoring range is 1–1,000,000 integer HP and 1–256
   characters for the name; these are tooling bounds, not new game rules.
3. **Read-only fields** retains authored descriptions, AI, attacks, perception,
   faction/hostility strings, limbs, harvesting, effects, spawn declarations and
   unknown metadata. The current look UI resolves descriptions by `actor.tile`,
   so editing a new-ID variant's description would not reliably change displayed
   prose. Description therefore has no typed control and cannot change through
   raw publication. This task does not repair or change that gameplay lookup.
4. Source, typed changes, undo/redo, validation and Diff use the existing single
   draft. HP edits replace only two scalar spans; other nested data, array order,
   prose, whitespace and line endings survive. Invalid raw JSON freezes typed
   controls. Raw and variant-ID edits clear typed history. No-op inspection
   writes nothing. Raw changes to any field outside ID/name/the two HP fields
   are rejected; an unsupported source cannot gain entitlement by raw promotion.
5. **Save as new variant**, enter a unique ID, **Validate draft**, review **Diff**,
   then **Apply variant → Confirm apply one file**. Publication always creates a
   new file beside the source in its existing creature directory. Original and
   saved actors remain unchanged. The host binds original source entitlement,
   dependencies, exact reviewed bytes and safe paths, repeats game validation,
   publishes atomically without clobbering, and checks the reopened hash.
6. **Factory result → Validate and construct exact creature** works on either
   the exact draft or reopened variant. It copies current data into disposable
   scratch, loads it with `DataLoader`, and calls the real `CreatureFactory.spawn`.
   The receipt shows actor identity/class, source-to-component HP/name comparison,
   Fighter/Perception/AI values, source/dependency hashes, available Git revision,
   worker contract/version and observation time. No inventory owner, campaign,
   AI/combat turn or ongoing world is created. This proves construction, not
   combat balance or natural encounter availability. Invalid drafts, external
   source/dependency changes and superseded jobs clear current factory evidence.
7. **Direct layout references** lists saved, direct `authored_submap` creature
   records with exact paths, fields and coordinates. **Inspect layout** reads that
   source without replacing a parked building draft. An empty table means no
   supported direct reference was found, not that every possible use is known.
   Ordinary buildings, plazas and entrance layouts have no creature-placement
   entitlement. `spawn_zones` is a declaration with no current Python consumer;
   actual zone lists, town selectors and resonance rules are separate authorities.

A new variant **does not join worldgen pools, replace existing instances, or
change an authored room**. Selection/reference changes are separate authoring
work. Five independent document drafts stay parked through creature navigation;
saving any file revokes older reviews. No second writer or multi-file transaction
was added. Catalogue pages render at most 100 rows.

The game-owned read-only contract is `revenant-hp-1`. It checks the original
single-object source under `entities/creatures/`, the ordinary revenant tile and
wandering/mirrored-HP shape, and the actual ability registry. It independently
rejects ambiguous entity IDs/case collisions, duplicate keys and missing required
dependencies. Tile references use `TileRegistry`. The factory's default
`body_human` fallback is absent in current data; the shipped Revenant's inline
limbs take precedence, so this unused fallback is disclosed as a warning.
Faction/hostile strings are membership labels, not a separate faction registry.

The [example variant](docs/examples/hollow_revenant_w4a.json) and
[factory receipt](docs/examples/hollow_revenant_w4a.factory.json) are outside the
active catalogue. Native publication occurs only in disposable ignored test data.
See [W4A delivery](docs/W4A_DELIVERY.md) for construction and existing G17 placement
corroboration, native captures, verification and limits. No creature placement UI,
AI/effect editor, encounter simulator or gameplay/save changes are included.

## Author an immediate recipe variant

1. Open an item and choose **Recipes**. **Produces this item** lists exact declared
   `result_item` references; **Potential ingredient matches** uses current game
   tag/tier predicates. Each row retains recipe ID and source path. Neither table
   proves knowledge, quantities, access to ingredients or ambient conditions.
   The content browser also searches recipe ID/name/category/path/output ID, with
   route and support filters. Select a source explicitly when IDs collide.
2. Open `bile_coating`, currently the one shipped writable recipe in this family.
   **Requirements** retains component order, repeated rows, reusable tools and
   ambient conditions. Defaults are minimum tier 1 and physical quantity 1.
   **Output** resolves the declared item and links to its item inspector. Return
   to an item or use the document buttons to retain structure/pool/item/recipe
   drafts and their independent histories.
3. **Begin edit** exposes name, authored description, category, known flag,
   ordered components/tools, ambient requirements and output item. Item tags come
   from the loaded keyword catalogue. Ambient tags come from the actual
   `CraftScreen._build_ambient_sources` collector exercised on disposable loaded
   decor/light definitions: `burning` is not an item-keyword catalogue entry.
   Controls support add/remove/reorder and exact scalar-span edits; unknown data,
   nested records and unedited whitespace remain intact. Invalid raw JSON freezes
   typed controls while retaining the raw draft. Raw/ID changes clear typed undo.
4. **Save as new variant**, choose a unique ID, **Validate draft**, inspect the
   exact **Diff**, then **Apply variant → Confirm apply one file**. Only a new
   file beside the source is published; recipe originals cannot be overwritten.
   The host checks source bytes, discovered entitlement, canonical safe paths,
   current dependencies and the exact reviewed draft, repeats game validation,
   atomically publishes without clobbering and verifies the reopened hash.
   External dependency changes revoke current evidence and require revalidation.
5. Read the visibility confirmation: recipe files in the active directory are
   recursively loaded in new sessions. `known` defaults to true; false shows an
   unknown recipe and blocks the crafting UI's attempt. Truthy `_deprecated`
   hides a recipe from that UI. A published recipe is active content, not an inert
   draft. This does not add a learning route or promise personal-save compatibility.
6. **Test requirements → Validate and test exact recipe** also works on the
   unchanged reopened recipe. The same exact-byte validation runs three presets:
   candidate inventory plus ambient, no physical inputs, and no ambient sources.
   A preset is not guaranteed eligible: inspect the actual production verdict.
   Inputs are synthetic physical instances created from current item definitions;
   ambient records are synthetic and separate. The receipt records instance IDs,
   tags, source identity, selected material/tool instances, missing amounts,
   factory output and before/after inventory. The real `plan_craft`, `ItemFactory`
   and `commit_craft`/`exchange` execute on a disposable inventory with an explicit
   capacity. Ordinary player controls, knowledge gate, acquisition, equipment use,
   world placement, turns and saves are not executed. A `known:false` fixture can
   satisfy material rules while the real crafting UI still refuses that recipe.

The game-owned `immediate-components-1` capability requires one non-deprecated
immediate `result_item` object with a nonempty `components` array. Optional tools
and ambient arrays are supported. Passive work, world/tile placement, conjunctions,
legacy processing fields and array-of-recipe sources remain source-navigable and
read-only. The other current immediate recipes contain excluded conjunction or
legacy fields; their execution class alone is not writing entitlement. Changing
an ID/category or raw flags cannot promote an unsupported source token.

Authoring bounds: nonnegative exact-integer tiers through `2^53−1`, quantities
1–32, at most 64 rows per array and 64 physical slots in total. These are explicit
Workbench bounds, not new gameplay rules. Ambient quantities are ignored by the
consumer and receive a warning. Categories use current catalogue strings; the
game groups unrecognized categories under its existing other-category heading.
No recipe loader, allocation, visibility, campaign or learning policy was changed.
Native samples are published only in ignored disposable content. The example in
`docs/examples/` is not installed into the active game catalogue.

## Author a component item and trace its use

1. Search the recursive item catalogue by ID, name or path, or follow **Open item
   `<id>`** from a pool entry. Category filters use the declared game category.
   One structure, pool and item draft can remain open independently. **Return to
   pool** restores the original entry and its draft; **Show structure** restores
   the structure. Changing the item name never changes its machine ID.
2. **Begin edit** is available only for a unique, single-object ordinary inert
   component under `roguelike/data/items/components/` (including safe nested
   folders). The current four are `wood_bundle`, `flint_shard`, `clay_lump` and
   `clay_pot`. Typed fields are `name`, `description`, `weight`, `stackable` and
   `keywords`. Name/description are literal authored text. Weight is finite and
   nonnegative, in kg per instance. `stackable` groups same-ID inventory display
   rows; it does not merge ownership or multiply an instance's weight. There is
   no editable stack-size field.
3. Keywords use current `data/keywords.json` tag IDs. Tier is a nonnegative integer
   from the game's persisted-instance rules, limited to `2^53−1` for exact editor
   transport. Factory defaults are not serialized on open. Source, typed edits,
   undo/redo, validation and diff use one exact text draft. **Undo item** operates
   on item property/keyword operations; a raw or variant-ID change clears that
   history. Invalid raw JSON remains intact and disables typed controls.
4. Choose **Save as new variant**, enter a unique ID, review the derived path
   beside the source, **Validate draft**, inspect **Diff**, then **Review & apply
   → Confirm apply one file**. The host reruns the exact staged bytes through
   `DataLoader`, the game-owned `engine.item_authoring` component capability,
   `save_components` field validators, reference checks and `ItemFactory.create`.
   Publication rechecks source/dependency identity, uses the existing single-file
   atomic transaction and reopens the persisted bytes. Duplicate IDs (including
   case collisions), skipped definitions and unsafe paths cannot authorize writes.
5. Return to the retained pool draft. Deliberately select the new item ID, choose
   a **new pool variant** ID, validate/diff/confirm and reopen it. Neither item
   publication nor pool publication rewrites existing references. These are two
   independent transactions; a successful item may remain unreferenced if the
   later pool operation fails.
6. **References** lists saved contextual-pool references and declared tile, text
   and keyword IDs. Recipe rows are **potential tag matches**, using the actual
   crafting predicates; they do not establish quantities, recipe knowledge,
   materials, ambient conditions or successful crafting. **Use binding** follows
   the actual `ItemSystem.use` dynamic handler lookup. `Handler found` establishes
   code support only; inventory ownership, lazy equipment repair, handler
   prerequisites and normal turn conditions are not executed.
7. **Factory result** is separate observed evidence: an unowned real instance,
   declared/property comparison, exact definition hash, input and loaded-catalogue
   hashes, game source identity and UTC observation time. An edited draft hides
   old factory results until revalidated. Advanced item inspection can instantiate
   a valid definition without claiming its use/equipment/effects work. A linked
   structure's **Preview draft** can additionally observe actual seeded container
   population. That fixture does not certify world selection or acquisition.

Weapons, lights, satchels, effect-bearing consumables, array-of-item files and
unknown/legacy categories remain readable as source, with no publication control.
Category, appearance, use handlers, qualities, effects and movesets have no typed
editor. Unknown metadata and nested content are preserved. The game loader remains
permissive/last-wins; Workbench reports both collision paths instead of choosing a
winner. Refresh/reload after external dependency changes; apply always revalidates.

Source-verified limits: `on_use_effects` is not consumed by `ItemFactory` or
`ItemSystem` (including the shipped tincture's `drink` path). `consumed_on_use`
governs automatic crafting-material eligibility, not every use-handler return.
`gather_from` and a hypothetical `stack_size` have no current item consumer;
neither is promoted to a control. Weapon/equipment definitions can be read by
later systems even when fields are absent from the basic factory instance.
Tile references use the actual `TileRegistry` ID list; graphical sprite rendering
is not exercised by item validation. The adapter is read-only and is not imported
by the gameplay path. It neither changes item creation semantics nor opens saves.

## Author a container's loot pool

1. Open an ordinary building, select a direct container on the canvas or in
   **Placed record**, then use **Open pool `<id>`**. This opens the reference
   actually declared in the draft. Apply pending container-field edits first.
   The building's unsaved draft stays in memory. Pools can also be searched by
   ID, description or path in the content browser.
2. **Begin edit** enables the table. Item selectors use the current game item
   catalogue. **Inspect `<item_id>`** shows the actual file path, array pointer
   when applicable, name and complete declared fields, read-only. The source
   trail records the originating structure/container and its declared pool ID.
   It does not claim that a newly saved pool has been assigned to that container.
3. Edit **Item ID**, **Weight**, or inclusive minimum/maximum **Roll count**.
   **Add entry** and **Remove** preserve remaining entry order. Table and Source
   share one text-preserving draft. Invalid JSON freezes table mutation.
   **Undo table / Redo table** apply to table edits; raw/property/variant-ID edits
   clear that history and retain their own text undo.
4. Choose **Save as new variant**, enter a unique ID, **Validate draft**, inspect
   **Diff**, then **Review & apply → Confirm apply one file**. The host repeats
   validation with current dependencies and compares source bytes before
   publishing and reopening. The original pool stays unchanged. A pool with no
   direct-container references is potentially unused.
5. **Return to structure** restores the retained draft. Create a separate new
   building variant, explicitly choose the saved pool in **Loot pool 1**, and
   **Apply container edit**. **Preview draft** runs the exact building through
   the actual stamper, `scene_generation.populate`, loot roller and item factory.
   The receipt records seed, source hashes and created contents. Review, apply
   and reopen the building variant separately.
6. These are two single-file transactions. If building publication fails, the
   pool remains valid and may be unused. Correct the building or return to the
   pool. No selection profile, existing structure or campaign is reassigned.
   **Reload pool** reopens external changes after the usual discard prompt.

Only immediate `roguelike/data/loot_pools/<safe-id>.json` single-object definitions
are writable in this family (17 at the W3A baseline; 79 loaded item IDs).
`data/loot/` is a different legacy family. Nested/array-of-pools files,
advanced item/recipe editing and a general relationship graph remain unsupported.

| Supported field | Current authoritative behavior |
| --- | --- |
| `id` | Unique nonempty string; variants require safe filename characters. Existing IDs cannot be renamed in place. |
| `description` | Retained metadata; authored prose is preserved. |
| `items` | Ordered array, default `[]`; empty means no loot. Rows require a resolvable `item_id`. Repeated item IDs remain separate entries. |
| `items[n].weight` | Finite nonnegative relative weight, default `1`; nonempty rows require positive finite total weight. No drop percentages. |
| `roll_count` | One or two ascending nonnegative integers, maximum `2^53−1`, default `[1,1]`. One value means a fixed count. The table writes two bounds when edited. |

The existing game `Validator.pool` owns the rules. The worker additionally checks
that `DataLoader` loaded the exact definition and that pool/item source IDs are
unambiguous. The production pool loader does not accept a UTF-8 BOM: inspection
preserves it, but publication fails rather than silently dropping it. Unknown
fields remain intact with inactive-field diagnostics. Quantity, conditions and
text binding are not consumed by this roller.

`roll_pool` draws without replacement **by entry**, caps count to entry count,
and stops when remaining total weight is zero. Multiple pool references roll
independently. Displayed defaults are not written on open. Source links are
declared references; draft verdicts establish consumer acceptance; only the
structure preview establishes observed population. Samples do not establish
frequencies, effect behavior or natural world selection. Item/reference lists
are catalogue snapshots; reopen after external dependency edits.

The host retains one building, pool, item, recipe and creature capability. Saving any revokes
all reviews; the frontend clears verdicts while retaining the other drafts.
Every apply remains one reviewed byte string and one confined target, with fresh
validation, conflicts and rollback. No general filesystem permission, new write
endpoint or multi-file transaction was added.

## Author one building

1. Open the current checkout. It starts read-only and retains W0's actual
   `starting_lab` 80 × 43 production preview.
2. Search by ID, description/name or relative path, optionally filter by folder.
   All immediate `data/buildings/<category>/*.json` ordinary buildings appear
   deterministically (58 at the W1 source baseline). Plazas are listed as
   unsupported/read-only; authored layouts retain W0 read-only inspection.
3. Select a building such as `commercial/apothecary_a.json`. Source, properties,
   diagnostics, file hash, source revision and worker compatibility are visible.
   **Begin edit** opts into one in-memory draft. The **Authored layout** shows
   native terrain glyphs, decor dots and placed-record markers. Select the active
   layer, search its palette, and use Pencil or Fill. Description, scalar fields
   and visual operations use text-span edits; **Source** exposes the same strict JSON.
4. Select an existing container marker or choose it under **Placed records**.
   Change its X/Y, choose an actual container decor ID, and add/remove existing
   loot-pool references. **Apply container edit** stages one undoable operation.
   The checked option moves matching container access targets with the record;
   the diff exposes these explicit companion edits. Other special types remain
   inspect-only, including their nested alternatives and unknown fields.
5. **Preview draft** or **Validate draft** runs `read_document`, `DataLoader`,
   `compile_structure`, the production building stamper and population factories
   against disposable current data. Problems distinguish syntax, references,
   physical placement and game access failures. **Locate cell / record** navigates
   diagnostics with source coordinates. Failed or stale output clears the draft
   preview and cannot authorize apply. The preview's receipt identifies exact
   draft bytes, dependencies, worker/game source, seed and actual created objects.
6. Inspect **Diff**, then **Review & apply**. The confirmation repeats the exact
   diff and warns about existing world references. The host revalidates the exact
   stored bytes with fresh dependencies before publishing one file. The receipt
   records target, before/after hashes and existing/variant outcome. The index,
   editor and preview reopen from disk.
7. Prefer **Save as new variant** for identity or meaning changes. Enter a unique
   ID using letters, digits, `_` or `-`; this updates the draft's ID and derives
   `<same category>/<id>.json`. Existing IDs cannot be renamed in place. Current
   town/roadside selection profiles are **not** modified or populated by saving.
   Legacy flat-pool generation can discover added files; creating a variant does
   not establish that current planned generation will select it.

Opening, switching tabs and closing clean source never serializes it. Property
edits retain unrelated spans, BOM and line endings; raw edits retain the source's
CRLF convention. Unknown fields, nested arrays, specials, decor and text bindings
remain in the one shared draft. Discard/Revert returns to the opened bytes;
Generate/refresh reloads disk. Switching files/projects, refresh and native close
protect unsaved drafts with an explicit discard prompt. Drafts are memory-only;
forced process termination loses unsaved edits, while source stays intact.

A three-second idle check reports external changes and exposes the disk version
without replacing the draft. Apply always compares bytes again, independently of
that check. There is no forced save or automatic merge. Keep the draft for manual
reconciliation, or discard/reload the external version.

There are three explicitly different views: **Authored layout** is the exact
source representation; **Draft production preview** is the current validated
unsaved draft; **Saved production preview** is the opened disk snapshot. W0's
starting laboratory retains its independent authentic 80 × 43 generated scene.
All production views are revealed semantic renderings, not player FOV or Pygame
sprite fidelity. Terrain/decor colors and record markers explain layers; they
do not create gameplay rules.

Draft checks stamp the ordinary building, centered without rotation into an
80 × 43 grass test scene, then call `engine.scene_generation.populate`. Actual
container contents come from the game's loot roller and item factory. With a
required declared entrance, existing `structure_preview.check_access` verifies
required placement targets and every directly editable container from one cell
outside the main entrance. These are static game reach/interaction checks with
revealed visibility. Buildings without a required entrance explicitly report
access unverified. No natural selection, all-transform placement, simulation or
balance certification is implied. Failed physical placement/access blocks saving.

## Canvas controls and preservation

- **V** selects/inspects; **B** pencils; **R** fills a dragged rectangle;
  **E** erases; **H**, Alt-drag or middle-drag pans. Wheel zooms; Home fits.
- Layer checkboxes independently show terrain, decor and placed records.
  Painting a hidden active layer is disabled. Coordinates are zero-based X/Y.
- Terrain uses only existing legend glyphs. Null-mapped glyphs leave the
  underlying test-context terrain intact; they do not mean floor. Weighted glyphs
  retain their native weights and resolve only in production preview.
- Decor uses the current dependency catalog. Erase writes `null`; terrain erase
  requires an existing null-mapped glyph. A missing decor grid is created only
  when explicitly painting its first cell. Current `g2-2` accepts nested row
  arrays with string/null cells. Historical array/object **cells** are preserved
  in Source and freeze visual mutation; they are never stringified or flattened.
- **Undo canvas / Redo canvas**, or Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y with canvas
  focus, undo a whole drag, fill or container edit. Text inputs keep their own
  undo. Any raw/property/variant-ID edit clears the canvas history explicitly.
  History holds up to 100 visual operations and is not persisted across sessions.
- Invalid JSON, unsupported native shapes and disk conflicts freeze painting.
  Correct Source or discard/reload; the canvas never overwrites an invalid draft
  with an older snapshot. Unknown metadata and unrelated source spans survive.
- Validation is asynchronous; newer edits supersede responses. Use **Cancel
  authoring request** to terminate a preview worker. Publication itself cannot
  be interrupted halfway through the trusted host transaction.

The complete [W2 demonstrated variant](docs/examples/apothecary_w2_furnished.json)
is a review artifact outside the live content catalog. It was created/reopened
through the native app on disposable current data. Its terrain changes at
(2..4,3), herbs at (3..4,2), and crate moved from (1,1) to (2,1) are described in
[W2 delivery](docs/W2_DELIVERY.md). Its pool is the existing `workshop_b_fuel`;
no pool definition or procedural membership was added.

## Launch

Windows x64 is verified. The release directory contains
`resonance-workbench.exe`, `bridge.py` and `python/`; **keep all three together**.
Double-click the executable. The NSIS package includes those same resources.
WebView2 Evergreen must already be installed; W0's installer does not download
it. This machine was verified with WebView2 155.0.4283.62.

Choose **Choose repository**, or enter the directory and use **Open directory**.
Select this repository's root (the `roguelike/` subdirectory is also accepted).
The read-only authored layout list contains `starting_lab`, a 60 × 16 source
definition. It produces a full 80 × 43 authored scene through the game compiler,
scene builder, generator and population factories.

Hover/click to inspect terrain coordinates and IDs; drag to pan, scroll or use
the buttons to zoom, and press Home to fit. Arrow keys pan the focused canvas.
**Generate / refresh** reloads source and uses the entered seed.
**Test invalid disposable fixture** runs the same validator on a temporary copy
with a deliberately incorrect width. **Cancel** terminates the active worker.
Authored-layout Source JSON remains read-only; ordinary buildings expose the W1 workflow above.

## Windows launch and project settings

This workstation is preconfigured for `G:\GameDev\RoguelikeProject`. Open
**Launch Workbench.vbs** in this folder (or the corrected desktop shortcut).
The application selects the checkout, verifies the bundled Python/bridge and
protocol 7 capabilities, opens the content browser and generates the initial
production preview. No source chooser, Python installation or environment
variable is needed. Installed NSIS distributions use their installed application
shortcut; installed-shortcut and clean-machine WebView2 provisioning are untested.

A valid saved project wins; otherwise Workbench checks the running application's
checkout, then the optional workstation fallback in `owner-defaults.json`.
Every candidate must contain game/Workbench markers and the current data layout;
the worker verifies its current game imports and capabilities before authoring.
The interpreter environment is never treated as a source checkout.

**Change Project** deliberately selects another complete checkout. **Repository
directory / Open directory** also accepts a path. Successful choices are saved
atomically in `%APPDATA%\com.resonance.workbench\project.json`, outside the game
and its saves, and survive restarts/updates. Missing or corrupt preferences are
reported and replaced only after a validated fallback handshake. If no valid
project exists, the error names the checked path and Change Project remains
available. Existing unsaved-draft discard/keep controls apply before switching;
document/review tokens are never carried across roots.

The sidebar shows source root/revision, worker mode and protocol. **Runtime &
source identity** includes Python/bridge paths, capability versions and selection
origin. A raw `target/release/deps` executable is unsupported and says so. Keep
`resonance-workbench.exe`, `bridge.py` and the complete `python/` directory together
when distributing a portable app. The initial working directory does not matter.

Ordinary release launches always use the bundled worker. A stale
`RESONANCE_PYTHON` is visibly ignored; deliberate developer overrides require
`--diagnostic-runtime` (or a development build) and must be absolute existing
paths. No interpreter path is accepted from frontend IPC or project preferences.
Diagnostic settings isolation uses the process-only
`RESONANCE_WORKBENCH_CONFIG_DIR`; normal launches use the per-user location above.

## Development and builds

Requirements: Windows x64, Node **24.x** (tested 24.15.0), npm (tested 11.12.1),
Rust/MSVC **1.95.0**, Visual Studio 2022 C++ tools/Windows SDK, and WebView2.
CPython **3.11** with exact root `requirements-baseline.txt` dependencies is the
development runtime. `npm.cmd run dev` uses the existing pinned environment in
`owner-defaults.json`, falling back to prepared `worker/runtime` if that
interpreter is absent. The real development bridge imports the selected current
game. A deliberate `RESONANCE_PYTHON` override receives the same runtime checks.

From `workbench/` in PowerShell:

```powershell
npm.cmd ci
npm.cmd run dev
# First-time build preparation downloads checked Python and wheels:
.\scripts\prepare-runtime.ps1 -Python 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
npm.cmd run build                    # executable + complete resources
npm.cmd run bundle                   # same app plus NSIS installer
npm.cmd run test:startup             # isolated native startup/restart scenarios
```

Production builds verify Python 3.11.0, every pinned dependency and native imports
before compiling. Missing/incomplete runtime preparation fails the build; owners
of a complete distribution do not run the preparation script. Both Tauri config
routes include the runtime. Outputs are
`src-tauri/target/release/resonance-workbench.exe`, `bridge.py`, `python/`, and
`src-tauri/target/release/bundle/nsis/Resonance Workbench_0.7.1_x64-setup.exe`.
The startup runner requires this release bundle, a current debug build
(`cargo build --locked --manifest-path src-tauri/Cargo.toml`), and the test-only
fault worker (`rustc scripts/fault-worker.rs -o .artifacts/fault-worker.exe`).
It creates only ignored disposable data/config/binary artifacts and controls its
own native windows with local CDP events. See [W4B delivery](docs/W4B_DELIVERY.md).

The Python archive and wheel hashes are checked during preparation. npm and
Cargo lockfiles pin transitive dependencies. `rust-toolchain.toml` fixes the
compiler. Rebuild downloads require connectivity; **application use is offline**.
The package imports game Python from the chosen source tree and does not freeze
an old copy of game rules. CPython and wheel licenses remain in the runtime.
Native numeric thread pools are capped at one for this small preview; the
initial default OpenBLAS pool reserved substantial memory without helping W0.
Git is optional at runtime: without it, source/catalog hashes remain available
and the Git revision/working-tree status is explicitly unavailable.

## Verification

```powershell
npm.cmd run build:web                # also typechecks; needed for cargo tests
npm.cmd test
cargo test --locked --manifest-path src-tauri/Cargo.toml
cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings
& $env:RESONANCE_PYTHON -B worker/test_bridge.py
& $env:RESONANCE_PYTHON -B scripts/render-reference.py
npm.cmd run test:desktop             # built RELEASE executable; real WebView2
npm.cmd run test:authoring           # disposable data + native apply/reopen/restart journey
npm.cmd run test:visual              # native canvas + exact draft preview + variant/reopen
npm.cmd run test:pools               # native container → pool → item and two variants
npm.cmd run test:items               # native new item → new pool → real factory/population
npm.cmd run test:recipes             # native item → recipe → variant → production requirements/output
npm.cmd run test:creatures           # native creature → variant → real factory; five parked drafts
& $env:RESONANCE_PYTHON -B worker/test_authoring.py
& $env:RESONANCE_PYTHON -B worker/test_visual.py
& $env:RESONANCE_PYTHON -B worker/test_pools.py
& $env:RESONANCE_PYTHON -B worker/test_items.py
& $env:RESONANCE_PYTHON -B worker/test_recipes.py
& $env:RESONANCE_PYTHON -B worker/test_creatures.py
```

`scripts/desktop-test.mjs` opens a test-owned native window and sends app-local
DOM events through WebView2 CDP. It tests with the WebView network offline,
captures screenshots and measures startup, panning frames and process memory.
No owner's desktop input is driven. The test-only CDP port is 9333; normal
launches expose no debug server. Results/profile files stay in `.artifacts/`.

To test the development window, keep `npm run dev` running, set
`WORKBENCH_TEST_MODE=development` and `WORKBENCH_EXE` to the absolute
`src-tauri/target/debug/resonance-workbench.exe` path, then run `test:desktop`.
For the release fault controls, compile the deliberately broken test helper:

```powershell
rustc scripts/fault-worker.rs -o .artifacts/fault-worker.exe
$env:WORKBENCH_TEST_MODE = 'protocol-mismatch' # also malformed-worker, worker-exit, slow-worker, missing-worker
npm.cmd run test:desktop
Remove-Item Env:WORKBENCH_TEST_MODE
```

The helper is excluded from every package; it provides only negative evidence.
Modes `draft-worker-exit`, `draft-worker-timeout` and `draft-worker-cancel`
first open a real building and unsaved draft, then fail only its production
preview. The timeout mode exercises the host's actual 90-second deadline.
`missing-dependency` additionally takes `WORKBENCH_EMPTY_PYTHON`, a disposable
CPython runtime without the game dependency wheels.

## Contract and limits

The protocol is **7**, worker/app **0.7.0**, game structure contract **g2-2**,
item contract **component-1**, recipe contract **immediate-components-1**, and
creature contract **revenant-hp-1**.
W0 identify/describe/inspect/preview requests remain read-only. Draft validation
is available only through the host's document boundary. Discovery grants an
opaque document token; validation grants a one-draft review token. Apply takes
that token and explicit confirmation, never an arbitrary destination or trusted
frontend verdict. W2's validation token is issued only after the exact draft's
production preview passes; apply repeats that check with the reviewed seed and
fresh dependencies. Starting replacement validation revokes an older review even
if the new worker fails or is cancelled. Variants stay beside the discovered source,
in its building category, immediate loot_pools directory or supported component folder.
There are no frontend filesystem/shell permissions, arbitrary Python evaluation
or Git mutations. The only frontend capabilities are local close-event listening.

The Rust host validates allowed path components, canonical containment and
reparse-point rejection again at publication. Windows directory handles prevent
parent moves; dependency read handles deny concurrent writes/renames during the
final validation. A separate source read lock covers validation, then releases
for replacement. The host compares current bytes immediately before publishing
and the actual displaced backup bytes afterward, restoring an intervening
external version on conflict. Input hashes/file membership are also rechecked.

An existing-file apply writes and flushes a sibling `.w1-stage-*.tmp`, closes its
write handle, then uses Windows `ReplaceFileW` with a uniquely named sibling
backup. Windows preserves supported original metadata, including creation time
and ACLs. A verified failure restores the backup; ordinary failures clean the
staging files. If recovery/cleanup is blocked, the error identifies the retained
backup and the idle disk check lists `.w1-*` remnants. Inspect those files before
manual recovery; Workbench never silently restores an ambiguous crash remnant.
Variants use no-clobber persistence. Exact published bytes are checked. This is
not a guarantee against arbitrary power loss, faulty storage or every Windows
filesystem. Existing-file replacement is Windows-only; other platforms remain unverified.

The worker writes only disposable scratch data, denies personal-save reads,
imports rules from the selected checkout and suppresses bytecode. Cancellation,
project replacement and close reap active workers and clean their temporary
roots. **Open trusted game checkouts:** Python audit hooks prevent incidental
writes; they are not an OS sandbox against hostile Python/native libraries.

The canonical loader validates the complete structure catalog. A broken unrelated
catalog definition can block applying a draft until it is repaired. Discovery
and raw source inspection remain available when the loader reports structural
errors. Files over 1 MiB and unsafe destination names are outside W1 authoring.
Other-family visual editing, special creation/deletion, new legend definitions,
transform tools, other loot families, selection-profile changes, persistent edit history
and automatic campaign migration remain outside W4A. Deferred physical specials
are visible and preserved, but block a successful draft preview with an explicit
unsupported diagnostic. Other live special types are inspect-only on the canvas.

The semantic Pixi rendering shows actual terrain, initial objects and arrival;
colors/markers differ from the Pygame renderer. Inspection is revealed, without
player FOV, simulation, balance analysis or a natural-world selection claim.
The seed, exact large scene seed (string), catalog/source hashes and context
identify a repeatable controlled preview; this is not global gameplay replay.
Refresh after external source/dependency changes. The palette represents the
catalog at open time; every validation and apply rereads current dependencies.
A generic schema registry and further W milestones remain separate work.

See [W3C delivery and evidence](docs/W3C_DELIVERY.md), [W3B delivery and evidence](docs/W3B_DELIVERY.md), [W3A delivery and evidence](docs/W3A_DELIVERY.md), [W2 delivery and evidence](docs/W2_DELIVERY.md), [W1 delivery](docs/W1_DELIVERY.md)
and the unchanged historical [W0 delivery](docs/W0_DELIVERY.md).
