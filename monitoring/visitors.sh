#!/usr/bin/env bash
# 访客日报 — 从 nginx 访问日志统计真实访客（北京时间日窗），可选 Server酱微信推送
# 用法:
#   visitors.sh                     打印「昨天 + 今日至今」报告
#   visitors.sh --push              推微信（默认早报：昨日为主）
#   visitors.sh --push --evening    晚报（cron 每天 22:00）：今日至今为主+昨日参考
# 口径: 日志时间为 UTC（+8 换算回北京日窗）；过滤机器人/自检 UA 与静态资源后，
#       2xx/3xx 算有效浏览，444 算被挡攻击探测；人数=不重复 IP（NAT 出口会低估，仅供参考）。
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
EVENING=0; for a in "$@"; do [ "$a" = "--evening" ] && EVENING=1; done
LOGDIR="$BASE/nginx-logs"
STATE="$BASE/state"; mkdir -p "$STATE"
CSV="$STATE/visitors.csv"
WEBHOOK_FILE="/home/ubuntu/.sec_webhook_url"
ALERTS="$BASE/alerts.log"

# 机器人/自检特征（UA 小写匹配）；空 UA 一律按机器人
BOT_RE='bot|spider|crawl|curl|wget|python|go-http|okhttp|java|headless|uptime|health|monitor|preview|feishu|dingtalk|wxwork|semrush|ahrefs|mojeek'
# 静态资源后缀（先剥 query 再匹配行尾；双反斜杠让 awk 字符串层保留 \. 给正则）
ST_RE='\\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|otf|map|xml|webp|json|txt)$'
# 轮询心跳类接口：浏览器挂着就反复刷，不计入有效浏览（2026-09-06 实测 unread-count 占 14%）
POLL_RE='^/api/notifications/unread-count'

# 时区自校准：mktime 按本机时区解释 wall clock，它对 1970-01-01 00:00 的返回值=-(本机UTC偏移)。
# 真纪元 = mktime(wall) - M，与 shell date 是否响应 TZ 无关（Git Bash date 无视 TZ 前缀的坑）。
M=$(awk 'BEGIN{print mktime("1970 1 1 0 0 0")}')
OFF=$((-M))

cat_logs() {
  cat "$LOGDIR/access.log" "$LOGDIR/access.log.1" 2>/dev/null
  [ -f "$LOGDIR/access.log.2.gz" ] && zcat "$LOGDIR/access.log.2.gz" 2>/dev/null
  return 0
}

