# Start here — production main, B3

G16 preparation: use `E` beside a newly selected workshop's crate and Enter to
search/take its one musk gland and one wood bundle (search again for the other).
Read its preparation note by taking it, selecting it in `I` and pressing Enter.
With the starter crude blade equipped, target the emptied crate in `E`, press
`X` and confirm Enter; take the second wood from the floor. In `C`, choose Field
Campfire and confirm a clear adjacent placement, then `E` the unlit fire to
ignite it with a burning offhand torch. In `C`, choose musk pellet and confirm a
clear drying spot near the fire. Placement counts as the first of ten processing
phases. Wait with `Z`, then `E`/pickup the finished pellet. Using it in `I` opens
throw targeting; Esc cancels, legal Enter spends it for brief nearby disruption.
Tables and hanging cloth are scenery. Old workshops receive no new stock.
See [G16 delivery](../../../docs/owner/GAMEPLAY_G16.md).


G15 recovery: use `E` beside a medicine chest in a newly selected apothecary,
select Herbal Dressing and press Enter to take it. Open `I`, select the dose,
and press Enter (or `E` / keypad Enter) to recover up to 12 HP, clamped to current
maximum. Successful use consumes that exact dose and costs one ordinary inventory
action; AI, effects and survival then proceed normally. Full health, a stale dose,
or a missing/dead fighter rejects use without consumption or time. Closing with
`I` or Esc is free. This is one physical 0.1 kg dose per new apothecary, with no
replenishment; old saved apothecaries retain their old contents and selections.
See [G15 delivery](../../../docs/owner/GAMEPLAY_G15.md).

Accepted Arc A, B1 and B2 are integrated on production `main`. B3 adds coherent
checkpoint generations, dirty-cache capture, recovery/rollback and slot-scoped
deletion. Read [B3_STATE](B3_STATE.md), [B3_VERIFICATION](B3_VERIFICATION.md), and
[B3_DEFERRED](B3_DEFERRED.md). Run `tools/verify_b3.py` with the existing environment
against this checkout. All verification is autonomous and headless/app-local.
The older isolated-copy instructions below are historical and superseded.

<details>
<summary>Earlier accepted history — superseded where stated above</summary>

# Start here — B2 development copy (23 October 2026)

Use `G:\GameDev\RoguelikeBaseline-20261020\project`, branch
`codex/b2-reconstruction`. B1 was accepted; B2 repairs component, hook, timer and
item reconstruction. Run `.\.venv\Scripts\python.exe tools/verify_b2.py` from the
project root. This includes the complete B1 regression suite and requires no
manual acceptance work. See [B2_STATE](B2_STATE.md), [B2_VERIFICATION](B2_VERIFICATION.md)
and [B2_DEFERRED](B2_DEFERRED.md). For optional play, use the unchanged disposable
launcher with a new name, e.g. `tools/baseline.py --session owner-b2-first --seed 20261020`.
The existing `.venv` and normal debug bindings remain unchanged.

<details>
<summary>Accepted B1 checkpoint and earlier history — retained, superseded where stated above</summary>

# Start here — B1 development copy

The isolated project is `G:\GameDev\RoguelikeBaseline-20261020\project`, on
`codex/b1-persistence`. The original project remains separate. B1 changes only
persistence ownership/validation and startup rejection handling; it preserves the
world, content, assets, controls and gameplay design.

Run the autonomous acceptance command from this project root:

```powershell
.\.venv\Scripts\python.exe tools/verify_b1.py
```

The existing Python 3.11.0 / Pygame 2.6.1 / tcod 19.3.0 environment is retained.
No new test dependencies are required. See [verification](B1_VERIFICATION.md),
[the v2 format](B1_FORMAT.md), [observations](OBSERVATIONS.md) and
[remaining scoped defects](B1_DEFERRED.md).

For an optional playable disposable world:

```powershell
.\.venv\Scripts\python.exe tools/baseline.py --session owner-b1-first --seed 20261020
```

