#!/usr/bin/env bash
# tools/topology.sh — GradPath 三线拓扑一条命令实测（反幻觉真相工具）
#
# 设计原则：让"实测"比"推断"更便宜。任何关于 本地/origin/生产 状态的断言，
# 先跑本工具，拿输出说话；没有输出支撑的状态句一律标"推断，未验证"。
#
# 用法：
#   bash tools/topology.sh                          # snapshot：三线现状+时间戳
#   bash tools/topology.sh content <sha> [路径]      # <sha> 的内容是否仍在 HEAD 线里
#   bash tools/topology.sh symbol <模式> <app相对路径> # 生产 site-packages 里有没有这段代码
#
# 退出码（可当闸门用）：
#   snapshot 恒 0；content：0=超集(无删除行) 1=有内容被改/删(看输出判断)；
#   symbol：0=命中 1=未命中(生产不在线) 2=用法/环境错
#
# 已知限制：symbol 的模式不能含单引号（ssh 引号地狱前科）；中文模式实测可用。

set -u
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT" || exit 2
PROXY="http://127.0.0.1:7897"
SSH_HOST="gradpath"
SERVER_REPO="/home/ubuntu/gradpath-platform"
PROD_CODE_GLOB="/usr/local/lib/python3*/site-packages/app"

stamp() { echo "== $(date '+%Y-%m-%d %H:%M:%S') =="; }

case "${1:-snapshot}" in
  snapshot)
    stamp
    echo "--- 本地 ---"
    echo "当前分支: $(git rev-parse --abbrev-ref HEAD) @ $(git rev-parse --short HEAD)"
    for b in main deploy-rebased; do
      git rev-parse --verify -q "$b" >/dev/null && echo "分支 $b: $(git rev-parse --short "$b")"
    done
    echo "工作区: $(git status --short | wc -l) 个未提交条目"
    echo "--- origin（ls-remote 实时，绝不信任 tracking ref）---"
    git -c http.proxy="$PROXY" ls-remote origin refs/heads/main 2>/dev/null \
      | awk '{print "origin/main: " substr($1,1,7)}' \
      || echo "origin/main: <取不到——代理/网络故障，禁止凭记忆推断>"
    echo "--- 生产 ---"
    ssh "$SSH_HOST" "cd $SERVER_REPO && echo 服务器HEAD: \$(git rev-parse --short HEAD) && echo 服务器工作区脏条目: \$(git status --short | wc -l)" 2>/dev/null \
      || echo "服务器HEAD: <取不到——ssh 故障>"
    ssh "$SSH_HOST" "docker exec gradpath-prod-db-1 psql -U gradpath -d gradpath -t -c 'SELECT version_num FROM alembic_version'" 2>/dev/null \
      | tr -d ' \n' | sed 's/^/生产alembic: /' || echo "生产alembic: <取不到>"
    echo
    echo "提示：并行会话活跃期，本快照保质期以小时计——任何写动作之后即过期，须重跑。"
    ;;

  content)
    sha="${2:?用法: content <sha> [路径]}"
    path="${3:-}"
    stamp
    if git merge-base --is-ancestor "$sha" HEAD 2>/dev/null; then
      echo "$sha 是 HEAD 祖先（提交在线），但内容可能被后续提交改动——看下面的 diff"
    else
      echo "$sha 不是 HEAD 祖先（孤儿/另一条线）——它的独有内容是否已并入，以下面 diff 为准"
    fi
    args=(diff "$sha" HEAD)
    [ -n "$path" ] && args+=(-- "$path")
    deletions=$(git "${args[@]}" | grep -c '^-[^-]' || true)
    additions=$(git "${args[@]}" | grep -c '^+[^+]' || true)
    echo "git diff $sha..HEAD${path:+ -- $path}: 删除行=$deletions 新增行=$additions"
    if [ "$deletions" -eq 0 ]; then
      echo "结论: $sha 的内容是 HEAD 的严格子集（无内容丢失）"
      exit 0
    fi
    echo "结论: HEAD 相对 $sha 有 $deletions 行删除——逐行看下方输出，区分"有意替换"与"丢失""
    git "${args[@]}" | head -60
    exit 1
    ;;

  symbol)
    pat="${2:?用法: symbol <模式> <app相对路径，如 services/path_decision_engine.py>}"
    rel="${3:?用法: symbol <模式> <app相对路径>}"
    stamp
    out=$(ssh "$SSH_HOST" "docker exec gradpath-prod-backend-1 sh -c 'grep -n \"$pat\" $PROD_CODE_GLOB/$rel 2>/dev/null | head -5; true'" 2>/dev/null)
    if [ -n "$out" ]; then
      echo "生产 site-packages/$rel 命中:"
      echo "$out"
      exit 0
    fi
    echo "生产 site-packages/$rel 未命中「$pat」——该代码未在线（或路径/模式写错，先本地 grep 对照）"
    exit 1
    ;;

  *)
    echo "未知子命令: $1（可用: snapshot | content | symbol）" >&2
    exit 2
    ;;
esac
