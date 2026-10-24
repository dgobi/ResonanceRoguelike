# Save, load and world changes

There are three separate kinds of saved work: your source files and Git history, the running game's mutable scene cache, and a published full game checkpoint. One does not replace the others.

## Make an explicit checkpoint

For normal keyboard save/load, set `DEBUG_MODE = False` in `roguelike/config.py`, restart, and use F5 while in local play. A successful save reports **Progress preserved.** F9 loads the latest valid published checkpoint.

With the shipped debug configuration, F5 teleports and F9 prints diagnostics. There is no `save` entry in the current debug console registry. Do not type a guessed command or treat a debug dump as a checkpoint. The automated test harness can call the SaveManager API directly; that is a separate route from owner keyboard controls.

**Current travel does not replace the explicit checkpoint.** Crossing a surface boundary and using stairs write working scene state, but the critical-fix pass removed the earlier full-save-on-boundary behavior. Closing the window or confirming quit also does not publish a full save. This corrects the retained B3 document's older surface-autosave wording.

## Where the state lives

| Location inside a save slot | Purpose |
|---|---|
| `HEAD.json` / `BACKUP.json` | References used to find published checkpoint generations. |
| `generations/g-…/` | Immutable checkpoint payloads: world, player, metadata, scenes and manifest. |
| `.sessions/<id>/chunks/` | Mutable session cache written by scene travel and eviction. |
| `world.json` containing only `{"seed": …}` | Explicit fresh-world initialization accepted by the disposable launcher before a first checkpoint. |

An ordinary launch uses `roguelike/saves/slot_0/`. The current disposable launcher redirects the root to `.baseline/g3-play-<session>/`, still with a `slot_0/` underneath. The old `baseline.py` launcher uses a different copied-game tree. Keep their paths distinct.

The payload save version is **2**; the outer checkpoint container version is **1**. World plan versions and scene generation revisions (`wg3` through `wg6`) are separate compatibility contracts. A matching save version alone does not prove that a new generator can reinterpret an older plan.

## What a full save captures

The snapshot combines the cold published base, session cache, hot cached scenes and active scene, with the more recent owner taking precedence. It includes inventory instances and exact equipment references, player/actor component state, world metadata, map layers and effect/processing state supported by the serializers.

The whole generation is written and verified before its reference is published. Loading checks payload hashes and reconstructs state before replacing the live world. A damaged current checkpoint can fall back to a previous complete published one. An invalid load leaves live state intact and reports an error.

Recovery is limited to referenced published generations. It is not an arbitrary search through every old directory. There is no owner-facing rollback hotkey; `SaveManager.load(engine, previous=True)` is an API for tools/code. Retained generations and abandoned session directories are not automatically pruned.

## What editing data changes

| Edit | What to expect |
|---|---|
| Weapon attack fields / movesets | Attacks consult the current weapon definition after restart. |
| Creature HP, armour or perception defaults | Existing saved actors restore recorded fields; create a new actor to test defaults. |
| Item nutrition, weight, keywords, handler or description | Existing saved instances can restore old fields. New instances use changed defaults. |
| Already-applied duration or coating count | The current effect retains its remaining saved state; new uses apply new settings. |
| Text prose | Reading looks up the text by its saved `text_id`; prose changes can appear after restart. |
| Processing time | Existing jobs keep their remaining time; new jobs use the edited recipe. |
| Building selection policy / site frequency / road layout | Applies to new plans. A saved shared plan remains authoritative. |
| Structure geometry or access contract | Can invalidate dependencies needed to generate an unseen saved-plan scene. Use a new disposable world for authoring; do not regenerate published scenes to force a change through. |
| Sprite mapping and many display settings | Read on startup. A runtime F12 remap is temporary unless you separately save the JSON edit. |

Keep IDs stable unless you intentionally update every reference and address compatibility. Saved actor IDs, item IDs, text IDs and structure references are not merely filenames.

## Preserve a campaign before changing compatibility-sensitive content

Close the game and copy the **entire slot directory** to a dated backup outside the active save tree. Copying only `player.json` from a generation cannot preserve the coherent world/scene snapshot. Keep the corresponding repository revision or checkpoint tag so the data and code can be recovered together.

Do not edit chunk pickle files as content authoring, and do not load untrusted downloaded saves. Scene files use Python pickle. Existing flat B1/B2 v2 slots have a read-only compatibility path; saving them is refused rather than silently migrating them. Older, incomplete or unsupported saves can be rejected. Personal-save migration is a separately scoped feature.

Death and debug F11 use slot retirement, limited to the current slot. The old claim that F11 deletes the entire saves root is superseded. It is still a destructive operation for the current campaign.

## Understand away-time

Active/hot map processing and disruption zones can age while those maps remain resident. Cold maps freeze. Inactive actor records do not become a fully simulated surrounding world. Explicit pursuers have their own live/pending ownership. The reality-bubble metadata does not establish complete neighboring simulation, elapsed-time catch-up or replay of all random gameplay outcomes.

## Source basis

[SaveManager and scene cache](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/save_manager.py) · [checkpoint store](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/checkpoints.py) · [component serialization](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/save_components.py) · [critical-fix record](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/docs/owner/CRITICAL_FIXES_VERIFICATION.md) · [current engine travel](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/engine.py).
