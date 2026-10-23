"""One bounded B1 worker, imported only from an explicitly copied game."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import traceback
from b1_support import Evidence, boot, dump, read


def main():
    job = read(sys.argv[1])
    game = Path(job["game"]).resolve()
    root = Path(job["run_root"]).resolve()
    assert game.is_relative_to(root) and (root / "disposable-b1.json").is_file()
    assert Path.cwd().resolve() == game
    sys.path.insert(0, str(game))
    # Setting imported config before Engine import changes this child only.
    import config
    if job["scenario"] == "journey" and job["variant"] in ("nondebug", "needs_f9"):
        config.DEBUG_MODE = False
    ev = Evidence(job)
    ev.record["evidence_class"] = "Actual main bootstrap and game API; Engine.run replaced only in API/component cases"
    try:
        if job["scenario"] == "journey":
            from b1_journey import run_journey
            run_journey(ev)
        else:
            if job["scenario"] == "format":
                from b1_format_cases import format_cases as callback
            elif job["scenario"] == "characterize":
                from b1_characterize import characterize as callback
            else:
                from b1_cases import run_case as callback
            boot(lambda e: callback(e, ev), ev)
        ev.bind_sources(game)
        ev.record["completed"] = True
    except BaseException as error:
        ev.record["error"] = repr(error)
        ev.record["traceback"] = traceback.format_exc()
    ev.record["assertion_count"] = len(ev.record["checks"])
    ev.record["passed"] = ev.record["completed"] and bool(ev.record["checks"]) and all(c["passed"] for c in ev.record["checks"])
    dump(job["result"], ev.record)
    print(json.dumps({k: ev.record.get(k) for k in ("run_id", "scenario", "phase", "passed", "assertion_count", "error")}))
    return 0 if ev.record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
