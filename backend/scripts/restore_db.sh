#!/usr/bin/env bash
# backend/scripts/restore_db.sh
# PostgreSQL 恢复脚本 — 从指定 dump 文件恢复数据库。
# 默认使用 pg_restore --clean --if-exists --no-owner，避免因已存在的对象失败。
# 用法:
#   ./restore_db.sh /var/backups/gradpath/gradpath_20260720_120000.dump
#   FORCE_DROP=1 ./restore_db.sh <file>  # 恢复前 DROP DATABASE 完全重建
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "用法: $0 <backup_file.dump>"
  echo "可选环境变量:"
  echo "  DATABASE_URL        目标数据库（默认读取环境变量）"
  echo "  FORCE_DROP=1        恢复前 DROP 并重建数据库（破坏性操作，需手动确认）"
  echo "  PGHOST/PGUSER/PGPASSWORD/PGDATABASE   单独指定连接参数"
  exit 1
fi

BACKUP_FILE="$1"
LOG_FILE="${LOG_FILE:-/tmp/restore_db.log}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

if [[ ! -f "${BACKUP_FILE}" ]]; then
  log "ERROR: 备份文件不存在: ${BACKUP_FILE}"
  exit 1
fi

# 先校验备份文件完整性
if ! pg_restore -l "${BACKUP_FILE}" >/dev/null 2>&1; then
  log "ERROR: 备份文件损坏或不是有效的 pg_dump -Fc 文件"
  exit 1
fi
log "备份文件校验通过"

# 解析连接参数
if [[ -n "${DATABASE_URL:-}" ]]; then
  DB_SOURCE="${DATABASE_URL}"
elif [[ -n "${PGHOST:-}" && -n "${PGUSER:-}" && -n "${PGDATABASE:-}" ]]; then
  DB_SOURCE="-h ${PGHOST} -p ${PGPORT:-5432} -U ${PGUSER} -d ${PGDATABASE}"
else
  log "ERROR: 必须设置 DATABASE_URL 或 PGHOST/PGUSER/PGDATABASE"
  exit 1
fi

if [[ "${FORCE_DROP:-0}" == "1" ]]; then
  log "WARNING: FORCE_DROP=1 — 将完全 DROP 并重建数据库！"
  read -p "确认继续？输入 YES 执行: " confirm
  if [[ "${confirm}" != "YES" ]]; then
    log "已取消"
    exit 0
  fi
  # 解析数据库名并重建（需要 SUPERUSER）
  if [[ -n "${DATABASE_URL:-}" ]]; then
    DBNAME="$(echo "${DATABASE_URL}" | sed -E 's#.*/([^/?]+)(\?.*)?$#\1#')"
    log "DROP DATABASE ${DBNAME} 并重新 CREATE"
    psql "${DATABASE_URL%"${DBNAME}"}postgres" -c "DROP DATABASE IF EXISTS \"${DBNAME}\";"
    psql "${DATABASE_URL%"${DBNAME}"}postgres" -c "CREATE DATABASE \"${DBNAME}\";"
  else
    log "ERROR: FORCE_DROP 模式需要 DATABASE_URL 环境变量"
    exit 1
  fi
fi

log "开始恢复: ${BACKUP_FILE} -> ${DB_SOURCE}"
if ! pg_restore --clean --if-exists --no-owner --exit-on-error ${DB_SOURCE} "${BACKUP_FILE}"; then
  log "ERROR: pg_restore 失败"
  exit 1
fi

log "=== 恢复完成 ==="
