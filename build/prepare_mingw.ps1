# Pre-download Nuitka MinGW compiler (fix SSL certificate errors)
# Usage: powershell -ExecutionPolicy Bypass -File build\prepare_mingw.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

# Prefer venv311 if present
$Python = "python"
$venvPy = Join-Path $Root ".venv311\Scripts\python.exe"
if (Test-Path $venvPy) { $Python = $venvPy }

$MingwUrl = "https://github.com/brechtsanders/winlibs_mingw/releases/download/15.2.0posix-13.0.0-msvcrt-r6/winlibs-x86_64-posix-seh-gcc-15.2.0-mingw-w64msvcrt-13.0.0-r6.zip"
$Version = "15.2.0posix-13.0.0-msvcrt-r6"
$ZipName = "winlibs-x86_64-posix-seh-gcc-15.2.0-mingw-w64msvcrt-13.0.0-r6.zip"
$CacheDir = Join-Path $env:LOCALAPPDATA "Nuitka\Nuitka\Cache\downloads\gcc\x86_64\$Version"
$DestZip = Join-Path $CacheDir $ZipName

Write-Host "MinGW cache target: $DestZip"

if (Test-Path $DestZip) {
    $sizeMb = [math]::Round((Get-Item $DestZip).Length / 1MB, 1)
    Write-Host "Already exists (${sizeMb} MB), skip download."
    exit 0
}

New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null

# Fix SSL: use certifi CA bundle
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $Python -m pip install -q certifi *>$null
$ErrorActionPreference = $prevEap
$certFile = & $Python -c "import certifi; print(certifi.where())" 2>$null
if ($certFile -and (Test-Path $certFile)) {
    $env:SSL_CERT_FILE = $certFile
    $env:REQUESTS_CA_BUNDLE = $certFile
    Write-Host "Using SSL cert: $certFile"
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host "Downloading MinGW (~200MB), please wait..."
$downloaded = $false
try {
    Invoke-WebRequest -Uri $MingwUrl -OutFile $DestZip -UseBasicParsing
    $downloaded = $true
} catch {
    Write-Host "Invoke-WebRequest failed: $($_.Exception.Message)"
}

if (-not $downloaded) {
    # Fallback: Python urllib with certifi
    $pyOneLiner = "import ssl,urllib.request,certifi,sys; u=sys.argv[1]; d=sys.argv[2]; c=ssl.create_default_context(cafile=certifi.where()); r=urllib.request.urlopen(u,context=c); open(d,'wb').write(r.read()); print('OK')"
    try {
        & $Python -c $pyOneLiner $MingwUrl $DestZip
        if ($LASTEXITCODE -eq 0 -and (Test-Path $DestZip)) { $downloaded = $true }
    } catch {
        Write-Host "Python download failed: $($_.Exception.Message)"
    }
}

if (-not $downloaded) {
    Write-Host ""
    Write-Host "Auto download failed. Please download manually:" -ForegroundColor Yellow
    Write-Host $MingwUrl
    Write-Host "Save as: $DestZip" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or install Visual Studio Build Tools and rebuild with -UseMsvc" -ForegroundColor Yellow
    exit 1
}

$sizeMb = [math]::Round((Get-Item $DestZip).Length / 1MB, 1)
Write-Host "Done (${sizeMb} MB). Re-run: build\nuitka_build.ps1" -ForegroundColor Green
