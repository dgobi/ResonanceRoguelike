# Resonance roguelike — production main

G12 repairs the Revelation Lens, satchel carrying, real preparation costs and
complete found-text access. See [G12 delivery](docs/owner/GAMEPLAY_G12.md),
[equipment, carrying, heat and reader controls](roguelike/docs/SYSTEMS.md), and
[recipe/item authoring fields](roguelike/docs/DATA_REFERENCE.md).

G10 gives the eight existing wilderness biomes coherent tree stands, clearings,
wet patches and rock masses, with an explicit saved surface policy. Read the
[terrain tuning and preview guide](roguelike/docs/WILDERNESS_TERRAIN.md).
G11 preserves reciprocal exterior access through wilderness entrance placement
and final composition for new campaigns. Existing G9/G10 campaigns retain their
historical generation routes. See [G11 delivery](docs/owner/WORLDGEN_G11.md).
G9's bounded country-road shortcuts preserve the complete G8 settlement and rural
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
& $ResonancePython -X utf8 tools/verify_g12.py --evidence evidence/gameplay-g12/owner-verification
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
`Resonance_Wiki_Maintenance/`. Wiki upkeep is commissioned separately through
targeted owner briefs; G10 leaves that edition intact.

