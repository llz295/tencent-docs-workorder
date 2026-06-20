# Windows build (run from tencent_docs_pom):
#   powershell -ExecutionPolicy Bypass -File build\build.ps1
# Lite (no browser, first-run download):
#   powershell -ExecutionPolicy Bypass -File build\build.ps1 -Lite

param(
    [switch]$Lite
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ReleaseDir = Join-Path $Root "releases"
$Dist = Join-Path $Root "dist"
$ZipName = if ($Lite) { "WorkOrderAutomation-Windows-lite.zip" } else { "WorkOrderAutomation-Windows.zip" }

Write-Host "==> pip install" -ForegroundColor Cyan
python -m pip install -q -r requirements.txt

if (-not $Lite) {
    Write-Host "==> playwright install chromium --no-shell" -ForegroundColor Cyan
    python -m playwright install chromium --no-shell
}

Write-Host "==> PyInstaller" -ForegroundColor Cyan
python -m PyInstaller build\tencent_docs.spec --noconfirm --clean

if (-not (Test-Path $Dist)) {
    Write-Error "dist folder missing"
}

$ExeBuilt = Join-Path $Dist "WorkOrderAutomation.exe"
if (-not (Test-Path -LiteralPath $ExeBuilt)) {
    $any = Get-ChildItem $Dist -Filter "WorkOrderAutomation*" | Where-Object { -not $_.PSIsContainer } | Select-Object -First 1
    if (-not $any) { Write-Error "executable not found in dist" }
    if ($any.Extension -ne ".exe") {
        Rename-Item $any.FullName ($any.FullName + ".exe") -ErrorAction SilentlyContinue
    }
    $ExeBuilt = Join-Path $Dist "WorkOrderAutomation.exe"
}

$DataSrc = Join-Path $Root "data"
$DataDst = Join-Path $Dist "data"
if (Test-Path $DataDst) { Remove-Item $DataDst -Recurse -Force }
New-Item -ItemType Directory -Path $DataDst -Force | Out-Null
Get-ChildItem $DataSrc -File | Where-Object { $_.Name -ne "session.json" } | Copy-Item -Destination $DataDst

$DistBrowsers = Join-Path $Dist "ms-playwright"
if ($Lite) {
    if (Test-Path $DistBrowsers) { Remove-Item $DistBrowsers -Recurse -Force }
    Write-Host "==> Lite: skip ms-playwright (download on first run)" -ForegroundColor Yellow
} else {
    Write-Host "==> copy Chromium to dist\ms-playwright" -ForegroundColor Cyan
    python build\stage_browsers.py $Dist
}

@("app.log", "templates") | ForEach-Object {
    $p = Join-Path $Dist $_
    if (Test-Path $p) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }
}

$Readme = Join-Path $Dist "README-win.txt"
$browserLine = if ($Lite) {
    "Lite: first run downloads ms-playwright (needs internet)."
} else {
    "ms-playwright folder included (Chromium only, about 400MB)."
}
@(
    "Work Order Automation - Windows",
    "",
    "Keep WorkOrderAutomation.exe, data/, in one folder.",
    $browserLine,
    "Double-click WorkOrderAutomation.exe to start.",
    "First login: WeChat scan. Session: data/session.json (do not share).",
    "Ship the whole folder or the zip from releases/."
) | Set-Content -Path $Readme -Encoding UTF8

New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
$ZipPath = Join-Path $ReleaseDir $ZipName
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path (Join-Path $Dist "*") -DestinationPath $ZipPath -Force

$total = (Get-ChildItem $Dist -Recurse -File | Measure-Object -Property Length -Sum).Sum
$totalMb = [math]::Round($total / 1MB, 1)
Write-Host ""
Write-Host "DONE dist: $Dist" -ForegroundColor Green
Write-Host "DONE zip:  $ZipPath  (${totalMb} MB unpacked)" -ForegroundColor Green
