#!/usr/bin/env bash
# GradPath 轻量部署：仅用于「服务器树即运行位置」的非应用文件（monitoring/ docs/ nginx/ tools/ *.md）。
# 这类改动不需要重建镜像，直接 bundle→scp→ff-merge 秒级上线；cron/systemd 读的就是服务器工作树。
# ⚠️ 若改动含 backend/ 或 frontend/ 应用代码，本脚本会拒绝——那必须走 gradpath-deploy 重路径
#    （update_from_bundle.sh 重建镜像 + alembic，~2-45min），因为运行代码 import 自 site-packages 而非工作树。
set -euo pipefail

REPO="${REPO:-/d/职业规划/职业规划}"          # Git Bash 路径；Windows 下按此，必要时 env 覆盖
SSH_ALIAS="${SSH_ALIAS:-gradpath}"
SRV_REPO="${SRV_REPO:-/home/ubuntu/gradpath-platform}"
BRANCH="${BRANCH:-deploy-rebased}"

cd "$REPO"

# 1. 目标 = 当前分支 HEAD；服务器 HEAD 先 fetch 刷新（并行会话可能已挪动，勿凭记忆）
TARGET=$(git rev-parse "$BRANCH")
git fetch "$SSH_ALIAS" "$BRANCH" 2>/dev/null || true
SRV=$(ssh "$SSH_ALIAS" "cd $SRV_REPO && git rev-parse HEAD")
echo "target=$TARGET"
echo "server=$SRV"

if [ "$SRV" = "$TARGET" ]; then echo "已是最新，无需部署"; exit 0; fi

# 2. 安全闸：服务器..目标 的差异必须只落在非应用路径，否则拒绝
CHANGED=$(git diff --name-only "$SRV..$TARGET")
if echo "$CHANGED" | grep -qE '^(backend|frontend)/'; then
  echo "❌ 改动含应用代码（backend/ 或 frontend/），不能走轻量路径。请改用 gradpath-deploy 重路径："
  echo "$CHANGED" | grep -E '^(backend|frontend)/' | sed 's/^/    /'
  exit 1
fi
echo "本次仅非应用文件，走轻量 ff-merge："
echo "$CHANGED" | sed 's/^/    /'

# 3. bundle（区间形式，避免单提交拒建）→ 双端 verify → scp
BUNDLE=$(cygpath -u "${TMPDIR:-/tmp}")/gp-light-${TARGET:0:9}.bundle
git bundle create "$BUNDLE" "$SRV..$TARGET"
git bundle verify "$BUNDLE" >/dev/null
scp -q "$BUNDLE" "$SSH_ALIAS:~/$(basename "$BUNDLE")"

# 4. 服务器 ff-only 合并（非祖先=分叉→停下拍板，绝不 reset）
ssh "$SSH_ALIAS" "cd $SRV_REPO && git fetch ~/$(basename "$BUNDLE") $BRANCH:refs/tmp-light && \
  git merge --ff-only refs/tmp-light && git update-ref -d refs/tmp-light && rm -f ~/$(basename "$BUNDLE") && \
  echo server-now=\$(git rev-parse --short HEAD)"

rm -f "$BUNDLE"
# 5. 对账：服务器 HEAD 必须等于目标
NEW=$(ssh "$SSH_ALIAS" "cd $SRV_REPO && git rev-parse HEAD")
[ "$NEW" = "$TARGET" ] && echo "✅ 轻量部署完成，服务器=$NEW" || { echo "❌ 服务器 HEAD 与目标不符：$NEW"; exit 1; }
