# Resonance Workbench · W0

An independent, local Tauri 2 desktop application for reading the current
Resonance source. Open a repository, inspect a shipped authored layout, run its
production validator and explore a generated 80 × 43 map. No playable game,
campaign, editor save operation or network service is started.

## Launch

Windows x64 is verified. The release directory contains
`resonance-workbench.exe`, `bridge.py` and `python/`; **keep all three together**.
Double-click the executable. The NSIS package includes those same resources.
WebView2 Evergreen must already be installed; W0's installer does not download
it. This machine was verified with WebView2 155.0.4283.62.

Choose **Choose repository**, or enter the directory and use **Open directory**.
Select this repository's root (the `roguelike/` subdirectory is also accepted).
The supported layout list currently contains `starting_lab`, a 60 × 16 source
definition. It produces a full 80 × 43 authored scene through the game compiler,
scene builder, generator and population factories.

Hover/click to inspect terrain coordinates and IDs; drag to pan, scroll or use
the buttons to zoom, and press Home to fit. Arrow keys pan the focused canvas.
**Generate / refresh** reloads source and uses the entered seed.
**Test invalid disposable fixture** runs the same validator on a temporary copy
with a deliberately incorrect width. **Cancel** terminates the active worker.
Source JSON is a read-only text view; closing/reopening never rewrites it.

## Development and builds

Requirements: Windows x64, Node **24.x** (tested 24.15.0), npm (tested 11.12.1),
Rust/MSVC **1.95.0**, Visual Studio 2022 C++ tools/Windows SDK, and WebView2.
CPython **3.11** with the root `requirements-baseline.txt` is the development
runtime. The project's established environment supplies dependencies only;
imports always come from the selected checkout. Other operating systems are
unverified; runtime preparation and packaging are Windows-specific in W0.

From `workbench/` in PowerShell:

```powershell
npm.cmd ci
$env:RESONANCE_PYTHON = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
npm.cmd run dev
```

`RESONANCE_PYTHON` is a trusted **launching-shell** setting, never a frontend
argument. Without it, development uses `worker/runtime/python.exe` if prepared,
then the selected repository's `.venv/Scripts/python.exe`. A missing runtime has
an actionable error. Installed/portable release builds use their bundled runtime
unless this explicit environment override is set.

```powershell
# Prepare a redistributable CPython 3.11.0 runtime and exact, hash-pinned wheels.
# First preparation downloads the official Python archive and wheels.
.\scripts\prepare-runtime.ps1 -Python $env:RESONANCE_PYTHON
npm.cmd run build                    # executable + resources, no installer
npm.cmd run bundle                   # same app plus NSIS installer
```

Outputs: `src-tauri/target/release/resonance-workbench.exe` with `python/` and
`bridge.py`; installer in `src-tauri/target/release/bundle/nsis/`.
The Python archive and wheel hashes are checked during preparation. npm and
Cargo lockfiles pin transitive dependencies. `rust-toolchain.toml` fixes the
compiler. Rebuild downloads require connectivity; **application use is offline**.
The package imports game Python from the chosen source tree and does not freeze
an old copy of game rules. CPython and wheel licenses remain in the runtime.
Native numeric thread pools are capped at one for this small preview; the
initial default OpenBLAS pool reserved substantial memory without helping W0.
Git is optional at runtime: without it, source/catalog hashes remain available
and the Git revision/working-tree status is explicitly unavailable.

## Verification

```powershell
npm.cmd run build:web                # also typechecks; needed for cargo tests
npm.cmd test
cargo test --locked --manifest-path src-tauri/Cargo.toml
cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings
& $env:RESONANCE_PYTHON -B worker/test_bridge.py
& $env:RESONANCE_PYTHON -B scripts/render-reference.py
npm.cmd run test:desktop             # built RELEASE executable; real WebView2
```

`scripts/desktop-test.mjs` opens a test-owned native window and sends app-local
DOM events through WebView2 CDP. It tests with the WebView network offline,
captures screenshots and measures startup, panning frames and process memory.
No owner's desktop input is driven. The test-only CDP port is 9333; normal
launches expose no debug server. Results/profile files stay in `.artifacts/`.

To test the development window, keep `npm run dev` running, set
`WORKBENCH_TEST_MODE=development` and `WORKBENCH_EXE` to the absolute
`src-tauri/target/debug/resonance-workbench.exe` path, then run `test:desktop`.
For the release fault controls, compile the deliberately broken test helper:

```powershell
rustc scripts/fault-worker.rs -o .artifacts/fault-worker.exe
$env:WORKBENCH_TEST_MODE = 'protocol-mismatch' # also malformed-worker, worker-exit, slow-worker, missing-worker
npm.cmd run test:desktop
Remove-Item Env:WORKBENCH_TEST_MODE
```

The helper is excluded from every package; it provides only negative evidence.
`missing-dependency` additionally takes `WORKBENCH_EMPTY_PYTHON`, a disposable
CPython runtime without the game dependency wheels.

## Contract and limits

The host exposes five narrow local commands: choose/open/close project, one
worker request and cancel. There are no frontend filesystem or shell plugin
permissions. A request is one versioned JSON line (`protocol: 1`, string `id`,
`op`), with one response and process exit. Operations: `identify`, `describe`,
`inspect` (optional fixed invalid fixture), `preview` (asset and seed). No raw
code, arbitrary files or executable arguments are accepted. Output is bounded;
errors include a code/message/remedy; game logs use stderr. Generation times out
after 90 seconds and can be cancelled earlier. Project replacement/window close
reap the child and remove its parent-owned temporary directory.

The worker checks `g2-2`, Python/dependency compatibility, root/link containment
and the exact `roguelike/data/layouts/*.json` route. It imports authoritative
game implementations. A write audit guard permits only temporary outputs and
rejects personal-save reads; bytecode writes are suppressed. **Open trusted game
checkouts:** Python audit hooks are protection from incidental writes, not an OS
sandbox for deliberately hostile repository code or native libraries.

The semantic Pixi rendering shows actual terrain, initial objects and arrival;
colors/markers differ from the Pygame renderer. Inspection is revealed, without
player FOV, simulation, balance analysis or a natural-world selection claim.
The seed, exact large scene seed (string), catalog/source hashes and context
identify a repeatable controlled preview; this is not global gameplay replay.
Refresh after external source changes. Editing, saves, broad content discovery,
conflict handling and a generic capability registry remain outside W0.

See [W0 delivery and evidence](docs/W0_DELIVERY.md).
