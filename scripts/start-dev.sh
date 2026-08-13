#!/usr/bin/env bash
# ======================================================================
# GradPath — 本地开发环境启动脚本 (bash 版,适用于 Linux / macOS / WSL)
# ======================================================================
# 用法:
#   ./scripts/start-dev.sh                # 启动全部服务
#   ./scripts/start-dev.sh backend        # 仅启动 backend (及其依赖 db/redis)
#   ./scripts/start-dev.sh --skip-port-check   # 跳过端口检查
#
# 行为:
#   1. 检查 8001 / 3000 / 8080 端口是否被占用
#   2. 用 docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d 启动
#   3. 等待各服务 health check 通过
#   4. 输出访问 URL
# ======================================================================
set -euo pipefail

# ---- 颜色 ----
if [[ -t 1 ]]; then
    C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_RED=$'\033[31m'; C_RESET=$'\033[0m'
else
    C_CYAN=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_RESET=""
fi

log()   { echo "${C_CYAN}[$(date +%H:%M:%S)]${C_RESET} $*"; }
ok()    { echo "${C_GREEN}[$(date +%H:%M:%S)] ✅${C_RESET} $*"; }
warn()  { echo "${C_YELLOW}[$(date +%H:%M:%S)] ⚠️ ${C_RESET} $*"; }
err()   { echo "${C_RED}[$(date +%H:%M:%S)] ❌${C_RESET} $*" >&2; }

# ---- 切换到项目根目录 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.dev.yml)

# ---- 解析参数 ----
SKIP_PORT_CHECK=0
SERVICE_ARGS=()
for arg in "$@"; do
    case "$arg" in
        --skip-port-check) SKIP_PORT_CHECK=1 ;;
        -h|--help)
            sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) SERVICE_ARGS+=("$arg") ;;
    esac
done

# ---- 依赖检查 ----
if ! command -v docker >/dev/null 2>&1; then
    err "未找到 docker 命令,请先安装 Docker"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    err "docker compose v2 不可用,请升级 Docker / 安装 compose 插件"
    exit 1
fi

# ---- 端口检查 ----
check_port() {
    local port=$1
    local name=$2
    local holder
    if command -v ss >/dev/null 2>&1; then
        holder=$(ss -tlnp 2>/dev/null | awk -v p=":$port" '$4 ~ p {print $NF}' | head -1)
    elif command -v lsof >/dev/null 2>&1; then
        holder=$(lsof -iTCP:"$port" -sTCP:LISTEN -n -P 2>/dev/null | awk 'NR>1 {print $1, $2}' | head -1)
    elif command -v netstat >/dev/null 2>&1; then
        holder=$(netstat -tlnp 2>/dev/null | awk -v p=":$port " '$4 ~ p {print $7}' | head -1)
    else
        warn "无法找到 ss/lsof/netstat,跳过端口 $port 检查"
        return 0
    fi
    if [[ -n "$holder" ]]; then
        err "端口 $port ($name) 已被占用: $holder"
        err "如确认无冲突,可用 --skip-port-check 跳过检查"
        return 1
    fi
    ok "端口 $port ($name) 空闲"
}

if [[ "$SKIP_PORT_CHECK" -eq 0 ]]; then
    log "检查端口占用..."
    check_port 8001 "GradPath backend" || exit 1
    check_port 3000 "GradPath frontend" || exit 1
    check_port 8080 "nginx dev 入口"    || exit 1
else
    warn "已跳过端口检查"
fi

# ---- 启动 docker compose ----
log "启动 docker compose (dev override)..."
log "  服务参数: ${SERVICE_ARGS[*]:-<全部>}"
docker compose "${COMPOSE_FILES[@]}" up -d "${SERVICE_ARGS[@]}"
if [[ $? -ne 0 ]]; then
    err "docker compose 启动失败"
    exit 1
fi

# ---- 等待 health check ----
wait_healthy() {
    local svc=$1
    local timeout=${2:-180}
    local elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        # docker compose ps --format 用 json 字段 status 包含 health 状态
        local health
        health=$(docker compose "${COMPOSE_FILES[@]}" ps "$svc" --format json 2>/dev/null \
                 | python3 -c "import sys,json; d=json.loads(sys.stdin.read() or '{}'); print(d.get('Health',''))" 2>/dev/null || echo "")
        if [[ -z "$health" ]]; then
            # 没定义 healthcheck 的服务,只要 running 即可
            local state
            state=$(docker compose "${COMPOSE_FILES[@]}" ps "$svc" --format json 2>/dev/null \
                    | python3 -c "import sys,json; d=json.loads(sys.stdin.read() or '{}'); print(d.get('State',''))" 2>/dev/null || echo "")
            if [[ "$state" == "running" ]]; then
                ok "$svc 已运行 (无 healthcheck)"
                return 0
            fi
        elif [[ "$health" == "healthy" ]]; then
            ok "$svc 健康"
            return 0
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        printf "  ⏳ %s 等待中 (%ds/%ds)\r" "$svc" "$elapsed" "$timeout"
    done
    echo ""
    err "$svc 健康检查超时 (${timeout}s),最近日志:"
    docker compose "${COMPOSE_FILES[@]}" logs --tail=30 "$svc" || true
    return 1
}

log "等待服务健康..."
# 决定要等待哪些服务
if [[ ${#SERVICE_ARGS[@]} -gt 0 ]]; then
    WAIT_SERVICES=("${SERVICE_ARGS[@]}")
else
    WAIT_SERVICES=(backend frontend)
fi

FAILED=0
for svc in "${WAIT_SERVICES[@]}"; do
    if ! wait_healthy "$svc" 180; then
        FAILED=1
    fi
done

if [[ $FAILED -ne 0 ]]; then
    err "部分服务未就绪,请查看日志: docker compose ${COMPOSE_FILES[*]} logs"
    exit 1
fi

# ---- 输出访问地址 ----
echo ""
ok "GradPath 开发环境已就绪 🎉"
echo ""
echo "📡 访问地址 (均绑定 127.0.0.1,不暴露外网):"
echo "   前端 (Next.js dev):    http://localhost:3000"
echo "   后端 API (FastAPI):    http://localhost:8001/docs"
echo "   nginx 反向代理入口:    http://localhost:8080"
echo "   flower 监控:           http://localhost:5555/flower"
echo "   n8n 工作流:            http://localhost:5678"
echo ""
echo "🔧 常用命令:"
echo "   查看日志:  docker compose ${COMPOSE_FILES[*]} logs -f"
echo "   停止服务:  docker compose ${COMPOSE_FILES[*]} down"
echo "   查看状态:  docker compose ${COMPOSE_FILES[*]} ps"
echo ""
