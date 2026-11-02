# ART-1 delivery — 1 November 2026

The local live Aseprite creation lab works. Open `art_lab/launch-art.cmd` from
the existing Resonance checkout, then type in its **Codex conversation** while
Aseprite remains open. The exact first prompt, revision workflow, setup,
troubleshooting and removal instructions are in [README.md](README.md).

## Installed and preserved

| Component | Verified version / handling |
| --- | --- |
| Starting game revision | `2e3168ea915650658af66d1ae41a9ae399185425`, existing `main`; retained the advanced checkout |
| Named local checkpoint | `checkpoint/art-1-before-2026-11-01` |
| Native Windows Codex CLI | `0.166.0-alpha.5.1`; existing sign-in and model defaults retained |
| Node / npm | `24.15.0` / `11.12.1` |
| Aseprite | Existing Steam installation, `1.3.18.6` |
| MCP adapter / extension | `@pebbly/aseprite-ai-artist` / extension `0.8.2` |
| Independent validator | Python `3.11.0`, Pillow `12.3.0` |

The package is pinned in `package.json` and `package-lock.json`. npm's recorded
`gitHead` is `5894b12cead839789077b279369409f868451ffc`, while the brief reviewed
`a32a2a58e76b06fc9ad7b29b12abd003ec769665`. These are distinct provenance facts;
the tested artifact is the registry's locked 0.8.2 package, not a claim that its
tarball equals the later reviewed Git revision. No alternate release or adapter
patch was needed. The installed entry point is `dist/cli.js`; startup calls it
with native Node and never resolves `@latest`.

The extension's existing configuration directory and unrelated extensions were
preserved. Local paths, config, backups, dependency installation and raw logs
are ignored. Aseprite was initially closed, so no unsaved document required a
forced restart. The owner allowed its script access dialog. A separate native
Codex approval gate then rejected document creation under `never`; the owner
explicitly approved lab-only permissions for `sprite_manage`, `layer`, `draw`
and `export`. General approval/sandbox policies and other servers were preserved.
Arbitrary Lua remains disabled. The setup is not tied to one model.

## What actually ran

- A fresh native Codex process started inside `art_lab`, loaded the scoped MCP
  configuration, passed **live** preflight and read `skill://draw`,
  `skill://review` and `skill://export`. The owner-facing route uses the same
  local configuration. Configuration visibility was also checked outside the
  lab: the entry was absent at the repository root.
- Through MCP, it created a transparent RGB **32x32** diagnostic lantern with
  `metal` and `light` layers, drew and inspected it, saved v001, then changed
  exactly `(15,17)`, `(16,17)`, `(15,18)`, `(16,18)` from `#e65050` to
  `#5de4d0`. It inspected and saved v002. All other decoded pixels are unchanged.
- It reopened the saved source through MCP, confirmed editable layers and
  re-exported the same decoded RGBA pixels. Requested working colors survived
  exactly with `paletteLock: false`.
- It read the actual amber sting beetle definition and current crop, drew one
  native candidate through MCP, inspected native/2x views, preserved v001,
  revised the right wing-case shading, and saved/reopened v002. The four source
  layers are `legs`, `body`, `elytra` and `head`. The final saved candidate was
  left visible in Aseprite.
- Independent file validation passed for all four native PNGs and layered
  sources: dimensions, one frame, RGBA, nonblank content, transparent margins,
  exact diagnostic correction, exact 2x previews and decoded-pixel equality
  against both live reopened-source exports. No Python-generated creative
  bitmap substitutes for the MCP drawing trial.
- Launcher readiness, missing-dependency errors, single-session locking and
  PowerShell syntax were checked. Errors remain visible. Existing Aseprite is
  reused; no forced close or desktop mouse control is involved.
- The interactive launcher was opened in a terminal at the correct lab path.
  Its `/model` picker displayed available models; it was exited without changing
  the owner's default or starting another drawing turn.

## Delivered artwork and references

| Result | Editable source | Native export |
| --- | --- | --- |
| Diagnostic | `drafts/diagnostic/diagnostic_v002.aseprite` | `exports/diagnostic_v002.png` |
| Beetle trial | `drafts/amber_sting_beetle/amber_sting_beetle_v002.aseprite` | `exports/amber_sting_beetle_v002.png` |

