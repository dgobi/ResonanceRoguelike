# Resonance G10 review and G11 implementation handoff

Reviewed `main`: `7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b`. Prepared 24 October 2026, America/Edmonton.

Start with **G10_REVIEW.md** for the assessment, then give **CODEX_G11_WILDERNESS_ENTRANCE_ACCESS.md** to Codex for the next bounded implementation. The brief is complete and may be used by itself; the evidence provides a reproducible defect and source coverage.

G10 improves terrain character and its retained verification is authentic. Independent review found that an entrance stamp can isolate Arnevel Vault in ordinary seed 20261023, Drowned Wood chunk (44,8). G11 repairs the final exterior-access relationship while retaining scenery, ownership and historical generation contracts. Existing campaigns are not silently upgraded.

## Contents

| Path | Purpose |
|---|---|
| `G10_REVIEW.md` | Outcome, evidence distinctions, defect, player-facing assessment and source links. |
| `CODEX_G11_WILDERNESS_ENTRANCE_ACCESS.md` | Executable next brief with scope, preservation, acceptance and delivery requirements. |
| `references/` | Supplied compass, dated state/workflow and actual issued G10 brief. These are unchanged reference copies; the state file's G9 baseline remains historical. The new review identifies the current G10 baseline. |
| `evidence/access/` | Portable access reproduction, original 60-scene discovery sample, stage/handler JSON and production images. |
| `evidence/g10-tests/` | Independently rerun nine-test output, receipt and lifecycle records. |
| `evidence/expedition/` | Independently replayed ordinary outing, original generated checkpoint, output and normal-FOV images. |
| `evidence/release-audit.json` | Independent reconciliation of retained G10 source, gates and evidence, qualified by the new access finding. |
| `evidence/review-summary.json` | Review revision, remote readback, environment and evidence scope. |
| `MANIFEST.json` | SHA-256 and byte size for every other package member. |

## Reproduce the specific access failure

Use the existing game's dependency interpreter:

```text
python evidence/access/reproduce_g10_entrance.py --repo PATH_TO_RESONANCE --out PATH_OUTSIDE_REPOSITORY
```

The script uses disposable saves and app-local events. Its success exit means the probe completed. Inspect `defect_observed` and the stage/handler records to distinguish the observed defect from a later corrected result. It is a baseline probe for the reviewed G10 code; adapt policy construction and its narrowly selected coordinate fixtures when implementing a newly versioned route.

The access test uses disclosed initial fixture positioning. It is not the ordinary-play excursion. The ordinary outing is separately retained under `evidence/expedition`. Revealed generation images and normal-FOV controlled screenshots are labeled separately.

The independent review ran on Linux/Python 3.12.14, pygame 2.6.1, tcod 19.3.0 and NumPy 2.3.5. The Windows production gate was audited from its retained raw evidence; it was not rerun in this environment. No game implementation or repository publication was performed by this review.

No PDF, wiki rebuild, new roadmap or reference-pack maintenance gate is included.
