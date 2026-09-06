#!/usr/bin/env bash
# 数据纯净度哨兵 — cron 每日一次（2026-09-05 整改，用户拍板"我不要出现假数据"）
# 检查所有用户可见内容表：非用户来源无溯源 / 孤儿向量 / 假爬虫回流 → Server酱推送告警。
# 与 sec_watcher.sh 解耦：本脚本日检低频查询，不复用其每分钟窗口。
# 本脚本只读+推送，不改任何数据。
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
ALERTS="$BASE/alerts.log"
WEBHOOK_FILE="/home/ubuntu/.sec_webhook_url"
LOG="$BASE/state/purity.log"
mkdir -p "$BASE/state"

PSQL="docker exec gradpath-prod-db-1 psql -U gradpath -d gradpath -t -A -c"

VIOLATIONS=""
check() {
  # check KEY SQL —— 违规行数 >0 即记入 VIOLATIONS
  local key="$1" sql="$2"
  local n
  n=$($PSQL "$sql" 2>/dev/null) || { VIOLATIONS="$VIOLATIONS\n[ERROR] $key 查询失败"; return; }
  if [ "${n:-0}" -gt 0 ]; then
    VIOLATIONS="$VIOLATIONS\n[key=$key 违规行数=$n]"
  fi
}

# 1. 社区表被非用户来源污染
check community_non_user "SELECT count(*) FROM experience_posts WHERE source_platform IS NOT NULL AND source_platform <> 'user' AND (source_url IS NULL OR source_url = '')"
check posts_by_system "SELECT count(*) FROM posts WHERE user_id::text = '00000000-0000-0000-0000-000000000000'"
check qas_by_system "SELECT count(*) FROM qas WHERE user_id::text = '00000000-0000-0000-0000-000000000000'"

# 2. 真实性门禁域：机器供给内容无溯源（CHECK 约束已挡写入，此处兜底防约束被移除）
check mentors_sourceless "SELECT count(*) FROM mentors WHERE source_url IS NULL OR source_url = ''"
check market_data_sourceless "SELECT count(*) FROM market_data WHERE source_url IS NULL OR source_url = ''"
check ext_research_sourceless "SELECT count(*) FROM t_external_research_item WHERE source_url IS NULL OR source_url = ''"
check yanzhao_sourceless "SELECT count(*) FROM grad_yanzhao_programs WHERE source_url IS NULL OR source_url = ''"

# 3. 孤儿向量（源行不存在，语义检索会复活已删内容）
check orphan_vectors "SELECT count(*) FROM document_embeddings e WHERE (e.source_table='experience_post' AND NOT EXISTS (SELECT 1 FROM experience_posts p WHERE p.id=e.source_id)) OR (e.source_table='qa' AND NOT EXISTS (SELECT 1 FROM qas q WHERE q.id=e.source_id))"

# 4. 假考公情报回流 / mentors 回流后的无源行
check intel_regress "SELECT count(*) FROM civil_service_post_intel WHERE data_sources IS NULL OR data_sources::text IN ('[]','null')"

TS=$(date '+%F %T')
if [ -n "$VIOLATIONS" ]; then
  printf '%s [PURITY-ALERT]%s\n' "$TS" "$VIOLATIONS" >> "$ALERTS"
  printf '%s [PURITY-ALERT]%s\n' "$TS" "$VIOLATIONS" >> "$LOG"
  if [ -f "$WEBHOOK_FILE" ]; then
    BODY=$(printf '%s' "$VIOLATIONS" | tr '\n' ' ' | head -c 300)
    curl -s -m 10 "$(cat "$WEBHOOK_FILE")" \
      -d "title=数据纯净度哨兵告警" \
      -d "desp=生产内容表出现无溯源/污染数据：$BODY" >/dev/null 2>&1
  fi
  exit 1
fi

printf '%s [PURITY-OK] 全部检查通过\n' "$TS" >> "$LOG"
exit 0
