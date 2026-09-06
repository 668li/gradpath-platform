#!/bin/sh
# GradPath 服务器增量更新脚本（服务器上执行）
# 用法: sh update_from_bundle.sh /tmp/gp.bundle
# 前置: 本地已 git bundle create /tmp/gp.bundle main 并 scp 到服务器 /tmp/
# 行为: 快进合并代码 → 重建变更镜像（国内源）→ 滚动重启 → alembic 升级
# 2026-09-05: PIP_INDEX_URL 阿里云→腾讯云内网源（实测阿里源 prune 后冷构建 ~100kB/s 超 40min，
#   腾讯源同机房全量 pip install 仅 8.9s；旧版备份 update_from_bundle.sh.bak-aliyun）
# ⚠️ 此为三道机器闸上线前（2026-09-05 晚）的版本留档。现行版本=tools/update_from_bundle_v2.sh
#   （flock 互斥/磁盘 6G 闸/部署后自动缓存回收）。回滚=把本文件内容 scp 回服务器同名路径。
set -e
BUNDLE=${1:?用法: sh update_from_bundle.sh /tmp/gp.bundle}
cd /home/ubuntu/gradpath-platform

echo "[1/4] 拉取并快进合并..."
git fetch "$BUNDLE" main
git merge --ff-only FETCH_HEAD
git log --oneline -1

echo "[2/4] 重建镜像（apt/pip/npm 层有缓存，通常 2-5 分钟）..."
docker compose -f docker-compose.prod.yml -f docker-compose.grey.yml build \
  --build-arg PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple/ \
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
