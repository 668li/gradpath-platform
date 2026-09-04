#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从真实招生简章/调剂公告正文提取"出身硬门槛"条款。

A2 任务：grad_school_intel.background_discrimination 缺真实数据源，个性化被闸门
（_grad_paths 中 `if not r.data_sources: continue`）关停。本提取器从官方招生
简章/调剂公告的报考条件原文中抓取"出身相关硬门槛"条款，输出结构化 JSON 供
写入 data_sources（带 URL+引用原文），使个性化重新点亮且零造假。

背景语义（2026-09-02 用户拍板"硬门槛条款驱动"）：
  - 不招收/不接受同等学力                → severe（专科被拒）
  - 同等学力须额外条件（不含统一加试）   → moderate（有条件接受）
  - 按本科毕业同等学力身份报考（标准）   → none（专科可报，无额外门槛）
  - 调剂仅限双一流/985/211               → severe
  - 调剂优先双一流/985/211               → moderate
  - 无相关条款                            → 不输出（学校保持中立，不点亮）

提取顺序：明确拒绝 → 有条件 → 标准接受 → 高职兜底（各命中即返回）。
调剂：硬性 → 软性。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# 1) 明确拒绝同等学力
RE_EQV_REJECT = re.compile(
    r"(?:不招收|不接受|不接收|不招|不予接收|不接收报名).{0,20}同等学力"
    r"|同等学力考生.{0,15}(?:不得|不能|不予|不接收|不接受)报考"
    r"|(?:本|我)校.{0,15}(?:不招收|不接受|不接收).{0,15}同等学力"
)
# 2) 报考条件额外要求（有条件接受）— 不匹配"复试时须加试"（教育部统一规定，非该校态度）
RE_EQV_CONDITION = re.compile(
    r"同等学力(?:考生|人员)?.{0,15}(?:须满足|需满足|还须|须符合|须具备).{0,30}(?:要求|条件|专业背景|课程成绩)"
    r"|同等学力.{0,10}跨专业.{0,20}(?:不得|不能|不予)报考"
    r"|同等学力考生.{0,15}(?:仅限|限).{0,15}(?:专业|方向)"
    r"|同等学力.{0,20}(?:须|应|需要|还须)[^。]{0,45}(?:修完|补修|通过|达到|参加|提供|提交|发表|在学期间).{0,25}(?:课程|科目|考试|证明|论文|成果|主干)"
)
# 3) 标准措辞（无额外限制）
RE_EQV_STANDARD = re.compile(
    r"(?:按本科毕业同等学力身份报考|按同等学力身份报考|以同等学力身份报考)"
)
# 4) 高职/专科毕业满 N 年（兜底；本身即"满足报考门槛"而非门槛条款）
RE_EQV_HIGHER_VOC = re.compile(
    r"(?:高职|专科)毕业.{0,15}满?\s*[一二两2]\s*年|获得国家承认的高职.{0,10}毕业学历"
)
# 调剂硬性：仅限/只接收 双一流/985/211 本科
RE_TJ_HARD = re.compile(
    r"(?:仅限|仅接收|只接收|仅面向|限).{0,10}(?:双一流|985|211|重点高校|原211|原985).{0,15}(?:本科|生源|考生)"
    r"|(?:双一流|985|211).{0,10}高校.{0,15}(?:本科|毕业生).{0,6}(?:优先|仅|要求)"
)
# 调剂软性：优先考虑
RE_TJ_SOFT = re.compile(r"(?:双一流|985|211|重点高校).{0,20}(?:优先|可优先|适当优先)")


def _section(text: str, *keywords: str) -> str:
    """截取"报考条件"大段中最早含关键字的上下文片段。

    锚定"报考条件"后找关键字，前 60 后 500 字——HTML 章节标题到正文间距通常
    <400 字，500 覆盖条款主体即可。
    """
    bk = text.find("报考条件")
    if bk >= 0:
        for kw in keywords:
            if kw == "报考条件":
                continue
            i = text.find(kw, bk)
            if i >= 0:
                return text[max(0, bk - 60): i + 500]
    for kw in keywords:
        i = text.find(kw)
        if i >= 0:
            return text[max(0, i - 60): i + 500]
    return ""


