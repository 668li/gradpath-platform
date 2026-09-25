"""路径模拟器 v2 测试 — 真数据胜率推演（2026-09-25 重构）。

覆盖：
- service 层：报录比字符串解析 / 分位数 / 百分位 / 考公量纲分簇 / 诚实降级（N<5）
- API 层：simulate 请求校验 / 响应结构（无单点预测数）/ 引擎叠加层降级
- 零造假红线：响应不含满意度/净资产/10年曲线等旧范式字段
"""

from app.services.career_simulator_service import (
    _cluster_of_bureau,
    _percentile,
    _percentile_of_score,
    _pos_word,
    _ratio_to_float,
    simulate_paths,
)

# ----------------------------------------------------------------------
# 单元：报录比解析 / 分位数 / 百分位
# ----------------------------------------------------------------------


def test_ratio_to_float():
    assert _ratio_to_float("15:1") == 15.0
    assert _ratio_to_float(" 8：1 ") == 8.0
    assert _ratio_to_float("约15:1") is None  # 脏值拒绝
    assert _ratio_to_float("") is None
    assert _ratio_to_float(None) is None


def test_percentile_linear_interpolation():
    vals = [1, 2, 3, 4, 5]
    assert _percentile(vals, 0.5) == 3
    assert _percentile(vals, 0.25) == 2
    assert _percentile([7], 0.5) == 7
    assert _percentile([], 0.5) == 0.0


def test_percentile_of_score_requires_min_sample():
    small = [100, 110, 120]  # N=3 < 5
    assert _percentile_of_score(small, 110) is None
    enough = sorted([100 + i * 5 for i in range(10)])
    pct = _percentile_of_score(enough, 122)
    assert pct is not None and 40 <= pct <= 60  # 122 落在中间


def test_pos_word_never_result_language():
    """位置描述词不得含结果性判断（对抗审查：badge 不当概率用）。"""
    for pct in (5, 30, 60, 90, None):
        w = _pos_word(pct)
        assert "概率" not in w and "稳" not in w and "推荐" not in w


# ----------------------------------------------------------------------
# 单元：考公量纲分簇（对抗审查致命项的回归锚点）
# ----------------------------------------------------------------------


def test_bureau_cluster_split():
    assert _cluster_of_bureau("国家税务总局广州市税务局") == "general"
    assert _cluster_of_bureau("成都铁路公安局") == "police"
    assert _cluster_of_bureau("吉林出入境边防检查总站") == "police"
    assert _cluster_of_bureau("广州海事局") == "general"
    assert _cluster_of_bureau("外交部") == "central"
    assert _cluster_of_bureau("某神秘单位") == "other"
    assert _cluster_of_bureau(None) is None


# ----------------------------------------------------------------------
# service 层：simulate_paths 诚实降级与结构
# ----------------------------------------------------------------------


def test_simulate_empty_db_degrades_honestly(db_session):
    """空库 → 结构完整、无编造数字、诚实缺口非空。"""
    result = simulate_paths(
        db_session, [{"path_type": "grad", "target": "985", "estimated_score": 350}]
    )
    p = result["paths"][0]
    assert p["path_type"] == "grad"
    assert p["metrics"] == []  # 无数据不给数字
    assert p["honest_gaps"]  # 如实说明
    assert "不等于" in p["disclaimer"]  # 固定免责在场
    # 零造假红线：旧范式字段不得回归
    assert "satisfaction" not in p
    assert "net_worth" not in p
    assert "yearly" not in p


def test_simulate_grad_with_data(db_session):
    from app.models.grad_intel import GradSchoolIntel

    for i in range(8):
        db_session.add(
            GradSchoolIntel(
                user_id="0" * 32,
                school_name=f"测试大学{i}",
                major_name="计算机",
                school_tier="985",
                year=2026,
                admission_ratio=f"{10 + i}:1",
                score_line=320 + i * 5,
            )
        )
    db_session.commit()

    result = simulate_paths(
        db_session, [{"path_type": "grad", "target": "985", "estimated_score": 340}]
    )
    p = result["paths"][0]
    labels = [m["label"] for m in p["metrics"]]
    assert any("报录比" in l for l in labels)
    assert any("复试线" in l for l in labels)
    # 每个数字带样本量与来源（证据链铁律）
    for m in p["metrics"]:
        assert m["sample_size"] >= 5
        assert m["source"]
    # 你的位置：340 在 [320..355] 线性分布里应在中段
    assert p["your_position"] is not None
    assert p["your_position"]["percentile"] >= 30
    assert "样本" in p["sample_note"]  # 样本性质声明在场


