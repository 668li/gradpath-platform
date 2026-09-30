#!/usr/bin/env bash
# GradPath 安全监控 watcher — cron 每分钟一次（2026-09-04 任务书）
# 5 项检查 → 微信推送（经 send_notify.sh 适配层：WxPusher 主 + Server酱兜底）；告警同时落 alerts.log 留痕。
# 让步顺序：站点可用 > 拦截有效 > 告警丰富。本脚本只读+推送，不改任何系统状态。
# 推送面向非技术用户：全中文，正文三段式（发生了什么/这意味着什么/需要做什么）；
# alerts.log 里级别 token 保持英文便于 grep。
# 2026-09-25 降噪修订：
#   (a) probe-bypass 判定收紧为「2xx 才算真绕过」——此前 status<400 把 port 80 的
#       301 重定向误判为绕过，每天制造数条假 CRITICAL（证据行清一色 "GET /.env" 301）；
#   (b) new-ban 单 IP 日常封禁只落盘不推送（≥2 才推），夜间 22:00 日报兜底。
# 2026-09-25 晚通道切换：推送改走 send_notify.sh（WxPusher 500条/天 主通道）；
#   每日计数器仅防风暴（INFO 30、其他 100），不再是 Server酱 5 条额度闸。
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
LOG="$BASE/nginx-logs/access.log"
F2B_LOG="/var/log/fail2ban.log"
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
  printf '%s [%s] %s | %s\n' "$(date '+%F %T')" "$level" "$title" "$body" >> "$ALERTS"
  # 每日计数器仅防推送风暴（WxPusher 免费额度 500/天，正常用量 <10/天）
  local cnt_file="$STATE/push-$(date +%Y%m%d).count"
  local cnt limit cn
  cnt=$(cat "$cnt_file" 2>/dev/null || echo 0)
  limit=100; [ "$level" = "INFO" ] && limit=30
  if [ "$cnt" -ge "$limit" ]; then
    printf '%s [PUSH-CAPPED] daily quota(%s) reached, log-only\n' "$(date '+%F %T')" "$limit" >> "$ALERTS"
    return 0
  fi
  case "$level" in
    CRITICAL) cn="严重" ;;
    WARNING)  cn="警告" ;;
    INFO)     cn="提示" ;;
    *)        cn="$level" ;;
  esac
  local resp
  resp=$(bash "$BASE/send_notify.sh" "【${cn}】GradPath ${title}" "$body

$(date '+%F %T') $(hostname)")
  echo $((cnt + 1)) > "$cnt_file"
  printf '%s [PUSH] %s -> %s\n' "$(date '+%F %T')" "$title" "$(printf '%s' "$resp" | tr -d '\n' | cut -c1-200)" >> "$ALERTS"
}

if [ "${1:-}" = "--test" ]; then
  send "INFO" "selftest" 0 "告警通道自检（测试消息）" "【发生了什么】这是一条手动触发的测试推送。
【这意味着什么】你能看到它，说明「服务器出事 → 微信提醒」这条链路是通的。
【需要做什么】无需处理。"
  echo "test dispatched; tail $ALERTS"
  exit 0
fi

# (a) CRITICAL：探测路径拿到了页面内容(2xx) —— 444 拦截失效。
# 只认 2xx：301/307 重定向没有内容（跳到 HTTPS 门口就被拦），不构成绕过；
# 401/403/444 更是拒绝。旧口径 status<400 是 2026-09-25 前假警报的根因。
if [ -f "$LOG" ]; then
  HIT=$(tail -n 500 "$LOG" 2>/dev/null | grep -E "\[($M0|$M1):" | grep -E "$PROBE_RE" \
        | awk '$9 ~ /^[0-9]+$/ && ($9+0) >= 200 && ($9+0) < 300' | head -1 | cut -c1-160)
  [ -n "$HIT" ] && send CRITICAL "probe-bypass" 0 "有人绕过封锁看到了真实页面" "【发生了什么】攻击者在被封锁的情况下，用异常路径（.git/.env/phpmyadmin 之类）探测网站，竟然拿到了页面内容（2xx 响应）而不是被拒绝。
