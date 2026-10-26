"""Sample the real bundled worker, with Windows process memory counters."""
import concurrent.futures
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "workbench/src-tauri/target/release"

class Counters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
        (key, ctypes.c_size_t) for key in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
                                          "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]

api = ctypes.WinDLL("psapi").GetProcessMemoryInfo
api.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
rows = []
for n in range(3):
    start = time.perf_counter()
    process = subprocess.Popen([str(RELEASE / "python/python.exe"), "-I", "-B", "-u", str(RELEASE / "bridge.py"), "--root", str(ROOT)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000)
    request = json.dumps({"id": f"measure-{n}", "protocol": 1, "op": "preview", "asset": "roguelike/data/layouts/starting_lab.json", "seed": 20261023}).encode() + b"\n"
    peak_ws = peak_private = 0
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = executor.submit(process.communicate, request)
        while not result.done():
            counters = Counters(); counters.cb = ctypes.sizeof(counters)
            if api(int(process._handle), ctypes.byref(counters), counters.cb):
                peak_ws = max(peak_ws, counters.PeakWorkingSetSize)
                peak_private = max(peak_private, counters.PrivateUsage)
            time.sleep(.01)
        stdout, stderr = result.result()
    response = json.loads(stdout)
    assert process.returncode == 0 and response["ok"], stderr
    r = response["result"]
    rows.append({"wall_ms": round((time.perf_counter() - start) * 1000, 2), "worker_ms": response["elapsed_ms"],
                 "generation_ms": r["elapsed_ms"], "peak_working_set_bytes": peak_ws, "sampled_peak_private_bytes": peak_private,
                 "terrain_sha256": r["terrain_sha256"]})
output = ROOT / "workbench/.artifacts/worker-performance.json"
output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
print(json.dumps(rows, indent=2))
