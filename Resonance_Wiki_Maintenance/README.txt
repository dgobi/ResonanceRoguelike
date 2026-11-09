RESONANCE CREATOR'S HANDBOOK — GUIDE-1 / EDITION 2.0

Open Resonance_Owner_Wiki.html directly in a browser, without a server or network.
Choose Start creating for L01, I want to for a task, How Resonance works for the
system atlas, or Look something up for authoring limits. Search: / or Ctrl+K.
All lessons, hints, full answers, essential images and JSON downloads are local.
Theme and text-size preferences may use browser storage; course notes are your
own plain text file. Copy examples/guide1/notes.txt outside any disposable root.

Source reviewed: c166ec650b98156d53b8ea72e715c028d27db905 (SYS-5).
Later handbook delivery commits do not silently repin the reviewed game source.

EXERCISES
Use the existing Windows/Python 3.11 game environment. In PowerShell, at the
production repository root:
  $ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
  & $ResonancePython -X utf8 -B Resonance_Wiki_Maintenance/practice.py L01 --output evidence/my-guide
Replace that interpreter path if your environment is elsewhere. A fresh machine
needs the checked-out requirements-baseline.txt and game assets. This ZIP is not
a game/dependency distribution. If the unpacked handbook is outside the game,
invoke its practice.py by absolute path and add --repo <existing-production-root>.

Each run announces its captured payload and separate save root; it never writes
normal content or opens personal campaigns. --keep retains that exact temporary
root for inspection; --play opens the selected practice game for your own use.
Do not use retained payloads as development checkouts. Store intended drafts
elsewhere. Ordinary opening or rebuilding never installs the teaching patch.

MAINTENANCE

Build: python build_wiki.py --repo <production-root>
Validate: python validate_wiki.py --repo <production-root> --html Resonance_Owner_Wiki.html --report <evidence-path>.json
Drift: python build_wiki.py --repo <production-root> --check-drift

One-time setup from the repository root (network needed for this installation):
  $DocRoot = Join-Path $env:LOCALAPPDATA 'ResonanceAuthoring/GUIDE-1'
  New-Item -ItemType Directory -Force "$DocRoot/python","$DocRoot/browsers" | Out-Null
  & $ResonancePython -m pip install --target "$DocRoot/python" -r Resonance_Wiki_Maintenance/requirements-docs.txt
  $env:PYTHONPATH = "$DocRoot/python"
  $env:PLAYWRIGHT_BROWSERS_PATH = "$DocRoot/browsers"
  & $ResonancePython -m playwright install chromium firefox
This installs Mistune 3.4.0 and Playwright 1.56.0 outside the game packages.
The full serial check is verify_edition.py --evidence <new-output-directory>.
Browser verification needs the installed Chromium/Firefox Playwright binaries;
native Workbench verification additionally needs its built package and npm deps.
Use check_topics.py --repo <production-root> to locate potentially stale topics.
It does not approve a revision or rewrite prose. templates/lesson.md supplies a
small reusable pattern. Wiki upkeep is manual or separately commissioned.
Read chapters/maintenance.md for reviewed source, authoring and product scopes,
immutable links, edition updates and separate documentation delivery commits.
Original Linux edition-1.0 records remain in audit/ and audit/edition-1.0/.
Edition-1.3 metadata remains in audit/edition-1.3/. Current execution receipts
are under evidence/guide-1 in the checkout and portable bundle. Automation proves
bounded scenarios, not human comprehension, retention or a whole game campaign.
