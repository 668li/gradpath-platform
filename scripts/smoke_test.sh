#!/usr/bin/env bash
#
# GradPath 冒烟测试 - Bash 版本
#
# 启动服务后自动验证关键路径,5 秒内反馈。
# 验证: 后端健康 / 后端登录 API / 前端根路径重定向 / 前端登录页 / 前端代理 API / 前端 dashboard
#
# Usage: ./scripts/smoke_test.sh
#

set -u

# 配置
BACKEND_URL="http://localhost:8001"
FRONTEND_URL="http://localhost:4001"
TEST_EMAIL="test-185651@example.com"
TEST_PASSWORD="Test12345678!"
TIMEOUT_SEC=10

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

pass_count=0
fail_count=0
failures=()
backend_token=""
frontend_token=""

info() { echo -e "${CYAN}[INFO]${NC} $1"; }
pass() { echo -e "${GREEN}[PASS]${NC} $1"; pass_count=$((pass_count + 1)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; fail_count=$((fail_count + 1)); failures+=("$1"); }

# 截断预览
truncate_str() {
    local s="$1"
    local len=${2:-200}
    if [ -z "$s" ]; then echo ""; return; fi
    if [ ${#s} -le $len ]; then echo "$s"; else echo "${s:0:$len}..."; fi
}

# 临时文件
TMP_LOGIN=$(mktemp)
TMP_DASH=$(mktemp)
trap 'rm -f "$TMP_LOGIN" "$TMP_DASH"' EXIT

# ========== Test 1: 后端健康 ==========
info "Test 1/6: 后端健康检查 $BACKEND_URL/health"
resp=$(curl -s -m $TIMEOUT_SEC -w "\n%{http_code}" "$BACKEND_URL/health" 2>/dev/null) || true
http_code=$(echo "$resp" | tail -n1)
body=$(echo "$resp" | sed '$d')
if [ "$http_code" = "200" ] && echo "$body" | grep -q '"status":"ok"' && echo "$body" | grep -q '"database":"connected"'; then
    pass "HTTP 200, status=ok, database=connected"
else
    fail "Test 1: 后端健康 (期望 200/status=ok/database=connected, 实际 status=$http_code, body=$(truncate_str "$body"))"
fi

# ========== Test 2: 后端登录 API ==========
info "Test 2/6: 后端登录 API POST $BACKEND_URL/api/auth/login"
body_json='{"email":"'"$TEST_EMAIL"'","password":"'"$TEST_PASSWORD"'"}'
resp=$(curl -s -m $TIMEOUT_SEC -w "\n%{http_code}" -X POST "$BACKEND_URL/api/auth/login" \
    -H "Content-Type: application/json" -d "$body_json" 2>/dev/null) || true
http_code=$(echo "$resp" | tail -n1)
body=$(echo "$resp" | sed '$d')
backend_token=$(echo "$body" | grep -oE '"access_token"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | sed -E 's/.*"access_token"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/')
if [ "$http_code" = "200" ] && [ -n "$backend_token" ]; then
    preview=$(echo "$backend_token" | cut -c1-20)
    pass "HTTP 200, access_token=${preview}..."
else
    fail "Test 2: 后端登录 API (期望 200/含 access_token, 实际 status=$http_code, body=$(truncate_str "$body"))"
fi

# ========== Test 3: 前端根路径 307 重定向 ==========
info "Test 3/6: 前端根路径 $FRONTEND_URL/ (期望 307 -> /login)"
http_code=$(curl -s -o /dev/null -m $TIMEOUT_SEC -w "%{http_code}" "$FRONTEND_URL/" 2>/dev/null) || true
location=$(curl -s -I -m $TIMEOUT_SEC "$FRONTEND_URL/" 2>/dev/null | tr -d '\r' | grep -i "^location:" | head -n1 | sed -E 's/^[Ll]ocation:[[:space:]]*//')
if [ "$http_code" = "307" ] && echo "$location" | grep -q "/login"; then
    pass "HTTP 307, Location=$location"
else
    fail "Test 3: 前端根路径重定向 (期望 307 + Location 含 /login, 实际 status=$http_code, Location=$location)"
fi

# ========== Test 4: 前端登录页 ==========
info "Test 4/6: 前端登录页 $FRONTEND_URL/login (期望 200 + '登录 GradPath')"
http_code=$(curl -s -o "$TMP_LOGIN" -m $TIMEOUT_SEC -w "%{http_code}" "$FRONTEND_URL/login" 2>/dev/null) || true
body=$(cat "$TMP_LOGIN")
if [ "$http_code" = "200" ] && echo "$body" | grep -q "登录 GradPath"; then
    pass "HTTP 200, HTML 包含 '登录 GradPath'"
else
    fail "Test 4: 前端登录页 (期望 200 + 含 '登录 GradPath', 实际 status=$http_code, body 长度=${#body})"
fi

# ========== Test 5: 前端代理 API ==========
info "Test 5/6: 前端代理 API POST $FRONTEND_URL/api/auth/login"
resp=$(curl -s -m $TIMEOUT_SEC -w "\n%{http_code}" -X POST "$FRONTEND_URL/api/auth/login" \
    -H "Content-Type: application/json" -d "$body_json" 2>/dev/null) || true
http_code=$(echo "$resp" | tail -n1)
body=$(echo "$resp" | sed '$d')
frontend_token=$(echo "$body" | grep -oE '"access_token"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | sed -E 's/.*"access_token"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/')
if [ "$http_code" = "200" ] && [ -n "$frontend_token" ]; then
    preview=$(echo "$frontend_token" | cut -c1-20)
    pass "HTTP 200, access_token=${preview}..."
else
    fail "Test 5: 前端代理 API (期望 200/含 access_token, 实际 status=$http_code, body=$(truncate_str "$body"))"
fi

# ========== Test 6: 前端 dashboard (带 cookie) ==========
info "Test 6/6: 前端 dashboard $FRONTEND_URL/dashboard (带 cookie, 期望 200 + '看板'/'dashboard')"
token="$frontend_token"
if [ -z "$token" ]; then token="$backend_token"; fi
if [ -z "$token" ]; then
    fail "Test 6: 前端 dashboard (无可用 token, 前置登录测试失败)"
else
    http_code=$(curl -s -o "$TMP_DASH" -m $TIMEOUT_SEC -w "%{http_code}" \
        -H "Cookie: gradpath_token=$token" "$FRONTEND_URL/dashboard" 2>/dev/null) || true
    body=$(cat "$TMP_DASH")
    matched=0
    if echo "$body" | grep -q "看板"; then matched=1; fi
    if echo "$body" | grep -qi "dashboard"; then matched=1; fi
    if [ "$http_code" = "200" ] && [ "$matched" = "1" ]; then
        pass "HTTP 200, HTML 包含 '看板'/'dashboard'"
    else
        fail "Test 6: 前端 dashboard (期望 200 + HTML 含 '看板'/'dashboard', 实际 status=$http_code, body 长度=${#body})"
    fi
fi

# ========== 总结 ==========
total=$((pass_count + fail_count))
echo ""
echo -e "${YELLOW}========================================${NC}"
if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}Summary: ${pass_count}/${total} passed - ALL GREEN${NC}"
else
    echo -e "${RED}Summary: ${pass_count}/${total} passed${NC}"
    echo -e "${RED}Failed tests:${NC}"
    for f in "${failures[@]}"; do
        echo -e "${RED}  - $f${NC}"
    done
fi
echo -e "${YELLOW}========================================${NC}"

if [ $fail_count -gt 0 ]; then exit 1; else exit 0; fi
