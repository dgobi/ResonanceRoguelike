# Set up and run the game

This handbook documents **Resonance Roguelike**, the Python, Pygame and tcod game in `dgobi/ResonanceRoguelike`. Its verified source snapshot is `main` at `4d7a7892e1afffb8d872ed4a8fd442984d14e7d5`, the reviewed G7 delivery. It is independent of the Godot Project Volumnia project.

## Find the two roots

The **repository root** contains `README.md`, `requirements-baseline.txt`, `tools/`, `docs/` and `roguelike/`. The **game root** is the `roguelike/` directory containing `main.py`, `config.py`, `data/` and `assets/`. Commands in this handbook start at the repository root unless explicitly stated otherwise. Paths beginning `roguelike/` are always repository-relative.

Many game paths are relative to the process's current working directory. Running `python roguelike/main.py` from the repository root is therefore not the normal launch recipe. Change into `roguelike/` first, or use the disposable launcher below, which does it for you.

## Use the existing environment

The repository records a Windows x64 / CPython 3.11 baseline and these dependency pins:

| Package | Recorded pin |
|---|---|
| pygame | 2.6.1 |
| tcod | 19.3.0 |
| numpy | 2.4.6 |
| cffi | 2.1.1 |
| pycparser | 3.11 |
| typing_extensions | 4.16.0 |

On the existing machine, the repository's command examples use this interpreter:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython --version
& $ResonancePython -m pip check
```

That path supplies dependencies; it does **not** decide which game's source runs. Run the commands from your current production checkout. If your environment lives elsewhere, set `$ResonancePython` to that environment's `python.exe` instead. No activation is necessary.

For a new installation, open PowerShell in the repository root and create a local environment:

```powershell
py -3.11 -m venv .venv
$ResonancePython = (Resolve-Path '.venv\Scripts\python.exe').Path
& $ResonancePython -m pip install -r requirements-baseline.txt
& $ResonancePython -m pip check
```

Use the requirements file belonging to the same checkout. The wiki's focused checks also ran under Linux / CPython 3.12.14 with the declared package pins; that is a bounded verification result, not a replacement for the project's recorded Windows target.

## Start a fresh world for authoring

The current convenience launcher uses the production source and isolates only the save directory:

```powershell
& $ResonancePython -X utf8 tools/play_disposable.py --session cottage-first-01 --seed 20261023
```

Choose a fresh session name each time. Names allow 1–64 letters, digits, underscores or hyphens. The save root is `.baseline/g3-play-cottage-first-01/`; the `g3-play-` prefix is retained even though the current generator is G9. It refuses to reuse an existing session. It has **no `--resume` flag**.

For an automated startup check with no desktop interaction:

```powershell
& $ResonancePython -X utf8 tools/play_disposable.py --session cottage-smoke-01 --seed 20261023 --headless-smoke
```

This initializes the actual game, prints the seed, plan mode, start coordinates, submap and save root, and exits before the interactive loop. A good result includes `"plan_mode": "shared-v1"`. It tests startup; it does not prove that every new building was selected, that controls work physically on your machine, or that a complete playthrough succeeds.

For the audited source and seed `20261023`, this check started at world chunk `[73,99]`, in `sub_73_99_0`. Do not follow old hardcoded directions to `(0,64)` for this world.

## Launch an ordinary campaign

From the repository root, after setting the interpreter variable:

```powershell
Push-Location roguelike
& $ResonancePython -X utf8 main.py
Pop-Location
```

This uses the ordinary `roguelike/saves/slot_0/` state. Read [Save, load and world changes](#saves-and-state) before relying on that campaign: the shipped configuration has `DEBUG_MODE = True`, which changes the meaning of F5 and F9.

## Work on the production source

The current project convention is to work directly on `main`, preserve unrelated changes and create named Git checkpoints before substantial changes. Old instructions for `codex/b1-persistence`, `codex/b2-reconstruction` and separate development copies are historical.

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git diff -- roguelike/data/items/weapons/severance_blade.json
```

Before editing, establish whether the file already contains your own unfinished work. A Git tag identifies a committed state; it does not capture uncommitted edits. When a coherent edit is ready, review and stage the specific files it changes, then make a descriptive commit. Avoid staging unrelated work.

`tools/baseline.py` still exists for historical evidence and intentionally copies the game into `.baseline/<session>/roguelike/`. Its `--resume` reuses that old copy. It is not the recommended launcher for testing today's edits to the production checkout. Do not mix the two launchers' save locations.

## Where to go next

- [Make a small, verifiable change](#first-change) establishes the edit → check → observe cycle.
- [Controls](#controls) describes actual input dispatch.
- The **World & structures** chapters explain creating content and making it appear.
- **Content catalogues** contain the exact JSON shipped in this revision.
- [Verification](#verification) explains which command answers which question.

## Source basis

[README](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/README.md) · [requirements](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/requirements-baseline.txt) · [current launcher](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/tools/play_disposable.py) · [bootstrap](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/main.py) · [collaboration rules](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/AGENTS.md).
