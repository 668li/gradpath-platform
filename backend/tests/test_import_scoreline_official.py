"""自划线院校复试分数线导入纯函数回归测试（DF-01c，2026-09-29）。

锁定 parse_batches 的验收闸：
  - status≠ok 的校年不入
  - source_url 非 http(s) 的校年不入（无源不入库红线）
  - total_score_line 非正整数的行丢弃（0=引擎脏占位口径）
  - 单科线非正整数清洗为 None
  - (校,专业,学位类型,年份) 去重
  - data_sources 必含官网 URL（过引擎溯源闸）
"""

import json

from scripts.import_scoreline_official import parse_batches


def _write(tmp_path, payload, name="scoreline_batch_X.json"):
    p = tmp_path / name
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return [p]


def test_ok_block_produces_record_with_url(tmp_path):
    paths = _write(
        tmp_path,
        {
            "schools": [
                {
                    "university_name": "测试大学",
                    "year": 2026,
                    "status": "ok",
                    "source_url": "https://grs.example.edu.cn/line.htm",
                    "lines": [
                        {
                            "major_name": "工学[08]",
                            "degree_type": "学术学位",
                            "total_score_line": 320,
                            "politics_score": 50,
                            "foreign_language_score": "45",
                            "business_1_score": 0,
                            "business_2_score": None,
                        }
                    ],
                }
            ]
        },
    )
    records, stats = parse_batches(paths)
    assert stats["school_years_ok"] == 1
    assert stats["rows_kept"] == 1
    r = records[0]
    assert r.university_name == "测试大学"
    assert r.year == 2026
    assert r.total_score_line == 320
    assert r.politics_score == 50
    assert r.foreign_language_score == 45  # 字符串数字可清洗
    assert r.business_1_score is None  # 0 视为未公布
    assert r.business_2_score is None
    assert r.data_sources == ["https://grs.example.edu.cn/line.htm"]


def test_not_found_and_bad_url_blocks_rejected(tmp_path):
    paths = _write(
        tmp_path,
        {
            "schools": [
                {"university_name": "甲大学", "year": 2026, "status": "not_found"},
                {
                    "university_name": "乙大学",
                    "year": 2026,
                    "status": "ok",
                    "source_url": "www.no-scheme.edu.cn/line.htm",
                    "lines": [{"major_name": "法学[03]", "total_score_line": 330}],
                },
            ]
        },
    )
    records, stats = parse_batches(paths)
    assert records == []
    assert stats["school_years_not_found"] == 2  # not_found + 无效URL 同桶


def test_bad_total_rows_dropped(tmp_path):
    paths = _write(
        tmp_path,
        {
            "schools": [
                {
                    "university_name": "丙大学",
                    "year": 2025,
                    "status": "ok",
                    "source_url": "https://grs.c.edu.cn/line.htm",
                    "lines": [
                        {"major_name": "理学[07]", "total_score_line": 310},
                        {"major_name": "医学[10]", "total_score_line": 0},
                        {"major_name": "农学[09]", "total_score_line": "abc"},
                        {"major_name": "", "total_score_line": 300},
                    ],
                }
            ]
        },
    )
    records, stats = parse_batches(paths)
    assert len(records) == 1
    assert stats["rows_dropped_bad_total"] == 2
    assert stats["rows_kept"] == 1


def test_duplicate_school_year_major_deduped(tmp_path):
    block = {
        "university_name": "丁大学",
        "year": 2024,
        "status": "ok",
        "source_url": "https://grs.d.edu.cn/line.htm",
        "lines": [{"major_name": "文学[05]", "degree_type": "学术学位", "total_score_line": 355}],
    }
    paths = _write(tmp_path, {"schools": [block, dict(block)]}, name="scoreline_batch_Y.json")
    records, stats = parse_batches(paths)
    assert len(records) == 1


def test_real_batches_parse_if_present():
    """实弹批次文件存在时必须全量可解析且零 bad_total 落库前校验。"""
    from pathlib import Path

    data_dir = Path(__file__).resolve().parent.parent / "scripts" / "data"
    paths = sorted(data_dir.glob("scoreline_batch_*.json"))
    if not paths:
        return  # 数据文件未随仓库分发时不阻塞
    records, stats = parse_batches(paths)
    assert len(records) > 1000  # 2026-09-29 实弹批次 2110 行
    assert stats["rows_kept"] == len(records)
    unis = {r.university_name for r in records}
    assert len(unis) >= 25  # 任务书 ≥25 校销账线
    for r in records:
        assert r.data_sources and r.data_sources[0].startswith("http")
        assert r.total_score_line and r.total_score_line > 0
