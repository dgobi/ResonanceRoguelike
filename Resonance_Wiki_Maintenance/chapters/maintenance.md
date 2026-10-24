# Keep this handbook accurate

This is edition **1.0**, audited on **24 October 2026** against `main` at `4d7a7892e1afffb8d872ed4a8fd442984d14e7d5`. It is a fixed, self-contained document. It does not contact GitHub in the background, and a newer repository push does not silently change the instructions you are reading.

## After a feature push

Return to this conversation with the feature/commit you want covered and request a wiki update. The revision in the header tells us the previous baseline. The companion source package preserves the authored chapters, interface, builder and source manifest so the next edition can be rebuilt and reviewed systematically.

A good update must:

1. Resolve the current repository HEAD and compare it with the audited source manifest.
2. Read changed guides and actual loaders/consumers, including changes to tests and examples.
3. Revise affected how-to pages, field references, source annotations and known limitations.
4. Recheck the examples and commands affected by the change. A wider gate is appropriate when the change crosses a core ownership/compatibility boundary.
5. Refresh the embedded document library, content catalogues and source fingerprints from the same revision.
6. Check internal links, search, keyboard behavior, layout and offline independence.
7. Record the new SHA, verification scope, edition date and a short owner-facing change log.

Updating only the header's date would make the document less trustworthy. The builder therefore refuses a different repository HEAD unless its audited-revision configuration has deliberately been updated after review.

## What the source package contains

| Part | Role |
|---|---|
| `chapters/` | The new, editable owner-facing Markdown chapters. |
| `build_wiki.py` | Collects current repository documents/data and renders the single HTML file. |
| `validate_wiki.py` | Checks HTML identifiers, internal links, search targets, embedded JSON and source coverage. |
| `theme.css` / `reader.js` | The local reading interface. |
| `wiki-config.json` | Edition identity, audited SHA, page ordering and labels. |
| `source-manifest.json` | Paths and SHA-256 fingerprints from this audited checkout. |
| `audit/` | Focused verification results and limitations for this edition. |
| `README.txt` | Rebuild and drift-check instructions. |
| `requirements-docs.txt` | Pins the Markdown renderer used for reproducible builds. |

The source package is for maintaining the handbook. It is not required to read the HTML. The game repository remains the authority for the game, and the original Markdown guides are preserved in the wiki's **Source library** with explicit status banners.

## Check drift before rebuilding

Run the included builder with `--check-drift --repo <repository-root>`. It compares the recorded paths/hashes and reports changed, missing and added files. This is a review aid, not an automated claim that the prose has become current. Asset-only edits can affect authoring instructions; test-only edits can affect verification; a changed source SHA without payload changes still requires the edition metadata to be considered deliberately.

The README gives exact rebuild commands using a separate documentation environment and the pinned Markdown renderer. Reading the completed HTML needs none of those tools.

## Read the evidence labels

| Label | Meaning |
|---|---|
| Current guide | Synthesized owner instructions checked against this source snapshot. Specific execution results are stated separately. |
| Source reference | An original repository document retained for traceability. Its banner explains scope and any important caveat. |
| Historical / mixed | Retained original wording that can contain superseded technical instructions. Prefer current guide pages for operational steps. |
| Design / proposal | Intent or proposed work; existence in prose is not implementation. |
| Snapshot data | Exact JSON from this revision, not an assertion that every declared field has an active consumer. |
| Executed check | A stated command/probe actually ran in the wiki audit, with its environment and bounded outcome. |

## Documentation method and comparable projects

The organization uses practical tutorials, task guides, reference material and system explanation, following the distinction described by [Diátaxis](https://diataxis.fr/start-here/). The complete definition → registration → appearance workflow draws on [Cataclysm: DDA's beginner mapgen guide](https://docs.cataclysmdda.org/JSON/JSON_Mapping_Guides/Guide_for_beginning_mapgen.html). Testing authored structures within their surrounding generated map follows the useful approach in [Dungeon Crawl Stone Soup's vault introduction](https://github.com/crawl/crawl/blob/master/crawl-ref/docs/develop/levels/introduction.txt).

Those projects inform the documentation method; their schemas and game rules have not been imported into Resonance. The local file design embeds assets and content because browsers can restrict cross-file requests under `file://`; see [MDN's explanation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS/Errors/CORSRequestNotHttp).

## Edition history

**1.0 · 24 October 2026:** Initial unified owner handbook for the G6 source. Added current setup, controls, save behavior, authoring workflows, data catalogues, source coverage, troubleshooting and update protocol. Retained the repository's original documents with scope annotations and resolved material contradictions in the current guide layer.
