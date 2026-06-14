#!/bin/bash
# Docker 构建脚本 — 在 Debian 容器中编译 Python 项目为独立二进制
# 用法: bash build.sh

set -e

echo "=== 1. 构建 Docker 编译镜像 ==="
docker build -t wtcmd-platform-builder -f Dockerfile.build .

echo ""
echo "=== 2. 提取编译产物 ==="
CID=$(docker create wtcmd-platform-builder)
docker cp "${CID}:/app/dist/wtcmd-platform-backend" ./wtcmd-platform-backend
docker rm "$CID"

echo ""
echo "=== 完成 ==="
ls -lh ./wtcmd-platform-backend
echo ""
echo "部署到 Debian 服务器后运行: ./wtcmd-platform-backend"
