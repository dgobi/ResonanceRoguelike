# B2 observations — 23 October 2026

The pre-B2 game source is the exact accepted `9bb0db8` tree, captured clean before
edits. The new component probes reproduce missing Needs setup/hooks/timers, lost
item/actor fields and offscreen processing failure on those bytes. Before evidence
is under `evidence/b2-before`; the final current record is
[b2-results.json](../../../evidence/b2-results.json).

Fresh and same-process tests verify immediate reconstruction and subsequent actual
turn consumers. Real original Engine.run journeys cover salve use, F5/F9,
independent bootstrap readers, expiry, critical Needs damage, rain collection,
Hardened Step movement and processing completion. Selected offscreen captures were
inspected by Codex. The full B1 journeys/32 original diagnostic properties remain
regressions. The [field ledger](B2_STATE.md) and [remaining defects](B2_DEFERRED.md)
limit the claims; assertion totals count harness/source checks too.

<details>
<summary>Accepted B1 checkpoint and earlier history — retained, superseded where stated above</summary>

# B1 observations and autonomous evidence — 22 October 2026

Use [B1_VERIFICATION.md](B1_VERIFICATION.md) for the exact enforced command and
[b1-results.json](../../../evidence/b1-results.json) for computed final outcomes.
The Arc A desktop-input interruption below is dated history, superseded by
original Engine.run tests using the game's own event queue. There is no mandatory
owner test task.

The unchanged baseline reproduced ten completed diagnostic workers, 32 assertions,
17 pass / 15 fail, and expected exit 1 with `--assert-properties`. Independent
component probes reproduced the hot-map alias, dropped dormant lurker, reset awake
lurker, null empty inventory, ghost torch and wrong duplicate relinking. Those
are failing-before observations, not successful persistence behavior.

B1 checks cover separate surface/lab contents at multiple addresses, empty actor
and item stores, repeated travel, saved HP/position, floor fuel/liquid, container
contents, explored state, explicit empty belongings, duplicate row zero/one and
reordering, inactive/absent light and burnout, immediate dormant/awake/pending
lurker state, actual ability/AI ticks, all serialization owners, version/reference/
scene rejection and strict new-game distinction. Writer checkpoints are immutable
and fresh readers have distinct PIDs. The default command also tests its own
failure handling and requires all matrix cases and parameter workers.

The actual event loop completes movement, waiting, inventory selection/equip,
pickup/drop, ordinary unarmed combat, existing lab label reading, dry-bitter-herb
processing (one ingredient, one placed output, 20 turns), stairs, ordinary surface
boundary crossing, debug-binding characterization and nondebug save/load with a
fresh bootstrap. Shifted stair Unicode and real app-local modifier state are
supplied; key releases prevent repeats. No desktop input or other-app capture is
used. Fixture placement/acquisition is explicitly logged.

Visual inspection: the lab and surface render with visible terrain and the expected
panels. Inventory displays the torch in offhand and the current carried objects.
The processing capture shows the lit fixture campfire and completion message;
semantic checks locate the exact dried-herb output. The bound sarcophagus label
opens with the correct title/redaction, but its last visible body word is `If`;
the rest of its one-page text is omitted. Baseline/candidate rendered-span traces
and captures agree. Equipped drop also leaves a stale slot on both sources.
These and six B2/B3 controls are individually accounted for in
[B1_DEFERRED.md](B1_DEFERRED.md), without broad repairs or blanket expected failures.

No asset or font substitution was required. The observations are for this Windows
runtime and 1280x720 default sprite render; they are not a cross-platform pixel or
physical-keyboard guarantee. Optional owner exercises are educational only.

<details>
<summary>Archived Arc A text — 20 October 2026; superseded operational requirements and failure status</summary>

# Bounded observation log and diagnostic recipe

Date: October 20, 2026, America/Edmonton. Source: reviewed dirty snapshot, with gameplay code/data unchanged. Environment and launch are in [START_HERE](START_HERE.md). Evidence is limited to the rows below; no claim of a complete playthrough, save fidelity, balance or broad UI compatibility.

## Live window run

Command from development root: `.\.venv\Scripts\python.exe -u tools/baseline.py --session opening --observe`. Actual game CWD: `.baseline/opening/roguelike`. Seed 20261020, initial scene `sub_0_64_0`, world `(0,64)`, local `(15,20)`, turn 480, 1280×720 client, default sprite mode.

