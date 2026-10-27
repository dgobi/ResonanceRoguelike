# W4B delivery — Windows startup and project defaults

Verified **26 October 2026, America/Edmonton** (27 October UTC).

Workbench **0.7.1**, protocol **7**, now opens this workstation's current checkout
automatically using its complete bundled worker. The owner's existing desktop
shortcut was corrected and actually launched/restarted. Its previously absent
per-user settings were created by the successful app launch, selecting
`G:\GameDev\RoguelikeProject`. No environment setup or source dialog is required.

## Revision and source-confirmed cause

- Baseline local `main`, local `origin/main` and live remote `main` were all
  **`0e79ecd267849a05897bb0341ed2edcdefdc3e39`**, W4A's evidence commit. There
  were no intervening commits. The sole pre-existing owner change was the
  untracked Workbench plan, which remains untouched and untracked.
- Implementation: **`6c6c99da288574e25866f2df5070aa53bc9657e6`**.
- This report, compact receipt and captures form a separate evidence commit.
  Resolve its SHA with `git log -1 --format=%H -- workbench/docs/W4B_DELIVERY.md`.
  The final handoff and ignored `workbench/.artifacts/w4b/final-publication.json`
  record the exact final evidence/remote SHA after publication; a commit cannot
  embed its own SHA in its contents.
- Named local tags: `checkpoint/workbench-w4b-start-20261026-a` and
  `checkpoint/workbench-w4b-verified-20261026-a`. Work stayed on production `main`;
  no branch, worktree, development copy, reset or force push was used.

The actual desktop shortcut targeted
`G:\GameDev\RoguelikeProject\workbench\src-tauri\target\release\deps\resonance_workbench.exe`,
with its working directory in `release\deps`. No process/user/machine
`RESONANCE_PYTHON` override was present. Launching that exact executable from an
unrelated working directory reproduced the owner's error: absent
`G:\GameDev\RoguelikeProject\.venv\Scripts\python.exe` and
`\\?\G:\GameDev\RoguelikeProject\workbench\src-tauri\target\release\deps\bridge.py`.
Tauri's Windows resource directory correctly followed that raw executable; it
had neither bridge nor bundled Python. The old host then inferred a nonexistent
project-local interpreter. The extended-path prefix itself was not defective.

W4A's runner instead launched `target\release\resonance-workbench.exe`, beside
the actual `bridge.py` and complete `python/` resource directory, and filled the
source input manually. The old frontend kept project choice only in React state.
These differences explain both the owner's failure and W4A's successful harness.
Before edits, the full packaged W4A creature journey passed in **69.052 seconds**.

Inspected sources included root guidance, approved owner plan, workflow reference,
W4A report/receipt, native runners, worker/authoring boundaries, Tauri configuration,
runtime preparation, launcher inventory and current local/remote Git identity.

## Delivered startup behavior

Use **[Launch Workbench.vbs](../Launch%20Workbench.vbs)** or the corrected existing
desktop shortcut. Its target now runs that cwd-independent launcher; a backup of
the original shortcut remains in ignored local evidence. The supported executable
is `G:\GameDev\RoguelikeProject\workbench\src-tauri\target\release\resonance-workbench.exe`.

Project priority is valid saved choice, valid checkout containing the running app,
then the validated optional `owner-defaults.json` fallback. No interpreter
directory, sibling project or initial working directory supplies game source.
Successful choices are atomically saved in
`%APPDATA%\com.resonance.workbench\project.json`. **Change Project** remains
available; invalid old settings report their reason and use a validated fallback.
Missing all candidates produces one explicit recovery flow with checked paths.
Root/data markers, current imported game modules and contracts are verified before
authoring; settings never contain executable paths or file/review tokens.

