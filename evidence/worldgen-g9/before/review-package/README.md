# Resonance G8 review and G9 execution handoff

Prepared 24 October 2026, America/Edmonton. Reviewed repository main and verified G8 tag: `b94a0b0db3685f7484632701f0486f3b0b79101e`.

## Start here

Give Codex **`CODEX_G9_COUNTRY_NETWORK.md`** as the execution brief. It opens with the remaining wiki verification correction, then specifies bounded useful country-road shortcuts while preserving the complete G8 baseline. **G9 is proposed here; it has not been implemented.**

`G8_REVIEW.md` explains the assessment and next-stage decision. `seed-20261023-network-witness.png` and its SVG show a conservative, uninstalled route witness using exact retained coordinates. Its full-width graph distance falls from 23,625 to 6,303 steps; actual materialization and traversal remain G9 requirements.

## Included evidence

- `sources/`: exact uploaded/committed G8 completion report and the preceding G8 implementation brief.
- `evidence/focused/`: fresh unfiltered direct run, 215 passes and one Windows-only skip out of 216 discovered tests; environment, output and source preservation.
- `evidence/diagnostic/`: fresh ordinary plans, real-handler journey, scene/access evidence and explored-checkpoint measurements. All three complete plans match retained G8 plans exactly.
- `evidence/evidence-audit/`: independent source/retained-receipt/hash audit and exact newline reconstruction evidence.
- `evidence/network/`: independent centerline measures, conservative corridor search, unmodified-validator replay, figure generator and source-bound outputs.
- `evidence/wiki-authoring/`: independent input-collision probes, wiki portability/repeat-build/static-integrity results and their exact executed scripts.
- `evidence/review-summary.json`, `source-preservation.json` and `remote-recheck.json`: concise review facts, unchanged source and final remote identity.

`MANIFEST.json` inventories retained files with byte size, SHA-256 and CRC32. It excludes its own hash to avoid self-reference. The ZIP was checked against this inventory after creation.

## Reproduce the independent network analysis

Use the current game's dependency interpreter, the reviewed source/evidence and a new disposable output directory. These commands are examples; supply the actual existing checkout and extracted package locations. Do not reset owner work or create a second game development checkout merely to rerun review evidence.

```text
python evidence/network/measure_country_network.py \
  --repo "/path/to/existing/ResonanceRoguelike" \
  --output "/disposable/review/country-network-metrics.json"

python evidence/network/check_macro_corridors.py \
  --repo "/path/to/existing/ResonanceRoguelike" \
  --metrics "/disposable/review/country-network-metrics.json" \
  --output "/disposable/review/macro-corridor-witnesses.json"

python evidence/network/probe_augmentation_replay.py \
  --repo "/path/to/existing/ResonanceRoguelike" \
  --witnesses "/disposable/review/macro-corridor-witnesses.json" \
  --output "/disposable/review/augmentation-replay.json"
```

`evidence/run_review_command.py` takes explicit `--repo`, `--python`, `--evidence` and `--check focused|diagnostic-journey` arguments. It runs unchanged production check commands, captures finite timeout/environment/status and verifies tracked-file preservation. Full focused discovery takes several minutes.

The one-off audit/wiki probe scripts are retained exactly as executed, including their captured review workspace paths. Adapt their initial repository/output/interpreter path constants before reuse. The receipts preserve the actual original commands. The network scripts above and the review wrapper already accept portable path arguments. Markdown parsing for wiki build probes used the package's pinned `mistune==3.4.0` in a disposable dependency folder; no dependency folder is included here.

## Scope and omissions

The review preserved all 3,843 tracked files and performed no commits, remote writes or runtime/wiki fixes. Tests used disposable saves; the network route is an in-memory feasibility probe. The 10 Windows release gates were independently audited as retained evidence. Browser/production gates were not represented as freshly rerun in this Linux review.

Personal campaigns, dependency installations, browser profiles, duplicate repository source, disposable worker saves, maintenance-copy build intermediates, symlink fixtures and large successful authoring-preview payloads are excluded. Their relevant commands, hashes, outcomes and omission reasons remain in the receipts/inventory. The unavailable original G8 portable delivery archive was not independently audited; this is a new review handoff package.

Continue the owner's production-main/checkpoint/headless-verification workflow and maintain the wiki as part of G9, as specified in the execution brief. No PDF report is supplied.
