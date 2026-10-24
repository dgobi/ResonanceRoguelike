# Independent G8 evidence and runtime-contract audit

Reviewed repository: `b94a0b0db3685f7484632701f0486f3b0b79101e`.
Frozen final inputs: `14c98afc38c659c9195b11c6b396fb82544ff03b`.
This is a read-only source/retained-evidence audit, not a fresh execution of the Windows gates. Root is separately running fresh Linux verification.

## Evidence result

The uploaded `Pasted text(6).txt` is byte-identical to `docs/owner/WORLDGEN_G8.md`: 13,185 bytes, SHA256 `03ec0df4de4d64b07bc4f217f16d085a0c96790b85bd056b29ae925fc344e459`.

All 704 paths in the final unified input manifest have the exact same Git blobs at frozen input and current HEAD, and the local checkout matches those blobs. Original tested Windows representations reconcile as 441 exact byte matches and 263 uniform newline-only reconstructions. There are zero other source differences. This manifest does not include the separate wiki package; that has its own binding discussed below.

All ten `final-b` gate receipts bind the same input commit, source map and complete detailed input manifest. All report exit 0, no timeout, stable source and reconciled committed inputs. Their index hashes reconstruct exactly from retained text with uniform newline conversion. Gates: guard, focused, browser, authoring, catalog, catalog-check, diagnostic, visuals, wiki, production.

Independently checked 1,022 retained output entries against raw recorded size/hash: 444 exact and 578 exactly reconstructable with uniform newlines; zero other mismatches. All 2,163 omitted output entries are within disposable `/saves/` paths: 67 guard entries and 2,096 production entries. This agrees with the report's declared omission of worker saves. No omission was silently counted as a verified file.

The final focused raw log says `Ran 216 tests in 466.800s` and `OK`. The parent receipt records no inherited PYTHONPATH; `tools/g8_clean_focused.py:13–17` removes it, and `tools/critical_fix_regressions/verify_fixes.py:48–51` explicitly passes the tools directory to its test child. The original G7 direct-run import defect is corrected.

The two final browser records each have 42 checks, no errors and 129 codec documents. The production record is unfiltered (`only` and `case` null), with 3,675 passed checks, 159 workers, 74 coverage groups and seven runner negative controls.

The failed first final attempt is preserved honestly: six gates passed, then `final-a/diagnostic/output.txt` records a syntax error in the comparison-report expression. The failure is not substituted for a pass. Commit `a708e0c` repaired the expression; `final-b` is a complete ten-gate rerun on the later immutable input commit.

The authentic G7 fixture ZIP is identical in all retained copies and the production test fixture: SHA256 `d33a2a8bffbacbe9625f76c2369c613467ed83c31204b0290baeaeba646ab2c7`, 1,569,006 bytes, eight members, no CRC errors or duplicate entries. Every payload agrees with both its checkpoint manifest and witness inventory. The saved plan is format5 / `wg7`, identity `17e968b99d8b65e0a8634f7c46b4a9d8018b3a713d834afba53bdae23411b948`, creator commit `8e56d36`; visited town [75,99], pending town [75,100], explored compound [74,34], pending rural [81,34]. Runtime restoration claims are supported by retained focused evidence; root's fresh run provides an independent execution.

The standalone portable G8 review archive/publication receipt mentioned by the completion report is not in the repository or supplied attachments. This audit does not claim an independent member/inventory/readback verification of that separate archive. The retained authentic compatibility ZIPs were checked as stated above.

## Inspected runtime contracts

No new critical runtime defect was found in the inspected default/composed paths. That conclusion is scoped to source inspection plus retained focused evidence, not an exhaustive proof of arbitrary edited configurations.

- `roguelike/generation/settlement_layout.py:129–184`: actual road bands and public/civic obstacles precede free-block subdivision; plot IDs derive from stable geometry; ordered placement uses the actual incoming-route entry.
- `settlement_layout.py:187–214`: each alternative stages routes/blocks/common and role fitting; alternatives share one actual required-transform trial budget. Generation errors distinguish exhausted budget from exhausted enumerated alternatives.
- `settlement_layout.py:217–282`: reciprocal block/lot/common ownership, fixed member dimensions, complete doorway projection, common circulation, exact free-space partition and route ownership are replayed without consulting current recipes.
- `roguelike/generation/world_plan.py:421–516`: validated registries, current layout replay, exact reservation multiset and restricted permission replay work together; common geometry is not a generic overlap exemption.
- `roguelike/generation/planned_scene.py:20–26,56–61,81–125,151–190`: affected pending public-surface dependency checks; painting/protection; populated common, roads, approaches and goals; native civic semantics and final content ownership.
- `tools/critical_fix_regressions/tests/test_generation_g8_layout.py:40–115`: three ordinary seed plans, all settlement members, horizontal/vertical occupancy, both controlled layouts with all cardinal directions, 20 normal/road-width fixtures and five layout/POI policy combinations.
- `tools/critical_fix_regressions/tests/test_generation_g8_lifecycle.py:31–49`: real pre-G8 checkpoint with original visited provenance and explicit pending adapter.
- The same lifecycle file's remaining tests: staged late failure after common/building work, recipe removal, affected-only terrain dependency change, checksum-consistent bad ownership/geometry/provenance, ordinary native updates, reverse member visits and explored checkpoint restore.

## Wiki binding qualifications

The wiki manifest contains 46 authoring inputs, separately from the 704 unified runtime inputs. Their current content reconciles exactly by newline representation: 22 raw exact; 23 uniform CRLF reconstructions; one mixed reconstruction. For `chapters/code-and-documentation-map.md`, retain LF for lines1–87 and convert only lines88–91 to CRLF; the resulting 11,830-byte file has the exact recorded SHA256 `f88e5d6668c14117a24dee5bc0f087d5fe61ac2593cf79b66a95f340ecd2eae5`. The raw reconstruction is retained beside this report. No semantic source discrepancy is implied by those newline differences.

The wiki agent independently found the delivered raw comparison rejects an ordinary LF checkout despite the declared canonical source policy; use that agent's reproduction and portability findings for the corrective brief.

`Resonance_Wiki_Maintenance/test_wiki_inputs.py` is absent from both the unified runtime input manifest and the wiki authoring manifest, although bound `verify_edition.py` invokes it. Add the contract test to the relevant test-input scope; the tested checker should be source-bound too. This is an evidence-maintenance correction, not evidence that the tests failed.

## Forward-compatibility traps for a network G9

A plan version bump needs deliberate dispatch changes. Format6-specific checks currently occur in `world_plan.py` (registry creation, layout replay, common reservation admission, public-space slicing), `planned_scene.py:135` (public-space provenance), and `save_manager.py:385` (public-space provenance validation). Preserve G8 public-space behavior in any new network plan contract and retain exact historical saved plans. Do not let `version == 6` fall through when introducing format7.

Country-routing graph changes also affect the meaning of incoming/assigned streets. `settlement_layout.py:148,231` looks up a country route whose `b` equals the settlement; roadside assigned frontage may use a different outgoing route. Define actual arrival and assigned geometry explicitly when a settlement can have multiple country connections. Preserve the distinction and test it.

`planned_scene.py:186–190` requires all road cells in one local chunk to form one usable connected component. A globally connected new network can still violate this if two local arms require leaving/re-entering the chunk to join. New routing must retain this local realization invariant or explicitly redesign and test the materializer contract; a graph-connectivity metric alone cannot prove it.

Keep unchanged upstream anchor placement separate from graph selection. `world_plan.py:163–190` establishes near-start first settlement, indexed forms and capital gateway; changing destination ordering for a network optimization must not silently change those choices.
