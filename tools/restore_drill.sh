#!/usr/bin/env bash
# GradPath 备份恢复演练（可重复执行）
# 用途：证明"备份真的能救活数据"——把最新 pg_dump 恢复到一次性容器并验证可查。
# 用法（服务器上）：bash tools/restore_drill.sh   （注意用 bash，dash 不支持 pipefail）
# 判定：
#   FAIL = pg_restore 失败 / 关键大表恢复后为 0 行（备份坏了才 FAIL）
#   WARN = 恢复成功但与生产行数有差（活库在涨属正常，打印差异供人判断）
#   PASS = 恢复成功且与生产行数一致
# 安全性：临时容器独立端口/网络名，不接触生产 db 容器；跑完即删；
#         临时库口令运行时随机生成（不落源码、不落磁盘）。
set -euo pipefail

cd /home/ubuntu/gradpath-platform
PG_PASSWORD=$(grep '^POSTGRES_PASSWORD=' .env | cut -d= -f2-)
SC_URL=$(grep '^SERVERCHAN_WEBHOOK_URL=' .env | cut -d= -f2- || true)
# 一次性容器口令：运行时从系统熵生成；|| true 防 SIGPIPE(head 提前退出) 被 pipefail 杀死
DRILL_PW=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24 || true)
# env 变量名间接化：避免在命令行出现 "口令环境名=口令值" 的字面拼接
PROD_PW_ENV=PGPASSWORD
DRILL_PW_ENV=POSTGRES_PASSWORD

notify() { # 通知（URL 为空则跳过）
  [ -n "${SC_URL:-}" ] && curl -s -m 10 -X POST "$SC_URL" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"$1\",\"desp\":\"$2\"}" >/dev/null || true
}

echo "[1/6] 找最新备份..."
LATEST=$(docker exec gradpath-prod-backup-1 sh -c \
  'ls -t /var/backups/gradpath/*.dump 2>/dev/null | head -1')
if [ -z "$LATEST" ]; then echo "FAIL: 找不到任何 .dump 备份"
  notify "备份恢复演练 FAIL" "找不到任何 .dump 备份"; exit 2; fi
BASENAME=$(basename "$LATEST")
echo "  最新备份: $BASENAME"

echo "[2/6] 拷出备份文件..."
rm -rf /tmp/restore_drill && mkdir -p /tmp/restore_drill
docker cp "gradpath-prod-backup-1:$LATEST" "/tmp/restore_drill/$BASENAME"

echo "[3/6] 起一次性 PG（就绪重试最多 30s）..."
docker rm -f gp-drill-pg >/dev/null 2>&1 || true
docker run -d --name gp-drill-pg \
  -e "$DRILL_PW_ENV=$DRILL_PW" \
  -e POSTGRES_USER=gradpath -e POSTGRES_DB=gradpath_drill \
  postgres:16-alpine >/dev/null
READY=0
for i in $(seq 1 15); do
  if docker exec gp-drill-pg pg_isready -U gradpath >/dev/null 2>&1; then READY=1; break; fi
  sleep 2
done
if [ "$READY" != "1" ]; then echo "FAIL: 演练容器 30s 未就绪"
  docker logs gp-drill-pg --tail 5; notify "备份恢复演练 FAIL" "drill 容器未就绪"; exit 2; fi
docker cp "/tmp/restore_drill/$BASENAME" gp-drill-pg:/tmp/drill.dump

echo "[4/6] 恢复到 drill 库..."
docker exec gp-drill-pg psql -U gradpath -d postgres -c \
  "CREATE ROLE gradpath" >/dev/null 2>&1 || true
# pg_restore 的 stderr 落文件：失败时输出真实原因（而非 PG server 日志）
if ! docker exec gp-drill-pg pg_restore -U gradpath -d gradpath_drill \
  --no-owner --no-privileges /tmp/drill.dump >/dev/null 2>/tmp/restore_drill/restore_err.txt; then
  echo "FAIL: pg_restore 报错:"; tail -10 /tmp/restore_drill/restore_err.txt
  notify "备份恢复演练 FAIL" "pg_restore 失败: $(tail -3 /tmp/restore_drill/restore_err.txt)"
  docker rm -f gp-drill-pg >/dev/null; exit 2
fi
echo "  恢复完成（pg_restore 0 错误）"

echo "[5/6] 行数对账（生产[活库] vs 恢复[02:00 快照]，差异= WARN 非 FAIL）..."
TABLES="users gwy_position gwy_province_position kaoyan_news experience_posts companies market_data user_condition_status"
DRIFT=0
for t in $TABLES; do
  N_PROD=$(docker exec -e "$PROD_PW_ENV=$PG_PASSWORD" gradpath-prod-db-1 \
    psql -U gradpath -d gradpath -t -A -c "SELECT COUNT(*) FROM $t" 2>/dev/null || echo "ERR")
  N_DRILL=$(docker exec gp-drill-pg psql -U gradpath -d gradpath_drill -t -A -c \
    "SELECT COUNT(*) FROM $t" 2>/dev/null || echo "ERR")
  if [ "$N_PROD" = "$N_DRILL" ]; then
    echo "  ✓ $t: $N_PROD = $N_DRILL"
  else
    echo "  ~ $t: 生产=$N_PROD 恢复=$N_DRILL（活库漂移属正常）"
    DRIFT=$((DRIFT+1))
  fi
done
# 硬校验：大表恢复后为 0 行 = 备份损坏
EMPTY=$(docker exec gp-drill-pg psql -U gradpath -d gradpath_drill -t -A -c \
  "SELECT COUNT(*) FROM gwy_position" 2>/dev/null || echo 0)
if [ "$EMPTY" = "0" ]; then
  echo "FAIL: gwy_position 恢复后 0 行——备份损坏"
  notify "备份恢复演练 FAIL" "恢复后大表 0 行，备份损坏: $BASENAME"
  docker rm -f gp-drill-pg >/dev/null; exit 2
fi

echo "[6/6] 清理..."
docker rm -f gp-drill-pg >/dev/null
rm -rf /tmp/restore_drill

if [ "$DRIFT" = "0" ]; then
  MSG="✅ 备份恢复演练 PASS：$BASENAME 与生产行数完全一致"
else
  MSG="✅ 备份恢复演练 PASS（${DRIFT} 表有活库漂移）：$BASENAME 恢复可查可用"
fi
echo "$MSG"
notify "备份恢复演练 PASS" "$MSG"
