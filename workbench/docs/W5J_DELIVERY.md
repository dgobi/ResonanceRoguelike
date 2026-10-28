# W5J — author usable supplies

Materials, food, drinks and treatment now use the existing registered item
document, exact-source publication and captured room-test workflow. The packaged
Windows journey saves five authored definitions, places eight objects, acquires
and uses selected instances, revises definitions, and exercises reset/latest and
separate-process ordinary persistence. No demonstration definitions or changed
player needs are installed in live content.

## Source and package boundaries

| Boundary | Identity |
| --- | --- |
| Reviewed, initial local and remote main | `9068855894c2ce53e4617dd0f5f696fbab0bbb4a` |
| Preserved start | `checkpoint/workbench-w5j-start-20261028` |
| Supplies implementation and both repairs | `d36f6231c1eaa51b8bd4d620b5439a46a5499a58` |
| Final Windows package inputs | `d71e27a4586b370f9f894fcca142e64b6d32f34e` |
| Journey, compatibility and evidence scripts | `16eb79f` |
| Final verified delivery | `checkpoint/workbench-w5j-verified-20261028`; exact local/remote readback in the handoff |

[Machine receipt](w5j-verification.json) binds executable/NSIS, bundled runtime,
bridge, working and Git source hashes, gate logs, fixture inputs and screenshots.
Package identity precedes the later evidence/documentation commits. The final
commit resolves through the named Git ref and remote readback without a self-hash
loop. Work stayed directly on production `main`; no branches, worktrees or
additional development checkouts were created.

## Repaired behavior and supported contract

The **W5I regression** compared raw saved rooms to compiled definitions. Freshness
now compares raw/raw, compiled/compiled, source path and original byte hashes.
Both container defaults omitted, either omitted individually, and both explicit
pass room validation, picker admission, active assignment, ordinary new-world
generation and actual production room construction without source writes. A real
post-load edit and a whitespace-only byte change remain rejected. Protected,
ambiguous, missing/invalid and active/inactive policies retain their existing tests.

The **inherited inventory defect** cached a removed full drink after successful
exchange returned false. Membership changes now invalidate those rows before the
next redraw. Real-handler/offscreen redraw and packaged inventory input prove the
empty item appears while inventory stays open and the selected removed instance
cannot be reused. Existing handler returns, action costs, deferred confirmations,
failed treatment and exchange-before-hydration ordering are preserved.

`usable-supplies-1` narrowly versions the existing family. The executable
[79-source inventory](evidence/w5j/shipped-sources.json) admits exactly **42**:
30 materials (4 components, 18 butchery, 8 inert consumables), 9 foods, 2 drinks,
1 treatment. Each supports same-ID editing and deliberate new-ID variants.
Source rules determine admission; no item-ID whitelist or quota is used.

Original category/use identity is fixed; unsupported originals cannot be promoted
by Source, recovery or descriptors. The adapter owns class/field semantics, and
the host independently confines writes/recovery to the three supported routes.
Canonical `empty_water_skin` is reference-only; `resonant_tincture` retains its
inspectable inactive effect metadata. Equipment, lights, readable items, corpses,
special preparations and effects remain outside this contract.

Common controls include existing tiles, grouping, ordered keyword tiers and the
accurate **Eligible for automatic ingredient selection** label. Class controls
add actual doses/messages and constrained saved returns. Local edits retain
formatting, omitted defaults, explicit supported nulls and unknown nested metadata.
Validation rejects bad types, bool-as-number, nonfinite/negative values, unsafe
integers, invalid keywords/tiles/returns and explicit nonpositive treatment doses.
Return definitions and saved survival configuration stale applicable evidence.
Factory results distinguish absent declarations/defaults and are explicitly
**Unowned factory construction**. See the [authoritative supplies guide](../../roguelike/docs/ITEM_AUTHORING.md).

## Packaged authoring and ordinary use

All accepted item/room bytes were authored in the actual packaged application.
Typed controls set meaningful common and class properties; Source adds disclosed
unknown metadata and defines room geometry. Existing placement controls add every
saved item reference. No accepted definition was written externally as UI proof.
The real external-conflict injection is separately labelled and restored.

| Authored ID | Saved behavior |
| --- | --- |
| `w5j_material` | Cordwood, 0.25 kg, fuel tier 2; automatic material eligibility false, explicit matching selection true |
| `w5j_food_a` | Independent bitter-herb source; nutrition 0.35, authored message and grouping; two instances |
| `w5j_food_b` | Independent cooked-meat source; nutrition 180, authored message |
| `w5j_drink` | Hydration 0.25, authored message, canonical empty-skin return; two instances |
| `w5j_treatment` | Healing 7 HP; two instances |

