# Wilderness terrain — G10

New campaigns use coherent tree stands, clearings, vegetation patches, wet ground
and rock masses sampled in absolute world-tile coordinates. The eight existing
wilderness biomes retain their original world locations. Ash Wastes interiors use
gravel, ash and rock, with no automatic living plants. Roads, river crossings,
towns, authored sites and underground generation keep their existing ownership.

## Preview a draft

Run from the production root with the established dependency interpreter:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force authoring/g10 | Out-Null
Copy-Item roguelike/docs/examples/g10_wilderness_profiles.json authoring/g10/draft.json
& $ResonancePython -X utf8 tools/wilderness_preview.py --seed 20261023 --chunk 73 99 --size 2 2 --profile authoring/g10/draft.json --output authoring/g10/forest.json
```

The JSON report and PNG show the actual complete populated production path. The
PNG is explicitly **revealed comparison evidence**, not a normal-FOV play view.
The report identifies every chunk, the frozen policy and unchanged G9 plan,
terrain and resource counts, reachable resource opportunities, native actors,
required access, repair events and generation timings. It generates only the
requested 1–3 by 1–3 scenes, plus a one-chunk metadata halo. Planning creates no
local scenes. A preview never visits a campaign or installs the draft.

Omit `--profile` to preview installed defaults. `--image` selects a separate PNG
target. Outputs cannot replace game files or the draft; file aliases, symbolic
links and report/image collisions share the authoring destination protection.
`--data-root` is available for rehearsing installation in a disposable data catalog.

## Tune the small profile

The complete example and installed `data/generation/wilderness_profiles.json`
contain `version: 1` and exactly eight profiles. Every profile supplies:

| Field | Meaning and supported range |
|---|---|
| `palette.ground` | Walkable natural base ground. `varied_grass` uses existing functional plant resolution. |
| `palette.patch` | A different walkable natural surface, selected in broad patches. |
| `palette.obstacle` | Existing blocking `tree` or `rock`. |
| `scale` | Broad field scale, 8–96 world tiles. Larger values make larger stands/pools/masses. |
| `cover` | Cover threshold control, 0–0.68. This is not a guaranteed tile percentage. |
| `patch_amount` | Patch threshold control, 0–1. |
| `wet_amount` | Shallow-water threshold control, 0–0.6, with a small saved-moisture influence. |
| `transition` | Metadata overlap width, 0–12 tiles. Small values preserve abrupt biome edges. |

Natural palettes are restricted to existing grass, tall grass, mud, packed earth,
gravel, ash, shallow water, trees and rocks. Blocking ground, unknown fields,
nonfinite values and ineffective identical ground/patch palettes are rejected.
Ash interiors must retain mineral ground, rock and zero wet amount. Deliberate
transitions and explicit authored content remain visible at their edges.

Tile semantics matter: gravel costs 1.1 movement, ash 1.5, mud 2, tall grass 2.5
with concealment, and shallow water 1.5 with chill and drinking. Trees and rock
block movement and visibility. `grey_stone` blocks; it is not a walkable waste
floor. Living plants appear only through eligible ground and the existing plant
API. Native creature profiles, survival rates and loot tables are unchanged.

## Deliberate installation and recovery

Preview and inspect the draft first. Back up the installed file, then replace
only this explicit tuning input and refresh its derived catalog:

```powershell
Copy-Item roguelike/data/generation/wilderness_profiles.json authoring/g10/installed-backup.json
Copy-Item authoring/g10/draft.json roguelike/data/generation/wilderness_profiles.json
& $ResonancePython -X utf8 tools/wilderness_preview.py --seed 20261023 --chunk 73 99 --size 2 2 --output authoring/g10/installed.json
& $ResonancePython -X utf8 tools/structure_authoring.py --refresh-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
```

The draft and installed policy identities and resulting terrain should agree.
To recover, copy `installed-backup.json` back to the installed path, repeat the
preview and catalog refresh/check, and keep the reviewed backup. Installation
affects **new campaigns only**. Existing new-policy campaigns carry a complete
saved policy and its terrain/decor dependency identities. Editing or removing
the installed tuning file does not change their pending terrain. A missing or
malformed installed file prevents creating a new campaign and reports an error.

Historical worlds explicitly stay on the G9 surface route, including pending
scenes. A new campaign's required policy cannot be removed to obtain that fallback.
Changed or missing required terrain/decor definitions are rejected; restore
compatible definitions and retry. Existing visited scenes and mutations retain
their checkpoint ownership. F5 saves the explored state and F9 restores it through
the existing checkpoint validation and atomic installation path.

## Verification

```powershell
& $ResonancePython -X utf8 tools/verify_g10.py --evidence evidence/worldgen-g10/owner-verification
```

This bounded gate has finite child timeouts. It checks terrain and lifecycle
behavior, three ordinary seeds, before/after production views, safe draft and
installation/recovery workflows, and a short scripted ordinary expedition with
normal-FOV captures and checkpoint restoration. It uses guarded disposable saves.
The established unfiltered focused suite and production `verify_d.py` remain the
final implementation gates. G9's long controlled journey remains historical
geometry/persistence evidence; the short ordinary outing does not establish
whole-world survival balance or unaided player discovery.

Wiki upkeep is separately commissioned. This feature guide does not rebuild or
modify the existing owner wiki edition.
