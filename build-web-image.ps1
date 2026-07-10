#requires -Version 5.1
<#
.SYNOPSIS
    构建 Web/服务端 Debian 一体化镜像并导出为交付用的 .tar。

.DESCRIPTION
    在本机（安装了 Docker Desktop / Docker Engine）执行，产出：
      - Docker 镜像 wtcmd-web:latest
      - 交付文件 wtcmd-web.tar（发给客户 IT）

    客户拿到 wtcmd-web.tar 后，配合同目录的 docker-compose.yml 与《部署说明.md》即可启动。

.EXAMPLE
    .\build-web-image.ps1
    .\build-web-image.ps1 -Tag wtcmd-web:1.0.0
#>
[CmdletBinding()]
param(
    [string]$Tag = 'wtcmd-web:latest',
    [string]$OutFile
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (-not $OutFile) { $OutFile = Join-Path $root 'wtcmd-web.tar' }

# 检查 Docker 是否可用
try { docker version --format '{{.Server.Version}}' | Out-Null }
catch { throw 'Docker 不可用：请先启动 Docker Desktop / Docker Engine 后重试。' }

Write-Host "==> 构建镜像 $Tag（上下文：$root）" -ForegroundColor Cyan
Push-Location $root
try {
    docker build -t $Tag .
    if ($LASTEXITCODE -ne 0) { throw "docker build 失败（退出码 $LASTEXITCODE）" }
}
finally {
    Pop-Location
}

Write-Host "==> 导出镜像到 $OutFile" -ForegroundColor Cyan
docker save -o $OutFile $Tag
if ($LASTEXITCODE -ne 0) { throw "docker save 失败（退出码 $LASTEXITCODE）" }

$sizeMB = [Math]::Round((Get-Item $OutFile).Length / 1MB, 1)
Write-Host ''
Write-Host "OK 镜像已构建：$Tag" -ForegroundColor Green
Write-Host "OK 交付文件：$OutFile ($sizeMB MB)" -ForegroundColor Green
Write-Host ''
Write-Host '交付给客户 IT 的文件：' -ForegroundColor Yellow
Write-Host '  1) wtcmd-web.tar'
Write-Host '  2) docker-compose.yml'
Write-Host '  3) 部署说明.md'
