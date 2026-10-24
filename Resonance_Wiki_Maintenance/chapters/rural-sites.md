# Add independent places beside country roads

G6 adds a separate pool of rural places along existing country roads. These are independent sites with their own mutable contents, **in addition to the single featured landmark**. Each accepted site currently contains one building and its complete protected access within one storage chunk.

Use `roguelike/data/generation/poi_profiles.json` for extra-site selection. Registering an asset in the featured-landmark role does not register it here, and registering it here does not change the featured-landmark pool.

## Start with a working rural draft

`roguelike/docs/examples/g6_wayhouse.json` is a complete 6 × 5 shelter with a main doorway, a separate required service doorway, a readable road marker, a populated coffer using `shrine_offering`, and a floor goal beside a blocking waystone. It permits all four quarter turns and declares the `landmark` placement context with a connected `spur` relation.

That context means the geometry is suitable for the rural/landmark fitter. Membership in a particular site's selection policy is a separate decision. The current extra-site validator accepts an explicit connected landmark context with `frontage` or `spur`; deliberately remote profiles cannot satisfy this connected route.

From the repository root, initialize drafts only if absent:

```powershell
New-Item -ItemType Directory -Force authoring/g6 | Out-Null
if (-not (Test-Path -LiteralPath authoring/g6/g6_wayhouse.json)) {
  Copy-Item roguelike/docs/examples/g6_wayhouse.json authoring/g6/g6_wayhouse.json
}
if (-not (Test-Path -LiteralPath authoring/g6/poi_profiles.json)) {
  Copy-Item roguelike/docs/examples/g6_poi_example.json authoring/g6/poi_profiles.json
}
```

Edit/import/export using the painter. Keep complete real container records and access targets; furniture symbols alone do not stock containers. When changing doorway cells, update full entrance spans, normals and any moved targets.

## Validate direct transforms and both road axes

```powershell
$Candidate = 'authoring/g6/g6_wayhouse.json'
& $ResonancePython -X utf8 tools/structure_authoring.py $Candidate --route ordinary_building --category wilderness --orientations --output evidence/authoring/g6-direct.json
foreach ($Normal in @('N','E','S','W')) {
  & $ResonancePython -X utf8 tools/structure_authoring.py $Candidate --assigned-site $Normal --category wilderness --output "evidence/authoring/g6-assigned-$Normal.json"
}
& $ResonancePython -X utf8 tools/structure_authoring.py $Candidate --site --category wilderness --poi-config authoring/g6/poi_profiles.json --seed 20261023 --output evidence/authoring/g6-selected.json
```

Replace `$Candidate` with the actual browser download if that is the file you edited. N/S entrances face horizontal roads; E/W entrances face vertical roads. `--assigned-site` is deliberately controlled: it uses one asset, one desired site and a required frontage normal while retaining the production fitter, protection rules, contents, population and final access validation.

The natural `--site` preview retains policy selection and can legitimately report nonselection. Its report identifies the parent country route, segment, exact join, side, primary entrance, placement and content receipts. The SVGs distinguish whole-plan geometry, detailed attachment geometry and complete-scene diagnostics. They are not gameplay screenshots.

## Install the two linked parts

The layout belongs at `roguelike/data/buildings/wilderness/<id>.json`. Its exact ID must also appear in `poi_profiles.json`:

```json
{"asset":"g6_wayhouse","weight":1,"cap":2}
```

The complete example policy retains the four existing assets and adds this draft. Review the diff before replacing the policy so later manual additions are not lost. If the draft ID already exists, decide deliberately whether you are updating it or making a new variation.

After installation, run `--catalog`, refresh/check the editor catalog, and run `--world-plan`. Changes affect new-world selection. The preview commands themselves do not install anything or open personal campaigns.

## The installed policy's controls

