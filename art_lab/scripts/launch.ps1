param([switch]$CheckOnly, [string]$Model)
. "$PSScriptRoot\paths.ps1"
$paths = Get-ArtPaths
Assert-ArtPaths $paths
if (!(Test-Path -LiteralPath $Adapter) -or !(Test-Path -LiteralPath (Join-Path $Lab '.codex\config.toml'))) {
    throw 'Lab dependencies/config are missing. Run setup-art.cmd first.'
}
New-Item -ItemType Directory -Force $Local | Out-Null
$lock = $null
Push-Location $Lab
try {
    try {
        $lock = [IO.File]::Open((Join-Path $Local 'art-session.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch { throw 'Another launch-art session owns this lab. Use that conversation or close it first.' }
    $effectiveText = & $paths.codex mcp get aseprite-ai-artist --json
    if ($LASTEXITCODE) { throw 'Lab MCP config is not loaded. See README: project trust and fresh session.' }
    $effective = ($effectiveText -join "`n") | ConvertFrom-Json
    if (!$effective.enabled -or $effective.transport.command -ne $paths.node -or
        $effective.transport.args[0] -ne $Adapter -or $effective.transport.args[1] -ne 'serve' -or
        $effective.transport.env.ASEPRITE_AI_ALLOW_LUA -ne '0' -or $effective.transport.env.ASEPRITE_AI_HEADLESS -ne '0') {
        throw 'Effective MCP runtime differs from this local locked live setup. Rerun setup-art.cmd and check conflicting config.'
    }
    if (!(Get-Process Aseprite -ErrorAction SilentlyContinue)) {
        # This is the requested visible editor, not a background helper.
        Start-Process -FilePath $paths.aseprite
    }
    & $paths.node "$PSScriptRoot\check-live.mjs"
    if ($LASTEXITCODE) { throw 'Live readiness check failed; see the message above. No drawing was attempted.' }
    if ($CheckOnly) { Write-Host 'Launcher preflight passed.'; return }
    Write-Host "Type art prompts in the Codex conversation below. Artwork appears in Aseprite. Lab: $Lab"
    Write-Host 'Use /model to select an available model. Keep one authoring conversation per editor.'
    $codexArgs = @('--no-daemon', '--cd', $Lab)
    if ($Model) { $codexArgs += @('--model', $Model) }
    & $paths.codex @codexArgs
    if ($LASTEXITCODE) { throw "Codex exited with code $LASTEXITCODE. The error remains visible in this window." }
} finally {
    if ($lock) { $lock.Dispose() }
    Pop-Location
}
