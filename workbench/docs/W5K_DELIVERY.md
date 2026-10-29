# W5K — author material preparation

Ordinary immediate and passive item-output recipes now share the registered
Workbench document lifecycle. The owner can save supplies and recipes, place
their saved inputs in a room, prepare them through ordinary game controls,
collect/use the floor output, and revise/retest the recipe. Live preparations,
loot, survival settings and the disabled assignment profile are unchanged.

## Source and package identities

| Boundary | Identity |
| --- | --- |
| Reviewed initial local/remote main | `ce3c7ab6d1b845c2dd41d07a9c91f6ed6d1b1d33` |
| Preserved start | `checkpoint/workbench-w5k-start-20261028` |
| Core implementation | `2dbd277` |
| First authoring package inputs | `checkpoint/workbench-w5k-package-inputs-20261028` (`2dbd277`) |
| Final package inputs | `checkpoint/workbench-w5k-final-package-20261028` (`cd13e2a`) |
| Final verified delivery | `checkpoint/workbench-w5k-verified-20261028`; exact local/remote SHA in the handoff |

The [machine receipt](w5k-verification.json) resolves full revisions and binds
executable/NSIS, bridge/runtime, source working/Git bytes, accepted inputs and
accessible evidence. Packages precede later evidence/documentation commits.
A commit cannot contain its own hash: the named final ref and post-push remote
readback identify the final delivery without a self-hash loop. Work stayed on
production `main`; no branches, worktrees or development checkouts were created.

## Supported authoring and repaired failures

`item-preparation-1` admits **15 of 18** shipped sources through source/dependency
rules: two immediate, two cooking, five drying, four steeping and two rendering.
Each supports same-ID edits and deliberate new-ID variants. The original
immediate/passive class remains fixed; category only groups the UI. Exact source
paths remain authoritative, including herb filename/ID differences.
`campfire` remains inspectable/gameplay-usable, `hungering_oil` remains legacy
`apply_turns` read-only, and `coldbell_extract_deprecated` stays excluded.
The [executable inventory](evidence/w5k/shipped-sources.json) records every source.

Components, retained tools, ambient requirements, both conjunction forms and
their combined allocation use production predicates. A conjunction list means
one automatically eligible item with every tag; object `max_quantity` means the
required number of distinct items, default one. Conjunctions have no explicit
chooser. Protected tag matches are distinguished from automatic matches, and
one multi-tag object cannot fill another component/tool slot simultaneously.
Quantities 1–32, tiers through `2^53−1`, 64 rows/list and 64 total physical slots
are tooling bounds. Unknown metadata, representation and omitted defaults survive
localized edits. Invalid types/references/templates cannot acquire a review.

Preparation controls expose the actual duration/source/defaults, supported
temporary visuals/no-marker policy, literal placement prompt, bounded completion
template and saved factory-valid output. Cooking places on fire and labels its
declared marker inactive. Other sources use beside-fire placement. Passive work
requires stationary fire plus declared ambient conditions; an owned active
offhand light cannot replace the stationary source. No placement/warmth rule is
loosened. Immediate exchange retains its existing **zero-turn** behavior.

The **W5J carryovers** are the item candidate-shape guard, portable report hashes,
and contradictory README guidance. Actual worker array candidates now receive
located shape diagnostics without review authority. The regression preserves a
valid catalogue by using an eligible unreferenced source. W5J's receipt now
identifies committed LF report bytes and retains both original CRLF working-byte
hashes; clean Git readback reproduces both identities. Historical observations,
accepted fixture bytes and native-run/package boundaries remain historical.

The **inherited preparation repairs** are independent of those carryovers:

- The existing component picker is reachable before automatic-plan rejection,
  including a sole protected matching definition. Automatic spending still
  excludes it. Confirmation rechecks the full plan, exact ownership and current
  conditions; picker/placement cancellation spends nothing and advances no turn.
- Completion constructs and validates output before retiring work/clearing its
  marker. Valid or malformed historical completion text produces once; malformed
  text uses a plain fallback. Missing/invalid output retains the due job at zero
  and its owned marker with a bounded active diagnostic. Restoring the definition
  in a fresh catalogue resumes completion, without refunds, substitution or a
  duration restart. No queue/save schema or general transaction layer was added.

The requirement probe remains bounded: declared references/potential matches,
synthetic production allocation and unowned construction are disclosed. Only
immediate recipes perform synthetic exchange. Passive validation never simulates
placement, processing duration, pickup or use; burning-only fixtures truthfully
fail the implicit stationary-fire condition. Actual lifecycle evidence comes
from Test room. See the [recipe guide](../../roguelike/docs/RECIPE_AUTHORING.md).

## Packaged author → prepare → use → revise

Baseline definitions were authored and byte-checked through supported controls
in the earlier packaged authoring run. An event-file reader lock interrupted gameplay;
the final package reopened those exact accepted bytes, restored the earlier
recipe/output version through typed controls, and repeated both preparations and
all revisions/cold checks. A final read-only packaged check follows the saved
conjunction input and output to their exact item sources and returns to the same
recipe. Package identities and process roles are explicit.
No external JSON writing is counted as accepted content authoring.

