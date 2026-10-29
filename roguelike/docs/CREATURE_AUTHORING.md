# Creature and harvest authoring · W5N

Workbench's `creature-harvest-2` adapter supports the twelve current Actor
definitions under `data/entities/creatures/`. Open a source, inspect its body,
binding and references, then **Begin edit**. The exact Source, typed controls,
Undo/Redo, validation, Diff, recovery and reviewed publication share one document.
Several creatures and other registered families can remain open independently.

| Source | Operations |
| --- | --- |
| drowned_revenant, grave_thing, heath_stalker, highland_bandit, hollow_revenant, sewer_thing | Same-ID edit; new-ID variant |
| barrow_wight, bog_wraith, briar_lurker, hollow_knight, plague_crow, stone_lurker | Same-ID edit; special binding retained |
| vine_network | Inspect-only configuration for the vine consumer |
| Player, NPC, unsupported or ambiguous shapes | Read-only inspection with specific limits |

Special duplication is unavailable because `ABILITY_REGISTRY` dispatches by
stable creature ID. A copied tile does not give a new ID that behavior. Same-ID
edits fix ID, file, tile, AI class, body and special settings. An ordinary new-ID
variant may select an existing `wandering`, `ambush`, `fleeing` or `circling` AI.
Capability is checked against the original source and complete entity namespace;
raw edits or recovery metadata cannot grant additional operations.

## Common fields

These are explicit authoring bounds, preserving all shipped values, rather than
new game balance rules. Raw Source and restored drafts receive the same checks.

| Control / source | Bound and actual meaning |
| --- | --- |
| `name` | 1–256 literal characters; `Player` is reserved by save/render paths |
| `description` | 0–8,192 characters; Look uses the stable definition ID |
| Effective HP: `base_hp` + `fighter.max_hp` | One atomic edit; equal integers 1–1,000,000; new Fighter starts at this maximum |
| `armour_value` | Integer 0–1,000,000; effective natural armour |
| `damage_dice` | Strict lowercase `NdM`, count 1–20 and sides 1–100; no additive syntax |
| `damage_bonus` | Integer −1,000–1,000; separate attack addition |
| `attack_verb` | 1–256 literal characters; monster attack prose |
| `perception.sight_radius` | Integer 0–1,000; actual perception radius |
| `perception.sees_in_dark` | Boolean |
| `wander_radius` | Integer 0–1,000 |
| `pursuit_timeout` | Integer 0–10,000; active and off-map pursuit use this ID's definition |
| `speed` | Finite 0.01–2; the current scheduler supports at most two actions per turn |

Booleans are not numeric values; invalid types, non-finite numbers and invalid
dice are rejected without review authority. No clamping occurs. Localized source
edits retain untouched spacing, key order, escaping, missing fields and metadata.
HP is a deliberate two-field edit. Invalid JSON remains recoverable and freezes
typed controls until corrected.

`fighter.power` and `fighter.defense` remain visible legacy/fallback values.
Hearing is constructed/saved but has no active AI consumer. Current AI does not
call `Perception.is_hostile_to`; membership labels do not promise targeting, and
an empty hostility list defaults in the constructor. Bodies/limbs,
corpse data, essence, effects, ranged blocks, spawn declarations, transition
flags, callouts and unknown metadata remain exact and read-only.

## Body, references and construction

Barrow Wight's body is supplied by its three inline limbs. `combat.get_body_def`
prefers these over the implicit `body_human` fallback. That unused fallback is
informational; it requires no repair or new body definition. An explicit unused
`body_id` is distinguished from the absent/default field. An actually needed
missing or ambiguous body remains a blocking dependency error.

`spawn_zones` is retained inactive metadata with no current runtime Python
consumer. **References** separately shows saved authored-submap placements and
zone `creatures` entries with exact paths and fields. `spawn_for_zone` processes
zone entries in order, tests their chance, and observes its maximum count; it
does not consume their `weight`. These are declarations, not observed encounters
or proof of natural selection. Zone editing is outside this view. The canonical
barrow definition is `data/zones/dungeon/barrow.json`; the obsolete duplicate
`dungeon.json` has been removed without changing the canonical file.

