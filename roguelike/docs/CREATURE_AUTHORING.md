# Common creature authoring · W5F

Workbench's `creature-common-1` adapter supports the twelve current Actor
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
an empty hostility list defaults in the constructor. Bodies/limbs, harvest,
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
