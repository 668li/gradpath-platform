#!/usr/bin/env bash
# GradPath 安全监控 watcher — cron 每分钟一次（2026-09-04 任务书）
# 5 项检查 → 企业微信群机器人 markdown 推送；告警同时落 alerts.log 留痕。
# 让步顺序：站点可用 > 拦截有效 > 告警丰富。本脚本只读+推送，不改任何系统状态。
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
LOG="$BASE/nginx-logs/access.log"
F2B_LOG="/var/log/fail2ban.log"
WEBHOOK_FILE="/home/ubuntu/.sec_webhook_url"
ALERTS="$BASE/alerts.log"
STATE="$BASE/state"
mkdir -p "$STATE"
NOW=$(date +%s)
date +%s > "$STATE/last-run.ts"   # 心跳：证明 cron 活着

# nginx 日志时间为 UTC；窗口取当前分钟+前一分钟，避免 cron 边界漏检
M1=$(date -u +'%d/%b/%Y:%H:%M')
M0=$(date -u -d '1 minute ago' +'%d/%b/%Y:%H:%M')
PROBE_RE='\.git|\.env|\.svn|\.ssh|\.php|\.asp|\.jsp|\.cgi|wp-|adminer|phpmyadmin|/shell'

# send LEVEL KEY COOLDOWN_SECS TITLE BODY —— cooldown=0 表示不冷却（CRITICAL）
send() {
  local level="$1" key="$2" cooldown="$3" title="$4" body="$5"
  local ts="$STATE/$(printf '%s' "$key" | md5sum | cut -c1-12).ts"
  if [ "$cooldown" -gt 0 ] && [ -f "$ts" ] && [ $((NOW - $(cat "$ts" 2>/dev/null || echo 0))) -lt "$cooldown" ]; then
    return 0
  fi
  date +%s > "$ts"
  body=$(printf '%s' "$body" | tr -d '"\\')   # 防日志内容破坏 JSON
  printf '%s [%s] %s | %s\n' "$(date '+%F %T')" "$level" "$title" "$body" >> "$ALERTS"
  if [ ! -f "$WEBHOOK_FILE" ]; then
    printf '%s [PUSH-SKIPPED] webhook file missing\n' "$(date '+%F %T')" >> "$ALERTS"
    return 0
  fi
  local url content resp
  url=$(cat "$WEBHOOK_FILE")
  content="**[$level] GradPath $title**\n> $body\n> $(date '+%F %T') $(hostname)"
  resp=$(curl -s -m 10 -H 'Content-Type: application/json' \
    -d "{\"msgtype\":\"markdown\",\"markdown\":{\"content\":\"$content\"}}" "$url" 2>&1)
  printf '%s [PUSH] %s -> %s\n' "$(date '+%F %T')" "$title" "$resp" >> "$ALERTS"
}

if [ "${1:-}" = "--test" ]; then
  send "INFO" "selftest" 0 "watcher self-test" "monitoring pipeline test message (ignore)"
  echo "test dispatched; tail $ALERTS"
  exit 0
fi

# (a) CRITICAL：探测路径拿到了真实响应(status<400) —— 444 拦截失效
if [ -f "$LOG" ]; then
  HIT=$(tail -n 500 "$LOG" 2>/dev/null | grep -E "\[($M0|$M1):" | grep -E "$PROBE_RE" \
        | awk '$9 ~ /^[0-9]+$/ && $9+0 < 400' | head -1 | cut -c1-160)
  [ -n "$HIT" ] && send CRITICAL "probe-bypass" 0 "probe passed blocking" "$HIT"

  # (e) WARNING：5xx 突增 >20/分钟
  C5=$(tail -n 1000 "$LOG" 2>/dev/null | grep -E "\[($M0|$M1):" | awk '$9 ~ /^[0-9]+$/ && $9+0 >= 500' | wc -l)
  [ "$C5" -gt 20 ] && send WARNING "5xx-burst" 600 "5xx burst ${C5}/min" "nginx 5xx count in last minute: $C5"
fi

# (b) INFO：fail2ban 新增封禁
T1=$(date +%H:%M); T0=$(date -d '1 minute ago' +%H:%M); D=$(date +%Y-%m-%d)
NEWBAN=$(sudo tail -n 200 "$F2B_LOG" 2>/dev/null | grep -E "^$D ($T0|$T1):" | grep 'NOTICE' \
         | grep -oE '\[[a-z-]+\] Ban [0-9.]+' | sort -u | tr '\n' ';')
[ -n "$NEWBAN" ] && send INFO "new-ban" 600 "fail2ban new bans" "$NEWBAN"

# (c) CRITICAL：容器 unhealthy / restarting
BAD=$(docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | grep -E 'unhealthy|Restarting' | tr '\n' ';')
[ -n "$BAD" ] && send CRITICAL "container-down" 0 "container unhealthy" "$BAD"

# (d) WARNING：根分区 >=90%（冷却 6h）
DISK=$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')
[ "${DISK:-0}" -ge 90 ] && send WARNING "disk" 21600 "disk usage ${DISK}%" "$(df -h / | tail -1)"

exit 0
