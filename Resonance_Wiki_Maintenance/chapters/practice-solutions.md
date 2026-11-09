# Complete solutions and patch recovery

These are the **distributed worked answers**, not missing integration steps. L01–L09 use complete JSON in their pages and the [example catalogue](#catalog-examples). L10–L12 install the following module through the two-file patch. L13 combines those same answers; L14 uses the L01 rejection path to diagnose a broken capability. Each lesson explains the reasoning and an independent task. Read the lesson before opening the whole answer.

## Start any lesson independently

Open PowerShell in your existing Resonance checkout. Set `$ResonancePython` to its supported Python 3.11 interpreter, as explained in [Start creating](#learning-path). No extra development checkout is needed.

```powershell
& $ResonancePython -X utf8 -B Resonance_Wiki_Maintenance/practice.py L10 --output evidence/my-guide/L10
```

Replace `L10` with any `L01`–`L14`, or `all`. The output prints the lesson, current source revision, captured data root, separate save root and reset boundary. A nonzero exit means the expectation failed: read the lesson log and receipt. A passing run is evidence of that bounded scenario, not your independent solution.

`--keep` retains the printed temporary payload for inspection. `--play` opens only that captured game window for your own practice. Advanced manual play stages three perk points and four tools; press **K** and purchase **Practice cadence** / **Practice survey** before trying their behavior. **I** opens inventory. The exchange starts with an injured, hydrated player. This setup is controlled provisioning, not natural acquisition. Close the game to finish. No ordinary campaign is loaded.

For JSON variations, copy the complete answer to a draft file, retain the fixture ID, change the required behavior, then pass `--draft C:/path/my-candidate.json` to a single lesson. Only listed targets in `examples/guide1/draft-targets.json` accept overrides. A variation may intentionally fail the distributed answer's expectations; update the described observation, not the game to fit a test. If the ZIP was unpacked elsewhere, add `--repo G:/GameDev/RoguelikeProject` to the launcher. The reader itself needs no checkout.

The payload follows the Workbench's existing bounded runtime-fixture pattern: required Python/data/assets, no `.git`, no campaigns, no ongoing development copy. All new definitions are under this handbook's examples until copied into that payload. The fixed launcher is not a general Python service or editor. Workbench candidate staging ordinarily overlays **data**, not arbitrary Python; our patch is an explicit separate installation before `build_engine` or cold load.

## Full L10–L12 implementation

Read [L10](#L10), [L11](#L11) and [L12](#L12) for the parsing/result/application, dispatch and persistence decisions. The module installs only when explicitly imported by the supplied patch. An ordinary production start cannot discover this examples directory.

<details><summary>Reveal the complete tested implementation</summary>

<!-- PRACTICE_FILE: solutions.py -->

</details>

## Exact integration and expected diff

Baseline: `c166ec650b98156d53b8ea72e715c028d27db905`. Only these game paths change in the captured payload:

| Path | Expected change |
|---|---|
| `roguelike/engine/engine.py` | Append explicit import and `install()` call after existing class/module definitions |
| `roguelike/engine/guide1_practice.py` | New complete module equal to `solutions.py` |

The engine fingerprint treats CRLF and LF as equivalent for applicability; recovery restores **original exact bytes**, including line endings and existence. The solution and patch hashes are recorded in the launch receipt. JSON definitions live in `examples/guide1/data` and are staged separately; no production loot or starting kit is enrolled.

<details><summary>Reveal baseline fingerprints and complete installation patch</summary>

<!-- PRACTICE_FILE: patch-baseline.json -->

<!-- PRACTICE_FILE: installation.patch -->

</details>

### Dry check, deliberate installation, and recovery

For ordinary learning, use `practice.py`: it applies the patch only to its newly allocated payload. The following dry check is read-only and may point at your production checkout:

```powershell
& $ResonancePython -B Resonance_Wiki_Maintenance/examples/guide1/patch_guard.py check --root .
git apply --check Resonance_Wiki_Maintenance/examples/guide1/installation.patch
```

The guard refuses a changed engine, an already-existing lesson module, or an edited solution without a regenerated contract. A refusal preserves the files. It is a reason to compare the relevant source, not reset the checkout.

For a deliberate owner source experiment, first stop your own game/Workbench processes normally, inspect `git status`, and create a uniquely named checkpoint: `git tag checkpoint/before-my-lesson HEAD`. A Git tag covers committed work only. The guard additionally backs up the exact affected current bytes and original existence in a new recovery directory **before** writing. Keep that manifest until restoration is verified. Never overlap a temporary patch with another writer or an ordinary game process. Do not terminate someone else's process.

The explicit installation command is `patch_guard.py apply --root <chosen-root> --recovery <new-directory-outside-roguelike>`. Use the full interpreter/script prefix from the dry check. For captured practice the launcher performs this for you. For a deliberate production experiment, the owner must intentionally choose that root; opening/building the guide never installs anything. Run only with an explicit disposable save root established before engine construction (the supplied launcher demonstrates it). Do not start the ordinary campaign entry point with teaching code installed.

Wrap temporary manual installation and the bounded check in PowerShell `try { ... } finally { ... }`, placing `patch_guard.py restore --recovery <same-directory>` in `finally`. After interruption, reconcile that manifest before resuming work. Restore first checks **all** affected current fingerprints and backup hashes; it restores nothing if an intervening edit conflicts. On conflict, keep both versions, compare the manifest's original against the current file, and reconcile only those paths manually. Never use blanket `reset`, `clean`, or save deletion. A successful restore checks byte identity and removes only the known-new module. The manifest remains as evidence.

To discard routine practice, let the launcher remove only its newly allocated root, or delete the exact printed retained root after inspecting it. Keep your draft and notes outside that root. To **keep an intentional design**, restore temporary integration first, retain your proposed solution as a draft, and turn it into a separately reviewed production feature with its own authoritative guide, acquisition route, state contract and tests. Do not commit a temporarily installed teaching module or add it to normal loot by accident.

<details><summary>Reveal the complete backup, refusal and restoration guard</summary>

<!-- PRACTICE_FILE: patch_guard.py -->

</details>

## Changing the code requirement

Example: L11 asks for feedback every second paid phase. Change the modulo in `solutions.py`, inspect its diff, then explicitly regenerate the fixed patch:

```powershell
& $ResonancePython -B Resonance_Wiki_Maintenance/examples/guide1/rebuild_patch.py --repo . --accept-reviewed-solution
& $ResonancePython -X utf8 -B Resonance_Wiki_Maintenance/practice.py L11 --output evidence/my-guide/cadence-two
```

The generator checks the original engine fingerprint, compiles the edited solution, regenerates only the two-file patch and its solution hash, and never repins a changed engine. Review the changed expectation in `event_response`: the delivered script expects feedback at three; the variant must assert at two and absence at one. Do not remove the duplicate-registration, paid-phase, cold-load or cleanup checks. L12's duration variation similarly changes `SURVEY_PHASES`, remaining-work expectations and schema bounds together. This is intentional authored test adaptation, not automatic acceptance of arbitrary edits.

<!-- PRACTICE_FILE: rebuild_patch.py -->

## How the executable checks work

Most events call the production input handler in a bounded captured room, with exact physical objects and normal modal screens. L10 also posts key events to the game's own queue and runs the **original `Engine.run`**. No desktop keys are synthesized. World enrollment uses a generated plan and real surface/underground constructors, then stages arrival at the selected entrance; it does not claim an unassisted expedition from the starting city. Each cold check launches a new interpreter, installs the same lesson module before loading, compares serialized state and continues the relevant behavior.

The complete driver is provided for inspection and adaptation. Its controlled initial needs, supplies, perk points and target positioning are labeled. Saved actor/floor/work records are compared, and rendering must leave the snapshot unchanged. It is test orchestration around production code, not a replacement game loop.

<details><summary>Reveal the complete input, world-construction and cold-load driver</summary>

<!-- PRACTICE_FILE: lesson_runtime.py -->

</details>

Keep `examples/guide1/notes.txt` with your own prediction, observation, diagnosis and next independent task. Browser preferences are only theme/text size; no browser-only progress record can become your only copy of work.