| Key | Default | Accepted range | Meaning |
|---|---:|---|---|
| `version` | 1 | 1 | Policy schema. |
| `id` | `rural-sites-v1` | Nonempty string | Saved profile identity. |
| `minimum`, `maximum` | 2, 4 | Integers 0–8, minimum ≤ maximum | Inclusive desired-count draw; minimum is also the publication obligation. |
| Asset `weight` | 1 | Finite positive ≤1000 | Multiplies the layout's placement weight. |
| Asset `cap` | 2 | Integer 1–8 | Hard accepted count across additional sites; excludes the featured landmark. |
| `repeat_multiplier` | 0.2 | Greater than 0, at most 1 | Soft penalty if this matches the nearest accepted site's asset. |
| `spacing_tiles` | 80 | Integer 1–4096 | Minimum Manhattan distance between extra-site joins, in world tiles. |
| `town_clearance_tiles` | 24 | Integer 0–256 | Manhattan join distance from the town's protected outer rectangle. |
| `junction_clearance_tiles` | 12 | Integer 1–80 | Join distance from perpendicular road intersections and bends. |
| `locations` | plains, forest, heath | Nonempty unique subset of these IDs | Allowed rural biomes. |
| `sample_step_tiles` | 16 | Integer 8–80 | World-coordinate lattice used to sample existing roads. |
| `enumeration_limit` | 8192 | Integer 1–65536 | Maximum raw road-side examinations before deduplication. |
| `candidate_limit` | 512 | Integer 1–4096 | Maximum canonical seeded joins considered. |
| `fit_budget` | 1024 | Integer 1–4096 | Bound on real transform-fit trials or empty-frontage asset trials. |

Spur length has **one authority**: `max_spur_tiles` in `g3_config.json`, currently 12. There is no second POI spur-length field. Layout buffers and entrances belong to the consumed structure definition.

The initial assets are `roadside_shrine_a`, `hunter_cabin`, `shepherds_hut_a` and `waymarker_shelter_a`. Their cap total must be sufficient for the minimum, but need not be sufficient for the maximum. The nearest repeat comparison uses Manhattan distance between saved joins, with site ID breaking ties. A repeat penalty is not a guarantee that every site has a distinct asset.

## Desired count, accepted count and shortfall

The desired count is drawn once and saved. Selection stops when it reaches that count. If it falls short but meets the configured minimum, the world may publish with `site_selection.shortfall_reason`. Falling below the minimum rejects the candidate world. Every accepted extra becomes a durable obligation, even when it is above the minimum.

For an explicit controlled shortfall demonstration, a policy containing only `hunter_cabin` with cap 2, minimum 2 and maximum 4 at seed 20261023 requests three and accepts two, recording cap exhaustion. Setting both count bounds to zero demonstrates valid nonselection. A minimum of two with a fit budget of one demonstrates a rejected minimum. These are test policies, not promises about ordinary frequency.

## Where sites can fit

The planner samples existing straight **country** road segments; town streets and other site approaches are not parents. It does not build a new country route to chase a candidate. It excludes town members, river chunks, special anchors, the featured chunk, existing accepted-site chunks and chunks with submaps. It also preserves crossing decks/approaches, private reservations and road-junction clearance.

Footprint, buffer, full primary door span and complete approach must fit the same 80 × 43 chunk. A site attaches perpendicularly to its exact saved parent segment. A nearby different road cannot stand in for a wrong or missing parent.

## Diagnose a rejected site

| Report reason | Check |
|---|---|
| Missing connected landmark context | Explicit placement contexts and `road_relation`, then exact policy ID. |
| No eligible permitted transform | The requested road axis and actual allowed doorway normals. |
| Footprint/buffer or approach conflict | Whole reserved rectangles, private approaches, water banks and assigned road. |
| Spans a storage chunk | Join location, transformed dimensions, buffer and full access length. |
| Complete entrance inaccessible | Every cell of both main and required service entrances after containers/decor are realized. |
| Bridge approach clearance | Use an ordinary road segment away from the crossing reservation. |
| Hard cohort caps exhausted | Add eligible capacity, deliberately raise a cap, or accept a permitted shortfall. |
| Minimum failure | No world was published; inspect budgets, geometric exclusions, eligibility and minimum together. |

The bounded rejection examples and counts are in `site_selection`; accepted plots also retain rejected-transform details. Preview a policy copy using `--world-plan --poi-config <draft>` before installation.

## Sources

- [Current POI policy](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/data/generation/poi_profiles.json)
- [Validation, candidates, selection and durable attachments](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/poi_selection.py)
- [Complete rural draft](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/docs/examples/g6_wayhouse.json)
- [G6 owner guide](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/docs/owner/WORLDGEN_G6.md)
