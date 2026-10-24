# G8 authoring and wiki review

Reviewed repository: `dgobi/ResonanceRoguelike`, clean review checkout at `b94a0b0`.
This review changed no tracked game or wiki source. All executable probes used separate disposable drafts or a maintenance-only copy; no second game development checkout was created.

## Assessment

The prior destructive authoring-output defect is corrected. The wiki now contains substantive G7/G8 guidance, a usable standalone HTML reader, separate reviewed-source/authoring/product scopes, and repeatable builds that permit later documentation-only delivery commits. The former self-referential HEAD/manifests deadlock is gone.

A bounded follow-up remains: distinguish semantic freshness from original raw-byte capture consistently, and bind the complete wiki verification input set. This affects portability and evidence precision, not the ability to read the shipped wiki or run the current G8 game. Rebuilding a maintenance-only copy against the clean LF checkout succeeds immediately without changing its reviewed source revision.

## 1. Authoring corrections independently verified

Source: `tools/authoring_outputs.py:11–56`; `tools/structure_authoring.py:64–86,91–114,177–192`.

The CLI constructs a protected input set including compound recipes, all children, configuration/access/selection/layout inputs, check-only editor catalog and initializer sources. It protects resolved installed roots and existing hard-link identities. Known outputs are checked before preview work. Complete JSON, per-preview SVG, per-settlement/site SVG, catalog and initializer artifacts are staged and checked again before publishing. Initializers use exclusive creation and preserve existing drafts; deliberate catalog refresh remains supported.

Independent Linux probes in `probe_output_safety.py`:

| Case | Result | Preservation |
|---|---|---|
| JSON report aliases the compound recipe | Exit 1, conflict | Every input unchanged; no new artifacts |
| Initializer report aliases an existing child | Exit 1, conflict | Existing child preserved; no new artifacts |
| Plan SVG symlink targets the recipe | Exit 1, conflict | Target bytes preserved; no report |
| Dynamic scene SVG symlink targets the child, with simultaneous catalog refresh | Exit 1, conflict | Target bytes preserved; staged catalog never published |
| Distinct report/SVG destinations | Exit 0 | Valid complete preview; inputs unchanged |

The Linux symlink cases supplement the retained Windows hard-link coverage. They do not replace the root agent's normal focused discovery. See `collision-probes/matrix.json` and individual JSON receipts. The positive preview's large scene payload need not be included in the review package.

## 2. Wiki scope and current content are materially improved

- `wiki-config.json` pins full reviewed source `a708e0c62cbd0d39637ee57ac0502c13c1cad23a` and explicit scope covering game, tools, authoritative docs and root guides.
- `wiki_inputs.py:17–45` checks scoped paths, including additions/missing files, against committed blobs. It permits text CRLF/CR versus LF only and keeps binary content exact.
- `wiki_inputs.py:48–65` separately fingerprints wiki authoring inputs and generated HTML, excluding generated manifests/reports from their own authoring identity.
- `build_wiki.py:164–170` collects scoped source Markdown; it does not duplicate wiki chapters as original game documents.
- `AGENTS.md:17–23` now makes affected owner-guide/wiki upkeep a continuing delivery requirement.
- Main chapters cover format 6/wg8, explicit policy-version decoupling, compounds and parent/child counts, both settlement layouts, public/private/civic space, actual-country-road arrival, cardinal frontage, bounded required fitting, current saved-world behavior, installation/recovery and maintenance.
- The compiled reader rewrites ordinary guide source links to the immutable reviewed revision. Historical source documents retain their context. Raw chapter source links still contain some older SHAs; the compiled reader's current-guide links are pinned correctly.
- Existing world-generation/settlement-layout guidance does not claim strategic country routing is optimized. It explicitly leaves network optimization, organic cities, cross-chunk buildings and continuous rendering to future decisions.

Fresh static integrity after an isolated rebuild: zero errors; 33 main chapters plus 4 generated guide pages; 56 original source documents; 351 game JSON definitions; 18 repository examples plus 1 wiki example; 370 catalogue records; 463 search records; 540 internal links. No new reader/browser run was performed in this subtask.

## 3. Portability limitation reproduced

The documented read-only command on the unchanged LF checkout:

```text
python Resonance_Wiki_Maintenance/build_wiki.py --repo . --check-drift
```

exits 2 with `stale source build binding; review source and rebuild`.

All 761 source-scope files match the pinned revision's Git blobs under the declared newline policy. Of these, 291 differ only in recorded raw hash/byte count while canonical hashes and Git blobs match. The shipped HTML exactly matches its manifest: 5,282,014 bytes; SHA-256 `8adfc9a0216ac6ac8c5010cc9a0f1acde597120209eae24545326d24acf57f0c`.