Bundled launch resolves resources with Tauri's
[`BaseDirectory::Resource` API](https://v2.tauri.app/develop/resources/), using the
existing resource map. Normal release launch uses `release\python\python.exe`
and `release\bridge.py`. Development uses the real development bridge and the
verified CPython environment at
`G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe`, with
imports independently verified under the selected current `RoguelikeProject`.
The historical environment supplies dependencies only.

Raw dependency executables now report `UNSUPPORTED_LAUNCH`. Ordinary bundled
launch visibly ignores stale `RESONANCE_PYTHON`; deliberate external diagnostics
require `--diagnostic-runtime` or a development build. Bad candidates report their
exact attempted mode/paths without selecting another project. The host verifies
bridge bytes, app/worker version, protocol, dependency/import checks and existing
`g2-2`, `immediate-components-1`, `revenant-hp-1` capabilities before readiness.
The publication version guard now derives from the application package version.

Both build configuration routes include Python. The production build hook checks
pinned Python **3.11.0**, exact dependencies and native imports; an incomplete
runtime fails the build deterministically. No preparation step is required by an
owner launching a complete distribution. The existing isolated worker, five
independent drafts, source hashes, entitlement checks and atomic writer remain.
No host permission, gameplay API, active data definition, save or wiki changed.

## Verification and observed state

[Machine receipt](w4b-verification.json) records exact paths, executable/installer
and source hashes, commands, native outcomes and log hashes. Full logs, temporary
data/config roots and binary copies remain under `workbench/.artifacts/w4b/`.
Windows x64 10.0.26200, WebView2 155, Node 24.15.0, Rust 1.95.0 were used.

| Check | Result |
| --- | --- |
| `npm.cmd test`; `npm.cmd run typecheck` | 27 tests; typecheck passed |
| `cargo test --locked --manifest-path src-tauri/Cargo.toml` | 21 passed |
| `cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings` | passed |
| Pinned development Python, `-B -m unittest discover -s worker -p test_*.py -v` | 34 passed, no skips; 299.167 s |
| `test_structure_contract test_structure_access test_crafting test_gameplay_g17` | 34 passed; 8.907 s |
| `npm.cmd run bundle` | release executable, resources and NSIS 0.7.1 built |
| `npm.cmd run test:startup` plus explicit owner-shortcut opt-in | all 17 native scenarios passed |
| `npm.cmd run test:creatures` | complete W4A publication/host safety journey; 85.670 s |
| `npm.cmd run test:visual`; `npm.cmd run test:recipes` | W2/W3C publication regressions; 47.765 / 66.211 s |
| `WORKBENCH_TEST_MODE=creature-worker-timeout`, `test:desktop` | real 90.167 s deadline, draft retained, no publication |
| `WORKBENCH_TEST_MODE=creature-worker-cancel`, `test:desktop` | cancellation retained draft and reaped worker |

The 17 startup scenarios cover fresh app-local launch, restart, deliberate project
change/restart, dirty-draft keep policy and old-token revocation, stale/corrupt
settings, ignored stale override, unavailable diagnostic interpreter, actual raw
`release\deps` executable, portable resources in a spaced/extended Windows path,
real development interpreter, initialization exit/cancel, protocol mismatch,
malformed output, and the corrected desktop shortcut twice using real per-user
settings. Negative cases granted no document/catalogue authority or settings file.
Resolver fixtures additionally cover saved-choice priority, missing all projects,
invalid data folders, bridge mismatch and settings version validation.

Fresh owner launch browsed **189** supported/read-only source entries, selected
`hollow_revenant`, and constructed the real production actor with **14/14 HP**.
`starting_lab` generated an **80×43** scene with origin **(10,13)** and arrival
**(15,20)** through the existing production route. The W4A regression separately
published/reopened the exact **19/19 HP** variant only in disposable data.
Full runs recorded zero external requests/console errors and no leftover worker
temporary roots. Initial handshake-field and publication-version omissions were
caught during iteration and fixed before the final runs; failed iterations are
retained locally and are not counted as passing evidence.

After committing implementation, the corrected shortcut was launched again with
both Python/config overrides absent. The live worker and UI reported revision
`6c6c99da288574e25866f2df5070aa53bc9657e6`. The
[normal startup](images/w4b/owner-startup.png) and
[1100×740 startup](images/w4b/minimum-window.png) captures were visually inspected.

The preservation checker found **7,972 protected files and all seven personal
saves unchanged**, including measured metadata and save membership. Its inherited
manifest baseline is honestly `7745f72ea5446af22d3f340c30043d3752ef0f54`; a separate
comparison verifies all **590 tracked game/requirements files** unchanged against
the actual W4B baseline. The owner plan SHA-256 remains
`bcf41ab230fea7aa43a2a2f26b2826bd6d0d53ec814c788903badc642910f49a`.

The NSIS installer was built; it was **not installed**, signed or exercised on a
clean WebView2 machine. No installed NSIS shortcut is claimed tested. The owner
shortcut and actual built portable application were exercised instead, without
registry installation. W4B stops at reliable startup; creature placement and
other later editing/gameplay milestones are not included.
