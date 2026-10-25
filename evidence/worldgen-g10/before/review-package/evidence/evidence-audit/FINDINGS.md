# G9 retained evidence audit

## Conclusion

No blocking inconsistency was found between the attached G9 report, current game/test inputs, frozen release receipts, retained output bytes, genuine G8 compatibility fixture, and ordinary network results. This is a read-only evidence and data audit. It does not substitute for a fresh game execution or establish that the journey is enjoyable with ordinary survival and enemy behavior.

Reviewed `main`: `f9fe901417b360bc1fda84835e0a793eaac2f6df`. Frozen ten-gate inputs: `919e8b40ab5ebca6cf5df6ae3afaf6baa4b67d78`. The working tree remained clean.

The attachment `Pasted text(7).txt` is byte-identical to `docs/owner/WORLDGEN_G9.md`: 19,778 bytes, SHA-256 `d09b5e47e1a38d0b78a08aa738c56fefb5fdc9d1bdadeea7fd4febd599699aac`.

## Source and execution evidence

All **726 declared frozen input paths** match their frozen Git blobs at reviewed HEAD. The captured Windows bytes reconstruct as **451 exact** and **275 uniform newline conversions**. No content discrepancy, missing source, changed tested Git object, or unresolved raw-byte identity was found.

All **ten final-b gate receipt hashes match exactly**. Each records the same frozen input commit, unchanged source, identical input manifest, reconciled committed inputs, exit zero and no timeout. All **1,076 retained gate-output entries are byte-exact**. The task-specific Git attributes preserve these records; newline reconstruction was not needed for retained output bytes.

The **2,163 absent output entries** are exclusively disposable save payloads: 67 in the guard and 2,096 in production. Every absent entry's path, size and SHA-256 exactly matches `omitted-disposable-saves.json`. That broader index has 2,299 entries totaling 4,113,359,306 bytes; its sum reconciles. Save absence was not counted as passing behavior.

Retained substantive results:

| Gate | Verified retained result |
|---|---|
| Focused | 229 tests, `OK`; 813.781-second child; parent has no inherited `PYTHONPATH` |
| Building editor Chromium | 42 checks, 129 codec documents, no errors |
| Building editor Firefox | 42 checks, 129 codec documents, no errors |
| Production | Unfiltered; 3,675/3,675 checks; 159 workers; 74 coverage groups; seven runner negative controls |
| Diagnostic | Three ordinary seeds; zero failures; baseline identity, traversal and checkpoint evidence retained |
| Lifecycle | Genuine G8 restore, policy-independent pending preparation, late rollback/recovery, sixteen checksum-consistent corruption cases |

The first frozen attempt is retained and correctly marked failed: guard, focused and browser passed, then authoring failed on the stale derived catalog. Final-b restarts every gate. Nothing in this audit relies on reusing that stopped attempt's passing gate status.

Relevant code and evidence:

- `tools/g8_clean_focused.py:13–17` removes inherited `PYTHONPATH` and records the clean parent.
- `tools/g7_evidence.py:25–52` records raw/canonical/Git source identities; the gate wrapper records source stability and process results separately.
- `evidence/worldgen-g9/final-b/release.json` binds all ten gates.
- `evidence/worldgen-g9/final-b/focused/results/{parent.json,focused-tests.txt}` carries the focused result.
- `evidence/worldgen-g9/release-summary.json` locates the production and browser records.
- `evidence/worldgen-g9/index.json:170–180` distinguishes the stopped first attempt from the final inputs.

## Independent ordinary-plan measurements

`audit_retained_geometry.py` uses only the retained JSON plans and Python's standard library. It imports no game code, creates no scenes or saves, and independently constructs the cardinal centerline union and full-width road/deck/access cells. It recovers the original plan by removing the saved optional additions and reverting only the declared version/settings envelope, then compares every original record against the pre-edit G8 plan and the final diagnostic's baseline plan.

All three complete G8 baselines are exactly preserved. All **57 primary pairs** (15, 21, 21) match the reported shortest physical distance before and after, and no distance increases.

| Seed | Baseline unique centerline edges | Added unique edges | Added fraction | New full-width road cells | New physical deck cells |
|---|---:|---:|---:|---:|---:|
| 0 | 11,900 | 0 | 0% | 0 | 0 |
| 20261023 | 24,631 | 5,265 | 21.3755% | 15,786 | 0 |
| 29417 | 11,833 | 0 | 0% | 0 | 0 |

