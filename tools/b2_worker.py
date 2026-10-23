"""One source-bound, bounded B2 process; no desktop input."""
from pathlib import Path
import sys
import traceback
from b1_support import Evidence, boot, dump, read


def frozen(value):
    if isinstance(value, dict):
        return {str(k): frozen(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [frozen(v) for v in value]
    return value


class B2Evidence(Evidence):
    def check(self, case, name, expected, observed):
        expected, observed = frozen(expected), frozen(observed)
        # The preserved baseline is measured, never accepted as a repaired build.
        if self.job["flavor"] == "before":
            self.record["checks"].append(dict(case=case, property=name, expected=expected,
                                             observed=observed, passed=observed == expected))
        else:
            super().check(case, name, expected, observed)


def main():
    job = read(sys.argv[1])
    game, root = Path(job["game"]).resolve(), Path(job["run_root"]).resolve()
    assert game.is_relative_to(root) and (root / "disposable-b2.json").is_file()
    assert Path.cwd().resolve() == game
    sys.path.insert(0, str(game))
    ev = B2Evidence(job)
    try:
        if job["scenario"] == "journey":
            import config
            config.DEBUG_MODE = False
            from b2_journey import run_journey
            run_journey(ev)
        else:
            if job["scenario"] == "format":
                from b2_format_cases import run_case
            else:
                from b2_cases import run_case
            boot(lambda e: run_case(e, ev), ev)
        ev.bind_sources(game)
        ev.record["completed"] = True
    except BaseException as error:
        ev.record["error"] = repr(error)
        ev.record["traceback"] = traceback.format_exc()
    ev.record["assertion_count"] = len(ev.record["checks"])
    ev.record["passed"] = ev.record["completed"] and bool(ev.record["checks"]) and all(c["passed"] for c in ev.record["checks"])
    dump(job["result"], ev.record)
    print({k: ev.record.get(k) for k in ("scenario", "phase", "passed", "completed", "assertion_count", "error")})
    return 0 if ev.record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