Choose a new session name. The launcher excludes saves and creates exactly a
seed-only initialization file. Missing player data in a full save is now an error,
not permission to start again. Existing Arc A/v1 development sessions cannot be
resumed with v2; no personal-save migration is part of B1. The default debug
bindings remain F5 teleport and F9 dump. The acceptance driver separately uses
process-local `DEBUG_MODE=False` for real F5/F9 save/load tests.

The default acceptance suite uses dummy SDL, its own Pygame events and offscreen
captures. It needs no PC takeover or owner keyboard work. Physical keyboard,
other display modes and other operating systems are not certified. Windows
resolves the existing assets/Fonts path case; no asset-path or asset changes were
needed in this environment.

An empty bag remains empty. A removed torch stops lighting. The second of two
torches remains the equipped second torch. Surface grass stays separate from
laboratory flagstone. Sleeping lurkers retain their definition; awake lurkers
remain awake. B2/B3 still own broader fidelity and checkpoint/crash guarantees.

<details>
<summary>Archived Arc A text — 20 October 2026; superseded operational requirements and failure status</summary>

# Start here

The current game starts beneath the surface in a laboratory. It contains surface exploration, underground maps, normal combat and weapon moves, weighted inventory and equipment, found texts and a lexicon, survival, gathering, containers, recipes and processing, weather, resonance, corruption and perks. Several of these are partial. This handbook teaches the captured implementation without promoting unfinished behavior to canon.

Read this page, [runtime](RUNTIME_MAP.md), [state](WORLD_AND_STATE.md), [content](CONTENT_ROUTES.md), then [the lesson](OWNER_LESSON.md). Source paths in these pages are relative to the repository root unless explicitly described as game-relative. Source context is the dirty working copy identified in [provenance](../../../evidence/PROVENANCE.md), captured on October 20, 2026, America/Edmonton.

## Install and launch a disposable world

The tested development copy is `G:\GameDev\RoguelikeBaseline-20261020\project`. The original remains at `G:\GameDev\RoguelikeProject`. These are separate directories and repositories.

From PowerShell, in the development copy:

```powershell
Set-Location 'G:\GameDev\RoguelikeBaseline-20261020\project'
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-baseline.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe tools/baseline.py --session owner-first --seed 20261020
```

On this machine the environment is already installed; run only the last command with a new session name. No environment activation or global Python/package changes are needed. For another machine, first obtain the **reviewed working-copy export** and apply the Arc A patch; a plain checkout of original HEAD lacks user work. Substitute your copy's absolute path in `Set-Location`. CPython 3.11 x64 is required for the tested recipe; another interpreter needs its own launch check.

The launcher copies `roguelike/`, excluding saves, caches and the old local log, into `.baseline/<session>/roguelike/`. It creates a marker and a minimal seed-only `saves/slot_0/world.json`. Because no `player.json` exists, the original bootstrap creates a new player and lab. It then changes CWD to that copied game directory and runs its original `main.py`. It refuses to replace an existing session. Use another name for another new world.

For an already prepared session, the exact ordinary launch is:

```powershell
Set-Location 'G:\GameDev\RoguelikeBaseline-20261020\project\.baseline\owner-first\roguelike'
& 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe' main.py
```

Alternatively use `tools/baseline.py --session owner-first --resume` from the project root. Resume means reuse that copied game and its saves; it does not copy later edits from the development source. Existing saves are not a fidelity guarantee.

Expected first screen: a 1280×720 client window titled **Roguelike**, a lit patch of the laboratory around the player, a right message panel and a bottom status bar. For the tested seed: world chunk `(0,64)`, submap `sub_0_64_0`, local `(15,20)`, turn 480 (Day 1, 08:00), HP 60, Unmarked, torch in offhand. A world seed is not a guarantee of identical later combat or local generation; some RNG owners are unseeded and functional variants use process-dependent hashing.

## What actually ran

Windows x64 build 26200; Python reports `Windows-10-10.0.26200-SP0` (this platform string is not a marketing-edition assertion). CPython **3.11.0**, Pygame **2.6.1**, SDL **2.28.4**, tcod **19.3.0**, NumPy **2.4.6**. Transitive runtime pins are in [requirements-baseline.txt](../../../requirements-baseline.txt); actual pip/setuptools and all package versions are in [environment.txt](../../../evidence/environment.txt). `pip check` passed.

