"""就业质量报告导入纯函数回归测试（DF-03，2026-09-29）。

锁定 parse_batch 的验收闸：
  - status≠ok 不入；source_url 非 http(s) 或非 .edu.cn 官方域名不入
  - year=报告届别年份（非入库年份）
  - pdf_hint/page_numbers 透传（供解析管道消费）
"""

import json

from scripts.import_employment_reports import parse_batch


def test_ok_and_not_found(tmp_path):
    payload = {
        "schools": [
            {
                "university_name": "测试大学",
                "report_year": 2025,
                "status": "ok",
                "source_url": "https://xxgk.example.edu.cn/report.htm",
                "pdf_hint": "https://xxgk.example.edu.cn/r.pdf",
                "page_numbers": ["毕业去向落实率 93.5%"],
            },
            {"university_name": "甲大学", "status": "not_found"},
        ]
    }
    rows, stats = parse_batch(payload)
    assert stats["ok"] == 1 and stats["not_found"] == 1
    assert rows[0]["year"] == 2025
    assert rows[0]["pdf_hint"].endswith(".pdf")
    assert rows[0]["page_numbers"] == ["毕业去向落实率 93.5%"]


def test_non_official_domain_rejected():
    payload = {
        "schools": [
            {
                "university_name": "乙大学",
                "report_year": 2024,
                "status": "ok",
                "source_url": "https://mp.weixin.qq.com/s/abc",
            },
            {
                "university_name": "丙大学",
                "report_year": 2024,
                "status": "ok",
                "source_url": "not-a-url",
            },
        ]
    }
    rows, stats = parse_batch(payload)
    assert rows == []
    assert stats["dropped_not_official"] == 1
    assert stats["dropped_bad_url"] == 1


def test_real_batches_if_present():
    """实弹批次（两文件合计 50 校 ok）解析闸全过。"""
    from pathlib import Path

    data_dir = Path(__file__).resolve().parent.parent / "scripts" / "data"
    total_ok = 0
    for name in ("employment_reports_batch.json", "employment_reports_batch2.json"):
        p = data_dir / name
        if not p.exists():
            continue
        rows, stats = parse_batch(json.loads(p.read_text(encoding="utf-8")))
        assert stats["dropped_bad_url"] == 0 and stats["dropped_not_official"] == 0
        total_ok += len(rows)
    assert total_ok >= 25  # 任务书 DF-03 验收线
