> Historical accepted record. Current main-only verification and remaining scope: [B3_VERIFICATION](B3_VERIFICATION.md) and [B3_DEFERRED](B3_DEFERRED.md).

> Historical accepted B1 contract. Current B2 status and commands are in [B2_VERIFICATION](B2_VERIFICATION.md). Four B2 defects below are now repaired; the current B1 regression runner asserts those repairs explicitly and retains the remaining baseline comparisons.

# Autonomous B1 verification

From `G:\GameDev\RoguelikeBaseline-20261020\project`, run:

```powershell
.\.venv\Scripts\python.exe tools/verify_b1.py
```

This is the enforced acceptance command, not a harness-completion-only command.
It runs the 34-case supplied matrix: 28 B1 gates and six separately classified
baseline characterizations. It requires every planned parameter worker and every
case, fails on an incorrect invariant, missing/stale evidence, zero assertions,
crash, timeout or source mismatch, and compares exact deferred-defect signatures
between the preserved baseline and candidate. `--only` is targeted development
diagnosis and explicitly never certifies the complete gate.

The suite uses Windows CPython 3.11.0, Pygame 2.6.1 / SDL 2.28.4, tcod 19.3.0 and
NumPy 2.4.6 from the existing isolated `.venv`; runtime pins remain in
`requirements-baseline.txt`. The tests add no dependencies. Standard-library
subprocess/JSON assertions are sufficient; no pytest or Hypothesis install was
needed. `pip check` and Python compilation accompany the final gate.

Each run gets a UUID-bearing `.baseline/b1-...` directory and disposable marker.
Game sources are copied without saves/caches. The baseline is exported from
`1b9531bda0ba593631ce7af4cb728165d7f4a7a9` and verified against the captured source
manifest. If that Git object is unavailable, `--baseline <reviewed-export>` accepts
only the same verified bytes. There is no reading/copying of personal saves and
no reuse of prior result files. Saved writer bytes are hashed immediately; writers
stop without subsequent travel. Independent readers receive identical save
copies; all travel writes remain in their own branches. Writer hashes are checked
again at the end.

Workers record run/scenario/phase/PID, exact command/CWD, seed, environment,
installed dependency versions, expected/observed checks, source origins and hashes,
stdout/stderr and exit status. Parent checks compare actual imported bytes with
the intended source copy. Workers use `SDL_VIDEODRIVER=dummy`,
`SDL_AUDIODRIVER=dummy`, and `PYTHONHASHSEED=20261020` set before startup. Global
random, NumPy, Engine RNG and AI RNG are seeded for fixtures. Cosmetic wall-clock
effects and private rendering RNGs are not asserted byte-for-byte.

API cases use real `main.main`, factories, save/load, maps and traversal. Their
replacement `Engine.run` callback is labeled API evidence. Journey cases wrap and
call the **original** `Engine.run`, post real paired KEYDOWN/KEYUP events and use
the original `event.get` queue. They supply stair Unicode, set/reset process-local
modifiers, verify the real Shift+W branch, and advance on observed frame/state
boundaries. Bounds are 200 polls, 80 turns, 90 seconds within the driver, and 180
seconds for a worker. No desktop input, focus, keyboard grabs, screenshots of other
apps or normal launch configuration changes occur.

The journeys cover lab startup, ordinary movement/wait, modal inventory,
pickup/equip/drop, ordinary unarmed bump combat, the existing bound sarcophagus
label, dry-bitter-herb ingredient consumption/placement/20-turn completion,
Unicode stairs, ordinary surface-edge movement, default debug F5 teleport/F9 dump,
and separately configured nondebug F5/F9 save/load. The nondebug terminal writer
also feeds a fresh-process real-loop bootstrap reader. Fixture setup and actual
player actions are recorded separately. Selected frames are saved from the real
Pygame surface and visually inspected; screenshots do not replace assertions.

The historical diagnostics are also run with `--assert-properties`: unchanged
baseline 32 assertions / 17 pass / 15 fail; candidate 32 / 32 / 0. A small wrapper
adds a 30-second timeout to each original diagnostic subprocess while leaving its
assertions and game modules unchanged. The old standalone lurker diagnostic now
saves its host before its fresh reader, because a seed-only file beside gameplay
records is correctly rejected as an incomplete v2 save. Full-scene lurker coverage
comes from the separate B1 tests.

Final machine-readable evidence is in [b1-results.json](../../../evidence/b1-results.json).
`evidence/b1-latest.json` points to the full local run directory. The return ZIP
contains the patch, readable changes, baseline/candidate logs, checkpoint hashes,
selected captures, the actual drivers, and independent ZIP/patch verification.
The owner's optional learning exercise requires no missing validation work.
