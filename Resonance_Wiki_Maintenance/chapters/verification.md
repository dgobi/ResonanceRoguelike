# Verify a change

Use a check that observes the thing you changed. A parser proves syntax, a factory proves construction, a layout validator proves selected structure constraints, and a generated-world test proves placement in context. None alone certifies balance, visual quality or an entire campaign.

All commands here run from the repository root, using the `$ResonancePython` variable from [Setup](#getting-started). Keep evidence outside `roguelike/` and choose a new output directory for each run. Do not overwrite the repository's frozen G1–G9 evidence.

## Choose a useful check

| Change | First useful check | Follow-up when behavior changes |
|---|---|---|
| One JSON value or prose field | `python -m json.tool <file>`; inspect its diff | New instance/read in a disposable run; referenced-ID check. |
| New item or creature | DataLoader + actual factory; debug spawn | Appropriate combat/ownership regressions and a real spawn route. |
| Structure geometry/access | Candidate validator and preview | All permitted transforms; naturally selected placement and complete scene. |
| Town roles, weights or caps | Planned previews over chosen seeds | G9 plus inherited authoring cases; distribution observations, not a single screenshot. |
| Rural POIs | Assigned-site preview, then natural `--site` | G9 journey including travel/save/load ownership. |
| Sprite/tile change | Mapping and bounds check; visual inspection | Actual renderer paths at supported zooms. |
| Save/state or core mechanics | Focused regression for the invariant | Unfiltered production gate for a feature delivery. |

## Syntax and basic startup

```powershell
& $ResonancePython -m json.tool roguelike/data/items/weapons/severance_blade.json
& $ResonancePython -m pip check
& $ResonancePython -X utf8 tools/play_disposable.py --session edit-smoke-02 --seed 20261023 --headless-smoke
```

Strict JSON uses double quotes, no comments and no trailing commas. Duplicate keys are also a mistake even though a basic JSON decoder may silently take the last value. A definition ID reused in another file can overwrite the earlier registry entry. Syntax success is not a duplicate-ID audit.

## Structure catalogue and editor freshness

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output .wiki-evidence/edit-02/catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
```

The catalogue describes 64 structure assets in this snapshot. Its route capability descriptions include legacy ordinary-building behavior; use the current World & structures chapters for modern planned transforms and profile selection.

The editor's catalog is generated from data and includes byte-sensitive source identity. During the wiki audit, a fresh Linux checkout reported it stale even though all compared asset contracts and semantic catalogue sections matched. Refreshing it is a legitimate generation step when data has changed:

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py --refresh-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
git diff -- tools/structure_editor/catalog.js
```

That refresh **writes** `tools/structure_editor/catalog.js`; review and retain it with the appropriate content edit. The wiki audit did not refresh the source repository to hide the stale result.

## Focused regression suite

```powershell
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike --timeout 1800 --evidence .wiki-evidence/edit-02/focused
```

This is the project's focused regression runner. The result and emitted evidence matter more than a count quoted from an earlier delivery. Avoid reusing a historical passing report as proof for newly modified code.

## Current world-generation workflows

```powershell
& $ResonancePython -X utf8 tools/verify_g9_authoring.py --evidence .wiki-evidence/edit-02/authoring
& $ResonancePython -X utf8 tools/worldgen_g9_diagnostic.py --journey --evidence .wiki-evidence/edit-02/journey
```

The first exercises current authoring recipes, including inherited G5–G8 coverage. The second checks a generated-world journey and its ownership/continuity properties. Use the exact candidate commands in the structure chapters for faster iteration before these broader checks.

## Full production and release gates

```powershell
& $ResonancePython -X utf8 tools/verify_d.py --evidence .wiki-evidence/edit-02/production
```

Despite its historical name, `verify_d.py` is the production gate including B1/B2/B3/C/D regressions. Its `--only` and `--case` options produce partial runs; those are useful diagnostics but must not be presented as an unfiltered pass.

The G9 release coordinator runs the unfiltered focused, editor, new/inherited authoring, catalogue, ordinary diagnostics/journey, production views, wiki and unfiltered production gates sequentially against a recorded source identity:

```powershell
& $ResonancePython -X utf8 tools/verify_g9_release.py --evidence evidence/worldgen-g9/owner-release-02
```

The root output directory must not already exist. Browser/editor verification has additional tooling requirements; this command is a release gate, not a minimal prerequisite for reading or editing JSON. The G9 feature delivery includes the full game gates; a later prose-only handbook edit does not require repeating unrelated game gates. The wiki's audit runs are listed in [Coverage and audit](#coverage).

## Keep useful evidence

Record the source SHA, relevant data diff, command, environment, exit status, seed/session, expected result and actual result. Preserve failing output. For random generation, retain the seed, candidate IDs and selection/configuration so the same failure can be investigated. A screenshot shows appearance; a path/connectivity check establishes access. Use both when that distinction matters.

The standing project workflow is autonomous headless processes and app-local events. Routine verification should not require taking over the desktop or assigning ordinary test execution to the owner.

## Source basis

[Focused runner](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/tools/critical_fix_regressions/verify_fixes.py) · [structure CLI](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/tools/structure_authoring.py) · [G9 authoring](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/tools/verify_g9_authoring.py) · [G9 diagnostic](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/tools/worldgen_g9_diagnostic.py) · [release coordinator](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/tools/verify_g9_release.py).

## G7 composition integration

The current mixed parent workflow is documented in [Compounds](#compounds). A building export supplies the consumed child structure; a separate recipe supplies two required slots, an optional third slot, common paths, private bounds and permitted parent/child transforms. The existing painter edits the building, not the recipe. Use actual exported bytes in `--child`. Run `tools/verify_g7_authoring.py` for inherited and compound workflows; direct focused discovery now supplies its own absolute tools import path. Keep previous evidence immutable.

## G9 evidence units and frozen inputs

The release sequence is serial: guard, clean-parent unfiltered focused discovery, both browser export consumers, five new network workflows plus separately counted inherited workflows, catalogue, ordinary diagnostics and real journey, populated production views, wiki contract/build/repeat/drift/integrity/reader and unfiltered production gates. `verify_g9_release.py` uses 2100 seconds for the focused outer gate and 1800 for its child; other outer gates use 1800 seconds and the diagnostic's inner journey limit is 1500. The first full 229-test run passed in 1154 seconds, close to the historical 1200-second cap; the expanded G9 release uses this finite extra allowance without filtering tests. An input change requires the whole unified sequence again. Documentation-only delivery uses the wiki's separate binding and does not rerun unrelated game gates.

The three ordinary seeds are 0, 20261023 and 29417. Keep every primary endpoint, zero-road result, candidate rejection and baseline record. Controlled two-link overlap/marginal tests use declared different admission thresholds and do not replace ordinary acceptance. The real journey walks the accepted connection forward/reverse, the original corridor and a fixed comparable pair, then checkpoints the actual explored world with common and compound state. It reports physical BFS steps separately from movement inputs, scene counts, save bytes and save/cold-load/F9 times. See `docs/owner/WORLDGEN_G9.md` and `evidence/worldgen-g9/index.json` for the current completed receipts and boundaries.
