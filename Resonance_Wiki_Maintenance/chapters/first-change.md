# Make a small, verifiable change

Start by changing one existing weapon. This exercise demonstrates the workflow you will reuse for larger edits, without requiring a new sprite, new handler or new registration route.

## Goal: increase Severance Blade's flat damage

1. Close the running game. Definitions are loaded at startup; this is not a general hot-reload editor.
2. In the production checkout, inspect `git status --short` and the existing diff for `roguelike/data/items/weapons/severance_blade.json`.
3. Open that file in a text editor. Keep its ID, tile, slot, use handler and movesets intact.
4. Change the existing `damage_bonus` from `1` to `2`. Keep `damage_dice` as `"1d6"`.

```json
"damage_dice": "1d6",
"damage_bonus": 2
```

This is a fragment to replace within the existing object, not a standalone JSON document. Do not add a second `damage_bonus` key. The dice parser expects plain `NdM`; do not write `"1d6+2"`.

## Check the edit

From the repository root:

```powershell
& $ResonancePython -m json.tool roguelike/data/items/weapons/severance_blade.json
git diff -- roguelike/data/items/weapons/severance_blade.json
```

The first command checks JSON syntax. The second should show precisely the intended numeric change. Neither proves damage behavior. For a behavior check after a substantive combat change, use the focused regression command in [Verification](#verification).

## Observe a new item

Launch a new disposable session with `tools/play_disposable.py` as explained in [Setup](#getting-started). The shipped debug mode exposes a backtick console. Enter:

```text
spawn_item severance_blade
```

The item is placed at your position through the debug item route. Close the console, pick it up with comma or `G`, open inventory with `I`, select it and use Enter or `E` to equip it. In an ordinary one-contact comparison with otherwise equal state, the flat weapon contribution is one point larger. Armour, essence, dodge, criticals, corruption, active effects and the dice roll can all change the final damage, so one random hit is not a reliable numerical test.

The factory makes an instance; the weapon's combat definition is consulted during attacks. Other item properties can be restored from a save's instance fields. Use fresh instances when comparing defaults. [Save behavior](#saves-and-state) explains why restarting alone does not refresh every saved property.

## Keep or reverse it

If you want the balance change, commit only the intended file after reviewing it. If this was practice, change `damage_bonus` back to `1` and inspect the diff. Do not use a blanket reset when unrelated changes exist.

## The authoring checklist for any system

| Question | Why it matters |
|---|---|
| Which loader reads this file? | A file in an unscanned folder can be perfectly valid and never load. |
| Which field does the consumer actually read? | Extra JSON fields often survive without implementing behavior. |
| What references this ID? | Registration, loot, zones, profiles and text bindings are separate concerns. |
| When is it chosen or instantiated? | Existing worlds and instances may already own their content. |
| How can I observe it deliberately? | Random selection can hide a working definition. |
| What check establishes the property I care about? | Parsing, construction, placement, access and appearance answer different questions. |

For a new item, follow the content chapter. For a new building, complete both the layout/access contract and a current placement profile; copying a file alone does not establish placement eligibility.

## Source basis

[Shipped Severance Blade](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/data/items/weapons/severance_blade.json) · [combat](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/combat.py) · [item factory](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/item_factory.py) · [debug commands](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/debug.py).
