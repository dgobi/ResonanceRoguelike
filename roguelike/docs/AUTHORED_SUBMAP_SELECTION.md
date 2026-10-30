# Assign saved rooms to new worlds

Freshness compares saved raw rooms with their catalogue raw entries, compiled
rooms with loaded compiled definitions, exact source paths and original byte
hashes. Implicit container `decor_id: crate` / `loot_pools: []` defaults stay valid
without rewriting source. A genuine post-load source edit still requires reloading.

The fixed `data/generation/authored_submap_selection.json` profile uses contract
`authored-submap-selection-1`, identity `authored_submap_selection`, integer
version 1. G20 enables the shipped profile for `barrow` at chance `0.35`, with
one weight-1 candidate, `barrow_ward_store_a`. Procedural barrows retain the
remaining share. This room has one ordinary Hollow Revenant, a Faceted Ward,
two openings through a dividing wall, and an ordinary readable clue. The
predeclared three-seed feasibility sample and route-assisted connected journeys
are recorded in `docs/owner/GAMEPLAY_G20.md`; selection does not guarantee nearby
access or supplies in every seed. Previously saved blank/authored assignments
retain their identities. An absent profile disables assignment, as the older
shipped disabled/empty profile did. A corrupt explicit file is an error
for new-world creation, including when its intended policy was inactive.

Save/reopen an ordinary room and its linked contents first. From that room's
**World assignment** button, open the shared profile, **Begin edit**, and optionally
**Add this room**. This stages one candidate row in the existing draft. Choose
**Enabled**, one existing type (`barrow`, `cave`, `vault`), and a finite
**Authored-interior chance** from 0 to 1. Candidate rows select saved ordinary
room IDs and finite positive relative weights. Review the diff, apply the one
file, and byte-check reopen. Save each dependency separately before the profile;
parked drafts never overlay validation or generation. A saved room remains a
valid unreferenced definition if the later profile transaction fails.

Only unique single-object rooms immediately under `data/layouts/` with the
supported direct room contract qualify. The starting laboratory, documentation
template, nested sources, ambiguous IDs and unsupported original source shapes
cannot be enrolled. Publish a template as a new ordinary variant first.
Production catalogue/compiler checks, saved reference identities, item/creature
factories and referenced reader payload checks are shared with the editor.
Furnished `authored-room-2` candidates additionally share decor admission and
staged native final occupancy/access checks; bare containers, system-owned markers
and inactive historical grids acquire no new placement permission.
Unrelated loadable unsupported content and historical warnings remain available.

Field types, identity/version, duplicate candidate IDs (including case aliases),
probability bounds and positive finite weights are always errors when invalid.
Missing/ineligible candidate references and their dependency errors are warnings
while disabled or at zero chance, and errors while enabled with nonzero chance.
An active nonzero policy requires at least one valid candidate. Inactive fields
are retained and diagnosed; they are not silently repaired. Unknown metadata is
non-executable and preserved by ordinary controls.

The chance applies only after normal dungeon occurrence/type/seed/name choices.
Failure of that chance deliberately keeps the instance procedural. Success
chooses among candidates by relative weight. Membership does not guarantee a
particular world's selection. A SHA-256-derived random domain, keyed by contract,
world/chunk/SubMap identity and seed, is independent of all existing generation
streams. Candidate IDs are sorted for selection, so table order and formatting
do not change the sample. The original geography, type distribution, surface
entrance and special laboratory remain unchanged. Only the new matching
instance's `layout_id` is set. Existing/manual assignments are retained.

**Preview saved assignments** explicitly generates one ordinary 128 × 128
`shared-v1` world with the new-game configuration and the entered seed. It reads
saved profile/dependencies only and constructs no underground scenes. The
receipt records seed/configuration, source identities, profile bytes/contract,
matching/authored/procedural counts and up to 100 selected instances. Any table
truncation is stated; generation itself is complete. Room links return to the
originating profile/row. Cancellation, edits, saved dependency changes and project
replacement stale the result; a preview never grants publication authority.
No automatic seed search, keystroke generation or campaign access occurs.

Room preview proves constructed contents and static access. **Test room** uses
its separate captured foyer. Assignment preview proves metadata. These are
distinct from walking to a naturally generated entrance and using its room.
The ordinary type supplies the exterior; selected authored geometry supplies
contents, arrival and return. Authored scenes receive no additional procedural
loot or ambient population.

| Change | Existing campaign behavior |
| --- | --- |
| Profile membership, weights, type, enabled state or chance | Recorded assignments stay unchanged, including unvisited rooms and procedural empty IDs; only later new worlds use the new choices. |
| Same-ID room-definition edit | Current saved definition is used at subsequent first construction, including pending rooms in an existing campaign (the W5G policy). |
| Already generated room | Owned cached/saved scene, population, mutations and entry/return metadata remain authoritative. No regeneration. |
| Preserve old definition meaning | Publish a distinct room variant and change future profile membership. |

Policy resolution occurs only inside `generate_world`, before atomic candidate
publication. `DataLoader` and world restoration do not resolve it. Changing,
removing or corrupting an unused profile does not prevent loading recorded
assignments. A genuinely needed missing layout fails on lazy first construction;
it never substitutes BSP. Missing owned caches retain their existing refusal.
No save/world-plan/generation schema was bumped or historical world relabelled.
Definition IDs, source files, SubMap instances and captured test sessions retain
separate identities. Existing current-definition reads for items/creatures/texts
and W5H immutable test captures keep their established behavior.

Repeatable scoped evidence: `workbench/scripts/run-assignments.mjs`, game tests
`test_authored_assignment.py`, worker `test_assignment.py`, and
`workbench/docs/W5I_DELIVERY.md`. Fixtures own explicit disposable save roots;
they never inspect personal campaigns. Wider selectors, entrance editing,
whole-world launch UI, grouped publication and campaign migration are deferred.
