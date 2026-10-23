"""Run the unchanged historical diagnostic entry with bounded child processes.

Only subprocess deadlines are supplied; game behavior and assertions are original.
"""
import runpy
import subprocess
import sys
from pathlib import Path

original_run = subprocess.run


def bounded_run(*args, **kwargs):
    kwargs["timeout"] = min(kwargs.get("timeout", 30), 30)
    return original_run(*args, **kwargs)


if __name__ == "__main__":
    script = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(script.parent))
    sys.argv = [str(script), *sys.argv[2:]]
    subprocess.run = bounded_run
    try:
        runpy.run_path(str(script), run_name="__main__")
    finally:
        subprocess.run = original_run
