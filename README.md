# Resonance roguelike — production main

G9 adds bounded country-road shortcuts over the complete G8 settlement and rural
baseline. Read [G9 delivery](docs/owner/WORLDGEN_G9.md), the
[country-network guide](roguelike/docs/COUNTRY_NETWORK.md) and the
[structure authoring guide](roguelike/docs/STRUCTURE_AUTHORING.md).

Work stays in this checkout on `main`, with named checkpoints and local commits;
follow [AGENTS.md](AGENTS.md). Tests use headless processes, app-local events and
disposable save roots. Personal campaigns are preserved.

Run the focused and full production gates with the established environment:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike --timeout 1800
& $ResonancePython -X utf8 tools/worldgen_g9_diagnostic.py --journey --evidence evidence/worldgen-g9/owner-diagnostic-02
& $ResonancePython -X utf8 tools/verify_d.py
```

The interpreter path supplies dependencies only; game code runs from this checkout.
The [G1](docs/owner/WORLDGEN_G1.md), [G2](docs/owner/WORLDGEN_G2.md) and
[B3](roguelike/docs/owner/B3_STATE.md) records retain their historical scope.
# Maintained owner documentation

The current settlement composer is documented in
[WORLDGEN_G8.md](docs/owner/WORLDGEN_G8.md). Open the maintained
[Resonance Owner Wiki](Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html)
locally for the complete offline guide, including G7 compounds, G8 streets,
commons and frontage, and G9 network preview/tuning and save contracts. Editable source and rebuild instructions live in
`Resonance_Wiki_Maintenance/`.

