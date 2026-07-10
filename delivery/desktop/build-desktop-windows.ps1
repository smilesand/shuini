#requires -Version 5.1
<#
.SYNOPSIS
    交付②（Windows 桌面端 + 管理员签发工具）：在 Windows 上一键打包。

.DESCRIPTION
    ⚠️ 为什么不是 Docker 镜像？
      桌面端内置的后端用 PyInstaller 打包，PyInstaller 无法跨平台编译
      （Linux 只能产出 Linux 可执行文件）。因此 Windows 桌面端必须在
      Windows 环境构建。本脚本即为在 Windows 构建机上一键完成打包。

    本脚本依次执行：
      1. python scripts/package.py --variant desktop --platform windows
         → 产出 Windows 安装包（NSIS）到 release/desktop/windows/
      2. （可选，-WithAdmin）python scripts/package.py --variant admin --platform windows
         → 产出管理员授权签发工具 wtcmd-license-admin.exe 到 release/license-admin/windows/

.PARAMETER WithAdmin
    同时构建管理员授权签发工具（内嵌授权私钥，仅限授权方管理员使用）。

.EXAMPLE
    .\build-desktop-windows.ps1                # 仅打包桌面安装包
    .\build-desktop-windows.ps1 -WithAdmin     # 桌面安装包 + 签发工具
#>
[CmdletBinding()]
param(
    [switch]$WithAdmin
)

$ErrorActionPreference = 'Stop'

# 必须在 Windows 上运行
if ($env:OS -ne 'Windows_NT') {
    throw '桌面端只能在 Windows 上打包（PyInstaller 不支持跨平台编译）。'
}

# 定位项目根目录（本脚本位于 <root>/delivery/desktop/）
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root

# ── 环境检查 ──────────────────────────────────────────────────────────────────
function Assert-Command($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "缺少依赖：$name。$hint"
    }
}
Assert-Command python ' 请安装 Python 3.11+ 并加入 PATH。'
Assert-Command node   ' 请安装 Node.js 18+ 并加入 PATH。'
Assert-Command npm    ' 请安装 Node.js（含 npm）并加入 PATH。'

Write-Host "==> 项目根目录：$root" -ForegroundColor Cyan
Write-Host "==> Python：$(python --version)" -ForegroundColor Cyan
Write-Host "==> Node：$(node --version)" -ForegroundColor Cyan

# ── 1. 打包桌面安装包 ─────────────────────────────────────────────────────────
Write-Host "`n==> [1/2] 打包 Windows 桌面安装包 ..." -ForegroundColor Cyan
python scripts/package.py --variant desktop --platform windows
if ($LASTEXITCODE -ne 0) { throw "桌面端打包失败（退出码 $LASTEXITCODE）" }

# ── 2. （可选）构建签发工具 ───────────────────────────────────────────────────
if ($WithAdmin) {
    Write-Host "`n==> [2/2] 构建管理员授权签发工具 ..." -ForegroundColor Cyan
    if (-not (Test-Path (Join-Path $root 'release\license-tool\wtcmd-license-tool.py'))) {
        Write-Host '   未检测到内嵌私钥的签发工具，先执行 init_license_keys.py 生成 ...' -ForegroundColor Yellow
        python scripts/init_license_keys.py
        if ($LASTEXITCODE -ne 0) { throw "生成授权密钥失败（退出码 $LASTEXITCODE）" }
    }
    python scripts/package.py --variant admin --platform windows
    if ($LASTEXITCODE -ne 0) { throw "签发工具构建失败（退出码 $LASTEXITCODE）" }
}

# ── 汇总 ──────────────────────────────────────────────────────────────────────
Write-Host "`n✓ 打包完成" -ForegroundColor Green
Write-Host "  桌面安装包：release\desktop\windows\" -ForegroundColor Green
if ($WithAdmin) {
    Write-Host "  签发工具：  release\license-admin\windows\wtcmd-license-admin.exe" -ForegroundColor Green
    Write-Host "`n[!] 签发工具内嵌授权私钥，仅限授权方管理员使用，切勿随桌面端分发给最终用户。" -ForegroundColor Yellow
}
