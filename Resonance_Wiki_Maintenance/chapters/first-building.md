# Make your first randomly placed building

This workflow creates a small cottage, validates its actual contents and access, registers it for new town plans, and gives you an optional disposable world in which to inspect it. **Previewing a draft does not install it. Installing a file does not, by itself, make it eligible for modern town selection.** Both the layout and the selection entry are required.

The complete `owner_cottage_a.json` example below was created for this wiki and originally checked against G6 and revalidated against this G8 edition: all eight permitted transforms, followed by production grid and roadside previews. The example remains outside the game's installed catalog.

## 1. Establish the working folder

Use your production repository root, the folder containing `AGENTS.md`, `tools/` and `roguelike/`. The known Windows path in the repository's instructions is `G:\GameDev\RoguelikeProject`. Substitute your actual checkout path if it differs. The separate interpreter path below supplies the established dependencies; it does not select a different game's source.

```powershell
Set-Location 'G:\GameDev\RoguelikeProject'
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
git status --short
git branch --show-current
New-Item -ItemType Directory -Force authoring | Out-Null
```

Work on the established `main` branch and preserve unrelated changes. Before a substantial edit, create a uniquely named checkpoint tag under your normal project workflow. Avoid repeatedly running a copy command over your edited draft.

## 2. Save a complete draft

Save the following as `authoring/owner_cottage_a.json` using UTF-8. This is a complete accepted format, with no omitted placeholder rows. Its food, readable and container IDs all exist at the documented revision.

```json
{
  "id": "owner_cottage_a",
  "category": "residential",
  "description": "A compact owner-authored cottage with food, a readable note and a supply crate.",
  "width": 9,
  "height": 7,
  "legend": {
    "#": "wall",
    ".": "floor",
    "+": "door_closed"
  },
  "layers": [
    "#########",
    "#.......#",
    "#.......#",
    "#.......#",
    "#.......#",
    "#.......#",
    "####+####"
  ],
  "special_tiles": [
    {
      "x": 2,
      "y": 4,
      "type": "item",
      "item_id": "crow_jerky"
    },
    {
      "x": 4,
      "y": 2,
      "type": "item",
      "item_id": "research_note",
      "text_id": "lab_label_equipment"
    },
    {
      "x": 6,
      "y": 4,
      "type": "container",
      "decor_id": "crate",
      "loot_pools": [
        "commoner_kitchen"
      ]
    }
  ],
  "placement": {
    "version": 1,
    "contexts": [
      "grid",
      "roadside"
    ],
    "weight": 1,
    "rotations": [
      0,
      90,
      180,
      270
    ],
    "mirror_x": true,
    "buffer": 1,
    "approach": 2,
    "road_relation": "frontage",
    "entrances": [
      {
        "id": "main",
        "x": 4,
        "y": 6,
        "normal": "S",
        "width": 1,
        "role": "main",
        "required": true
      }
    ],
    "targets": [
      {
        "x": 4,
        "y": 4,
        "kind": "floor",
        "required": true
      },
      {
        "x": 2,
        "y": 4,
        "kind": "item",
        "required": true
      },
      {
        "x": 4,
        "y": 2,
        "kind": "readable",
        "required": true
      },
      {
        "x": 6,
        "y": 4,
        "kind": "container",
        "required": true
      }
    ]
  }
}
```

The footprint is nine columns by seven rows. The main entrance is at source coordinate `(4,6)`, facing south. `targets` declare what must remain usable; they do not spawn the food, note or crate. The corresponding `special_tiles` records spawn those objects. A valid container target checks a legal nearby interaction position, since the player need not stand on the crate.

## 3. Edit visually if useful

Open the repository's `layout_painter.html` in your browser. Its adjacent scripts and catalog must remain under `tools/structure_editor/`. Choose the ordinary-building route and residential category, then import your draft. Edit its terrain, content records or Placement metadata. Use **Apply ID** when giving a variation its own identity.

Export the complete JSON and save the downloaded file deliberately as your draft. If the browser adds `(1)` to the filename or places it in Downloads, point validation at that exact exported file. Validating an older draft does not check your new edits.