**Factory result** calls the real `DataLoader` and `CreatureFactory.spawn` in
disposable data and reports Actor/Fighter/Perception/AI, stable ID, source hashes,
effective values and special binding. Safe read-only Actor sources can still be
constructed. Construction alone does not execute an ability or prove combat,
balance or natural encounters. Source/dependency changes invalidate the evidence.

## Publication and saved instances

Validate, inspect Diff, then **Review & apply → Confirm apply one file**. Ordinary
variants additionally use **Save as new variant** and a unique ID. Publication
binds original policy, exact reviewed bytes and dependencies; the host repeats
validation, writes one allowed file and verifies the reopened hash. New variants
stay beside their source under `data/entities/creatures/` and join no selector.
They can be deliberately selected in the existing authored-submap placement view.

Changes become available on the next game launch/catalogue initialization.
Workbench does not modify a running game's cached definitions. Restoration uses
the current definition and then reinstates stored component snapshots:

| Value | Previously saved actor after reload | Fresh actor |
| --- | --- | --- |
| Name, current/max HP, natural armour, saved sight/darkvision, wander radius | Retains stored instance values | Uses new constructor values |
| Description, attack dice/bonus/verb, speed, pursuit timeout | Reads current definition by stable ID | Reads current definition |
| ID, AI class, body structure, special binding | Preserved by same-ID policy | Preserved for same-ID edits; ordinary variants use the selected AI |

HP edits do not rescale injured saved actors. Older rows missing a snapshot field
retain existing factory-default fallback semantics. Sight edits do not redefine
the wight's separate fixed ability radius. The save format and restoration policy
are unchanged; no migration, respawn or personal-save rewrite occurs.

Accepted drafts checkpoint through shared recovery, including invalid JSON and
variant intent. Recovery performs fresh discovery and policy checks and restores
no review authority. Special variant intent is refused while keeping stored text
available. Saving one document does not retire another document's draft.

Sources: `engine/creature_authoring.py`, `engine/creature_factory.py`,
`engine/creature_abilities.py`, `engine/effect_lifecycle.py`, `engine/look_mode.py`,
`components/ai.py`, `engine/engine.py`, `engine/save_manager.py` and
`engine/save_components.py`. See [W5F delivery](../../workbench/docs/W5F_DELIVERY.md)
for source-bound verification and the controlled encounter/restore evidence.

## Remains and complete harvest tables

The **Harvest** tab uses the same exact Source, Undo/Redo, recovery and reviewed
single-file publication as common fields. Eleven original non-ephemeral Actors
admit harvest edits: nine existing tables plus Sewer Thing and Hollow Knight,
which can deliberately gain a table. Bog Wraith remains common-field editable
but cannot gain harvest authority; Vine Network is not an Actor. Admission is
structural, never an ID whitelist. Original `ephemeral` must be absent or exactly
false and the original profile absent or supported. Raw edits/recovery cannot
promote an unsupported original by deleting fields. Six ordinary sources retain
variants; special creatures retain same-ID edits only. Body/limbs, corpse sprites,
abilities, effects, spawn declarations and nested unknown metadata stay protected.

Add/remove the profile, choose default/timed/no decay, add/edit/reorder/remove
tiers and outputs. Defaults are displayed without inserting keys on open.
Metadata travels with exact source row spans and is read-only. Removing a whole
profile or row is deliberate. Save/reopen item dependencies before choosing them;
other dirty documents never overlay reference validation or Test room capture.

