# Resonance Roguelike ChatGPT and Codex Workflow

**Version:** 1.0  
**Prepared:** 24 October 2026, America/Edmonton  
**Purpose:** Make research, reviews and implementation briefs preserve the game direction without creating a second development project out of documentation.

This protocol combines established owner preferences with a recommended lightweight way to apply them. It does not commission implementation, authorize publication or require a new approval ritual. Use the current task and existing session authorization to decide what work to perform.

## Start with the right context

For a substantive design discussion, milestone review or next-brief request, consult:

1. `RESONANCE_PROJECT_COMPASS.md` for enduring experience and setting.
2. `RESONANCE_DECISIONS_AND_STATE.md` for decisions, known conflicts and the last inspected baseline.
3. The actual current repository, relevant brief, completion report and supporting evidence.

For a small correction, read the applicable instructions and the relevant files. Do not require the entire wiki, every historical report or a full repository audit before each edit.

These filenames are an organizational convention. ChatGPT Project sources, ChatGPT instructions and the Codex working tree are separate context surfaces. An uploaded file or a GitHub URL does not synchronize the local checkout. Codex needs the relevant guidance in its actual task context or repository; `AGENTS.md` has its own documented discovery mechanism. [W1, W2]

## Separate intention from implementation

Ask two different questions.

**What should the game become, and what work is authorized?** Use the owner's latest explicit instructions, established decisions and current authorized brief. Retain supported creative intent. Mark recommendations and unresolved choices as such. An assistant-authored proposal does not become an owner decision because it is newer or more confident.

**What currently exists and works?** Inspect the identified source revision and relevant behavior or evidence. Distinguish a source path from an observed result, a previous report from a rerun, and a fixture from ordinary play. Documentation and code can disagree without either automatically redefining the intended game.

When sources conflict, state the specific disagreement and resolve only what the task actually requires. A stale wiki instruction already superseded by the owner does not require asking the same question again. An unresolved choice about the player origin or progression should remain open until work depends on it.

Do not silently merge contradictory instructions into an invented compromise. Do not restore old bugs to the current backlog merely because an archive describes them.

## Roles and handoff

| Participant | Main responsibility in the established workflow |
|---|---|
| Owner | Creative direction, priorities, consequential design choices and experiential feedback. |
| ChatGPT review/research | Compare intent, current source and evidence; investigate relevant methods; explain tradeoffs; prepare the next bounded brief and useful owner documentation when requested. |
| Codex implementation | Implement the supplied scope in the established checkout, preserve existing work and state, perform appropriate autonomous verification, and deliver source-bound results under the actual authorization. |

These are working roles, not a restriction against an explicitly requested different arrangement. A read-only review environment is distinct from Codex's production implementation checkout.

## A normal milestone review

### 1. Establish what was actually inspected

Identify the branch/commit, relevant task brief, completion report and accessible sources. Compare changed code with the prior reviewed baseline where that answers the question. A short coverage statement is enough; do not claim to have read all project chats when only excerpts or retrieved summaries were available.

If the repository advanced after the report, inspect the intervening changes. If access is unavailable, finish the useful document-level analysis and identify the exact limitation. Do not describe the result as a live-repository review.

### 2. Review the delivered outcome

Check the commissioned outcome, important invariants, integration points and material regressions. Trace consequential claims to code or evidence. Preserve the distinction between completion, reported verification, independent verification and owner acceptance.

Explain what the player or content author gains. A road-distance improvement can support better travel; it does not by itself demonstrate engaging exploration. A safe save round trip protects the experience even if it adds no visible content.

### 3. Select the next useful objective

Use the compass and current experience to choose a bounded improvement or repair. Do not automatically extend the subsystem that was just completed. Ask what currently obstructs a useful expedition, readable place, satisfying interaction, material choice or practical authoring task.

Research when the decision needs it. For substantial new systems or design changes, use relevant primary documentation, original research and comparable implementations, and explain what transfers to Resonance. Verify version-sensitive technical details. Sources inform the choice; their full feature sets do not become requirements.

### 4. Produce the requested brief or recommendation

When the owner asks for the next brief, provide it rather than stopping at a proposal to write one. If a consequential unresolved choice genuinely prevents a coherent brief, do the supported analysis first and ask the narrow question that remains. Do not ask for permission already established in the conversation.

### 5. Keep only material context changes

A review can end with a small note containing a new decision, changed baseline, newly demonstrated limit or next issued brief. Update these reference files when asked or when a deliberate consolidation is commissioned. Do not append a full transcript or make the pack a routine implementation gate.

## What a useful Codex brief contains

Use these elements when they help; the format is not another mandatory long template.

| Element | What it should establish |
|---|---|
| Outcome and reason | What the player or author will gain, or what defect will be removed. |
| Current basis | Relevant commit, source paths, prior result and actual constraints. |
| Scope and exclusions | One coherent deliverable and the adjacent work it does not commission. |
| Integration contract | Existing behavior, identity, content, saves and authoring routes to preserve. |
| Acceptance | Observable results that demonstrate the intended outcome. |
| Verification | Appropriate autonomous checks, genuine compatibility evidence where needed, and disclosed limits. |
| Delivery and stopping point | Necessary code/data, concise guide or report, relevant evidence and already-authorized commit/publication steps; stop at the scoped outcome. |

Begin with the result, not pages of process. Give Codex room to solve routine implementation details. Include exact algorithmic requirements only when they protect a real invariant or a deliberate owner choice. Do not prescribe research-derived machinery merely because it is sophisticated.

