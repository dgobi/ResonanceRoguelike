# Resonance G9 review and G10 implementation brief

Prepared 24 October 2026, America/Edmonton.

**Recommended next task:** G10 — Wilderness character and playable exploration. G9's bounded country-road objective is complete. The next visible improvement is coherent terrain using Resonance's existing biomes, tiles and gameplay. Routine wiki maintenance is explicitly removed; the owner will commission wiki work separately.

## Use this package

Give Codex `CODEX_G10_WILDERNESS_CHARACTER.md` as the next implementation brief. `G9_REVIEW.md` explains why that task follows from the current source, completion report, independent evidence checks and production images.

- `CODEX_G10_WILDERNESS_CHARACTER.md`: complete implementation scope, preservation requirements, ordinary-play demonstration and proportionate verification.
- `G9_REVIEW.md`: assessment of G9, fresh versus retained results, terrain findings and deferred alternatives.
- `g9-wilderness-baseline.png`: four actual G9 production scenes with revealed visibility. This is current-game evidence, not proposed G10 artwork or normal-FOV gameplay.
- `sources/WORLDGEN_G9.md`: exact attached/in-repo completion report.
- `sources/CODEX_G9_COUNTRY_NETWORK.md`: preceding implementation brief for comparison.
- `evidence/`: independent audits, fresh test and diagnostic receipts, complete fresh plans/journey reports, terrain observations, source-preservation records and reproduction scripts.
- `MANIFEST.json`: sizes, SHA-256 and CRC32 for every other package member.

## Reviewed state

Repository: https://github.com/dgobi/ResonanceRoguelike

Main and verified G9 tag: `f9fe901417b360bc1fda84835e0a793eaac2f6df`.

Frozen G9 game/test inputs: `919e8b40ab5ebca6cf5df6ae3afaf6baa4b67d78`.

The attachment and in-repo report are identical. All 726 frozen input files reconcile. All ten final-b release gates and 1,076 retained output identities reconcile. Independent data-only analysis verifies all 57 ordinary primary-pair distances, including 23,625 → 8,063 for the required capital journey.

Fresh review execution passed the 13 G9 network/lifecycle tests and the ordinary three-seed diagnostic with its 107,749-input journey. All 86 shortcut-scene fingerprints and all explored-checkpoint surface fingerprints match the retained run. The checkout's 6,302 tracked files remained unchanged and its status stayed clean.

The broad 229-test and 3,675-check production results are retained release evidence; they were not rerun wholesale during this review. The journey pauses AI and survival and uses invincibility, as its records disclose. G10 adds a short ordinary live excursion instead of treating that long controlled traversal as proof of play balance.

This is a new independent review package. The original separate G9 delivery ZIP was not supplied, so its exact archive inventory was not certified here. Current main and checkpoint tags were read back from the remote and matched the reviewed source.

## Reproduction

Use an environment with the game's dependencies. Review execution used Python 3.12.14, pygame 2.6.1, tcod 19.3.0 and numpy 2.3.5; the image contact sheet additionally uses Pillow. Timing comparisons across the implementation and review machines are not performance-improvement claims.

The scripts accept explicit checkout/output paths. In `evidence/`:

- `run_review_command.py --repo REPO --python PYTHON --evidence OUTPUT --check g9-tests` runs the existing two G9 test modules with guarded temporary saves and before/after tracked-file hashes.
- The same wrapper with `--check diagnostic-journey` runs the unchanged G9 diagnostic and real-handler journey with a finite timeout.
- `summarize_review.py --repo REPO --evidence REVIEW_OUTPUT` compares those fresh outputs with retained G9 plans and fingerprints.
- `evidence-audit/audit_g9_evidence.py --repo REPO --output OUTPUT_DIR` audits source and receipt identities without running game code.
- `evidence-audit/audit_retained_geometry.py --repo REPO --output OUTPUT_JSON` independently reconstructs geometry and physical distances.
- `gameplay-direction/probe_wilderness.py --repo REPO --out OUTPUT_JSON` measures ordinary metadata and explicitly controlled base-only scenes.
- `gameplay-direction/render_wilderness_baseline.py --repo REPO --out OUTPUT_DIR` renders the four ordinary complete native scenes.

Run evidence commands only when needed; the retained results already accompany this handoff. Historical source documents are copied verbatim, and their relative links retain their original repository context. Logs preserve the actual review paths and interpreter; those paths are provenance, not required installation locations. The contact-sheet script names the Linux display font used in this review; adapt that font path when reproducing the sheet on another platform. The game-rendered scene captures have their own unchanged production-renderer path.

No personal campaigns, dependencies, browser profiles or redundant game checkout are included. No game, wiki or remote source change was made by this review. Implementation and publication begin only when this brief is commissioned in the production checkout.
