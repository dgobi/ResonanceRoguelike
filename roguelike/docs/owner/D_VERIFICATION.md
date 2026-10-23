# D autonomous verification

Completed run `d-20261023-123410-e7af593e` tested implementation `257b41d`:
**159 workers and 3,675 checks passed, zero failed**. This includes 146 normal
workers and 13 deliberately terminated checkpoint writers, plus seven negative
harness controls. Compilation, dependency consistency and whitespace checks pass.
The final evidence commit changes documentation/evidence only; source hashes are
rechecked before packaging. The preservation audit verifies 645 unchanged prior
tracked files and the accepted C archive.

Run from `G:\GameDev\RoguelikeProject`:

```powershell
& 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe' -X utf8 tools/verify_d.py
```

Only the existing interpreter is reused. Every worker imports production source
in place and uses a disposable `.baseline` save root with SDL video/audio dummy
drivers. No window activation, desktop input, personal-save access or source copy.

The complete gate independently enumerates 159 workers: all 143 B1/B2/B3/C
workers plus 16 D workers. Thirteen are deliberately terminated checkpoint writers.
Seven separate negative controls enforce nonzero, complete, current, correctly
bound evidence. Partial runs (`--only d`, `--case ...`) never certify completion.
The runner hashes Python source and authored JSON definitions before and after.
Assertion counts include harness checks, not just distinct player scenarios.

| Group | Observable contract |
| --- | --- |
| D-01 | Armor mitigation, final charge, dodge/invincibility/wait, refresh, transfer |
| D-02 | Coating damage and charge parity, misses, blocked corners, lethal scaling |
| D-03 | Real passive suppression, expiry and authored moveset application |
| D-04 | AI pause/resume, stable-identity Disconnect, normal blade equipping |
| D-05 | Multiple aura sources, stable wraith identity, suppression/death |
| D-06 | Confirm/cancel/stale-owner handling, cost and sight expiry |
| D-07 | Aim/cancel, range/visibility/path rejection, zone pause/expiry |
| D-08 | Salve/sprint timing, final move, expiry, waits, blocked moves, composition |
| D-09 | Pending/live retirement clocks, cached actor freeze, hot-map deduplication |
| D-10 | Same-process and fresh-process checkpoints, then actual effect consumers |
| D-11 | Four original Engine.run/render journeys with paired app-local events |

The journeys cover inventory confirmation and true-sight health UI, throw aiming
and cancellation, zone lifetime across F5/F9, salve movement/expiry, and armor /
coated moveset combat. Fixtures use actual factories and resolver/AI functions;
none substitute successful combat or effect outcomes. Definitions/positions may
be configured in disposable process memory to make contracts measurable.

`evidence/d-before` freezes eight observations from accepted C before edits.
`evidence/d-results.json` is the full completed gate record; `d-summary.json`,
`d-final-checks.json` and `d-preservation.json` give totals and preservation checks.
`d-screens` holds offscreen captures from the original renderer. The independent
UI-TEXT-HEIGHT signature remains enforced and is not silently accepted as repaired.

The review ZIP includes an exact binary patch from accepted C, readable changed
files, source/member hashes and an archive verifier. Patch verification uses only
a temporary Git index and must produce the committed tree without changing HEAD
or the working tree. No test saves, dependencies or source checkout are packaged.
