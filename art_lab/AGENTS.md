# Resonance art lab

Create in this directory using the live `aseprite-ai-artist` MCP connection.
Keep game/runtime assets, sprite maps, definitions, settings, saves, workbench
and wiki untouched. This lab does not commission the later 32px migration.

- Call `preflight` first. Require `ready: true`, `mode: live`. Never substitute
  headless mode for a failed live connection. Use only one authoring session per
  live editor. Keep arbitrary Lua disabled.
- Read the available drawing, review and export MCP resources (for example
  `skill://draw`, not a promised `/aseprite:draw` Codex slash command). Follow
  this bounded brief over upstream concept-image, palette, animation, delegation
  or multi-stage workflow suggestions. No image-generation service is needed.
- Work at native 32x32, one static frame. Draw and revise actual pixels through
  Aseprite MCP. Inspect with `look` after meaningful changes, at native size and
  nearest-neighbor 2x. Use crisp integer placement, useful named layers and
  coherent pixel clusters. Never shrink a large illustration into a sprite.
- Use supplied owner colors. Otherwise proceed with temporary working colors;
  there is no required permanent palette or palette interview. In 0.8.2,
  `draw` defaults to palette snapping: explicitly use `paletteLock: false` for
  requested RGB working colors unless the owner requests palette restriction.
- Read the actual definition and `references/manifest.json`, inspect the crop,
  and distinguish placeholders. Keep animal anatomy; Maya-inspired carved
  forms belong where construction/history supports them. Build original
  Resonance forms with readable silhouettes, material planes and restrained wear.
- Use transparent surroundings for isolated creatures/props; full tile coverage
  where terrain needs it. No forced AAP-64 quantization.
- Always identify the target with its stable sprite ID (`#id`), obtain
  `sprite_info`, and inspect its current pixels before edits. After owner edits,
  reacquire the live document even if unsaved. Do not reopen stale disk content
  over their changes or apply a cached redraw. Save a new version before a
  substantial revision; never discard documents or silently overwrite versions.
- Resolve every open/save/export path against this lab to an absolute path;
  Aseprite's working directory can differ. Save named layers in
  `drafts/<asset-id>/<asset-id>_v001.aseprite`, native pixels in
  `exports/<asset-id>_v001.png`, and 2x previews separately in
  `previews/<asset-id>_v001_2x.png`. Increment versions. Retain the prompt and a
  short revision note beside the source. Independently verify 32x32 geometry,
  alpha and nonblank export. Enlargement is a preview, never an import asset.
- ART-1's diagnostic and one amber sting beetle trial are designated publication
  artifacts. Subsequent owner experiments are not automatically approved for
  committing or pushing. Stage explicit paths; preserve unrelated owner art.
