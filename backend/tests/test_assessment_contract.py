# backend/tests/test_assessment_contract.py
"""跨语言类型对账闸（2026-09-05 对抗审查后新增）。

背景：测评类型散落多处注册（题库/计分器/合法值/前端联合类型/上下文槽位），
加类型时漏改任意一处都只在特定数据流里炸（前科：学历枚举直传 500、isLikert
漏分支）。业界标准答案（FastAPI 官方 SDK 指南 / openapi-typescript / Malt、
alasco 等团队实践）= 单一真源 + 对账守门。codegen 是大工程，本文件先落
对账闸：任一侧加/改类型而另一侧漏改 → 这里红，而不是等生产炸。
"""

import re
from pathlib import Path

from app.api.assessment import _ASSESSMENT_ANSWER_VALUES
from app.services.assessment_service import (
    ASSESSMENT_CALCULATORS,
    ASSESSMENT_QUESTIONS,
)
from app.services.user_context_service import (
    LEARNING_STYLE_ASSESSMENT_TYPE,
    MAIN_ASSESSMENT_TYPES,
)

FRONTEND_TYPES_PATH = Path(__file__).resolve().parents[2] / "frontend" / "types" / "index.ts"


def test_backend_registries_parity():
    """题库/计分器/合法值三张注册表键必须完全一致。"""
    question_types = set(ASSESSMENT_QUESTIONS.keys())
    assert question_types == set(ASSESSMENT_CALCULATORS.keys()), (
        "ASSESSMENT_CALCULATORS 与 ASSESSMENT_QUESTIONS 键不一致，"
        f"差集：{question_types ^ set(ASSESSMENT_CALCULATORS.keys())}"
    )
    assert question_types == set(_ASSESSMENT_ANSWER_VALUES.keys()), (
        "_ASSESSMENT_ANSWER_VALUES 与 ASSESSMENT_QUESTIONS 键不一致，"
        f"差集：{question_types ^ set(_ASSESSMENT_ANSWER_VALUES.keys())}"
    )


def test_frontend_union_matches_backend_registry():
    """前端 AssessmentType 联合类型必须与后端题库注册表逐字一致。"""
    src = FRONTEND_TYPES_PATH.read_text(encoding="utf-8")
    m = re.search(r"export type AssessmentType = ([^;]+);", src)
    assert m, "前端 AssessmentType 定义丢失或改了形态，请同步本对账闸"
    frontend_types = set(re.findall(r'"([a-z_]+)"', m.group(1)))
    backend_types = set(ASSESSMENT_QUESTIONS.keys())
    assert frontend_types == backend_types, (
        f"前端/后端测评类型漂移。仅前端有：{frontend_types - backend_types}；"
        f"仅后端有：{backend_types - frontend_types}。"
        "加类型请同步：题库+计分器+合法值+前端联合类型+TYPE_NAMES/typeOrder"
    )


def test_every_type_classified_into_context_slot():
    """每个测评类型必须归入上下文槽位（主画像 或 学习风格信号），不许裸奔。"""
    all_types = set(ASSESSMENT_QUESTIONS.keys())
    assert all_types == set(MAIN_ASSESSMENT_TYPES) | {LEARNING_STYLE_ASSESSMENT_TYPE}, (
        f"未分类的类型：{all_types - set(MAIN_ASSESSMENT_TYPES) - {LEARNING_STYLE_ASSESSMENT_TYPE}}"
    )