# window_stats S E → 首行 "pv uv blocked total"，其后每行 "path count"（热门页面 Top3）
window_stats() {
  cat_logs | awk -v s="$1" -v e="$2" -v off="$OFF" -v bot="$BOT_RE" -v st="$ST_RE" -v poll="$POLL_RE" '
  BEGIN{ split("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec",MN," "); for(i=1;i<=12;i++) m[MN[i]]=i }
  {
    if ($4 !~ /^\[/) next
    t=$4; gsub(/^\[/,"",t); gsub(/[:\/]/," ",t); split(t,a," ")
    tr=mktime(a[3]" "m[a[2]]" "a[1]" "a[4]" "a[5]" "a[6])+off
    if (tr < s || tr >= e) next
    total++
    status=$9+0
    if (status==444) { blocked++; next }
    p=$7; sub(/\?.*/,"",p)
    if (p ~ st) next
    if (p ~ poll) next
    ua=""; for(i=12;i<=NF;i++){ if($i ~ /^rt=/) break; ua=ua" "$i }
    ua=tolower(ua); gsub(/"/,"",ua)
    if (ua=="" || ua ~ /^[- ]*$/ || ua ~ bot) next
    if (status<200 || status>=400) next
    pv++; seen[$1]=1; pc[p]++
  }
  END{
    uv=0; for(ip in seen) uv++
    printf "%d %d %d %d\n", pv, uv, blocked, total
    for(k=1;k<=3;k++){ best=""; bc=0; for(x in pc){ if(pc[x]>bc){bc=pc[x];best=x} }
      if(best=="") break; printf "%s %d\n", best, bc; delete pc[best] }
  }'
}

window_report() {  # S E 标签 → 多行人类可读
  OUT=$(window_stats "$1" "$2")
  SUM=$(printf '%s\n' "$OUT" | head -1)
  read -r PV UV BLK TOT <<EOF
$SUM
EOF
  TOP=$(printf '%s\n' "$OUT" | tail -n +2 | awk '{printf "%s ×%s；",$1,$2}' | sed 's/；$//')
  # 空格分隔：read 时 TOP 作为末字段吞掉其余空格（TOP 内含空格）
  printf '%s %s %s %s %s\n' "$PV" "$UV" "$BLK" "$TOT" "$TOP"
}

# 北京「今天 00:00」真纪元；VIS_Y0/VIS_Y1 仅测试注入用（Git Bash date 无视 TZ，本地测试时手动给值）
Y1=${VIS_Y1:-$(TZ=Asia/Shanghai date -d "today 00:00" +%s)}; Y0=${VIS_Y0:-$((Y1-86400))}
YD=$(TZ=Asia/Shanghai date -d yesterday +%F)
YD_CN=$(TZ=Asia/Shanghai date -d yesterday +%-m月%-d日)
TD_CN=$(TZ=Asia/Shanghai date +%-m月%-d日)
read -r PV UV BLK TOT TOP <<< "$(window_report $Y0 $Y1)"
read -r PV0 UV0 BLK0 TOT0 _  <<< "$(window_report $((Y0-86400)) $Y0)"
read -r TPV TUV TBLK TTOT TTOP <<< "$(window_report $Y1 $(date +%s))"

if [ "${UV0:-0}" -gt 0 ] 2>/dev/null; then
  D=$((UV-UV0)); [ "$D" -ge 0 ] && DELTA="比前天多 ${D} 人" || DELTA="比前天少 $((-D)) 人"
else
  DELTA="前天无数据"
fi

if [ "${EVENING:-0}" = "1" ]; then
  # 晚报 22:00：今天基本过完，报「今日至今」为主，昨日全天作对比
  if [ "${UV0:-0}" -gt 0 ] 2>/dev/null; then
    DT=$((TUV-UV0)); [ "$DT" -ge 0 ] && TDELTA="比昨天全天多 ${DT} 人" || TDELTA="比昨天全天少 $((-DT)) 人"
  else
    TDELTA="昨天无数据"
  fi
  REPORT="📊 今日访客（${TD_CN} 0点起，北京时间）
· 到访约 ${TUV:-0} 人（${TDELTA}）
· 有效浏览 ${TPV:-0} 个页面
· 自动挡掉攻击探测 ${TBLK:-0} 次
· 热门页面：${TTOP:-无}

昨天全天参考：约 ${UV} 人 / ${PV} 页
——
人数按不重复 IP 估算（同一 WiFi 出口会算作 1 人），仅供参考"
else
  REPORT="📊 昨日访客（${YD_CN}，北京时间）
· 到访约 ${UV} 人（${DELTA}）
· 有效浏览 ${PV} 个页面
· 自动挡掉攻击探测 ${BLK} 次
· 热门页面：${TOP:-无}

今日至今：约 ${TUV:-0} 人 / ${TPV:-0} 页
——
人数按不重复 IP 估算（同一 WiFi 出口会算作 1 人），仅供参考"
fi

echo "$REPORT"

if [ "${1:-}" = "--push" ]; then
  # 记历史（一行一天，供以后做趋势）
  grep -q "^${YD}," "$CSV" 2>/dev/null || echo "${YD},${PV},${UV},${BLK}" >> "$CSV"
  # 共享每日推送配额（与 sec_watcher 同一计数器；日报非提示级，上限 5）
  CNT_FILE="$STATE/push-$(date +%Y%m%d).count"
  CNT=$(cat "$CNT_FILE" 2>/dev/null || echo 0)
  if [ "$CNT" -ge 5 ]; then
    printf '%s [DAILY-CAPPED] quota reached, log-only\n' "$(date '+%F %T')" >> "$ALERTS"
    exit 0
  fi
  if [ ! -f "$WEBHOOK_FILE" ]; then
    printf '%s [DAILY-SKIPPED] webhook missing\n' "$(date '+%F %T')" >> "$ALERTS"
    exit 0
  fi
  if [ "${EVENING:-0}" = "1" ]; then
    TITLE="【日报】今天 ${TUV:-0} 位访客 · 挡掉 ${TBLK:-0} 次攻击"
  else
    TITLE="【日报】昨天 ${UV} 位访客 · 挡掉 ${BLK} 次攻击"
  fi
  RESP=$(curl -s -m 10 \
    --data-urlencode "title=$TITLE" \
    --data-urlencode "content=$REPORT" \
    "$(cat "$WEBHOOK_FILE")" 2>&1)
  echo $((CNT + 1)) > "$CNT_FILE"
  printf '%s [DAILY] -> %s\n' "$(date '+%F %T')" "$(printf '%s' "$RESP" | tr -d '\n' | cut -c1-160)" >> "$ALERTS"
fi
# 注意：本文件会被 traffic_pipeline.sh source 复用，末尾绝不能有 exit（会把调用方 shell 一起退出）
