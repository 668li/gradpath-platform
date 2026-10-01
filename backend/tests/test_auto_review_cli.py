"""auto_review_queue CLI 单元测试（backend/scripts/auto_review_queue.py）。

只测纯函数部分（对账闭合自证 + verdict 标签表）；真正跑闸的行为由
tests/test_research_auto_review.py 覆盖（CLI 不复制任何闸门规则）。
"""

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "auto_review_queue.py"
_spec = importlib.util.spec_from_file_location("auto_review_queue", _SCRIPT)
assert _spec and _spec.loader
auto_review_queue = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auto_review_queue)


def _stats(**over):
    base = {
        "_mode": "dry-run",
        "pending": 4,
        "auto_approved": 1,
        "promoted": 1,
        "gate_reputation": 1,
        "gate_score": 1,
        "chsi_rejected": 1,
        "details": [{"verdict": "pass_standard"}],
    }
    base.update(over)
    return base


class TestSummarize:
    def test_closed_when_counts_match_pending(self):
        s = auto_review_queue._summarize(_stats())
        assert s["closed"] is True
        assert s["counted"] == 4
        assert s["mode"] == "dry-run"

    def test_flags_broken_closure(self):
        """计数对不上 pending 时必须报不闭合（防止漏判被当成全过）。"""
        s = auto_review_queue._summarize(_stats(auto_approved=0))
        assert s["closed"] is False
        assert s["counted"] == 3

    def test_keeps_details_and_drops_private_mode_key(self):
        s = auto_review_queue._summarize(_stats())
        assert s["details"] == [{"verdict": "pass_standard"}]
        assert "_mode" not in s

    def test_zero_pending_is_closed(self):
        s = auto_review_queue._summarize(
            _stats(pending=0, auto_approved=0, promoted=0, gate_reputation=0, gate_score=0, chsi_rejected=0, details=[])
        )
        assert s["closed"] is True


def test_every_verdict_has_human_label():
    """verdict 是 CLI 与 service 之间的契约：新增判定必须同时补标签，否则打原文。"""
    service_verdicts = {
        "pass_official_fast_track",
        "pass_standard",
        "block_reputation",
        "block_score",
        "reject_redline",
    }
    assert service_verdicts <= set(auto_review_queue._VERDICT_LABELS)
