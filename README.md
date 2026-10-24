# Resonance roguelike — production main

G7 adds small multi-building compounds with shared access, mixed rural destinations,
durable child ownership and complete authoring workflows. Read
[G7 delivery](docs/owner/WORLDGEN_G7.md), [G6 history](docs/owner/WORLDGEN_G6.md) and the
[structure authoring guide](roguelike/docs/STRUCTURE_AUTHORING.md).

Work stays in this checkout on `main`, with named checkpoints and local commits;
follow [AGENTS.md](AGENTS.md). Tests use headless processes, app-local events and
disposable save roots. Personal campaigns are preserved.

Run the focused and full production gates with the established environment:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike
& $ResonancePython -X utf8 tools/worldgen_g7_diagnostic.py --journey --evidence evidence/worldgen-g7/diagnostic
& $ResonancePython -X utf8 tools/verify_d.py
```

The interpreter path supplies dependencies only; game code runs from this checkout.
The [G1](docs/owner/WORLDGEN_G1.md), [G2](docs/owner/WORLDGEN_G2.md) and
[B3](roguelike/docs/owner/B3_STATE.md) records retain their historical scope.