Cause: `wiki_inputs.py:72` compares the complete `source` dictionary, including raw hashes and byte sizes, after `reviewed_inputs` already established canonical equality. Line 73 likewise compares raw-only wiki authoring identities. The 46 authoring entries reconcile as 22 exact, 23 uniformly CRLF, and one mixed-newline file (`chapters/code-and-documentation-map.md`: lines 1–87 LF, lines 88–91 CRLF). There is no substantive authoring-content mismatch in this comparison.

`probe_wiki_portability.py` copied only the maintenance package, installed its pinned `mistune==3.4.0` into a disposable dependency folder, and kept the game checkout read-only. Results:

1. Delivered-copy drift check: exit 2 as above.
2. Rebuild: exit 0, unchanged reviewed source SHA.
3. Drift: exit 0.
4. Integrity validation: exit 0, zero errors.
5. Second build: exit 0; HTML, source manifest and build report all byte-identical to first rebuilt outputs.
6. Second drift: exit 0.
7. Existing three synthetic contract tests: all pass, including later documentation-only commit and changed/missing/added source/product negatives.

The rebuilt HTML has SHA-256 `6af89da7cf6d353f42a20f5f2a472ee8bcd4491aa4b5eca7d2b2e04addcaa566`. It differs from the shipped HTML because the builder exposes checkout raw hashes and byte sizes. This is expected under its present representation; it is not evidence of changed gameplay source.

Relevant artifacts: `portable-drift.json`, `wiki-rebuild-probe.json`, `integrity-a.json`, `wiki-contract-tests.json`, `wiki-portability-conclusion.json` and the build/drift/validation logs.

### Related download/hash labeling

`build_wiki.py:182–188,219–225` reads text with newline normalization but displays raw file byte size/hash. `reader.js:55` downloads `new Blob([code.textContent], ...)`. For the shipped `deep_tongue.json` catalogue entry, the metadata says 102,885 bytes / SHA prefix `d231ff061a39`, while the embedded downloadable text encodes as 98,460 UTF-8 bytes / SHA `fc5d2d52d4e60dffa5353d3103f0e43d2f5e3ecd99cce0cc4aa8a830fe8ca6cf`. JSON values are equal. This was reconstructed from the delivered HTML with its own parser, not reported as a newly executed browser download. See `download-metadata.json`.

A consistent correction can either use canonical payload hashes/lengths for displayed/downloaded text or clearly distinguish original captured raw-source provenance from the normalized download. Static validator source-hash checks at `validate_wiki.py:294–300` must follow the same policy; changing only `check_products` will not finish the portability correction.

## 4. Verification-input binding omission

`verify_edition.py:18` executes `test_wiki_inputs.py`. That test file is absent from `wiki_inputs.py:49–52`'s authoring set. The root evidence auditor confirms it is also absent from all 704 unified runtime inputs; the wiki receipt's direct command-file binding captures `verify_edition.py`, not every transitive script. Consequently a change to the contract-test source alone does not invalidate the declared wiki input binding.

This does not show that tests failed or were modified. The current test source independently passes. It is a provenance/coverage gap to close before the next claimed frozen wiki release.

## Recommended opening correction for the next brief

1. Keep raw tested bytes/hashes as immutable capture provenance; compare semantic freshness through explicit text canonical hashes plus path/revision/scope, with binary bytes exact.
2. Add canonical wiki authoring identities and bind the complete transitive verification input set, including `test_wiki_inputs.py`, while keeping generated outputs outside their own input scope.
3. Make displayed/source/download hash and byte-size labels match their documented representation. Validate either canonical values or the retained exact build capture, not a different checkout's incidental newline convention.
4. Add a tiny synthetic fixture crossing LF, CRLF and mixed-newline representations; prove unchanged semantic source does not become stale, while substantive text edits, binary changes, missing/added files, verification-script changes and stale output still fail.
5. Preserve later documentation-only commit and repeated-build positives. Do not normalize the owner's repository wholesale, silently repin an unreviewed SHA, weaken drift guards, or treat a failed gate as passing.

For a strategic-network next arc, update world generation, settlement tuning/layouts, rural sites/compounds, saves/state, troubleshooting, code map and verification with the actual new route/arrival/attachment contracts and supported owner controls. Continue delivering the compiled offline HTML and editable maintenance package with explicit source/evidence scope.

## Packaging note

Retain this report, probe scripts, JSON receipts and small logs. Omit `docs-deps/`, `maintenance-copy/`, and bulky positive-preview scene artifacts: those are disposable reproduction intermediates, not new owner deliverables.
