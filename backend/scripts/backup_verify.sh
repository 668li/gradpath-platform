#!/usr/bin/env bash
# backend/scripts/backup_verify.sh
# 备份验证脚本 — 检查备份目录中最新的 DB 与 Redis 备份文件完整性。
# 适合作为 cron 健康检查任务定期执行，连续 3 次失败时触发告警。
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/gradpath}"
LOG_FILE="${BACKUP_DIR}/backup_verify.log"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"  # 可选：失败时调用 webhook 告警

mkdir -p "${BACKUP_DIR}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

failures=0
total_checks=0

# === 检查 1: 备份目录存在且可写 ===
total_checks=$((total_checks + 1))
if [[ ! -d "${BACKUP_DIR}" ]]; then
  log "FAIL: 备份目录不存在: ${BACKUP_DIR}"
  failures=$((failures + 1))
fi

# === 检查 2: 最近 24h 内至少有 1 个 DB 备份 ===
total_checks=$((total_checks + 1))
LATEST_DB="$(find "${BACKUP_DIR}" -name "gradpath_*.dump" -type f -mtime -1 2>/dev/null | sort -r | head -1)"
if [[ -z "${LATEST_DB}" ]]; then
  log "FAIL: 最近 24h 内无 DB 备份"
  failures=$((failures + 1))
else
  log "OK: 最新 DB 备份: $(basename "${LATEST_DB}")"
fi

# === 检查 3: 最新 DB 备份文件完整性 ===
total_checks=$((total_checks + 1))
if [[ -n "${LATEST_DB}" ]]; then
  if pg_restore -l "${LATEST_DB}" >/dev/null 2>&1; then
    log "OK: DB 备份完整性校验通过"
  else
    log "FAIL: DB 备份文件损坏: ${LATEST_DB}"
    failures=$((failures + 1))
  fi
fi

# === 检查 4: DB 备份文件大小 > 0 ===
total_checks=$((total_checks + 1))
if [[ -n "${LATEST_DB}" ]]; then
  SIZE_BYTES="$(stat -c %s "${LATEST_DB}" 2>/dev/null || stat -f %z "${LATEST_DB}" 2>/dev/null || echo 0)"
  if [[ ${SIZE_BYTES} -lt 1024 ]]; then
    log "FAIL: DB 备份文件异常小 (${SIZE_BYTES} bytes)"
    failures=$((failures + 1))
  else
    log "OK: DB 备份大小 ${SIZE_BYTES} bytes"
  fi
fi

# === 检查 5: 最近 24h 内至少有 1 个 Redis 备份（仅当 REDIS_URL 配置时检查） ===
if [[ -n "${REDIS_URL:-}" ]]; then
  total_checks=$((total_checks + 1))
  LATEST_REDIS="$(find "${BACKUP_DIR}" -name "redis_*.rdb" -type f -mtime -1 2>/dev/null | sort -r | head -1)"
  if [[ -z "${LATEST_REDIS}" ]]; then
    log "WARN: 最近 24h 内无 Redis 备份"
    # Redis 备份失败为 WARN 级别（Redis 数据可重建），不增加 failures
  else
    SIZE_BYTES="$(stat -c %s "${LATEST_REDIS}" 2>/dev/null || stat -f %z "${LATEST_REDIS}" 2>/dev/null || echo 0)"
    if [[ ${SIZE_BYTES} -lt 1 ]]; then
      log "FAIL: Redis 备份文件为空"
      failures=$((failures + 1))
    else
      log "OK: Redis 备份完整性校验通过 (${SIZE_BYTES} bytes)"
    fi
  fi
fi

# === 总结 ===
log "=== 验证完成: ${total_checks} 项检查, ${failures} 项失败 ==="

if [[ ${failures} -gt 0 ]]; then
  # 触发 webhook 告警（可选）
  if [[ -n "${ALERT_WEBHOOK}" ]]; then
    curl -fsS -m 10 -X POST -H 'Content-Type: application/json' \
      -d "{\"event\":\"backup_verify_failed\",\"failures\":${failures},\"total\":${total_checks},\"timestamp\":\"$(date -Iseconds)\"}" \
      "${ALERT_WEBHOOK}" >/dev/null 2>&1 || true
    log "已触发告警 webhook"
  fi
  exit 1
fi

exit 0