| Saved ID | Meaningful authored behavior |
| --- | --- |
| `w5k_meat` | Protected ordinary meat material; two placed/acquired instances |
| `w5k_leaf` | Automatic bitter/edible sprig; four placed/acquired instances |
| `w5k_pot` | Saved vessel/heatproof tool retained after both preparations |
| `w5k_roast` | Food restoring 0.25 hunger; later same-ID revisions to 0.6 and 0.8 |
| `w5k_dressing` | Ordinary treatment healing 9 HP |
| `w5k_cook` | Independent `cook_meat` source; one protected component, retained vessel, three turns, roast output |
| `w5k_dry` | Independent `dry_bitter_herb` source; conjunction quantity two, retained vessel, four turns, dressing output |

The room's seven saved input/tool references were added with ordinary placement
controls; Source supplied disclosed fixture geometry. Ordinary movement/pickup
acquired the exact objects. The once-only setup created a real stationary fire
at `(39,21)` through production decor placement and established hunger/thirst
0.8 and HP 45/60. This is a focused heat/needs fixture, not room-decor authoring,
new station behavior or a balance/unaided-discovery claim.

The real crafting UI offered its sole protected meat definition. Picker and
placement cancellation retained inputs and time. Cooking confirmation left two
turns, preserved the fire, spent one exact meat and retained the vessel. Normal
turns produced one floor roast, followed by directional pickup and ordinary food
use. Drying at `(39,22)` spent two distinct leaves, retained the vessel, recorded
the beside-fire marker and three remaining turns, then produced one floor
treatment for ordinary pickup/use.

| Use | Observed before → after | Action calls / turns |
| --- | --- | --- |
| Roast, 0.25 hunger dose | Hunger 0.804 → 0.555 | 1 / 1 |
| Dressing, 9 HP | HP 45 → 54 | 1 / 1 |

Normal hunger rises 0.001/turn; thirst rises 0.001375 under the actual plains
modifier. Effects/elapsed time remain ordinary after setup. Screenshots and
[structured observations](evidence/w5k/observations.json) retain exact physical
identities, ownership differences, first-tick records, floor objects and uses.
Transient identities are compared only within their process.

Typed same-ID recipe revision changes cooking to five turns, dressing output and
new completion text. Reset retains the original immutable manifest and starts
the old roast job with two remaining; latest-saved captures a different manifest
and starts the new dressing job with four remaining. A compact real same-ID
`briar_binding_oil` validation/publication proves immediate conjunction permission
without claiming an oil-use itinerary. Another invalid dirty shared document
survives navigation/publication/recovery. A real external conflict preserves
competing bytes. Supplies/recipes/room saves remain independent transactions.

## Separate-process compatibility

An ordinary owned save, separate from immutable captures, records a confirmed
unfinished roast job with two remaining, consumed meat absent and vessel retained.
After the UI recipe/output revisions, another pinned process cold-loads it with
a fresh catalogue. Its old output ID, source, marker/on-fire state, duration and
completion text remain exact; there is no stored recipe ID to redirect.
Real turns construct one roast using the current **0.6** definition of its stored
target. A newly started job instead captures the revised five-turn dressing recipe.

A separate fault save cold-loads with the roast definition temporarily unavailable
only in the disposable project. Repeated turns retain the zero-due job/fire and
report once. Restoring the definition and starting another process completes one
output normally. The focused beside-fire regression independently retains the
owned temporary marker on missing/invalid output.

After acquiring/saving the 0.6 roast, a further UI definition revision to 0.8 and
fresh process preserve its copied 0.6 value; new construction is 0.8. The revised
dressing job completes once and its treatment uses an ordinary turn. Further
save/load/turn input produces no duplicate output or respawned material. Exact
inventory comparison occurs immediately after load; a later normal turn advances
the equipped torch's burn counter while prepared supplies retain their values.
Explicit save-access audits remain confined to the owned disposable roots.

## Verification, preservation and limits

The receipt records commands, environments, hashes and corrected attempts.
Final gates include 69 frontend tests, TypeScript, 68 Rust tests, clippy with
warnings denied, 101 broad game cases plus the six focused repair cases (102
distinct game cases overall), 79 worker cases (78 pass, one expected embedded
runtime skip) and its separate dependency
negative control, locked Windows packaging, packaged workspace/room lifecycle,
the preparation journey and ordinary 128×128 startup/default save/load.

Early failures remain distinct from passing observations: outdated permission
expectations, a referenced-source shape fixture, monitor/navigation contention,
portalled control selectors, read-only BUSY retries, a bounded AI trajectory
check replacing an unreliable six-turn endpoint comparison, a transient Windows
event-file lock, an incomplete
concurrent worker attempt, and the torch-time comparison described above.
The final stable suite and exact accepted fixtures are recorded separately.

Accessible evidence includes the inventory/observations/gate summaries, exact
accepted fixture bytes, and actual screenshots of preparation controls, room
placement, cooking, floor roast, drying, treatment and revised work. Reports use
UTF-8 LF identities; fixture `.gitattributes` preserves accepted mixed line endings.
`scripts/w5k-readback.py` checks committed bytes and exact remote-main agreement.

Preservation verifies bytes/mtimes for **8,226** pre-existing out-of-scope files,
including the unchanged
untracked owner plan. Live data/campaigns, fonts/settings, launcher, previous
evidence boundaries, wiki edition and assignment profile remain preserved.
Active/distinct hot maps tick once per simulated turn; cold maps stay frozen.
No wall-clock catch-up, new continuous fuel rule or missing-owned-cache generation
was introduced. World-placement authoring, conjunction choice UI, stations,
equipment/effects, learning, broad migration, balance work and wiki upkeep remain
separately commissioned. Work stops at the requested material-preparation outcome.
