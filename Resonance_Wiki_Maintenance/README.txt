RESONANCE OWNER WIKI - READING AND MAINTENANCE
============================================

Audited edition: 1.0 / G6 / 24 October 2026
Repository: https://github.com/dgobi/ResonanceRoguelike
Reviewed HEAD: 4d7a7892e1afffb8d872ed4a8fd442984d14e7d5

READ THE HANDBOOK

Download Resonance_Owner_Wiki.html and double-click it to open it in your
browser. The document contains its content, styles, search index and figures.
No server, Python installation or game installation is needed to read it.
Only external links you choose to open require an internet connection.

Resonance_Wiki_Maintenance.zip is the separate editable source package. It is
not required for reading. This is a fixed, reviewed edition, not an automatic
GitHub-sync app. Later game pushes do not update the existing HTML.

WHAT IS IN THE SOURCE PACKAGE

  chapters/                 Editable owner-facing Markdown guides.
  wiki-config.json          Reviewed commit, date, milestone, edition and
                            chapter/navigation configuration.
  build_wiki.py             Collects the supplied repository's documents/data
                            and renders one self-contained HTML document.
  theme.css / reader.js     The embedded reading interface.
  source-manifest.json      Tracked source paths and SHA-256 fingerprints for
                            detecting changes since the reviewed snapshot.
  validate_wiki.py          Structural/content-coverage integrity checks.
  requirements-docs.txt     Pinned documentation-only Markdown dependency.
  examples/                 Complete authoring examples for the handbook.
  illustrations/            Included diagnostic illustration assets.
  audit/                    Recorded focused checks, findings and limitations.
  build-report.json         Last build's counts, hashes and link handling.

Game source is not bundled. Supply your own Git checkout to rebuild; the
builder reads it without editing game files. Git must be available on PATH.
Use Python 3.11 or 3.12 for the commands below. Rebuilding the documentation
does not require installing the game's requirements.

REBUILD THE SAME REVIEWED EDITION

Extract the maintenance ZIP. Open a terminal in the directory containing
build_wiki.py. Replace the example repository path with your checkout's root
(the directory containing .git and roguelike/). Keep the output path quoted.
The separate environment below needs no activation.

Windows PowerShell:

  $Repo = 'C:\GameDev\ResonanceRoguelike'
  $Out = Join-Path $PWD 'Resonance_Owner_Wiki.html'
  py -3.11 -m venv .docs-venv
  $DocsPython = Join-Path $PWD '.docs-venv\Scripts\python.exe'
  & $DocsPython -m pip install -r requirements-docs.txt
  & $DocsPython build_wiki.py --repo "$Repo" --check-drift
  & $DocsPython build_wiki.py --repo "$Repo" --output "$Out"
  & $DocsPython validate_wiki.py --html "$Out" --repo "$Repo" --report audit/html-integrity.json

Unix/macOS shell:

  repo='/path/to/ResonanceRoguelike'
  out="$PWD/Resonance_Owner_Wiki.html"
  python3 -m venv .docs-venv
  .docs-venv/bin/python -m pip install -r requirements-docs.txt
  .docs-venv/bin/python build_wiki.py --repo "$repo" --check-drift
  .docs-venv/bin/python build_wiki.py --repo "$repo" --output "$out"
  .docs-venv/bin/python validate_wiki.py --html "$out" --repo "$repo" --report audit/html-integrity.json

Run the commands one at a time and inspect each result. Dependency installation
may need internet access; subsequent builds use local files. Reuse the created
environment on later runs. A build replaces the chosen output HTML and updates
the build report, so retain an older delivered edition before overwriting it.

The drift check prints changed, added and missing tracked paths and compares
HEAD. Exit 0 means no detected drift; exit 2 means drift was found (or a command
input error, which the error text identifies). It does not rebuild or change
the manifest. Investigate differences before treating the prose as current.
Fingerprints are raw bytes; checkout line endings can affect them.

A normal build refuses a HEAD different from wiki-config.json and refuses
dirty tracked repository files. It does not bypass those guards or fetch a
different revision. Do not discard your game work to satisfy them: use the
reviewed clean revision after the relevant source changes have been committed.
Untracked game files are not part of the tracked source snapshot.

The validator returns 0 for a pass, 1 for findings, and 2 for an input failure.
Read its JSON report. A structural pass does not establish gameplay correctness
or visual quality. Open the rebuilt HTML and check navigation, search and layout.

UPDATE AFTER A FEATURE PUSH

1. Preserve the previous HTML, source package and evidence. Run --check-drift
   against the intended new repository revision and inspect the reported paths.
2. Review changed guides, definitions, actual loaders/consumers, tests and
   evidence. Distinguish implemented behavior from proposals and inactive fields.
3. Update affected chapters, examples, source links and status annotations.
   Review the builder's generated coverage/edition text if its assumptions or
   evidence have changed. A fresh catalogue alone cannot update authored prose.
4. Run focused checks for the changed workflows; record revision, environment,
   command, seed, outcome and limitations under audit/. Run broader game gates
   only when the change's scope or project requirements call for them.
5. Deliberately update wiki-config.json: commit, date, date_label, milestone and
   edition, plus chapter configuration where needed. Update the edition history.
   Merely changing the SHA or date is not a completed documentation review.
6. Only after that review, refresh the source manifest while building:

   PowerShell (using the variables above):
     & $DocsPython build_wiki.py --repo "$Repo" --output "$Out" --write-manifest

   Unix/macOS (using the variables above):
     .docs-venv/bin/python build_wiki.py --repo "$repo" --output "$out" --write-manifest

7. Run the validator and --check-drift again, inspect build-report.json, and
   check the HTML in a browser. Retain any unresolved findings with their scope.
   Package the reviewed source and HTML together as the next edition.

Do not use --write-manifest merely to silence drift. It replaces the baseline
used by subsequent comparisons. The builder also creates a manifest if it is
absent, so keep the supplied one until the review is complete. Validation is a
separate command; a successful build is not a validator result.

EVIDENCE SCOPE AND KNOWN FINDINGS

Read the HTML's Coverage & audit page and audit/ for the full record. This
edition used focused Linux / CPython 3.12.14 probes, including startup,
loaders/factories, selected structure scenes/transforms, WFC and asset loading.
These are not a new full production/release gate, a Windows keyboard test or
a complete playthrough. Original repository evidence retains its own scope.

The generated editor catalogue freshness check failed on the untouched clone:
compared semantic sections and the contract hash matched, while raw identity
differed. The exact cause was not established. The game catalogue was not
rewritten to conceal the result. The asset probe also recorded the wall_pillar
Urizen crop mismatch and ignored top-level vine entries. Current guide chapters
explain their practical consequences and other reproduced limitations.

The validator checks the generated handbook, not the game. Review failures and
warnings rather than deleting them or relabelling historical evidence as new.
Return to the original chat with the new feature/commit when requesting the
next reviewed edition.
