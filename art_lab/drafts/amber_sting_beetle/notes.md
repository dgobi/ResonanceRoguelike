# ART-1 amber sting beetle: one creative trial

## Trial prompt retained

"Create ONE original richer native 32x32 amber sting beetle through live Aseprite MCP. It must remain a broad six-legged animal with split amber shell, paired antennae and hooked mandibles. Show distinct head/thorax/abdomen, substantial chitin plates, clean negative space around the six legs and material planes; no jewelry, human mask or headdress. Temporary amber, deep umber and cool dark working colors are fine; no permanent palette. Choose a few useful named layers. Native 32x32 only, no shrinking large art."

## Reference and construction

- Read actual creature JSON: broad six-legged insect, split amber shell, hooked mandibles; separate head/thorax/abdomen and six leg definitions.
- Read `references/manifest.json`: beetle explicitly non-placeholder, first 16x16 cell of `amber_insect`. Inspected exact 4x reference and contact sheet. White reference supplies a broad insect silhouette, not a permanent palette. Sheet placeholders were not used as designs.
- Native 32x32 RGB, one frame, transparent surroundings. Four editable layers: `legs`, `body`, `elytra`, `head`.
- All silhouette, material and revision pixels through live typed MCP `draw`, always `paletteLock: false`. No illustration reduction, imagegen, Lua, desktop control, headless mode or delegation.
- Temporary amber/yellow material planes, deep umber seams, cool dark outlines/joints. Broad wing cases, three separate leg pairs, paired antennae and small hooked jaws preserve animal anatomy. No jewelry, human mask or headdress.

## Versions and review

- v001: silhouette inspected live at 1x/2x; materials inspected at 1x/2x and supplemental 8x. Saved layered source, native PNG and 2x preview. An initial short head-grid row was rejected and corrected before v001 save.
- Finding: right wing case looked flat, with a long highlight stripe competing with the split.
- v002: reacquired live info/pixels; saved new source version before editing. One bounded revision on `elytra`, x=16..23,y=15..24, replaces the stripe with a stepped shoulder reflection, broader amber plane and recessed umber edge. Other layers/left shell unchanged. Inspected live at 1x/2x/8x; saved source and matching native/2x exports. v001 retained.
- Reopened saved v002 as #317. Confirmed four editable layers, RGB, one frame, saved unmodified state. Inspected at 1x/2x; exported `.local/beetle-reopened.png`. Live composite RGBA matches original saved document. Final reopened v002 left active; no documents closed.
- Full-shell `look` ASCII exceeded its 261-glyph capacity with the default 256-entry palette plus working colors. Used live previews and `read_pixels`; did not change/restrict palette.

## Remaining weakness and verification limit

Pose remains stiff and nearly symmetrical; front legs are angular. Head and mandibles remain compact at native scale. Artistic quality is not certified; no game integration commissioned.

Independent checks subsequently passed in the implementation session: decoded equality after live reopen, native geometry, alpha/nonblank, editable source layers and exact 2x replication. See `../../evidence/file-validation.json` and `../../scripts/verify_outputs.py`. The art-session shell itself could not invoke Python; no sandbox policy was changed. No game integration.
