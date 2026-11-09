# Resonance Creator's Handbook

## Research, production plan, and complete Codex commission

**Package:** GUIDE-1  
**Version:** 1.0  
**Prepared:** 9 November 2026, America/Edmonton  
**Project:** [dgobi/ResonanceRoguelike](https://github.com/dgobi/ResonanceRoguelike)  
**Inspected published baseline:** `main`, `c166ec650b98156d53b8ea72e715c028d27db905`  
**Existing handbook baseline:** edition 1.3 / G9, reviewed source `f76aac1976a1c9b68adb00ed859398bbd60d6ee2`, dated 24 October 2026.  
**Status:** Researched production commission. This file is the plan and implementation brief for the guide, not the completed guide and not a claim that its future lessons have already been executed.

## Read this first

The intended outcome is that Dan can take an idea for his world, find the relevant part of Resonance, understand the important decisions, implement a bounded change, verify it, and diagnose a problem with ordinary reference lookup. An LLM may answer a specific question, but completing the workflow must not depend on an LLM writing the feature, remembering the project, or grading the exercise.

Build one durable **Resonance Creator's Handbook** by extending the existing owner wiki and its maintained source. Give it two connected uses: an immediate task reference and a guided learning path. A comprehensive reference can cover the whole project while the learning path introduces only what a particular creative task needs.

**Recommended execution: one substantial Codex commission, with internal milestones and one final delivery.** Part II below is ready to hand to the owner's local Codex session. It incorporates the relevant working rules so that the owner does not have to ferry a succession of briefs or milestone reports. It expressly includes the advanced code work; those chapters must not disappear behind a polished interface and a few JSON examples.

The handbook should be usable for months after this membership window ends. Its creation is a bounded delivery; learning a mature codebase remains an ongoing practice. No evidence can guarantee an individual's retention, and product verification must not be described as proof that the owner has already learned the material.

---

# Part I — Findings and product design

## 1. What was investigated

This review used the current published GitHub tree and targeted implementation reads across the runtime, authoring contracts, world construction, persistence, Workbench, verification infrastructure, existing handbook, and owner documentation. Separate read-only reviews examined runtime extension points, world/content authoring, and educational research. Selected saved project sources and relevant earlier decisions were also consulted.

The source investigation is broad and targeted, not a line-by-line audit of every repository file or every historical evidence directory. No game, Workbench, or production regression suite was executed for this planning review. Findings below are source-checked; older test reports remain reported evidence. GUIDE-1 requires Codex to run the actual examples in the supported local environment.

The current published head closes SYS-5. The subsequent action-adventure integration is a proposal, not an implementation established at this head. The guide must refresh against the actual checkout when work begins and account for any intervening changes without resetting it.

The saved references reviewed include the Project Compass, current Project Instructions, Workflow, Decisions and State, and relevant opening sections of the approved Implementation Proposal. The latest instruction to create this learning resource constitutes a dedicated handbook commission; the standing rule against automatic wiki upkeep during unrelated feature work does not block it.

## 2. The project already contains useful foundations

The existing `Resonance_Wiki_Maintenance/` directory has **33 authored chapters**, a standalone HTML reader, editable Markdown, search/navigation, embedded catalogues, examples, build/validation tools, and explicit source/authoring/product freshness checks. That investment should be retained. Its reviewed game snapshot is still G9, so its present-day existence does not certify present-day instructions. [R01–R03]

The active authoring registry has **eleven families**: access profiles, buildings, loot pools, underground assignment, settlement selection, rooms, creatures, items, recipes, texts, and typography. Their support is bounded by source class and operation; a listed family is not a promise that every file in that domain is editable. [R04]

The runtime has multiple real mechanisms for extending content and behavior. It also has specific boundaries and incomplete declarations that a trustworthy teaching resource must expose. The opportunity is to connect the existing systems into a usable mental model, supported by runnable examples.

### The central model to teach

For each feature, answer these questions:

1. **Definition:** What is declared, and where is its stable identity?
2. **Loading and construction:** When is that definition read, and what instance is created?
3. **Activation:** What action, event, placement, or selection route actually reaches it?
4. **State ownership:** Which object owns values that can change?
5. **Time:** What advances the behavior, and when is an action committed?
6. **Persistence:** What is saved, validated, restored, recomputed, or deliberately frozen?
7. **Feedback:** What can the player or author observe, and what evidence establishes success?

Do not imply that every feature passes through the exact same class or registry. This is a set of investigation questions, not a fabricated universal architecture.

## 3. Consequential findings that change the guide design

### 3.1 The existing documents mix several eras

The retained architecture material describes `TurnQueue`, while the current general simulation coordinator is `Engine._advance_turn`. Some owner status headings still refer to much earlier milestones. Workbench documents contain older contract strings alongside later additions: the inspected code has `expedition-items-6`, `item-preparation-3`, and `creature-composite-10`. The old owner lesson also contains an obsolete development-copy/branch workflow. [R05–R08]

These documents remain useful evidence and history. The new operational handbook must reconcile them against actual consumers, retain old reports as history, and stop presenting chronological milestone accumulation as the reader's route through the game.

### 3.2 “Add an ability” is several different tasks

| Desired behavior | Real starting route | What the guide must distinguish |
|---|---|---|
| A new weapon technique using existing effects | Weapon `movesets`, `movesets.py`, `Engine._try_moveset_action` | A new data combination versus a genuinely new primitive |
| A new usable item behavior | Item `on_use`/capability, `ItemSystem.use`, registered method | A string selects implemented code; it does not create a handler |
| A perk or event response | Perk hooks, `HookEvent`, `HANDLER_MAP`, live dispatch site | Registration, actual event firing, effect consumption, cleanup, and restored state |
| A creature assembled from existing behavior | `ai_profile`, factory, composite host and attachments | Supported recipes/hosts versus arbitrary behavior |
| A legacy creature power | `creature_abilities.ABILITY_REGISTRY` | Several powers depend on exact creature IDs |
| A timed condition | Specific lifecycle such as `venom.py`, action gates, saves | A working condition implementation versus an inactive generic-looking status declaration |

At this revision, the module-level `engine.py::_apply_effects` has literal unimplemented branches for `add_status` and `remove_status`. Several perk declarations and moveset fields do not have the broad semantics their names might suggest. The guide must distinguish **declared**, **retained**, **actively consumed**, and **verified in a stated scenario** where that distinction matters. [R09–R13]

Workbench equipment authoring retains essence and movesets as read-only. A complete technique guide therefore needs a manual source route. It must not pretend the editor already provides controls for every runtime feature. [R14]

### 3.3 Definition, appearance, and persistence are separate

A saved item does not automatically enter loot. A room does not automatically become a destination. A creature's `spawn_zones` metadata does not itself enroll it in an active spawn route. A debug spawn proves construction, not normal discovery.

For underground rooms, the current sequence is saved room → new-world selection policy → saved submap assignment → first construction → owned scene. Assignment edits affect new worlds; a same-ID room edit can affect a still-unbuilt room in an existing campaign; already generated scenes keep their saved state. Planned surfaces have additional captured dependency checks, so changing an existing definition can cause a pending construction refusal rather than silently update it. [R15–R17]

The guide needs a small lifetime table on each relevant recipe: running session, new instance, loaded instance, unbuilt scene, generated scene, and new world.

### 3.4 Action success, consumption, and time are different

An item action can succeed without consuming the item. `ItemSystem.use` distinguishes consumption from committed use through `last_use_committed`. Weapon timing, movement/work timing, AI opportunities, and display frames are not one interchangeable clock. The handbook should teach this with before/after state, rejected-action controls, and actual input routes. [R09, R18]

### 3.5 New state needs explicit persistence

Adding an attribute to an actor does not automatically save it. The project has explicit serialization, validation, defaults, reconstruction, and state-specific lifecycle rules. Even a supported container such as `Perks.perk_state` does not automatically validate a new inner schema.

The strongest implemented case study for a new persistent subsystem is **SYS-1 vessels**: exact physical item identity, water quantity, menus, revalidation, delayed jobs, completion/abandonment, rollback, and legacy absence rules. **SYS-2 is shared illumination**, not vessels. [R19–R21]

### 3.6 Existing verification can support good lessons, but must be selected carefully

Useful foundations include external structure drafts, candidate validation in temporary data roots, captured Workbench room tests, temporary save roots, real-engine fixtures, and app-local Pygame input journeys. They establish different things and should keep their labels.

Some old authoring journeys write into production content. In particular, `workbench/scripts/run-sys-5.mjs` points at the production root and publishes definitions even though its settings and saves are disposable. It must not be offered as a harmless general learning command. Likewise, the older copied-code `owner_lesson.py` workflow is not the current implementation arrangement. [R22–R27]

A small learner-facing launcher may be useful, but it is guide support to be implemented and verified, not a capability already assumed to exist.

## 4. The finished handbook

### 4.1 Four entry points

| Entry point | Reader's question | Content |
|---|---|---|
| **Start creating** | “How do I get oriented and make my first real change?” | Short setup, source navigation, first controlled edit, optional learning routes |
| **I want to…** | “How do I add this particular thing?” | Direct task recipes, prerequisites, exact files, tools, verification, failure diagnosis |
| **How Resonance works** | “Why does this behave this way?” | System atlas, execution traces, ownership/lifetime diagrams, design explanations |
| **Look something up** | “What does this field, term, error, or command mean?” | Schemas, glossary, symbol/source map, capability limits, troubleshooting, current catalogues |

This organization adapts the distinction between tutorials, task guides, reference, and explanation described by Diátaxis. It is an information-design framework, not evidence that a particular interface guarantees learning. [E09]

A reader should be able to skip the course and use a recipe immediately. The learning route should link the same authoritative material rather than maintain a second contradictory explanation.

### 4.2 A restrained visual direction

Use the existing reader as the foundation, with a refined field-guide/editorial appearance suited to Resonance: warm neutral reading surfaces, dark charcoal text, one restrained accent, and small authentic game images. These are proposed visual choices, not a new game-art specification.

Priorities:

- Readable body type, comfortable line length, clear hierarchy, adjustable text size, and light/dark themes.
- Stable task navigation, breadcrumbs, in-page contents, and fast local search.
- Code and its explanation close together; long code horizontally scrolls without forcing the entire page sideways.
- Distinct treatments for runnable code, partial excerpts, expected output, hints, and historical sources.
- Actual captured Workbench/game views with focused annotations. Do not invent interface screenshots.
- Small diagrams of state, ownership, selection, or event order; no giant node graph of the entire repository.
- Text labels as well as color; keyboard access, visible focus, usable zoom, and a narrow-screen layout.
- Print styles and readable Markdown sources as fallbacks.

Avoid a decorative dashboard filled with chapter statistics. The opening screen should make the next useful action obvious.

### 4.3 Durable offline use

The canonical standalone HTML must open directly from disk with no account, server, paid API, LLM, internet call, CDN, or browser extension required to read, search, reveal answers, and use the reference. The supporting examples and full solutions belong in the downloadable/repository package.

Reading offline and rebuilding a development environment offline are different promises. Record the tested Python, game, Workbench, documentation, and browser prerequisites. Explain what must be installed once; do not claim an untouched computer can compile and run everything without dependencies.

Optional bookmarks/progress may use local storage as a convenience, but need explicit export/import and a readable file fallback. Browser behavior for `file:` local storage is not guaranteed, so it cannot be the only durable copy of notes or progress. [E10]

A reader may continue using a dated edition after the game changes. It must show the reviewed revision and explain how to check relevant drift without treating a source hash as proof that the prose is correct.

## 5. Learning design grounded in evidence

The goal is practical authorship. Reading a clear explanation and feeling that it makes sense is useful, but insufficient. Lessons should require a small prediction, an observed result, a reasoned change, and eventually a different problem.

| Mechanism | Application to Resonance | Evidence and limits |
|---|---|---|
| Retrieval practice | Before revealing an answer, recall the relevant state owner, predict the result, or reconstruct the path | Recall improved delayed retention over rereading in controlled prose studies; that alone does not prove programming competence. [E01] |
| Spaced practice | Reuse concepts in later creative tasks and offer short delayed revisit prompts | Useful spacing depends on the retention goal; a fixed schedule is a design convenience, not an optimum established for this game. [E02] |
| Worked examples with fading | Complete example → partially guided variation → independently chosen implementation | Experiments support fading combined with explanation, especially for structured tasks; architectural transfer needs further practice. [E03] |
| Predict, Run, Investigate, Modify, Make | Read a small working path, predict it, observe it, change it, then make a related thing | PRIMM has favorable school-classroom findings. Solo adult use is an adaptation with explicit reasoning prompts and answer explanations. [E04] |
| Purpose-labeled steps | “Create the instance,” “Make it reachable,” “Commit the action,” “Preserve its state” | Programming studies support subgoal labels for initial problem solving. Longer-course evidence did not show a general exam-score advantage. [E05] |
| Explanatory feedback | Show why the result is right, what a failed result means, and how a lucky answer differs from understanding | Feedback benefits can include initially correct but uncertain responses. It does not require scoring every task. [E06] |
| Visible expert reasoning | Explain why an edit belongs in one module, what alternative was rejected, and what evidence is needed | Cognitive apprenticeship is a useful design framework, not a controlled trial of this handbook. [E07] |
| Separate completion from learning | Require a new variant, a diagnosis, and a delayed attempt; keep LLM help optional and conceptual | A recent small randomized developer study found weaker immediate skill assessment with AI assistance on an unfamiliar library. It does not establish that all AI use harms learning or predict this owner's outcome. [E08] |

The classic studies are included because they address durable learning mechanisms. “Modern” should mean applying good evidence carefully, not attaching fashionable features to a static manual.

### A standard substantial lesson

1. **Make something meaningful.** Show the exact game or authoring outcome.
2. **Establish the starting state.** Give the prerequisites, verified environment, files, fixture, and reset boundary.
3. **Predict.** Ask two or three short questions before revealing the explanation.
4. **Observe and trace.** Run the existing behavior and follow a small real execution path.
5. **Study the worked change.** Supply complete edits, purpose-labeled steps, reasoning, and observable checkpoints.
6. **Vary it.** Change one meaningful requirement with less guidance.
7. **Diagnose a fault.** Introduce a safe, realistic failure and show how evidence locates its cause.
8. **Make a different example.** Supply requirements and acceptance criteria without prescribing every edit.
9. **Check the explanation.** Include a hint ladder and complete solution/rationale locally.
10. **Return later.** Revisit the concept in another lesson or a short delayed task.

Not every field reference needs this structure. Use it for substantial lessons, and keep quick lookup concise.

### A practical review routine

At the start of a work session, recall three things about the previous change: where it enters, what owns its state, and how success was checked. At the end, write one sentence explaining an important decision. Revisit with a small variation after roughly one day, several days, a week, and a few weeks, adjusting to actual use and difficulty.

These intervals are optional defaults. No streak penalties, mandatory exams, notification service, or artificial mastery percentage is needed.

### What counts as independence

With reference lookup allowed, the owner can locate the relevant implementation, explain the important relationship, make a changed example, verify it, diagnose a realistic fault, and return after a delay. Useful progress labels are **followed**, **varied**, and **independent**, backed by a commit or short note.

Codex can verify that exercises and solutions work. It cannot certify the owner's later retention before the owner attempts them.

## 6. Curriculum and creative routes

The path is selective; the reference is comprehensive. Someone interested in places can reach location authoring before studying advanced mechanics. Someone interested in abilities can take the common foundation and then the code route.

| Lesson | Concrete outcome | Main understanding |
|---|---|---|
| L01 — Find, run, and explain one change | Trace an existing food, make one controlled change, inspect and reverse the diff | Definitions, instances, units, ordinary input, paid time, safe working context |
| L02 — Create a usable item | Author a supported variant through Workbench and understand the equivalent JSON; place and use it | Identity, saved dependencies, construction, appearance, runtime consumer |
| L03 — Put writing into the world | Create ordinary found text, bind a readable carrier, acquire and read it | Text versus carrier identity, page/span knowledge, language boundaries |
| L04 — Build a preparation chain | Supply materials/tool/heat, craft or process, obtain and use an output | Distinct physical ingredients, retained tools, first tick, cancellation, jobs |
| L05 — Compose a creature | Make meaningfully different ordinary enemies from supported behavior | Host obligations, perception, paid opportunities, supported attachments, saved profiles |
| L06 — Build a playable place | Create a room with geometry, a threat, readable context, useful contents, access, and an exit | Construction, reachability, interaction, light, encounter layout, depletion |
| L07 — Make a place appear naturally | Enroll an underground room and separately place a surface building through their actual routes | Selection, frontage/transforms, metadata versus construction, world/scene lifetimes |
| L08 — Give content a readable appearance | Edit/register an asset or display role and verify it in context | Sprite keys/atlas users, typography, UI/rendering boundaries, real preview |
| L09 — Add a weapon technique | Use supported moveset effects with an intentional identity and observable behavior | Targeting as implemented, cooldown IDs, accepted/rejected/missed action timing |
| L10 — Implement a genuinely new ability primitive | Follow a complete Python change through parsing, application, feedback, and checks | How to extend an existing mechanism rather than merely select a predefined effect |
| L11 — Add an event response and understand a condition | Implement a new hook handler; trace venom or another current lifecycle | Actual dispatch, registration/cleanup, effect consumption, phase boundaries, persistence |
| L12 — Build a small persistent subsystem | Study vessels end to end, then implement a bounded unfamiliar state machine in a lesson fixture | Ownership, state transitions, failure/cancellation, schema/defaults, cold restore |
| L13 — Author an original expedition | Combine the owner's place, enemy, discovery, useful reward, and later consequence | Creative intent translated into a content graph; meaningful play and reusability |
| L14 — Diagnose and maintain independently | Repair an unfamiliar defect, describe the change, update the relevant guide page | Hypothesis, smallest useful observation, regression evidence, source drift |

L08 can be taken when visual authorship becomes useful. L09–L12 are mandatory delivered chapters, even if the owner chooses to study them later. L13 uses a small representative expedition as an instructional exercise; it does not commission the pending production action-adventure package.

Publish explicit short routes for content, places, abilities, and persistent systems. For each lesson, distinguish concepts the learner must understand from supporting assets the fixture supplies. A place-authoring lesson must include ready-made creatures, texts, and items so earlier authorship lessons remain optional unless their concepts are genuinely required. Each lesson needs a complete independent starting fixture or a clearly identified supplied checkpoint; do not require reconstructing every preceding exercise. Cross-links can offer deeper study without becoming hidden prerequisites.

The first several lessons should stay small enough to finish in a satisfying session. Advanced work may span sessions, with explicit restart points. Publish time estimates only after a dry run and label them estimates.

---

# Part II — Codex implementation commission

## 7. The commissioned outcome

**Execute GUIDE-1: produce the complete, current, polished, offline Resonance Creator's Handbook and its verified practice materials.**

This is a dedicated handbook, teaching, reference, and tightly bounded supporting-tooling task. Extend the maintained owner wiki rather than creating an unrelated documentation application. Complete the package through the internal milestones below, including advanced code lessons, verification, commit, push, and remote revision readback. Stop at this package boundary.

The owner wants to become the primary author of Resonance. Write for someone who can follow basic code and concepts but has not personally constructed this whole Python codebase. Use clear adult language, introduce necessary Python and architecture concepts when they become useful, and connect explanations to actual creative work.

Do not return only an outline, architecture report, source-file summaries, refreshed catalogue, attractive homepage, or a promise to write the harder lessons later.

## 8. Working arrangement and scope

### Required execution rules

- Read applicable `AGENTS.md`, inspect current branch/HEAD/status and existing work, and reconcile this inspected baseline with the actual checkout.
- Use the existing production checkout on `main`. Preserve unrelated owner changes and personal campaigns. Do not create task branches, worktrees, or additional development copies/checkouts. Existing bounded test fixtures and host-captured runtime payloads remain allowed within their established contracts; they are not places to develop a parallel game implementation.
- Make named checkpoints before substantial changes. Use one implementation writer. Parallel helpers may inspect, research, and review without competing edits.
- Use autonomous headless or app-local verification. Do not control the owner's desktop or make routine testing depend on the owner.
- Internal milestones are continuation/recovery points, not new approval requests. Keep one compact resumable progress record.
- Resolve routine example choices, writing, layout, and implementation details within scope. Pause only for a consequential unresolved choice or a genuine blocker that cannot be resolved within the package; finish independent work first.
- **Commit and push the completed scoped work, verify the remote revision/readback, and report the result.** Do not claim publication if it is blocked.
- Do not execute pending gameplay packages or expand the project roadmap as part of guide production.

The existing rule that wiki upkeep is separately commissioned is satisfied by this task. Its historical “update the whole wiki on every feature” wording must not be reinstated as a standing obligation.

### Authorized work

Current handbook prose, information architecture, theme/reader improvements, relevant documentation corrections or current-guide pointers, examples/solutions, source inventory, small lesson launch/validation helpers, appropriate tests for new guide behavior, and packaging/maintenance instructions.

Temporary exercise patches may be used for verification under the guarded procedure in section 13. They are not authorization to leave tutorial mechanics installed in ordinary production gameplay.

### Keep the game scope bounded

Preserve current gameplay and creative direction. Do not use documentation discrepancies as permission to generalize statuses, redesign targeting, replace the scheduler, overhaul saves, migrate the engine, or add a new magic/quest system. A broken or incomplete current feature can be documented with a precise limitation and extension route. If a production defect blocks a chosen example, choose a different sound example or isolate the issue; do not silently convert this into a broad repair campaign.

Keep existing historical reports as historical evidence. Correct active instructions where necessary without rewriting the entire project history.

## 9. Required deliverables

1. **One canonical offline reader.** Preserve `Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html` as the stable openable path unless a concrete compatibility issue requires an alias. The visible title may become “Resonance Creator's Handbook.” Existing useful anchors should remain valid or receive explicit redirects.
2. **Editable sources in the existing repository.** Reuse `chapters/`, the build pipeline, examples, illustrations, and maintenance contract. Extend the organization where useful without creating competing current handbooks.
3. **Complete worked lessons L01–L14.** Include runnable worked solutions, guided variations, independent tasks, answers, hints, expected observations, failure diagnosis, and restart/cleanup steps.
4. **A comprehensive system and capability atlas.** Cover the domains in section 10 and distinguish active implementation, partial support, historical intent, and new proposals.
5. **An intent-based task reference.** A user searching “add an ability,” “new town,” “why isn't my item appearing,” or “save my new field” must reach the right route.
6. **A bounded practice package.** Keep examples outside normal production scans until deliberately installed. Provide supported fixtures and an owner-facing launcher if existing commands are too brittle or unsafe.
7. **A small source/evidence map.** Reuse existing manifests where possible; connect topics/lessons to definitions, symbols, relevant checks, reviewed revision, and execution receipts. Do not build a new documentation platform.
8. **Offline progress/notes export if progress is implemented.** Use stable lesson IDs and plain portable data; browser storage is optional convenience.
9. **An independently usable release bundle.** Include the reader, examples, solutions, concise opening/setup instructions, and maintainable source. A ZIP is appropriate for the portable bundle; the HTML itself must not require the ZIP's server.
10. **One concise final delivery report.** State what works, how to open it, the first recommended activity, source revision, checks actually run, material limitations, commit/push/readback, and any remaining blocker.

No PDF is required. The owner prefers Markdown source and an attractive usable guide.

## 10. Coverage specification

### 10.1 Current authoring-family reference

For each of the eleven registered families, document source location, eligibility, supported operations, controls, retained/read-only fields, validation, publication boundary, incoming references, runtime activation, fresh-versus-saved behavior, one useful example, and troubleshooting.

| Family | Required practical coverage |
|---|---|
| Item | Ordinary materials/supplies, food/drink, supported equipment, lights, coatings and vessels; exact eligibility; manual paths for unsupported mechanics |
| Recipe | Immediate and passive output, ingredients, conjunctions, quantity, tools, heat, water, cancellation, first tick, output, unsupported execution classes |
| Creature | Ordinary actors, supported AI recipes/attachments, perception, combat, harvest/remains, ID-bound exceptions, placement and saved profiles |
| Text | Variant creation, prose/page format, damage spans, preview, physical carrier, knowledge identity, protected/special texts |
| Pool | Weighted physical entries, context, dependency order, room/container binding, generated stock versus new rolls, legacy loot distinction |
| Room | Geometry/legend, direct items/actors/remains/decor, furnishing, access targets, preview, captured Test room, ordinary enrollment |
| Building | Category, placement contract, transforms, footprint/frontage/access, contents, eligibility, explicit memberships and legacy selection |
| Assignment | Saved underground candidates, chance/weights, new-world metadata, lazy construction and generated-scene retention |
| Selection | Current editable settlement membership lists, protected civic/layout policy, practical relation to larger generation |
| Access | Current coffer/screen methods, requirements, costs, state changes, alternate approaches, persistence, finite supported scope |
| Typography | Font/role profile, preview, resource dependencies, actual rendering, limits of the supported editor |

Treat registry/code-derived inventories as aids. An automatically generated table must not become an unsupported claim that every field has a live consumer.

### 10.2 System atlas

Every row below needs a useful current explanation and change route. Related rows may share a chapter when that improves navigation.

| Domain | Required explanation and authorship route |
|---|---|
| Startup and repository | Current launcher, working directories, interpreter/dependencies, configuration, production versus fixture, where logs appear |
| Python foundations in context | Modules/imports, functions/methods, dictionaries/JSON, objects/components, references/mutation, return values, exceptions, small tests |
| Runtime/input/time | Frame loop, modal input, action acceptance, consumption, phase costs, AI opportunity, death guards, pause/inspection |
| Definitions and identity | Loaders/catalogues, factories, stable IDs, filenames, instance IDs, duplicate/unknown data, session caches |
| Inventory/equipment | Exact ownership, same-ID siblings, transfer helpers, carrying, equip/use, drops, containers, remains |
| Combat and abilities | Attack path, body/armour/essence, techniques, targeting as implemented, cooldowns, item effects, perks/hooks, legacy abilities |
| AI and perception | Basic and composable hosts, registered recipes, attachments, commitments, visibility/hearing/light, no hidden-information shortcuts |
| Conditions and transformations | Venom phases and full physical paralysis, treatment, timers, effects, corruption/exposure boundaries, current limitations |
| Materials and processes | Crafting, harvesting, flesh depletion, vessel jobs, exact doses, material-sensitive preparations, completion/rollback |
| World structure | Coarse world, local scene, submap, identities, construction, scene ownership, transitions, hot/cold behavior |
| Places and generation | Buildings, rooms, entrances, settlement layouts, compounds, POIs, roads, wilderness, WFC where used, selection/dependencies |
| Lore and knowledge | Readable content, languages/glyphs, learned information and persistence, actually implemented gates, open/proposed systems |
| Needs and progression | Food/water units, ticks, survival modifiers, levels/perks/acquisition, supported versus declared unlocks |
| Light/weather/resonance | Shared illumination, held light/fuel, rendering versus perception, weather selection/consumers, resonance and discharge |
| Art and UI | Current sprite/atlas workflow, keys and shared cells, actual native/display dimensions, fonts/palette, panels, feedback and UI state |
| Saves and compatibility | Serialization/validation/defaults/restore, player/items/actors/scenes/world, checkpoints, fresh process, identity and legacy rules |
| Workbench internals | React document/edit views, Rust path/publication authority, Python worker/adapters, schema vocabulary, adding a supported field |
| Testing and diagnosis | Minimal reproduction, traceback, source search, breakpoints/observations, deterministic inputs, controlled versus ordinary scenarios |
| Sustainable maintenance | Git checkpoints/diffs/revert, focused checks, documentation updates, source drift, dependency restoration, explicit publication |

Provide the supported route for changing world-generation policy even where there is no Workbench page. Do not turn the lack of a control into the lack of a runtime capability.

### 10.3 Task recipes

At minimum, cover the following questions, grouping related recipes without omitting their distinct integration steps:

- Change an existing property and know when the change becomes active.
- Create an item variant, a food/drink, equipment, a held light, and a supported coating/vessel.
- Bind an item to loot, a container, an authored place, or starting/debug acquisition, with the scope explicit.
- Create a recipe and a passive processing chain; diagnose requirements and quantities.
- Add a creature; compose existing behavior; add harvest/remains; diagnose a lost ID-bound power.
- Write a readable text; bind its carrier; understand language/knowledge boundaries.
- Create a room; add threats/furnishings/items/access; test it; enroll it in a world.
- Create a building and validate its placement/approach; tune settlement membership; understand layouts/compounds/POIs/roads.
- Add a sprite or change a display role and verify actual appearance.
- Add a weapon technique from existing effects.
- Implement a new usable-item or weapon primitive in Python.
- Add a perk handler and verify its real event, registration, cleanup, and restored state.
- Add a timed condition or explain precisely what new implementation it requires.
- Build a new persisted subsystem, including failure and compatibility behavior.
- Find why an edit parses but does nothing, does not appear, uses stale values, loses state, or spends time incorrectly.
- Keep a creative change, undo only that change, and refresh the affected documentation without an LLM.

Each recipe needs the same compact contract: outcome; prerequisites; exact files/symbols; supported tool route; equivalent source changes; activation; state/time/persistence; expected evidence; common failure; next extension. Avoid duplicate explanations by linking the atlas and field reference.

## 11. Source and evidence discipline

Create a modest topic map with:

- Stable topic/lesson ID and authoring outcome.
- Reviewed source revision and relevant file/symbol references.
- Definition, consumer, state owner, and activation route.
- Workbench support and manual route.
- Current limitations or unresolved design boundary where relevant.
- Runnable example and relevant check.
- Actual execution receipt/environment, or an honest source-only label.
- Related task/reference pages.

Link to immutable repository sources and include essential explanatory excerpts locally. Prefer symbols plus exact paths over line numbers alone. Paths in the current manual must match the checked snapshot.

Use at least these distinctions in prose where needed:

- **Current implementation:** inspected active code.
- **Executed example:** named scenario ran on stated inputs/environment.
- **Historical source:** retained original account of an earlier state.
- **Partial/unsupported:** precise boundary and nearest working route.
- **Proposal:** future option, not installed behavior.

Do not label a whole feature “verified” because one fixture passed. Do not promote a screenshot to normal-play proof, a direct handler call to event-loop proof, or a source receipt to a gameplay result.

The initial snapshot in this package is an anchor for investigation, not a command to reset an advanced checkout. Resolve any later source differences locally and use the actual reviewed source in the final edition.

## 12. Lesson construction requirements

### 12.1 Teach the reasoning alongside the edit

Explain the important choices:

- Why this file/function owns the change.
- Why a value is definition-owned or instance-owned.
- Why an action is rejected, committed, consumed, or charged time.
- Why a reference or registration is required.
- Why a saved record needs a default, validator, or version.
- Why the chosen check proves the property and what it leaves untested.

Do not annotate every trivial line. Show the few decisions that transfer to the next task.

Use just-in-time Python explanations with tiny examples drawn from the same lesson. A novice-friendly glossary should unpack terms such as consumer, factory, instance, hook, invariant, schema, snapshot, and idempotence when they appear.

### 12.2 Every substantial worked lesson must be complete

Supply the exact starting state, exact commands and working directory, full runnable input or a clearly labeled partial excerpt, intended diff, checkpoints, expected result, cleanup, and full solution.

Never end a code example with “wire this into the engine,” “update persistence as needed,” or “add appropriate tests.” Show those changes. Advanced lessons may span several files, but the patch must be coherent and tested against the declared baseline.

For random behavior, describe controlled inputs and robust observations. A fixed world seed alone is not a promise of replay-identical combat. Do not use a lucky single hit or one absent spawn as decisive evidence.

### 12.3 Include meaningful practice

A guided variation must change a requirement, not only an ID. An independent task must leave an important decision to the learner. A diagnosis exercise must have a real symptom and a check that distinguishes likely causes.

Keep each lesson centered on one compact fixture or change. Guided variations and deliberate faults should usually modify that same example, not create separate projects. Independent tasks may adapt the shared scenario while leaving a meaningful decision to the learner. Related lessons may reuse assets, supplied checkpoints, explanations, and diagnostic exercises through explicit links; identify the distinct decision practiced in each. L13 is the full multi-system capstone. This reuse must not remove a lesson's runnable worked path or weaken the separate demonstrations required for L10–L12.

Use answer reveals and graduated hints: conceptual hint, relevant source location, partial step, then complete solution. Keep answers available offline. Reference lookup is allowed; the target is reasoning and authorship.

### 12.4 Three mandatory code-focused demonstrations

**A. New primitive:** teach a genuinely new runtime behavior, beyond a new JSON combination. Show the complete parsing/registration/result/application path, success and rejection, time/consumption, feedback, state/lifecycle if applicable, relevant authoring limits, and tests. Choose a small effect after inspecting the current code; keep it in a clearly identified practice namespace, not production loot or canon.

**B. New event response/condition:** show a new handler and real dispatch path with acquisition, duplicate-registration prevention, cleanup, and save/reload. Use the delivered venom lifecycle as a worked trace; preserve the full physical-paralysis semantics. Do not present the generic status stubs as a functioning API.

**C. New persisted subsystem:** first explain the implemented vessel system as a complete example. Then provide a small unfamiliar state machine with a named owner, configuration, state transition, normal action/inspection, time rule if applicable, cancellation/failure behavior, explicit serialization/validation/defaults, and same/fresh-process continuation. Choose an instructional mechanism that is understandable without new canon. Reusing an existing validated state container is acceptable when its limits are explicit, but a single extra JSON flag or an essay about architecture does not satisfy this requirement. Explain the additional production integration points for a new component/state owner.

Examples can share a teaching scenario where that reduces repetition, but each demonstrated capability must remain independently visible and testable.

Each of L10–L12 must exercise its intended production input or dispatch route with the final distributed solution/patch active, rather than only call the new helper directly. At least one advanced demonstration must run through the original event loop or captured room-test app-local events. Bind the exact solution/patch fingerprint to its execution receipt. Stateful lessons must verify a fresh process with the same lesson code and registrations installed before loading, then continue the behavior. Check absent or malformed lesson state before replacing current state. Focused real-handler checks remain appropriate for most negative controls.

## 13. Safe, reproducible practice

### 13.1 Reuse the right existing foundations

- Use external structure drafts and review outputs for geometry/placement work.
- Adapt the worker's temporary data-only validation and the separate existing disposable runtime-fixture patterns where appropriate. The latter may copy required Python, data, and assets for a bounded test; preserve their provenance and do not turn them into extra development checkouts.
- Use captured Test room for controlled authored play; teach Reset capture versus latest saved capture.
- Use an explicit disposable save root before engine construction/startup probing.
- Use real production factories, consumers, and input handlers. For at least representative play paths, use the original event loop or existing room-test app-local events.
- Keep component checks, direct-handler checks, native/input-loop checks, world-discovery checks, and cold-load checks separately described.
- Treat Windows/Python 3.11 gates in existing wrappers honestly. Verify the owner's actual supported environment rather than assuming a Linux command is equivalent.

### 13.2 Supporting launcher

If needed, build one small explicit lesson launcher by adapting existing fixtures. It may prepare disposable data/assets/saves and call production code or the existing captured runtime. It must show the lesson, source revision, data root, save root, and reset scope in plain language.

It must not become a second editor, a universal plugin framework, an arbitrary Python execution service, a parallel game implementation, or an extra development checkout. Preserve existing host capture/diagnostic activation boundaries and the distinction between a bounded test payload and a development copy.

All ordinary exercise outputs stay outside personal campaigns and normal scanned production content. A “disposable save” label must not hide production JSON writes.

### 13.3 Code patches

For lessons requiring real source edits, deliver complete reviewable patch files with:

- The exact baseline or matching content fingerprints.
- A list of affected paths and expected diff.
- A dry check and a readable refusal when the source is incompatible.
- Exact backup/checkpoint and rollback instructions that preserve pre-existing work.
- Explicit instructions for keeping a deliberate owner change versus discarding practice.
- Disposable save roots and no automatic enrollment in the production world.

During guide production, the lead may temporarily apply a scoped lesson patch to the existing checkout for verification only when the affected inputs are known and unrelated edits are preserved. Verify the actual intended route, then restore only the lesson changes and confirm the expected before/after identity. Never use a blanket reset, clean, or automatic overwrite to achieve that restoration. If an unrelated change conflicts, adapt the example or use an existing bounded fixture rather than discard it.

Before applying a temporary patch, preserve exact original bytes and existence state for every affected path and write a recovery manifest outside those paths. Record the patch fingerprint and expected patched-file fingerprints; apply only after the dry check passes. Use bounded child processes with explicit disposable save roots. Restore in `finally`; after interruption, reconcile the recovery manifest before other work resumes. Restore a path only if its current bytes match the expected lesson-patched bytes; otherwise preserve the intervening change and report the conflict. Verify original byte identity and absence of lesson-created production files. Never commit or push temporarily installed exercise code. Do not overlap temporary patch verification with another source writer or an ordinary game/Workbench process that may read those files; do not terminate an owner's process automatically.

Do not claim that Workbench candidate staging overlays arbitrary Python; it currently stages data. If a process-local registration fixture is used, disclose that setup and include the actual production patch/installation explanation. The fixture must still execute the real runtime seam it purports to teach.

Running the handbook build or opening the reader must never apply gameplay patches.

### 13.4 Useful deliberate faults

Choose a representative subset, not a separate test project for every row:

- Unknown use handler.
- A field that is parsed but never consumed.
- Duplicate or wrong ID/reference.
- A new item with no appearance route.
- A clone whose legacy power was bound to the old ID.
- Shared moveset cooldown because of reused action ID.
- A running catalogue or owned instance retaining old values.
- A room/profile change tested against the wrong lifetime.
- A missing saved field/default or malformed inner state.
- A cancelled/rejected action spending time or resources.
- A timer advanced by rendering rather than paid phases.
- A helper passing while no ordinary input reaches it.

Teach the evidence-driven diagnosis, not merely the final correction.

## 14. Internal milestones and continuation

### M0 — Reconcile current source and freeze the teaching scope

Inspect the real checkout and relevant instructions. Inventory current systems, authoring families, prior handbook assets, safe verification routes, environment, and material document/code mismatches. Resolve the actual source baseline and record the initial checkpoints.

Create the compact coverage/topic map and choose concrete examples. Do not produce a long standalone audit as the final result. Continue into M1.

### M1 — Complete one representative learning slice and the reader skeleton

Build L01 and L02 through actual execution, answer/hint sections, reference links, source evidence, and a rendered reader page. Include the task index and atlas navigation. Inspect readability and whether the instructions are sufficient without inferred steps.

Use this as an internal quality gate. Repair the pattern before scaling it across the book; do not stop to ask the owner to approve routine layout or lesson decisions.

### M2 — Reconcile the current atlas and reference

Cover every domain/family in section 10. Update the relevant old chapters or organize them into clear current pages. Preserve historical sources in a distinct archive/reference area. Add accurate Workbench/code routes and field-status/lifetime explanations.

Include the current SYS-1–SYS-5 and AI integration where supported by source, and any later source-checked changes. Keep pending production proposals explicitly separate.

### M3 — Complete the content and world learning route

Deliver L03–L08 and the associated task recipes using saved-dependency order, external candidates, captured play, world assignment, and appropriate persistence checks. Each worked example must be complete and executable.

Explain how to make an original place meaningful: layout, threat, clue, reward/use, access, and consequence. Keep the owner free to supply the fiction and aesthetic.

### M4 — Complete the code and systems learning route

Deliver L09–L12, including all three code demonstrations in section 12.4. Trace actual methods and state, supply complete patches/solutions, and verify the behavior and relevant negative controls.

This is a core milestone, not optional enrichment. Do not substitute a generic Python tutorial, copied source dump, or a hypothetical architecture essay.

### M5 — Finish integration, diagnosis, and independent authorship

Deliver L13–L14, the troubleshooting routes, glossary, source-search/debugging instructions, and concise optional LLM-help appendix. The capstone must require meaningful choices; the answer should explain valid alternatives rather than impose a single story.

Add maintenance instructions that the owner can follow manually: edit a page, validate a changed example, rebuild an edition, inspect source drift, preserve notes, and keep/publish a change.

### M6 — Finish visual quality, offline behavior, and portability

Refine the existing reader. Capture real relevant views. Check desktop/narrow layouts, zoom, long code/tables, keyboard navigation, search, anchors, reveals, copy/download actions, print, and local file opening with network disabled.

If notes/progress are implemented, verify export/import and storage failure behavior. Copy the reader/bundle to a different path and check it again. Required content and answers must remain accessible without an external source.

### M7 — Independent review, scoped repair, and final delivery

Use read-only reviewers to audit representative instructions from the reader alone, the advanced code lessons, current-source claims, and the acceptance matrix below. This is a documentation/usability review, not proof of human learning.

Repair material findings within scope. Complete the necessary final checks, package, commit, push, verify the remote revision, and deliver one concise report. Preserve a resumable record if interrupted; do not silently mark an incomplete mandatory chapter complete.

## 15. Completion criteria

The package is complete only when all of the following are satisfied:

| Criterion | Required evidence |
|---|---|
| Current baseline | Actual reviewed source revision, comparison with this planning baseline, clear historical/proposed distinctions |
| Comprehensive coverage | Every section-10 domain/family has a substantive current page/route; no empty stubs or catalogue-only substitutes |
| Task navigation | Representative intent and symptom searches reach the correct current pages; historical hits cannot masquerade as current instructions |
| Complete learning route | L01–L14 present with full solutions/hints, meaningful variation, diagnosis, and appropriate restart points |
| Genuine code teaching | New primitive, handler/lifecycle, and persistent-subsystem examples include full integration and executable evidence |
| Workbench accuracy | Supported controls/operations and read-only boundaries match implementation and observed relevant UI |
| Definition-to-play proof | Representative new item, recipe, enemy, room, and world-enrollment routes reach their claimed runtime behavior |
| Ordinary versus controlled use | Fixture staging and diagnostic intervention disclosed; debug success is not labeled natural discovery |
| Time/ownership correctness | Relevant accepted/rejected/cancelled actions, exact physical identity, and no double tick/consumption verified |
| Persistence | Stateful examples survive a fresh process and relevant scene leave/reentry; missing/malformed state behavior checked where meaningful |
| Practice isolation | No personal campaign access; no undeclared production content writes; temporary code changes restored; normal startup does not load practice mechanics |
| Offline reader | Direct file opening, search, navigation, essential images/examples/answers and downloads work with network disabled |
| Durable optional progress | Export/import works; blocked/cleared local storage does not break reading or destroy the only intended copy of progress |
| Readability/access | Representative pages inspected at desktop and narrow width, 200% zoom, keyboard navigation, and print; no clipped instructions |
| Source/maintenance | Source and product binding preserved, Workbench/lesson inputs included, drift identifies impacted topics without claiming prose correctness |
| Rebuildability | Documented build/validation commands run in the stated environment; no hidden dependency on this conversation |
| Publication | Scoped commits pushed and exact remote revision read back, or a precise publication blocker reported |
| Learning claims | No statement that successful automation proves the owner's comprehension or future retention |

Run checks proportionate to the change. Reuse existing gates relevant to affected contracts and preserve required obligations. Do not run every historical gameplay campaign after every prose edit, write tests that merely mirror text, or demand an owner playthrough as a delivery gate. Stop optional testing once the concrete remaining risks are resolved.

## 16. Maintenance without an ongoing LLM

Extend the existing source/authoring/product contract rather than replace it. Include the relevant Workbench source, lesson inputs, and supporting helpers in the audited input scope. Avoid hashing generated products as their own inputs.

A drift check should help the owner answer “which topics might now be stale?” It must not automatically rewrite prose, bless a new SHA, or certify that a field still behaves as described.

Document the actual build sequence, including the distinction between reviewed game/source revision and later handbook-product delivery commits. Preserve historical editions in the established manner. Update the current maintenance chapter's obsolete automatic-upkeep instruction to the actual separately commissioned/manual workflow.

Provide a small reusable page/lesson template and an example of updating one affected page. The owner should be able to maintain a feature guide after a small change without rebuilding the intellectual history of the project or requesting another full research pass.

## 17. Optional LLM help that preserves authorship

Include a short appendix with bounded question examples:

- “Explain how this value reaches this consumer. Use these files and do not edit anything.”
- “I expected X and observed Y. Here is the smallest reproduction. Give me one diagnostic hint before a solution.”
- “Review my proposed state owner and save behavior. Identify a missed case without implementing the feature.”
- “Check my explanation of this function and correct the misunderstanding.”
- “Compare my patch with these acceptance criteria. Keep suggestions separate from changes.”

The guide itself must provide enough reference, solutions, and diagnostic methods that these questions remain optional. Do not embed an AI tutor, API key flow, subscription, or model-specific orchestration requirement.

## 18. Final Codex report format

Keep the final report short enough to use:

1. The concrete result and exact file/launcher to open.
2. The first recommended lesson and where the “I want to…” index lives.
3. Reviewed game source and handbook delivery revision.
4. A concise coverage/verification summary, including actual platforms and meaningful limits.
5. Any unsupported current game behavior discovered that materially affects use.
6. Confirmation that ordinary gameplay/personal campaigns were preserved and practice is isolated, based on actual checks.
7. Commit, push, remote readback, and any publication blocker.
8. A clear statement of remaining incomplete scope if a genuine blocker prevents completion.

Do not require a new ChatGPT review before the owner can use the guide. The package should stand on its own.

---

# Part III — Source ledger

## 19. Project evidence

All repository links below are pinned to the inspected published source unless otherwise stated. They identify the basis of the planning findings, not a newly executed test run.

| ID | Source | Used for |
|---|---|---|
| R01 | [Existing wiki configuration](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/Resonance_Wiki_Maintenance/wiki-config.json) | 33 authored chapters; edition 1.3/G9; reviewed source/date; existing scope |
| R02 | [Wiki builder](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/Resonance_Wiki_Maintenance/build_wiki.py) | Existing standalone product and collection pipeline |
| R03 | [Wiki input contract](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/Resonance_Wiki_Maintenance/wiki_inputs.py) | Source/authoring/product identity and drift |
| R04 | [Authoring registry](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/content_authoring.py) | Eleven explicit families and bounded descriptor vocabulary |
| R05 | [Historical architecture guide](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/docs/ARCHITECTURE.md) | Historical scheduler description; need to reconcile |
| R06 | [Current collaboration rules](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/AGENTS.md) | Production main, preservation, separate wiki commission, finite packages |
| R07 | [Item adapter](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/item_authoring.py) | Current item contract, eligibility, consumption naming, inert effects, lifetime |
| R08 | [Recipe adapter](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/recipe_authoring.py) | Current recipe contract, execution limits, publication |
| R09 | [Engine](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/engine.py) | Actual simulation, moveset/perk paths, inactive status branches |
| R10 | [Movesets](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/movesets.py) | Result parsing and supported technique path |
| R11 | [Legacy creature abilities](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/creature_abilities.py) | Exact-ID registry boundary |
| R12 | [AI profiles](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/ai_profiles.py) | Registered recipes and supported hosts |
| R13 | [Perk handlers](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/perk_handlers.py) | Handlers, cleanup, restored bonuses |
| R14 | [Equipment authoring](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/equipment_authoring.py) | Retained read-only movesets/essence and action-ID cooldown note |
| R15 | [Underground assignment implementation](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/generation/authored_submap_selection.py) | Policy selection and saved assignment route |
| R16 | [Assignment guide](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/docs/AUTHORED_SUBMAP_SELECTION.md) | Metadata, lazy construction, campaign lifetime |
| R17 | [Building authoring](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/building_authoring.py) | Placement/selection, captured dependencies, legacy folder enrollment |
| R18 | [Item use](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/item_system.py) | Consumption versus committed use; exact object checks |
| R19 | [Saved component schema](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/save_components.py) | Explicit serialization, validation, defaults, restore |
| R20 | [Practical vessels](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/docs/PRACTICAL_VESSELS.md) | Persistent-system worked study |
| R21 | [SYS-1 delivery](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/docs/owner/SYS_1.md) and [SYS-2 delivery](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/docs/owner/SYS_2.md) | Vessels versus shared light; reported scope |
| R22 | [Worker bridge](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/workbench/worker/bridge.py) | Candidate data staging, real validators, incidental write guard |
| R23 | [Room runtime](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/room_test.py) | Captured inputs, injected save root, actual engine loop |
| R24 | [Native room-test fixture](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/workbench/scripts/run-room-tests.mjs) | Existing disposable authoring fixture pattern |
| R25 | [SYS-5 Workbench journey](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/workbench/scripts/run-sys-5.mjs) | Concrete warning: production data publication despite disposable app state |
| R26 | [Disposable play launcher](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/tools/play_disposable.py) | Production-code practice with isolated saves; smoke limitation |
| R27 | [Original-loop journey driver](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/tools/b1_journey.py) and [G18 example](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/tools/verify_g18.py) | App-local original input loop and environment-specific harness |
| R28 | [Venom](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/venom.py) | Captured victim-owned condition lifecycle |
| R29 | [SYS-5 report](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/docs/owner/SYS_5.md) | Latest published package context |
| R30 | [Existing maintenance chapter](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/Resonance_Wiki_Maintenance/chapters/maintenance.md) | Rebuild procedure and obsolete automatic-upkeep wording to reconcile |

The source list is an investigation map. Codex must also read actual adjacent consumers, schemas, UI paths, and checks needed by the final examples. A link alone does not certify its claim.

## 20. Educational and documentation evidence

The entries below give the research basis and its relevant limits. The proposed handbook structure and exact exercises are design decisions informed by these sources.

- **E01 — Roediger and Karpicke (2006), Test-Enhanced Learning.** [Original article](https://journals.sagepub.com/doi/abs/10.1111/j.1467-9280.2006.01693.x). Controlled recall-versus-restudy experiments with delayed assessment motivate short retrieval prompts. The material was prose, not mature-codebase maintenance.
- **E02 — Cepeda et al. (2008), Spacing Effects in Learning.** [Author's university record](https://www.yorku.ca/ncepeda/publications/CVRWP2008.html). Study/review spacing interacted with the final retention interval. It supports revisiting concepts, not claiming one exact programming-review schedule.
- **E03 — Atkinson, Renkl, and Merrill (2003), Transitioning From Studying Examples to Solving Problems.** [Author's university record](https://asu.elsevierpure.com/en/publications/transitioning-from-studying-examples-to-solving-problems-effects-/). Fading steps combined with prompts about underlying principles supported transfer in structured probability problems. This informs worked/guided/independent stages.
- **E04 — Sentance, Waite, and Kallia (2019), Teaching Computer Programming with PRIMM.** [Full paper](https://primmportal.com/wp-content/uploads/2020/10/teaching-computer-programming-with-primm-a-sociocultural-perspective.pdf). Predict, Run, Investigate, Modify, Make was studied with school pupils and teacher-led discussion. The adult solo version requires explicit explanatory support and is not directly validated by that study.
- **E05 — Margulieux, Morrison, and Decker (2020), Reducing Withdrawal and Failure Rates in Introductory Programming with Subgoal Labeled Worked Examples.** [Full paper](https://link.springer.com/article/10.1186/s40594-020-00222-7). A semester-long quasi-experiment found better formative quiz performance and fewer withdrawals/failures, without a statistically better average exam result. Purpose labels are useful scaffolding, not a complete learning method.
- **E06 — Butler, Karpicke, and Roediger (2008), Correcting a Metacognitive Error.** [Full paper](https://learninglab.psych.purdue.edu/downloads/2008/2008_Butler_Karpicke_Roediger_JEPLMC.pdf). Feedback improved later correct recall after initially wrong answers and after correct answers given with low confidence in general-knowledge experiments. Supply answer rationales, not only pass/fail indicators.
- **E07 — Collins, Brown, and Newman (1987), Cognitive Apprenticeship.** [Original technical report](https://files.eric.ed.gov/fulltext/ED284181.pdf). The framework makes expert reasoning visible through modeling, scaffolding, explanation, and exploration. It is a conceptual framework, not a randomized evaluation of this guide.
- **E08 — Shen and Tamkin (2026), How AI Impacts Skill Formation.** [Research preprint](https://arxiv.org/html/2601.20245v2). The main randomized study involved 52 experienced Python users learning an unfamiliar asynchronous library and measured immediate understanding. The findings caution against equating completed AI-assisted tasks with skill acquisition. Interaction-pattern comparisons are exploratory, not randomized proof of a particular prompt strategy.
- **E09 — Diátaxis.** [Official framework](https://diataxis.fr/). Its distinction among tutorials, task guides, reference, and explanation informs navigation and prevents one page from trying to satisfy incompatible reading needs.
- **E10 — MDN, Window.localStorage.** [Official documentation](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage). Direct-file storage behavior is unspecified and can vary, motivating explicit progress export/import and a readable fallback.

Additional studies considered included [Margulieux, Guzdial, and Catrambone (2012)](https://appinventor.mit.edu/explore/resources/subgoal-labeled-instructional-material.html) on subgoal instruction and [Hou, Ericson, and Wang (2022)](https://web.eecs.umich.edu/~xwanghci/papers/ICER22.pdf) on optional Parsons scaffolds. The latter reduced practice time without establishing a learning advantage in its classroom comparison; a custom code-puzzle engine is therefore not part of this commission.

## 21. Handoff to the local Codex session

Attach this file and use the following instruction:

> Read RESONANCE_GUIDE_1_RESEARCH_AND_CODEX_PACKAGE.md in full and execute Part II, GUIDE-1, as one finite commission. Use Part I and the source ledger as the researched rationale, then verify the actual current checkout before writing. Build the complete offline Resonance Creator's Handbook, including the advanced code and persistent-system lessons, working examples, solutions, task reference, and maintenance route. Continue through the internal milestones with one resumable record; do not return after each milestone for another brief. Preserve the existing production main checkout, unrelated work, and personal campaigns; use autonomous headless/app-local checks without desktop takeover. Keep tutorial mechanics isolated from ordinary production gameplay. Complete the acceptance checks, commit and push the scoped work, verify the remote revision, and deliver the finished guide with concise opening instructions and honest limits. Stop at GUIDE-1.

