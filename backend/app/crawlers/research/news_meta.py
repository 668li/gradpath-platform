"""考研资讯结构化元信息抽取（规则版，Phase G）。

在关键时间点（key_dates，research_promote 已有）之外，把"决策数据卡"
需要的高价值字段用规则抽取：招生人数 / 考试科目 / 参考书目。

设计原则（与 quality.py / experience_quality.py 一致）：
- 纯正则本地计算，零 LLM 成本，审核确认落库时同步完成
- 抽不到就留空（None / []），诚实降级，不编造数字
- LLM 增强挂载点见 services/experience_enhance.py / news_enhance.py

全部返回 JSON 安全结构：{"enrollment_count": int|None,
"exam_subjects": [str], "reference_books": [str]}
"""
import re

# 招生人数：招/录 字眼附近 ≤15 字的范围内出现"数字+人"（容忍"约/拟/计划/个"等修饰）
# 例：拟招收 120 人 / 计划招生80人 / 拟录取 45 人左右 / 新增 300 个名额
# \d{1,5} 让 5 位数进入护栏（>9999 拒绝），避免 \d{1,4} 把 99999 截断成 9999 漏检
_ENROLL_RE = re.compile(
    r"(?:拟?招(?:生|收)?|拟?录(?:取|用)|计划招(?:生|收)|扩招|新增)"
    r"[^。；\n]{0,15}?"
    r"(?:约|共|拟)?\s*(\d{1,5})\s*(?:名|个)?\s*(?:人|位|名额)"
)
# 考试科目：初试科目/考试科目/专业课 之后的科目段（到句号/分号/换行/复试 为止）。
# 两种合法形态，避免把"初试科目调整公告(一)"这类标题整句误抓成科目：
#   a) 冒号引导：初试科目：①101思想政治理论 / 考试科目：数据结构 / 专业课：操作系统
#   b) 代码引导（无冒号）：专业课①408计算机学科专业基础（多为标题里的科目指代）
# \n 作为段边界：title+content 拼接时标题内匹配需在换行处截止（避免吞后续正文）
_SUBJECT_COLON_RE = re.compile(
    r"(?:初试|考试|笔试|专业课)(?:科目|课程)?[:：]\s*(.{1,120}?)(?=复试|加试|面试|。|\.|\n|$)",
    re.S,
)
_SUBJECT_CODE_RE = re.compile(
    r"(?:初试|考试|笔试|专业课)(?:科目|课程)?\s*"
    r"((?:[①-⑧]\s*)?\d{3}[^。；\n]{0,110}?)(?=复试|加试|面试|。|\.|\n|$)",
    re.S,
)
# 科目代码+名称：①101思想政治理论 / 101思想政治理论 / 政治
_CODE_NAME_RE = re.compile(r"\d{3}\s*([\u4e00-\u9fff]{2,16})")
# 参考书目：书名号内容（权威教材特征强，误报率低）。
# 前置捕获：紧跟 3 位科目代码的《》是科目名指代（如 440《新闻与传播专业基础》），非参考书
_BOOK_RE = re.compile(r"(\d{3})?\s*《([^》《]{2,60})》")


def _dedupe(items: list[str], limit: int = 8) -> list[str]:
    """去重保序并截断。"""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        item = item.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def _extract_enrollment_count(title: str, content: str) -> int | None:
    text = f"{title or ''}\n{(content or '')[:3000]}"
    m = _ENROLL_RE.search(text)
    if not m:
        return None
    try:
        num = int(m.group(1))
    except (TypeError, ValueError):
        return None
    # 合理性护栏：招生人数通常是 1-4 位数（个位数多为"1人"等极小专业），超 9999 视为误配
    if num <= 0 or num > 9999:
        return None
    return num


def _extract_exam_subjects(title: str, content: str) -> list[str]:
    text = f"{title or ''}\n{(content or '')[:3000]}"
    subjects: list[str] = []
    matched = None
    for pattern in (_SUBJECT_COLON_RE, _SUBJECT_CODE_RE):
        matched = pattern.search(text)
        if matched:
            break
    if matched:
        segment = matched.group(1)
        # 按常见分隔符拆出科目名
        parts = re.split(r"[、；;，,①②③④⑤⑥⑦⑧\s]+", segment)
        for part in parts:
            part = part.strip(" ：:·—").strip()
            if not part or part in ("等", "如下", "科目"):
                continue
            # 优先取"代码+名称"里的名称（如"101思想政治理论" → 思想政治理论）
            cm = _CODE_NAME_RE.match(part)
            name = cm.group(1) if cm else part
            if name and len(name) >= 2:
                subjects.append(name)
    return _dedupe(subjects)


def _extract_reference_books(title: str, content: str) -> list[str]:
    text = f"{title or ''}\n{(content or '')[:4000]}"
    books: list[str] = []
    for m in _BOOK_RE.finditer(text):
        # 紧跟 3 位科目代码的《》是科目名指代（440《新闻与传播专业基础》），非参考书
        if m.group(1):
            continue
        books.append(m.group(2).strip())
    return _dedupe(books, limit=6)


def extract_news_structured_meta(title: str, content: str) -> dict:
    """从标题+正文抽取资讯结构化元信息（规则版）。

    返回 {"enrollment_count": int|None, "exam_subjects": [str],
          "reference_books": [str]} —— 抽不到保持 None/[]。
    """
    return {
        "enrollment_count": _extract_enrollment_count(title, content),
        "exam_subjects": _extract_exam_subjects(title, content),
        "reference_books": _extract_reference_books(title, content),
    }
