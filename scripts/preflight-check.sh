#!/usr/bin/env bash
# ======================================================================
# GradPath — 预启动健康检查脚本 (bash 版,适用于 Linux / macOS / WSL)
# ======================================================================
# 用法:
#   ./scripts/preflight-check.sh          # 仅检查
#   ./scripts/preflight-check.sh --fix    # 检查并自动修复可修复的问题
#
# 检查 5 个维度:
#   1. .next 缓存完整性 (middleware-manifest.json)
#   2. 后端依赖完整性 (tenacity/redis 模块)
#   3. 数据库 Schema 与 SQLAlchemy 模型一致性
#   4. 后端 API 路由注册完整性 (>= 65 个模块)
#   5. 关键 API 端点可用性 (5 个核心端点返回 200)
# ======================================================================
set -uo pipefail

# ---- 颜色 ----
if [[ -t 1 ]]; then
    C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_RED=$'\033[31m'; C_MAGENTA=$'\033[35m'; C_RESET=$'\033[0m'
else
    C_CYAN=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_MAGENTA=""; C_RESET=""
fi

# ---- 颜色辅助 ----
header()  { echo ""; echo "${C_CYAN}$*${C_RESET}"; }
sub_pass() { echo "  ${C_GREEN}[PASS]${C_RESET} $*"; }
sub_fail() { echo "  ${C_RED}[FAIL]${C_RESET} $*"; }
sub_warn() { echo "  ${C_YELLOW}[WARN]${C_RESET} $*"; }
do_fix()  { echo "  ${C_MAGENTA}[FIX]${C_RESET}  $*"; }
hint()    { echo "         ${C_YELLOW}$*${C_RESET}"; }

# ---- 切换到项目根目录 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# ---- 配置 ----
BACKEND_CONTAINER="gradpath-backend-1"
BACKEND_URL="http://localhost:8001"
FRONTEND_NEXT_DIR="$PROJECT_ROOT/frontend/.next"
MANIFEST_FILE="$FRONTEND_NEXT_DIR/server/middleware-manifest.json"
TEST_EMAIL="${GRADPATH_TEST_EMAIL:-test-185651@example.com}"
TEST_PASSWORD="${GRADPATH_TEST_PASSWORD:-Test12345678!}"
MIN_ROUTE_COUNT=65
NORMAL_ROUTE_COUNT=70

# ---- 解析参数 ----
FIX=0
for arg in "$@"; do
    case "$arg" in
        --fix) FIX=1 ;;
        -h|--help)
            sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
    esac
done

# ---- 计数器 ----
CHECKS_PASSED=0

# ========== Check 1: .next 缓存完整性 ==========
header "[Check 1/5] .next 缓存完整性"
check1_ok=0
if [[ -f "$MANIFEST_FILE" ]]; then
    sub_pass "middleware-manifest.json 存在，.next 缓存完整"
    check1_ok=1
else
    if [[ $FIX -eq 1 ]]; then
        if [[ -d "$FRONTEND_NEXT_DIR" ]]; then
            if rm -rf "$FRONTEND_NEXT_DIR"; then
                do_fix "已清理 .next 缓存 (删除 $FRONTEND_NEXT_DIR)"
                sub_pass ".next 缓存已清理，Next.js 将在启动时重新构建"
                check1_ok=1
            else
                sub_fail "清理 .next 缓存失败"
                hint "手动执行: rm -rf frontend/.next"
            fi
        else
            do_fix ".next 目录不存在（首次启动，无需清理）"
            sub_pass ".next 缓存不存在，Next.js 将首次构建"
            check1_ok=1
        fi
    else
        sub_fail "middleware-manifest.json 缺失: $MANIFEST_FILE"
        sub_fail "  (可能导致 hydration 失败 / middleware-manifest.json ENOENT)"
        hint "修复建议: 重新运行本脚本并加 --fix 参数，或手动执行:"
        hint "  rm -rf frontend/.next"
    fi
fi
[[ $check1_ok -eq 1 ]] && ((CHECKS_PASSED++))

# ========== Check 2: 后端依赖完整性 ==========
header "[Check 2/5] 后端依赖完整性 (tenacity/redis)"
check2_ok=0
dep_ok=0
dep_source=""

# 优先检查容器内 Python
dep_output=$(docker exec "$BACKEND_CONTAINER" python -c "import tenacity, redis; print('OK')" 2>/dev/null)
if [[ $? -eq 0 && "$dep_output" == "OK" ]]; then
    dep_ok=1
    dep_source="容器内"
fi

# 回退到本地 Python
if [[ $dep_ok -eq 0 ]]; then
    dep_output=$(python -c "import tenacity, redis; print('OK')" 2>/dev/null)
    if [[ $? -eq 0 && "$dep_output" == "OK" ]]; then
        dep_ok=1
        dep_source="本地"
    fi
fi

