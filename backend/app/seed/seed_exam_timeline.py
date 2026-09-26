"""考公时间线 seed（feature 001 / M1）— 零日期常量的诚实骨架 + 证据通道。

宪法级约束（spec §2.5，FR-E3）：
- 本脚本**不含任何日期字面量**；节点日期只能经 services/timeline_service 的
  证据闸（fetch / manual_paste）在运行时真实验证后才允许落库；
- 2027 的 PREDICTED 由 derive_predicted_next_year 从 2026 已证日期推导（FR-E6），
  2026 无证据的环节 2027 一律 UNKNOWN——推算的推算还是编造；
- 取不到证据的节点保持预测/未知态并显示"暂无可核验来源"。宁可没数据，不伪装知道。

用法：
    py -3.13 -m app.seed.seed_exam_timeline                      # 纯骨架（幂等，不触日期）
    py -3.13 -m app.seed.seed_exam_timeline --proposal FILE.json # 按证据提案过闸写 OFFICIAL

提案 JSON（不是数据源——每条在 seed 运行时会重新真实抓取验证，闸拒即拒写）：
    [{"stage_key": "registration", "date": "2025-10-15", "end_date": "2025-10-24",
      "url": "https://www.beijing.gov.cn/...", "exam": "guokao-2026"}]
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.exam_timeline import DateStatus, Exam, ExamNode, NodeStage
from app.services.timeline_service import (
    EvidenceRejected,
    Fetcher,
    apply_evidence_date,
    derive_predicted_next_year,
    upsert_skeleton,
)

# 骨架常量仅允许：考次定义 + 专题入口 URL（FR-E3；URL 可在公告正文实证，非日期）
EXAM_SPECS: tuple[dict[str, Any], ...] = (
    {
        "code": "guokao-2026",
        "name": "2026 国考",
        "track": "guokao",
        "year": 2026,
        # 专题网站地址在公告正文中明文出现（"专题网站，http://bm.scs.gov.cn/kl2026"）
        "official_home_url": "http://bm.scs.gov.cn/kl2026",
        "status": "closed",
    },
    {
        "code": "guokao-2027",
        "name": "2027 国考",
        "track": "guokao",
        "year": 2027,
        # 2027 专题尚未上线——入口挂报名平台稳定域名；公告捕获后 Phase 2 回填具体专题页
        "official_home_url": "http://bm.scs.gov.cn/",
        "status": "upcoming",
    },
    {
        "code": "guangdong-shengkao-2026",
        "name": "2026 广东省考",
        "track": "shengkao",
        "year": 2026,
        # 省考入口未取证前留空——宁缺勿假（FR-E4）
        "official_home_url": "",
        "status": "closed",
    },
    {
        # B2（2026-09-26）：考研线时间节点重建——考公线退役后时间线伴随的主线
        "code": "kaoyan-2027",
        "name": "2027 考研",
        "track": "kaoyan",
        "year": 2027,
        # 研招网稳定域名（规定原文的教育部 gov.cn URL 走证据提案，不放这里）
        "official_home_url": "https://yz.chsi.com.cn/",
        "status": "upcoming",
    },
)


def ensure_exams(db: Session) -> dict[str, Exam]:
    """按 code upsert 考次 + 补齐 12 环节骨架（永不触碰日期诚实字段）。"""
    out: dict[str, Exam] = {}
    for spec in EXAM_SPECS:
        exam = db.query(Exam).filter(Exam.code == spec["code"]).first()
        if exam is None:
            exam = Exam(**spec)
            db.add(exam)
            db.flush()
        upsert_skeleton(db, exam)
        out[spec["code"]] = exam
    # 骨架先落定事务：提案处理中的坏证据 rollback 只撤销提案自身，不连坐骨架
    db.commit()
    return out


def _cached_fetcher() -> Fetcher:
    """单次运行内按 URL 缓存抓取结果——每次运行仍是真实 HTTP，不跨运行造假。"""
    cache: dict[str, tuple[int, bytes]] = {}

    def fetch(url: str) -> tuple[int, bytes]:
        if url not in cache:
            from app.services.timeline_service import _default_fetcher

            cache[url] = _default_fetcher(url)
        return cache[url]

    return fetch


def apply_proposals(
    db: Session,
    exams: dict[str, Exam],
    proposals: list[dict[str, Any]],
    *,
    fetcher: Fetcher | None = None,
    recorded_by: str = "seed",
) -> dict[str, list[str]]:
    """逐条提案过证据闸写 OFFICIAL。失败不中断，汇总报告（审计友好）。"""
    fetch = fetcher or _cached_fetcher()
    report: dict[str, list[str]] = {"ok": [], "rejected": []}
    for prop in proposals:
        if not prop.get("date"):
            # 提案文件里的"无日期记录项"（如查分仅有月份）——留说明不写库
            report["rejected"].append(
                f"{prop.get('exam')}/{prop.get('stage_key')}: no_date_proposed（保持诚实状态，见条目 note）"
            )
            continue
        exam_code = prop.get("exam", "guokao-2026")
        exam = exams.get(exam_code)
        if exam is None:
            report["rejected"].append(f"unknown_exam:{exam_code}")
            continue
        try:
            stage = NodeStage(prop["stage_key"])
        except ValueError:
            report["rejected"].append(f"unknown_stage:{prop.get('stage_key')}")
            continue
        node = next((n for n in exam.nodes if n.stage_key == stage), None)
        if node is None:
            report["rejected"].append(f"missing_node:{exam_code}/{prop['stage_key']}")
            continue
        try:
            on_date = date.fromisoformat(prop["date"])
            end_date = date.fromisoformat(prop["end_date"]) if prop.get("end_date") else None
            apply_evidence_date(
                db,
                node,
                on_date=on_date,
                end_date=end_date,
                source_url=prop["url"],
                recorded_by=prop.get("by", recorded_by),
                fetcher=fetch,
            )
            report["ok"].append(f"{exam_code}/{prop['stage_key']}={prop['date']}")
        except (EvidenceRejected, KeyError, ValueError) as e:
            db.rollback()  # 证据/诚实校验失败的半写回滚，节点保持原诚实态
            report["rejected"].append(f"{exam_code}/{prop.get('stage_key')}: {e}")
    return report


def seed_exam_timeline(
    db: Session,
    proposals: list[dict[str, Any]] | None = None,
    *,
    fetcher: Fetcher | None = None,
) -> dict[str, Any]:
    """幂等主流程：骨架 →（可选）提案过闸 → 2027 预测推导。跑两遍计数不变。"""
    exams = ensure_exams(db)
    proposal_report = {"ok": [], "rejected": []}
    if proposals:
        proposal_report = apply_proposals(db, exams, proposals, fetcher=fetcher)
    predicted = derive_predicted_next_year(db, exams["guokao-2027"], exams["guokao-2026"])
    db.commit()

    summary: dict[str, Any] = {
        "proposal": proposal_report,
        "predicted_2027": predicted,
        "exams": {},
    }
    for code, exam in exams.items():
        counts: dict[str, int] = {"OFFICIAL": 0, "PREDICTED": 0, "UNKNOWN": 0}
        for n in exam.nodes:
            counts[n.date_status.value] += 1
        summary["exams"][code] = counts
    # 宪法级负断言：无证据的 OFFICIAL 行数必须=0
    no_ev = (
        db.query(ExamNode)
        .filter(ExamNode.date_status == DateStatus.OFFICIAL, ExamNode.evidence_id.is_(None))
        .count()
    )
    summary["official_without_evidence"] = no_ev
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", help="证据提案 JSON 文件（每条运行时重验）")
    args = parser.parse_args()

    from app.database import SessionLocal

    proposals = []
    if args.proposal:
        with open(args.proposal, encoding="utf-8") as f:
            proposals = json.load(f)

    with SessionLocal() as db:
        summary = seed_exam_timeline(db, proposals=proposals)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["official_without_evidence"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
