# Controls and interaction

These bindings follow the current dispatch in `engine/engine.py` and the relevant screens. The game's debug mode runs before most ordinary screen handling, so its function keys retain their debug meanings even when another screen is open.

## Exploring

| Action | Control | Behavior |
|---|---|---|
| Move | Arrow keys; numpad directions | Eight-way movement is available on the numpad. Bumping a creature performs ordinary melee; bumping a closed door opens it. |
| Wait | `Z`, `.`, numpad `5` | Advances time; Space is not in `WAIT_KEYS`. |
| Sprint | Shift+`W` | Activates the configured sprint when its cooldown permits. Activation itself does not spend a turn. |
| Weapon actions | `Q`, `R` | Uses the equipped weapon's matching moveset entry, if present and usable. |
| Interact | `E` | Opens the adjacent interaction cursor. The selected action must satisfy reach and scene rules. |
| Gather, harvest or take | `G` | Attempts harvest, then gather, then pickup. |
| Take floor item | `,` | Uses the normal pickup route. |
| Drink from terrain | `W` without Shift | Tries the supported terrain-drinking route. |
| Look | `X` or `;` | Moves an inspection cursor; look/examine is not a way to bypass physical interaction reach. |
| Ascend / descend | `<` / `>` | Stand on the corresponding stairs. Input is routed through death and modal guards. |
| Overmap | `M` | Available on the surface. In a submap, the game reports that bearings are unavailable. |
| Zoom | `+` or `=`; `-` | Changes zoom in local view. |
| Message history | Page Up / Page Down | Scrolls the recent log. |
| Quit | Escape twice in local play | First prompts, second quits. Closing the window also exits. Neither is an explicit save action. |

Avoid relying on vi keys for general movement. `H` and `L` open screens before movement dispatch; the presence of letters in `MOVE_KEYS` is not a promise that every screen gives them the same meaning. Arrow keys and numpad controls are the dependable instructional convention.

## Screens

| Screen | Open / close | Main interaction |
|---|---|---|
| Inventory | `I`; `I` or Escape closes | Up/down select; Enter/`E` uses or toggles equipment; `D` drops the selected non-header item; Page Up/Down scroll. |
| Health/status | `H` | Review current health and state. |
| Crafting | `C`; `C` or Escape closes | Up/down select; Enter begins/continues the recipe workflow; the details view can expose component choices. |
| Perks | `K` | Review and purchase with the implemented point interface. See the perk chapter for unsupported prerequisites. |
| Lexicon | `L` | Inspect learned words. |
| Text reader | Use/examine a readable object | Left/right changes pages; Up/Down, Page Up/Down and Home/End scroll the current page; Escape/Enter closes. |
| World/processing placement | Opened by the relevant item/recipe | Movement keys aim, Enter confirms, Escape cancels. Materials are consumed after valid confirmation. |

Inventory is weight-based. Items with the same definition ID remain separate instances. Dropping equipment clears its equipment/light references; picking it back up does not automatically equip or light it. Take-all can move the items that fit and leave the rest. There is no general container-deposit UI introduced by the current transfer system.

## What advances time?

Movement, committed attacks, waiting and physical actions advance the simulation according to their route. Movement may accumulate extra terrain cost; sprint and salve can earn skipped enemy phases. Inventory navigation and opening screens are free. Accepted reading/equipment uses may commit a phase without consuming the item. Rejected/no-op inventory uses with no commitment spend no phase. Consumption, action commitment and time are distinct outputs. Opening wight confirmation or pellet targeting is free; final confirmation owns commitment and cancellation is free. Transfer and placement use their specific success guards. [L10](#L10) demonstrates all three decisions with a new primitive.

Player-duration preparations include their application action. Hit-count effects consume on connecting contacts rather than elapsed turns. Actor suppression/disruption and map zones have their own clocks. Read the combat/effect chapter before changing those durations.

## Function keys depend on debug mode

The shipped `roguelike/config.py` sets `DEBUG_MODE = True`.

| Key | Debug mode on | Debug mode off |
|---|---|---|
| F5 | Legacy nearest-submap teleport | Explicit full checkpoint save in local play |
| F9 | State dump to terminal | Load the latest valid published checkpoint in local play |
| F10 | Legacy coordinate teleport prompt using direct region generation | No matching ordinary binding |
| F11 | Retire/delete the current save slot | No matching ordinary binding |

The current debug travel route recommended for inspection is Enter on the debug overmap cursor. F5, F10 and unshifted F8 still use older direct generation helpers; they are not valid acceptance checks for current scene ownership and should be confined to disposable experiments. See [Debug tools](#debug-tools).

## Source basis

[Input and turn dispatch](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/engine.py) · [inventory](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/inventory_screen.py) · [crafting UI](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/rendering/craft_screen.py) · [text reader](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/text_reader.py) · [C ownership contract](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/docs/owner/C_STATE.md).
