#!/usr/bin/env bash
# backend/scripts/backup_db.sh
# PostgreSQL 物理备份脚本 — 通过 pg_dump 生成自定义格式（-Fc）压缩备份。
# 备份文件命名: gradpath_YYYYMMDD_HHMMSS.dump
# 保留策略: 默认保留最近 14 天的备份（RETENTION_DAYS 可覆盖）。
# 用法:
#   ./backup_db.sh                          # 使用环境变量 DATABASE_URL
#   RETENTION_DAYS=30 ./backup_db.sh        # 自定义保留期
#   BACKUP_DIR=/var/backups ./backup_db.sh  # 自定义备份目录
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/gradpath}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/gradpath_${TIMESTAMP}.dump"
LOG_FILE="${BACKUP_DIR}/backup.log"

mkdir -p "${BACKUP_DIR}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

log "=== 数据库备份开始 ==="

# 优先使用 PG_* 环境变量；若未设置则从 DATABASE_URL 解析
if [[ -n "${DATABASE_URL:-}" ]]; then
  # DATABASE_URL 形如: postgresql://user:pass@host:5432/dbname
  # pg_dump 接受 postgresql:// URL 作为 conninfo
  DB_SOURCE="${DATABASE_URL}"
elif [[ -n "${PGHOST:-}" && -n "${PGUSER:-}" && -n "${PGDATABASE:-}" ]]; then
  DB_SOURCE="-h ${PGHOST} -p ${PGPORT:-5432} -U ${PGUSER} -d ${PGDATABASE}"
else
  log "ERROR: 必须设置 DATABASE_URL 或 PGHOST/PGUSER/PGDATABASE 环境变量"
  exit 1
fi

# 执行备份
if ! pg_dump -Fc ${DB_SOURCE} -f "${BACKUP_FILE}"; then
  log "ERROR: pg_dump 失败"
  exit 1
fi

# 计算文件大小
FILE_SIZE="$(du -h "${BACKUP_FILE}" | cut -f1)"
log "备份完成: ${BACKUP_FILE} (${FILE_SIZE})"

# 验证备份文件可被读取（完整性检查）
if ! pg_restore -l "${BACKUP_FILE}" >/dev/null 2>&1; then
  log "ERROR: 备份文件完整性校验失败"
  exit 1
fi
log "备份文件完整性校验通过"

# 清理过期备份
DELETED_COUNT=0
while IFS= read -r old_file; do
  if [[ -f "${old_file}" ]]; then
    rm -f "${old_file}"
    log "清理过期备份: $(basename "${old_file}")"
    DELETED_COUNT=$((DELETED_COUNT + 1))
  fi
done < <(find "${BACKUP_DIR}" -name "gradpath_*.dump" -type f -mtime +${RETENTION_DAYS})

log "清理完成：删除 ${DELETED_COUNT} 个过期备份（保留期 ${RETENTION_DAYS} 天）"
log "=== 数据库备份完成 ==="

# 输出 JSON 摘要供 cron 上报
cat <<EOF | tee -a "${LOG_FILE}"
{"event":"db_backup","status":"success","file":"${BACKUP_FILE}","size":"${FILE_SIZE}","retention_days":${RETENTION_DAYS},"deleted_old":${DELETED_COUNT},"timestamp":"$(date -Iseconds)"}
EOF
