#!/bin/sh
# GradPath 服务器增量更新脚本（服务器上执行）
# 用法: sh update_from_bundle.sh /tmp/gp.bundle
# 前置: 本地已 git bundle create /tmp/gp.bundle main 并 scp 到服务器 /tmp/
# 行为: 快进合并代码 → 重建变更镜像（国内源）→ 滚动重启 → alembic 升级
set -e
BUNDLE=${1:?用法: sh update_from_bundle.sh /tmp/gp.bundle}
cd /home/ubuntu/gradpath-platform

echo "[1/4] 拉取并快进合并..."
git fetch "$BUNDLE" main
git merge --ff-only FETCH_HEAD
git log --oneline -1

echo "[2/4] 重建镜像（apt/pip/npm 层有缓存，通常 2-5 分钟）..."
docker compose -f docker-compose.prod.yml -f docker-compose.grey.yml build \
  --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
  --build-arg DEBIAN_MIRROR=http://mirrors.tencentyun.com \
  --build-arg NPM_REGISTRY=https://registry.npmmirror.com \
  backend frontend celery-worker

echo "[3/4] 滚动重启..."
docker compose -f docker-compose.prod.yml -f docker-compose.grey.yml up -d --pull never --remove-orphans

echo "[4/4] 数据库迁移到 head..."
sleep 15
docker exec gradpath-prod-backend-1 sh -c "cd /app && python -m alembic upgrade head"

echo "=== 更新完成 ==="
docker compose -f docker-compose.prod.yml -f docker-compose.grey.yml ps --format "{{.Name}} {{.Status}}"