Both v001 sources/PNGs are retained. Separate previews are under `previews/`.
Prompts and revision notes are beside the sources. The beetle's pose is still
stiff and nearly symmetrical, especially its front legs. This is a bounded
creation trial; artistic success and permanent colors remain the owner's call.

`references/contact-sheet.png` and `references/manifest.json` cover fourteen
registered source cells, with exact crops and nearest-neighbor 4x views. The
manifest binds real sheet dimensions, source coordinates, file hashes and the
starting revision. Ancient floor and the shared question-mark cell are marked
as placeholders. No external game sprite libraries were downloaded.

## Evidence and limits

`evidence/file-validation.json` records independent results and artifact hashes;
`evidence/roundtrip.json` records the fresh authoring session. The compact
`evidence/mcp-proof.json` records actual tool counts, save/reopen operations,
inspection scales and two recovered input/display errors. Live re-export PNGs
and private process logs remain under ignored `.local/`. To rerun the retained
file checks, use `python scripts/verify_outputs.py --require-reopened` while
those live re-export files exist. Without that flag, missing local re-export
files are explicitly reported as not rerun.

This Codex build omits the adapter's `validate` MCP tool because its schema is
incompatible. Normal drawing, inspection and file operations were verified;
independent validation covers this trial. The noninteractive child session
could not invoke the installed Python interpreter, so the outer implementation
session performed the independent Pillow/file checks successfully. No sandbox
policy was relaxed to work around interpreter discovery.

The task changes only `art_lab/`. Runtime PNGs, map/definitions, display settings,
saves, workbench, root instructions and wiki remain unchanged. The unrelated
owner workbench-plan file was preserved byte-for-byte and excluded from staging.
No broad game regression suite was run for this lab-only change. Later runtime
32px conversion, final palette policy, bulk art and manual workbench import
remain separately commissioned work.

Publication is to existing remote `main`, without force. The delivered commit
and remote readback result are reported with this delivery in the chat; this
receipt is stored inside that revision rather than embedding a self-referential
commit SHA.

## Explorer launcher correction — 1 November 2026

The initial terminal verification inherited Codex's app-specific PATH. The owner
then reported that double-clicking the launcher could not find Codex. This was
reproduced using only the persisted Windows machine/user PATH. Discovery now
uses PATH first, then the executable recorded by setup, then installed desktop
builds if that saved executable no longer exists. No system PATH was changed.

Both the saved-path route and the stale-cache discovery route passed under the
ordinary Windows PATH. The full launcher preflight passed, and a new visible
art-lab console was launched with Codex running beneath it and the session lock
held. Existing Aseprite was reused. See `evidence/launcher-path-fix.json`.

## Owner-requested full access — 1 November 2026

The owner requested an easy way to grant full access or start with it enabled
because the art conversation repeatedly requested permissions. The default
launcher now supplies `--sandbox danger-full-access --ask-for-approval never`.
Its `/permissions` menu was verified to show **Full Access (current)** immediately
after startup, without an additional confirmation. These are process options;
user-wide Codex defaults are unchanged. `launch-art.cmd -StandardPermissions`
omits the full-access shell options.

The lab's ignored MCP configuration now preapproves the Aseprite server's
normal tools with `default_tools_approval_mode = "approve"`, replacing the
original four-tool list. Setup reproduces this setting and preserves backups.
It applies in both launcher modes. Arbitrary Lua remains disabled. The MCP
setting is stored in project config because passing it as an inline `-c`
override caused this CLI build's interactive bootstrap to fail; the final
project-config route successfully opened the interactive conversation.

For an existing conversation, `/permissions` > **Full Access** > **Yes, continue
anyway** was also verified. Relaunch the art conversation to load the new MCP
preapproval policy. Aseprite does not need a restart or reinstall.

Verification included a fresh native session using the launcher's final options:
the previously blocked Python interpreter ran, and the Aseprite `frame` tool
(outside the original four approvals) successfully listed the current document's
frames without prompting. This test did not mutate artwork. Local config remains
lab-scoped, and existing owner studies were excluded from this change and commit.
See `evidence/full-access-launch.json` for the concise verification record.
