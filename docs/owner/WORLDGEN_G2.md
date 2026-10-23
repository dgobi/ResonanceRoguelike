# G2 — Dependable structure authoring

Implemented in the production checkout on `main`, starting from clean
`05bcc4973b09e86afcd099af99b277eab92a2bec`. The owner workflow is in
[Structure Authoring](../../roguelike/docs/STRUCTURE_AUTHORING.md); open the root
[layout painter](../../layout_painter.html) locally. This records implementation
and verification, without claiming a subsequent owner-acceptance event.

## Delivered behavior

The offline painter retains complete imported JSON, including unknown and inactive
metadata. Terrain, full-ID decor, supported special records, starts and entrance
fields can be edited independently. Real file input/download and paste import work
without a service. Undo/redo covers the complete document. The 60-column lab fits;
enlargement and null-padding are explicit, destructive cropping is refused, and
unsupported oversized documents remain intact for export.

`tools/structure_authoring.py` is the authoritative catalog/validation/preview
command. Runtime loaders and author tools use the same typed contract and
caller-owned data catalogs. It validates every weighted branch and referenced
scene/pool before choice, preserves raw source, and reports actionable source
diagnostics. Browser catalog hints never certify runtime success.

All four existing routes use production consumers in previews: ordinary buildings
(normal and vertical mirror), plazas, interior entrances and authored submaps.
JSON/SVG show realized objects, rolled contents, stairs and explicit access targets.
SVGs are diagnostic glyph views, not game-renderer screenshots. Controlled cottage
registration retains all 57 installed candidates and proves positive selection and
content in a real town fixture. It is not a world-frequency estimate. Examples and
browser exports remain outside live placement pools.

## Corrective milestone: before and after

| Case | Reproduced baseline | Delivered contract |
|---|---|---|
| Debug departure | Wraith exposure 4 remained in cache and returned at turn 480 with FOV radius 5. | Clear departing exposure/overcorrection after successful preparation and before serialization. Same-address/failure and F9 saved encounters keep their distinct semantics; no turn or checkpoint advance. |
| Cottage checker | Omitted container decor/pools raised key errors; the old fallback was inconsistent. | Compatibility command uses the shared production adapter and `crate` / `[]` defaults, including separately and jointly omitted fields. |
| Shared mouths | Extreme width3 roads lost cells/differed at town boundaries; width13 river became11 on the short axis. | Resolve the whole mouth into the non-corner interval once; preserve requested legal width and omitted/zero defaults, reject impossible requests. Exact reciprocal masks and inward approaches are tested. |
| Stair access | A stair in an isolated two-cell rock pocket passed the former local guard. | Require connection to pre-stamp meaningful entry/road anchors, recheck after contents, and reject blocked candidates before publication. Authored/fallback positives and return travel pass. |

Baseline probes and the tested correction milestone are retained under
[evidence/worldgen-g2](../../evidence/worldgen-g2/). These synthetic geometry
reproducers do not assert a measured shipped-world failure rate.

## Compatibility and deliberate limits

New geometry/content records generation revision **wg2**. Absent-field legacy and
explicit wg1 scenes remain authoritative on load/revisit/F9, including their
mutations. New exploration can be wg2 while world origin stays wg1; there is no
backfill, old-world relabeling or cross-version seam guarantee.

The live inventory remains 55 ordinary buildings, two plazas, six entrances and
one authored submap. Eight dimension/ragged-row corrections preserve actual stamp
and materialized-content semantics; the frozen 65-file baseline corpus remains
unchanged. The final catalog has zero errors and 238 classified warnings: 229
inactive fields, two unused legacy terrain references, four deferred physical
specials and three inactive loot-pool row fields.

Folder categories and current town roles remain the eligibility contract. Row
packing is uniform among fitting definitions; corner scattering and plaza
selection retain their existing weighting. `town_config.json` remains inactive.
There are no new rotations, categories, POI scatter, planner, body/stele physics,
authored creatures, save migration or gameplay RNG replay. Static access checks
require explicit targets and treat native creatures as dynamic occupants.

## Verification and acceptance mapping

