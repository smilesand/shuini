#requires -Version 5.1
<#
.SYNOPSIS
    准备本机打包环境：检查 Python / Node，创建独立虚拟环境(.venv)，安装依赖。

.DESCRIPTION
    面向「只装过 Python 和 Node.js」的使用者。本脚本会：
      1. 检查 python / node / npm 是否已安装（缺失则给出安装指引并中止）；
      2. 在项目根目录创建独立虚拟环境 .venv（不污染系统 Python）；
      3. 在 .venv 中安装后端依赖 + 打包工具(PyInstaller)；
      4. 为前端(frontend)、以及可选的桌面壳(desktop) 安装 npm 依赖。

    幂等：重复执行会自动跳过已完成的步骤。返回 .venv 的 python 路径供调用方使用。

    ⚠️ 全程只在项目内的 .venv 与各自的 node_modules 中操作，不修改系统环境。

.PARAMETER Desktop
    同时为桌面壳目录(desktop/)安装 npm 依赖（打包桌面端时需要）。

.PARAMETER Frontend
    为前端目录(frontend/)安装 npm 依赖（打包 Web/桌面前端时需要）。

.OUTPUTS
    [string] .venv 中 python 可执行文件的完整路径。
#>
[CmdletBinding()]
param(
    [switch]$Frontend,
    [switch]$Desktop
)

$ErrorActionPreference = 'Stop'

# 项目根目录（本脚本位于 <root>/scripts/）
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvDir = Join-Path $root '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$depsMarker = Join-Path $venvDir '.build-deps-ok'

function Write-Step($msg) { Write-Host "[env] $msg" -ForegroundColor Cyan }
function Write-Warn2($msg) { Write-Host "[env] $msg" -ForegroundColor Yellow }

# ── 1. 检查系统 Python（要求 3.10~3.12：numpy/scipy 仅提供到 3.12 的预编译包）──
$MinMinor = 10
$MaxMinor = 12

function Get-PythonInfo {
    param([string]$Launcher, [string[]]$LaunchArgs)
    try {
        $out = & $Launcher @LaunchArgs -c "import sys;print('%d.%d'%sys.version_info[:2]);print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            $lines = @($out -split "`r?`n" | Where-Object { $_ })
            if ($lines.Count -ge 2) {
                return @{ Launcher = $Launcher; LaunchArgs = $LaunchArgs; Ver = $lines[0]; Exe = $lines[1] }
            }
        }
    } catch { }
    return $null
}

function Test-Supported {
    param([string]$ver)
    $parts = $ver -split '\.'
    return ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge $MinMinor -and [int]$parts[1] -le $MaxMinor)
}

function Resolve-SystemPython {
    $candidates = @()
    # 优先用 py 启动器精确定位 3.12 / 3.11 / 3.10
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($m in 12, 11, 10) { $candidates += (Get-PythonInfo 'py' @("-3.$m")) }
    }
    # 再考虑 PATH 中的 python / py 默认版本
    foreach ($cmd in 'python', 'py') {
        $c = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($c) { $candidates += (Get-PythonInfo $c.Source @()) }
    }
    $candidates = @($candidates | Where-Object { $_ -ne $null })

    foreach ($cand in $candidates) {
        if (Test-Supported $cand.Ver) { return $cand }
    }
    if ($candidates.Count -gt 0) {
        return @{ Unsupported = $true; Ver = $candidates[0].Ver; Exe = $candidates[0].Exe }
    }
    return $null
}

$sysPy = Resolve-SystemPython
if (-not $sysPy) {
    throw @"
未检测到 Python。请先安装 Python 3.12（推荐）：
  1) 打开 https://www.python.org/downloads/release/python-3129/
  2) 下载并安装，安装时务必勾选「Add Python to PATH」
  3) 安装完成后重新打开 PowerShell，再次运行本脚本
"@
}
if ($sysPy.Unsupported) {
    throw @"
检测到 Python $($sysPy.Ver)（$($sysPy.Exe)），但本项目依赖的 numpy/scipy 仅提供到
Python 3.12 的预编译包，3.13+ 需要额外的编译器且极易失败。
请安装 Python 3.12（可与现有版本共存，无需卸载）：
  1) 打开 https://www.python.org/downloads/release/python-3129/
  2) 下载并安装，安装时勾选「Add Python to PATH」
  3) 重新打开 PowerShell，再次运行本脚本
安装后脚本会自动优先使用 3.12 创建虚拟环境。
"@
}
Write-Step "系统 Python：$($sysPy.Exe)（版本 $($sysPy.Ver)）"

# ── 2. 创建虚拟环境 .venv ─────────────────────────────────────────────────────
if (-not (Test-Path $venvPython)) {
    Write-Step "创建虚拟环境 .venv（不影响系统 Python）..."
    & $sysPy.Launcher @($sysPy.LaunchArgs) -m venv $venvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) {
        throw "创建虚拟环境失败。请确认已安装 Python 的 venv 模块（标准发行版自带）。"
    }
} else {
    Write-Step "已存在虚拟环境 .venv，复用。"
}

# ── 3. 安装后端依赖 + 打包工具（幂等，用标记跳过） ────────────────────────────
# if (-not (Test-Path $depsMarker)) {
#     Write-Step "在 .venv 中安装后端依赖与打包工具（首次较慢，请耐心等待）..."
#     & $venvPython -m pip install --upgrade pip
#     if ($LASTEXITCODE -ne 0) { throw "升级 pip 失败。" }
#     & $venvPython -m pip install -r (Join-Path $root 'backend\requirements.txt') -r (Join-Path $root 'backend\requirements-dev.txt')
#     if ($LASTEXITCODE -ne 0) { throw "安装 Python 依赖失败，请检查网络后重试。" }
#     New-Item -ItemType File -Path $depsMarker -Force | Out-Null
#     Write-Step "Python 依赖安装完成。"
# } else {
#     Write-Step "Python 依赖已就绪，跳过。"
# }

# ── 4. 检查 Node / npm 并安装前端依赖 ─────────────────────────────────────────
if ($Frontend -or $Desktop) {
    $node = Get-Command node -ErrorAction SilentlyContinue
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $node -or -not $npm) {
        throw @"
未检测到 Node.js / npm。请先安装 Node.js 18 (LTS) 或更高版本：
  1) 打开 https://nodejs.org/
  2) 下载并安装 LTS 版本（默认会加入 PATH）
  3) 安装完成后重新打开 PowerShell，再次运行本脚本
"@
    }
    Write-Step "Node.js：$(& node --version)"
}

if ($Frontend) {
    $feModules = Join-Path $root 'frontend\node_modules'
    if (-not (Test-Path $feModules)) {
        Write-Step "安装前端依赖(frontend)：npm install ..."
        Push-Location (Join-Path $root 'frontend')
        try { & npm install; if ($LASTEXITCODE -ne 0) { throw '前端 npm install 失败。' } }
        finally { Pop-Location }
    } else {
        Write-Step "前端依赖已存在，跳过。"
    }
}

if ($Desktop) {
    $deModules = Join-Path $root 'desktop\node_modules'
    if (-not (Test-Path $deModules)) {
        Write-Step "安装桌面壳依赖(desktop)：npm install ..."
        Push-Location (Join-Path $root 'desktop')
        try { & npm install; if ($LASTEXITCODE -ne 0) { throw '桌面壳 npm install 失败。' } }
        finally { Pop-Location }
    } else {
        Write-Step "桌面壳依赖已存在，跳过。"
    }
}

Write-Step "环境就绪。"