【这意味着什么】网站最外层的拦截规则可能失效，攻击者有机会看到不该看到的文件。这是最高级别告警。
【证据（原始日志）】$HIT
【需要做什么】尽快上服务器检查 nginx 配置有没有被改动（compare: git -C ~/gradpath-platform status）。"

  # (e) WARNING：5xx 突增 >20/分钟
  C5=$(tail -n 1000 "$LOG" 2>/dev/null | grep -E "\[($M0|$M1):" | awk '$9 ~ /^[0-9]+$/ && $9+0 >= 500' | wc -l)
  [ "$C5" -gt 20 ] && send WARNING "5xx-burst" 600 "网站错误突然增多（每分钟 ${C5} 次）" "【发生了什么】最近一分钟服务器返回了 ${C5} 次「5xx」服务器内部错误（正常应在 20 次以内）。
【这意味着什么】网站可能卡顿或部分功能用不了。常见原因：程序报错、数据库吃紧、或被大量恶意请求刷。
【需要做什么】打开网站试试是否正常。偶尔一次可忽略；连续收到这条再上服务器查日志（docker logs --tail 100 gradpath-prod-backend-1）。"
fi

# (b) INFO：fail2ban 新增封禁 —— 单 IP 日常封禁只落盘；一分钟内封 ≥2 个才推送
T1=$(date +%H:%M); T0=$(date -d '1 minute ago' +%H:%M); D=$(date +%Y-%m-%d)
NEWBAN=$(sudo tail -n 200 "$F2B_LOG" 2>/dev/null | grep -E "^$D ($T0|$T1):" | grep 'NOTICE' \
         | grep -oE '\[[a-z-]+\] Ban [0-9.]+' | sort -u | tr '\n' ';')
if [ -n "$NEWBAN" ]; then
  BAN_LIST=$(printf '%s' "$NEWBAN" | sed -e 's/;[[:space:]]*/；/g' -e 's/；$//' -e 's/\[\([a-z-]*\)\] Ban /【\1】/g')
  NB=$(printf '%s' "$NEWBAN" | grep -o 'Ban' | wc -l)
  if [ "$NB" -ge 2 ]; then
    send INFO "new-ban" 600 "防火墙自动封禁了新的攻击 IP（${NB} 个）" "【发生了什么】过去一分钟，防火墙把 ${NB} 个正在攻击服务器的 IP 拉黑了：${BAN_LIST}
【这意味着什么】这些 IP 正在暴力破解密码或恶意扫描。系统已自动把他们挡在门外——这是防护在正常工作的日常通知，不是故障。
【防线说明】sshd=SSH 远程登录防线；recidive=屡犯者加重长期封禁；其余名称多为网站访问防线。
【需要做什么】无需任何处理。看到这条反而说明防护有效。"
  else
    printf '%s [LOG-ONLY] 单IP日常封禁不推送 | %s\n' "$(date '+%F %T')" "$BAN_LIST" >> "$ALERTS"
  fi
fi

# (c) CRITICAL：容器 unhealthy / restarting
BAD=$(docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | grep -E 'unhealthy|Restarting' | tr '\n' ';')
[ -n "$BAD" ] && send CRITICAL "container-down" 0 "服务容器异常：正在重启或不健康" "【发生了什么】以下服务容器状态异常：${BAD}
【这意味着什么】对应功能可能正在中断（网站打不开、后台任务停摆等），docker 正在自动尝试恢复。
【需要做什么】等 2-3 分钟看能否自愈；持续收到这条就上服务器跑 docker ps 和 docker logs --tail 100 <容器名> 查原因。"

# (d) WARNING：根分区 >=90%（冷却 6h）
DISK=$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')
[ "${DISK:-0}" -ge 90 ] && send WARNING "disk" 21600 "服务器磁盘已用 ${DISK}%" "【发生了什么】服务器根分区已用 ${DISK}%（警戒线 90%）。
【这意味着什么】磁盘快满了。真满会导致数据库写不进、日志丢失、服务崩溃——本项目之前就发生过构建中途磁盘挤爆的事故。
【需要做什么】抽空上服务器清理大文件/旧镜像（docker system df 先看大头）；每次部署脚本也会自动检查这个水位。"

exit 0
