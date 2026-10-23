# Current status — B2 (23 October 2026)

Accepted B1 is the base. B2 implements component replacement, Needs configuration,
perk-hook reconstruction and immediate bonuses, explicit timers and item instance
values, restoration of already-written actor fields and correct offscreen hot-map
processing ownership. The autonomous gate is `tools/verify_b2.py`; its final
[evidence](../../../evidence/b2-results.json) contains B2 checks and the complete B1
regression record. [B2_VERIFICATION](B2_VERIFICATION.md) defines its enforced cases.

The four original B2 defects are now positive regression properties. The four
remaining dynamically reproduced B3/C/UI defects and additional source limits are
in [B2_DEFERRED](B2_DEFERRED.md). Recommend B3 next. Creative authority, content,
normal controls, runtime versions and the original project are preserved.

<details>
<summary>Accepted B1 checkpoint and earlier history — retained, superseded where stated above</summary>

# Current implementation and evidence status

B1 (22 October 2026) implements scene identity, cold full-load replacement,
explicit empty inventory/equipment, exact saved-copy references, ghost armor/light
clearing, narrow lurker lifetime and v2 startup/format rejection. The final
acceptance record is [b1-results.json](../../../evidence/b1-results.json); the exact
command and evidence classes are in [B1_VERIFICATION.md](B1_VERIFICATION.md).

The mandatory baseline journeys now run autonomously through original Engine.run
and app-local events: movement/wait, inventory/equip, pickup/drop, ordinary combat,
bound document reading, processing completion, stairs, surface-edge movement and
nondebug save/load with a fresh-process bootstrap reader. Captures are offscreen
game surfaces. The text cutoff and equipped-drop defect are reproduced and
reported separately; completing dispatch is not certification of their correctness.

B1 is a narrow persistence repair. The individually reproduced B2/B3/C/UI limits
are in [B1_DEFERRED.md](B1_DEFERRED.md). No broad save fidelity, power-loss safety,
all recipes/combat/effects, creative redesign, personal-save migration or physical
keyboard certification is implied. Continue with [B2](NEXT_ARC.md).

Creative authority and the original decision register remain unchanged. Arc A's
historical diagnostics retain 17 pass / 15 fail; the corrected original properties
now pass 32/32. Owner learning remains optional and separate from acceptance.

<details>
<summary>Archived Arc A text — 20 October 2026; superseded operational requirements and failure status</summary>

# Current implementation and documentation authority

These labels are independent: **implemented** means an active source path exists; **partial** means important contracts are incomplete; **legacy** means retained but inactive/alternate; **planned** means intended without a complete path; **unverified** means this baseline lacks the relevant observation. A feature can be implemented and still unverified through normal input.

| System | Implementation | Arc A evidence / limitation |
|---|---|---|
| Bootstrap / default sprite display | Implemented | Live lab at 1280×720, no traceback; tcod warning only. Windows only. |
| Movement / wait / inventory | Implemented, transfer limits | Real movement and manual Z/I recorded; inventory inspected. Most native injected letter keys not delivered. |
| Turn flow / AI budget | Implemented | Source-backed `_advance_turn`; no active TurnQueue. Background simulation is partial. |
| Combat / equipment | Partial | Single HP pool with location/armor/essence stages. Ordinary combat in window remains unverified. Coatings, movesets and stale equipped references have reviewed defects. |
| Surface / underground / chunk travel | Partial | Source-supported; persistence fixtures lose surface contents after underground save. Normal-input traversal incomplete. |
| Save/load | Partial, unsafe invariants | Same-session and fresh-process diagnostics fail scene identity, empty-state replacement and lurking creature identity. Some explicit nonempty equipment relinking works; that is not full fidelity. |
| Crafting / processing / containers | Partial | Real offscreen craft render inspected; normal-input crafting completion unverified. Assignment/consumption/capacity/background-owner issues remain. |
| Text / language | Partial | Lab text and look component renders inspected; native readable-text input incomplete. Fixed lexical/glyph identity preserved. |
| Decor | Implemented functional layer, partial interactions | Blocking, harvest, resonance/objects and serialized map state exist; old “cosmetic/nonpersistent” claims are wrong. |
| Perks / progression / corruption | Partial; creative decisions open | Current K/points/hook implementation differs from discovery design. Zero/Unmarked startup observed. Separate Engine/component corruption values. |
| TurnQueue / StructurePlacer / old starting helper | Legacy/alternate | No active scheduler/structure-placer calls; main uses local_gen for the lab. |
| Broad ritual magic / shelter progression / full background world | Planned or incomplete | Do not convert roadmap checkmarks into feature certification. |
| ASCII, resizing, multiple pages, long-run progression | Unverified | Default sprite/window coverage only; one-page component renders are not broad UI certification. |

