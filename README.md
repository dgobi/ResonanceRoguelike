# Resonance roguelike — production main

Accepted Arc A, B1 and B2 are merged into `main` at `d179c08`. B3 implements
coherent checkpoint generations, inactive dirty-cache capture, interruption
recovery, previous-checkpoint rollback and slot-scoped deletion.

Read [START_HERE](roguelike/docs/owner/START_HERE.md),
[B3_STATE](roguelike/docs/owner/B3_STATE.md),
[B3_VERIFICATION](roguelike/docs/owner/B3_VERIFICATION.md), and
[B3_DEFERRED](roguelike/docs/owner/B3_DEFERRED.md).

Run the complete autonomous gate from this production root:

```powershell
& 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe' tools/verify_b3.py
```

The existing Python environment is reused; all game code runs directly from this
checkout. Tests use disposable save roots, headless processes and app-local game
events. No desktop control, new source checkout or owner verification is required.
Final evidence: [b3-results.json](evidence/b3-results.json) and
[b3-summary.json](evidence/b3-summary.json).

Work stays on `main` with named Git checkpoints and local commits, as recorded in
[AGENTS.md](AGENTS.md). The historical isolated copy and accepted B1/B2 evidence
remain available. No push is implied. Content, assets and personal saves are
preserved. Flat legacy v2 saves are loadable but read-only; no implicit migration
occurs. Generation/session history is retained until slot retirement.

The equipped-drop and text-height issues remain separate. Recommend C next for
transfer ownership. Historical copy-based verification drivers are retained for
provenance; use the B3 gate for this main-only workflow.
