"""分数线 PDF 缓存解析器（加时包，2026-09-29，纯解析零网络）。

读 scripts/data/_pdf_cache/ 下按命名约定的 PDF（pypdf 文本层），
解析行 → 合并进 scripts/data/scoreline_batch_C.json（按 校+年 重写块）。

列序按校配置（FILE_MAP 第 4 元 total_first）：
  - total_first=True：每行数字为 [总分, 单科(=100), 单科(>100)]（中山式）
  - total_first=False：[政治, 外语, 业务1[, 业务2], 总分]（清华式）
跨行单元格：名称多行累积到出现纯数字行才发射（pypdf 常拆行）。
码口径：码长>=4 且第三位为 5 → 专业学位；否则学术学位（0301Z1 学硕/035101 专硕均正确）。

用法：py -3.13 scripts/parse_scoreline_pdfs.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

BACKEND_ROOT = Path(__file__).resolve().parent.parent
CACHE = BACKEND_ROOT / "scripts" / "data" / "_pdf_cache"
OUT_FILE = BACKEND_ROOT / "scripts" / "data" / "scoreline_batch_C.json"

# 缓存文件 → (校名, 年份, 官方公示页URL, 总分是否在首列)
FILE_MAP: dict[str, tuple[str, int, str, bool]] = {
    "sysu2026.pdf": ("中山大学", 2026, "https://graduate.sysu.edu.cn/zsw/article/521", True),
    "sysu2025.pdf": ("中山大学", 2025, "https://graduate.sysu.edu.cn/zsw/article/480", True),
}

NUMS_TAIL_RE = re.compile(r"^(?P<name>.*?)\s+(?P<nums>(?:\d{2,4}[\s]+){1,4}\d{2,4})$")
PURE_NUMS_RE = re.compile(r"^(?:\d{2,4}[\s]+){1,4}\d{2,4}$")
CODE_RE = re.compile(r"\[(\d{2,6}[A-Z0-9]{0,2})\]")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
SKIP_RE = re.compile(r"总分|单科|满分|学科门类|学位类别|类别|基本分数线|单独考试|专项计划|分=|分>")


def _degree_of(code: str) -> str:
    """专硕判据：4 位码第三位 ∈ {5,6}（0251/0854/0861/1258…）；2 位门类码=学硕。"""
    if len(code) == 2:
        return "学术学位"
    return "专业学位" if len(code) >= 4 and code[2] in "56" else "学术学位"


def _emit(name: str, nums: list[int], total_first: bool, rows: list[dict], seen: set) -> None:
    name = re.sub(r"\s+", "", re.sub(r"[\s:：、]+$", "", name)).strip()
    if not name or not CJK_RE.search(name):
        return
    code_m = None
    for cm in CODE_RE.finditer(name):
        code_m = cm
    code = code_m.group(1) if code_m else ""
    major = name if name.endswith("]") else (f"{name}[{code}]" if code else name)
    key = major
    if key in seen:
        rows.append({"__stop__": True})  # 同名码复现=进入单独考试/专项区，截断
        return
    seen.add(key)
    if total_first:
        total, rest = nums[0], nums[1:]
    else:
        total, rest = nums[-1], nums[:-1]
    if not 100 <= total <= 500:
        return
    if len(rest) == 1:
        subs = [rest[0], rest[0], None]
    elif len(rest) == 2:
        subs = [rest[0], rest[0], rest[1]]
    elif len(rest) == 3:
        subs = [rest[0], rest[1], rest[2]]
    else:
        subs = [rest[0], rest[1], rest[2], rest[3]]
    rows.append(
        {
            "major_name": major,
            "degree_type": _degree_of(code) if code else "学术学位",
            "total_score_line": total,
            "politics_score": subs[0],
            "foreign_language_score": subs[1],
            "business_1_score": subs[2],
            "business_2_score": subs[3] if len(subs) > 3 else None,
        }
    )


def parse_pdf_text(txt: str, total_first: bool) -> list[dict]:
    lines = [
        re.sub(r"\s+", " ", re.sub(r"[\u3000\xa0]", " ", raw)).strip()
        for raw in txt.split("\n")
    ]
    lines = [ln for ln in lines if ln and not SKIP_RE.search(ln)]
    rows: list[dict] = []
    seen: set[str] = set()
    pend = ""
    for ln in lines:
        if PURE_NUMS_RE.match(ln):
            if pend:
                nums = [int(p) for p in ln.split()]
                _emit(pend, nums, total_first, rows, seen)
                pend = ""
                if rows and rows[-1].get("__stop__"):
                    break
            continue
        m = NUMS_TAIL_RE.match(ln)
        if m and CJK_RE.search(m.group("name")):
            nums = [int(p) for p in m.group("nums").split()]
            _emit(pend + m.group("name"), nums, total_first, rows, seen)
            pend = ""
            if rows and rows[-1].get("__stop__"):
                break
            continue
        if CJK_RE.search(ln) and ("[" in ln or "（" in ln or "、" in ln):
            pend = (pend + ln) if pend else ln
            continue
        if CJK_RE.search(ln) and len(ln) <= 3 and pend:
            pend += ln  # 跨行单元格碎片（如"医"）
            continue
        pend = ""
    return [r for r in rows if not r.get("__stop__")]


def main() -> None:
    payload = {"collector": "batch-C", "schools": []}
    if OUT_FILE.exists():
        payload = json.loads(OUT_FILE.read_text(encoding="utf-8"))
    blocks = {(s["university_name"], s["year"]): s for s in payload["schools"]}
    for fn, (school, year, page_url, total_first) in FILE_MAP.items():
        p = CACHE / fn
        if not p.exists():
            print(f"skip(缺文件) {fn}")
            continue
        rd = PdfReader(str(p))
        txt = "\n".join((pg.extract_text() or "") for pg in rd.pages)
        rows = parse_pdf_text(txt, total_first)
        if len(rows) < 5:
            print(f"FAIL {school} {year} rows={len(rows)} 太少")
            continue
        blocks[(school, year)] = {
            "university_name": school,
            "year": year,
            "status": "ok",
            "source_url": page_url,
            "lines": rows,
        }
        print(f"OK {school} {year} rows={len(rows)}")
    payload["schools"] = list(blocks.values())
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    ok_years = sum(1 for s in payload["schools"] if s["status"] == "ok")
    unis = {s["university_name"] for s in payload["schools"] if s["status"] == "ok"}
    print(f"done: batch ok_school_years={ok_years} ok_schools={len(unis)} -> {OUT_FILE.name}")


if __name__ == "__main__":
    main()
