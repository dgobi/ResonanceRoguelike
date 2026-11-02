# ART-1 diagnostic lantern

## Trial prompt retained

"Create a new transparent RGB 32x32 single-frame diagnostic lantern icon using MCP, with named layers (e.g. metal, light). Draw a recognizable symbol through typed draw operations. Explicitly disable paletteLock for all temporary RGB draws. Put a 2x2 red light at x=15..16,y=17..18 (exact #e65050)."

"Then make a controlled visible correction through MCP: replace just those four red light pixels with exact #5de4d0."

## Execution and revisions

- Aseprite 1.3.18.6, extension and installed adapter 0.8.2; live ready. No imagegen, arbitrary Lua, headless mode or desktop control.
- Native 32x32 RGB, one frame; editable layers `metal`, `light`. All creative pixels via typed MCP grid/rect operations with `paletteLock: false`.
- v001: suspended lantern with cool metal handle, cap, cage, dark glazing and exact red test pixels. Inspected live with `look` at 1x/2x; saved and exported.
- v002: one 2x2 rect operation on `light` at (15,17), exact #5de4d0. Inspected at 1x/2x, saved source/native PNG/2x preview; v001 preserved.
- Reopened saved v002 as #102. `sprite_info` confirmed both layers editable, RGB, one frame. Re-export: `.local/diagnostic-reopened.png`. Original and reopened live composite RGBA reads match; all four final pixels read #5de4d0.
- Independent checks subsequently passed in the implementation session: decoded file equality after live reopen, exactly four changed pixels, native geometry, alpha/nonblank, editable source layers and exact 2x replication. See `../../evidence/file-validation.json` and `../../scripts/verify_outputs.py`. The art-session shell itself could not invoke Python; no sandbox policy was changed.

## Visual limit

This is a route diagnostic, not production lantern art. The small light sits in a simple rectangular glazing field. Preview is not an import asset. No commit/push or game integration.
