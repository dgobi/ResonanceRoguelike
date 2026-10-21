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
