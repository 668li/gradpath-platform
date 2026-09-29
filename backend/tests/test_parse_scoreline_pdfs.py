"""分数线 PDF 文本解析回归测试（加时包 2026-09-29，中山大学式样例）。

锁定 parse_scoreline_pdfs.parse_pdf_text：
  - total_first 列序（中山式：总分 单科100 单科>100）
  - 跨行名称单元格合并 + 纯数字尾行发射
  - 6 位专业码（035101）/自设码（1260S1）学位判据
  - 同名码复现 → 截断（单独考试/专项区不入库）
"""

from scripts.parse_scoreline_pdfs import _degree_of, parse_pdf_text

SYSU_TEXT = """中山大学2026年硕士研究生招生考试复试基本分数线
类别 学科门类/学位类别 总分 单科（满分=100分） 单科（满分>100分）
哲学[01] 345 45 90
经济学[02] 330 45 70
法律（非法学）[035101] 350 50 90
公共政策[1260S1] 360 50 90
城乡规划[0853]、电子信息[0854]、机
械[0855]、材料与化工[0856]、资源与
环境[0857]、能源动力[0858]、土木水
利[0859]、生物与医药[0860]、交通运输[0861]
300 50 60
公共卫生[1053] 305 50 170
公共卫生[1053] 300 40 180
大气科学[0706] 275 40 50
"""


def test_sysu_style_rows() -> None:
    rows = parse_pdf_text(SYSU_TEXT, total_first=True)
    by = {r["major_name"]: r for r in rows}
    assert by["哲学[01]"]["total_score_line"] == 345
    assert by["哲学[01]"]["degree_type"] == "学术学位"
    assert by["哲学[01]"]["politics_score"] == 45
    assert by["哲学[01]"]["business_1_score"] == 90
    assert by["经济学[02]"]["foreign_language_score"] == 45
    assert by["法律（非法学）[035101]"]["degree_type"] == "专业学位"
    assert by["公共政策[1260S1]"]["degree_type"] == "专业学位"
    combined = by[
        "城乡规划[0853]、电子信息[0854]、机械[0855]、材料与化工[0856]、"
        "资源与环境[0857]、能源动力[0858]、土木水利[0859]、生物与医药[0860]、交通运输[0861]"
    ]
    assert combined["degree_type"] == "专业学位"  # 末码 0861
    assert combined["total_score_line"] == 300
    # 同名码复现 → 截断：单独考试区（公共卫生第二行与大气科学）不入
    assert list(by).count("公共卫生[1053]") == 1
    assert "大气科学[0706]" not in by


def test_degree_rule() -> None:
    assert _degree_of("01") == "学术学位"
    assert _degree_of("0301Z1") == "学术学位"
    assert _degree_of("035101") == "专业学位"
    assert _degree_of("0861") == "专业学位"
    assert _degree_of("1258S1") == "专业学位"
