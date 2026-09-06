#!/usr/bin/env bash
# gp-preflight.sh <目标ref(要部署的本地提交)> —— 部署发射前的机器闸（只读，除非 --fix）
# 固化 2026-09-06 部署风暴五连坑：服务器线被并行会话 force-reset（祖先断裂）、
# DB 被 stamp 到线上不存在的幻影迁移、磁盘机器闸、docker 基础镜像被 prune 后拉不到
# （Docker Hub 国内超时）、bundle ref 必须名为 main。
set -u
TARGET=${1:?用法: gp-preflight.sh <目标ref> [--fix]}
FIX=${2:-}
cd "$(dirname "$0")/.." || exit 1
FAIL=0
say() { echo "[$1] $2"; }

# 1) 服务器 HEAD 是目标的祖先？（ff-only 可行性——并行重置探测器）
SRV=$(ssh -o ConnectTimeout=10 gradpath 'cd ~/gradpath-platform && git fetch origin 2>/dev/null; git rev-parse HEAD')
SRV=${SRV:-unknown}
if git cat-file -e "$TARGET^{commit}" 2>/dev/null && git merge-base --is-ancestor "$SRV" "$TARGET" 2>/dev/null; then
  say PASS "服务器HEAD ${SRV:0:7} 是 ${TARGET:0:7} 的祖先，可 ff 部署"
else
  say FAIL "服务器线(${SRV:0:7})不是目标祖先=已被并行会话移动/重置 → 先跑 tools/gp-converge.sh 收敛到服务器线之上，禁止 reset 硬上"
fi

# 2) 磁盘水位（update 脚本机器闸同值 6291456KB，这里留 8G 实际余量提醒）
AVAIL=$(ssh gradpath 'df --output=avail / | tail -1' | tr -d ' ')
if [ "${AVAIL:-0}" -ge 8388608 ]; then
  say PASS "磁盘余 $((AVAIL/1024/1024))G（≥8G，构建峰值无虞）"
elif [ "${AVAIL:-0}" -ge 6291456 ]; then
  say WARN "磁盘余 $((AVAIL/1024/1024))G 过闸但贴近构建峰值风险；冷缓存首建需 ~8G"
else
  say FAIL "磁盘余 $((AVAIL/1024/1024))G < 6G 机器闸必拒；回收序：docker builder prune -f → docker image prune -f → apt clean → journalctl --vacuum-size=50M（卷/容器数据不碰，需拍板）"
fi

# 3) 基础镜像在场（prune 后 Docker Hub 国内不可达 = 今日 DeadlineExceeded 教训）
for img in python:3.11-slim node:20-alpine; do
  if ssh gradpath "docker images -q $img | grep -q ." ; then
    say PASS "基础镜像在场 $img"
  elif [ "$FIX" = "--fix" ]; then
    say FIX  "拉取并 retag $img（daocloud 国内源）"
    ssh gradpath "docker pull docker.m.daocloud.io/library/$img >/dev/null 2>&1 && docker tag docker.m.daocloud.io/library/$img $img" \
      && say PASS "$img 已恢复" || say FAIL "$img 拉取失败——换源或找腾讯内网镜像"
  else
    say FAIL "基础镜像缺失 $img → Docker Hub 不可达会烧 40min 超时死；--fix 自动经 daocloud 恢复"
  fi
done

# 4) DB stamp vs 目标迁移树（幻影 stamp 探测——今日 b5d9/c8d4 悬空事故）
STAMP=$(ssh gradpath 'docker exec gradpath-prod-backend-1 sh -c "cd /app && python -m alembic current" 2>/dev/null' | tail -1 | awk '{print $1}')
if [ -n "$STAMP" ] && git ls-tree -r --name-only "$TARGET" -- backend/migrations/versions backend/alembic/versions 2>/dev/null | grep -q -- "-$STAMP"; then
  say PASS "DB stamp $STAMP 在目标迁移树中（alembic 步可过）"
elif [ -z "$STAMP" ]; then
  say WARN "读不到 DB stamp（容器未起？alembic 步风险自负）"
else
  say FAIL "DB stamp $STAMP 在目标树无对应文件=幻影 stamp → 部署第4步必红。修复：git log --all -S $STAMP 找到原始迁移文件归还到目标线（文件已在 DB 应用过时归位即 no-op，勿改 DB）"
fi

# 5) origin 前进探测（只报不拦）
ORIG=$(git ls-remote origin main 2>/dev/null | cut -c1-10)
[ -n "$ORIG" ] && say INFO "origin/main=${ORIG:0:7}（与部署无关，推分支时再对账）"

echo "-----"
[ $FAIL -eq 0 ] && echo "PREFLIGHT: GO" || echo "PREFLIGHT: NO-GO（上面 FAIL 项全部解决前禁止发射）"
exit $FAIL
