# C autonomous verification

Run from production `G:\GameDev\RoguelikeProject` on `main`:

```powershell
& 'G:/GameDev/RoguelikeBaseline-20261020/project/.venv/Scripts/python.exe' -X utf8 tools/verify_c.py
```

Only the interpreter in the existing development folder is reused. All imports
bind to production main. Workers use real Pygame/tcod/NumPy and dummy SDL video and
audio; saves go under `.baseline/c-<timestamp>-<id>`. The runner creates no source
copy, worktree, task branch, desktop input or interactive window. Tests require no
routine owner verification. `--only` and `--case` are diagnostic partial runs and
cannot certify acceptance.

The enforced gate independently enumerates 143 workers: all 132 accepted B1/B2/B3
workers, plus eleven C workers. Thirteen B3 workers terminate deliberately at
checkpoint publication boundaries. The seven existing negative harness controls
reject missing/empty/stale/wrong-phase/false/crashed/timed-out evidence. Binding
checks validate actual loaded source hashes and independent writer/reader PIDs;
canonical writer save bytes remain untouched. Source must remain unchanged during
the complete run. Check counts include harness assertions, not independent features.

| C case | Behavioral evidence |
| --- | --- |
| C-01 | Blade/armor/light/talisman drop, re-pickup, re-equip, duplicate and stale operations, equipment replacement |
| C-02 | Invalid destination, full bag, exact floor source despite stale coordinates, legacy entity pickup; reproduced baseline defects |
| C-03 | Container duplicate instances, nested state, capacity/stale/closed rejection, legacy row materialization |
| C-04 | Campfire cancel/invalid placement/confirmation, reusable equipped tool |
| C-05 | Whole recipe preflight, invalid/overweight output, exact component choice, stale processing, cancellation/completion and pending-craft save/load |
| C-06 | Full-capacity vessel replacement, failed/successful refill and harvest |
| C-07 | Same-process and fresh-process checkpoints containing inventory, floor and container owners with distinct instance fields |
| C-08 | Original `Engine.run`, paired Pygame key events, original renderer: equipped drops, partial take-all, second container item, craft cancel/confirm, F5/F9 |

Before evidence in `evidence/c-before/` binds the accepted B3 source: the equipped
blade drop retains its slot, empty inventory blocks pickup, take-all erases rejected
items/corpses, container previews lose fuel/recreate instances, and campfire cancel
loses exact fuel. Fixture construction is recorded; gameplay claims do not rely
on a screenshot alone. The C gate requires this observed baseline record.

The old B1 drop oracle now positively requires cleared slot/flag and a successful
save. Burnout positively requires darkness and released owner reference (the light
may now be absent). Remaining UI-TEXT-HEIGHT observations still match the frozen
B2 signature exactly. The original B3 artifact/evidence is retained unchanged.

Final results: `evidence/c-results.json`, concise totals and environment in
`evidence/c-summary.json`, working-file preservation in `evidence/c-preservation.json`,
and offscreen captures in `evidence/c-screens/`. The review ZIP contains the exact
committed patch, readable changed files, hashes and a verifier. Its optional Git
check applies the patch only to a temporary index and compares canonical trees;
it never resets or changes the user's checkout.
