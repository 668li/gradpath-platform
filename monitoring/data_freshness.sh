#!/bin/sh
# 数据新鲜度监控 v1（2026-09-05）：逐校静默断供检测。
#
# 背景：增量架构下爬虫整体"成功"会掩盖单校静默失明——列表页改版/被挡时
# 该校每次都"解析 0 条"，crawler_runs 仍 success，没人知道信息差断了。
#
# 红警：最近 24h official_announce 的某校栏目每一次运行都"解析 0 条"
#       （样本 ≥3 次；=该校列表页结构变化/被挡，爬虫活着但该校失明）
# 黄警：某校域名最近 45 天在 t_external_research_item 零新增（内容老化，人工复核）
# 推送：复用 sec_watcher 的 Server酱通道（/home/ubuntu/.sec_webhook_url，绝不入库）
# 防骚扰：每校每类每天最多推送一次（state/ 下按天去重）
# 只读：不写任何业务数据。cron 建议：20 * * * *（整点爬取+自动放行之后）

set -u
BASE="/home/ubuntu/gradpath-platform/monitoring"
STATE="$BASE/state/data_freshness"
LOG="$BASE/state/data_freshness.log"
WEBHOOK_FILE="/home/ubuntu/.sec_webhook_url"
RED_MIN_SAMPLES=3      # 红警最少样本数（24h 每小时一轮应 ≥20）
YELLOW_DAYS=45
export RED_MIN_SAMPLES YELLOW_DAYS   # awk ENVIRON 只见导出变量
mkdir -p "$STATE"
TODAY=$(date '+%F')
NOW=$(date '+%F %T')

send_push() {  # $1=title $2=desp
    if [ ! -f "$WEBHOOK_FILE" ]; then
        printf '%s [PUSH-SKIPPED] webhook file missing\n' "$NOW" >> "$LOG"
        return
    fi
    curl -s --max-time 10 "$(cat "$WEBHOOK_FILE")" -d "title=$1" --data-urlencode "desp=$2" >/dev/null 2>&1
}

should_alert() {  # $1=key —— 当天未告警过则放行并记名
    f="$STATE/${1}.date"
    if [ -f "$f" ] && [ "$(cat "$f")" = "$TODAY" ]; then
        return 1
    fi
    echo "$TODAY" > "$f"
    return 0
}

# ===== 红警：24h 全零解析的校（列表页结构变/被挡 => 静默失明） =====
docker logs --since 24h gradpath-prod-celery-worker-1 2>&1 \
| grep '\[official_announce\] school=' \
| awk '{
    # 只用 ASCII 锚点（school=/parsed=）定位，锚点间距在按字(gawk)与按字节(mawk)
    # 的 awk 下自洽，规避多字节偏移不可移植问题
    c = index($0, "school="); p = index($0, "parsed=");
    if (!c || !p || p <= c) next;
    name = substr($0, c+7, p-1-(c+7));
    sub(/^[ \t]+/, "", name);
    n = substr($0, p+7) + 0;
    total[name]++; if (n == 0) zero[name]++;
} END {
    for (s in total) if (zero[s] == total[s] && total[s] >= int(ENVIRON["RED_MIN_SAMPLES"])) print s;
}' > "$STATE/red_today.txt"

RED_ALL=""
if [ -s "$STATE/red_today.txt" ]; then
    while IFS= read -r school; do
        [ -z "$school" ] && continue
        key="red_$(echo "$school" | tr ' /' '__')"
        if should_alert "$key"; then
            RED_ALL="$RED_ALL- $school（24h 全部解析 0 条）\n"
        fi
    done < "$STATE/red_today.txt"
fi

# ===== 黄警：域名 45 天零新增 或 预期域名完全缺席 =====
HOSTS=$(docker exec gradpath-prod-backend-1 python -c "
from app.crawlers.research.official_announce_crawler import DEFAULT_SECTIONS
from urllib.parse import urlparse
print(' '.join(sorted({(urlparse(s['list_url']).hostname or '') for s in DEFAULT_SECTIONS if s.get('list_url')})))
" 2>/dev/null)

YELLOW_ALL=""
if [ -n "$HOSTS" ]; then
    docker exec gradpath-prod-db-1 psql -U gradpath -d gradpath -t -A -F'|' -c "
        select split_part(source_url,'/',3) as host,
               coalesce(max(created_time)::date::text,'-') as last_day,
               coalesce((current_date - max(created_time)::date)::text,'9999') as age
        from t_external_research_item
        where crawler_name='official_announce' and source_url is not null and source_url <> ''
        group by 1" > "$STATE/host_age.txt" 2>/dev/null

    for h in $HOSTS; do
        [ -z "$h" ] && continue
        age=$(awk -F'|' -v h="$h" '$1==h{print $3}' "$STATE/host_age.txt")
        if [ -z "$age" ]; then
            msg="$h 从未入库"
        elif [ "$age" -ge "$YELLOW_DAYS" ] 2>/dev/null; then
            msg="$h ${age} 天零新增"
        else
            continue
        fi
        if should_alert "yellow_$h"; then
            YELLOW_ALL="$YELLOW_ALL- $msg\n"
        fi
    done
fi

# ===== 汇总推送 =====
if [ -n "$RED_ALL" ] || [ -n "$YELLOW_ALL" ]; then
    TITLE="数据新鲜度告警"
    [ -n "$RED_ALL" ] && TITLE="$TITLE·红$(echo "$RED_ALL" | grep -c .)"
    [ -n "$YELLOW_ALL" ] && TITLE="$TITLE·黄$(echo "$YELLOW_ALL" | grep -c .)"
    send_push "$TITLE" "$(printf "*红·静默失明*\n${RED_ALL}\n*黄·内容老化*\n${YELLOW_ALL}")"
    printf '%s [ALERT] red=%s yellow=%s\n' "$NOW" "$(echo "$RED_ALL" | grep -c .)" "$(echo "$YELLOW_ALL" | grep -c .)" >> "$LOG"
else
    printf '%s [OK] 无断供/老化告警\n' "$NOW" >> "$LOG"
fi
exit 0
