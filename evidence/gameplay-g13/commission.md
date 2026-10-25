# Codex G13 — One useful scavenging stop

**Project:** Resonance Roguelike  
**Prepared:** 25 October 2026, America/Edmonton  
**Repository:** https://github.com/dgobi/ResonanceRoguelike  
**Reviewed `main`:** `3c7b51333aa4f9d1052b52caff2f19abed0f2b79`  
**G12 frozen runtime/test inputs:** `08c1cf9f84b15340563ee969a0a369890d8dd24e`  
**Verified checkpoint:** `checkpoint/gameplay-g12-verified-20261025-a`  
**Companion:** `G12_REVIEW_AND_NEXT_DIRECTION.md` and `Resonance_G13_Review_Package.zip`.

## Outcome

Deliver one small, convincing scavenging stop using the systems G12 made reliable. A player can approach a normally generated stocked tool shed, recognize and search its storage, acquire the existing Leather Satchel and ordinary useful supplies, equip the bag, and leave with the benefit and the depleted location preserved.

The owner reports that G12 took much longer than earlier rounds. **This task is one content variant and its integration.** It does not implement the whole compact region from the gameplay analysis. Use existing runtime mechanisms; keep the work small enough to assess as one place.

## Current basis and working arrangement

Read `AGENTS.md`, this brief, the companion review and relevant current source. The supplied compass/workflow govern intent; the older decisions pack is historical. Inspect any advance beyond the reviewed HEAD without resetting it.

Work in the owner's existing production checkout on `main`, using unique immutable starting/final checkpoints. Preserve unrelated changes, owner interior/decor work and personal campaigns. No task branch, worktree, second development checkout, PR or desktop takeover. Codex owns autonomous headless/app-local verification.

G12's main paths are accepted with a known nonblocking omission: the craft menu can reject a valid explicit torch-as-fuel choice before offering it. The ordinary two-wood campfire works. Record that issue separately; this task neither repairs nor depends on it.

## 1. Author exactly one new version

Create `roguelike/data/buildings/storage/tool_shed_b.json`, retaining `tool_shed_a` and all its existing dependencies unchanged. Use the current small shed as the placement envelope: retain its footprint, entrances, permitted rotations, buffer, approach and road relation. Furnish and stock the new interior using supported fields and existing assets. Preserve access to every container after dressing. Keep `placement.targets` consistent with actual containers: the existing three positions already work; if using two, remove or appropriately replace the unused required container target.

The content ceiling is:

- One small single-floor structure version.
- Two or three real searchable containers with differentiated practical contents.
- One existing `leather_satchel` in one appropriate fixed source per selected occurrence.
- Modest supplies drawn from existing useful items: for example light, provisions, wood or a working implement.
- Up to three new site-local loot pools and, only if useful, one short mundane note.

Use an existing container decor and a singleton pool (`roll_count: [1,1]`, one `leather_satchel` entry) for the bag. Keep incidental extra bags out of the other local pools. Do not modify shared pools or add item, recipe, decor, creature or rendering definitions.

Make the room look used and interrupted through a few existing furnishings and purposeful storage. Each description should match actual objects and interactions. Use `special_tiles`/container fields consumed by the current runtime; inactive metadata or letters mapped to floor are not working furniture. A note is optional, with no new knowledge unlock, quest or mechanical dependency.

The Leather Satchel's existing 10% carrying reduction is the reward. Keep its 0.8 kg physical weight and current behavior. Demonstrate the same acquired inventory's effective load before/after equip; do not retune the bag or inflate supplies to manufacture a dramatic capacity rejection.

Codex is delegated this one version. Preserve the owner's other drafts and authored assets; do not turn the task into a workshop catalogue or a batch of interior replacements.

## 2. Use the existing fresh-world placement cohort

In `roguelike/data/generation/settlement_profiles.json`, replace only the `tool_shed_a` asset reference with `tool_shed_b` in:

- `profiles.grid.roles.support`
- `profiles.roadside.roles.support`

Retain those entries' current weight `1.0` and cap `3`, and retain all other members, minima, schedules, geometry and world-generation settings. Leave compound recipes and their existing `tool_shed_a` references unchanged. No new selector, nearby-start guarantee or world/plan version is required.

The review's in-memory feasibility probe preserved all three selected shed locations/geometry at seed `20261023`, including `(75,99)`, two chunks from start `(73,99)`. That is a useful verification candidate, not already delivered content or an all-seed guarantee. Confirm the actual installed version through ordinary production generation and materialization; an assigned preview alone is insufficient.

## 3. Preserve saved worlds and historical checks

Existing plans must keep their selected `tool_shed_a`, old dependency hashes and visited state. No replacement on load, F9, arrival or revisit. Retain all old definitions; do not regenerate old scenes to add the new room.

