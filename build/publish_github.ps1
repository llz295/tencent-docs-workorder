# Publish source code to GitHub (first time)
# Usage:
#   powershell -ExecutionPolicy Bypass -File build\publish_github.ps1 -RepoUrl "https://github.com/你的用户名/仓库名.git"

param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Find-Git {
    $cmd = Get-Command git -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($p in @(
        "${env:ProgramFiles}\Git\cmd\git.exe",
        "${env:ProgramFiles(x86)}\Git\cmd\git.exe"
    )) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$git = Find-Git
if (-not $git) {
    Write-Host ""
    Write-Host "ERROR: Git not installed." -ForegroundColor Red
    Write-Host "Download: https://git-scm.com/download/win"
    Write-Host "Install with 'Add Git to PATH', then restart Cursor and run this script again."
    exit 1
}

Write-Host "Using Git: $git"

$userName = & $git config --global user.name 2>$null
$userEmail = & $git config --global user.email 2>$null
if (-not $userName -or -not $userEmail) {
    Write-Host ""
    Write-Host "Configure Git identity first (one time only):" -ForegroundColor Yellow
    Write-Host '  git config --global user.name "Your Name"'
    Write-Host '  git config --global user.email "your@email.com"'
    exit 1
}

if (-not (Test-Path (Join-Path $Root ".git"))) {
    Write-Host "git init ..."
    & $git init
}

Write-Host "git add ..."
& $git add .

$status = & $git status --porcelain
if (-not $status) {
    Write-Host "No changes to commit."
} else {
    Write-Host "git commit ..."
    & $git commit -m @"
Initial release: Tencent Docs work order automation

- Desktop GUI + Web UI + CLI
- Download, summarize, calendar date ranges
- Nuitka packaging scripts
"@
}

Write-Host "git branch -M main ..."
& $git branch -M main

$remotes = & $git remote 2>$null
if ($remotes -notcontains "origin") {
    Write-Host "git remote add origin ..."
    & $git remote add origin $RepoUrl
} else {
    Write-Host "git remote set-url origin ..."
    & $git remote set-url origin $RepoUrl
}

Write-Host ""
Write-Host "Pushing to GitHub (browser login may pop up) ..."
& $git push -u origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Push failed. Common fixes:" -ForegroundColor Yellow
    Write-Host "  1) Create empty repo on GitHub first (no README)"
    Write-Host "  2) Use HTTPS URL and login when prompted"
    Write-Host "  3) Or use Personal Access Token as password"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Source code pushed successfully!"
Write-Host " Next: upload release zip on GitHub website"
Write-Host " File: releases\WorkOrderAutomation-Nuitka-Windows.zip"
Write-Host "========================================" -ForegroundColor Green