Historical Python 3.13.5 notes are retained as history, not the tested interpreter. The tcod constant access emits a FutureWarning; it did not prevent launch. No dependency upgrades, rendering changes or gameplay corrections were made. Utilities needing Pillow are outside this minimal game recipe.

The actual directory is `roguelike/assets/Fonts/`, while `config.py` and `engine/display_config.py` request `assets/fonts/`. Windows resolved the paths in this run. A case-sensitive filesystem remains unsupported by this evidence; reconcile the folder/path spelling before testing there. Do not infer Linux/macOS support from the Windows launch.

## Controls for this snapshot

| Purpose | Current control and cost |
|---|---|
| Move / ordinary melee | Arrows or numpad directions. Bump a creature to attack. A successful ordinary move/attack advances a turn; difficult terrain can add more. |
| Wait | `Z`, `.`, numpad `5`; one turn. Space is not in the current wait-key set. |
| Inventory | `I`; arrows select; Enter/E uses; `D` drops; I/Esc closes. Opening/navigation are free. Using a selected item advances one turn even if its handler fails. |
| Pickup / gather | `G` tries harvest, gather, then pickup; `,` pickup. `E` opens adjacent interaction selection. Old Shift+G instructions are stale. |
| Empty crate | In `E` selection, target a visible adjacent empty crate and press `X`. Confirm with Enter or cancel with Esc. Requires an owned cutting tool equipped in weapon/offhand; one turn removes the crate and leaves one wood bundle on its floor cell. Enter alone still searches. |
| Look | `X` or `;`; arrows inspect; X/Enter details; Esc closes. Physical interactions through look have known reach/time inconsistencies. |
| Craft / status / perks / lexicon | `C`, `H`, `K`, `L`. Thus H/K/L are **not dependable vi movement keys** despite entries in MOVE_KEYS. |
| Stairs | `<` ascend, `>` descend while standing on the corresponding stair. The run loop uses shifted punctuation's Unicode before modal dispatch; these paths currently do not call `_advance_turn`. |
| Overmap / zoom | `M` on surface; `+` / `-`. Only default sprite mode/size was observed here. |
| Sprint / weapon moves | Shift+W; Q/R. Current action-cost/effect limitations are in STATUS.md. |
| Exit | Close window, or Esc twice in local play. Closing does **not** perform a full save. |

`config.DEBUG_MODE=True` is the captured setting. **F5 teleports; F9 dumps state; neither is save/load.** F11 recursively deletes relative `saves/`. Death/restart also delete that relative directory. Do not use these operations around personal saves. With `DEBUG_MODE=False`, local F5 calls full save and F9 calls load, but those bindings were not window-tested in Arc A. Debug controls intercept before normal/modal input. The changed-file package does not switch the debug setting.

## Save, stop and restore safely

All baseline-session saves are `.baseline/<session>/roguelike/saves/slot_0/`: world/player/meta JSON and pickled maps in `chunks/`. Surface transitions call full save; cache writes also occur during travel. Cache files alone are not a full player save. There is no reachable explicit full-save key in the captured debug configuration.

For diagnostic persistence use [the documented harness](OBSERVATIONS.md), which explicitly invokes `SaveManager.save(engine)`. Do not describe that as normal-input save coverage. The launcher observation option also exposes a bounded diagnostic save command; its source and semantics are documented there.

Stop with the window close button after accepting that unsaved progress may be lost. Keep each experimental world in its own named session; restoration means a fresh named copy. Do not merge disposable saves into personal saves. Only load saves you created yourself: the present format uses pickle and an `eval` path and has no robust compatibility or transactional recovery contract.

The startup, movement, manual wait and inventory screen were observed. Full normal-input combat/travel/crafting coverage remains incomplete because native letter/Enter/Escape injection did not reach the game and physical Escape then stopped desktop automation. [OBSERVATIONS.md](OBSERVATIONS.md) records each remaining scenario. Saving underground and explicit empty-state restoration demonstrably fail diagnostic invariants. This is a runnable development baseline, not a certified persistent campaign.

</details>

</details>

</details>
