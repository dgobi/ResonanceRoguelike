AUDIT RECORDS - WIKI EDITION 1.0 / G6

All game findings refer to commit
4d7a7892e1afffb8d872ed4a8fd442984d14e7d5.

startup-smoke.txt          Actual disposable-launcher headless startup output.
content_checks.json        33 focused content/factory/consumer check results.
content_discrepancies.json Source-backed current-vs-old-guide discrepancies.
asset-probe.json           Sprite/tile geometry and loading observations.
core-review.json           Independent editorial/command/source review.
browser-review.json        Actual handbook UI checks and their limitations.
html-integrity.json        Reusable validator result for the delivered HTML.
html-integrity-negative-checks.json
                          Deliberately damaged temporary-copy check proving
                          that the validator detects expected error classes.
world/                     Structure catalogue, scene and transform JSON
                           reports; summary in wiki-authoring-checks.json.

These results have intentionally bounded scope. They are not a fresh full
release/production gate. See Coverage & audit in the HTML for the interpreted
results, including the editor-catalogue freshness failure on the unchanged
checkout. The game was not changed to make a check pass.

Some recorded paths identify the temporary audit workspace or original
runtime output locations. They are provenance, not required local paths on
your PC. The reusable HTML validator and build commands are argument driven.
Preserve this edition's evidence when producing a later edition; label new
checks with their own source revision, environment, seed and actual outcome.