Do not automatically add a new browser editor, general framework, benchmark campaign, documentation subsystem or exhaustive audit to each feature. A task that changes a real authoring contract should explain the changed contract accurately; that is different from rebuilding the complete wiki.

## Evidence that answers the actual question

Choose evidence for the risk and claim being made. Existing required release gates remain applicable to their authorized scope; this protocol does not waive them.

| Evidence | Supports | Does not establish by itself |
|---|---|---|
| Source inspection | An active path, field, ownership rule or configured value exists. | Successful use through normal game handlers. |
| Focused automated check | A specified invariant or regression behaves as asserted. | Complete feature quality or all-world coverage. |
| Controlled traversal fixture | Access, seams, interactions or persistence under disclosed conditions. | Ordinary survival pacing when AI, supplies or invincibility were altered. |
| Short ordinary-play script | A bounded outing works with the stated visibility, AI, survival and resources. | Unaided human discovery, an exploration AI or overall fun. |
| Production-rendered image | Visible output at the stated seed, location and rendering conditions. | Normal player visibility if the image was revealed/debugged. |
| Save, cold load and restore | The stated scene, actor and mutable content contracts survive that scenario. | Universal migration or complete RNG replay. |
| Timed sample | Cost of the measured scope on that environment. | A universal performance guarantee or a fair comparison of unequal workloads. |

Codex should use headless execution, app-local events and disposable save roots where appropriate. It should not take over the owner's desktop, access personal campaigns for fixtures or make the owner replay routine verification. Preserve failures that materially explain a repair or a limit; do not require piles of redundant successful evidence.

For player-facing work, add a small relevant ordinary-use demonstration when feasible. Do not inherit a previous arc's enormous coverage itinerary just because it exists. A few meaningful chunks can answer a playability question better than a much longer protected walk. Subjective feedback can guide priorities without becoming mandatory manual testing.

## Preserve the existing execution arrangement

Codex implementation uses the owner's existing production checkout on `main`, with named checkpoints and clearly scoped changes. Preserve unrelated owner work, existing campaigns and established compatibility contracts. Do not reset an advanced branch to match an old brief or create task branches/worktrees contrary to the standing project preference.

Respect the actual session's commit and push authorization. A review request or this reference pack alone is not a request to publish code. Conversely, an already authorized implementation/push does not need a second approval simply because it reaches delivery. Use the current brief's publication and readback requirements rather than importing blanket approval steps from an external example.

## Maintain context with little overhead

| Item | Update trigger | Who normally handles it |
|---|---|---|
| Compass | The owner changes enduring game identity, priorities or a durable boundary. | ChatGPT during a requested reference update. |
| Decisions | A consequential choice is explicitly made, reversed or newly exposed. | Capture in the review; consolidate when useful. |
| Dated baseline | A substantive milestone review or new arc needs a reliable starting point. | ChatGPT source/evidence review. |
| Workflow | The owner changes the arrangement, or a recurring concrete failure justifies a small adjustment. | A targeted instruction update. |
| Relevant feature guide/report | The commissioned feature needs accurate usage or delivery information. | Within that feature's scoped delivery. |
| Full owner wiki | The owner commissions a dedicated wiki update. | The separately requested wiki task. |

Use one active version of each reference filename, with date/version inside. Preserve older copies as clearly historical records rather than leaving competing current versions. Project uploads and repository copies require deliberate replacement; do not assume either updates the other. No automated upkeep or schedule is introduced by this pack.

## Reusable prompts

These are optional starting points, not additional work that must accompany every request.

### Review a completed milestone and write the next brief

> Review the completed Resonance milestone against RESONANCE_PROJECT_COMPASS.md, the current decisions/state record, its actual brief, the live repository and its completion evidence. Identify the revision and source coverage inspected. Explain what changed, what is verified, important limits or regressions, and the player-facing benefit. Research the next decision where useful, then provide the next bounded Codex brief. Keep road simulation subordinate to play and appearance, preserve autonomous headless/app-local testing, and exclude routine wiki maintenance. Do not treat proposals as approval or extend scope simply because the previous arc worked on that subsystem.

### Evaluate a proposed feature

> Assess this idea against Resonance's core loop, setting and pillars. Explain the concrete benefit, the simplest coherent version, dependencies, material tradeoffs and what could demonstrate it. Separate existing capability, retained intent and new proposal. Resolve routine details yourself; surface only consequential owner choices. This request is analysis, not implementation authorization.

### Refresh the reference pack

> Reconcile the three Resonance reference files with the owner's latest decisions, current repository and newest completion evidence. Preserve stable goals, replace stale baseline statements, retain unresolved choices, and mark superseded guidance explicitly. Update only materially affected sections. Do not expand the roadmap, commission new game work or maintain the wiki as part of this task.

## Research basis

This is a project-specific application of concise goals, explicit boundaries, scoped evidence and lightweight decision records. It does not adopt a complete external harness. The supporting research and the ready-to-paste Project instructions are in `RESONANCE_START_HERE.md`.

- **W1:** OpenAI, [Projects and chats](https://learn.chatgpt.com/docs/projects).
- **W2:** OpenAI, [Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
- OpenAI, [Prompting](https://learn.chatgpt.com/docs/prompting), [Long-running work](https://learn.chatgpt.com/docs/long-running-work), and [Rethinking skills and prompts](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).
- Michael Nygard, [Documenting Architecture Decisions](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
