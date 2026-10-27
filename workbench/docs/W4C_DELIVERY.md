# W4C delivery — direct creatures in authored underground rooms

Verified 26 October 2026, America/Edmonton (27 October UTC).

Workbench **0.8.0** connects the existing W2 canvas and shared source draft to
G17 placement and actual actor construction. The owner can add, select, move and
delete direct creature records, inspect production errors, and publish/reopen one
new layout variant. Protocol remains **7**, game schema **g2-2**; the host checks
the new Workbench capability **direct-creatures-1**.

## Revision and preflight

- Baseline local `main`, `origin/main`, live remote `main`, and W4B's final evidence
  commit were all `7303e6151db7b841758f01c04c3920b79f9bbc3b`. W4B's earlier
  implementation was `6c6c99da288574e25866f2df5070aa53bc9657e6`; no intervening
  changes needed reconciliation. The only owner change was the untracked plan.
- Implementation: **7a76245505a20ea6196750ff17ea746d1eb17fa2**. This report, receipt, three native
  captures and controlled example form a separate evidence commit. Resolve it
  with `git log -1 --format=%H -- workbench/docs/W4C_DELIVERY.md`. The final handoff
  and ignored `.artifacts/w4c/final-publication.json` record the exact evidence and
  remote SHA after normal publication; a commit cannot contain its own SHA.
- Named checkpoints: `checkpoint/workbench-w4c-start-20261026-a` and
  `checkpoint/workbench-w4c-verified-20261026-a`. Work stayed in the production
  checkout on `main`, without a branch, worktree, reset or history rewrite.
- Read root guidance, owner brief/review and approved plan; project compass,
  state, proposal and workflow references; W4B README/report/receipt/capture;
  current launcher, host, worker, W2 and W4A code. The W4A native preflight passed
  in 76.737 seconds. W2 preflight exposed a harness race: disk polling correctly
  disabled review before the test clicked it. The corrected test opens the
  confirmation first, then makes the concurrent edit; apply still rejects it.
- The supported VBS launcher, bundled runtime, automatic source selection,
  close/restart, Change Project and saved alternate-project restart all passed
  offline smoke checks. Per-user settings were preserved; smoke tests used their
  own settings directories. No `release/deps` executable or runtime override was
  used for successful normal workflows.

## Source contracts and bounded implementation

The actual G17 guide is [docs/owner/GAMEPLAY_G17.md](../../docs/owner/GAMEPLAY_G17.md),
not the older brief's `roguelike/docs/owner` candidate. Its final-a release and
production evidence were inspected. Existing production APIs already expose the
needed receipts, so **no game code, game data or game-owned adapter changed**:

| Authority | API used or checked |
| --- | --- |
| `roguelike/generation/structure_contract.py` | `compile_structure`, `Validator.special`, authored-submap route rules |
| `roguelike/generation/spawn_specs.py` | Direct special identity and source-coordinate provenance |
| `roguelike/generation/structure_preview.py` | `preview`: compiler, controlled world/scene and actual population receipts |
| `roguelike/generation/local_gen.py` | `generate_submap`: production centering/translation and arrival |
| `roguelike/engine/scene_generation.py` | `create_submap`, `populate`: staged factories, complete batch occupancy and reserved arrival/stairs |
| `roguelike/engine/creature_factory.py` | `CreatureFactory.spawn`: actual `Actor`, components and creature terrain admission |
| `roguelike/engine/creature_authoring.py` | Existing W4A source catalogue/reference/factory boundary retained |
| `tools/structure_authoring.py` | Existing CLI/example/access contract retained |

The shared `LayoutCanvas`, `LayoutEditor`, span edits, `CanvasHistory`, `Authoring`
document and Rust reviewed-byte publisher are reused. Only direct creature ID
and integer source coordinates are graphical fields. Non-creature specials,
terrain, arrival and immutable metadata are retained. Overlapping records can
be selected by array index. Ordinary buildings retain painting without creature
placement controls. Unsupported/weighted/legacy sources and `starting_lab`
cannot promote themselves through raw edits. The palette uses unique loaded
non-player definitions admitted by the actual G17 validator.