`--observe` wraps bootstrap/key dispatch and snapshots actual state; it does not replace gameplay handlers. Windows arrows reached Pygame, but multiple automated letter/Return/Escape attempts produced no matching dispatch records. Additional user keyboard input occurred during the early run and is retained in the trace. The owner was asked to leave the window idle, then to perform a manual Esc/Z/I check. The owner replied **Done**. The trace confirms manual Z and I events. Physical Escape triggered the computer-use emergency stop. The process was later absent; no traceback was present, but its exit cause was not independently recorded. The owner subsequently authorized renewed PC control; a window-list request still returned the same emergency-stop error. No further app input was issued, and no additional window checks are claimed. This remaining limit is the tool's stop state, not missing owner permission.

| Requested scenario | Expected | Actual / evidence class |
|---|---|---|
| Laboratory start | New lab and lit torch | **Observed in window.** `(15,20)`, HP60, Unmarked, torch offhand, turn480; [lab image](../../../evidence/screens/01-laboratory.png). |
| Ordinary move | Up moves one tile and costs one turn | **Observed in window and trace.** `(15,20)->(15,19)`, 480->481. |
| Wait | Z advances time without moving | **Manual input + trace confirmed.** Later Z events advanced 481->482->483 and 483->484; inventory/cursor input is separated in JSONL. Last position `(15,19)`. |
| Inventory screen | List starters / equipment and details | **Manual I + captured game surface inspected.** Six items, 5.6/20.0 kg, torch offhand. [Inventory image](../../../evidence/screens/03-inventory.png). No full row/scroll/resize certification. |
| One normal combat | Bump a hostile, observe damage/turn | **Blocked / not completed in window.** No lab creature present; native input delivery and subsequent stop prevented controlled continuation. No combat success claimed. |
| Pickup / drop / equip | Move item among stores, equip owned instance | **Blocked / not completed in window.** Inventory opened but those actions were not verified. Persistence fixtures separately test ownership. |
| Readable text | Read bound lab document through input | **Attempted input blocked.** Interaction cursor and inscription selected; Return/numpad Enter injection produced no corresponding dispatch. Later component render is not normal-input coverage. |
| Craft/processing | Make one currently supported output | **Not completed in window after input stop.** Starter materials insufficient for campfire; offscreen representative screen inspected, no completion claim. |
| Ascent / descent | Correct surface/lab and FOV in both directions | **Window check incomplete.** Actual traversal methods run in diagnostics below, including deliberately corrupted save scenario; these are not the manual test. |
| Surface chunk transition | Adjacent surface chunk loads and player mirrors edge | **Window check incomplete.** Source path identified, no live transition result asserted. |
| Explicit full save | Preserve active player/world/scenes | **No explicit normal-input binding in DEBUG_MODE=True.** F5 teleport/F9 dump are not used as save/load. A later live diagnostic save request was not consumed because the process had ended; no live full-save claim. Actual full saves were performed by persistence workers. |
| Fresh-process reload | Load and compare identities/content | **Diagnostic only.** Separate Python process uses ordinary `main.main` bootstrap load before the worker takes over. Results below fail several properties. No GUI reload observation. |

[opening-observations.jsonl](../../../evidence/opening-observations.jsonl) holds before/after states, handlers, keys and fixture/capture commands. It records game input, not proof of which person injected every event. Game screenshots were captured from the Pygame surface; desktop/other-app screenshots are not packaged. Startup stdout/stderr are generated task logs, not the owner's prior `game_out.txt`.

## Screen inspection beyond the live run

`tools/render_baseline_screens.py` uses real bootstrap, fonts, sprites and screen classes with SDL dummy video at 1280×720. These are **offscreen component renders**, not game-window observations or action tests. [Source hashes and dimensions](../../../evidence/screen-render-record.json) bind the procedure.

* [Craft](../../../evidence/screens/craft-component.png): title, recipe list and requirements visible. Field Campfire shows fuel requirement 2 / have 1, while the footer still advertises Enter craft. Completion not inferred from that prompt.
* [Text](../../../evidence/screens/text-component.png): Sarcophagus Exterior title, condition and redaction render. The displayed body ends at “If”, omitting the remainder of the source page. This is an observed **component-render clipping** defect at this size, not only a hypothetical later-page concern.
* [Look](../../../evidence/screens/look-component.png): cursor and stone-tile examine panel render with navigation hints. Placement over the map is visible; physical interaction reach/time is not tested by rendering it.

Other page lengths, modes, fonts, glyph inventory and window sizes remain unverified. UI fixes are deferred.

## Persistence diagnostics

From project root:

```powershell
.\.venv\Scripts\python.exe tools/persistence_diagnostics.py --prefix owner-persistence-1
```

Use a new prefix each time. The script creates five marked session copies, runs a write phase and **a separate read process** for each, and leaves synthetic saves locally. It imports real dependencies and boots `main.main`; only `Engine.run` is replaced to perform bounded method calls without a GUI loop. No AST extraction or dependency stand-ins are used.

