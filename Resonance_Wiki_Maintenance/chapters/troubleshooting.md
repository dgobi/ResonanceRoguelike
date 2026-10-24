# When an edit does not work

Start with the symptom and the source path. The most common distinctions are a definition that did not load, a definition that loaded but was not selected, a saved instance that retained old state, and a field that has no implemented consumer.

| Symptom | Check first | Next action |
|---|---|---|
| Game cannot find data, fonts or assets | Working directory and path spelling | Use the current launcher or change into `roguelike/` before `main.py`. Current font paths use `assets/Fonts/`. |
| Dependency import fails | Selected Python executable | Use the intended environment, install its matching requirements, then `pip check`. |
| My JSON edit has no effect | Restart; correct file/loader; exact ID | Check the fresh instance, then the field's consumer. A file extension/folder alone does not guarantee loading. |
| One new definition replaces another | Duplicate IDs or duplicate object keys | Give the new definition a unique ID and repair references; do not depend on load order. |
| New item looks wrong | Item `tile`, sprite-map key, sheet name and crop bounds | Inspect the exact registered mapping and atlas dimensions. A gameplay ID can differ from the visual tile ID. |
| Item exists but will not equip/use | `slot`, `on_use`, current handler | Copy a working definition of the same kind. An arbitrary string does not implement a handler. |
| Creature can be debug-spawned but never appears naturally | Active zone spawn list | A creature's own descriptive `spawn_zones` is not registration. Check the zone route and its `chance`/count behavior. |
| Building validates but never appears | Current eligible pool, context/role, sidecar and fit | Use a natural `--planned` or `--site` preview, inspect selection, then test several seeds. |
| Building is selected but rejected | Entrance normal, width, clearance, required goals, reservations | Read the candidate report. Test every permitted transform and complete surrounding access. |
| POI appears in an assigned-site preview only | Natural selection and policy constraints | Assigned previews establish compatibility in a controlled context; they do not guarantee random selection. |
| Existing town ignores changed weights | Saved plan identity | Generate a new disposable world. Do not delete individual cached maps to bypass plan ownership. |
| Scene entry fails after structure edits | Saved plan dependency/geometry mismatch | Retain the error and source revision; use matching old data or a fresh test world. |
| Editor says catalogue is stale | Generated catalogue identity | Refresh with the actual CLI, inspect the changed `catalog.js`, then recheck. Byte/line-ending identity can matter. |
| A lit torch does not satisfy recipe heat | Crafting ambient-source route | Current ambient collection checks the `light` slot while normal light equip uses `offhand`; use an actual nearby lit campfire for the documented working heat source. |
| Recipe says ingredients missing | Per-unit allocation, keyword tier, ambient sources | One item instance cannot pay two required component units just because it carries both tags. |
| Perk text promises prerequisites or special behavior | UI checks and hook implementation | Current prerequisite/conflict metadata is not a general purchase gate; descriptive effects need an implemented consumer. |
| F5/F9 does the wrong thing | `DEBUG_MODE` | In the shipped mode these are teleport/dump, not save/load. |
| Progress disappears after quitting | Was an explicit checkpoint published? | Travel cache is not a full checkpoint. Save through nondebug F5 before quitting. |
| Old campaign is refused | Save format, plan version, required references | Preserve the error and complete slot. Do not turn malformed saved data into a new game by deleting selected fields. |
| Long text is cut off | Known UI-TEXT-HEIGHT limitation | Split authored prose into deliberate pages where appropriate; a general text-layout repair remains separate. |

## Distinguish errors from warnings

The structure catalogue can succeed with warnings about preserved legacy fields and deferred specials. Those warnings are useful descriptions of route limits. A failed required goal, missing referenced item or invalid placement contract is different: it can block that candidate. Read the report's actual status and location, not just its process output length.

## Build a useful defect report

Include the full Git commit, changed files, a seed, command/session name, world and local coordinates, submap ID, exact error, expected outcome and observed outcome. For a structure include the layout, sidecar and profile/policy changes together. For state include whether the item/map was newly created or loaded from an existing checkpoint.

Keep the failing candidate and evidence. Reducing the candidate is useful if it preserves the failure; deleting evidence or silently changing seed until it passes loses the explanation.

## Current limits with practical consequences

The current source does not provide general multi-building compound recipes, a generic ranged-combat system from a larger moveset `range`, a general recipe-discovery mechanic from `known: false`, full background simulation, exact replay of all gameplay RNG, personal-save migration or automatic checkpoint pruning. Specific weapon declarations such as free movement on kill and pool lifetime also remain incomplete. See the relevant chapter before treating a data field as an available feature.

This handbook records these limits so you can make edits that the current game can use. It does not silently choose new creative rules or implement the missing systems.

## Source basis

[Data loader](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/data_loader.py) · [current structure guide](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/docs/STRUCTURE_AUTHORING.md) · [craft ambient sources](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/rendering/craft_screen.py) · [perk screen](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/rendering/perk_screen.py) · [next-arc history](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/docs/owner/NEXT_ARC.md).
