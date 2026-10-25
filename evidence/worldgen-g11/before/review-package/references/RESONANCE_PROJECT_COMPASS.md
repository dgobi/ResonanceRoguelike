# Resonance Roguelike Project Compass

**Version:** 1.0  
**Prepared:** 24 October 2026, America/Edmonton  
**Purpose:** Keep design, research, repository reviews and implementation briefs directed toward the intended game.  
**Status:** Synthesis of explicit owner direction and retained creative references. This document does not approve new features, settle recorded open decisions or certify implementation.

## The game we are making

Resonance is a dark medieval, new-weird, open-world, turn-based traditional roguelike. The player inhabits the silence after a resonance catastrophe: ruined settlements, interrupted lives, strange wilderness, surviving mechanisms and older civilizations beneath the visible world. Exploration supplies particular objects, materials and knowledge. Understanding and using those discoveries lets the player become better equipped and venture farther and deeper. [C1]

The owner's governing priority is **a fun, playable, realistic-in-appearance post-apocalyptic open world that fits this setting**. Plausible geography, streets, settlements and systems serve exploration, atmosphere and meaningful interaction. Efficient road networks or comprehensive simulation are not independent project goals. [O1]

This is Resonance Roguelike, at `https://github.com/dgobi/ResonanceRoguelike`. Its identity and technical history are separate from Project Volumnia and the owner's other Godot or PSX game concepts.

## The core player loop

1. **Explore and interpret.** Read terrain, buildings, objects, threats and fragments of text; decide where to go and what to risk.
2. **Scavenge and harvest.** Find particular useful things in places where they make sense. Choose what to carry, use or leave.
3. **Process and experiment.** Turn materials and discoveries into usable preparations, equipment and understanding.
4. **Prepare and grow.** Improve the ability to survive and act through equipment, knowledge and the world's transformative systems.
5. **Venture farther or deeper.** Revisit changed places and reach more demanding locations with new capabilities. [C1, C3]

This is an experience target. It does not claim every stage is complete, balanced or presented through its final interface. In particular, discovery-led progression and the current recipe/perk interfaces remain an open design reconciliation.

## Five design pillars

These pillars organize the existing direction; they are not five new feature commissions.

### 1. The aftermath is readable in places and things

The world should suggest how people lived, what they believed and what interrupted them. A shrine, storehouse and house need different arrangements and contents. Architectural layers, unfinished work, furniture, containers and found texts carry the story. Silence and absence have meaning because the places show evidence of life. Rare, oblique NPC encounters support this experience; a conventional quest-hub society is not the recorded foundation. [C1]

**Decision test:** Does this addition make a place more particular, interpretable or worth searching? A larger number of interchangeable buildings is a weak substitute for a small set of convincing places.

### 2. Physical discoveries feed the next expedition

Scavenging should produce useful choices: an object has context, a material has a use, and processing can change what the player can do. Containers and furnishing are part of that interaction. Carrying limits, tools, preparations and equipment matter when they create intelligible decisions within the exploration loop. [C1, C3]

**Decision test:** What can the player discover, obtain, transform or use differently? Adding simulation detail without a useful decision needs a specific justification.

### 3. Knowledge of this strange world creates power

Resonance, essences, material provenance, language, creatures and correct conditions give the world learnable rules. Recorded intent favors experimentation and found knowledge. Corruption is transformative: it should open possibilities, not merely act as a generic punishment meter. Combat is intended to be driven by weapons and their properties. The world presents dangerous places rather than scaling everything to the player's level. [C2, C3]

**Decision test:** Does a mechanic reward observation and understanding of Resonance's particular rules? Preserve functioning interfaces until an authorized task resolves their differences from the intended discovery experience.

### 4. Exploration leads through believable, connected places

Wilderness, settlements, rural sites, landmarks and underground locations should relate coherently. Approaches must reach actual entrances; streets should serve readable places; terrain should create navigable patterns and useful choices. A large world is valuable when its space supports discovery, pacing, orientation and atmosphere. [O1, C4]

**Decision test:** Does the work improve a journey the player can undertake or a place the player can understand? Graph scores, asset counts and map extent are supporting measurements, not the player experience itself.

Spatial connection, a continuously scrolling view and offscreen simulation are separate capabilities. Progress on one does not imply completion or authorization of the others. [C4]

### 5. Actions feel tangible and their consequences endure

Movement, combat, harvesting, interactions and transformations need clear, satisfying feedback. The creative reference treats impact, callouts and effects as part of design. The repair history establishes that a player's objects, changes and location must survive the supported transfer, travel and save/load contracts. [C1, C5]

**Decision test:** Can the player tell what happened, and can they trust it to remain true? Automated evidence can establish a specific persistence or interaction property; it cannot alone establish atmosphere or fun.

## Setting anchors to preserve

**The catastrophe has already occurred.** Grey stone carries resonance. Settlement bells tuned stones, stones tuned people, and accumulated resonance discharged. Dangerous bells, waystones, transformed survivors and interrupted infrastructure connect the setting's appearance to its mechanics. The transformed dead should not casually become generic zombies. [C2]

