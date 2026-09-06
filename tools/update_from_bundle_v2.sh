#!/bin/sh
# GradPath 服务器增量更新脚本（服务器上执行）
# 用法: sh update_from_bundle.sh /tmp/gp.bundle
# 前置: 本地已 git bundle create /tmp/gp.bundle main 并 scp 到服务器 /tmp/
# 行为: 快进合并代码 → 重建变更镜像（国内源）→ 滚动重启 → alembic 升级
# 2026-09-05: PIP_INDEX_URL 阿里云→腾讯云内网源（实测阿里源 prune 后冷构建 ~100kB/s 超 40min，
#   腾讯源同机房全量 pip install 仅 8.9s；旧版备份 update_from_bundle.sh.bak-aliyun）
# 2026-09-05 晚: 三道机器闸（用户拍板，起因=两会话并发部署互踩+构建峰值打爆磁盘 1.2G 残水）：
#   闸1 flock 互斥——并发部署探测是瞬时采样，两秒窗口照样撞车（当日实锤）；真互斥锁原子拒绝
#   闸2 磁盘闸——可用 <6GB 拒绝开建（当日实锤 no space left on device 死在 compose 元数据写入）
#   闸3 部署成功后自动回收构建缓存至 8GB——buildkit 债不再无界累积（当日曾滚到 39.8GB）
set -e
BUNDLE=${1:?用法: sh update_from_bundle.sh /tmp/gp.bundle}

# ── 闸1：部署互斥锁（fd 9 持锁至脚本退出，原子性由 flock 保证）──
exec 9>/tmp/gradpath-deploy.lock
if ! flock -n 9; then
  echo "❌ 拒绝部署：另一个 update_from_bundle 正在运行（锁 /tmp/gradpath-deploy.lock 被持有）。"
  echo "   并发部署 = 构建互锁 40min+ / 磁盘互踩（2026-09-05 实锤）。等它结束后再上。"
  exit 1
fi

# ── 闸2：磁盘水位（构建峰值可吃 8G+，<6GB 一律先拍板 prune）──
AVAIL_KB=$(df --output=avail / | tail -1 | tr -d '[:space:]')
if [ "${AVAIL_KB:-0}" -lt 6291456 ]; then
  echo "❌ 拒绝部署：根分区仅 ${AVAIL_KB}KB 可用（<6GB）。"
  echo "   构建峰值曾打爆磁盘（2026-09-05 实锤）。需先拍板执行 docker builder prune。"
  exit 1
fi

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

echo "[5/5] 构建缓存回收（保留 8GB 加速余量，防债务复发）..."
docker builder prune -f --keep-storage 8GB >/dev/null 2>&1 || true

echo "=== 更新完成 ==="
docker compose -f docker-compose.prod.yml -f docker-compose.grey.yml ps --format "{{.Name}} {{.Status}}"
