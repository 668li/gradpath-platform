#!/usr/bin/env bash
# gp-converge.sh <我的提交ref> [更多ref...] —— 服务器线被并行会话移动时的收敛配方
# 今天（09-06）手动重复了 5 次的动作固化：一次性克隆 → checkout 服务器最新线 →
# cherry-pick 我的提交 → 迁移链单头自检 → 打名为 main 的 bundle。全程零服务器写入、
# 零 reset、零碰他人工作树。打完还需过 gp-preflight.sh 再发射。
set -eu
[ $# -ge 1 ] || { echo "用法: gp-converge.sh <提交ref...> [--clone <路径>]"; exit 1; }
CLONE=/tmp/gpclone
MINE=()
while [ $# -gt 0 ]; do
  case "$1" in
    --clone) CLONE=$2; shift 2 ;;
    *) MINE+=("$1"); shift ;;
  esac
done
cd "$(dirname "$0")/.." || exit 1
MAIN=$(git rev-parse --show-toplevel)

[ -d "$CLONE/.git" ] || git clone --quiet --no-hardlinks "$MAIN" "$CLONE"
cd "$CLONE"
git fetch --quiet "$MAIN" "${MINE[@]}" 2>/dev/null || git fetch --quiet "$MAIN"
git remote get-url gradpath >/dev/null 2>&1 || git remote add gradpath ssh://gradpath/home/ubuntu/gradpath-platform
git fetch --quiet gradpath main
SRV=$(git rev-parse FETCH_HEAD)
echo "服务器线: ${SRV:0:7}"
git checkout --quiet -B main "$SRV"
for c in "${MINE[@]}"; do
  SHA=$(git rev-parse "$c" 2>/dev/null || echo "")
  [ -n "$SHA" ] || { echo "✗ 找不到 $c"; exit 1; }
  if git merge-base --is-ancestor "$SHA" main 2>/dev/null; then echo "= 已在线上: ${SHA:0:7}"; continue; fi
  git cherry-pick --quiet "$SHA" || { echo "✗ cherry-pick $c 冲突——人工解决后 git cherry-pick --continue，或停下改走拍板"; exit 1; }
  echo "✓ 挑入 ${SHA:0:7}"
done

# 迁移链自检（若克隆有 backend 环境；缺 .env 只跳过大检，做文件名级探测）
[ -f backend/.env ] || cp "$MAIN/backend/.env" backend/.env 2>/dev/null || true
if [ -f backend/alembic.ini ]; then
  (cd backend && py -3.13 -m alembic heads 2>/dev/null | tee /tmp/gp-heads.txt >/dev/null || true)
  N=$(grep -c "(head)" /tmp/gp-heads.txt 2>/dev/null || echo 0)
  [ "${N:-0}" -le 1 ] && echo "✓ alembic 单头" || echo "✗ 多头(${N})——先修链再部署（今日幻影 stamp 事故形态）"
fi

SHORT=$(git rev-parse --short main)
B="/tmp/gp-$SHORT.bundle"
git bundle create "$B" "${SRV:0:40}..main" >/dev/null
git bundle list-heads "$B" | grep -q "refs/heads/main" && echo "✓ bundle ref 名为 main"
echo "CONVERGED: $B (base ${SRV:0:7} → ${SHORT})"
echo "下一步: bash tools/gp-preflight.sh main && scp -q $B gradpath:~/ && ssh gradpath 'nohup sh ~/update_from_bundle.sh $(basename "$B") > /tmp/deploy-$SHORT.log 2>&1 &'"
