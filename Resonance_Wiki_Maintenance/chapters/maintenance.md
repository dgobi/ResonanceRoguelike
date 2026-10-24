# Maintain the owner handbook

The stable reader is `Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html`. Open it directly; no server is needed. Editable chapters, examples, theme and reader stay beside the builder. This is a reviewed edition, not automatic synchronization.

## Three input scopes

`wiki-config.json` pins a full immutable `commit` and explicit `source_scope`: game, tools, authoritative docs and root guides. Both builder and validator compare those scoped checkout inputs to that revision, including added and missing paths. Text may differ only by CRLF/CR versus LF; binary bytes are exact. The manifest also records raw bytes used. A later commit containing only wiki metadata/products preserves unchanged game-source binding.

Wiki authoring inputs are hashed separately: chapters, examples, illustrations, configuration, edition evidence, theme, reader, builder, validator and shared input checker. Changed or missing inputs invalidate stale products. HTML, manifests, build/validation reports and audits are excluded from their own inputs. Wiki chapters are not duplicated in the original game-document library.

`source-manifest.json` records source revision, exact authoring inputs, output hashes and documentation HEAD at build time. Subsequent product-only delivery commits may differ. Current guide/source links pin the reviewed source; original historical text retains its context.

## Repeatable update sequence

1. Preserve previous editions and review affected source and workflow evidence. Commit intended game and authoritative-guide inputs, preserving unrelated work.
2. Update affected chapters/examples and `edition-evidence.json`. Distinguish newly executed checks from historical evidence.
3. Deliberately set reviewed source and edition metadata. Changing a SHA alone is not review.
4. Build, validate and inspect the real reader. Repeat unchanged build/drift checks. Commit wiki delivery separately.

```powershell
$env:PYTHONPATH = "$env:LOCALAPPDATA/ResonanceAuthoring/python"
& $ResonancePython -X utf8 Resonance_Wiki_Maintenance/build_wiki.py --repo .
& $ResonancePython -X utf8 Resonance_Wiki_Maintenance/validate_wiki.py --repo . --html Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html --report evidence/wiki-integrity.json
& $ResonancePython -X utf8 Resonance_Wiki_Maintenance/build_wiki.py --repo . --check-drift
```

Install the pinned documentation-only `mistune` dependency from `requirements-docs.txt` outside the game environment. `--write-manifest` remains a compatibility spelling and cannot bypass source verification. Every successful build binds its inputs/products. A build alone does not certify browser behavior or gameplay.

A feature affecting owner workflows must update authoritative guides and wiki chapters/examples, rebuild and validate, and record source/evidence. Record a scoped no-handbook-impact conclusion when appropriate. This is a delivery rule, not a scheduled task.

## Edition history

**1.0, 24 October 2026:** Original G6 handbook and Linux audit. Dated configuration, manifest, build report and README remain under `audit/edition-1.0/`; original probe outputs remain in `audit/`. Their raw catalogue drift finding and inspection limits remain historical.

**1.1 integration, 24 October 2026:** Shared source/authoring/product contract and G7 compound catch-up. Final G8 metadata will record completed feature/release scope.
