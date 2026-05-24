# Build closed-source release: frontEnd dist + PyInstaller backend (onedir exe)
# Usage (from CustomProject root):
#   powershell -ExecutionPolicy Bypass -File scripts/build_release.ps1
# Options:
#   -SkipFrontend     skip npm build
#   -SkipPyInstaller   skip pyinstaller (bin/ must already exist)

param(
    [switch]$SkipFrontend,
    [switch]$SkipPyInstaller
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$BackEnd = Join-Path $ProjectRoot "backEnd"
$FrontEnd = Join-Path $ProjectRoot "frontEnd"
$BinDir = Join-Path $ProjectRoot "bin"
$ReleaseRoot = Join-Path $ProjectRoot "release"
$Staging = Join-Path $ReleaseRoot "CustomProject"

Write-Host "==> CustomProject release build" -ForegroundColor Cyan
Write-Host "    root: $ProjectRoot"

if (-not $SkipFrontend) {
    Write-Host ""
    Write-Host "==> npm run build ..." -ForegroundColor Cyan
    Push-Location $FrontEnd
    if (-not (Test-Path "node_modules")) {
        npm ci
    }
    npm run build
    Pop-Location
    if (-not (Test-Path (Join-Path $FrontEnd "dist\index.html"))) {
        throw "frontEnd/dist/index.html missing"
    }
}

if (-not $SkipPyInstaller) {
    Write-Host ""
    Write-Host "==> PyInstaller ..." -ForegroundColor Cyan
    Push-Location $BackEnd
    python -m pip install -r requirements.txt pyinstaller --quiet
    pyinstaller --noconfirm --clean customproject-api.spec
    Pop-Location

    $Built = Join-Path $BackEnd "dist\customproject-api"
    if (-not (Test-Path (Join-Path $Built "customproject-api.exe"))) {
        throw "PyInstaller output missing: $Built\customproject-api.exe"
    }

    if (Test-Path $BinDir) { Remove-Item $BinDir -Recurse -Force }
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
    Copy-Item -Path (Join-Path $Built "*") -Destination $BinDir -Recurse -Force
    Write-Host "    copied to $BinDir"
}

if (-not (Test-Path (Join-Path $BinDir "customproject-api.exe"))) {
    throw "bin/customproject-api.exe missing; run full build first"
}

Write-Host ""
Write-Host "==> staging release/CustomProject ..." -ForegroundColor Cyan
if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Path $Staging -Force | Out-Null

foreach ($name in @("config", "workflows", "prompt", "docs")) {
    $src = Join-Path $ProjectRoot $name
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination (Join-Path $Staging $name) -Recurse -Force
    }
}

Copy-Item -Path $BinDir -Destination (Join-Path $Staging "bin") -Recurse -Force

$feOut = Join-Path $Staging "frontEnd\dist"
New-Item -ItemType Directory -Path (Split-Path $feOut -Parent) -Force | Out-Null
Copy-Item -Path (Join-Path $FrontEnd "dist") -Destination $feOut -Recurse -Force

$startBat = @"
@echo off
setlocal
set "CUSTOM_PROJECT_ROOT=%~dp0"
set "COMFYUI_ROOT=%~dp0.."
cd /d "%~dp0bin"
echo CustomProject API: http://127.0.0.1:8000
echo Start ComfyUI first: http://127.0.0.1:8188
customproject-api.exe
pause
"@
Set-Content -Path (Join-Path $Staging "start-api.bat") -Value $startBat -Encoding ASCII

$usageDoc = Join-Path $ProjectRoot "docs\使用说明.md"
if (Test-Path $usageDoc) {
    Copy-Item -Path $usageDoc -Destination $Staging -Force
}

$zip = Join-Path $ReleaseRoot "CustomProject-closed.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $Staging -DestinationPath $zip -Force

Write-Host ""
Write-Host "==> done" -ForegroundColor Green
Write-Host "    dir: $Staging"
Write-Host "    zip: $zip"
Write-Host "    unzip under ComfyUI, run start-api.bat, open http://127.0.0.1:8000"