if [[ $dep_ok -eq 1 ]]; then
    sub_pass "tenacity 和 redis 模块均可正常导入 ($dep_source Python)"
    check2_ok=1
else
    if [[ $FIX -eq 1 ]]; then
        do_fix "尝试在容器内安装缺失依赖 (tenacity redis)..."
        docker exec "$BACKEND_CONTAINER" pip install tenacity redis >/dev/null 2>&1
        if [[ $? -eq 0 ]]; then
            # 复查
            recheck=$(docker exec "$BACKEND_CONTAINER" python -c "import tenacity, redis; print('OK')" 2>/dev/null)
            if [[ "$recheck" == "OK" ]]; then
                sub_pass "缺失依赖已安装 (tenacity, redis)"
                check2_ok=1
            else
                sub_fail "依赖安装后仍无法导入"
                hint "手动执行: docker exec $BACKEND_CONTAINER pip install tenacity redis"
            fi
        else
            sub_fail "pip install 失败 (容器可能未运行)"
            hint "手动执行: docker exec $BACKEND_CONTAINER pip install tenacity redis"
        fi
    else
        sub_fail "后端缺少 tenacity 或 redis 模块 (导致多个 API 路由静默跳过)"
        hint "修复建议: 重新运行本脚本并加 --fix 参数，或手动执行:"
        hint "  docker exec $BACKEND_CONTAINER pip install tenacity redis"
    fi
fi
[[ $check2_ok -eq 1 ]] && ((CHECKS_PASSED++))

# ========== Check 3: 数据库 Schema 一致性 ==========
header "[Check 3/5] 数据库 Schema 一致性"
check3_ok=0

# 通过 docker exec + stdin 传入 Python 脚本，避免引号转义问题
schema_output=$(docker exec -i "$BACKEND_CONTAINER" python - 2>&1 <<'PYEOF'
from sqlalchemy import inspect
from app.database import engine, Base
import importlib, pkgutil, app.models
for finder, name, is_pkg in pkgutil.iter_modules(app.models.__path__):
    try:
        importlib.import_module(f'app.models.{name}')
    except Exception:
        pass
insp = inspect(engine)
all_missing = []
for table_name in sorted(set(insp.get_table_names()) & set(Base.metadata.tables.keys())):
    db_cols = {c['name'] for c in insp.get_columns(table_name)}
    model_cols = set(Base.metadata.tables[table_name].columns.keys())
    missing = model_cols - db_cols
    if missing:
        print(f"FAIL: {table_name} 缺失列: {sorted(missing)}")
        all_missing.append((table_name, sorted(missing)))
if not all_missing:
    print("OK: schema 一致")
PYEOF
)
schema_rc=$?

if [[ $schema_rc -eq 0 && "$schema_output" == *"OK: schema"* ]]; then
    sub_pass "数据库 Schema 与 SQLAlchemy 模型一致"
    check3_ok=1
elif [[ "$schema_output" == *"FAIL:"* ]]; then
    sub_fail "数据库 Schema 与模型不一致 (缺失列):"
    echo "$schema_output" | grep "FAIL:" | while IFS= read -r line; do
        echo "         ${C_RED}${line}${C_RESET}"
    done
    hint "修复建议: 运行 schema 同步脚本:"
    hint "  ./scripts/sync-schema.sh"
    hint "  或手动添加缺失列 (参考 backend/migrations/)"
else
    sub_fail "Schema 检查执行失败 (容器可能未运行或数据库未连接)"
    err_first=$(echo "$schema_output" | head -3 | tr '\n' ' ')
    if [[ -n "$err_first" ]]; then
        hint "错误输出: $err_first"
    fi
    hint "修复建议: 确认后端容器已启动且数据库已连接"
fi
[[ $check3_ok -eq 1 ]] && ((CHECKS_PASSED++))

# ========== Check 4: API 路由注册完整性 ==========
header "[Check 4/5] API 路由注册完整性"
check4_ok=0
route_count=0
log_source=""

# 优先搜索最近 5 分钟日志
logs=$(docker logs "$BACKEND_CONTAINER" --since 5m 2>&1)
# 取最后一次匹配 "已自动注册 N 个 API 路由模块"
route_count=$(echo "$logs" | grep "已自动注册" | tail -1 | sed -n 's/.*已自动注册 \([0-9][0-9]*\) 个 API 路由模块.*/\1/p')

if [[ -z "$route_count" ]]; then
    # 回退: 搜索全部日志 (后端可能启动超过 5 分钟)
    logs=$(docker logs "$BACKEND_CONTAINER" 2>&1)
    route_count=$(echo "$logs" | grep "已自动注册" | tail -1 | sed -n 's/.*已自动注册 \([0-9][0-9]*\) 个 API 路由模块.*/\1/p')
    if [[ -n "$route_count" ]]; then
        log_source="(来自全部日志)"
    fi
