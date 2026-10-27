$ErrorActionPreference = 'Stop'
$workbenchRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $workbenchRoot 'worker\runtime\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Bundled runtime is missing. Run scripts/prepare-runtime.ps1 before building. No incomplete distribution will be produced.'
}
& $pythonPath -I -B -c "import sys, importlib.metadata as m; assert sys.version_info[:3]==(3,11,0); expected={'pygame':'2.6.1','tcod':'19.3.0','numpy':'2.4.6','cffi':'2.1.1','pycparser':'3.11','typing_extensions':'4.16.0'}; assert all(m.version(k)==v for k,v in expected.items()); import pygame,tcod,numpy,cffi; print('Complete pinned bundled runtime verified')"
if ($LASTEXITCODE -ne 0) { throw 'Bundled runtime or native dependency verification failed. Restore it with scripts/prepare-runtime.ps1.' }