| Native declaration | Effective production rule / publication bound |
| --- | --- |
| Profile absent / `{}` | Free refusal. An otherwise non-ephemeral Actor still leaves a corpse. Whole-profile null is invalid. |
| `decay_turns` absent / null | 200 active-map ticks / no decay. Explicit integers 0–9007199254740991; zero/one expires at the next active tick. |
| `tiers` absent / `[]` in a nonempty profile | No qualifying tier: corpse retained, one paid turn, no extra harvest debt. Null is invalid. |
| `min_cutting_tier` absent | 1; explicit exact integer 0–32. Highest qualifying threshold wins, with first-row tie precedence. |
| `yields` absent / `[]` in the selected tier | Successful empty harvest: consumes this corpse at normal cost. Null is invalid. |
| `item_id` | One unique saved, case-unambiguous, factory-valid persisted item. Constructibility is distinct from permission to edit its behavior; otherwise valid reference-only items are included. Exact source paths appear in References and choices. |
| Quantities absent | Inclusive independent roll 0–1. Explicit min/max exact integers 0–32, effective min ≤ max, including omitted members. Repeated IDs stay separate rolls. |
| Aggregate work | At most 64 tiers, 64 outputs per tier and 64 possible physical outputs per tier (sum of effective maxima). |

Booleans, unsafe/nonfinite numbers and malformed/null records are rejected before
review. These are bounded publication/execution rules, not shipped-balance edits.
`engine/harvesting.py` owns validation, defaults, selection, copied cutting
keywords and the runtime transaction. The editor does not calculate a second
harvesting model. Factory Actor/item construction is unowned evidence and does
not establish defeat, death finalization, ownership, butchery or usable output.

## Ordinary butchery, decay and save activation

Pickup and both interaction-cursor routes pass the actual corpse instance.
Commitment rechecks reachable floor ownership and prompt scene/address. Same-ID
siblings remain distinct; stale selection never chooses a substitute. Legacy
coordinate-only dispatch requires one unambiguous actual floor corpse; a décor
marker cannot supply one. Only exact inventory-owned, currently equipped weapon
or offhand objects supply their **copied instance** cutting keywords. Stale slots,
flags alone and current definition keywords cannot grant a cutter. Tools remain
owned and equipped after success. `bone_reader` qualifies all tiers independently
of a cutter, but does not maximize quantity rolls or change actual cutting tier.

Before consumption, the runtime validates the current profile and selected item
references, rolls bounded quantities and constructs distinct valid physical
outputs. It stages everything before floor publication and checks every placement.
Construction/placement failure, including a partial write, removes only that
attempt's publications, retains the exact corpse and all prior objects, charges
no action/debt and reports failure. Retry can produce one complete harvest. RNG
is not rewound. Success publishes all outputs, removes only the selected corpse,
reports actual quantities and pays once: `max(1, 5 - (actual tier - threshold))`.
The threshold cap bounds the bare-hands perk case to 37 turns. Ordinary turn/death
handling drains debt. A valid zero-roll result is still successful consumption.

| Boundary | Activation |
| --- | --- |
| Actor death | Current session definition controls corpse eligibility and initial decay; normal death records stable `source_creature`. |
| Existing saved corpse | Retains source ID, copied name and remaining `decay_timer`; catalogue changes never reset the timer or regenerate an Actor. |
| Butchery | Uses the current session's table through `source_creature`. An old corpse can use a revised table after fresh-catalogue restore. Removing the profile can make it unharvestable while retaining stored decay. |
| Existing tool / harvested item | Retains copied physical fields, keywords and existing dynamic references. Fresh construction uses current definitions. |
| Running game / Reset / latest saved | Running catalogue stays loaded. Reset reuses the immutable capture; latest saved makes a new capture from saved dependencies. |
| Scene / decay | Active-map floor ticking and saved ownership/depletion remain authoritative. No offscreen catch-up, extra processing-map corpse ticks or respawn is added. |

No save schema/migration, yield-table snapshot, natural spawn registration or
global transfer framework is introduced. See [W5N delivery](../../workbench/docs/W5N_DELIVERY.md)
for the capability inventory, controlled authored-room provenance and separate
ordinary-save fresh-catalogue proof.
