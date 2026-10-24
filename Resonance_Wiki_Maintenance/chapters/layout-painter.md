# Use the offline layout painter

The layout painter is an existing repository tool, separate from this wiki. Open the root `layout_painter.html` locally. It loads its JavaScript, styling and generated ID catalog from `tools/structure_editor/`, so keep those adjacent files in place. It needs no web service or running campaign.

Its purpose is to preserve and edit complete structure documents. **A successful browser export proves that JSON was exported; the Python authoring command certifies the supported runtime contract and relevant physical access.** Always validate the actual downloaded bytes.

## A dependable editing session

1. Start from a complete example or installed asset. For a new town building, `g5_service_house.json` provides a placement profile; for a rural site, use `g6_wayhouse.json`. Both live under `roguelike/docs/examples/` and remain outside the live catalog.
2. Choose the correct route and intended category. Ordinary buildings, plazas, interior entrances and authored submaps do not consume identical fields.
3. Import the JSON file or use paste import. An invalid or cancelled import leaves the current document intact.
4. For a new variation, apply a unique internal ID and use a corresponding new filename. A different filename with the old ID still creates a duplicate.
5. Paint the terrain layer using single-character legend entries. The grid readout exposes source coordinates.
6. Use the decor layer for complete decor IDs. Erasing a decor cell sets that cell to null; it does not erase the terrain underneath.
7. Edit supported specials in their JSON panel, then choose **Apply record**. Catalog selectors insert IDs into the draft panel; applying the edit is a separate action.
8. Edit starts and Placement metadata deliberately. Entrance positions and access targets must track your changed geometry and contents.
9. Export a draft. Keep your prior draft until the exported file passes the relevant checks. The exported-text area is a portable fallback if you need to save manually.
10. Run `tools/structure_authoring.py` on the exact export, then inspect both the JSON report and adjacent diagnostic SVGs.

The painter preserves unknown metadata, field absence, null, false, zero and ordered arrays. Retention does not activate inactive features. The catalog's legacy capability descriptions must be read together with the current planned-placement guidance: modern quarter turns and role selection live in the explicit placement and policy contracts.

## Resize without losing authored content

The editor supports up to 256 × 256 cells, but the current runtime supports at most 80 × 43 local-map cells and planned buildings require space for their buffer and approach. An oversized imported document stays intact and exportable with grid editing disabled; it is not thereby a valid installed asset.

Use **Review resize** before applying changes. Enlargement and explicit ragged-grid normalization pad using an existing null-mapped character, or explicitly add such a mapping. They do not floor-fill, reposition content or silently shrink another dimension. Destructive crops are refused and affected cells/records are identified. Cancelling the preview changes nothing.

Undo/redo covers the whole document and route view, not only painted terrain. Removing a legend character still used by the grid is refused; repaint those cells first. Unknown coordinate-bearing metadata is retained for review, but nontrivial runtime transforms may reject it because its geometry cannot be safely inferred.

## Refresh the ID catalog

The browser catalog is generated from the checkout's data and contract. When you add items, texts, pools, decor or structures, refresh it from the repository root and reload the painter:

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output evidence/authoring/catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --refresh-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
```

The first command validates the actual catalog; refreshing does not cure an invalid definition. The freshness check compares a generated representation with `tools/structure_editor/catalog.js`, including raw checkout identity. During this wiki's review, the untouched cloned checkout passed catalog validation but failed the freshness check; the asset list, route capabilities and contract hash agreed while the raw data identity differed. The wiki therefore does not repeat an unconditional claim that the shipped catalog is fresh on every checkout. Refresh locally, check again and reload the page.

## Which validation command should I use?

| Task | Command mode | What it establishes |
|---|---|---|
| Direct ordinary draft | Candidate + `--route ordinary_building --category …` | Compiles and realizes normal/legacy-mirrored previews. Intended access needs a sidecar. |
| Modern transformed building | Candidate + `--orientations` and route/category | Checks all allowed placement transforms and the declared entrances/targets. |
| New town candidate | Candidate + `--planned --context grid/roadside --role … --category …` | Temporary policy membership and actual production selected-scene realization. |
| Featured landmark candidate | Candidate + `--planned --context landmark --role landmark --category wilderness` | Eligibility and placement in the one featured slot. Selection can legitimately miss the draft. |
| Additional rural candidate | Candidate + `--site --category wilderness` | Selection within the additional-site policy. |
| Controlled rural orientation | Candidate + `--assigned-site N/E/S/W --category wilderness` | A disclosed single-asset, one-site fitting fixture for the chosen frontage normal. |
| Installed entrance/lab/plaza | Installed candidate path | Infers route/category from its catalog path and runs that consumer. |
| Whole policy change | `--world-plan` with appropriate config override | Validates a complete new plan without opening a campaign. |

External drafts must identify their route, and ordinary drafts their category, where required by the selected mode. `--output` must name JSON outside the game/source-asset tree. Use a fresh path under `evidence/authoring/`; the CLI refuses output that would overwrite the game or the input candidate.

## Reading the result

The console summary reports `passed`, asset/diagnostic totals, preview count and output path. Detailed JSON contains actual terrain/content/links and access results. SVG hover information includes IDs and rolled contents. A controlled stamp, an assigned fixture and a naturally selected mixed-policy placement are different kinds of evidence; none alone estimates long-run frequency.

With a direct-stamp access sidecar, use `coordinates: "source"` by default, an `entry: {x,y}` and `targets: [{name,kind,x,y}]`. Source coordinates transform with the preview origin/mirror; an exterior entry can sit just outside the footprint. The sidecar validates a chosen entry. It does not invent a generated player spawn for a route that has none.

## Sources

- [Editor model and preservation rules](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/tools/structure_editor/model.js)
- [Editor controls](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/tools/structure_editor/editor.js)
- [Authoring CLI](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/tools/structure_authoring.py)
- [Current walkthrough and diagnostic definitions](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/docs/STRUCTURE_AUTHORING.md)

## G7 composition integration

The current mixed parent workflow is documented in [Compounds](#compounds). A building export supplies the consumed child structure; a separate recipe supplies two required slots, an optional third slot, common paths, private bounds and permitted parent/child transforms. The existing painter edits the building, not the recipe. Use actual exported bytes in `--child`. Run `tools/verify_g7_authoring.py` for inherited and compound workflows; direct focused discovery now supplies its own absolute tools import path. Keep previous evidence immutable.

## Town composition is a separate authoring surface

The painter edits building documents and permitted transforms. G8 streets, common and lots use complete JSON previews in [Settlement layouts](#settlement-layouts). A downloaded building must still fit its lot, full doorway and assigned street. Both browser engines export actual files consumed by the G8 planned path during verification.
