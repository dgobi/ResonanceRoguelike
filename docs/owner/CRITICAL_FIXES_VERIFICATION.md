# Critical fixes applied on 23 October 2026

Applied `Resonance_Critical_Fixes_2026-10-23.zip` directly to the existing
production checkout on `main`. The checkout was clean at
`04f703599f0e20c8a4b9f9dea256f66de0494bfd`, marked by
`checkpoint/critical-fixes-start-20261023`. The verified delivery is marked by
`checkpoint/critical-fixes-verified-20261023`.

The supplied checker recognized all ten original game files. The local
`FullGame.zip` matched the package's base-archive SHA-256, and `git apply --check`
passed. No reconciliation was necessary. All 21 applied and staged payloads match
the package after line-ending normalization; no package code was changed during
application. Existing CRLF blobs and the four verbatim historical test helpers
retain their formatting.

The fixes cover explicit checkpoint preservation during travel, bounded reachable
interactions, successful-transfer turn costs, modal stair input, complete recipe
allocation, durable wraith exposure and pursuer destinations, shared melee hooks,
stable creature identity, single death finalization, and font directory casing.
See [Tuning existing features](TUNING_EXISTING_FEATURES.md) for the owner guide.

Validation used the existing Python 3.11.0 environment with pygame 2.6.1,
tcod 19.3.0, and NumPy 2.4.6. Both commands ran against this checkout with dummy
SDL and disposable saves:

```powershell
& 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe' -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike
& 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe' -X utf8 tools/verify_d.py
```

- All 66 focused tests passed, including 4,096 exhaustive crafting comparisons.
- The full D gate passed all 159 workers and 3,675 checks, with zero failures.
  This includes 13 deliberately interrupted writers and seven negative harness
  controls. The gate's source hashes still match the applied source.
- Python compilation, dependency consistency, and whitespace checks for runtime
  changes, the guide, and new tests passed. The unchanged historical helper
  `b1_support.py` retains its original final blank line.
- The preservation audit found 676 unchanged pre-existing tracked files. The
  ten intended game files and generated `evidence/d-latest.json` account for the
  other eleven. All seven personal-save files and `FullGame.zip` are unchanged.

[Verification summary](../../evidence/critical-fixes-20261023/summary.json) records
package provenance, payload hashes, preservation checks, and results.
[Focused test output](../../evidence/critical-fixes-20261023/focused-tests.txt)
and the [complete compressed D gate report](../../evidence/critical-fixes-20261023/d-results.json.gz)
retain the detailed evidence. The latter is a gzip-compressed JSON file, with its
uncompressed SHA-256 in the summary. Earlier accepted D evidence remains intact.

The existing `UI-TEXT-HEIGHT` defect remains deferred and was detected by the
unchanged gate. Incomplete moveset features identified by the tuning guide remain
outside this correction pass. No new branch, worktree, development checkout,
desktop control, or personal-save migration was used.
