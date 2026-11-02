# Resonance Aseprite creation lab (ART-1)

Double-click **`art_lab/launch-art.cmd` in the existing Resonance checkout**.
It opens or reuses Aseprite, checks the local connection, and opens a fresh
native Windows Codex conversation rooted here. **Type prompts in that Codex
conversation.** The editable pixels appear in the Aseprite window. The prompt
does not go into Aseprite's console or the workbench.

The launcher uses the existing Codex sign-in and model choice. Use Codex's
`/model` picker to choose an available model without reinstalling anything, or
run `launch-art.cmd -Model <available-model-id>`. Keep one art conversation per
live Aseprite editor. The launcher prevents a second launcher session in this
lab, but cannot lock conversations started by other routes.

## First experiment

Paste this into the local Codex conversation:

```text
Use the connected Aseprite AI Artist tools in live mode. Check preflight and
read the drawing, review and export resources. Inspect the current live
document before editing anything, preserving any manual work.

Create one new native 32x32 amber_sting_beetle candidate. Read
../roguelike/data/entities/creatures/amber_sting_beetle.json and inspect
references/crops/amber_sting_beetle.png plus references/contact-sheet.png.
Keep the broad insect, six legs, split shell, paired antennae and hooked
mandibles. Develop distinct overlapping head, thorax and abdomen, readable
chitin planes and clear negative space around the legs. Keep it an animal.
Use temporary colors unless I supply mine; disable palette snapping for
requested RGB colors. No palette interview or concept-image service.

Draw actual pixels through MCP at native size with a few named layers.
Inspect at native and exact nearest-neighbor 2x, make a bounded correction,
and save the next unused version under drafts/amber_sting_beetle/ with a
matching 32x32 PNG in exports/ and separate 2x preview in previews/.
Resolve all MCP file paths absolutely from this lab. Preserve prior versions
and production assets. Stop after one candidate and note its main weakness.
```

The current art direction is original, richer Resonance pixel art: tangible
forms after a resonance catastrophe, readable silhouettes and restrained
material detail. Maya-inspired stepped forms and deep recesses are useful for
appropriate ancient manufactured subjects; they do not turn natural creatures
into decorated humanoids. Qud and Path of Achra are broad atmosphere/readability
references. Colors remain yours. Native 32x32 is selected; runtime migration
and a future manual workbench importer require later briefs.

## Reference, revise, edit, save

- Reference an existing sprite by its crop path and definition, or attach an
  owner-supplied image to Codex. `references/manifest.json` records source IDs,
  coordinates, real sheet dimensions, hashes and revision. The contact sheet
  includes native crops and exact 4x views. `ancient_floor` and
  `sprite_placeholder` are question marks, not designs to imitate.
- Ask for a specific correction: “Separate the near legs with negative space;
  preserve the accepted shell and overall dimensions. Save a new version.”
- Edit directly in Aseprite with its pencil/layer tools and use Ctrl+S to save
  the source. Then say: “I edited the shell. Read sprite_info and look at the
  current live document again, preserve my edits, and change only the antennae.”
  Codex must reacquire the current state even if your changes are still unsaved.
  Do not let it reopen an older disk image over your edits.
- `.aseprite` in `drafts/<asset-id>/` is the editable layered source. The
  matching file in `exports/` is the native **32x32 PNG** for future import.
  `previews/*_2x.png` is **64x64**, for inspection only. Keep prompt/revision
  notes with the source. Increment filenames before a substantial revision.
- Manual PNG export: File > Export, PNG, one frame, 100% scale, no trimming;
  choose a new file in `exports/`. Retain the `.aseprite` source separately.
  Isolated creatures/props need transparent surroundings; terrain may need full
  coverage. Do not replace native exports with enlarged previews.

Browser ChatGPT planning conversations do not automatically acquire this local
MCP connection. They can help draft prompts and critique uploaded art. The
verified route here is the native Windows Codex CLI opened by the launcher.
Workflow resources such as `skill://draw` are read by Codex through MCP; the
`/aseprite:*` commands in other-client demonstrations are not promised Codex
slash commands.

## Install again or relocate

