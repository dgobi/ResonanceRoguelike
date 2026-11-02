. "$PSScriptRoot\paths.ps1"
$paths = Get-ArtPaths
Assert-ArtPaths $paths
New-Item -ItemType Directory -Force $Local, (Join-Path $Local 'backups') | Out-Null
Push-Location $Lab
try {
    & $paths.npm ci --ignore-scripts --no-fund --no-audit
    if ($LASTEXITCODE) { throw 'npm ci failed.' }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $backup = Join-Path $Local "backups\$stamp"
    New-Item -ItemType Directory $backup | Out-Null
    $extension = Join-Path $paths.asepriteConfig 'extensions\aseprite-ai-artist'
    if (Test-Path -LiteralPath $extension) { Copy-Item -LiteralPath $extension -Destination $backup -Recurse }
    $ini = Join-Path $paths.asepriteConfig 'aseprite.ini'
    if (Test-Path -LiteralPath $ini) { Copy-Item -LiteralPath $ini -Destination $backup }
    & $paths.node $Adapter install-extension --dir $paths.asepriteConfig --dry-run
    if ($LASTEXITCODE) { throw 'Extension preflight failed.' }
    & $paths.node $Adapter install-extension --dir $paths.asepriteConfig
    if ($LASTEXITCODE) { throw 'Extension installation failed.' }
    & $paths.node "$PSScriptRoot\configure.mjs" --dry-run
    if ($LASTEXITCODE) { throw 'Configuration preflight failed.' }
    & $paths.node "$PSScriptRoot\configure.mjs"
    if ($LASTEXITCODE) { throw 'Configuration failed.' }
    $paths | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Local 'paths.json') -Encoding UTF8
    Write-Host 'Setup saved. If Aseprite is open, save your documents and close it normally before launch-art.cmd.'
    Write-Host 'Lab art-tool approvals configured. launch-art.cmd starts full access; -StandardPermissions uses standard shell permissions. User-wide defaults were preserved.'
} finally { Pop-Location }
