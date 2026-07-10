# 打包 Web 版（后端可执行文件 + 前端静态资源，产出到 release/web/windows）。
# 首次运行会自动创建 .venv 并安装依赖，不影响系统环境。
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

& (Join-Path $PSScriptRoot 'scripts\ensure-build-env.ps1') -Frontend
$PythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $PythonExe .\scripts\package.py --variant web --platform windows
if ($LASTEXITCODE -ne 0) { throw "打包 Web 版失败（退出码 $LASTEXITCODE）" }
Write-Host "`nOK Web 版已打包到 release\web\windows" -ForegroundColor Green