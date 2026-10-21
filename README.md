# Roguelike: owner entry point

This is the existing dark medieval, post-apocalypse roguelike. Arc A adds a disposable development recipe, orientation and diagnostic evidence. It changes no gameplay code or content.

Start with [the owner launch guide](roguelike/docs/owner/START_HERE.md). Then read the [runtime map](roguelike/docs/owner/RUNTIME_MAP.md), [world and state](roguelike/docs/owner/WORLD_AND_STATE.md), [content routes](roguelike/docs/owner/CONTENT_ROUTES.md), and [Crow Jerky lesson](roguelike/docs/owner/OWNER_LESSON.md).

[Implementation status and documentation authority](roguelike/docs/owner/STATUS.md) separate observed behavior, source-supported behavior and creative intent. [Owner decisions](roguelike/docs/owner/DECISIONS.md) remain open. [Evidence and remaining manual checks](roguelike/docs/owner/OBSERVATIONS.md) state the limits of this baseline. [The next repair brief](roguelike/docs/owner/NEXT_ARC.md) is limited to persistence identity and explicit replacement.

Baseline: original `main` at `9e1f32328a19aec88e818f552b7a4e36fcbb027f`, **plus all 188 dirty/untracked paths**, not HEAD alone. All 503 exported project files matched the independent review. See [provenance](evidence/PROVENANCE.md). The independent development copy has its own baseline commit `863bc5f`; it is not an upstream commit.

Use `.venv` and `tools/baseline.py`; do not launch experiments from the original project's save directory. Historical documents are retained and labeled. Their self-described authority does not approve conflicting design choices.
