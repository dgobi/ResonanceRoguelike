# Compose a small rural compound

The installed G7 policy in `roguelike/data/generation/poi_profiles.json` is version 2. Its inclusive 2–4 draw counts **parents**, separate from the featured landmark. `kind_minimum` requires at least one `single` and one `compound`. A compound contains exactly two required children and at most one optional child, plus shared paths and one country-road gate. Parent caps count accepted parents; child placements do not consume another parent count.

`choices` contains kind-tagged single `asset` or compound `recipe` IDs, positive weights and caps. Single weights multiply the asset's placement weight; compound base weight is one. Recipes live under `roguelike/data/generation/compounds/`. Children remain ordinary building definitions. Selection never grants a transform forbidden by a child.

## Copy and preview a complete example

Run from the repository with the dependency interpreter described in Setup:

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py --init-compound authoring/g7 --output evidence/authoring/g7-init.json
& $ResonancePython -X utf8 tools/structure_authoring.py --compound authoring/g7/g7_travellers_court.json --child authoring/g7/g7_wayhouse.json --assigned-compound S --output evidence/authoring/g7-assigned.json
& $ResonancePython -X utf8 tools/structure_authoring.py --compound authoring/g7/g7_travellers_court.json --child authoring/g7/g7_wayhouse.json --poi-config authoring/g7/g7_poi_example.json --seed 20261023 --output evidence/authoring/g7-selected.json
```

The initializer preserves existing drafts. Reports and derived SVGs cannot replace inputs or initializer targets, even through aliases. A selected preview can truthfully report nonselection; assigned preview is a controlled fit, not a frequency estimate. Reports include production content receipts and populated access checks. SVG diagrams are not gameplay screenshots.

Import the child into `layout_painter.html`, edit and export, then substitute that actual download for `--child`. Repeat `--child` for multiple draft children. The painter edits buildings, not compound recipes.

## Geometry and bounded fitting

The version-one recipe declares `id`, `size`, `rotations`, `gate`, `paths`, `slots` and `fit_budget`. Named path joins must be reciprocal and physically connected; the gate must touch its named path. Slots declare their path, join, normal, private `buildable` rectangle, required status, role label, base child rotations and weighted assets. These role labels do not replace town role selection.

Required slots precede the optional slot. Two required children must fit atomically. The optional child can be omitted with a capacity or budget reason. Private buffers stay within private regions; siblings cannot overlap. Only narrow declared path/envelope permissions are shared. A parent ID never grants blanket permission for children to overlap.

The effective child transform includes the parent turn and must be permitted by the child. Every admitted child needs a required usable target; direct compilation alone does not certify this consumer obligation. Real containers need special records and loot pools, not just a decorative symbol.

## Installation and saved worlds

After previews pass, deliberately install children in existing building categories, recipes under `generation/compounds/`, and the reviewed v2 policy in `generation/poi_profiles.json`. Review the diff and refresh/check the editor catalogue. Rehearse in a disposable data root with sentinels. Previews do not install files or open campaigns.

G7 introduced format 5 / `wg7` resolved compounds. Current G8 format 6 preserves that parent/child model and adds settlement resolution. Recipe or policy edits affect new plans. Pending scenes use saved child IDs, transforms and geometry; consumed child changes can reject affected pending scenes while visited and unaffected pending scenes remain usable. Complete chunk scenes own runtime state, including independent containers for identical children.

Explicit version-one POI policies retain single-site count meaning. On the historical G7 fresh-policy path they select format 4 / `wg6`; old plans are never relabeled or recomposed. Current version-3 settlement settings use format 6 / `wg8` independently of this POI choice.

## G9 preserves these owners

Current G9 network augmentation runs after the complete mixed rural baseline is resolved. It preserves parent/child coordinates, assets, dependencies, paths, gate and assigned road attachment. No new full-width road cells may enter the site's owner chunk. Mixed POI v2, legacy single-site v1 and explicit zero additional parents all retain their semantics independently of the network switch. Saved pending sites use resolved records; changing today's network policy cannot move them. Preview assignments finish site insertion before optional augmentation so their preservation contract covers the actual complete preview.