Reuse `evidence/gameplay-g12/final-b/journey/lab/lab-checkpoint.zip`, the retained real-event laboratory checkpoint, with its recorded expected state and the review's `replacement_probe.json` fingerprint evidence. Its world includes the old pending support scene at `(75,99)` and saved visited laboratory state. This is distinct from the controlled `authentic-pre-g12-checkpoint.zip` equipment witness. Show that the lab checkpoint's saved plan and pending scene fingerprint remain unchanged with the new content installed, and that its existing visited state restores. No new general migration or fixture framework is needed.

There is known, finite test maintenance because several historical tests compare old results to regeneration using today's defaults. Bind those historical checks to exact recorded historical selection input, preserving their expected artifacts and assertions:

| Existing test | Permitted maintenance |
|---|---|
| `test_generation_g11_access.G11Access.test_three_complete_macro_plans_and_coarse_owners_unchanged` | Use authentic historical selection input for exact historical world comparisons. |
| `test_generation_g9_network`: `test_ordinary_preservation_benefit_and_every_touched_scene` and `test_disabled_zero_budget_and_exhaustion_keep_complete_baseline` | Bind old full-baseline comparisons to their original selection input; retain network/geometry/behavior assertions. |
| `test_generation_g5_cohort.G5Cohort.test_every_transform_and_documented_assigned_context` | Preserve historical certification of `tool_shed_a` using its recorded support assignment/policy; it must not infer that assignment from today's replaced membership. |
| `test_structure_contract`: `test_complete_inventory_and_immutable_defaults` | Account explicitly for one additional ordinary building: 65 total / 56 ordinary at this baseline; recompute from the actual preserved catalogue if `main` advanced, retaining the other contracts. |

Use a source-bound historical profile fixture if needed; retain immutable historical worlds and receipts. Keep current-input validation and an ordinary `tool_shed_b` selection check separate. Do not rewrite golden worlds, drop inconvenient fields, skip tests or filter the new building out of all comparisons.

**Run the small asset/access checks and these affected historical checks early.** If this content change appears to require a new runtime policy-history system, migration adapter, generation rewrite or broader authoring framework, stop that expansion and report the concrete blocker. Do not turn it into an implicit additional milestone.

## 4. Demonstrate the place through normal actions

Use one fresh production-generated occurrence and the existing event/renderer infrastructure. Record seed, chunk, placement ID, content source and actual native contents. Run a short normal-input sequence: approach from its public access, enter, inspect/search, take the bag and at least one useful supply, equip, and exit.

Normal FOV, native AI, survival and action costs remain active. Do not insert the reward after generation, equip it directly, clear native threats, enable invincibility or reset health/supplies during the trace. Full-state route selection is allowed and disclosed.

Keep the trace local and bounded. Initial staging at the actual generated public approach is allowed if needed; disclose it and do not call it a normal-start expedition. A long survival itinerary, hunt, alternate combat solution or seed-search campaign is not required.

Show the real room and its searchable storage in a few useful production-rendered views. Verify that the acquired bag works, the item leaves its original container exactly once, and depleted contents remain depleted after exit/revisit. Use F5, a genuinely separate-process cold load and F9 to cover the acquired/equipped reward and the changed site with the existing save mechanisms. Distinguish the expected snapshot restored by F9 from later unsaved mutations.

## 5. Verify, deliver and stop

After targeted validation, freeze the final runtime/data/test inputs and run the established **unfiltered focused suite and unfiltered production D gate**, plus the one bounded G13 content journey. Reuse the existing runner, ownership, persistence, G12 equipment and structure/access checks. No new general harness, broad balance study or extra repeated gate campaign. Rerun affected checks and required final gates if their tested inputs change.

Use the established production interpreter for release verification. Preserve the existing historical float-equality qualification from Linux review; do not expand this task into cross-platform determinism work. Record exact commands, environment, counts, source identities, controls and material failures honestly.

Deliver the new content/registration, narrowly necessary test fixtures, a concise `docs/owner/GAMEPLAY_G13.md`, one compact source-bound evidence package, and only the affected authoritative authoring guidance needed to explain this versioned example. Correct no unrelated docs as a release prerequisite.

When the owner supplies this brief for implementation, scoped delivery includes committing and publishing to the existing remote `main`, unique immutable checkpoints and exact remote branch/tag readback, subject to more specific instructions in that session. Preserve unrelated work, do not force-push or move existing tags, and do not ask again for authorization already carried by the invoked brief.

**Stop when this one useful place is installed, normally selected, reachable, visibly coherent, searchable, useful and persistent, and the required evidence agrees with delivered source.**

No second destination, bespoke guardian, underground population, preparation chain, starting-kit redistribution, generic salvage/disassembly, new property system, inventory/crafting/reader rewrite, XP/perk/corruption change, wiki maintenance, reference-pack refresh or PDF belongs in G13. The following review chooses the next connection from the resulting game.
