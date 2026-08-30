#!/bin/sh
# RSSHub 按需启停 — RSSHub 每天只被 rsshub_research 采集任务（APScheduler 每日 02:30 触发）使用一次，
# 却常驻 ~700M 内存（2核4G 机器的 1/5）。用 cron 每小时整点过 10 分跑 auto：
# 02:00-03:59 采集窗口内确保启动（02:30 触发前有 20 分钟余量），窗口外确保停止。
# 部署脚本 up -d 会把 rsshub 重新拉起，auto 模式会在下一个整点后 10 分钟内把它停掉。
# 用法: rsshub_onoff.sh start|stop|auto
set -u
cd "$(dirname "$0")/.." || exit 1

COMPOSE="docker compose -f docker-compose.prod.yml -f docker-compose.grey.yml"
CONTAINER=gradpath-prod-rsshub-1
LOG_TAG="[rsshub_onoff $(date '+%F %T')]"

is_running() {
  [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" = "true" ]
}

start_rsshub() {
  if is_running; then
    echo "$LOG_TAG already running"
    return 0
  fi
  echo "$LOG_TAG starting rsshub"
  $COMPOSE start rsshub >/dev/null 2>&1 || $COMPOSE up -d rsshub >/dev/null 2>&1
  # 等待 healthy（最多 150s，healthcheck start_period 40s）
  i=0
  h="unknown"
  while [ "$i" -lt 150 ]; do
    h=$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null)
    if [ "$h" = "healthy" ]; then
      echo "$LOG_TAG rsshub healthy after ${i}s"
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  echo "$LOG_TAG WARN rsshub not healthy after 150s (status=$h)"
}

stop_rsshub() {
  if ! is_running; then
    echo "$LOG_TAG already stopped"
    return 0
  fi
  echo "$LOG_TAG stopping rsshub (释放内存)"
  $COMPOSE stop rsshub >/dev/null 2>&1
}

case "${1:-auto}" in
  start)
    start_rsshub
    ;;
  stop)
    stop_rsshub
    ;;
  auto)
    hour=$(date +%H)
    if [ "$hour" = "02" ] || [ "$hour" = "03" ]; then
      start_rsshub
    else
      stop_rsshub
    fi
    ;;
  *)
    echo "usage: $0 start|stop|auto"
    exit 2
    ;;
esac
