# G2 verification evidence

Production source: `G:\GameDev\RoguelikeProject` on `main`. Baseline:
`05bcc4973b09e86afcd099af99b277eab92a2bec`; tested final source:
`29a3ef68c4514073100fc9dc12ff8a6743d1cc01`. The final verified tag includes only
documentation/evidence changes after that source commit. See
[the owner record](../../docs/owner/WORLDGEN_G2.md) for the complete G2-01–17 map,
checkpoints, commands and compatibility limits.

- `baseline.json`, `before-state.json`, `before-geometry.json`, `before-checker.json`:
  clean starting state and actual failing-before reproducers. The attached brief's
  SHA is recorded; the source archive itself is not committed.
- `corrections-pass/`: 115-test corrective checkpoint. The earlier failures are
  historical baseline evidence, not claims that the delivered tests failed.
- `data-corrections.json`: eight explicit dimension/null-padding corrections.
  Original files remain in the separately pinned 65-document test fixture corpus;
  production stamp/materialized-content equivalence is tested.
- `catalog.json`, `catalog-summary.json`: all 64 current assets and 238 classified
  warnings, zero errors. `authoring-commands.json` records all eight successful
  final catalog/preview/compatibility invocations and complete guide-example parity.
- `author-cottage.json`, `author-cottage-0.svg`: a directly viewable representative
  runtime preview with note/food/container access and actual mixed-pool registration.
- `previews.zip`: all 21 detailed JSON/SVG outputs, including both mirrors,
  scene/weighted example, entrance, lab, plaza, compatibility command and the two
  browser-exported assets' runtime results. `previews-manifest.json` lists original
  paths, sizes and SHA256 values. SVGs are diagnostic glyph maps, not game rendering.
  The direct cottage files are also in the archive. Uncompressed originals were
  preserved as local review artifacts outside the repository.
- `browser/`: both isolated headless browser reports, logs, screenshots, downloaded
  cottage JSON and source-bound summary. Runtime reports referenced by those logs
  are retained at their original relative names inside `previews.zip`. Each browser
  passed 26 checks; the 65 original + 64 delivered codec round-trips supplement real
  file import/edit/download tests. The pinned original Git blob hashes also pass.
- `focused/`, `focused-run.json`: 127 discovered tests against the frozen source,
  unchanged 180-second bound, actual versions and before/after source identities.
- `source-reconciliation.json`: all 569 gate inputs reconcile to Git; 357 are exact
  bytes and 212 differ only by Windows LF/CRLF checkout conversion. This includes
  runtime/data/tests, example JSON, frozen corpus and HTML/JS/CSS/catalog files.
- `full-gate-log.txt`, `full-gate-results.json.zip`, `final-results.json`: the
  unfiltered D+B1/B2/B3/C gate and final combined acceptance. Its large report is
  compressed without dropping worker assertions or source identities. Disposable
  save roots and browser profiles are not part of the delivered package.

The fixed environment is Python 3.11.0, pygame 2.6.1, tcod 19.3.0 and NumPy 2.4.6.
Browser tooling is external Playwright 1.64.1 with Chromium 156.0.8078.4 and Firefox
157.0. The package's internal driver version and RECORD verification are retained.
No personal campaigns were opened or modified. New generation is `wg2`; legacy/wg1
maps remain authoritative. Neither direct previews nor bounded positive selection
claim ordinary-world frequency.
