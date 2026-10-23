# Resonance roguelike — owner entry point

B1 repairs development save/load identity and explicit replacement in the existing
isolated copy. Read [START_HERE](roguelike/docs/owner/START_HERE.md),
[world and state](roguelike/docs/owner/WORLD_AND_STATE.md),
[the v2 format](roguelike/docs/owner/B1_FORMAT.md), and
[verification](roguelike/docs/owner/B1_VERIFICATION.md).

From this root, the enforced autonomous command is:

```powershell
.\.venv\Scripts\python.exe tools/verify_b1.py
```

It uses only disposable sessions, headless SDL, subprocesses and app-local game
events. Final evidence: [b1-results.json](evidence/b1-results.json).
Known unrelated defects: [B1_DEFERRED](roguelike/docs/owner/B1_DEFERRED.md).
Next recommendation: [B2](roguelike/docs/owner/NEXT_ARC.md). No mandatory manual
verification or personal-save migration is required or provided.

The starting point is the complete preserved working copy plus Arc A commit
`1b9531b`, not original HEAD alone. [Arc A provenance](evidence/PROVENANCE.md)
retains that history. B1 uses branch `codex/b1-persistence` in
`G:\GameDev\RoguelikeBaseline-20261020\project`; your original project stays
separate. The owner requested a separate commit of its pre-existing work and a
persistent accepted-work commit preference; these are recorded in its preservation
commit and [AGENTS.md](AGENTS.md).

The existing dark medieval setting, content and assets are unchanged. Broader
Needs/hooks/timers remain B2; coherent checkpoints and failure recovery remain B3.
Creative decisions stay in the [owner decision register](roguelike/docs/owner/DECISIONS.md).
