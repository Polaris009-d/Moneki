# Moneki 一键启动脚本（Windows PowerShell）
# 自动：创建 venv → 装后端依赖 → 建库 → 装前端依赖 → 启动前后端
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

$python = "python"
if (-not (Test-Path (Join-Path $backend ".venv"))) {
    Write-Host "==> 创建后端虚拟环境..." -ForegroundColor Cyan
    & $python -m venv (Join-Path $backend ".venv")
}
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"
$venvPip = Join-Path $backend ".venv\Scripts\pip.exe"

Write-Host "==> 安装后端依赖..." -ForegroundColor Cyan
& $venvPip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r (Join-Path $backend "requirements.txt") | Out-Null

Write-Host "==> 初始化数据（清洗 + 建库）..." -ForegroundColor Cyan
Push-Location $backend
& $venvPython scripts/init_db.py
Pop-Location

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "==> 安装前端依赖..." -ForegroundColor Cyan
    Push-Location $frontend
    & npm install --registry=https://registry.npmmirror.com | Out-Null
    Pop-Location
}

Write-Host "==> 启动后端 http://localhost:8000" -ForegroundColor Green
Start-Process -FilePath $venvPython -ArgumentList "-m","uvicorn","app.main:app","--port","8000" -WorkingDirectory $backend

Write-Host "==> 启动前端 http://localhost:5173" -ForegroundColor Green
Start-Process -FilePath "npm.cmd" -ArgumentList "run","dev" -WorkingDirectory $frontend

Write-Host ""
Write-Host "完成！浏览器打开 http://localhost:5173（记得先在 backend/.env 配置 DEEPSEEK_API_KEY）" -ForegroundColor Green
