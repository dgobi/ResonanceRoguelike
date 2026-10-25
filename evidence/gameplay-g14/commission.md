# Codex G14 — Crate wood for a field campfire

**Project:** Resonance Roguelike  
**Prepared:** 25 October 2026, America/Edmonton  
**Repository:** https://github.com/dgobi/ResonanceRoguelike  
**Reviewed main:** 1146b5c0300c0b0ff47689a85bb1fe6f3019de4e  
**G13 frozen inputs:** cd058c9610fe8db4d4ed1034cefdd71eeb8abfe3  
**Verified checkpoint:** checkpoint/gameplay-g13-verified-20261025-a  
**Companion:** G13_REVIEW_AND_NEXT_DIRECTION.md and Resonance_G14_Review_Package.zip.

## Outcome

Make one existing furnishing useful after it has been searched. A player can deliberately dismantle an **empty crate**, using an equipped cutting tool, recover **one existing wood bundle on the floor**, and combine it with the completed G13 shed's existing floor wood to place and light a campfire through the current paid recipe.

This is one interaction with one existing object type, followed by an existing payoff. It connects scavenging to making and leaves a persistent physical change in the place. The owner reported that G12 took much longer than previous rounds. Keep this task concentrated: no new location, item definition, recipe, content catalogue or general dismantling framework.

## Current basis and working arrangement

Read AGENTS.md, this brief, the companion review and the relevant current source. The supplied compass and workflow govern intent; the older decisions pack and G10-era gameplay analysis supply historical context. Inspect advances beyond the reviewed HEAD without resetting them.

The repository already contains completed G13 despite the latest request calling the delivery G12. G13's shed and source-bound evidence are accepted for their bounded scope. Its old content versions and historical selection fixtures remain valid. The known G12 craft-menu omission for an explicit torch-as-fuel choice remains separate; the ordinary two-wood campfire route works.

Use the owner's existing production checkout on main, with unique immutable starting and final checkpoints. Preserve unrelated changes, owner interior/decor work and personal campaigns. No task branch, worktree, second development checkout, PR or desktop takeover. Codex owns autonomous headless/app-local verification.

## 1. Add one explicit action

Support only the existing decor ID **crate**, with a matching live container owner and an actually empty authoritative item list. Require the decor and container record to agree. A decorative crate without a container owner is unsupported. A nonempty crate is refused even if a stale state flag calls it looted. Serialized item rows count as contents.

Offer a clearly labelled dismantle action in the existing adjacent interaction flow, using a control that does not conflict with movement. Keep ordinary Enter/search behavior intact. Taking the last item or searching an empty crate must not destroy it automatically.

Use a compact confirmation that makes the consequence clear: remove this empty crate, leave one wood bundle, require an equipped cutting tool, and spend one ordinary world turn. Cancellation changes nothing.

Require an actually owned, currently equipped weapon or offhand item with cutting tier at least 1, following the existing butchery convention. Retain the tool. No wear or durability system is introduced. In the demonstration, equip the starter crude blade through normal inventory actions if it is not already equipped.

At confirmation, revalidate the live scene, exact source owner, matching decor, empty contents, tool, range, visibility and existing diagonal-corner rules. A prompt opened for a source that has disappeared, changed or been replaced must not authorize a different source at the same coordinates. Rejection and cancellation create no output, remove nothing and do not advance the world.

## 2. Make the physical conversion reliable

On success, create exactly one valid existing wood_bundle, remove the crate decor and its empty container owner, and place that item on the crate's floor cell through the established ownership helpers. Preserve the underlying terrain, actors and unrelated floor objects.

Keep the operation local and all-or-nothing. Output creation or placement failure leaves the original crate and owner intact. Once removed, the source cannot yield again. Do not add a general transaction or salvage framework to implement this small operation.

Do not put the output straight into inventory. A full pack does not prevent dismantling: the wood stays on the floor, and later pickup obeys existing capacity and ownership rules. A rejected pickup must not consume or duplicate it.

Charge one ordinary action through the existing interaction completion/clock path. Demonstrate a one-turn increase in the ordinary debt-free case; preserve existing action-debt handling. No timed work order, interruption system, noise simulation, animation requirement or new fatigue cost.

Keep the shared crate and wood_bundle definitions, existing recipes, G13 layout/pools, selection profiles and generation behavior unchanged. An explicit runtime rule for this one supported decor type is sufficient. Do not infer recoverability from names, arbitrary keywords or prose. The recovered instance may use a short accurate description through the already persisted instance-description field; it need not inherit the shared wood definition's deadfall wording.

## 3. Preserve changed places and existing campaigns

Use the existing mutable-scene persistence route. A visited crate changes only after the player explicitly acts; loading an old scene must not dismantle or reinterpret it. Keep the saved generation plan and dependency identities unchanged.