The correction checkpoint passed 115 focused tests. The completed implementation
passed all 127 focused tests and 26 checks in each headless browser. Both browsers
also round-trip the 65 frozen originals and 64 delivered documents, and their real
downloaded edits pass the Python CLI and mixed-pool town registration.

| Acceptance | Evidence |
|---|---|
| G2-01 | `test_generation_g2_corrections`: actual debug departure, cache/effects/checkpoint assertions; retained F9 effect tests. |
| G2-02 | Correction tests for original/defaulted cottage; compatibility command and shared `populate`. |
| G2-03 | Correction and retained geometry tests: axes, extremes, defaults, rejection, full reciprocal town/wilderness lists, inward access and ford semantics. |
| G2-04 | Correction, geometry and structure-access tests: isolated pocket, authored/fallback stairs, final content blockade, real return travel. |
| G2-05 | Catalog JSON/summary and contract tests: 64 exact route identities, duplicates/all paths, invalid roots, unrelated list loader preserved. |
| G2-06 | Contract tests: grids/dimensions/coordinates/decor, all alternatives, references, text/scene/pool row shapes and container capability. |
| G2-07 | Shared consumers/defaults, invalid-candidate publication guard, retained legacy fixtures and explicit wg1 world/scene save/revisit/F9 test. |
| G2-08 | Alias/inactive/deferred tests; eight original-versus-corrected production stamp/content equivalence fixtures. |
| G2-09 | Both browsers: 65 original blob identities and value-tree round-trips; 64 delivered documents and absence/null/false/zero/unknown sentinels. |
| G2-10 | Both browsers: actual single terrain/decor/record edits, erase, invalid/cancelled/sequential imports, compared downloaded JSON. |
| G2-11 | Both browsers: lab60→61, resize cancel, crop refusal, legend guard, undo/redo, starts; oversized/ragged model checks. |
| G2-12 | Two retained temporary data catalogs with matching IDs/different content alternate A/B/A/B/A/B through all four real consumers and town plaza dispatch, with unrelated gameplay RNG. |
| G2-13 | Structure-access tests: engine pickup/read, legal blocking-crate transfer and descend/return agree with named access targets; interaction-corner negative control. |
| G2-14 | Each browser's downloaded candidate passes unified CLI and positive existing-pool generation with realized item/container contents. |
| G2-15 | Isolated headless Chromium/Firefox drive actual local-file controls and downloads; no owner desktop or signed-in profile. |
| G2-16 | Complete cottage/scene-weighted examples, route previews, compatibility and catalog commands; guide covers installation, diagnostics and saved-scene limits. |
| G2-17 | Final frozen-source focused/browser/full production gate and source reconciliation recorded below. |

Commands use the established interpreter, not game source from its historical
directory. Python 3.11.0, pygame 2.6.1, tcod 19.3.0 and NumPy 2.4.6 are unchanged.
Pinned external development Playwright 1.64.1 uses Chromium 156.0.8078.4 and Firefox
157.0. Its bundled driver reports `1.64.0-beta-1791568591000`; the runner verifies
the driver's package file against the Python distribution RECORD. Resolving the
physical Windows LocalAppData path fixed Firefox's native assembly lookup without
browser binary/security changes. No downloaded dependencies are committed.

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike --evidence evidence/worldgen-g2/focused
& $ResonancePython -X utf8 tools/verify_structure_editor.py --evidence evidence/worldgen-g2/browser
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output evidence/worldgen-g2/catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
& $ResonancePython -X utf8 roguelike/docs/examples/validate_building.py --game roguelike --building roguelike/docs/examples/author_cottage_a.json --output evidence/worldgen-g2/compatibility-cottage.json
& $ResonancePython -X utf8 tools/verify_d.py
```

## Commits and final gate

- Start: `checkpoint/worldgen-g2-start-20261023` at `05bcc497` (clean main).
- Corrections: `815dfb5`, `checkpoint/worldgen-g2-corrections-20261023`.
- Implementation/gate-input commit and final unfiltered gate: recorded after the
  frozen-source run below. No partial gate is represented as full acceptance.

See [G1](WORLDGEN_G1.md) for preserved historical evidence and the
[approved proposal](WORLD_GENERATION_AUDIT_AND_PROPOSAL.md) for the subsequent
settlement/road/plot planning boundary. G2 stops here.