App-local normal walking/pickup transfers all eight exact floor instances from
`w5j_supplies_room`. The disclosed once-only fixture establishes hunger/thirst
0.8 and HP 45/60. Ordinary needs, ownership, input, effects and turns then run.

| Selected use | Before → after | Action calls / turns |
| --- | --- | --- |
| Food A, fraction 0.35 | Hunger 0.800 → 0.451 | 1 / 1 |
| Food B, 180 / saved maximum 1000 | Hunger 0.451 → 0.272 | 1 / 1 |
| Drink, fraction 0.25 | Thirst 0.802750 → 0.554125 | 1 / 1 |
| Treatment, 7 HP | HP 45 → 52 | 1 / 1 |

Hunger rises 0.001 per turn; thirst rises 0.001375 with the actual plains
modifier. These account for the observed totals. Selected transient identities
are recorded; same-ID siblings remain owned. The return appears immediately in
the open inventory. Production material predicates operate on the acquired
cordwood; no new full crafting journey is claimed.

The native process also recovers an invalid supply after actual termination,
requires fresh validation, retains another dirty shared document, navigates to
the canonical return and back without losing the drink draft, and refuses a real
external change with `EXTERNAL_MODIFICATION_CONFLICT` while preserving its bytes.

## Revision and compatibility

Typed same-ID revisions change Food A to 0.6, drink hydration/message to 0.5/new
text, drink return to `w5j_material`, and that return's name/weight to revised
cordwood/0.4 kg. Save/reopen verifies exact bytes. Reset retains the original
capture manifest and doses; latest-saved creates a distinct manifest and revised
instances. Captured inputs are never modified in place.

A distinct ordinary-save fixture acquires all eight UI-authored supplies and
saves the room with removed floor objects. After those same-ID revisions, a new
pinned Python process initializes a fresh catalogue and cold-loads the save.
Stored inventory values/ownership and room terrain/floor state remain exact;
removed objects do not respawn. New construction uses revised definitions.

Specifically, the restored old drink retains hydration **0.25** and its original
message, while `empty_form` comes from the fresh session definition and constructs
the currently defined revised cordwood at **0.4 kg**. Its same-ID sibling remains
owned. The old acquired material remains 0.25 kg with its saved name. Explicit
disposable save access is audited. This ordinary compatibility fixture is separate
from W5H's immutable captures; no save schema or campaign migration changed.

## Verification, preservation and limits

Final gates: **68 frontend tests**, TypeScript, **68 Rust tests**, clippy with
warnings denied, **66 game tests**, **72 worker cases** (71 pass and the expected
embedded dependency-absence skip), plus the separate successful negative control.
Windows locked NSIS packaging, packaged shared workspace, packaged W5H
capture/reset/cold-load/lifecycle, and ordinary 128×128 startup/default disposable
save/load are exercised. Windows room tests use pinned Python 3.11 and all six
pinned packages. Broader game cold-child regressions use the configured development
environment and explicit `PYTHONPATH`; receipt commands distinguish these routes.

The receipt retains meaningful early failures/corrections: a worker result staled
by concurrent source editing, wrong test-module/embedded-child import setup,
native harness revert/apply-label timing, transient identity comparison across
F9/cold restoration, and an optional standalone fixture-copy collision. Corrected
stable gates follow; failed runs are not counted as successful observations.

[Structured observations](evidence/w5j/observations.json), exact saved fixture
inputs, and these actual screenshots are committed and accessible:

- [Drink controls, effective value and reference](evidence/w5j/workbench-drink.png)
- [Saved placement workflow](evidence/w5j/workbench-room.png)
- [Returned object in the still-open inventory](evidence/w5j/game-return-visible.png)
- [Ordinary treatment](evidence/w5j/game-treatment.png)
- [Fresh latest-saved room](evidence/w5j/game-revised.png)

Preservation checks retain bytes and mtimes for **8,203** pre-existing out-of-scope
files, including the unchanged untracked owner plan. Live content, personal
campaigns, fonts/settings, launcher, wiki edition and previous evidence are
preserved. The shipped assignment profile remains disabled and empty. Runtime
fixtures contain all demonstration definitions and altered needs.

This controlled demonstration does not establish balance, unaided discovery or
normal-start pacing. New items still require explicit saved references; liquids
do not gain partial-volume use or generalized refilling. Equipment/effects,
processing/recipe expansion, further selectors, assets and wiki work remain
separately scoped. Work stops at the commissioned supplies/use/revision outcome.