## Proposed authority model — owner approval pending

The creative identity remains the dark medieval new weird world after the resonance apocalypse. Preserve its specific creatures, gods, moons, archaic ancient voices, mundane plain voices and established glyph identities. This handbook does not redesign those elements.

Use three separate authorities:

* **Approved design:** owner-approved decisions and explicitly designated design passages. The two CLAUDE documents and ESSENCE contain important intent, but conflicting claims remain candidates until resolved. Code does not automatically redefine canon.
* **Current implementation:** source paths, fields and consumers bound to this snapshot. This handbook records those paths and known limits; newer prose alone is not authority.
* **Observed behavior:** bounded run records, actual screenshots and computed diagnostics with their evidence class. Source-supported and observed are not synonyms.

`DECISIONS.md` records unresolved choices and their future trigger. The owner has not yet approved a new canonical design document, so none is fabricated here. Owner participation in a small input check is not approval of design or confirmation of learning.

## Historical document labels

All original text is retained below a short banner pointing here. The labels scope technical claims, not erase creative history.

| Historical source | Status / use |
|---|---|
| Root and nested `CLAUDE.md` | Mixed design intent, implementation notes and instructions. Preserve creative constraints; reconcile conflicts through the decision register. “Equipment save/load clean” and all-JSON claims are not current guarantees. |
| `docs/OMNIDOC.md` | Historical composite duplicating standalone guides. Not an independent corroborating source or the new handbook. |
| `ARCHITECTURE`, `COMPONENTS`, `SYSTEMS`, `COMBAT` | Historical technical descriptions; verify against live source. Correct inactive scheduler and obsolete per-limb HP model. |
| `DATA_REFERENCE`, `CREATURES`, `GENERATION`, `LAYOUT_AUTHORING`, `WFC_AUTHORING` | Historical authoring references. Route-specific fields, stamping and probability/uniqueness claims need validation. |
| `DECORATIVES`, `DECOR AND RANDOM TILES`, `RENDERING`, `SPRITESHEET_GUIDE`, `DEBUG` | Mixed useful constraints and stale runtime claims. Use actual consumers/current controls. |
| `UI_RULES` | Retained design/implementation constraints, not a certification that every current screen satisfies them. |
| `ESSENCE` | Retained creative reference; not replaced by current partial mechanical consumers. |
| `INDEX` | Historical index. New reading order starts at repository README. |

## Prioritized backlog

1. B1: scene identity, stable creature identity and explicit empty-state replacement; use [NEXT_ARC.md](NEXT_ARC.md).
2. B2/B3: post-load derived state, torch fuel linkage, hooks/needs/timers, unique item instances, transactional save failures and deletion scope. Explicit compatibility decisions precede personal-save migrations.
3. Transfers/actions: rejected pickup/harvest/take-all, drop/equipment ownership, crafting allocation and refunds, scene/reach/time gates, cursor bounds.
4. Combat/effect lifecycle: damage modifier ordering, death ownership, aura expiration/stacking, moveset/coating behavior.
5. World/authoring: entrance footprint/link preservation, generation policy, active schemas/duplicate IDs, actual loot routes, painter losslessness, UI modes.

These are retained findings, not fixes delivered in Arc A. Do not combine the whole backlog into B1.

</details>

</details>
