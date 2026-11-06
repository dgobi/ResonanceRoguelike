# Working ruins and alternative access (SYS-4)

A Bound Coffer retains its original rolled contents while its lashings remain
secured. A Lashed Timber Screen occupies one ordinary floor cell and blocks
movement, sight and shared light. It is an optional shortcut: required approaches
and the return route must work while it remains intact.

Use **E**, select an adjacent visible host, then Enter. Esc cancels freely.
The ordinary chooser shows these methods for `pale_lashings`:

| Method | Requirement and cost | Result |
| --- | --- | --- |
| Careful cutting | Equipped owned cutting tier 1; three separate actions; sound strength 2 each | Release coffer; or remove screen and place exactly one wood bundle |
| Quick force | One action; sound strength 8 from the player's work tile | Release/remove; no salvage |
| Dissolution | Unused carried coating dose, captured Dissolution strength >=0.4; one action; no work pulse | Spend entire selected dose, release/remove; no salvage |

The tool stays equipped and owned. Continue cutting is the first choice after a
step; no tool chooser repeats. Walking away, waiting, changing scenes or saving
does not advance or erase work. Force or wash can finish partial cutting; that
finishing method determines salvage. Invalid/stale choices spend no time,
progress or resources. Actors and survival advance normally after each accepted
action; audible methods emit once before that phase, after geometry changes.

The dose chooser identifies strength and weapon-contact budget. Six and twelve
contacts are equally eligible at equal strength, but environmental use spends
the whole selected unit. Same-ID doses retain independent captured payloads.
This uses the ordinary `apply_to_weapon` dose capability; raw reagents, Binding,
coated weapons and depleted items are ineligible. Existing bile coating works
without an item-ID exception. See [SYS-3 preparation](MATERIAL_WEAPON_PREPARATIONS.md).

Releasing a coffer enables ordinary browse/take of the same items. Its contents
remain hidden until release, including when empty. Clearing a screen restores
its captured floor; it is never a bump-openable door. Player/creature routes,
FOV, light and sound use the changed tile. Exposure can increase when a barrier
comes down. Failure to construct/place salvage or consume the exact dose rolls
back ownership, geometry and the final step without charging an action.

## Authoring

Workbench's **access** family (`access-profile-1`, route `access_profile`) edits
and creates immediate JSON files in `data/access_profiles`. Open a supported
profile, Begin edit, change controls or Source, Validate draft, review and apply
one file. Reopen verifies saved bytes. Original-source entitlement, identity,
stale review, protected metadata, recovery and independent host path checks
apply. Removing unsupported original fields cannot confer write permission.

Version-one scalar settings are `host_container`, `host_screen`, `allow_careful`,
`cutting_tier` (1–5), `work_steps` (1–12), `allow_force`, `allow_dissolution`,
`dissolution_threshold` (finite, >0 and <=1), and `screen_careful_yield` (empty
or `wood_bundle`). At least one host and method are required; wood requires
careful work and screen compatibility. Name/description are bounded text;
ID/version are protected. Yield validates one unique actual factory output.
There are no arbitrary scripts, effects or autonomous work settings.

Room and building placement support both records:

```json
{"type":"container","x":7,"y":5,"decor_id":"bound_coffer","loot_pools":["bound_coffer_stores"],"access_profile":"pale_lashings"}
{"type":"screen","x":11,"y":6,"access_profile":"pale_lashings"}
```

Choose **Placement kind → container → bound_coffer** or **screen**, select a
saved compatible profile, then place it. Select the record to edit, follow its
profile reference, move or delete it. Undo/redo and resize guards share Source.
Screens use a timber glyph; do not paint `access_screen` as terrain.
Screens require unoccupied `floor`, `grass`, `packed_earth`, `dirt_path`,
`cobblestone` or `gravel`. Doors, stairs, links, furniture, items, jobs, corpses,
actors and arrival overlaps reject. At least two cardinal approaches must
connect around the intact screen. Trials isolate tiles and owners; failures
cannot partly stamp a candidate. Previews check actual intact required access.

Save profile dependencies before the host. Preview establishes initial geometry
and access, not a completed action. **Test room** captures saved dependencies;
**Reset current test** replays that capture; **Test latest saved version**
captures saved edits. Other unsaved drafts stay excluded. `woven_lashings` and
`sys4_access_room` are the packaged reuse example: two careful steps and both
hosts, without ordinary world enrollment.

## Availability and persistence

Fresh grid/roadside commercial membership replaces `workshop_d` with
`workshop_e` in the same two rows, each retaining weight 1 and cap 5. The successor
retains previous supplies and adds an optional coffer and clue.
`barrow_bound_store` is appended at weight 1 after six existing barrow candidates;
the authored chance stays 0.35. Its southern route remains open, with an
independent coffer approach, far-bay fire and ordinary Hollow Revenant. The
optional readable clue grants no permission flag.

Each generated host captures effective profile, unique owner association,
progress and result. Screens also capture underlying ground. Definition edits
affect fresh captures, not existing generated owners. Released/depleted coffers,
removed screens, spent doses and salvage persist through F5/F9, cold loads and
map caches. A durable manifest rejects missing or contradictory modern state
before installation. Historical unconfigured containers remain ordinary; decor
identity alone never retroactively binds one. Visited maps do not regenerate or
restock. Existing pending-placement dependency checks remain in force.

This package adds no general destruction, ordinary-door work, lockpicking,
fluid spreading, extra essences, NPC object work or away-time progress.