1. Install official [Aseprite](https://www.aseprite.org/download/) 1.3+ if missing,
   and run it once. This machine uses its existing Steam copy. Setup discovers
   Steam libraries from `libraryfolders.vdf`, including custom locations. For
   a nonstandard portable install set `ASEPRITE_PATH` in your local environment;
   use `ASEPRITE_USER_FOLDER` if its config folder is nonstandard.
2. Have native Windows Node 22.6+ with `npm.cmd` and the Codex CLI on PATH.
   Existing Codex sign-in is reused; this lab stores no credentials and installs
   no image service. A WSL executable is not the Windows art-session route.
3. Run `setup-art.cmd`. It runs `npm ci` using the exact dependency and lock,
   backs up any old adapter extension, and installs only this extension and
   this lab's MCP entry. Save/close Aseprite normally after an extension update,
   then run `launch-art.cmd`. Never force-kill it with unsaved documents.
4. If Codex presents project trust, trust this checkout/lab, then start a fresh
   session. This checkout was already trusted at delivery. Setup does not edit
   user trust, model, approval or sandbox defaults.
5. Aseprite may request script access for `aseprite-ai-artist/ai-artist.lua`.
   Allow the extension's requested file and localhost access. Then rerun the
   launcher. The owner performed this application permission step during ART-1.

Generated `.codex/config.toml`, `.local/paths.json`, backups and logs are ignored.
The MCP command is the detected native Node executable plus the **locked local
`node_modules/@pebbly/aseprite-ai-artist/dist/cli.js`**, never `npx @latest`.
Lua escape-hatch execution and headless mode are explicitly disabled.
The owner approved lab-scoped preapproval for exactly `sprite_manage`, `layer`,
`draw` and `export`. Their tool tables use `approval_mode = "approve"`, because
the native noninteractive client otherwise rejects these writes. General
approval and sandbox settings, and other servers/tools, retain their defaults.
Startup uses installed packages; it does not fetch an adapter from the network.
Codex itself still needs its normal service connection.

Reference extraction and independent PNG checks use Python 3.11+ and Pillow
(the pinned optional dependency is in `requirements.txt`). To regenerate the
current read-only game references, run `python scripts/extract_references.py`.
This updates provenance to the current checkout; it does not migrate game art.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Editor closed / extension not connected | Launch Aseprite, allow its extension-access dialog, and retry. After installation, save and restart Aseprite normally. Check Edit > Preferences > Extensions if disabled. |
| Stale Codex tool list | Close the art conversation and relaunch; it must start in this folder. |
| Local config ignored | Check project trust. From this folder run `codex mcp get aseprite-ai-artist --json`; it must show the installed local command and enabled state. A TOML file alone is not evidence. |
| Wrong Windows/WSL host | Use `launch-art.cmd` from Windows. The existing game coding arrangement remains separate. |
| Another bridge / port conflict | The adapter reuses its bridge on localhost ports 9931/9932. Do not start another authoring session. Inspect `node .../dist/cli.js doctor`; stop only a positively identified stale adapter bridge after all authoring sessions finish, then relaunch. Do not terminate unrelated Node processes. |
| Missing/moved executable or moved checkout | Restore native executables to PATH / set the local Aseprite override, then rerun setup to regenerate absolute MCP paths. |
| Another launcher owns this lab | Use that conversation or exit it normally. A stale lock file is harmless: the lock is held by the live process. |
| `validate` MCP schema warning | Codex 0.166.0-alpha.5.1 omits the adapter's `validate` tool. Drawing, inspection and save/export work. Use `scripts/verify_outputs.py` for the delivered trial's independent file checks. |
| ASCII inspection exceeds the glyph limit | Use `look` image previews and `read_pixels`. Do not quantize working colors just to make the ASCII view fit. |
| Save/export access dialog | Allow the Aseprite extension's requested file access; resume with live preflight and reacquire the intended document before retrying. |

The launch window stays open on errors. For a noninteractive startup check:
`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/launch.ps1 -CheckOnly`.
This checks effective configuration and the live editor without drawing. It is
not a substitute for the retained draw/inspect/revise/save evidence.

## Remove or restore the connection

Exit the art Codex session. Remove only `[mcp_servers.aseprite-ai-artist]` and
its `.env` and four `.tools.*` tables from this lab's ignored `.codex/config.toml` (or set
`enabled = false` in that server table). Leave unrelated entries intact.
Prior local config copies, when one existed, are next to it as `config.toml.bak-*`;
restore just the affected stanza if other configuration has since changed.

To remove the Aseprite extension too, save and close Aseprite normally, then
remove only the `extensions/aseprite-ai-artist` directory inside its config
folder. If setup replaced a prior copy, restore it from
`.local/backups/<timestamp>/aseprite-ai-artist`. Other extensions, Aseprite,
user-wide Codex settings and existing artwork do not need removal. Backups of
`aseprite.ini` are local recovery records; do not blindly restore the entire
file over later preferences or permissions.

## Evidence and sources

See `DELIVERY.md` and `evidence/` for actual versions, checks and limitations.
The implementation follows the supplied ART-1 brief and the owner's companion
`RESONANCE_32PX_ART_WORKFLOW_AND_MIGRATION_GUIDE_2026-11-01.md`, plus the retained
Project Compass and Workflow under the repository's G11 review references.

- [Pinned adapter source and install documentation](https://github.com/with-pebbly/aseprite-ai-artist/blob/a32a2a58e76b06fc9ad7b29b12abd003ec769665/docs/INSTALL.md)
- [Official Codex project configuration and trust](https://learn.chatgpt.com/docs/config-file/config-basic)
- [Official Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp)