## 4. Check every orientation

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/owner_cottage_a.json --route ordinary_building --category residential --orientations --output evidence/authoring/owner-cottage-orientations.json
```

Look for `passed: true`, then open the JSON and adjacent numbered SVG files. This example allows four rotations and horizontal reflection before rotation, giving eight previews. The checks include declared required entrance cells and targets. These SVGs are diagnostic maps, not artwork from the game renderer.

If you remove an orientation from `placement.rotations`, the authoring command only checks those you retain. Permit meaningful orientations deliberately; extra rotations do not increase the asset's random weight.

## 5. Check actual planned placement

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/owner_cottage_a.json --planned --category residential --role residential --context grid --seed 20261023 --output evidence/authoring/owner-cottage-grid.json
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/owner_cottage_a.json --planned --category residential --role residential --context roadside --seed 20261023 --output evidence/authoring/owner-cottage-roadside.json
```

These commands add the draft only in memory to the selected role while retaining the installed mixed policy. They generate the plan and complete selected scenes with real contents and final access checks. Inspect the report's placements, rejected candidates and produced previews. A valid asset can be eligible but unselected in another seed; direct validation and random selection answer different questions.

## 6. Install the asset and register its roles

After reviewing the draft, install it under an unused filename. If the destination already exists, inspect it and choose whether you are updating that asset or creating a different ID; do not silently overwrite unrelated content.

```powershell
if (Test-Path -LiteralPath roguelike/data/buildings/residential/owner_cottage_a.json) {
  throw 'Destination already exists. Review it before replacing anything.'
}
Copy-Item -LiteralPath authoring/owner_cottage_a.json -Destination roguelike/data/buildings/residential/owner_cottage_a.json
```

Open `roguelike/data/generation/settlement_profiles.json`. Add this object to **each** intended role array, preserving the existing entries:

```json
{"asset":"owner_cottage_a","weight":1,"max_per_settlement":4}
```

For this cottage, those arrays are `profiles.grid.roles.residential` and `profiles.roadside.roles.residential`. Add it to both if you want both forms to use it. Adding an ID only to the grid profile does not register it for roadside settlements. Do not add a legacy `pools` object to current version-3 `g3_config.json`.

The filename makes the document discoverable, the internal `id` supplies references, the existing category folder supplies its loader route, `placement.contexts` allows the geometry, and the role entries admit it to selection. Keep them aligned.

## 7. Check the installed result

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output evidence/authoring/installed-catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --refresh-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --world-plan --seed 20261023 --output evidence/authoring/installed-world.json
git diff -- roguelike/data/buildings/residential/owner_cottage_a.json roguelike/data/generation/settlement_profiles.json tools/structure_editor/catalog.js
```

The catalog checks structure definitions. The world-plan command checks selection policy and fitting. Catalog freshness is a separate check against raw checkout bytes; refresh and reload the painter after content changes. The shipped catalog may also need regeneration after a different checkout's byte representation changes its identity. Refreshing the editor catalog is a generated-file update, not a repair to invalid JSON.

Restart before play because definitions are loaded and cached. A new plan is required to observe changed memberships, weights and caps. Optional play uses the existing production source with a new disposable save root:

```powershell
& $ResonancePython -X utf8 tools/play_disposable.py --seed 20261023 --session owner-cottage-first
```

Choose an unused session name. Existing generated maps are preserved; revisiting them will not make the new cottage appear. A world-plan report is usually quicker than wandering randomly while trying to establish that registration worked.

## Useful variants

For a house with a separate service entrance, start from `roguelike/docs/examples/g5_service_house.json`. For a workshop with existing readables, a scene and a real crate, use `g5_workshop.json`. For the rural route, use `g6_wayhouse.json` and the separate POI workflow. Complete examples are preferable to combining partial snippets from different historical routes.

## Sources

- [CLI behavior and output contract](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/tools/structure_authoring.py)
- [Placement validation and transformations](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/placement.py)
- [Role registration and selection validation](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/settlement_selection.py)
- [Complete existing authoring recipes](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/docs/STRUCTURE_AUTHORING.md)

## G7 composition integration

The current mixed parent workflow is documented in [Compounds](#compounds). A building export supplies the consumed child structure; a separate recipe supplies two required slots, an optional third slot, common paths, private bounds and permitted parent/child transforms. The existing painter edits the building, not the recipe. Use actual exported bytes in `--child`. Run `tools/verify_g7_authoring.py` for inherited and compound workflows; direct focused discovery now supplies its own absolute tools import path. Keep previous evidence immutable.
