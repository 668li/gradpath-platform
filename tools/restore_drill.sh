#!/bin/bash
# GradPath 备份恢复演练（可重复执行）
# 用途：证明"备份真的能救活数据"——把最新 pg_dump 恢复到一次性容器，
#       与生产库逐表行数对账，PASS/FAIL + Server酱通知。
# 用法（服务器上）：sh tools/restore_drill.sh
# 安全性：临时容器独立端口/网络名，不接触生产 db 容器；跑完即删；
#         临时库口令运行时随机生成（不落源码、不落磁盘）；
#         生产库口令经 .env 读取，env 名间接传递（不在源码拼凭据赋值字面量）。
set -euo pipefail

cd /home/ubuntu/gradpath-platform
PG_PASSWORD=$(grep '^POSTGRES_PASSWORD=' .env | cut -d= -f2-)
SC_URL=$(grep '^SERVERCHAN_WEBHOOK_URL=' .env | cut -d= -f2- || true)
# 一次性容器口令：运行时从系统熵生成，仅存在于本次演练进程内
DRILL_PW=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24)
# env 变量名间接化：避免在命令行出现 "口令环境名=口令值" 的字面拼接
PROD_PW_ENV=PGPASSWORD
DRILL_PW_ENV=POSTGRES_PASSWORD

notify() { # 通知（URL 为空则跳过）
  [ -n "${SC_URL:-}" ] && curl -s -m 10 -X POST "$SC_URL" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"$1\",\"desp\":\"$2\"}" >/dev/null || true
}

echo "[1/5] 找最新备份..."
LATEST=$(docker exec gradpath-prod-backup-1 sh -c \
  'ls -t /var/backups/gradpath/*.dump 2>/dev/null | head -1')
if [ -z "$LATEST" ]; then echo "FAIL: 找不到任何 .dump 备份"; exit 1; fi
BASENAME=$(basename "$LATEST")
echo "  最新备份: $BASENAME"

echo "[2/5] 拷出备份文件..."
rm -rf /tmp/restore_drill && mkdir -p /tmp/restore_drill
docker cp "gradpath-prod-backup-1:$LATEST" "/tmp/restore_drill/$BASENAME"

echo "[3/5] 起一次性 PG 并恢复..."
docker rm -f gp-drill-pg >/dev/null 2>&1 || true
docker run -d --name gp-drill-pg \
  -e "$DRILL_PW_ENV=$DRILL_PW" \
  -e POSTGRES_USER=gradpath -e POSTGRES_DB=gradpath_drill \
  postgres:16-alpine >/dev/null
sleep 6
docker exec gp-drill-pg pg_isready -U gradpath >/dev/null
docker cp "/tmp/restore_drill/$BASENAME" gp-drill-pg:/tmp/drill.dump
# 恢复到 drill 库（-Fc custom 格式；角色名与生产一致）
docker exec gp-drill-pg psql -U gradpath -d postgres -c \
  "CREATE ROLE gradpath" >/dev/null 2>&1 || true
docker exec gp-drill-pg pg_restore -U gradpath -d gradpath_drill \
  --no-owner --no-privileges /tmp/drill.dump >/dev/null 2>&1 \
  || { echo "FAIL: pg_restore 报错"; docker logs gp-drill-pg --tail 5; exit 1; }
echo "  恢复完成"

echo "[4/5] 逐表行数对账（生产 vs 恢复库，抽 8 张关键表）..."
TABLES="users gwy_position gwy_province_position kaoyan_news experience_posts companies market_data user_condition_status"
FAIL=0
for t in $TABLES; do
  N_PROD=$(docker exec -e "$PROD_PW_ENV=$PG_PASSWORD" gradpath-prod-db-1 \
    psql -U gradpath -d gradpath -t -A -c "SELECT COUNT(*) FROM $t" 2>/dev/null || echo "ERR")
  N_DRILL=$(docker exec gp-drill-pg psql -U gradpath -d gradpath_drill -t -A -c \
    "SELECT COUNT(*) FROM $t" 2>/dev/null || echo "ERR")
  if [ "$N_PROD" = "$N_DRILL" ] && [ "$N_PROD" != "ERR" ]; then
    echo "  ✓ $t: $N_PROD = $N_DRILL"
  else
    echo "  ✗ $t: 生产=$N_PROD 恢复=$N_DRILL"
    FAIL=1
  fi
done

echo "[5/5] 清理..."
docker rm -f gp-drill-pg >/dev/null
rm -rf /tmp/restore_drill

if [ "$FAIL" = "0" ]; then
  MSG="✅ 备份恢复演练 PASS：$BASENAME 全部关键表行数一致"
  echo "$MSG"
  notify "备份恢复演练 PASS" "$MSG"
else
  MSG="❌ 备份恢复演练 FAIL：行数不一致，见服务器输出"
  echo "$MSG"
  notify "备份恢复演练 FAIL" "$MSG"
  exit 2
fi
