# B3 autonomous verification

Run from production `main` at `G:\GameDev\RoguelikeProject`:

```powershell
& 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe' tools/verify_b3.py
```

The existing interpreter is reused in place (Python 3.11.0, Pygame 2.6.1,
SDL 2.28.4, tcod 19.3.0, NumPy 2.4.6). No environment or source copy is created.
Another interpreter with the same installed requirements may run the same tool.
The worker imports the production source and redirects `SAVE_DIR` in that child
before the real bootstrap. Each worker has a bounded disposable save root under
`.baseline`, dummy SDL/audio, a fixed seed, exact source bindings and a timeout.
Only save fixtures are cloned for independent readers; writer bytes are checked
again at the end. No desktop control, physical input or owner testing is used.

The default gate covers:

- Whole-checkpoint same-process and independent-process reconstruction, actual
  stair writes after save, inactive dirty layers/actors, eviction and processing.
- Termination at each publication boundary, including individual player/world/
  metadata/scene writes, manifest, sealed generation, backup, pointer and commit.
  Fresh readers prove old-or-new whole state. Separate first-save interruptions
  cover the absence of a previous checkpoint. Intentional exits are accepted only
  with the exact reached-boundary marker, exit status and source evidence.
- Corrupt pointer, active/inactive scene, manifest and checksum-consistent malformed
  component fixtures; recovery, explicit previous rollback, all-invalid rejection,
  recovery messages and preservation of live owners/save bytes.
- Short writes/storage failure, failed eviction, competing kernel locks, stale
  writers and publication during load. A killed lock-holder must release its lock.
- Active-slot death/quit/debug deletion, sibling isolation, invalid IDs and a
  disposable redirected-directory refusal. No owner save is inspected.
- Original Engine.run and paired app-local key events for F5, stairs, F9 recovery
  and continued turns, with offscreen game-surface captures.
- Accepted B1 scene/gear/light/lurker cases, payload rejection, startup and all
  prior gameplay journeys; B2 components/items/actors/processing and journeys;
  the original 32 persistence diagnostic properties.

Format tests intentionally author and reseal semantic fixtures to reach payload
validation. Separate raw-corruption tests do not reseal their damaged bytes.
Synthetic flat fixtures exercise legacy v2 validation; an actual pre-B3 B2
checkpoint captured on main independently checks read-only legacy compatibility.

`--only` and `--case` are investigation filters. A partial run never certifies
completion. Missing results, timeouts, unexpected exceptions, zero checks, wrong
source bindings, missing workers or changed source fail the full gate.

Final evidence lives in `evidence/b3-results.json` and `b3-summary.json`, with
the exact source, argv, CWD, PIDs, phases, dependency versions, stdout/stderr,
expected/observed checks, hashes and selected game captures. Historical B1/B2
evidence remains unchanged. Their older copy-based runners are historical;
use `verify_b3.py` for the current main-only workflow.
