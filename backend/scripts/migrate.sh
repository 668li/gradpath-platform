#!/usr/bin/env bash
#
# GradPath 数据库迁移脚本 (Linux / macOS / Git Bash)
#
# 封装常用 Alembic 操作：升级、回滚、查看状态、生成新迁移。
# 在 backend/ 目录下运行；DATABASE_URL 由 .env 或环境变量提供。
#
# 用法:
#   ./scripts/migrate.sh upgrade            # 应用最新迁移 (alembic upgrade head)
#   ./scripts/migrate.sh downgrade          # 回滚一步 (alembic downgrade -1)
#   ./scripts/migrate.sh status             # 查看当前版本 (alembic current)
#   ./scripts/migrate.sh make "msg"         # 生成新迁移 (alembic revision --autogenerate -m "msg")
#   ./scripts/migrate.sh history            # 查看迁移历史
#   ./scripts/migrate.sh heads              # 查看 head 列表
#

set -euo pipefail

# 切换到 backend/ 目录（脚本的父目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

# 选择 Python 解释器：优先 venv，其次 PY 环境变量，最后 python3 / python
resolve_python() {
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        local venv_python="$VIRTUAL_ENV/bin/python"
        if [[ -x "$venv_python" ]]; then
            echo "$venv_python"
            return
        fi
    fi
    if [[ -n "${PY:-}" ]] && command -v "$PY" >/dev/null 2>&1; then
        echo "$PY"
        return
    fi
    if command -v python3 >/dev/null 2>&1; then
        echo "python3"
        return
    fi
    echo "python"
}

PYTHON="$(resolve_python)"

# 校验 Alembic 可用
if ! "$PYTHON" -m alembic --help >/dev/null 2>&1; then
    echo "ERROR: Alembic 不可用，请先安装：pip install alembic" >&2
    exit 1
fi

ACTION="${1:-status}"
MESSAGE="${2:-}"

case "$ACTION" in
    upgrade)
        echo "==> 应用最新迁移 (alembic upgrade head)"
        "$PYTHON" -m alembic upgrade head
        ;;
    downgrade)
        echo "==> 回滚一步迁移 (alembic downgrade -1)"
        "$PYTHON" -m alembic downgrade -1
        ;;
    status)
        echo "==> 当前迁移版本 (alembic current)"
        "$PYTHON" -m alembic current
        ;;
    make)
        if [[ -z "$MESSAGE" ]]; then
            echo "ERROR: 生成新迁移需要提供消息：./scripts/migrate.sh make \"your message\"" >&2
            exit 1
        fi
        echo "==> 生成新迁移: $MESSAGE"
        "$PYTHON" -m alembic revision --autogenerate -m "$MESSAGE"
        echo ""
        echo "提示：请检查 migrations/versions/ 下新生成的文件，确认 upgrade()/downgrade() 内容正确后再提交。"
        ;;
    history)
        echo "==> 迁移历史 (alembic history --verbose)"
        "$PYTHON" -m alembic history --verbose
        ;;
    heads)
        echo "==> 当前 head 列表 (alembic heads)"
        "$PYTHON" -m alembic heads
        ;;
    *)
        echo "Usage: $0 {upgrade|downgrade|status|make <message>|history|heads}" >&2
        exit 1
        ;;
esac
