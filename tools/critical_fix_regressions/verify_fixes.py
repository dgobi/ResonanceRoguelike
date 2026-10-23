"""Run the focused corrections suite against an explicitly selected game checkout.

Uses the active Python environment and temporary test saves. Does not install
dependencies, modify game data, change Git state, or open existing campaigns.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path,
                        default=here.parents[1] / "roguelike")
    parser.add_argument("--evidence", type=Path,
                        help="Optional directory for the test log and loop evidence")
    args = parser.parse_args()
    game = args.game.resolve()
    if not (game / "main.py").is_file():
        parser.error("--game must point to the roguelike directory containing main.py")
    versions = {}
    for dependency in ("pygame", "tcod", "numpy"):
        try:
            versions[dependency] = importlib.metadata.version(dependency)
        except importlib.metadata.PackageNotFoundError:
            parser.error("Use the game's Python environment; missing " + dependency)
    with tempfile.TemporaryDirectory(prefix="resonance-fix-regressions-") as temp:
        evidence = args.evidence.resolve() if args.evidence else Path(temp) / "evidence"
        evidence.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env.update(RESONANCE_GAME_ROOT=str(game),
                   RESONANCE_TEST_TOOLS=str(here / "historical_tools"),
                   RESONANCE_TEST_EVIDENCE_DIR=str(evidence),
                   SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
                   PYGAME_HIDE_SUPPORT_PROMPT="1", PYTHONHASHSEED="20261020",
                   PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        search = [str(game), str(here / "tests")]
        if env.get("PYTHONPATH"):
            search.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(search)
        command = [sys.executable, "-m", "unittest", "discover", "-s",
                   str(here / "tests"), "-p", "test_*.py", "-v"]
        print(json.dumps({"game": str(game), "python": sys.version,
                          "dependencies": versions, "scope": "focused regressions"}, indent=2))
        try:
            result = subprocess.run(command, cwd=game, env=env, text=True,
                                    encoding="utf-8", capture_output=True, timeout=180)
        except subprocess.TimeoutExpired as error:
            print("Focused suite exceeded 180 seconds.", file=sys.stderr)
            return 2
        output = result.stdout + result.stderr
        print(output, end="")
        (evidence / "focused-tests.txt").write_text(output, encoding="utf-8")
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
