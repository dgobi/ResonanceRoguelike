# W5G required recovery repair checkpoint

Baseline: `f2c85fa791092601f16411062024f9dba4e976ff`; start checkpoint
`checkpoint/workbench-w5g-start-20261027`. Work stays in the production `main`
checkout. The untracked owner plan is excluded.

Accepted unfinished intent and restoration now use the same admission predicate.
An eligible variant-only text/recipe can restore exact valid or invalid bytes
before choosing a variant. It retains `variant:false`, empty variant ID and the
source target. No review or same-ID permission is granted. Explicit variant
intent still requires the original source's variant operation. Existing baseline,
generation, live-owner and claim-before-read checks are retained.

The shared family diagnostic assembly removes exact duplicates after source-path
translation. Every diagnostic attribute participates in equality; changed field,
severity or location remains distinct.

Locally executed evidence (ignored artifacts under `workbench/.artifacts/w5g`):

- `cargo test --locked --manifest-path workbench/src-tauri/Cargo.toml`: **56 pass**,
  including W4D faults, special clone, changed originals, competing ownership and
  the new test invoking actual text/recipe adapters and fresh variant validation.
- Focused Wight reference worker test: **pass**; inspected/validated informational
  problems are identical, with field/severity distinctions retained.
- `npm.cmd run build`: **pass**, complete pinned runtime and Windows release.
- `node scripts/run-recovery-unfinished.mjs`: **pass**, two packaged processes,
  actual accepted valid text and invalid BOM/Unicode recipe drafts before variant
  selection, abrupt termination, cold restore, no restored review, deliberate
  variant and fresh successful validation. Receipt:
  `.artifacts/w5g/repair-native-1793160402402/receipt.json`; package and draft
  hashes, process IDs and generations are recorded there.

Early native script runs exposed test-locator assumptions (variant-only button
label, hidden Source after validation and multiple mounted variant fields).
Those harness locators were corrected; no product assertion was relaxed.
The final native run above passed. This checkpoint precedes the room extension;
the final W5G receipt identifies its commit without a self-hash loop.
