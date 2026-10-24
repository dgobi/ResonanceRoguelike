# Tune towns, roads and building variety

Current fresh-world tuning uses **four files with separate jobs**: `roguelike/data/generation/g3_config.json` controls world placement and road widths, `settlement_layouts.json` controls local streets, common and frontage, `roguelike/data/generation/settlement_profiles.json` controls which assets fill which roles, and `country_network.json` controls optional country connections. The historical filename `g3_config.json` remains active at G9. The older `town_config.json` is not the current shared-planner control surface.

Changes here affect **new plans**. They do not reselect a saved pending building, alter a visited town or add new sites to an older world.

## Geometry controls

The current geometry configuration is complete and uses `version: 4`, `country_network_version: 1`, `settlement_layout_version: 1` and `selection_profile_version: 1`. Do not insert an old `pools` field into it. An explicit version-1 override retains a compatibility path with different meaning; it is not the recommended authoring format.

| Key | Current value | Allowed values / units | Practical effect |
|---|---:|---|---|
| `settlement_count` | `[2,4]` | Inclusive integer range, both endpoints 2–8 | Number of settlements; the near-start site is counted within it. |
| `minimum_separation_chunks` | 12 | Integer 3–128 chunks | Euclidean separation between settlement anchors. |
| `near_start_radius_chunks` | 10 | Integer 2–128 chunks | Requires one eligible counted settlement near the start. |
| `forms` | `["grid","roadside"]` | Exactly this ordered pair | Alternating forms; not an open-ended list of generators. |
| `road_width_tiles` | 3 | Integer 1–5 tiles | Full country-road width. |
| `street_width_tiles` | 3 | Integer 1–5 tiles | Full grid-town street width; independent of country roads. |
| `plot_spacing_tiles` | 18 | Integer 14–40 tiles | Historical slot spacing; G8 uses layout `frontage_tiles`. |
| `setback_tiles` | 2 | Integer 1–8 tiles | Minimum setback; profile requirements can increase it. |
| `max_spur_tiles` | 12 | Integer 2–24 tiles | Maximum complete primary approach; also the authority for extra rural sites. |
| `route_search_nodes` | 16384 | Integer 16–65536 | Bound for each road search. |
| `site_search_limit` | 16384 | Integer 1–16384 | Settlement-site candidate bound. |

Increasing separation while increasing settlement count can make the request infeasible. Reducing a search budget can leave feasibility unresolved. The planner rejects an invalid required world rather than silently breaking its obligations. Inspect the diagnostic reason before changing several controls at once.

## Selection profiles and roles

`settlement_profiles.json` has `version: 1` and exactly three profiles: `grid`, `roadside`, `landmark`. Each profile contains an ID, `roles`, `minimum`, `schedule`, `repeat_multiplier` and `required_fit_budget`. These are complete policy objects; unknown partial schemas are rejected.

| Form | Roles | Required baseline |
|---|---|---|
| Grid | residential, commercial, support, civic | At least one residential and one commercial; exactly one civic `bell_tower_a`. |
| Roadside | residential, commercial, support | At least one residential and one commercial. |
| Featured landmark | landmark | Exactly one landmark. |

Each role array contains records such as:

```json
{"asset":"apothecary_a","weight":2,"max_per_settlement":5}
```

The asset must be installed and explicitly support the required context. Civic candidates require the `civic` context; ordinary town roles require the relevant `grid` or `roadside` context. Connected roles reject `road_relation: "remote"`. Within one form, an asset cannot be duplicated across different role arrays. The same asset can be registered in both grid and roadside profiles.

`weight` is a finite positive multiplier at most 1000. `max_per_settlement` is an integer from 1 through 128 and counts accepted instances across all chunks of that one settlement. It is a hard cap, not a suggested frequency. Role minima are integers 0–8 subject to the baseline obligations above, and their candidate caps must be sufficient.

## How selection produces variety

The effective draw weight is:

**layout `placement.weight` × role `weight` × applicable repeat multiplier**

The engine draws the asset before trying its permitted transforms. A four-rotation asset does not get four times the weight of a one-rotation asset. Failed fitting branches consume no accepted cap.

Required assignments are reserved first using bounded backtracking. The default `required_fit_budget` is 256, with valid range 1–4096. **Since G6, one budget unit is one transform fit, or an asset trial with no eligible frontage.** The older G5 report's asset/slot wording is historical. G6 can revisit an earlier asset's alternative transform when a later required role fails. Budget exhaustion reports unresolved feasibility; exhausting all enumerated alternatives is a different outcome.

G8 required commercial choices prefer the civic join, then actual arrival distance. Ordinary lots are stably ordered by Manhattan distance from the saved country arrival, with stable identity tie breaks. Remaining slots use the ordered schedule. The installed schedule is:

```json
["commercial","residential","support","residential"]
```

This helps place a commercial focus near arrival while mixing residential and support use. It does not change streets, native AI or district definitions.

The default repeat multiplier is `0.2`, valid in `(0,1]`. For settlements, the G8 reference neighbor is the nearest accepted **frontage join by Manhattan tile distance**, with the stable plot ID breaking ties. Historical formats preserve slot-index semantics. This is a soft preference, not a hard spacing rule. A repeated asset can still win. If only one eligible choice remains, the report records a soft fallback. Optional plots that cannot fit remain explicit vacancies rather than exceeding caps.

## Live connected candidates

