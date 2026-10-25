# G14 — Crate wood for a field campfire

25 October 2026, America/Edmonton. Production checkout `main`.
Starting source: `1146b5c0300c0b0ff47689a85bb1fe6f3019de4e`.
Frozen runtime/data/test inputs: `7f5d8f44b919254cbb44da0909be40e41ac073c1`.

An explicitly emptied crate can become one physical wood bundle. In `E`
adjacent selection, target the crate and press `X`; Enter confirms and Esc
cancels. Ordinary Enter still searches, and taking the last item leaves the
crate standing. The prompt states removal, one floor wood output, a retained
equipped cutting tool and one world turn. Controls are also recorded in
[START_HERE](../../roguelike/docs/owner/START_HERE.md) and
[SYSTEMS](../../roguelike/docs/SYSTEMS.md).

Only the exact existing `crate` decor with a matching live container owner and
an actually empty authoritative list qualifies. Serialized rows count as
contents regardless of the looted flag. Confirmation rechecks the same map,
scene address, exact owner, unchanged source state, range, visibility, diagonal
corners and an owned weapon/offhand cutting tool of tier 1+. Replaced or stale
sources and tools cannot authorize work. Cancellation/rejection changes no
owners or time.

Success places one existing `wood_bundle` through the floor helper before
removing the crate decor and its container owner. Factory/placement failure, including a partial
floor write, preserves the source and unrelated objects. Terrain and actors
remain. One ordinary action uses the existing clock/debt completion path;
the debt-free case increases the turn by exactly one. The tool remains. Full
packs permit conversion; later rejected pickup leaves the same output on the
floor. Its persisted instance description records its actual crate origin.

## Demonstration and preservation

The [final event trace](../../evidence/gameplay-g14/final-a/journey/journey.json)
uses seed `20261023`, normally selected `tool_shed_b` in chunk `(75,99)`, placement
`settlement-0-cross-market-lot-1-23-N-0-building`. Native storage and wood are
recorded from generation. The bag crate is local `(18,29)`. Initial staging at
the generated public approach and full-state route/UI selection are disclosed.
This is a local interaction/process demonstration. Normal FOV, native AI,
survival and action costs remain active; no fuel/rewards were inserted, threats
cleared, invincibility enabled or health/supplies reset.

The player searches and empties the bag crate, retains its Leather Satchel,
equips the starter crude blade normally, confirms dismantling, and sees one
floor wood bundle and the missing crate. The recovered wood and the shed's
native floor wood are picked up normally, then spent as the exact two physical
materials in the existing Field Campfire recipe. Placement produces an unlit
fire in one action; a separate interaction lights it in another. Blade, bag and
torch remain. Working fire is reached after **18 world turns**, at
**60 HP**. The trace contains **42 inputs** including save/restore.
Four full production-rendered views and one 480×320 prompt check are retained.

F5 saves immediately after dismantling, with the output still on the floor.
The retained archive passes CRC and a genuinely separate process restores the
complete snapshot. Later pickup and fire creation are deliberately unsaved;
F9 restores the earlier missing-crate/one-floor-wood snapshot exactly. A focused
cache eviction/disk revisit proves neither source nor extra yield regenerates.

The genuine committed G13 shed checkpoint loads unchanged before any action:
the previously emptied crate remains present, its floor has no new output,
the complete saved player/world/scene snapshot agrees and all **51**
placement dependency closures pass. Shared crate/wood definitions, all recipes,
G13 layout/pools, selection profiles, world-generation policy, save schema, original
evidence, historical fixtures and personal campaigns are preserved.

## Verification and delivery

Windows x64; production CPython 3.11.0, pygame 2.6.1, tcod 19.3.0,
NumPy 2.4.6; dummy SDL; disposable save roots.

| Final check | Result |
|---|---|
| Unfiltered focused discovery | 267/267 pass |
| Unfiltered production D gate | 3676/3676 pass; 159 workers |
| Subsequent bounded journey, historical load, F5/cold/F9 | Pass |
| Stable frozen inputs and Git binding | 772 inputs |

The [release receipt](../../evidence/gameplay-g14/final-a/release.json) retains
commands, environment, finite timeouts, source/Git bindings and results.
Focused and production gates ran concurrently in separate evidence/save roots;
their measured durations were **26m 14.2s** and **10m 31.4s**. The
subsequent journey took **0m 16.7s**. Actual final gate wall time was
**26m 31.3s**. Overlapping process durations are not added as elapsed time;
no total development-time claim is made. All seven runner negative controls
reject correctly. The [audit](../../evidence/gameplay-g14/audit.json) and
[artifact index](../../evidence/gameplay-g14/artifact-index.json) bind completion
evidence to the frozen inputs.

The eight new focused tests group source/tool eligibility and staleness, actual
emptiness, reach/visibility/corners, cancellation, factory and placement failure,
single output/owner removal, capacity-aware pickup, turn/debt and cache revisit.
The [preflight receipt](../../evidence/gameplay-g14/preflight.json) records 19
passing G14/G12 checks, the rendered journey and the corrected test-fixture
clock/FOV and active-scene assumptions. These development failures are separate
from the final unfiltered gates.

Repeat with committed inputs and a fresh evidence directory:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/verify_g14.py --evidence evidence/gameplay-g14/owner-verification
```

The known G12 explicit torch-as-fuel menu omission remains separate; this trace
uses two wood bundles. No cross-platform determinism claim is added. The existing
wiki edition is preserved. No other furniture, disassembly system, item, recipe,
art, tool wear, progression or wider gameplay work is included.

Immutable checkpoints: `checkpoint/gameplay-g14-start-20261025-a`,
`checkpoint/gameplay-g14-inputs-20261025-a`, and
`checkpoint/gameplay-g14-verified-20261025-a`. The portable delivery receipt records
exact published remote main and annotated/peeled tag readback.
