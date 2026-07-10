#requires -Version 5.1
<#
.SYNOPSIS
    将项目源代码打包为 zip，交付给客户自行安装依赖并构建。

.DESCRIPTION
    面向“只会装 Python 和 Node.js”的客户：解压后直接运行根目录的
    package-desktop.ps1 / package-sign-tool.ps1 即可打包桌面端与授权签发工具。

    仅拷贝打包所必需的源代码，并：
      - 包含 scripts/keys/（公钥 + 私钥），使客户无需额外密钥即可自助打包签发工具；
      - 自动排除：文档(document/)、发布目录(release/)、编译缓存、
        前端依赖(node_modules) 与虚拟环境(.venv)、
        Web/Docker 交付物（Dockerfile / compose / 镜像 tar / 部署说明）、
        开发调试用脚本、数据库 / 日志 / 本地 .env 等运行期文件。

    生成的 zip 位于 code-package/ 目录。

    ⚠！本源码包内含授权私钥（scripts/keys/private_key.pem），属敏感交付物，
       请仅向可信客户交付并告知其妥善保管。

.EXAMPLE
    .\package-source.ps1
    .\package-source.ps1 -OutputDir D:\deliver
#>
[CmdletBinding()]
param(
    [string]$OutputDir = (Join-Path $PSScriptRoot 'code-package')
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path $PSScriptRoot).Path
$outputDirResolved = [System.IO.Path]::GetFullPath($OutputDir)

# ── 排除规则 ──────────────────────────────────────────────────────────────────
# 按目录名排除（任意层级，命中即整目录跳过，避免遍历 node_modules 等海量文件）
$excludeDirNames = @(
    'node_modules', '__pycache__', '.pytest_cache', '.ruff_cache', '.git',
    '.venv', 'venv', '.idea', '.vscode', 'dist', 'build',
    '_pdf_pages', 'manual_screenshots'
)

# 按相对路径排除的目录（相对项目根）
$excludeRelDirs = @(
    'document', 'release', '.agents', 'delivery', 'code-package',
    'backend\tests'
)

# 按文件名 / 扩展名通配排除（注意：不再排除 *.pem/*.key/*.bin，以便包含 scripts/keys）
$excludeFilePatterns = @(
    '*.pyc', '*.pyo', '*.pyd', '*.log', '*.log.*',
    '*.db', '*.db-journal', '*.sqlite', '*.sqlite3',
    '*.spec.bak', '*.tar',
    '.DS_Store', 'Thumbs.db',
    'wtcmd-platform-backend', 'wtcmd-platform-backend.exe', '_t.txt'
)

# 精确排除的文件（相对路径）：Web/Docker 交付物、开发调试脚本、自身
$excludeRelFiles = @(
    'frontend\.env', 'backend\.env', 'desktop\.env',
    'scripts\license_dev.py', 'scripts\expire_trial.py', 'scripts\decrypt_db.py',
    'scripts\verify_legacy_upgrade.py', 'scripts\extract_public_key.py',
    'frontend\find_words.py', 'frontend\fix_typo.py'
)

function Test-RelDirExcluded {
    param([string]$rel)
    foreach ($d in $excludeRelDirs) {
        if ($rel -ieq $d -or $rel.StartsWith("$d\", [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Test-FileExcluded {
    param([System.IO.FileInfo]$file)
    $rel = $file.FullName.Substring($root.Length).TrimStart('\', '/')
    foreach ($f in $excludeRelFiles) {
        if ($rel -ieq $f) { return $true }
    }
    foreach ($pat in $excludeFilePatterns) {
        if ($file.Name -like $pat) { return $true }
    }
    return $false
}

# ── 拷贝到暂存目录（剪枝式递归，跳过被排除的目录）────────────────────────────
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$pkgName = "shuini_calculator_src_$stamp"
$stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) "shuini_src_$stamp"
$stage = Join-Path $stageRoot $pkgName
New-Item -ItemType Directory -Path $stage -Force | Out-Null

$script:copiedCount = 0

function Copy-Tree {
    param([string]$dir)
    foreach ($item in Get-ChildItem -LiteralPath $dir -Force) {
        if ($item.PSIsContainer) {
            if ($excludeDirNames -contains $item.Name) { continue }
            if ([System.IO.Path]::GetFullPath($item.FullName) -eq $outputDirResolved) { continue }
            $relDir = $item.FullName.Substring($root.Length).TrimStart('\', '/')
            if (Test-RelDirExcluded $relDir) { continue }
            Copy-Tree $item.FullName
        }
        else {
            if (Test-FileExcluded $item) { continue }
            $rel = $item.FullName.Substring($root.Length).TrimStart('\', '/')
            $dest = Join-Path $stage $rel
            $destDir = Split-Path $dest -Parent
            if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
            Copy-Item -LiteralPath $item.FullName -Destination $dest -Force
            $script:copiedCount++
        }
    }
}

Write-Host '正在收集源代码...' -ForegroundColor Cyan
Copy-Tree $root

# ── 压缩 ──────────────────────────────────────────────────────────────────────
if (-not (Test-Path $outputDirResolved)) {
    New-Item -ItemType Directory -Path $outputDirResolved -Force | Out-Null
}
$zipPath = Join-Path $outputDirResolved "$pkgName.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Write-Host '正在压缩...' -ForegroundColor Cyan
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zipPath -CompressionLevel Optimal

Remove-Item -Path $stageRoot -Recurse -Force

$sizeMB = [Math]::Round((Get-Item $zipPath).Length / 1MB, 2)
Write-Host ''
Write-Host "OK 已打包 $script:copiedCount 个文件" -ForegroundColor Green
Write-Host "OK 输出：$zipPath ($sizeMB MB)" -ForegroundColor Green
Write-Host ''
Write-Host '提示：本源码包已按要求包含 scripts/keys（含私钥），属敏感交付物，请仅向可信客户交付。' -ForegroundColor Yellow -ForegroundColor Yellow