def _strip_html(raw: str) -> str:
    """粗粒度 HTML → 文本（足够提取条款即可）。"""
    raw = re.sub(r"<script[\s\S]*?</script>", "", raw, flags=re.I)
    raw = re.sub(r"<style[\s\S]*?</style>", "", raw, flags=re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"&nbsp;?", " ", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw


def _collapse_cn_ws(text: str) -> str:
    """删除中文字符之间的空白——HTML 标签边界产生的噪音（"按本[</p><p>]科毕业"）。"""
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=\d)", "", text)
    text = re.sub(r"(?<=\d)\s+(?=[\u4e00-\u9fff])", "", text)
    return text.strip()


def _make_clause(source: str, tier: str, label: str, text: str, m: re.Match) -> dict[str, str]:
    lo, hi = max(0, m.start() - 40), min(len(text), m.end() + 40)
    return {
        "source": source,
        "tier": tier,
        "label": label,
        "quote": text[lo:hi],
    }


def extract_eqv(text: str) -> dict[str, str] | None:
    """同等学力/专科出身条款。顺序：拒绝→有条件→标准→高职兜底。"""
    for pat, tier, label in (
        (RE_EQV_REJECT, "severe", "明确拒绝同等学力考生"),
        (RE_EQV_CONDITION, "moderate", "同等学力须满足额外条件"),
    ):
        m = pat.search(text)
        if m:
            return _make_clause("eqv", tier, label, text, m)
    m = RE_EQV_STANDARD.search(text)
    if m:
        # 标准措辞可能伴生额外条件："本科结业生，但必须同时满足以下条件：a…b…c…。按本科毕业同等学力身份报考"
        pre = text[max(0, m.start() - 160): m.start()]
        if re.search(r"(?:高职|专科|本科结业|结业生).{0,40}(?:必须|须|需)同时满足(?:以下|下列)?条件", pre):
            return _make_clause("eqv", "moderate", "同等学力须满足额外条件", text, m)
        return _make_clause("eqv", "none", "按本科毕业同等学力身份报考", text, m)
    m = RE_EQV_HIGHER_VOC.search(text)
    if m:
        return _make_clause("eqv_higher_voc", "none", "高职/专科毕业满年限可报考", text, m)
    return None


def extract_tiaoshi(text: str) -> dict[str, str] | None:
    """调剂出身限制条款。顺序：硬性→软性。"""
    for pat, tier, label in (
        (RE_TJ_HARD, "severe", "调剂仅限双一流/985/211本科"),
        (RE_TJ_SOFT, "moderate", "调剂优先双一流/985/211"),
    ):
        m = pat.search(text)
        if m:
            return _make_clause("tiaoshi", tier, label, text, m)
    return None


def analyze(text: str) -> dict[str, Any]:
    """入口：HTML 或纯文本 → 条款列表。"""
    clean = _strip_html(text) if "<" in text else text
    clean = _collapse_cn_ws(clean)
    clauses: list[dict[str, str]] = []
    for extractor in (extract_eqv, extract_tiaoshi):
        clause = extractor(clean)
        if clause:
            clauses.append(clause)
    return {"clause_count": len(clauses), "clauses": clauses}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="提取招生简章/调剂公告中的出身硬门槛条款")
    parser.add_argument("--file", help="输入 HTML/文本文件路径")
    parser.add_argument("--text", help="直接传入正文文本")
    parser.add_argument("--out", help="输出 JSON 路径（缺省打印 stdout）")
    args = parser.parse_args(argv)

    if args.file:
        raw = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        raw = args.text
    else:
        parser.print_usage()
        return 2

    result = analyze(raw)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
