# CustomProject 一键启动：后端 (8000) + 前端 (5173)
# 用法：在项目根目录执行  .\start-dev.ps1
# 说明：ComfyUI 需单独启动（http://127.0.0.1:8188）

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "backEnd"
$FrontendDir = Join-Path $Root "frontEnd"

function Test-CommandExists([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Path $BackendDir)) {
    Write-Error "找不到后端目录: $BackendDir"
}
if (-not (Test-Path $FrontendDir)) {
    Write-Error "找不到前端目录: $FrontendDir"
}
if (-not (Test-CommandExists "python")) {
    Write-Error "未找到 python，请先安装 Python 并加入 PATH"
}
if (-not (Test-CommandExists "npm")) {
    Write-Error "未找到 npm，请先安装 Node.js"
}

Write-Host ""
Write-Host "CustomProject 开发服务启动中..." -ForegroundColor Cyan
Write-Host "  后端: http://127.0.0.1:8000  (backEnd)"
Write-Host "  前端: http://127.0.0.1:5173  (frontEnd)"
Write-Host "  提示: ComfyUI 需另行启动 -> http://127.0.0.1:8188"
Write-Host ""

$backendCmd = "Set-Location -LiteralPath '$BackendDir'; python main.py"
$frontendCmd = "Set-Location -LiteralPath '$FrontendDir'; npm run dev"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    $backendCmd
) -WindowStyle Normal

Start-Sleep -Milliseconds 500

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    $frontendCmd
) -WindowStyle Normal

Write-Host "已在两个新窗口中启动后端与前端。" -ForegroundColor Green
Write-Host "关闭对应窗口或按 Ctrl+C 即可停止服务。" -ForegroundColor DarkGray
Write-Host ""