def test_simulate_civil_clusters_dimension_safe(db_session):
    from app.models.gwy_score_line import GwyScoreLine

    # 两簇不同量纲的数据（复刻生产实测分布）
    for i in range(6):
        db_session.add(
            GwyScoreLine(
                id=f"tax{i}",
                year=2026,
                batch="首批",
                dept_name="税务局",
                bureau=f"国家税务总局测试市税务局{i}",
                position_code=f"T00{i}",
                min_score=110.0 + i,
            )
        )
    for i in range(6):
        db_session.add(
            GwyScoreLine(
                id=f"pol{i}",
                year=2026,
                batch="首批",
                dept_name="铁路公安",
                bureau=f"测试铁路公安局{i}",
                position_code=f"P00{i}",
                min_score=55.0 + i,
            )
        )
    db_session.commit()

    result = simulate_paths(
        db_session, [{"path_type": "civil", "target": "general", "estimated_score": 112}]
    )
    p = result["paths"][0]
    m = p["metrics"][0]
    # 只统计 general 簇（~110-115），不得混入 police 簇（~55-60）
    assert 105 <= m["p50"] <= 120
    assert p["your_position"]["percentile"] >= 10  # 112 在 general 簇中低位以上
    # 分簇概览同时呈现两簇
    assert set(p["clusters"].keys()) >= {"general", "police"}


def test_simulate_career_official_anchor(db_session):
    from app.models.market_data import MarketData

    db_session.add(
        MarketData(
            indicator="城镇非私营单位就业人员年平均工资",
            category="全体",
            value=129441.0,
            unit="元/年",
            year=2025,
            source="国家统计局",
            source_url="https://www.stats.gov.cn/test",
        )
    )
    db_session.commit()

    result = simulate_paths(db_session, [{"path_type": "career"}])
    p = result["paths"][0]
    assert any("官方" in m["source"] for m in p["metrics"])
    assert any(m.get("source_url") for m in p["metrics"])
    # 个体预测免责在场
    assert any("个体" in gap for gap in p["honest_gaps"])


def test_engine_analysis_layer(db_session):
    """engine_input 带专业时叠加引擎结论；引擎异常时降级不阻塞。"""
    result = simulate_paths(
        db_session,
        [{"path_type": "career"}],
        engine_input={"major": "计算机"},
    )
    # 引擎可能因数据不足内部降级，但键必须存在且不抛错
    assert "engine_analysis" in result


# ----------------------------------------------------------------------
# API 层
# ----------------------------------------------------------------------


def test_api_simulate_validation(client):
    resp = client.post(
        "/api/career-simulator/simulate",
        json={"paths": [{"path_type": "unknown"}]},
    )
    assert resp.status_code == 422

    resp = client.post(
        "/api/career-simulator/simulate",
        json={"paths": [{"path_type": "grad"}] * 4},
    )
    assert resp.status_code == 422  # 超 3 条拒绝


def test_api_simulate_no_auth_required(client):
    """模拟器保持旧版无鉴权口径（公开工具页）。"""
    resp = client.post(
        "/api/career-simulator/simulate",
        json={"paths": [{"path_type": "grad", "target": "985"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["method_note"]
    assert len(body["paths"]) == 1


def test_api_presets_and_meta(client):
    assert client.get("/api/career-simulator/presets").status_code == 200
    resp = client.get("/api/career-simulator/meta")
    assert resp.status_code == 200
    clusters = {c["id"] for c in resp.json()["clusters"]}
    assert clusters == {"general", "police", "central"}