**History is layered.** Deep One stone-and-bone engineering lies beneath Valdric metallurgy and monumental masonry; medieval successors occupied those remains before the latest catastrophe. VUKH and Valdremor anchor this geography and history. A shop within an older arch or a cellar exposing pre-human stone expresses this more effectively than undifferentiated ruin dressing. [C2, C3]

**The player has two mysteries.** The retained origin is awakening in a sarcophagus in an underground laboratory that studied resonance. What happened to the world and what happened to the player are related questions. The intended Touched start and the current mechanical start are recorded separately as an open decision. [C2]

**The world has its own vocabulary.** Preserve the six essences—Dissolution, Binding, Quickening, Consumption, Revelation and Severance—and established creature, deity, moon, language and glyph identities. The essence ontology does not require a numeric essence field on every item; its full mechanical scope is not settled by this compass. [C3, C6]

**Voice has different registers.** Ancient material can be ornate and archaic; mundane descriptions should be terse and specific. In-world narrators may be unreliable. Technical instructions, controls, owner guides and development evidence should still be clear and accurate. Fictional uncertainty is not permission for ambiguous project documentation. [C1]

## Enabling commitments

- **Protect existing play.** Preserve owner work, player-modified places, item ownership and supported save contracts. Do not regenerate a visited area to conceal a generation problem.
- **Keep content authoring practical.** Prefer supported data-driven definitions, useful examples and previews of the actual runtime path. The owner should be able to add and tune appropriate content without repeatedly reverse-engineering the code. This is a preference for usable authoring, not a promise that every new mechanic needs no code.
- **Respect the existing game.** Extend the current systems within the authorized task. Engine replacement, broad rewrites, expanded platform support and new presentation modes are separate decisions.
- **Keep verification useful.** Codex performs appropriate autonomous headless or app-local checks. The owner supplies creative judgment and experiential feedback; routine regression testing should not be transferred to them.
- **Keep documentation proportional.** A changed feature can need a concise accurate guide or completion record. Comprehensive wiki maintenance happens only through separately commissioned work. [O1, C5, C7]

## Boundaries against drift

The following are not standing commissions: realistic transport optimization; traffic or civilization simulation; exhaustive climate, erosion or ecology models; a larger or infinite world; a continuous viewport; a conventional NPC economy; generic elemental magic; or a wholesale progression redesign. Some ideas may be considered later, but they require a concrete player benefit and an authorized scope.

Long-term ideas such as world-age ecology, shelter progression and fuller ritual magic remain design references or deferred work until their implementation and scope are established. A roadmap checkmark, a research paper or a confident older paragraph does not settle that status.

Likewise, no milestone needs a complete wiki rebuild merely because it changes a feature. The owner's latest wiki instruction supersedes older automatic-maintenance language. The current reconciliation is described in `RESONANCE_DECISIONS_AND_STATE.md`.

## A short filter for the next substantive brief

Before committing the next arc, answer these questions in ordinary language:

1. What changes for the player, or what concrete defect or authoring obstacle is removed?
2. Which part of the core loop or which pillar does that support?
3. What is the smallest coherent outcome that can demonstrate the benefit?
4. What existing behavior and saved state must continue to work?
5. What evidence will establish the outcome, and where will judgment still be needed?

If the benefit is only a better internal metric, a more elaborate technique or a larger scope, reconsider the objective. When the bounded outcome has been demonstrated, choose the next task from the resulting game rather than automatically deepening the same subsystem.

## Source basis and change rule

Change this compass when the owner changes the enduring direction. Routine milestone completion belongs in the dated state record. Do not turn a code change or an assistant recommendation into a new creative commitment.

- **O1:** Owner's 24 October 2026 instruction in the G8/G9 review discussion: prioritize a fun, playable, realistic-in-appearance open-world post-apocalypse; commission wiki maintenance separately. The exact supplied wording and its effects are recorded in `RESONANCE_DECISIONS_AND_STATE.md`.
- **C1:** [Retained identity, tone and core loop](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/CLAUDE.md#L17-L81).
- **C2:** [Catastrophe, player origin and historical strata](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/CLAUDE.md#L83-L198).
- **C3:** [Spatial danger, world structure and systems design](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/CLAUDE.md#L594-L944) and [retained design constraints, including weapon-driven combat](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/CLAUDE.md#L1235-L1261). Retain creative direction; reverify technical claims.
- **C4:** [Historical world-generation audit and proposal](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/docs/owner/WORLD_GENERATION_AUDIT_AND_PROPOSAL.md). Candidate techniques and sequence are not permanent requirements.
- **C5:** [Persistence, ownership and combat repair records](https://github.com/dgobi/ResonanceRoguelike/tree/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/docs/owner).
- **C6:** [Essence reference](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/docs/ESSENCE.md) and [open decisions](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/docs/owner/DECISIONS.md).
- **C7:** [Repository working preferences at the reviewed commit](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/AGENTS.md). Its automatic wiki paragraph is superseded by O1.
