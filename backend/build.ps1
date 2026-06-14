# Docker 构建脚本 — 在 Debian 容器中编译 Python 项目为独立二进制
# 用法: .\build.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== 1. 构建 Docker 编译镜像 ===" -ForegroundColor Cyan
docker build -t wtcmd-platform-builder -f Dockerfile.build .

Write-Host "`n=== 2. 提取编译产物 ===" -ForegroundColor Cyan
$cid = docker create wtcmd-platform-builder
docker cp "${cid}:/app/dist/wtcmd-platform-backend" ./wtcmd-platform-backend
docker rm $cid | Out-Null

Write-Host "`n=== 完成 ===" -ForegroundColor Green
Get-Item ./wtcmd-platform-backend | Format-List Name, Length, LastWriteTime
Write-Host "`n部署到 Debian 服务器后运行: ./wtcmd-platform-backend"