Exit 0 means the harness completed, **not** that all game properties pass. `--assert-properties` returns exit 1 for a failed property and is intended as a future repair gate. Consult each JSON `harness_completed`, `exit_code`, `expected`, `observed` and `property_passed`. Primary executed result: [arc-a2-results.json](../../../evidence/arc-a2-results.json), ten completed worker processes.

| Fixture | Expected property | Observed property |
|---|---|---|
| Independent surface/underground markers and actors; save underground, load, ascend, redescent | Surface grass+hollow_revenant; lab flagstone+grave_thing; correct IDs | Underground load/redescent identity and contents pass; both in-session and fresh-process ascent report surface ID None with **underground** flagstone+grave_thing. **Fail**. |
| Empty inventory and all empty equipment slots | Replace prior/starter state with empty | In-session leather_jack survives; fresh process restores all six starters. Slots retain prior torso or bootstrap offhand. **Fail**. |
| One saved jerky, all slots empty | Jerky only, no equipment, every equipped reference owned | Inventory replacement passes, but torso/offhand stale references survive outside it. **Fail**. |
| Two saved items equipped | Reconstructed owned blade/torch, no unrelated equipped prior instance | Fresh-process ownership and blade relink pass. In-session stale torso survives outside restored inventory. **Partial/fail**. |
| Actual stone-lurker hibernation, serialize/reconstruct in each process | Stable stone_lurker definition identity despite rock presentation | Serialized ID `rock`; factory warns unknown creature; restored list empty. **Fail**. |

The surface actor marker uses a different creature definition from the lab actor, so this checks contents as well as terrain. It does not prove arbitrary mutable actor state, all effects, RNG replay, duplicate item identity or save failure recovery. The tests use slot 0 only inside fresh marked copies.

Harness correction: the first local run (`arc-a`, retained outside the small return package) passed a SubMap object to the string-ID descent API, so its redescent assertion was too weak. The corrected harness passes `sub.submap_id` and asserts the resulting identity as well as contents. The full ten-process suite was rerun as `arc-a2`; use only that result as the final evidence. This was a harness correction, not a game fix.

Reviewed helpers were read as evidence (not executed at their original absolute paths): `core-focused-probes.py` and the audit helper README/procedures. The new harness expands their surface-marker idea to full bootstrap, separate processes, actual ascent/descent, independent entities and computed assertions. Their fixed review paths/synthetic slot901 were replaced by `tools/baseline.prepare` and per-case copies. No imported helper's historical output is presented as newly executed.

## Reproducing the remaining manual scenarios

Use a new `--observe` session. These steps are a **pending checklist**, not recorded passes. Keep seed/scene/turn before and after each action and note whether debug setup was required.

1. In the opening chamber, use arrows and Z; I/select crude blade/Enter equips. D drops an unequipped jerky, I closes, G picks it up. Check inventory/equipment ownership, not just icons.
2. At initial `(15,20)`, move up three to `(15,17)`, G takes the sarcophagus label; I/select note/Enter reads. Inspect the whole text; known clipping may truncate it.
3. For bounded combat without a long search, the existing backtick debug console can `spawn_creature hollow_revenant` near the player. Record this as debug fixture acquisition, then use an ordinary directional bump attack and observe HP/turns. Do not use an overpowered debug blade as normal combat evidence.
4. For a currently available craft, acquire two `wood_bundle` items through gathering or explicitly recorded debug fixture setup; starter crude_blade provides cutting. C/select Field Campfire/Enter enters placement; confirm a valid neighboring tile. Record ingredient changes, result and actual turn delta. Do not use the offhand torch as proof that burning ambient detection works.
5. Return to initial lab stairs `(15,20)` and press `<`; record surface scene and visibility. Immediately `>` should descend via the linked stair. Cross a surface boundary on an ordinary move, record old/new world coordinate and local position. Do not use F5 teleport as boundary coverage.
6. In captured debug mode, use an explicit **diagnostic** save entry, then close and launch a fresh process with `--resume`. Compare more than player position. To test non-debug F5 separately, change DEBUG_MODE only in a dedicated session copy, record that configuration and use F5/F9; this is a separate input configuration.

Observation harness command example (while that particular marked session is running): write `{"action":"save"}` to its `.baseline/<name>/diagnostic-command.json`. The next event-poll wrapper invokes `SaveManager.save`; JSONL labels it diagnostic_before/after. Other bounded commands (capture, position, give, hunger, spawn) are explicit fixture operations in `tools/baseline.py`, never counted as player actions. Do not leave an old command for `--resume`: commands are read at first poll as well. Remove only that created command file before resuming, or use a session that has none.

Normal-input checks need manual keyboard delivery or a separately repaired input-tool path. No change to game controls was made to hide this limitation.

</details>

</details>
