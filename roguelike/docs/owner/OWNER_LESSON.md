# One owner lesson: change how much Crow Jerky restores

**Learning outcome: awaiting owner validation.** The automated experiment below passed through the real inventory handler without a window. Its manual-window version remains unverified because desktop input automation was stopped. The owner confirmed a wait/inventory input sequence, not completion of this lesson.

## Locate and predict

Open [`roguelike/data/items/consumables/crow_jerky.json`](../../data/items/consumables/crow_jerky.json). Locate `nutrition: 0.35` and `on_use: "eat"`. Navigate to `engine/item_factory.py::ItemFactory.create`, `engine/item_system.py::ItemSystem._use_eat`, `components/needs.py::Needs.eat`, then `engine/inventory_screen.py::InventoryScreen.handle_key`.

**Prediction question:** from hunger 0.500, will reducing nutrition from 0.35 to 0.20 leave the character more or less hungry? What exact values should remain after the action's normal hunger tick?

## The full contract for this example

| Concern | Current behavior |
|---|---|
| Purpose | A starter food restores hunger; it does not heal or equip. |
| Authority / units | `player.needs.hunger`, 0 full through 1 critical. `nutrition <= 1.0` is a fraction; values above 1 are points divided by survival hunger max (1000 here). Do not casually cross this discontinuous unit boundary. |
| Definition / loader | JSON ID `crow_jerky`; DataLoader recursively loads items; ItemFactory copies nutrition/on_use into a new instance. Filename is navigation, ID is lookup identity. |
| Supported fields | `id,name,description,tile,weight,stackable,on_use,nutrition,keywords`; optional `eat_message` is consumed by the eat handler. `_essence_note` is commentary, not a mechanic. This does not promise other arbitrary effect fields work. |
| Prerequisites / acquisition | Valid food_item tile, existing eat handler, player Needs and Inventory. Main gives one instance at new-game startup; no broken lab loot route required. |
| Action cost / lifecycle | Inventory use dispatches handler; successful eat returns True, removes that instance, then advances one turn. Browsing/selecting costs none. The item definition remains reusable. |
| Scene scope | Carried by the player, usable in lab or surface; current surface biome influences the turn's survival rate even underground. For this new seed the lab is backed by forest. |
| Persist/reset/recompute | Hunger explicitly saved. Inventory instances reconstructed from current definitions; nutrition is not in the saved-item whitelist. Old session copies retain old JSON. Loaded Needs configuration is defective; use a **new game** for this lesson. |
| Invariants / rejection | One food consumed, hunger never below zero, one turn through this screen. No food acquisition/transfer overflow is involved in this fixture. |
| Expected result | `max(0, 0.500 - nutrition) + 0.001`: baseline 0.151; edited 0.301. Starting at hunger zero would hide most of the change due to clamping. |
| Limits | Native GUI lesson not completed; other biomes/loaded state differ. UI stage labels alone cannot establish exact values. |

## Reversible manual exercise

Use the separate development repository after its baseline changes are saved. Keep other edits out of this lesson branch.

```powershell
Set-Location 'G:\GameDev\RoguelikeBaseline-20261020\project'
git switch -c codex/owner-jerky-lesson
.\.venv\Scripts\python.exe tools/baseline.py --session jerky-original-owner --seed 20261020
```

In the game press F7, type `0.5,0,0`, and Enter. This sets disposable fixture hunger/thirst/corruption without advancing time. F9 prints a diagnostic state dump to the launching terminal; verify hunger 0.5000 and turn 480. Press I, select Crow Jerky with arrows, press Enter once. Press I to close inventory, F9 to inspect hunger 0.1510 and turn 481. The item should be gone. Close the game window. F9 is a **dump**, not save.

In the development source, change only `nutrition` from `0.35` to `0.20` in `roguelike/data/items/consumables/crow_jerky.json`. Inspect:

```powershell
git diff -- roguelike/data/items/consumables/crow_jerky.json
.\.venv\Scripts\python.exe tools/baseline.py --session jerky-edited-owner --seed 20261020
```

Repeat the same F7 fixture and inventory action in this fresh world. Expect 0.3010 at turn 481 and one consumed jerky. Do not resume the first session: it contains a separate, already copied definition.

Undo only the lesson's file (provided the displayed diff contains only your lesson edit):

```powershell
git restore --source=HEAD -- roguelike/data/items/consumables/crow_jerky.json
git diff --exit-code -- roguelike/data/items/consumables/crow_jerky.json
git switch codex/runnable-baseline
```

The two disposable worlds can remain as evidence; no source deletion or save cleanup is required. This rollback changes only the dedicated lesson edit. If the diff contains other work, preserve it first instead of using this command.

**Verification question:** which object changed (definition, carried instance or Needs), why is the result not exactly 0.150/0.300, and why does editing the JSON in the development tree not alter an already running session?

## What was actually verified by Codex

Run from project root with a fresh name:

```powershell
.\.venv\Scripts\python.exe tools/owner_lesson.py --session jerky-check-2
```

This makes a disposable copy, temporarily edits only its food definition, starts separate Python processes for both variants, uses the real `InventoryScreen.handle_key` path on a real Engine and restores the original definition bytes in `finally`. It does not inject a Windows key or draw a game window.

[owner-lesson-results.json](../../../evidence/owner-lesson-results.json) records 0.15100000000000002 and 0.301, turn_delta 1, item_removed true, both properties passed, exact-byte restoration true and source hashes. This verifies the numeric/code path while keeping the normal-input limitation explicit. Record the owner's prediction, observed values, explanation and feedback separately when they complete the manual exercise.
