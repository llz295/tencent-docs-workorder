# Nuitka lightweight build (Windows)
# Usage:
#   powershell -ExecutionPolicy Bypass -File build\nuitka_build.ps1
#   powershell -ExecutionPolicy Bypass -File build\nuitka_build.ps1 -Lite
#   powershell -ExecutionPolicy Bypass -File build\nuitka_build.ps1 -SkipUpx

param(
    [switch]$Lite,
    [switch]$SkipUpx,
    [ValidateSet("auto", "mingw", "msvc")]
    [string]$Compiler = "auto"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ReleaseDir = Join-Path $Root "releases"
$DistRoot = Join-Path $Root "dist"
$NuitkaOut = Join-Path $Root "build\nuitka-out"
$AppDist = Join-Path $DistRoot "WorkOrderAutomation"
$ZipName = if ($Lite) { "WorkOrderAutomation-Nuitka-Windows-lite.zip" } else { "WorkOrderAutomation-Nuitka-Windows.zip" }

Write-Host "========================================"
Write-Host " Nuitka build - WorkOrderAutomation"
Write-Host "========================================"

Write-Host "`n[0/8] Clean stale build artifacts"
# 删除 dist 前，先把可用的 Chromium 保留到项目 ms-playwright，避免每次重下 ~180MB
$distBrowsers = Join-Path $AppDist "ms-playwright"
$projBrowsers = Join-Path $Root "ms-playwright"
if (Test-Path $distBrowsers) {
    Write-Host "  preserving ms-playwright from dist -> project ..."
    & python build\stage_browsers.py --import-from $AppDist 2>$null
    if ($LASTEXITCODE -ne 0) {
        # fallback: simple copy if import helper not used yet
        $revDir = Get-ChildItem $distBrowsers -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^chromium-\d+$' -and $_.Name -notmatch 'headless_shell' } |
            Select-Object -First 1
        if ($revDir -and (Test-Path (Join-Path $revDir.FullName "chrome-win64\chrome.exe"))) {
            New-Item -ItemType Directory -Path $projBrowsers -Force | Out-Null
            $dest = Join-Path $projBrowsers $revDir.Name
            if (-not (Test-Path $dest)) {
                Copy-Item $revDir.FullName $dest -Recurse -Force
                Write-Host "  preserved: $($revDir.Name)"
            }
        }
    }
}

$cleanBefore = @(
    (Join-Path $Root "build\nuitka-out"),
    (Join-Path $Root "run.build"),
    (Join-Path $Root "run.dist"),
    (Join-Path $Root "run.onefile-build"),
    (Join-Path $Root "nuitka-crash-report.xml"),
    $AppDist
)
foreach ($p in $cleanBefore) {
    if (Test-Path $p) {
        Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  removed: $p"
    }
}
# 仅删过旧/损坏的 chromium 目录（无 chrome.exe），保留有效缓存
Get-ChildItem $projBrowsers -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^chromium-' -and $_.Name -notmatch 'headless_shell' } |
    ForEach-Object {
        $exe = Join-Path $_.FullName "chrome-win64\chrome.exe"
        if (-not (Test-Path $exe)) {
            Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  removed broken: ms-playwright\$($_.Name)"
        }
    }

Write-Host "`n[1/8] Install dependencies"
python -m pip install -q -r requirements.txt
python -m pip install -q nuitka ordered-set zstandard certifi

# Fix SSL for Nuitka auto-downloads (CERTIFICATE_VERIFY_FAILED)
$certFile = python -c "import certifi; print(certifi.where())" 2>$null
if ($certFile -and (Test-Path $certFile)) {
    $env:SSL_CERT_FILE = $certFile
    $env:REQUESTS_CA_BUNDLE = $certFile
    Write-Host "SSL cert bundle: $certFile"
}

Write-Host "`n[2/8] Prepare vendor/app.py"
python build\prepare_vendor.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $Lite) {
    Write-Host "`n[3/8] Ensure Chromium matches Playwright revision"
    python build\stage_browsers.py --ensure-project
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "`n[3/8] Lite mode: skip browser install"
}

Write-Host "`n[4/8] Nuitka compile (standalone)"

function Test-MsvcInstalled {
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $vswhere)) { return $false }
    $path = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null
    return [bool]$path
}

$env:PYTHONPATH = (Join-Path $Root "vendor") + ";" + $Root

$dataDir = Join-Path $Root "data"
$staticDir = Join-Path $Root "web\static"

$pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$useMsvc = $false
$useMingw = $false

if ($Compiler -eq "msvc") {
    $useMsvc = $true
} elseif ($Compiler -eq "mingw") {
    $useMingw = $true
} else {
    if (Test-MsvcInstalled) {
        $useMsvc = $true
        Write-Host "Detected Visual Studio -> using MSVC"
    } else {
        $useMingw = $true
        Write-Host "No Visual Studio -> using MinGW64"
        Write-Host "Preparing MinGW (run prepare_mingw.ps1 if SSL fails)..."
        powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "prepare_mingw.ps1")
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "MinGW prep failed. Try: -Compiler msvc (install VS Build Tools) or manual download per prepare_mingw.ps1"
        }
    }
}

