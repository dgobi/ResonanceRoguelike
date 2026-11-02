$ErrorActionPreference = 'Stop'
$Lab = Split-Path $PSScriptRoot -Parent
$Local = Join-Path $Lab '.local'
$Adapter = Join-Path $Lab 'node_modules\@pebbly\aseprite-ai-artist\dist\cli.js'
function Find-CommandPath([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    return $null
}
function Find-CodexPath {
    foreach ($name in @('codex.exe', 'codex.cmd')) {
        $command = Find-CommandPath $name
        if ($command) { return $command }
    }
    # Explorer does not inherit the desktop app's private PATH additions.
    # Reuse the executable verified by setup before looking for a newer build.
    $savedPaths = Join-Path $Local 'paths.json'
    if (Test-Path -LiteralPath $savedPaths) {
        try {
            $saved = Get-Content -LiteralPath $savedPaths -Raw | ConvertFrom-Json
            if ($saved.codex -and (Test-Path -LiteralPath $saved.codex -PathType Leaf)) {
                return $saved.codex
            }
        } catch { Write-Warning 'Could not read saved lab paths; discovering the installed Codex client.' }
    }
    # Build directory names change during desktop updates; do not pin one here.
    $desktopBin = Join-Path $env:LOCALAPPDATA 'OpenAI\Codex\bin'
    if (Test-Path -LiteralPath $desktopBin) {
        $installed = Get-ChildItem -LiteralPath $desktopBin -Directory | ForEach-Object {
            Get-Item -LiteralPath (Join-Path $_.FullName 'codex.exe') -ErrorAction SilentlyContinue
        } | Where-Object { !$_.PSIsContainer } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($installed) { return $installed.FullName }
    }
    return $null
}
function Get-ArtPaths {
    $node = Find-CommandPath 'node.exe'
    $codex = Find-CodexPath
    $npm = Find-CommandPath 'npm.cmd'
    if ($env:ASEPRITE_PATH -and !(Test-Path -LiteralPath $env:ASEPRITE_PATH -PathType Leaf)) {
        throw 'ASEPRITE_PATH points to a missing executable. Correct that local override before continuing.'
    }
    $candidates = @($env:ASEPRITE_PATH, (Find-CommandPath 'aseprite.exe'))
    $steam = Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue
    $libraries = @("${env:ProgramFiles(x86)}\Steam", $steam.SteamPath)
    if ($steam.SteamPath) {
        $vdf = Join-Path $steam.SteamPath 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            $libraries += [regex]::Matches((Get-Content -LiteralPath $vdf -Raw), '"path"\s+"([^"]+)"') |
                ForEach-Object { $_.Groups[1].Value.Replace('\\', '\') }
        }
    }
    foreach ($library in $libraries) {
        if ($library) { $candidates += Join-Path $library 'steamapps\common\Aseprite\Aseprite.exe' }
    }
    $candidates += Join-Path $env:ProgramFiles 'Aseprite\Aseprite.exe'
    $aseprite = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1
    $config = $env:ASEPRITE_USER_FOLDER
    if (!$config) { $config = Join-Path $env:APPDATA 'Aseprite' }
    [pscustomobject]@{ node=$node; npm=$npm; codex=$codex; aseprite=$aseprite; asepriteConfig=$config }
}
function Assert-ArtPaths($paths) {
    foreach ($name in @('node','npm','codex','aseprite')) {
        if (!$paths.$name) { throw "Missing $name. See art_lab/README.md, then rerun setup-art.cmd." }
    }
    $version = [version]((& $paths.node --version).TrimStart('v'))
    if ($version -lt [version]'22.6.0') { throw 'Node 22.6+ is required.' }
    if (!(Test-Path -LiteralPath $paths.asepriteConfig)) { throw 'Run Aseprite once, close it normally, then rerun setup-art.cmd.' }
}
