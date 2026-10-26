param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$workbenchRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $workbenchRoot 'worker\runtime'
$artifactsRoot = Join-Path $workbenchRoot '.artifacts'
New-Item -ItemType Directory -Force $artifactsRoot | Out-Null
$archivePath = Join-Path $artifactsRoot 'python-3.11.0-embed-amd64.zip'
$archiveSha = '68FB03784E8545C35BCB5F240B696E6E676CA3E5FB90926ED0673D564299FB94'
if (-not (Test-Path -LiteralPath $archivePath)) {
    Invoke-WebRequest 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-embed-amd64.zip' -OutFile $archivePath
}
if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash -ne $archiveSha) { throw 'CPython archive SHA-256 mismatch' }
if (Test-Path -LiteralPath (Join-Path $runtimeRoot 'python.exe')) {
    Write-Output 'Runtime exists; verifying the pinned versions without replacing it.'
} else {
    Expand-Archive -LiteralPath $archivePath -DestinationPath $runtimeRoot
}
$sitePackages = Join-Path $runtimeRoot 'Lib\site-packages'
if (-not (Test-Path -LiteralPath $sitePackages)) {
    & $Python -m pip install --only-binary=:all: --no-compile --require-hashes --target $sitePackages -r (Join-Path $workbenchRoot 'worker\requirements.lock')
    if ($LASTEXITCODE -ne 0) { throw 'Pinned dependency installation failed. Inspect the runtime directory before retrying.' }
}
Set-Content -LiteralPath (Join-Path $runtimeRoot 'python311._pth') -Encoding ascii -Value "python311.zip`n.`nLib/site-packages`n"
& (Join-Path $runtimeRoot 'python.exe') -I -B -c "import importlib.metadata as m; expected={'pygame':'2.6.1','tcod':'19.3.0','numpy':'2.4.6','cffi':'2.1.1','pycparser':'3.11','typing_extensions':'4.16.0'}; assert all(m.version(k)==v for k,v in expected.items()); import pygame,tcod,numpy; print('Pinned Windows x64 runtime verified')"
if ($LASTEXITCODE -ne 0) { throw 'Runtime verification failed' }
$bytes = (Get-ChildItem -LiteralPath $runtimeRoot -Recurse -File | Measure-Object -Property Length -Sum).Sum
Write-Output "Bundled runtime: $bytes bytes. Includes CPython and dependency licenses. No system Python is needed at launch."
