#!/usr/bin/env bash
# backend/scripts/backup_redis.sh
# Redis RDB 快照备份脚本 — 使用 BGSAVE 触发后台持久化，然后复制 dump.rdb。
# 备份文件命名: redis_YYYYMMDD_HHMMSS.rdb
# 保留策略: 默认 7 天（Redis 数据可重建，保留期可短于 DB）。
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/gradpath}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"
LOG_FILE="${BACKUP_DIR}/backup.log"

mkdir -p "${BACKUP_DIR}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

if [[ -z "${REDIS_URL:-}" ]]; then
  log "ERROR: 必须设置 REDIS_URL 环境变量"
  exit 1
fi

log "=== Redis 备份开始 ==="

# 触发 BGSAVE — 异步操作，需要轮询等待完成
redis-cli -u "${REDIS_URL}" BGSAVE >/dev/null 2>&1 || {
  log "ERROR: BGSAVE 失败 — 检查 Redis 连接 / 权限"
  exit 1
}

# 轮询 LASTSAVE 时间戳变化（最长等待 60s）
LASTSAVE_BEFORE="$(redis-cli -u "${REDIS_URL}" LASTSAVE 2>/dev/null | tr -d '[:space:]')"
for i in $(seq 1 60); do
  sleep 1
  LASTSAVE_AFTER="$(redis-cli -u "${REDIS_URL}" LASTSAVE 2>/dev/null | tr -d '[:space:]')"
  if [[ "${LASTSAVE_AFTER}" != "${LASTSAVE_BEFORE}" ]]; then
    log "BGSAVE 完成 (${i}s)"
    break
  fi
  if [[ ${i} -eq 60 ]]; then
    log "ERROR: BGSAVE 超时 60s"
    exit 1
  fi
done

# 定位 Redis 数据目录
REDIS_DIR="$(redis-cli -u "${REDIS_URL}" CONFIG GET dir 2>/dev/null | tail -1)"
REDIS_DBFILENAME="$(redis-cli -u "${REDIS_URL}" CONFIG GET dbfilename 2>/dev/null | tail -1)"
RDB_SOURCE="${REDIS_DIR}/${REDIS_DBFILENAME}"

if [[ ! -f "${RDB_SOURCE}" ]]; then
  log "ERROR: Redis RDB 文件不存在: ${RDB_SOURCE}"
  exit 1
fi

cp "${RDB_SOURCE}" "${BACKUP_FILE}"
FILE_SIZE="$(du -h "${BACKUP_FILE}" | cut -f1)"
log "备份完成: ${BACKUP_FILE} (${FILE_SIZE})"

# 清理过期备份
DELETED_COUNT=0
while IFS= read -r old_file; do
  if [[ -f "${old_file}" ]]; then
    rm -f "${old_file}"
    log "清理过期 Redis 备份: $(basename "${old_file}")"
    DELETED_COUNT=$((DELETED_COUNT + 1))
  fi
done < <(find "${BACKUP_DIR}" -name "redis_*.rdb" -type f -mtime +${RETENTION_DAYS})

log "清理完成：删除 ${DELETED_COUNT} 个过期 Redis 备份"
log "=== Redis 备份完成 ==="

cat <<EOF | tee -a "${LOG_FILE}"
{"event":"redis_backup","status":"success","file":"${BACKUP_FILE}","size":"${FILE_SIZE}","retention_days":${RETENTION_DAYS},"deleted_old":${DELETED_COUNT},"timestamp":"$(date -Iseconds)"}
EOF