$nuitkaCmd = @(
    "-m", "nuitka",
    "--standalone",
    "--assume-yes-for-downloads",
    "--enable-plugin=tk-inter",
    "--windows-console-mode=disable",
    "--output-dir=$NuitkaOut",
    "--output-filename=WorkOrderAutomation.exe",
    "--file-version=1.0.0.0",
    "--product-version=1.0.0.0"
)
if ($useMsvc) {
    $nuitkaCmd += "--msvc=latest"
    Write-Host "Compiler: MSVC"
} elseif ($useMingw) {
    $nuitkaCmd += "--mingw64"
    Write-Host "Compiler: MinGW64 (Python $pyVer)"
} else {
    Write-Host "Python $pyVer -> default backend"
}
# LTO can slow/fail on some MinGW builds; enable only for MSVC
if ($useMsvc) {
    $nuitkaCmd += "--lto=yes"
}
$nuitkaCmd += @(
    "--include-package=customtkinter",
    "--include-package=playwright",
    "--include-package=pandas",
    "--include-package=openpyxl",
    "--include-package=fastapi",
    "--include-package=uvicorn",
    "--include-package=starlette",
    "--include-package=ui",
    "--include-package=config",
    "--include-package=auth",
    "--include-package=pages",
    "--include-package=services",
    "--include-package=core",
    "--include-package=summarize",
    "--include-package=web",
    "--include-module=app",
    "--include-data-dir=$dataDir=data",
    "--include-data-dir=$staticDir=web\static",
    "--nofollow-import-to=matplotlib",
    "--nofollow-import-to=IPython",
    "--nofollow-import-to=jupyter",
    "--nofollow-import-to=pytest",
    "--nofollow-import-to=scipy",
    "--nofollow-import-to=sklearn",
    "--nofollow-import-to=torch",
    "--nofollow-import-to=tensorflow",
    "--nofollow-import-to=PyQt5",
    "--nofollow-import-to=PyQt6",
    "--nofollow-import-to=PySide2",
    "--nofollow-import-to=PySide6",
    "--nofollow-import-to=wx",
    "--nofollow-import-to=pandas.tests",
    # Playwright ships PyInstaller hooks; do not bundle PyInstaller into Nuitka output
    "--nofollow-import-to=PyInstaller",
    "--nofollow-import-to=playwright._impl.__pyinstaller",
    "run.py"
)

python @nuitkaCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Nuitka compile failed. Common fixes:" -ForegroundColor Yellow
    Write-Host "  1) powershell -File build\prepare_mingw.ps1   # fix MinGW SSL download"
    Write-Host "  2) Install VS Build Tools, then: -Compiler msvc"
    Write-Host "  3) powershell -File build\build.ps1           # PyInstaller fallback"
    Write-Error "Nuitka compile failed"
}

$BuiltDir = Join-Path $NuitkaOut "run.dist"
if (-not (Test-Path $BuiltDir)) {
    $BuiltDir = Get-ChildItem $NuitkaOut -Directory | Where-Object { $_.Name -like "*.dist" } | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $BuiltDir -or -not (Test-Path $BuiltDir)) {
    Write-Error "Nuitka output directory (*.dist) not found"
}

Write-Host "`n[5/8] Stage dist folder"
if (Test-Path $AppDist) { Remove-Item $AppDist -Recurse -Force }
New-Item -ItemType Directory -Path $AppDist -Force | Out-Null
Copy-Item -Path (Join-Path $BuiltDir "*") -Destination $AppDist -Recurse -Force

$DataSrc = Join-Path $Root "data"
$DataDst = Join-Path $AppDist "data"
if (Test-Path $DataDst) { Remove-Item $DataDst -Recurse -Force }
New-Item -ItemType Directory -Path $DataDst -Force | Out-Null
Get-ChildItem $DataSrc -File | Where-Object { $_.Name -notmatch '^(session\.json|instance\.lock|session\.json\.bak)$' } | Copy-Item -Destination $DataDst

if ($Lite) {
    Write-Host "`n[6/8] Lite: no ms-playwright (download on first run)"
    $bp = Join-Path $AppDist "ms-playwright"
    if (Test-Path $bp) { Remove-Item $bp -Recurse -Force }
} else {
    Write-Host "`n[6/8] Copy Chromium to ms-playwright"
    python build\stage_browsers.py $AppDist
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipUpx) {
    Write-Host "`n[7/8] UPX compress"
    powershell -ExecutionPolicy Bypass -File build\apply_upx.ps1 -TargetDir $AppDist
} else {
    Write-Host "`n[7/8] Skip UPX"
}

Write-Host "`n[8/8] Create release zip"
$Readme = Join-Path $AppDist "README-win.txt"
$browserLine = if ($Lite) { "Lite: Chromium downloads on first run (internet required)." } else { "Includes ms-playwright Chromium (~400MB)." }
@(
    "Work Order Automation - Windows (Nuitka)",
    "",
    "Run WorkOrderAutomation.exe",
    "WeChat scan required for Tencent Docs login on first use.",
    $browserLine,
    "Config: data/   Session: data/session.json (do not share)",
    "",
    "Web UI: set ui_mode=web or run with --web",
    "LAN: web_host=0.0.0.0 then open http://<your-ip>:8765",
    "",
    "Ship the entire folder, not exe alone."
) | Set-Content -Path $Readme -Encoding UTF8

New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
$ZipPath = Join-Path $ReleaseDir $ZipName
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path (Join-Path $AppDist "*") -DestinationPath $ZipPath -Force

$total = (Get-ChildItem $AppDist -Recurse -File | Measure-Object -Property Length -Sum).Sum
$totalMb = [math]::Round($total / 1MB, 1)
$exePath = Join-Path $AppDist "WorkOrderAutomation.exe"
$exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 1)

Write-Host ""
Write-Host "========================================"
Write-Host " DONE"
Write-Host " App folder: $AppDist"
Write-Host " Release:    $ZipPath"
Write-Host " exe size:   ${exeSize} MB"
Write-Host " total:      ${totalMb} MB"
Write-Host "========================================"