Supported sources have a compiler-valid native string grid, declared player start,
dimensions at most the current 80×43 preview scene and only direct supported
specials. The exact G17 documentation example is allowlisted for reading and
in-memory drafting. Its original and sidecar remain read-only. A variant can
create only one safe new ID/file in the immediate `data/layouts` directory.
`decor_layer` is retained but labelled inactive because G17 does not consume it;
actual blocking decor/containers are visible in production context.

One bounded safety repair advances a host document revision and revokes its
review whenever shared-draft edits occur. A late validation cannot restore a
revoked review. Invalid raw text clears old evidence. Source, definition, sidecar
and dependency changes invalidate reviews; publication repeats real validation
under the existing containment, no-junction, dependency-lock, atomic no-clobber
and reopened-byte checks. No second writer or JSON export path was added.

The example's **saved** preview reads its original access sidecar and reports
that file's hash. Draft and new-file previews explicitly use the production
generated-arrival context, with no additional access targets. This single-file
scenario needs no new sidecar. Physical stairs and actual arrival still reserve
cells through production rules. Saving never changes world-selection references.

## Native result and actual actor evidence

[Controls and normal launcher](../README.md#place-a-creature-in-an-authored-underground-room)
describe the complete owner workflow. The final offline packaged journey passed
in **68.154 seconds** using a disposable data fixture, copied game source,
and exact example bytes enriched with CRLF and nested metadata for fidelity checks.
This fixture is not a Git checkout, so its worker correctly reports a null commit;
the implementation SHA and source/content hashes bind the run in the receipt.

The original direct marker moved from source `(7,2)` to `(6,2)`. Add/delete and
undo/redo returned exact source bytes. Invalid JSON froze mutation; a wall marker
at `(0,0)` produced `PRODUCTION_PLACEMENT`, a source-cell link and disabled apply.
The same session rejected a superseded job, changed sidecar, forged/revoked review,
source/definition conflict, destination race, unsafe path and layout junction.
It published `roguelike/data/layouts/w4c_guard_room.json`, reopened exact bytes,
closed/reopened the project, and reproduced actual actor construction.

| Observed field | Value |
| --- | --- |
| Input seed / scene seed | `20261023` / `207596318960738832600795127233809601945` |
| Scene address | `[0, 0, "preview-submap"]` |
| Source grid / scene | 11×7 / 80×43 |
| Measured origin / actual arrival | `(35,18)` / `(37,23)`; physical up stair at arrival |
| Special index / creature | `0` / `hollow_revenant` |
| Source cell → instantiated scene cell | `(6,2)` → `(41,20)` |
| Constructed class / count / HP | `Actor` / `1` / `14 of 14` |
| Published and reopened SHA-256 | `7be26e6ff9c4a0f0eaddde6e62664ece450297e2238fc97981f6048b16d93b4b` |
| Semantic creature-definition SHA-256 | `c0331811611da71f88d170e85f9b1cd76b99bce610189caf1cba21494de5f90e` |

These are actual `create_submap`/population/factory receipts, not actors appended
by the renderer. The retained [controlled example](examples/w4c_guard_room.json)
is evidence outside the active game catalogue; no owner layout variant was
installed or selected into a campaign. The [verification receipt](w4c-verification.json)
contains file hashes, dependencies, definition source hash and final runtime identity.

Native captures: [source markers](images/w4c/submap-source.png),
[instantiated actor](images/w4c/submap-instantiated.png), and
[1100×740 Problems view](images/w4c/minimum-problems.png). Final visual inspection
also clarified the footer so a saved-source success cannot imply an invalid draft
passed. Diagnostics remain readable by scrolling the inspector at minimum size.

## Verification

Commands below ran from `workbench` unless stated otherwise. Results are measured
on this workstation, not universal performance budgets. Detailed logs stay ignored;
their hashes and compact outcomes are retained in the receipt.

| Command / check | Result |
| --- | --- |
| `npm.cmd test` | 30 tests passed: span fidelity/history, raw freeze, rectangular corners, pan/zoom and DPI normalization, existing editor adapters |
| `npm.cmd run typecheck` | Passed |
| `cargo test --manifest-path src-tauri/Cargo.toml` | 23 passed, including interrupted/no-clobber publication, source entitlement, revision revocation and sidecar stamp |
| `cargo clippy --manifest-path src-tauri/Cargo.toml -- -D warnings` | Passed |
| `worker/runtime/python.exe -X utf8 -B -m unittest discover -s worker -p test_*.py -v` | 38 collected: 37 passed, 1 intentional embedded-runtime skip; 412.589 s |
| Development Python: `-m unittest test_bridge.BridgeTests.test_dependency_absence_structured -v`, from `worker` | The skipped dependency-absence case passed separately; 0.681 s |
| Relevant existing game tests, command below | 34 passed; 7.571 s |
| `npm.cmd run bundle` | Release app, complete bundled Python/bridge and 0.8.0 NSIS package built |
| `npm.cmd run test:submaps` | Final native W4C workflow passed; 68.154 s, no external requests, console errors or leaked worker roots |
| `npm.cmd run test:visual` | Existing W2 painting/pool/shared-writer journey passed; 55.526 s |
| `npm.cmd run test:creatures` | W4A references/factory, five parked editor drafts and variant journey passed; 92.962 s |
| `$env:WORKBENCH_STARTUP_SMOKE='1'; npm.cmd run test:startup` | Four VBS/restart/project-switch runs passed; 15.209 / 7.833 / 18.293 / 7.577 s |
| `WORKBENCH_TEST_MODE=submap-worker-cancel`, `submap-worker-exit`, `submap-worker-timeout`; `npm.cmd run test:desktop` | All passed; unsaved bytes retained, no verdict/review/apply, originals unchanged, no temporary roots. Actual timeout observed at 90.385 s |
| `worker/runtime/python.exe -B scripts/check-preservation.py`; `git diff --check` | Passed |

Fault runs deliberately use the excluded diagnostic fault-worker helper and
diagnostic runtime override; successful owner workflows use the bundled runtime.
Occupancy coverage includes walls, blocking decor/container later in the array,
water with/without actual swimming, arrival, physical stairs and actor overlap;
a legal corridor guard passes. Schema coverage includes missing/unknown/player
IDs, boolean/fractional/out-of-range coordinates, conflicting kind/type, weighted
alternatives, ordinary-building rejection, unsupported raw promotion and immutable
metadata/non-creature changes. Native DPI 1.5 and zoom/pan tested both grid corners.

The game command, from repository root, was:

```powershell
& 'workbench/worker/runtime/python.exe' -X utf8 -B -c "import os,sys,unittest;sys.path[:0]=['roguelike','tools','tools/critical_fix_regressions/tests'];os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1');unittest.main(module=None,argv=['unittest','test_structure_contract','test_structure_access','test_crafting','test_gameplay_g17','-v'])"
```

Development iterations corrected a test click outside the zoomed viewport and
module-search paths in the initial game-test invocation. Final native retesting
also caught an existing UI coupling: preview availability depended on an English
disabled-message string. It now receives an explicit capability boolean, so
clarifying the submap prompt cannot disable preview of a reopened variant.
A packaging attempt
while the timeout test held the executable hit Windows' file lock; packaging was
rerun after that test closed. None is counted as a passing verification. No game
contract changed, so historical full G17 release/persistence gates were not rerun
or claimed; the relevant current structure/access/crafting/G17 cases did run.

## Preservation and limits

The inherited pre-edit manifest checks **7,972 protected files and 7 personal-save
files**, including bytes, measured metadata and save membership: zero changes.
That manifest's historical baseline is `7745f72ea5446af22d3f340c30043d3752ef0f54`,
distinct from the W4C baseline above. A separate Git comparison against W4C's
actual baseline confirms unchanged tracked `roguelike` files and requirements;
their working-byte aggregate is retained in the receipt. The owner plan remains
untracked and byte-identical. Per-user project settings retain the same hash.
The wiki, historical examples/receipts, legacy CLI, campaigns and world selectors
were not edited. Binaries, disposable saves and large logs are not committed.

This proves controlled initial construction and safe single-file publication.
It does not prove natural campaign selection, combat/AI, balance, player FOV,
defeat persistence, clean-machine installation, signing or universal performance.
No terrain/decor painter for submaps, two-file authoring, rotation/mirroring,
groups/weights, behavior overrides or later Workbench milestone was added.