| Role | Current IDs in both ordinary settlement forms |
|---|---|
| Residential | `house_small_a`, `house_small_b`, `house_two_room_a`, `house_hearth_a` |
| Commercial | `market_stall_a`, `shop_a`, `apothecary_a`, `workshop_a` |
| Support | `storehouse_a`, `tool_shed_a`, `shrine_a` |
| Civic, grid only | `bell_tower_a` |
| Featured landmark | `roadside_shrine_a`, `hunter_cabin`, `shepherds_hut_a`, `waymarker_shelter_a` |

Other installed buildings remain available to their supported legacy route or direct previews, but are not automatically added to modern planned towns. A folder called `wilderness` is not a general random wilderness scattering rule.

## Preview a policy before installing it

Copy the complete current policy into an unused draft path, edit that copy, and pass it explicitly. Keep existing drafts when repeating setup:

```powershell
if (-not (Test-Path -LiteralPath authoring/settlement_profiles.json)) {
  Copy-Item roguelike/data/generation/settlement_profiles.json authoring/settlement_profiles.json
}
& $ResonancePython -X utf8 tools/structure_authoring.py --world-plan --selection-config authoring/settlement_profiles.json --seed 20261023 --output evidence/authoring/tuned-selection.json
```

For geometry, use `--config authoring/g3_config.json`. The complete shipped `roguelike/docs/examples/g5_selection_example.json` is also a working example: it raises the grid apothecary multiplier, lowers a house cap and reduces the repeat multiplier.

Inspect accepted counts, vacancies, required-role diagnostics, rejected transforms and SVG geometry. A small sample can expose errors and give examples of the resulting mix; it does not establish long-run placement percentages. Once reviewed, make a deliberate file replacement, inspect the diff, refresh the editor catalog if its source identity changed and test with a fresh world.

## Public and private space

Opposing buildings may share cells belonging to their assigned public road. Their footprints, buffers and private approach areas remain exclusive. The actual assigned road's full width controls setback and fitting, including even widths; do not assume all roads have the same width.

A null cell inside a layout preserves terrain while still belonging to the reserved structure area. Enlarging an attractive yard or buffer can therefore cause valid optional vacancies. That is a geometry consequence, not a failed random draw.

## Sources

- [Geometry schema and fitter](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/generation/world_plan.py)
- [Current installed selection profiles](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/data/generation/settlement_profiles.json)
- [Selection weighting, caps and required search](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/generation/settlement_selection.py)
- [G6 correction to required-transform search](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/docs/owner/WORLDGEN_G6.md)

## Preview and tune the country network

The authoritative complete guide is `roguelike/docs/COUNTRY_NETWORK.md`; the downloadable `g9_country_network.json` example contains every required field. The painter continues to edit buildings. Network previews use disposable geometry and do not open campaigns or install policy.

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py --network-preview --seed 20261023 --output authoring/network-ordinary.json
& $ResonancePython -X utf8 tools/structure_authoring.py --init-network authoring/network-draft --output authoring/network-init.json
& $ResonancePython -X utf8 tools/structure_authoring.py --network-preview --network-policy authoring/network-draft/g9_country_network.json --seed 20261023 --output authoring/network-tuned.json
```

JSON reports include all fixed primary pairs, exact before/after distances, accepted and rejected candidates, budgets and topology. Adjacent SVG and PNG overlays show gold baseline and green accepted connections, including reused portions. Initializing again preserves existing draft edits. Input paths, initializer targets, generated reports and catalog outputs share preflight and staged collision checks, including hard-link aliases.

| Policy field | Default | Valid range |
|---|---:|---|
| `version` | 1 | Exactly integer 1 |
| `max_shortcuts` | 2 | Integer 0–2 |
| `max_added_fraction` | 0.25 | Finite 0–0.25 |
| `min_saved_steps` | 500 | Integer 1–100000 physical steps |
| `min_relative_improvement` | 0.25 | Finite 0.01–1 |
| `candidate_pair_limit` | 8 | Integer 1–32 |
| `search_expansion_limit` | 8192 | Integer 1–16384 |
| `world_expansion_budget` | 32768 | Integer 1–65536 |

Policies must be complete; unknown fields, missing fields, booleans in numeric fields and non-finite values fail. One shared construction budget counts overlapping accepted connections once. Previously accepted roads change the next connection's marginal benefit.

Try `max_added_fraction: 0.1` in the draft: the same ordinary seed adds no connection. Try `max_shortcuts: 0`: a new format-7/wg9 world records `disabled` and preserves the complete G8 baseline content. This does not turn an existing G8 save into a G9 world. Seed 0 illustrates `no qualifying candidate`; `world_expansion_budget: 1` illustrates bounded exhaustion. Neither result proves that no legal beneficial corridor exists. A malformed policy or broken required baseline is an error, not a zero-road outcome.

For deliberate installation, first copy the complete data directory to a disposable authoring directory, preserve its original network policy bytes, replace only that policy with the reviewed draft, and run the CLI with `--data-root` pointing there. Run `--catalog`, `--refresh-editor-catalog` with a disposable `--editor-catalog` target, and `--check-editor-catalog`. Restore the saved policy bytes and repeat; unrelated-file hashes must stay unchanged. `tools/verify_g9_authoring.py` executes this sequence with sentinels, plus all inherited workflows. Exact commands and production recovery are in `COUNTRY_NETWORK.md`.

Production installation is a separate deliberate edit to `roguelike/data/generation/country_network.json`, followed by previews, review and a named Git checkpoint/commit. For recovery, inspect the diff and recover the intended earlier policy using `git show <reviewed-checkpoint>:roguelike/data/generation/country_network.json` into a draft before replacing the single reviewed file. Preserve unrelated edits; do not reset the checkout. Existing saved worlds keep their resolved connections regardless of today's policy.
