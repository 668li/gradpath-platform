#!/bin/sh
# GradPath 服务器更新脚本（GitHub SSH Deploy Key 直连版）
# 用法:
#   sh update_server.sh                      # git pull + 重建 backend/frontend/celery + 重启 + 迁移
#   sh update_server.sh backend              # 只重建 backend（celery 同镜像自动受益）
#   sh update_server.sh frontend             # 只重建 frontend
#   SKIP_PULL=1 sh update_server.sh backend  # 跳过 git pull（代码已就位时）
# 备胎: GitHub SSH 通道被墙时用 bundle——本地 git bundle create /tmp/gp.bundle main
#       并 scp 到服务器后: sh update_server.sh backend frontend celery-worker /tmp/gp.bundle
set -e
cd /home/ubuntu/gradpath-platform

BUNDLE=""
SERVICES=""
for a in "$@"; do
  case "$a" in
    /tmp/*|*.bundle) BUNDLE="$a" ;;
    *) SERVICES="$SERVICES $a" ;;
  esac
done
[ -n "$SERVICES" ] || SERVICES="backend frontend celery-worker"

if [ -n "$BUNDLE" ]; then
  echo "[pull] 从 bundle 快进: $BUNDLE"
  git fetch "$BUNDLE" main && git merge --ff-only FETCH_HEAD
elif [ -z "$SKIP_PULL" ]; then
  echo "[pull] GitHub 直连..."
  git pull --ff-only
fi
git log --oneline -1

echo "[build] 重建:$SERVICES（依赖层有缓存，源码变更通常 1-2 分钟）"
docker compose -f docker-compose.prod.yml -f docker-compose.grey.yml build \
  --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
  --build-arg NPM_REGISTRY=https://registry.npmmirror.com \
  $SERVICES

echo "[restart] 滚动重启..."
docker compose -f docker-compose.prod.yml -f docker-compose.grey.yml up -d --pull never --remove-orphans

echo "[migrate] 数据库迁移到 head..."
sleep 15
docker exec gradpath-prod-backend-1 sh -c "cd /app && python -m alembic upgrade head"

echo "=== 更新完成 ==="
docker compose -f docker-compose.prod.yml -f docker-compose.grey.yml ps --format "{{.Name}} {{.Status}}"
