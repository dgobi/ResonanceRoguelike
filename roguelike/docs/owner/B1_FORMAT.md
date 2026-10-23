# B1 development save format — 22 October 2026

The sole supported format is integer `save_version: 2` in `meta.json`. This is a
development format, with no personal-save migration. Versions 1, 3, 999, absent,
null, boolean, string and fractional versions fail explicitly. Files are neither
migrated nor deleted on rejection. Pickle remains an internal trusted-save
mechanism; this work is not a serializer replacement or arbitrary-corruption
recovery project.

## Scene address and persisted state

`player.json` retains `world_x`, `world_y`, and `current_submap_id` (explicitly null
for the surface). `SceneAddress` validates them together against the saved world's
chunk and submap membership. Surface records remain `chunks/<wx>_<wy>.pkl`;
underground records remain `chunks/<submap_id>.pkl`. Full save routes the active
scene to its matching store. Saving laboratory flagstone cannot overwrite the
paired surface's grass.

Full load validates the version, player references, complete scene address, active
record, and active/pursuer creature identities before applying B1 fields. It uses
a new `ChunkCache` to read disk. It never flushes the unsaved old `hot` or
`submap_hot` objects. It reconstructs the active actors, replaces both pursuer
collections, and clears `_pending_transfer`. Thus a later in-memory map, nested
container, floor item or actor mutation cannot win over the persisted record.
Missing or invalid active records fail; there is no active-scene regeneration
fallback in full load. Ordinary exploration can still generate unvisited scenes.

`main.main` distinguishes a new game before generation. Only no saved files, or
exactly one `world.json` with exactly `{"seed": <non-boolean integer>}`, means new
game. Zero is a valid seed. Other payloads, partial full saves and generic session
markers cannot authorize fresh-game substitution. Rejected startup exits with
code 1 before `Engine.run` or lab descent. A failed F9 does not reconfigure the
existing player's Needs. Successful F9 retains its existing reconfiguration step.

## Inventory, equipment and light

Inventory is required as `{"capacity": 13.5, "items": []}` or a populated items
array. Capacity must be finite and positive. Missing/null/malformed inventory,
unknown item definitions and invalid rows are errors. An empty bag remains empty.
Restoration appends every validated row, even if changed item definitions would
make that saved bag overweight; it is replacement, not a new pickup transaction.

Equipment is a required object. `{}`, missing known slot entries, and explicit
null slots all mean empty. Unknown slots fail. A populated slot has one authority:

```json
"equipment": {
  "offhand": {"inventory_index": 1, "item_id": "tallow_torch"},
  "weapon": null
}
```

The index identifies the exact saved inventory row. `item_id` must agree with that
row and never selects a fallback. Index 0 is valid; booleans, negative, fractional,
string, missing and out-of-range indices fail. Unknown earlier rows cannot be
filtered away and shift later references. Runtime object identity builds the
writer's row mapping; Python `id()` values are not written. No global UUIDs or
second authoritative equipment map were introduced.

Replacement order: validate; clear the old objects' equipped flags; reconstruct
the complete inventory; replace the light component (including explicit null);
replace every equipment slot; link exact rows and set their flags; reconnect the
offhand light; recompute armor. Existing multi-slot relationships are retained by
the slot map. A removed jacket contributes no armor. An unequipped saved torch
stops lighting. The second of two unequal-fuel torches remains the equipped second
torch, and only it burns on the next turn, including its final fuel turn.

`light_source: null` clears the component. A saved inactive light remains inactive;
when unequipped it intentionally has no item reference after reconstruction.
An active item light requires a valid equipped offhand light. Radius/color/falloff/
flicker/active remain the existing explicit fields. `_item_ref`, `_item_id`,
`_burn_turns` and `_turns_used` derive from the restored offhand item. No detached
bootstrap torch qualifies. Other item properties, perk light effects and broader
component reconstruction remain B2.

## Creature definition and stone-lurker lifetime

Actor `id` now comes from `_creature_id`, independently of saved presentation
`tile`, `name` and `blocks_movement`. Missing/unknown live creature definitions
raise a diagnostic instead of disappearing. No legacy `rock` inference is made.
The shared serializer covers surface, submap, live-pursuer and pending-arrival
owners. Existing corpse/remains reconstruction is outside this narrow contract.

A stone lurker stores a small `lurker` object:

| Field | Policy |
|---|---|
| `hibernating` | Stored boolean once initialized. Null explicitly means the initial ability tick has not happened; restoration leaves that attribute uninitialized. |
| `ambush_ready` | Stored boolean: a pending free ambush survives, a consumed one stays consumed. Missing runtime attribute derives false when writing. |
| `ai_triggered` | Stored `AmbushAI._triggered` boolean, preserving its one-time trigger. |
| dormant/awake display tile | Derived from initialized hibernation (`rock` / `stone_lurker`), consistent with the existing ability. Uninitialized presentation retains the saved tile. |

Dormant reconstruction is inspected before any ability tick, then after a distant
tick, approach/wake and actual AI processing. Awake reconstruction stays awake
when the player is distant. Pending ambush is consumed once; a consumed ambush
does not replay. AI target memory, all pursuit timelines, general timers and RNG
progress are not promised by B1.

## Limits

Travel already writes scene files. Full save does not flush every inactive dirty
hot entry. Consequently, full load reads correctly addressed persisted records;
it does not roll an entire campaign back to an immutable checkpoint after later
travel. Atomic multi-file generations, interrupted writes, rollback after arbitrary
component failures, slot/deletion policy and recovery belong to B3. Needs, hooks,
timers, remaining item fields and derived-system fidelity belong to B2. See
[the individually reproduced deferred defects](B1_DEFERRED.md).
