# backend/scripts/auto_review_queue.py
"""自动过闸 CLI —— 消化 t_review_queue_item 的 PENDING 存量（2026-10-01）。

``app/services/research_auto_review.auto_review_pending`` 此前只有爬虫任务间接触发
（爬完库自动跑一次），没有人工单跑入口，导致 PENDING 只能靠 /admin/research-queue
逐条点批。本脚本是那个缺失的入口：默认 dry-run 打印逐条判定明细，供人工抽验后
再决定是否 ``--commit``。

判定逻辑零改动——本脚本只调 service，不复制任何闸门规则（避免口径漂移）。

安全设计：
- **默认 dry-run**：不加 ``--commit`` 一行数据库都不写（service 侧 dry_run=True 不 commit）
- **逐条可读**：每条给 verdict（pass/block/reject）+ 卡点原因 + 质量分，
  抽验时能直接定位"谁被哪道闸挡了、差多少分"
- **对账闭合**：pending 数 == auto_approved + gate_reputation + gate_score + chsi_rejected
  （JOIN 是内连接，每行必落一个 verdict），JSON 里带 closed 字段自证
- **小批量灰度**：``--limit N`` 只处理队列最靠前的 N 条（service 侧确定性排序）
- **阈值可临时覆盖**：``--min-score`` 等仅用于探查不同口径，不写死进代码

用法：
    py -3.13 scripts/auto_review_queue.py                      # dry-run + 逐条明细
    py -3.13 scripts/auto_review_queue.py --json               # JSON（测试断言/留档用）
    py -3.13 scripts/auto_review_queue.py --limit 10           # 只看最前 10 条
    py -3.13 scripts/auto_review_queue.py --json --limit 10 --min-score 50  # 探口径
    py -3.13 scripts/auto_review_queue.py --commit             # 实际放行（幂等，可重跑）
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# 允许直接从 backend/ 目录运行：python scripts/auto_review_queue.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.services.research_auto_review import auto_review_pending

_VERDICT_LABELS = {
    "pass_official_fast_track": "放行·官方快通",
    "pass_admission_content": "放行·招生内容",
    "pass_standard": "放行·三闸全过",
    "block_reputation": "卡·来源信誉",
    "block_score": "卡·质量分",
    "reject_redline": "驳回·研招网红线",
}


def _summarize(stats: dict) -> dict:
    """统计 + 对账闭合自证（details 为空时也能算）。"""
    counted = (
        stats.get("auto_approved", 0)
        + stats.get("gate_reputation", 0)
        + stats.get("gate_score", 0)
        + stats.get("chsi_rejected", 0)
    )
    return {
        "mode": stats.pop("_mode", "unknown"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pending": stats.get("pending", 0),
        "auto_approved": stats.get("auto_approved", 0),
        "promoted": stats.get("promoted", 0),
        "gate_reputation": stats.get("gate_reputation", 0),
        "gate_score": stats.get("gate_score", 0),
        "chsi_rejected": stats.get("chsi_rejected", 0),
        "closed": counted == stats.get("pending", -1),
        "counted": counted,
        "details": stats.get("details", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="对 PENDING 审核队列跑三闸门自动放行（默认 dry-run，不写库）",
    )
    parser.add_argument("--commit", action="store_true", help="实际放行（默认 dry-run 预览）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 摘要（供测试断言）")
    parser.add_argument("--limit", type=int, default=0, help="只处理队列最靠前的 N 条（0=全部）")
    parser.add_argument("--min-score", type=int, default=None, help="覆盖质量分门槛（默认 60）")
    parser.add_argument("--min-history", type=int, default=None, help="覆盖信誉历史量门槛（默认 30）")
    parser.add_argument("--min-pass-rate", type=float, default=None, help="覆盖信誉通过率门槛（默认 0.9）")
    parser.add_argument("--reviewer", default=None, help="审核人邮箱（默认系统管理员账号）")
    args = parser.parse_args()

    kwargs = {"dry_run": not args.commit, "explain": True}
    if args.limit:
        kwargs["limit"] = args.limit
    if args.min_score is not None:
        kwargs["min_score"] = args.min_score
    if args.min_history is not None:
        kwargs["min_history"] = args.min_history
    if args.min_pass_rate is not None:
        kwargs["min_pass_rate"] = args.min_pass_rate
    if args.reviewer:
        kwargs["reviewer_email"] = args.reviewer

    with SessionLocal() as db:
        stats = auto_review_pending(db, **kwargs)
        if "error" in stats:
            print(f"auto_review 中止：{stats['error']}")
            if args.json:
                print(json.dumps(stats, ensure_ascii=False))
            raise SystemExit(1)
        stats["_mode"] = "commit" if args.commit else "dry-run"
        summary = _summarize(stats)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return

    print(f"=== {'实际放行' if args.commit else 'dry-run（未写库）'} ===")
    print(
        f"PENDING {summary['pending']} 条 | 放行 {summary['auto_approved']}"
        f"（落业务表 {summary['promoted']}）| 卡信誉 {summary['gate_reputation']}"
        f" | 卡质量分 {summary['gate_score']} | 红线驳回 {summary['chsi_rejected']}"
    )
    print(f"对账闭合：{summary['counted']}/{summary['pending']} → {'闭合' if summary['closed'] else '不闭合！'}")
    for row in summary["details"]:
        label = _VERDICT_LABELS.get(row["verdict"], row["verdict"])
        score = "" if row.get("score") is None else f" 分={row['score']}"
        print(
            f"  [{label}] {row['item_type']} {row['host'] or '(无源)'}"
            f" {row['credibility']}{score} | {row['reason']} | {row['title'][:60]}"
        )
    if not args.commit:
        print("\n加 --commit 实际放行（幂等，可重复运行）。")


if __name__ == "__main__":
    main()
