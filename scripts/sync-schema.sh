#!/usr/bin/env bash
#
# GradPath Schema 同步工具包装脚本 (Linux / macOS / Git Bash)
#
# 从项目根目录直接调用 backend 容器内的 scripts/sync_schema.py，
# 无需手动 docker exec。容器名可通过环境变量 GRADPATH_BACKEND_CONTAINER 覆盖。
#
# 用法:
#   ./scripts/sync-schema.sh --check       # 检测不一致（默认）
#   ./scripts/sync-schema.sh --generate    # 生成 ALTER TABLE SQL
#   ./scripts/sync-schema.sh --apply       # 执行 ALTER TABLE ADD COLUMN
#   ./scripts/sync-schema.sh --dry-run     # 显示会执行什么，但不实际执行
#   ./scripts/sync-schema.sh               # 默认等同 --check
#

set -euo pipefail

CONTAINER="${GRADPATH_BACKEND_CONTAINER:-gradpath-backend-1}"
SCRIPT_PATH="/app/scripts/sync_schema.py"

# 无参数时默认 --check
if [[ $# -eq 0 ]]; then
    ARGS=("--check")
else
    ARGS=("$@")
fi

echo "[$CONTAINER] python $SCRIPT_PATH ${ARGS[*]}" >&2
docker exec "$CONTAINER" python "$SCRIPT_PATH" "${ARGS[@]}"
