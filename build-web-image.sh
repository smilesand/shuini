#!/usr/bin/env bash
# =============================================================================
# 构建 Web/服务端 Debian 一体化镜像并导出为交付用的 .tar。
#
# 在安装了 Docker Engine 的 Linux 机器上执行，产出：
#   - Docker 镜像 wtcmd-web:latest
#   - 交付文件 wtcmd-web.tar（发给客户 IT）
#
# 用法：
#   bash build-web-image.sh
#   bash build-web-image.sh wtcmd-web:1.0.0 ./out/wtcmd-web.tar
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")"

TAG="${1:-wtcmd-web:latest}"
OUTFILE="${2:-$(pwd)/wtcmd-web.tar}"

# ── 检查 Docker ──────────────────────────────────────────────────────────────
if ! docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
    echo '❌ Docker 不可用：请先安装并启动 Docker Engine 后重试。'
    exit 1
fi

# ── 构建镜像 ─────────────────────────────────────────────────────────────────
echo "==> 构建镜像 ${TAG}（上下文：$(pwd)）"
docker build -t "${TAG}" .

# ── 导出 ─────────────────────────────────────────────────────────────────────
echo "==> 导出镜像到 ${OUTFILE}"
docker save -o "${OUTFILE}" "${TAG}"

# ── 汇总 ─────────────────────────────────────────────────────────────────────
SIZE=$(du -h "${OUTFILE}" | cut -f1)
echo ''
echo "✅ 镜像已构建：${TAG}"
echo "✅ 交付文件：${OUTFILE}（${SIZE}）"
echo ''
echo '交付给客户 IT 的文件：'
echo '  1) wtcmd-web.tar'
echo '  2) docker-compose.yml'
echo '  3) 部署说明.md'
