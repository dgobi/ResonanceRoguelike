# Independent G10 entrance-access witness

Reviewed `main` at **7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b**. This probe was run in a disposable Linux/Python 3.12.14 environment with pygame 2.6.1, tcod 19.3.0 and NumPy 2.3.5. It does not claim to rerun the Windows production gate.

## Finding

On ordinary seed **20261023**, Drowned Wood chunk **(44, 8)** owns the cave `submap_44_8_0`, named **Arnevel Vault**. The completed G10 scene passes its production checks, but the cave stair cannot be reached from any natural scene edge.

| Stage | Anchor | Reachable cells | Reachable boundary cells | Cave stair accessible from exterior |
|---|---|---:|---:|---|
| New terrain, before entrance stamp | (24, 10) | 152 | 29 | Not stamped yet |
| After entrance stamp | (24, 10) | 79 | 0 | No: stair at (14, 5) |
| Completed dressing/population | (24, 10) | 79 | 0 | No |
| Current supported G9 route over the same saved coarse world | (40, 21) | 2,788 | 209 | Yes: stair at (22, 12) |

The G9 comparison uses the current runtime's supported legacy route over genuine pre-edit G9 coarse metadata. It is not a fresh execution of the historical G9 checkout. The G10 handler probe separately starts the actual normal game at the same seed and reproduces the scene.

Static reachability uses the existing `generation.access` rules: eight-way movement, openable doors and blocking decor. It deliberately excludes dynamic actors. The final cave stair is outside the union of every exterior-connected component; choosing a different boundary entry cannot solve it. The one native Plague Crow does not cause the separation. Trees, natural rock and walls lack harvest/gather escape mechanics in the inspected terrain definitions.

## Actual handler evidence and limits

The probe fixtures the player in adjacent chunk (43, 8) at (79, 1). A real right-movement input enters (44, 8) at (0, 1). That exterior component has 87 cells and cannot reach the stair. Native AI and survival run; invincibility is off.

Separately, explicit fixture positioning places the player on the inaccessible stair solely to test `>` descent and `<` ascent. Those real handlers return the player to (14, 5) inside the sealed 79-cell component. No additional positioning is needed underground. F5/F9 retains the scene and the same sealed component.

**This does not show normal walking trapping a player inside the cave.** Normal exterior play cannot enter that cave. It shows an inaccessible underground discovery, plus a sealed arrival/return pocket under the separately disclosed controlled placement.

## Why the current checks miss it

- `wilderness.materialize()` selects the largest natural component touching an edge before authored entrances are stamped (`roguelike/generation/wilderness.py`, 246–267 at the reviewed revision).
- `create_planned_surface()` keeps the spawn and road-edge cells as required anchors. A roadless scene has only the interior spawn (`roguelike/generation/planned_scene.py`, 91–93).
- `_place_submap_entrance()` checks that the stair and retained anchors can reach one another. It does not require them to remain reachable from an exterior edge (`roguelike/generation/region_gen.py`, 476–478).
- Final access validation repeats the local relation and checks roads/sites/placements. A locally connected, externally sealed cave can therefore pass. The G10 boundary regression uses forest (73, 100), not this entrance-stamping case.

Preserve a genuine exterior access witness through the complete pipeline and validate the completed scene. Prefer rejecting/reselecting the offending candidate while keeping natural cover and existing ownership. The witness does not justify clearing every decorative pocket or connecting every edge.

## Reproduce

Use the repository's dependency interpreter. The script sets dummy SDL drivers, resolves imports through `--repo`, writes only under `--out` and temporary save roots, and does not edit tracked files or access a personal campaign.

```text
python reproduce_g10_entrance.py --repo PATH_TO_RESONANCE --out PATH_OUTSIDE_REPOSITORY
```

The script reports `defect_observed: true` at the reviewed revision. Exit success means the probe completed; inspect the JSON to distinguish the defect from a repaired result. Its current implementation expects the same cave and usable west-edge test point, so adapt those narrow fixtures if a later authorized fix deliberately changes them.

Add `--sample` only to repeat the bounded discovery sample:

```text
python reproduce_g10_entrance.py --repo PATH_TO_RESONANCE --out PATH_OUTSIDE_REPOSITORY --sample
```

## Original discovery sample

`probe.json` records **60** complete production scene creations over the eight wilderness biomes of seed 20261023. The selection uses `Random(1025)` and up to four coordinates from each sorted biome/submap-presence stratum. Deep Mountain has no submaps, giving 60 rather than 64 samples. All 60 materialized successfully; (44, 8) was the one sampled completed scene whose default/stair component lacked a boundary. This targeted sample is defect-discovery evidence, **not a statistical estimate of world prevalence**.

The original sample JSON also records a separate low-priority observation: syntactically invalid installed profile JSON aborts `DataLoader` before restoration. That is not the access defect and is not required to fix it.

## Handoff files

- `reproduce_g10_entrance.py`: portable reproduction.
- `entrance-isolation.json`: stage and supported-G9 comparison.
- `entrance-handlers.json`: controlled real movement, descent/ascent and F5/F9.
- `probe.json`: original 60-scene sample and disclosed secondary observation.
- `before-entrance.png`, `after-entrance.png`, `final.png`: explicitly revealed production views.
- `boundary-entry-normal-fov.png`, `cave-return-normal-fov.png`: normal-FOV views of controlled handler checks, not an ordinary itinerary.

Large pickles, disposable save roots and duplicate verification output are unnecessary for the handoff. The exact current repository and the script reproduce the witness.
