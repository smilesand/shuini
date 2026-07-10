# 一键打包客户所需的 Windows 产物：桌面安装包 + 管理员授权签发工具。
# 首次运行会自动创建 .venv 并安装所有依赖，不影响系统环境。
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

& (Join-Path $PSScriptRoot 'scripts\ensure-build-env.ps1') -Frontend -Desktop
$PythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

# 1) 桌面安装包
& $PythonExe .\scripts\package.py --variant desktop --platform windows
if ($LASTEXITCODE -ne 0) { throw "打包桌面端失败（退出码 $LASTEXITCODE）" }

# 2) 管理员授权签发工具（若内嵌私钥的签发工具尚未生成，先从 scripts/keys 生成）
if (-not (Test-Path (Join-Path $PSScriptRoot 'release\license-tool\wtcmd-license-tool.py'))) {
    Write-Host '==> 从 scripts/keys 生成内嵌私钥的签发工具（不会改变现有密钥）...' -ForegroundColor Cyan
    & $PythonExe .\scripts\init_license_keys.py
    if ($LASTEXITCODE -ne 0) { throw "生成签发工具失败（退出码 $LASTEXITCODE）" }
}
& $PythonExe .\scripts\package.py --variant admin --platform windows
if ($LASTEXITCODE -ne 0) { throw "打包签发工具失败（退出码 $LASTEXITCODE）" }

Write-Host "`nOK 全部完成：" -ForegroundColor Green
Write-Host '  桌面安装包：release\desktop\windows'
Write-Host '  签发工具：release\license-admin\windows\wtcmd-license-admin.exe'
Write-Host "`n[!] 签发工具内嵌授权私钥，仅限管理员使用，切勿随桌面安装包分发给最终用户。" -ForegroundColor Yellow