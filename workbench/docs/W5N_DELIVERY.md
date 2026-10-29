# W5N — authored creature harvests

The existing registered creature family now authors complete native harvest
profiles alongside common Actor fields. An owner can publish a creature variant,
place it and an obtainable cutter in a furnished room, defeat it normally,
butcher its exact corpse, acquire its material, prepare and use the result, then
revise and retest with the stated save/catalogue boundaries. No live content
pack, starter redistribution or natural encounter membership is installed.

## Revisions and preservation

| Boundary | Identity |
| --- | --- |
| Starting local and remote `main` | `838958de0f72054e573651cbc250e9ada8ebb8c0` |
| Named start | `checkpoint/workbench-w5n-start-20261029` |
| Implementation and application/package inputs | `9ab99d0befd922191c21e6d9f470545f85a42dbb` |
| Package inputs | `checkpoint/workbench-w5n-package-inputs-20261029` |
| Completed delivery | `checkpoint/workbench-w5n-verified-20261029` |

The [verification receipt](w5n-verification.json) binds application/package inputs,
working and committed source hashes, pinned runtime, exact accepted fixture bytes,
immutable captures, native observations and gates. Application inputs precede the
later harness/evidence commits. Git-normalized committed bytes and executed
working bytes have separate hashes. A commit cannot contain its own SHA; resolve
the final named ref. The final handoff and ignored `remote-readback.json` provide
the full exact local/remote-main match after the commissioned push.

Work stayed on production `main` without branches, worktrees or development copies.
Only disposable runtime/content/save fixtures were copied for verification.
The preservation inventory reports 8,353 unchanged pre-existing files and covers the pre-existing untracked owner plan and
tracked out-of-scope content, settings, fonts, launcher, campaigns and prior
artifacts. Wiki chapters/examples, standalone HTML and reference packs are
unchanged. W5M's delivery now explicitly corrects its unsupported furnishing
placement statement; historical fixtures are untouched and no reproduced editor
defect is claimed from that earlier attempt.

## Contract, permissions and consumption

`creature-harvest-2` remains the same registered creature family and shared
publication path. The [executable inventory](evidence/w5n/creature-inventory.json)
admits eleven original non-ephemeral Actor sources: nine existing tables plus
Sewer Thing and Hollow Knight. Six ordinary sources retain same-ID/variant
operations; identity-bound special sources retain same-ID editing. Bog Wraith
retains its previous common-field permissions but no harvest authority; Vine
Network is not an Actor. Counts are corpus observations, not an ID whitelist.

Entitlement uses the original source: `ephemeral` must be absent or exactly false
and the original profile absent or a supported native object. Raw Source,
recovery, deleted fields or renderer flags cannot promote an excluded source.
Bodies/limbs, corpse presentation, special identity, abilities/effects, spawn
metadata and unrelated fields remain protected. New records contain only the
supported harvest fields; retained unknown metadata is read-only and travels
with its source spans. Profile/row removal is deliberate.

The Harvest tab adds/removes profiles, selects omitted/timed/null decay, edits
thresholds and saved output references, and adds/removes/reorders nested records.
Existing exact-source primitives preserve key presence, order, CRLF/BOM, escaping
and untouched metadata. Shared history, recovery, validation, one-use review,
conflict refusal, rollback and byte-checked reopen remain in force. Multiple
creature documents and an independent dirty document coexist. Saved dependencies
alone supply validation and capture; parked drafts do not overlay them.

`engine/harvesting.py` owns the effective rules used by the renderer's descriptor,
worker and production consumer. TypeScript and Rust add no harvesting calculation.
See the [authoritative creature guide](../../roguelike/docs/CREATURE_AUTHORING.md)
for every default, numeric bound, effective range and persistence boundary.

* Missing/empty-object profile: free refusal. Nonempty profile without qualifying
  tiers: retained corpse, one paid turn, no extra debt. Whole-profile/list nulls
  and malformed records are invalid.
* Absent decay: 200 active-map ticks; null: no decay; explicit exact counts through
  `2^53-1`; zero/one expires on the next active decay tick.
* Highest qualifying threshold wins, with first-row ties and independent inclusive
  output rolls. Omitted threshold is 1; omitted quantities are 0/1. Explicit
  thresholds/quantities are 0–32. Effective minimum must not exceed maximum.
* At most 64 tiers, 64 outputs per tier and 64 possible physical outputs per tier.
  Repeated item IDs remain separate rows/rolls. Empty/zero-yield selected tiers
  successfully consume their corpse at the normal cost.
* Every output resolves to one saved, case-unambiguous, factory-valid persisted
  item. Exact source paths accompany reference evidence and choices. Otherwise
  valid items outside editable behavior classes remain selectable references.

Pickup and both cursor routes pass the selected corpse instance. Commitment
rechecks its reachable floor owner and captured scene/address. A stale selection
cannot harvest a same-ID sibling; coordinate-only legacy dispatch requires one
unambiguous real floor corpse and never invents one from décor. Only exact owned,
currently equipped weapon/offhand instances supply their copied cutting keywords.
A stale slot, equipped flag alone or revised definition keywords cannot grant a
cutter. The tool remains owned and equipped.

Validation and complete bounded construction precede publication. All rewards
are distinct valid physical objects. Every floor placement result is checked;
construction/placement exceptions and partial writes remove only this attempt's
publications. Failure retains the exact corpse, prior objects and existing move
debt, grants no reward/action/debt, and reports clearly. Retry yields one complete
harvest. Success removes only the selected corpse, reports actual quantities and
pays `max(1, 5 - (actual cutting tier - selected threshold))` once. `bone_reader`
qualifies all tiers but neither maximizes rolls nor changes the actual cutting
tier used for time. Threshold bounds cap its bare-hands case at 37 turns.
Ordinary death handling stops debt draining. RNG is never rewound or replaced by
this transaction.

