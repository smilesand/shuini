#requires -Version 5.1
<#
.SYNOPSIS
    打包「管理员授权签发工具」（wtcmd-license-admin.exe）。

.DESCRIPTION
    产出带图形界面的授权签发客户端：管理被授权设备信息，并为设备指纹签发授权码。
    首次运行会自动创建 .venv 并安装依赖，不影响系统环境。

    流程：
      1. 准备打包环境（.venv + 依赖）；
      2. 若内嵌私钥的签发工具尚未生成，则从 scripts/keys 里现有的密钥生成
         （不加 --force，不会改变已交付的密钥，也不会作废历史授权码）；
      3. 用 PyInstaller 打包成单文件 exe。

    产物：release\license-admin\windows\wtcmd-license-admin.exe

    ⚠️ 该 exe 内嵌授权私钥，仅限授权方管理员在受控机器上使用，
       切勿随桌面安装包一起分发给最终用户。
#>
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# 必须在 Windows 上打包（PyInstaller 不支持跨平台编译）
if ($env:OS -ne 'Windows_NT') {
    throw '签发工具只能在 Windows 上打包（PyInstaller 不支持跨平台编译）。'
}

& (Join-Path $PSScriptRoot 'scripts\ensure-build-env.ps1')
$PythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

# 校验密钥是否存在（随源码交付的 scripts/keys）
$privKey = Join-Path $PSScriptRoot 'scripts\keys\private_key.pem'
if (-not (Test-Path $privKey)) {
    throw "未找到授权私钥 scripts\keys\private_key.pem。请确认已随源码包一并解压 scripts\keys 目录。"
}

# 若内嵌私钥的签发工具尚未生成，则从现有密钥生成（不加 --force）
if (-not (Test-Path (Join-Path $PSScriptRoot 'release\license-tool\wtcmd-license-tool.py'))) {
    Write-Host '==> 从 scripts/keys 生成内嵌私钥的签发工具（不会改变现有密钥）...' -ForegroundColor Cyan
    & $PythonExe .\scripts\init_license_keys.py
    if ($LASTEXITCODE -ne 0) { throw "生成签发工具失败（退出码 $LASTEXITCODE）" }
}

& $PythonExe .\scripts\package.py --variant admin --platform windows
if ($LASTEXITCODE -ne 0) { throw "打包签发工具失败（退出码 $LASTEXITCODE）" }

Write-Host "`nOK 签发工具已打包：release\license-admin\windows\wtcmd-license-admin.exe" -ForegroundColor Green
Write-Host "`n[!] 该工具内嵌授权私钥，仅限授权方管理员使用，切勿随桌面安装包分发给最终用户。" -ForegroundColor Yellow
