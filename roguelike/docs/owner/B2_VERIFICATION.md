> Historical accepted record. Current main-only verification and remaining scope: [B3_VERIFICATION](B3_VERIFICATION.md) and [B3_DEFERRED](B3_DEFERRED.md).

# Autonomous B2 verification

Run from `G:\GameDev\RoguelikeBaseline-20261020\project`:

```powershell
.\.venv\Scripts\python.exe tools/verify_b2.py
```

This enforced default runs all B2 cases, the exact before-fix controls against
accepted B1 bytes, and the complete B1 matrix/diagnostic regression suite. A missing
case, wrong value, missing/stale result, wrong source binding, crash, timeout or
unexpected baseline symptom fails the gate. `--only` is partial development
diagnosis and never certifies completion. `--before` records uncorrected properties
and intentionally exits 1. It is not an acceptance pass.

The environment remains Windows Python 3.11.0, Pygame 2.6.1 / SDL 2.28.4,
tcod 19.3.0 and NumPy 2.4.6. No new dependency is required. Child processes alone
receive dummy SDL video/audio drivers, PYTHONHASHSEED and deterministic fixture
RNG seeds. No desktop input, focus, mouse control or normal launch changes occur.

The runner creates unique `.baseline/b2-...` roots and exports B1 commit
`9bb0db884b989bb9a21f25387b5772e3246ba978`. It checks all captured game-source hashes.
If the Git object is unavailable, `--baseline <clean-export>` accepts only those
same bytes. Personal saves are excluded. Every worker records command, CWD, PID,
phase, versions, environment, source origins/hashes, stdout/stderr, assertion
values and completion status. Writer checkpoints are hashed immediately, cloned
to independent readers and rechecked unchanged at the end. Same-process mutations
use distinct fixtures. No fresh reader follows a travel-modified writer.

When running without the repository history, also supply `--b1-baseline
<clean-Arc-A-export>` for the nested B1 gate. That export is independently bound
to its captured Arc A manifest; the two baselines are never interchangeable.

| Gate | Required behavior |
|---|---|
| B2-01 | Needs configuration on direct/fresh routes; component replacement, language/level preservation and next-turn configured Needs drain. |
| B2-02 | Exact perk hooks, immediate bonuses, no duplicate effects on repeated loads, one subsequent healing effect, removal/absence clears hooks and bonuses. |
| B2-03 | Nonzero and empty timer/status replacement, next-turn countdown and eventual expiry. |
| B2-04 | Distinct item values, remaining fuel, custom nutrition consumer, exact equipment, mutable-value isolation and full shipped item-catalog roundtrip. |
| B2-05 | Active, paired surface and inactive submap processing each tick once; aliases do not double-tick; output belongs to the correct map; persisted active duration resumes. |
| B2-06 | Actor stats/perception/AI/status restoration before ticking, then actual arrival cooldown consumption. |
| B2-07 | Invalid extension/field rejection before owner replacement, read-only failed bootstrap, explicit absence/nulls, missing-extension defaults and actual B1-writer compatibility. |
| B2-08 | Original Engine.run with real paired KEYDOWN/KEYUP events: inventory salve use, F5/F9, fresh bootstrap, waits, Hardened Step movement, critical Needs drain, rain collection and processing completion. |
| B2-09 | Complete B1 regression gate: all 28 identity/format gates, six baseline characterization cases, corrected original 32/32 properties, negative runner controls. |
| B2-H | Exact sources/phase/PID/checkpoint and planned-worker completeness; baseline symptoms separately checked. |

There are 36 B2 workers: 13 preserved-B1 controls and 23 candidate workers.
The nested B1 gate uses 72 workers plus 20 original diagnostic workers. Assertion
totals include source-binding/harness checks and are not independent feature counts.
The original B1 source still shows 134 failing B2 property observations in the
new probes; final regression compares their exact values. The historical Arc A
diagnostics remain 17/32 passing before B1 and 32/32 on the current candidate.

The original B1 characterizations are updated narrowly: on the candidate they now
assert the four repaired B2 properties. Baseline still asserts their historical
failure signatures. Only those four IDs leave the candidate deferred list; the
other four exact symptoms must still match. No B1 acceptance assertion is waived.

Journeys wrap and call original Engine.run and original event.get. Fixtures are
explicitly labeled. Posted events must be accepted; keys are paired and modifiers
cleared. The driver stops by observed state within 200 polls, 80 turns and 90
seconds; workers have a 180-second parent deadline. Selected PNGs come from the
actual Pygame surface and are inspected by Codex. They support semantic assertions.
The returned evidence contains those observations, not a request for owner testing.

Final evidence: [b2-results.json](../../../evidence/b2-results.json),
[summary](../../../evidence/b2-summary.json), and the before records under
`evidence/b2-before/`. The review ZIP contains the patch, readable changed files,
field ledger, drivers, embedded logs and checkpoint hashes, selected captures,
source-preservation records, manifests and isolated patch/ZIP verification.
