# Author entrances and underground layouts

Surface entrances and underground layouts use different consumers from ordinary town buildings. Start from a file belonging to the intended route, import it directly, and validate that route. Copying every field from a town building into a laboratory does not give the laboratory that building's decor, placement or random-selection semantics.

## Surface entrances

The current catalog contains six entrance documents under `roguelike/data/entrances/`. An entrance's `entrance_type` associates it with an existing submap type. Variants matching that type are selected uniformly; the descriptive `variant` field is not a weighting mechanism.

| Submap type | Existing entrance type |
|---|---|
| `barrow`, `deep_vault` | `barrow_mound` |
| `cave` | `rock_face_cut` |
| `vault`, `sunken_ruin`, `cellar`, `crypt`, `laboratory` | `sunken_ruin` |
| `flooded_ruin` | `drowned_threshold` |

This is the current `SUBMAP_ENTRANCE` mapping in `region_gen.py`. A new arbitrary `entrance_type` string will not automatically make a new kind of underground place appear. Likewise, an available `overgrown_gatehouse` asset does not prove the current submap mapping selects it.

An interior entrance consumes `layers`, `legend`, supported `legend_weights` and `entrance_type`. It must contain real accessible down-stair terrain. The placement code checks the whole footprint and protected spaces, and validates meaningful access to the stairs before establishing links. It can use a bounded valid bare-stair fallback if a full authored footprint cannot fit; it must not publish an isolated unusable stair.

The existing `connection_point`, `spawn_offset` and `edges` fields are retained but **do not control the surface interior placement route**. They have meaning in the separate edge-stamping API. Ordinary entrance previews use the interior route. Do not apply an edge API's rotation/anchor explanation to every surface entrance.

### Edit an entrance variant

1. Copy an existing matching file to a draft, preserving its working stairs and approach while changing appearance.
2. Give a new variation a unique ID. Keep `entrance_type` matched to the submap family you intend to vary.
3. Maintain a rectangular grid, known terrain IDs and real down-stair terrain.
4. Preview the exported draft explicitly, because a file outside the installed catalog cannot infer its route:

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/my_barrow.json --route interior_entrance --output evidence/authoring/my-barrow.json
```

5. Use an explicit access sidecar if you need to certify a particular exterior entry and stair target. A successful direct stamp alone is not the full campaign placement/return-travel check.
6. Install deliberately at `roguelike/data/entrances/<id>.json`, validate the catalog and refresh the painter catalog. Test in a fresh disposable world or a controlled complete-scene fixture; visited entrances retain saved state.

For an unchanged installed entrance, route inference works:

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py roguelike/data/entrances/barrow_mound_a.json --output evidence/authoring/barrow.json
```

### Weighted entrance terrain

`legend_weights` maps a legend character to weighted records containing `tile` and `weight`. Every character still needs its fixed legend entry. A chosen `tile: null` means fall back to that character's fixed legend. Only if the fixed legend itself is null is underlying terrain preserved. This differs from treating every weighted null as a blank cell.

## Authored underground layouts

The shipped authored laboratory is **60 × 16**, centered in an 80 × 43 map initially filled with walls. The historical layout guide's 60 × 35 size is stale. The current validator permits a maximum source extent of 80 × 43, but use room for an enclosing wall and validate actual access; the old “78 × 41” advice is a practical border convention, not the present compiler's exact size limit.

An authored submap consumes:

- `layers` and `legend` for terrain;
- `player_start` for the source-relative arrival, falling back to the layout center if omitted;
- supported `special_tiles`;
- `exit_direction`, `exit_x` and `exit_y` as the existing fallback when no up-stair terrain is painted.

A top-level `stairs_up: {x,y}` object is **not** the command that paints a staircase. Paint actual `stairs_up` through the legend/grid, or deliberately understand the consumer's exit fallback. An ordinary building containing stair terrain still needs a separate submap/link integration; artwork alone does not create travel.

The authored-submap route does not consume an ordinary `decor_layer` or `legend_weights`. The starting laboratory has a small code-owned candle placement near its arrival; that does not generalize into automatic decor-layer support. Top-level stele text metadata is retained, but physical body/stele behavior remains deferred.

## Safely change the existing laboratory

Import `roguelike/data/layouts/starting_lab.json` into the painter's authored-submap route. Keep its ID when intentionally editing the existing starting laboratory, and preserve a usable arrival, route to the real up-stair and required readable items. Export a draft outside the installed tree and preview it:

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/starting_lab.json --route authored_submap --output evidence/authoring/lab-draft.json
```

Inspect the report's actual arrival and realized items. Direct ordinary/plaza/entrance stamps do not invent a generated player arrival; this submap route has one to check. The production complete-scene path also verifies stairs and return access after population.

After deliberate installation, restart and use a new disposable session. Loading an old visited laboratory restores that map; it does not rebuild it from your edited floor plan.

## Add a different authored level

Saving `roguelike/data/layouts/my_level.json` registers the definition but does not select it. A new `SubMap` must have `layout_id: "my_level"`, along with the correct identity, parent/link and generation metadata. The current starting laboratory assignment is in `generation/world_gen.py`; actual layout generation is in `generation/local_gen.py`. There is not a general JSON pool for scheduling arbitrary new authored submaps in the current owner workflow.

This integration is a code task when no existing selection point refers to your layout. It needs a controlled first-entry/return-travel and persistence check. The old statement “no code changes are needed to add new layouts” is only true when an already implemented route is deliberately made to reference the new definition.

Do not use “delete all saves” as an authoring step. A uniquely named disposable session supplies fresh generation without changing a personal campaign.

## Sources

- [Submap type to entrance mapping and protected placement](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/generation/region_gen.py)
- [Authored submap consumer](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/generation/local_gen.py)
- [Starting laboratory source](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/data/layouts/starting_lab.json)
- [World creation and `layout_id` assignment](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/generation/world_gen.py)
- [Separate edge-stamping API](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/generation/layout_stamper.py)