## Packaged connected journey

The [observations](evidence/w5n/observations.json), reviewed diffs, screenshots and
five exact fixtures establish the controlled authored-room journey. Supported
controls publish a Sewer Thing variant with HP 4, natural armour 0, 1d1 damage,
zero damage bonus, speed .25 and wander radius 0. Its two tiers require effective
cutting 1/2 and yield inclusive 1–1/2–2 raw meat, with decay 500. A saved 2d6+3
cleaver carries copied cutting tier 2. These are disclosed authored encounter
parameters; no harness patches the encounter or manufactures its corpse.

Source supplies the 19×11 wall-bounded room geometry and ordinary return stair.
Room controls place the saved creature, obtainable cleaver and stationary unlit
campfire. Accepted room bytes and production population/furnishing state are
asserted before launch. This corrects W5M's attempted-click evidentiary gap.
The ordinary player profile and starter supplies remain unchanged; no raw meat
is present in the starting inventory or room floor.

Normal movement/pickup and inventory Enter acquire/equip the exact cleaver.
Ordinary attacks defeat the authored creature and production finalization creates
its stable-source corpse. Unequipping the cutter demonstrates a native one-turn
insufficient-tool refusal with the exact corpse retained. Re-equipping and normal
pickup interaction harvests two real meat objects at the established cost while
retaining the tool. Normal pickup acquires those exact identities.

Ordinary interaction lights the authored campfire. Existing `cook_meat` consumes
one physical ingredient whose identity came from the corpse, records normal
processing, completes to real `cooked_meat`, and supplies it through ordinary
pickup. Inventory Enter consumes that result and improves hunger. No replacement
ingredient, heat/needs fixture, slot injection, health patch, scripted death or
RNG override is used in this native journey.

Save, leave/return and a separate pinned `--load` process retain inventory and
slot-row ownership, the remaining raw material and exact cutter, consumed food,
removed corpse, depleted creature/tool placements and persistent lit furnishing.
There is no respawn or duplicate reward. Workbench then revises the same creature
to decay 900 and animal-bone outputs of 1/3 at thresholds 1/2, and revises the
cleaver's copied keyword definition to tier 1. Reset reuses the original immutable
capture and yields two meat with its old tier-2 tool/500-decay definition. Latest
saved captures revised inputs; a fresh defeat/harvest yields one bone using the
new tier-1 tool and revised initial decay. This is a small retest, not another
preparation expedition.

## Separate ordinary fresh-catalogue proof

Before revision, a distinct disposable ordinary save enters the exact UI-published
room through production descent, normally acquires/equips its cleaver and retains
an unbutchered corpse from production finalization. This headless fixture explicitly
calls death finalization; it is separate from the native ordinary-attack defeat.
Source identity, copied corpse name/timer, copied tool fields, ownership and scene
are recorded before save.

A separate process/catalogue loads that ordinary save after the UI revisions.
The old corpse retains source/name/remaining countdown and the exact owned old
tool retains copied tier 2 while its current definition/fresh construction has
tier 1. Ordinary keyboard butchery selects the revised threshold-2 table and
produces three distinct bones at five turns. It conserves unrelated scene state,
retains the tool, removes the exact corpse and refuses stale repeat harvest.
No Actor is regenerated from the depleted placement. A distinct fresh production
finalization initializes decay 900, followed by an accounted ordinary tick to 899.
Focused tests additionally cover absent-profile removal and no-decay restoration.
No yield table is copied into saves and no migration/schema change is introduced.

## Verification and limits

[Gates](evidence/w5n/gates.json) record Windows commands, environments and log
hashes: 77 frontend tests, TypeScript, 68 Rust tests, clippy with warnings denied,
124 game regressions plus the final nine focused consumer cases, 98 worker cases (one expected embedded-runtime skip), a
separate missing-dependency control, locked executable/NSIS packaging, the native
connected journey, shared workspace and room-session lifecycle, and ordinary
128×128 main/default save-load. Focused cases test source/raw bypasses, numeric
and aggregate bounds, defaults/null/empty distinctions, ties/repeated rows,
metadata/history/recovery, exact selection/ownership, copied cutting tiers,
`bone_reader`, debt/death, zero rewards, missing/invalid outputs, late construction,
placement false, partial-write exceptions/false, conservation and clean retry.

Early harness publication-selector, BUSY admission, textarea CRLF-versus-DOM
comparisons and newline-sensitive invalid-fixture construction were corrected
without changing application bytes. The cold-run harness also clears its previous
quit control file before launch to prevent replaying an old Escape event.
Removing only a terminal CRLF leaves valid
JSON; the final invalid fixture deliberately removes the root closing delimiter. Exact recovery is checked in stored
recovery bytes while the textarea follows its native normalized display. An early
concurrent shared-workspace scroll assertion is excluded from final gates; its
isolated rerun supplies the completed lifecycle result. Only passing final runs
count as completion evidence. The [compact correction record](evidence/w5n/harness-corrections.json)
binds the excluded local receipts without replacing accepted fixtures.

This is one controlled authored-room connection, not unaided discovery, survival
balance, natural selection or every-ability evidence. Factory observations remain
unowned construction facts. Current-session tables, saved copied physical fields,
unchanged-capture restoration, ordinary fresh-catalogue restoration and fresh death
are verified separately. Active-map decay and existing saved scene depletion remain
unchanged; no offscreen catch-up, processing-map corpse ticking, new loot/salvage,
perk redesign, surface migration, global transfer framework or wiki upkeep is
included.
