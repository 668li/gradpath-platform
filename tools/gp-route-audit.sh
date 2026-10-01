#!/usr/bin/env bash
# gp-route-audit.sh — 全站路由 30x 审计（复盘 2026-10-01「新增做②」）
#
# 动机：night-shift 实锤 next.config.js 遗留 redirect 把 /decision-lab 与
# /decision-engine 两核心页 307 打死而全站入口仍指向——"功能存在"≠"可达"。
# 对核心路由逐个 GET 跟随重定向，比对最终路径，30x 异常一眼可见。
#
# 用法：
#   bash tools/gp-route-audit.sh                    # 服务器内网视角（匿名）
#   BASE=https://quxianglab.cn bash ...             # 外部视角
#   TOKEN=<access_token> bash ...                   # 登录态：AUTH 页期望保持自身
#
# 路由表格式：route|匿名期望|登录态期望（留空=保持原路径）
# 判读纪律：MISMATCH 只在期望路径 != 最终路径时出现；http→https 301 属规范化自动剥除。

set -uo pipefail
BASE="${BASE:-http://127.0.0.1/}"
HOST="${HOST:-quxianglab.cn}"
TOKEN="${TOKEN:-}"

# route|anon_expect|auth_expect（空 auth_expect=与 anon 相同）
ROUTES=(
  "/||"
  "/login|/login|"
  "/register||"                              # 匿名可停留（已登录跳走在前端处理）
  "/dashboard|/login|/dashboard"
  "/decision-engine||/decision-engine"       # 夜班从 307 里救回的核心页
  "/decision-lab||/decision-lab"             # 同上
  "/decision-center|/login|/decision-center"
  "/decision-os||/decision-os"               # 客户端守卫，匿名 SSR 可达
  "/decisions|/login|/decision-center"       # 已知重定向（退役页归口）
  "/micro-actions|/login|/micro-actions"
  "/growth|/login|/growth"
  "/growth-patterns|/login|/growth-patterns"
  "/assessment|/login|/assessment"
  "/employment|/login|/employment"
  "/major-prospects||"
  "/kaoyan|/login|/kaoyan"
  "/timeline|/login|/timeline"
  "/interview|/login|/interview"
  "/community|/login|/community"
  "/skills|/login|/skills"
  "/war-room|/login|/war-room"
)

MODE=anon; [ -n "$TOKEN" ] && MODE=auth
PASS=0; FAIL=0
printf "mode=%s base=%s\n" "$MODE" "$BASE"
printf "%-22s %-6s %-24s %s\n" "ROUTE" "CODE" "FINAL_PATH" "VERDICT"
for entry in "${ROUTES[@]}"; do
  IFS='|' read -r route anon auth <<<"$entry"
  expect="$anon"; [ "$MODE" = auth ] && { expect="${auth:-$anon}"; }
  [ -z "$expect" ] && expect="$route"
  out=$(curl -sL -o /dev/null -w "%{http_code} %{url_effective}" \
        ${TOKEN:+-H "Authorization: Bearer $TOKEN"} \
        -H "Host: ${HOST}" --max-time 15 "${BASE}${route}")
  code="${out%% *}"
  final_url="${out#* }"
  final_path="${final_url#*//*/}"; final_path="/${final_path#*/}"
  final_path="${final_path%%\?*}"
  if [ "$final_path" = "$expect" ]; then
    printf "%-22s %-6s %-24s OK\n" "$route" "$code" "$final_path"
    PASS=$((PASS+1))
  else
    printf "%-22s %-6s %-24s MISMATCH(expect %s)\n" "$route" "$code" "$final_path" "$expect"
    FAIL=$((FAIL+1))
  fi
done
echo "----"
echo "mode=$MODE PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