else
    log_source="(来自最近 5 分钟日志)"
fi

if [[ -n "$route_count" && "$route_count" =~ ^[0-9]+$ ]]; then
    if [[ "$route_count" -ge "$MIN_ROUTE_COUNT" ]]; then
        sub_pass "已自动注册 $route_count 个 API 路由模块 $log_source (>= $MIN_ROUTE_COUNT 阈值，正常为 $NORMAL_ROUTE_COUNT)"
        check4_ok=1
    else
        sub_fail "API 路由注册数 $route_count < $MIN_ROUTE_COUNT (正常为 $NORMAL_ROUTE_COUNT) $log_source"
        hint "可能有 API 模块导入失败导致静默跳过"
        hint "修复建议: 查看后端日志定位失败模块:"
        hint "  docker logs $BACKEND_CONTAINER --tail 100"
    fi
else
    sub_fail "未在后端日志中找到 '已自动注册 N 个 API 路由模块' 记录"
    hint "可能原因: 后端容器未启动 / 启动失败 / 日志已被清除"
    hint "修复建议:"
    hint "  1. 确认后端运行: docker ps"
    hint "  2. 查看完整日志: docker logs $BACKEND_CONTAINER --tail 100"
fi
[[ $check4_ok -eq 1 ]] && ((CHECKS_PASSED++))

# ========== Check 5: 关键 API 端点可用性 ==========
header "[Check 5/5] 关键 API 端点可用性"
check5_ok=0

endpoints=(
    "/api/notifications"
    "/api/notifications/unread-count"
    "/api/auth/me"
    "/api/decisions"
    "/api/streaks/stats"
)

# 登录获取 token
token=""
login_ok=0
login_body=$(printf '{"email":"%s","password":"%s"}' "$TEST_EMAIL" "$TEST_PASSWORD")
login_resp=$(curl -s -o /tmp/.gradpath_login_resp -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$login_body" \
    --connect-timeout 10 --max-time 15 \
    "$BACKEND_URL/api/auth/login" 2>/dev/null)

if [[ "$login_resp" == "200" ]]; then
    token=$(python3 -c "import json,sys; print(json.load(open('/tmp/.gradpath_login_resp')).get('access_token',''))" 2>/dev/null)
    if [[ -n "$token" ]]; then
        login_ok=1
    fi
fi
rm -f /tmp/.gradpath_login_resp

if [[ $login_ok -eq 0 ]]; then
    sub_fail "登录失败，无法获取 token (测试账号: $TEST_EMAIL)"
    hint "跳过端点检查。修复建议:"
    hint "  1. 确认后端已启动: docker ps"
    hint "  2. 确认测试账号存在 (可通过环境变量 GRADPATH_TEST_EMAIL / GRADPATH_TEST_PASSWORD 覆盖)"
    hint "  3. 查看后端日志: docker logs $BACKEND_CONTAINER --tail 50"
else
    # 检查每个端点
    endpoint_fail_count=0
    for ep in "${endpoints[@]}"; do
        status=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $token" \
            --connect-timeout 10 --max-time 15 \
            "$BACKEND_URL$ep" 2>/dev/null)
        if [[ "$status" == "200" ]]; then
            sub_pass "$ep -> 200"
        else
            sub_fail "$ep -> ${status:-连接失败}"
            ((endpoint_fail_count++))
        fi
    done
    if [[ $endpoint_fail_count -eq 0 ]]; then
        check5_ok=1
    else
        sub_fail "$endpoint_fail_count/${#endpoints[@]} 端点不可用"
        hint "修复建议: 检查失败端点的后端日志和依赖"
        hint "  docker logs $BACKEND_CONTAINER --tail 50"
    fi
fi
[[ $check5_ok -eq 1 ]] && ((CHECKS_PASSED++))

# ========== 汇总 ==========
total_checks=5
echo ""
echo "========================================" | sed "s/.*/${C_CYAN}&${C_RESET}/"
if [[ $CHECKS_PASSED -eq $total_checks ]]; then
    echo "${C_GREEN}汇总: ${CHECKS_PASSED}/${total_checks} 检查通过 - ALL GREEN${C_RESET}"
else
    echo "${C_RED}汇总: ${CHECKS_PASSED}/${total_checks} 检查通过${C_RESET}"
    echo ""
    echo "${C_YELLOW}失败项请参考上方 [FAIL] 行及修复建议${C_RESET}"
    if [[ $FIX -eq 0 ]]; then
        echo "${C_YELLOW}提示: 加 --fix 参数可自动修复部分问题 (清理 .next 缓存、安装缺失依赖)${C_RESET}"
    fi
fi
echo "========================================" | sed "s/.*/${C_CYAN}&${C_RESET}/"

if [[ $CHECKS_PASSED -lt $total_checks ]]; then
    exit 1
else
    exit 0
fi
