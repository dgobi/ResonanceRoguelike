# Resonance roguelike — owner entry point

B2 reconstructs saved components and their derived systems in the same isolated
copy, preserving accepted B1 scene/item identity guarantees. Read
[START_HERE](roguelike/docs/owner/START_HERE.md), the
[B2 field ledger](roguelike/docs/owner/B2_STATE.md), and
[verification](roguelike/docs/owner/B2_VERIFICATION.md).

From this root, run the enforced autonomous gate:

```powershell
.\.venv\Scripts\python.exe tools/verify_b2.py
```

It includes the complete B1 regression suite. All tests use disposable save roots,
headless processes and app-local game events. Final evidence is
[b2-results.json](evidence/b2-results.json). No routine verification is delegated
to the owner. The supported environment remains the existing Python 3.11.0 /
Pygame 2.6.1 / tcod 19.3.0 runtime with no added dependencies.

B2 starts from accepted B1 commit `9bb0db8` on branch `codex/b2-reconstruction`
in `G:\GameDev\RoguelikeBaseline-20261020\project`. The original project stays
separate and untouched. Accepted-work commits follow [AGENTS.md](AGENTS.md).
B1 and Arc A provenance remain in their dated evidence and owner handbook.

The development format remains v2 with explicit B2 extension records. Older B1
v2 synthetic saves are tested; no personal saves are used or migrated. Current
[remaining boundaries](roguelike/docs/owner/B2_DEFERRED.md) include B3 checkpoint
coherence/dirty flushing, C transfer ownership and UI text height. Recommend
[B3 next](roguelike/docs/owner/NEXT_ARC.md). Content, assets, normal controls and
creative decisions remain unchanged.
