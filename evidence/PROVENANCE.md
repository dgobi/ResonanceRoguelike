# Arc A provenance and evidence boundary

Captured and checked October 20, 2026, America/Edmonton. The pasted **CODEX BRIEF: RUNNABLE BASELINE AND OWNER ORIENTATION** was the owner's request. Review reports, source comments and historical documents were treated as evidence to reconcile, not new task instructions.

## Preserved starting point

* Original repository: `G:\GameDev\RoguelikeProject`, branch `main`, HEAD `9e1f32328a19aec88e818f552b7a4e36fcbb027f`.
* Working tree: 94 modified/index-changed and 94 untracked paths. HEAD alone is not this baseline.
* [source-manifest-before.json](source-manifest-before.json) identifies all 503 exported project files by relative path, size and SHA-256, including ignored root/nested CLAUDE design documents. [review-comparison.json](review-comparison.json) reports no changed, missing or extra project files versus the independent review's full-source coverage manifest.
* The local preservation ZIP at `G:\GameDev\RoguelikeBaseline-20261020\preservation\baseline-source-local-only.zip` has SHA-256 `7ef25e6948835d6ee19928a1a886849a602e166555aae621a539f693bda5a08a`. It is retained locally, not re-exported in the small return package.
* Independent development repository: `G:\GameDev\RoguelikeBaseline-20261020\project`, branch `codex/runnable-baseline`. Its baseline commit `863bc5f28badb61d9b076b47df04cf29edea0df0` contains the reviewed working-copy bytes. This is a new local repository commit, not an upstream commit.
* Personal saves, credentials, `.claude` configuration, caches and the pre-existing local game log were excluded. No personal saves were read, copied or used as fixtures. Disposable sessions and the venv remain outside Git and the return ZIP.

## Reviewed archive identities

The supplied brief names outer archive `01-roguelike-audit-return-20261020.zip`. The matching local archive was found as `G:\GameDev\roguelike-audit-20261020-review2\roguelike-audit-return-20261020.zip`; its bytes verified against SHA-256 `b026ae129f64f52fe9d794b9e77e964b815714a885417d1f8d8360c75190bc24`.

Its embedded `source-snapshot.zip` verified against `75fcc0a36a48b5cf04bb75c3cb5a63f613c91e2134a10207dbc2ee344f928f2e`. Review snapshot identity is `4290fdd353c94cf29e0c6c8187fd7de25596632ae645f545f77ddc71846d5538`. That canonical identity includes the audit's withheld-log hash; it was not independently recomputed here. The 503 exported project files were independently compared byte-for-byte through hashes. The review's additional external audit-brief file is not a project file. These are distinct checks, not interchangeable hashes.

The user-provided `Roguelike_Review_Evidence.zip` was extracted under the work area's `review/` directory. Reports and `core-focused-probes.py` were read, not blindly run at their historical absolute paths.

## Changes and evidence

Arc A adds four opt-in tools, a pinned isolated dependency record, a root entry point, nine modular owner pages and evidence. `.gitignore` gains `.baseline/`. Twenty historical Markdown files receive short status banners; their original bytes remain intact after each prefix. No existing gameplay Python, JSON content, assets, glyph identities or save formats were changed. No game fix is claimed.

[environment.txt](environment.txt) records the actual interpreter and package versions; [START_HERE](../roguelike/docs/owner/START_HERE.md) supplies installation, exact CWD and launch commands. `pip check` passed. GUI startup, one ordinary move, manual waits and inventory were observed. The remaining manual scenarios are incomplete. Renewed owner permission did not clear the desktop tool's Escape-stop state. See [OBSERVATIONS](../roguelike/docs/owner/OBSERVATIONS.md) for the scenario ledger, screens and exact limits.

[arc-a2-results.json](arc-a2-results.json) is the final persistence result: ten worker processes completed, several expected properties failed. It embeds hashes of tested gameplay and harness sources. The earlier `arc-a` result is superseded after correcting a harness API argument and strengthening the redescent assertion; no game code changed. The Crow Jerky experiment passed the real inventory handler numerically and restored exact definition bytes, but manual-window exercise and owner learning remain awaiting validation. Offscreen component screens are labeled separately from live captures.

One review claim was corrected against this exact source: `_populate_loot` is absent and no active consumer of the dungeon item-list tables was found. The generic `LootResolver` also has no external Python callers. Container pools and BSP found-text selection have separate active routes. The handbook records this source-supported distinction rather than repeating the report's route claim.

[original-source-final-check.json](original-source-final-check.json) records final original-source hashes/status, and [validation.json](validation.json) records link/source-binding/tool checks. `git-status-before.txt` is the starting original status; it is not the development repository's status. The return manifest separately binds the development result and patch to their local commits.