For seed `20261023`, `settlement-1` to `capital-gateway` is independently **23,625 → 8,063** physical four-neighbour steps, satisfying the brief's at-least-50% reduction inside the 25% shared construction cap. The accepted road itself connects `settlement-1` and `settlement-3`. The planner did find the more direct capital candidate, but chose the other route under the declared aggregate-benefit ranking. No further optimization is needed to satisfy G9's stated result.

The retained ordinary diagnostic contains **86 materialized touched scenes** for that accepted route and zero scenes at each planning completion. `tools/worldgen_g9_diagnostic.py:92–119` compares entire baseline plans, all primary physical distances and adjacent complete local road slices, materializes touched scenes, and checks access from actual town arrivals to required doors.

The no-road worlds are bounded-policy outcomes, not exhaustive claims that no possible road could ever be useful. The report explicitly says eight pairs were examined, leaving seven/thirteen/thirteen unexamined (`docs/owner/WORLDGEN_G9.md:249–254`).

## Compatibility and journey scope

The authentic G8 archive has **nine members**, all CRC, SHA-256 and size checks pass, and all checkpoint manifest entries match. Its complete plan matches the separately compressed G8 plan. The fixture and pre-edit witness copies are exact. Recorded creator is G8 commit `b94a0b0db3685f7484632701f0486f3b0b79101e`; the archive's actual world plan is **format 6 / wg8**. The witness includes visited town/common, compound and country scenes; pending town and country chunks; independent compound mutations; and labelled fixture controls.

`test_generation_g9_lifecycle.py:44–63` restores that fixture with current policies unavailable and replanning/augmentation patched to fail. It preserves visited fingerprints, checks the explicit adapter for pending chunks, then cold-loads and uses F9. Lines 65–80 exercise a failure after actual populated-road preparation, compare player/world/RNG/actor/cache/files/HEAD state, and recover with current network policy unavailable. Lines 82–99 cover sixteen forged-but-checksummed plan corruptions before installation.

The retained journey uses real handlers and actually walks the accepted route forward and backward, the original country alternative and both fixed-pair paths. It records 107,749 movement inputs and an explored checkpoint of 470 scene files / 254,086,073 bytes. Its physical distance counts are distinct from route-centerline length and potentially diagonal-capable local movement. The report correctly avoids treating the warm return journey as a cold speed comparison (`docs/owner/WORLDGEN_G9.md:267–278`).

AI and survival are paused and the player is invincible in the coverage journey. This proves traversal and persistence under disclosed controls. It does **not** establish survival pacing, readability of route choices, rewards, or an enjoyable ordinary expedition. Those are appropriate concerns for the next design decision; additional road-graph optimization is not established as the next priority.

## Material limits

- This audit checks retained results; it does not rerun the 229-test suite, either browser, the full production gate or the full journey.
- The original standalone G9 delivery ZIP and its adjacent external publication receipt were not supplied. Its full original archive inventory and publication attestation therefore remain outside this audit. `index.json:148–159,184` explicitly identifies those as external requirements. Current remote main/tag readback can establish the present published source independently.
- Planning and checkpoint cost tables are correctly qualified in the report (`WORLDGEN_G9.md:220–265`). The larger G9 coverage itinerary cannot establish a storage regression or improvement on an equal route. Recorded G9 planning is materially slower than G8 on the same machine.
- G9's already commissioned wiki work belongs to G9's closed scope. The owner's latest instruction removes wiki maintenance from routine implementation. Do not carry G9's wiki gate, chapter rebuild or broad handbook update forward into the next brief.

## Reproduction

Run the two accompanying scripts with explicit paths:

```sh
python audit_g9_evidence.py --repo /path/to/ResonanceRoguelike --output /path/to/audit
python audit_retained_geometry.py --repo /path/to/ResonanceRoguelike --output /path/to/audit/geometry.json
```

`audit_g9_evidence.py` expects the supplied report at the review workspace's `upload/Pasted text(7).txt`; change that one attachment path for another workspace. Both scripts are read-only with respect to the repository. Results are `audit.json` and `geometry.json`.
