"""四件套完整率端点测试（数据北极星）。

覆盖：整体口径计算、Top100 热度代理口径、total_score_line=0 脏数据过滤、名称归一化匹配。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.models.grad_intel import GradSchoolIntel, GradScorelineRecord, GradYanzhaoProgram
from app.models.school import School
from app.models.user import User


@pytest.fixture
def admin_headers(client, db_session):
    admin = User(
        email="cov-admin@test.com",
        password_hash=hash_password("Admin1234!"),
        name="管理员",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "cov-admin@test.com", "password": "Admin1234!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def seeded_coverage(db_session):
    # 3 所有排名的院校：A 四件套全占、B 缺分数线、C 情报名带空格（归一化应匹配）
    db_session.add_all(
        [
            School(name="苏州大学", slug="suzhou", ranking=40),
            School(name="云南大学", slug="yunnan", ranking=60),
            School(name="西藏大学", slug="xizang", ranking=200),
            School(name="无排名大学", slug="no-rank", ranking=None),
        ]
    )
    SYS = "00000000000000000000000000000000"
    db_session.add_all(
        [
            GradYanzhaoProgram(
                university_name="苏州大学",
                department="计算机学院",
                major_name="计算机",
                degree_type="学硕",
            ),
            GradYanzhaoProgram(
                university_name="云南大学",
                department="法学院",
                major_name="法学",
                degree_type="学硕",
            ),
            GradYanzhaoProgram(
                university_name="苏 州大学",
                department="计算机学院",
                major_name="软件",
                degree_type="专硕",
            ),
            GradSchoolIntel(school_name="苏州大学", major_name="计算机", year=2026, user_id=SYS),
            GradSchoolIntel(school_name="云南大学", major_name="法学", year=2026, user_id=SYS),
            GradSchoolIntel(school_name="苏州大学", major_name="软件", year=2026, user_id=SYS),
            GradScorelineRecord(
                university_name="苏州大学", major_name="计算机", year=2026, total_score_line=350
            ),
            GradScorelineRecord(
                university_name="云南大学", major_name="法学", year=2026, total_score_line=0
            ),
        ]
    )
    db_session.commit()
    return db_session


def test_coverage_requires_admin(client, seeded_coverage):
    resp = client.get("/api/data-freshness/coverage")
    assert resp.status_code in (401, 403)


def test_coverage_overall_and_top100(client, seeded_coverage, admin_headers):
    resp = client.get("/api/data-freshness/coverage", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    overall = body["overall"]
    top = body["top100"]

    # 总体：分数线只算 >0 → 苏州大学（350 有效），云南大学 0 分线被过滤
    assert overall["schools_total"] == 4
    assert overall["full_set"] == 1  # 只有苏州大学四件套全占
    assert overall["full_set_rate"] == round(1 / 4, 4)

    # Top100：无排名大学不参与；苏州/云南/西藏入榜，全占仅苏州
    assert top["total"] == 3
    assert top["full_set"] == 1
    assert top["full_set_rate"] == round(1 / 3, 4)

    # 缺失明细要能指出缺什么
    by_school = {r["school"]: set(r["missing"]) for r in top["missing_sample"]}
    assert by_school["云南大学"] == {"scoreline"}
    assert by_school["西藏大学"] == {"catalog", "intel", "scoreline"}
