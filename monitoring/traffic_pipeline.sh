#!/usr/bin/env bash
# 站点流量日聚合入库：nginx 日志 + users 注册数 → t_traffic_daily（/admin/traffic 看板数据源）
# 可借鉴模式：宿主只读聚合 → DB 日聚合宽表 → admin API → 前端看板。
# 其他指标（留存/转化漏斗新环节）在此宽表加列、同管道入库即可，不必各起炉灶。
# 用法: traffic_pipeline.sh [N]   # 聚合最近 N 天（默认 8 = 7 个完整日 + 今日快照）
#       cron 21:50 每日跑；幂等 upsert，当日部分快照会被次日运行覆盖成完整日。
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
N="${1:-8}"
PSQL="docker exec gradpath-prod-db-1 psql -U gradpath -d gradpath"

# 复用 visitors.sh 的同一套统计口径（window_stats）；无参 source 不会触发推送
# shellcheck source=visitors.sh
source "$BASE/visitors.sh" >/dev/null 2>&1

echo "=== traffic_pipeline start $(date '+%F %T') N=$N ==="
for i in $(seq 0 $((N - 1))); do
  DAY=$(TZ=Asia/Shanghai date -d "$i days ago" +%F)
  S=$(TZ=Asia/Shanghai date -d "$DAY 00:00" +%s)
  E=$((S + 86400))
  OUT=$(window_stats "$S" "$E")
  read -r PV UV BLK _TOT <<< "$(printf '%s\n' "$OUT" | head -1)"
  REG=$($PSQL -tAc "SELECT count(*) FROM users WHERE (created_at AT TIME ZONE 'Asia/Shanghai')::date = DATE '$DAY'")
  $PSQL -c "INSERT INTO t_traffic_daily (date, pv, uv, blocked, registrations, created_at, updated_at)
            VALUES ('$DAY', $PV, $UV, $BLK, $REG, now(), now())
            ON CONFLICT (date) DO UPDATE SET
              pv=EXCLUDED.pv, uv=EXCLUDED.uv, blocked=EXCLUDED.blocked,
              registrations=EXCLUDED.registrations, updated_at=now()" >/dev/null
  echo "$DAY pv=$PV uv=$UV blocked=$BLK reg=$REG"
done
echo "=== traffic_pipeline done $(date '+%F %T') ==="
