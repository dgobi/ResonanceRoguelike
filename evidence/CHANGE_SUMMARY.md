# Arc A change summary

## Files modified or added

* `.gitignore` — ignores disposable `.baseline/` copies; no gameplay change.
* `requirements-baseline.txt` — exact tested game dependency versions for a separate Python 3.11 venv.
* `tools/baseline.py` — safe fresh-copy launch and optional labeled observation/fixture commands.
* `tools/persistence_diagnostics.py` — five isolated cases, ten writer/reader processes, expected versus observed properties and source hashes.
* `tools/owner_lesson.py` — reversible food-definition experiment through the real inventory handler.
* `tools/render_baseline_screens.py` — clearly labeled offscreen craft/text/look component renders.
* `README.md` — short owner entry point.
* `roguelike/docs/owner/START_HERE.md`, `RUNTIME_MAP.md`, `WORLD_AND_STATE.md`, `CONTENT_ROUTES.md` — launch, active flow, state ownership and consumer map.
* `roguelike/docs/owner/STATUS.md`, `DECISIONS.md`, `OWNER_LESSON.md`, `OBSERVATIONS.md`, `NEXT_ARC.md` — implementation labels, open choices, lesson, evidence limits and separate B1 brief.
* Both `CLAUDE.md` files and 18 existing `roguelike/docs/*.md` files — status prefix only; all original bytes retained. `historical-labels.json` enumerates and verifies each.
* `evidence/` — source/status manifests, environment, generated run logs, selected game screenshots, diagnostic results and verification records. No personal saves or old private game log.

## Bugs / tasks addressed

* Isolated Windows launch: **verified**, Python 3.11.0 / Pygame 2.6.1 / tcod 19.3.0. No asset or game-code correction was necessary on Windows.
* Bounded gameplay observation: **partial**; launch, ordinary movement, manual wait and inventory confirmed. Remaining scenarios blocked by input delivery and the desktop tool's retained Escape-stop state, even after renewed permission.
* Persistence diagnostics: **harness complete; game properties deliberately fail**. Surface content is replaced by underground content, empty inventory/equipment fails replacement, and dormant creature identity is lost. No fixes made.
* Owner orientation: initial handbook delivered; numeric lesson passes and edit is undone. Manual lesson and owner learning are **awaiting validation**.

## Secondary issues noticed, deferred

Text component clipping at 1280×720; misleading craft-ready footer; loaded Needs/hooks/light reconstruction; transfer/crafting ownership; unconsumed dungeon loot lists; Windows font-path case mismatch. See STATUS and CONTENT_ROUTES for scope and prioritized backlog.

Crash check: **PASS for observed startup/movement/inventory interval**; no traceback, tcod FutureWarning only. Later process disappearance had no independently recorded exit cause.

Lab submap ascent: **FAIL for diagnostic persistence property**; window/FOV ascent and descent check **INCOMPLETE**. Do not treat the component traversal as a manual FOV pass.
