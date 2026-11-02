$ErrorActionPreference = 'Stop'
$Lab = Split-Path $PSScriptRoot -Parent
$Local = Join-Path $Lab '.local'
$Adapter = Join-Path $Lab 'node_modules\@pebbly\aseprite-ai-artist\dist\cli.js'
function Find-CommandPath([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    return $null
}
function Get-ArtPaths {
    $node = Find-CommandPath 'node.exe'
    $codex = Find-CommandPath 'codex.exe'
    if (!$codex) { $codex = Find-CommandPath 'codex.cmd' }
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
