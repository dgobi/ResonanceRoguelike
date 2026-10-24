# Verify a change

Use a check that observes the thing you changed. A parser proves syntax, a factory proves construction, a layout validator proves selected structure constraints, and a generated-world test proves placement in context. None alone certifies balance, visual quality or an entire campaign.

All commands here run from the repository root, using the `$ResonancePython` variable from [Setup](#getting-started). Keep evidence outside `roguelike/` and choose a new output directory for each run. Do not overwrite the repository's frozen G1–G6 evidence.

## Choose a useful check

| Change | First useful check | Follow-up when behavior changes |
|---|---|---|
| One JSON value or prose field | `python -m json.tool <file>`; inspect its diff | New instance/read in a disposable run; referenced-ID check. |
| New item or creature | DataLoader + actual factory; debug spawn | Appropriate combat/ownership regressions and a real spawn route. |
| Structure geometry/access | Candidate validator and preview | All permitted transforms; naturally selected placement and complete scene. |
| Town roles, weights or caps | Planned previews over chosen seeds | G5/G6 authoring cases; distribution observations, not a single screenshot. |
| Rural POIs | Assigned-site preview, then natural `--site` | G6 journey including travel/save/load ownership. |
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
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike --evidence .wiki-evidence/edit-02/focused
```

This is the project's focused regression runner. The result and emitted evidence matter more than a count quoted from an earlier delivery. Avoid reusing a historical passing report as proof for newly modified code.

## Current world-generation workflows

```powershell
& $ResonancePython -X utf8 tools/verify_g6_authoring.py --evidence .wiki-evidence/edit-02/authoring
& $ResonancePython -X utf8 tools/worldgen_g6_diagnostic.py --journey --evidence .wiki-evidence/edit-02/journey
```

The first exercises current authoring recipes, including inherited G5 coverage. The second checks a generated-world journey and its ownership/continuity properties. Use the exact candidate commands in the structure chapters for faster iteration before these broader checks.

## Full production and release gates

```powershell
& $ResonancePython -X utf8 tools/verify_d.py --evidence .wiki-evidence/edit-02/production
```

Despite its historical name, `verify_d.py` is the production gate including B1/B2/B3/C/D regressions. Its `--only` and `--case` options produce partial runs; those are useful diagnostics but must not be presented as an unfiltered pass.

The G6 release coordinator runs the selected focused, editor, authoring, catalogue, diagnostic, visuals, production and independent probe gates sequentially against a recorded source identity:

```powershell
& $ResonancePython -X utf8 tools/verify_g6_release.py --evidence .wiki-evidence/g6-release-02
```

The root output directory must not already exist. Browser/editor verification has additional tooling requirements; this command is a release gate, not a minimal prerequisite for reading or editing JSON. A full game gate was **not rerun just to publish this wiki**. The wiki's audit runs are listed in [Coverage and audit](#coverage).

## Keep useful evidence

Record the source SHA, relevant data diff, command, environment, exit status, seed/session, expected result and actual result. Preserve failing output. For random generation, retain the seed, candidate IDs and selection/configuration so the same failure can be investigated. A screenshot shows appearance; a path/connectivity check establishes access. Use both when that distinction matters.

The standing project workflow is autonomous headless processes and app-local events. Routine verification should not require taking over the desktop or assigning ordinary test execution to the owner.

## Source basis

[Focused runner](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/tools/critical_fix_regressions/verify_fixes.py) · [structure CLI](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/tools/structure_authoring.py) · [G6 authoring](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/tools/verify_g6_authoring.py) · [G6 diagnostic](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/tools/worldgen_g6_diagnostic.py) · [release coordinator](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/tools/verify_g6_release.py).
