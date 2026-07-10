# 打包 Windows 桌面安装包（产出到 release/desktop/windows）。
# 首次运行会自动创建 .venv 、安装 Python 依赖与前端/桌面 npm 依赖，不影响系统环境。
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

& (Join-Path $PSScriptRoot 'scripts\ensure-build-env.ps1') -Frontend -Desktop
$PythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $PythonExe .\scripts\package.py --variant desktop --platform windows
if ($LASTEXITCODE -ne 0) { throw "打包桌面端失败（退出码 $LASTEXITCODE）" }
Write-Host "`nOK 桌面安装包已打包到 release\desktop\windows" -ForegroundColor Green