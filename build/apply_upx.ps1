# UPX compress exe/dll in dist folder
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetDir,

    [string]$UpxPath = ""
)

$ErrorActionPreference = "Stop"

if (-not $UpxPath) {
    $Root = Split-Path -Parent $PSScriptRoot
    $candidates = @(
        (Join-Path $Root "upx.exe"),
        (Join-Path $Root "tools\upx.exe")
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) {
            $UpxPath = (Resolve-Path -LiteralPath $c).Path
            break
        }
    }
    if (-not $UpxPath) {
        $cmd = Get-Command upx.exe -ErrorAction SilentlyContinue
        if ($cmd) { $UpxPath = $cmd.Source }
    }
}

if (-not $UpxPath -or -not (Test-Path -LiteralPath $UpxPath)) {
    Write-Warning "upx.exe not found, skip UPX (place upx.exe in project root)"
    exit 0
}

Write-Host "UPX: $UpxPath"

$files = Get-ChildItem -Path $TargetDir -Recurse -File -Include *.exe, *.dll |
    Where-Object {
        $_.Name -notmatch '^(python|vcruntime|msvcp|api-ms-win|ucrtbase)' -and
        $_.FullName -notmatch '\\ms-playwright\\'
    }

$before = ($files | Measure-Object -Property Length -Sum).Sum
$ok = 0
$skip = 0

foreach ($f in $files) {
    try {
        & $UpxPath --best --lzma --force $f.FullName 2>$null
        if ($LASTEXITCODE -eq 0) { $ok++ } else { $skip++ }
    } catch {
        $skip++
    }
}

$after = ($files | Measure-Object -Property Length -Sum).Sum
$saved = [math]::Round(($before - $after) / 1MB, 1)
Write-Host "UPX done: compressed=$ok skipped=$skip saved=${saved}MB"
