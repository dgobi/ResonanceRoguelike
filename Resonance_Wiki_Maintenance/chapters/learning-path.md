# Start creating

Start with one idea small enough to observe: a more sustaining ration, a note beside a dangerous room, a guard that withdraws, or a tool that remembers unfinished work. You do not need to understand the whole game first.

This edition reviews production source `c166ec650b98156d53b8ea72e715c028d27db905` (SYS-5). It extends the older G9 handbook. Historical reports remain in the source library; pending action-adventure proposals are not installed behavior.

## Open, choose, run

Open `Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html` directly. Reading, search, answers, images and embedded examples need no server or connection. The Python exercises need a checkout of the reviewed game and its installed dependencies. The portable ZIP carries handbook source and practice material, not an entire game installation or dependency cache.

In PowerShell at the **production repository root**, select the existing supported interpreter:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython --version
& $ResonancePython -m pip check
& $ResonancePython -X utf8 -B Resonance_Wiki_Maintenance/practice.py L01 --output evidence/guide-1/my-first-run
```

The interpreter path is this machine's dependency environment; the launcher takes source from the checkout containing it. On another installation create `.venv` using `py -3.11 -m venv .venv`, install `requirements-baseline.txt`, and set `$ResonancePython` to that environment's executable. An initial install may need internet or previously downloaded wheels. Offline reading is a different promise from offline installation.

The launcher announces the lesson, source revision, temporary **payload**, separate **state root**, and reset scope. Its bounded payload follows the Workbench test-fixture pattern: required production Python, data and assets copied for one test. It has no Git directory and is not a place to develop the game. It cannot publish a definition. Personal campaigns are never selected. The default run is headless and finite. Add `--play` to open that practice room yourself, or `--keep` to retain its announced temporary files for inspection. Every fresh invocation supplies the full starting state; no previous lesson must have been completed.

## Choose a short route

| Your interest | Route | Supplied so you can start independently |
|---|---|---|
| Content | [L01](#L01), [L02](#L02), [L03](#L03), [L04](#L04), [L13](#L13) | Room, ordinary starting equipment, source definitions |
| Places | L01, [L06](#L06), [L07](#L07), L13 | Ready-made guard, note, meal, fire and exit |
| Abilities | L01, [L09](#L09), [L10](#L10), [L11](#L11) | Weapon, target and explicit lesson registrations |
| Persistent systems | L01, L10, L11, [L12](#L12), [L14](#L14) | Full state machine, save checks and cold-process driver |
| Appearance | Take [L08](#L08) whenever visual feedback matters | Existing registered assets and real renderer |

Reference lookup is allowed throughout. Use [I want to…](#task-index) to skip the course. The [system atlas](#system-atlas) explains relationships, and [authoring reference](#authoring-reference) describes current tool boundaries.

## What to do in each lesson

Predict the result before running. Trace the few named methods. Study the worked solution, make the variation, diagnose the fault, then attempt the independent requirement. Open the graduated hints only as needed. A passed automated check establishes a scenario; it does not establish that you understood it.

Keep a plain text note with `lesson ID | followed/varied/independent | decision | evidence path | revisit`. A ready template is `examples/guide1/notes.txt`. There is deliberately no browser-only progress store. Your own text file remains readable after browser storage is cleared or the guide moves.

At the next session, recall where the action enters, which object owns the changed value, and what proved success. Revisit after roughly a day, several days, a week and a few weeks if useful. These are optional practice intervals, not a tested optimum. No personal completion times or mastery claims are supplied.

## Restart, keep or discard

Each default run deletes only its freshly allocated temporary payload after writing receipts. A failed run's log remains in the output directory. Use `--keep` when investigating; restart with a new invocation instead of editing the captured Python. Store deliberate JSON candidates outside production scans, and pass `--draft your-file.json` on the lessons that support it. The candidate's ID stays fixed for the fixture.

When you decide to keep a creative change, apply its reviewed diff to production `main`, create a named checkpoint first, validate its dependencies and actual appearance route, and commit only the intended files. Practice never performs that publication. See [maintenance](#maintenance) for exact commands and conflict-safe reversal.