The review's disposable feasibility probe removed the already-empty bag crate from a genuine G13 checkpoint, left one floor wood item, and successfully saved and restored it in a separate process with the original required-container target still in the plan. That proves the storage path can represent this state. It is not implemented gameplay evidence and does not replace the G14 normal-action demonstration.

Implementation anchors are:

- engine/interaction_cursor.py: reach validation, prompt ownership and action completion.
- engine/engine.py: container interaction, interaction candidates and equipped cutting-tool convention.
- generation/floor_object_utils.py and generation/decor_utils.py: authoritative object owners and physical decor.
- data/recipes/campfire.json: the existing two-fuel, reusable cutting-tool recipe.

Paths above are relative to roguelike/. Add only the small helper needed to keep container removal and floor output consistent. No save schema, migration, generation-contract weakening or historical-fixture rewrite is expected.

## 4. Demonstrate the connection once

Use one normally selected G13 tool_shed_b and the existing event/renderer infrastructure. The reviewed seed 20261023, chunk (75,99), is a known suitable occurrence; the bag crate is local (18,29) in that placement. Record actual source, seed, placement and native contents rather than assuming coordinates if the baseline advanced.

Run one short trace:

1. Approach, search and empty the bag crate through normal actions. Retain the acquired bag and normally equip the required blade.
2. Show the explicit dismantle offer/confirmation, perform the action, and show the missing crate and exactly one floor wood output.
3. Take that wood and the shed's existing floor wood through normal pickup.
4. Use those two physical wood bundles in the existing campfire recipe, retain the tool and torch, place the unlit fire and ignite it separately.

Use a nearby legal fire position through current controls. No new recipe or tactical effect is needed. The torch is not used as an explicit fuel choice, so this trace does not depend on the known G12 menu omission.

Normal FOV, native AI, survival and costs remain active. Initial staging at the generated public approach and full-state route/UI selection are allowed when disclosed. Do not inject fuel or rewards, clear threats, enable invincibility or reset health/supplies. Call this a local interaction/process demonstration, not an unaided or normal-start expedition.

Capture only the few production-rendered views needed to assess the prompt, physical result and working fire. A hunt, second preparation, additional location or long survival itinerary is outside this proof.

## 5. Verify the actual risks and deliver

Use compact focused cases for eligibility/actual emptiness; missing or stale tool/source; reach and visibility; cancellation; creation/placement failure; repeated use; and full-pack output followed by capacity-aware pickup. Group related cases rather than building a new test framework. Check the successful action's single output, synchronized owner removal and turn cost.

Use one post-dismantling checkpoint with the crate absent and output still on the floor. Cover F5, a genuinely separate-process cold load and F9 through the existing save mechanisms. Distinguish this saved snapshot from later unsaved pickup/fire creation. Add a focused cache/unload/revisit check so neither crate nor yield reappears. Do not multiply save campaigns for unchanged campfire behavior.

Use the genuine committed G13 shed checkpoint at evidence/gameplay-g13/final-d/journey/shed/shed-checkpoint.zip to establish that a pre-edit visited scene loads unchanged until an explicit action. Preserve original evidence and historical fixtures. The review's Linux 6.3 versus 6.300000000000001 load representation difference is disclosed; do not turn this task into cross-platform determinism work.

Run small interaction, ownership, persistence and visual checks before freezing final inputs. Then run the established **unfiltered focused suite and unfiltered production D gate**, followed by the bounded G14 journey. Reuse the G13 concurrent arrangement for the two independent gates, with separate evidence/save roots, stable frozen inputs and both successful before the journey. Use the production interpreter and finite timeouts. No optional broad rerun campaign or new general harness; changed tested inputs require the affected checks and applicable final gates again.

Deliver the scoped implementation/tests, concise docs/owner/GAMEPLAY_G14.md, compact source-bound evidence and any directly affected control guidance. Record commands, environment, results, material failures and measured final gate wall time honestly. Do not infer total working time from commit intervals or add routine wiki/reference-pack maintenance.

When the owner supplies this brief for implementation, scoped delivery includes committing and publishing to the existing remote main, unique immutable checkpoints and exact remote branch/tag readback, subject to more specific instructions in that session. Preserve unrelated work; do not force-push or move existing tags.

**Stop when one explicitly emptied crate can become one recoverable wood bundle, that conversion supports the existing paid campfire path, and the change survives the required restore/revisit checks.**

No filled-container destruction or spill rules, portable-item disassembly, other furniture families, salvage catalogue, new tag/property system, new items/recipes/art, tool wear, XP/perks/corruption, craft-menu repair, healing, underground population, second site, broad balance work, wiki rewrite, reference-pack refresh or PDF is included.

