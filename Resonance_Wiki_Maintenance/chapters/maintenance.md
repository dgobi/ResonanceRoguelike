# Maintain the owner handbook

The stable reader is `Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html`. Open it directly; no server is needed. Editable chapters, examples, theme and reader stay beside the builder. This is a reviewed edition, not automatic synchronization.

## Three input scopes

`wiki-config.json` pins a full immutable `commit` and explicit `source_scope`: game, tools, authoritative docs and root guides. Both builder and validator compare those scoped checkout inputs to that revision, including added and missing paths. Text may differ only by CRLF/CR versus LF; binary bytes are exact. The manifest also records raw bytes used. A later commit containing only wiki metadata/products preserves unchanged game-source binding.

Wiki authoring inputs are hashed separately: chapters, examples, illustrations, configuration, edition evidence, theme, reader, builder, validator, shared input checker, contract tests and every root Python/JavaScript/CSS helper. The source scope covers the game, authoring tools and their project-owned dependencies consumed by edition verification. Added, changed or missing inputs invalidate stale products. HTML, manifests, build/validation reports and historical audits are excluded from their own inputs. Dependency and browser versions belong in execution receipts, rather than inventories of installations. Wiki chapters are not duplicated in the original game-document library.

Schema 3 compares text freshness by canonical SHA-256 and byte size after CRLF/CR to LF only, with exact path membership, scope and pinned revision. BOM and trailing-newline changes remain substantive. Binary files remain exact. Raw capture hashes and sizes are retained unchanged as provenance; drift checks never rewrite files. LF, CRLF and mixed-newline equivalents pass for both source and wiki authoring inputs. Rebuild after upgrading an older manifest; the checker never silently repins it.

Catalogue downloads use UTF-8, LF newlines, no BOM, and preserve whether a trailing newline exists. Each record labels the full SHA-256 and size of that exact download separately from the original raw-source capture. The static validator checks both identities; Chromium and Firefox verification performs actual downloads and hashes their returned bytes.

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

**1.2, G8:** Two bounded settlement layouts, protected civic commons, actual-road frontage, format-6 resolution, current historical adapters, G7 compounds and real browser/download workflows. Main chapters, standalone HTML, three-scope build contract and headless reader verification are maintained together. The G8 owner report and evidence index provide source-bound game gates; historical audits remain unchanged.

**1.3, G9:** Portable raw/canonical/download identity repair, complete wiki verification input binding, bounded country connections and safe network authoring. Main generation, tuning, layout, rural/compound, save, troubleshooting, verification and code-map chapters cover the new format/settings and preserved baseline. Complete policy examples accompany the standalone reader. Genuine pre-edit G8 evidence and the final frozen G9 receipts are distinguished in the owner report; historical edition audits remain unchanged.
