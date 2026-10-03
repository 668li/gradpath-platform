# -*- coding: utf-8 -*-
"""资源导航 seed 数据 — RN-1c（2026-10-03），候选池的唯一真相源。

来源与实测纪律（任务书 2026-10-03）：
- 藏货层候选转录自 delivery《考研资源站点情报-按流程环节-2026-09-19.md》
  （已过对抗审查，未过用户终审）——本 seed 只负责转录，不新增判断；
- 开源精选来自 docs/灵感聚合调研-2026-09-13.md star 清单；
- 每条 sources 字段携带 2026-10-03 实测记录（HTTP 状态/页面 title/仓库活跃度），
  由 backend/scripts/resource_link_probe.py 产出（脚本可复跑复核）；
- 全部 status=pending / user_approved=false：用户终审是唯一转正闸，
  转正动作=用户会话指令→修改本文件 status=active→部署（同门道卡维护协议）；
- 性质核对拦截记录：daxianz.fun 200 但 title=「死去的她」（域名易主）→ 不收录，
  证明逐条性质核对必要。

用户点名区（RN-4 预留）：
# >>> 用户点名区：站长给出的网站清单在此追加，逐条实测后按同结构入池 <<<
# {"name": "...", "url": "...", "category": "...", "note": "...", ...}
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.resource_link import (
    RESOURCE_ADDED_VIA_AI,
    RESOURCE_ADDED_VIA_USER,
    RESOURCE_CATEGORY_EMPLOYMENT,
    RESOURCE_CATEGORY_KAOYAN,
    RESOURCE_CATEGORY_OFFICIAL,
    RESOURCE_CATEGORY_OPEN_SOURCE,
    RESOURCE_COPYRIGHT_CAUTION,
    RESOURCE_COPYRIGHT_ORIGINAL,
    RESOURCE_STATUS_PENDING,
    ResourceLink,
)

logger = logging.getLogger(__name__)

_CHECKED = "2026-10-03"

_LINKS: list[dict] = [
    # ---------------- 考研干货 · 藏货层（delivery 文档转录） ----------------
    {
        "name": "Simple408 · AI 原生 408 简纲",
        "url": "https://simple408.cn/",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "AI 原生教材形态的 408 简纲，个人匠人站样板，用户点名首批收录",
        "risk_note": "github.io 备用域同步收录，主域失联时走备用",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_USER,
        "sources": [
            {
                "title": "主域实测",
                "url": "https://simple408.cn/",
                "http_status": 200,
                "page_title": "408 简纲 · AI 原生的考研408教材",
                "verdict": "ok",
                "checked_at": _CHECKED,
                "note": "性质核对：AI 原生教材，与收录定位一致",
            }
        ],
    },
    {
        "name": "Simple408 备用域",
        "url": "https://liangbohan.github.io/postgraduate-exam-website/",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "Simple408 的 github.io 备用域，与主域同内容",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_USER,
        "sources": [
            {
                "title": "备用域实测",
                "url": "https://liangbohan.github.io/postgraduate-exam-website/",
                "http_status": 200,
                "page_title": "408 简纲 · AI 原生的考研408教材",
                "verdict": "ok",
                "checked_at": _CHECKED,
                "note": "与主域 title 一致，确认同站",
            }
        ],
    },
    {
        "name": "408CSFamily · 408 全家桶文档站",
        "url": "https://142vip.github.io/408CSFamily/",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "VitePress 形态的 408 全科知识文档站，配套开源仓库 703 star 持续维护",
        "risk_note": "delivery 审查备注：需核内容原创性（若为王道笔记二创属灰区）——请终审时判断",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "页面实测",
                "url": "https://142vip.github.io/408CSFamily/",
                "http_status": 200,
                "page_title": "首页 | 计算机408全家桶",
                "verdict": "ok",
                "checked_at": _CHECKED,
            },
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/142vip/408CSFamily",
                "stars": 703,
                "pushed_at": "2026-09-22",
                "verdict": "ok",
                "checked_at": _CHECKED,
                "note": "活跃维护中",
            },
        ],
    },
    {
        "name": "Didnelpsun/CS408 · 自写四科笔记",
        "url": "https://github.com/Didnelpsun/CS408",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "408 四科完整自写笔记（王道为参考书），结构清晰可整仓下载",
        "risk_note": "仓库 2023-05 后未再更新（内容稳定型，非活跃维护）",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/Didnelpsun/CS408",
                "stars": 276,
                "pushed_at": "2023-05-23",
                "verdict": "ok",
                "checked_at": _CHECKED,
                "note": "停滞但内容完整，如实标注",
            }
        ],
    },
    {
        "name": "LYuYang61/408 · 手写笔记",
        "url": "https://github.com/LYuYang61/408",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "手写数据结构等 408 笔记，2026 年仍在更新",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/LYuYang61/408",
                "stars": 215,
                "pushed_at": "2026-01-20",
                "verdict": "ok",
                "checked_at": _CHECKED,
                "note": "近期有更新",
            }
        ],
    },
    {
        "name": "WilliamTrouvaille/CS408_Note",
        "url": "https://github.com/WilliamTrouvaille/CS408_Note",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "11408（408+数一）备考笔记，2025 年仍有维护",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/WilliamTrouvaille/CS408_Note",
                "stars": 55,
                "pushed_at": "2025-10-25",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "研岛 · 408 在线题库",
        "url": "https://www.408dao.com/",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "408 真题模考与题单练习平台，在线刷题用",
        "risk_note": "⚠️ 含历年真题载体（同英语/408 真题仓口径标灰区）+ 部分功能登录墙，请终审单独拍板",
        "copyright_tier": RESOURCE_COPYRIGHT_CAUTION,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "页面实测",
                "url": "https://www.408dao.com/",
                "http_status": 200,
                "page_title": "研岛 - 408考研题库 | 计算机考研专业课练习平台",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "荒原之梦 · 考研数学",
        "url": "https://zhaokaifeng.com/",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "2017 年起个人维护的考研数学站，图形化讲解+真题解析免费，八年可持续",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "页面实测",
                "url": "https://zhaokaifeng.com/",
                "http_status": 200,
                "page_title": "荒原之梦 – 专注于考研数学|高等数学|线性代数|概率统计",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "Canis 考研数学笔记",
        "url": "https://blandalpha.github.io/",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "开源 GPL 数二笔记（基于张宇18讲整理），Obsidian Publish 镜像",
        "risk_note": "github.io 境内可达性一般，有 Obsidian 镜像兜底",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "页面实测",
                "url": "https://blandalpha.github.io/",
                "http_status": 200,
                "page_title": "Canis的主页",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "TingQang/Math-Notes",
        "url": "https://github.com/TingQang/Math-Notes",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "LaTeX 排版的考研数学三科笔记，2026 年初仍有更新",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/TingQang/Math-Notes",
                "stars": 3,
                "pushed_at": "2026-01-09",
                "verdict": "ok",
                "checked_at": _CHECKED,
                "note": "star 少但活跃，藏货层本就小众",
            }
        ],
    },
    {
        "name": "Mangolia-club/Kaoyan-Math-Doc",
        "url": "https://github.com/Mangolia-club/Kaoyan-Math-Doc",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "MkDocs 形态数一复习文档+个人批注",
        "risk_note": "仓库 2022-10 后未更新（如实标注）",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/Mangolia-club/Kaoyan-Math-Doc",
                "stars": 18,
                "pushed_at": "2022-10-09",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "patrick-andstar/kaoyan-math-ai",
        "url": "https://github.com/patrick-andstar/kaoyan-math-ai",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "数一 Obsidian 资料库，OCR+AI 整理流程，AI 原生类藏货（simple408 同类）",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/patrick-andstar/kaoyan-math-ai",
                "stars": 78,
                "pushed_at": "2026-06-02",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "XColorful/Politics-Obsidian-Note",
        "url": "https://github.com/XColorful/Politics-Obsidian-Note",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "政治开源协作笔记（CC BY-SA 4.0），政治品类孤品级藏货，2026-09 仍活跃",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/XColorful/Politics-Obsidian-Note",
                "stars": 141,
                "pushed_at": "2026-09-18",
                "license": "CC-BY-SA-4.0",
                "verdict": "ok",
                "checked_at": _CHECKED,
                "note": "活跃+明示协议，安全性最高档",
            }
        ],
    },
    {
        "name": "m2kar/KaoYan-English · 真题集",
        "url": "https://github.com/m2kar/KaoYan-English",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "英语一真题 1980-2020（PDF/Word/手译版），手译版是特色",
        "risk_note": "⚠️ 版权灰区：历年真题再排版，delivery 审查定级 caution，请终审单独拍板；仓库 2021-10 后未更新",
        "copyright_tier": RESOURCE_COPYRIGHT_CAUTION,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/m2kar/KaoYan-English",
                "stars": 390,
                "pushed_at": "2021-10-14",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    # ---------------- 官方入口（只挂外链，时间线主场在产品内） ----------------
    {
        "name": "研招网",
        "url": "https://yz.chsi.com.cn/",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_OFFICIAL,
        "note": "报名/调剂/查分的唯一官方系统，本站时间线功能的数据主场，此处只挂外链",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_USER,
        "sources": [
            {
                "title": "页面实测",
                "url": "https://yz.chsi.com.cn/",
                "http_status": 200,
                "page_title": "中国研究生招生信息网",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "学信网",
        "url": "https://www.chsi.com.cn/",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_OFFICIAL,
        "note": "学籍/学历官方查询，考研报名与政审环节的官方依赖",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_USER,
        "sources": [
            {
                "title": "页面实测",
                "url": "https://www.chsi.com.cn/",
                "http_status": 200,
                "page_title": "中国高等教育学生信息网（学信网）",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "教育部",
        "url": "https://www.moe.gov.cn/",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_OFFICIAL,
        "note": "招生政策与国家线发布的最高官方源",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_USER,
        "sources": [
            {
                "title": "页面实测",
                "url": "https://www.moe.gov.cn/",
                "http_status": 200,
                "page_title": "中华人民共和国教育部政府门户网站",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "国家大学生就业服务平台",
        "url": "https://www.ncss.cn/",
        "track": "employment",
        "category": RESOURCE_CATEGORY_OFFICIAL,
        "note": "教育部主办的官方就业服务平台，求职线的官方信息源",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_USER,
        "sources": [
            {
                "title": "页面实测",
                "url": "https://www.ncss.cn/",
                "http_status": 200,
                "page_title": "国家大学生就业服务平台",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    # ---------------- 开源精选（跨场景自我管理/求职/身份参考） ----------------
    {
        "name": "career-ops · 求职即运营系统",
        "url": "https://github.com/career-ops-hq/career-ops",
        "track": "employment",
        "category": RESOURCE_CATEGORY_EMPLOYMENT,
        "note": "7.3 万 star：把求职做成扫描→评估→行动→追踪→复盘的运营闭环，方法论与本站决策中心同构",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/career-ops-hq/career-ops",
                "stars": 73354,
                "pushed_at": "2026-10-03",
                "verdict": "ok",
                "checked_at": _CHECKED,
                "note": "当日仍在推送，极活跃",
            }
        ],
    },
    {
        "name": "developer-roadmap · 技能路线图",
        "url": "https://github.com/kamranahmedse/developer-roadmap",
        "track": "employment",
        "category": RESOURCE_CATEGORY_EMPLOYMENT,
        "note": "36.8 万 star：各技术岗的完整成长路线图，看清整条路+标记学到哪",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/kamranahmedse/developer-roadmap",
                "stars": 368761,
                "pushed_at": "2026-10-02",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "coder2gwy · 程序员考公指南",
        "url": "https://github.com/coder2gwy/coder2gwy",
        "track": "common",
        "category": RESOURCE_CATEGORY_OPEN_SOURCE,
        "note": "2.7 万 star：程序员视角的考公全流程经验指南，身份代入感强（跨线参考，非考公线功能）",
        "risk_note": "指南已完稿（2022 年后无更新），内容稳定型",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/coder2gwy/coder2gwy",
                "stars": 27684,
                "pushed_at": "2022-02-11",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "developer2gwy",
        "url": "https://github.com/miss-mumu/developer2gwy",
        "track": "common",
        "category": RESOURCE_CATEGORY_OPEN_SOURCE,
        "note": "从程序员到公务员的上岸最佳实践，与 coder2gwy 互为补充",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/miss-mumu/developer2gwy",
                "stars": 11307,
                "pushed_at": "2024-08-06",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "张雪峰技能 · 敢说真话的决策框架",
        "url": "https://github.com/alchaincyf/zhangxuefeng-skill",
        "track": "common",
        "category": RESOURCE_CATEGORY_OPEN_SOURCE,
        "note": "1 万 star：敢说真话的专业选择决策框架，思路与本站劝退卡/敢说真话翻译器同源",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/alchaincyf/zhangxuefeng-skill",
                "stars": 10375,
                "pushed_at": "2026-08-25",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "Super Productivity · 时间盒调度",
        "url": "https://github.com/johannesjo/super-productivity",
        "track": "common",
        "category": RESOURCE_CATEGORY_OPEN_SOURCE,
        "note": "2.2 万 star开源待办：Timeboxing（时间盒）调度而非清单堆积，备考节奏管理可用的重工具",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/johannesjo/super-productivity",
                "stars": 22492,
                "pushed_at": "2026-10-03",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "beaverhabits · 极简习惯打卡",
        "url": "https://github.com/daya0576/beaverhabits",
        "track": "common",
        "category": RESOURCE_CATEGORY_OPEN_SOURCE,
        "note": "1.8 千 star 开源习惯打卡（BSD-3），连胜机制轻量，可自部署",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/daya0576/beaverhabits",
                "stars": 1847,
                "pushed_at": "2026-09-17",
                "license": "BSD-3-Clause",
                "verdict": "ok",
                "checked_at": _CHECKED,
                "note": "灵感调研文档中的仓库名有误（beaverhabits/beaverhabits），实测修正为 daya0576",
            }
        ],
    },
    # ---------------- RN-4 定向调研（GitHub topic 扫描 + exa 检索，2026-10-03） ----------------
    {
        "name": "neville-studio/408-exam-paper · 408 真题",
        "url": "https://github.com/neville-studio/408-exam-paper",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "408 历年真题 PDF 整理（MIT 协议标注），2026 年仍活跃维护",
        "risk_note": "⚠️ 版权灰区：历年真题再排版，delivery 审查定级 caution，请终审单独拍板",
        "copyright_tier": RESOURCE_COPYRIGHT_CAUTION,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/neville-studio/408-exam-paper",
                "stars": 219,
                "pushed_at": "2026-08-13",
                "license": "MIT",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "exam-data/NETEMVocabulary · 考研英语大纲词汇",
        "url": "https://github.com/exam-data/NETEMVocabulary",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "考研英语大纲词汇结构化数据集（可导入 Anki 等工具二次利用）",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/exam-data/NETEMVocabulary",
                "stars": 248,
                "pushed_at": "2026-06-06",
                "license": "NOASSERTION",
                "verdict": "ok",
                "checked_at": _CHECKED,
                "note": "官方大纲词汇的数据化整理",
            }
        ],
    },
    {
        "name": "xiaolei565/aimto408",
        "url": "https://github.com/xiaolei565/aimto408",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "4.6 千 star 的 408 备考资源与复习路线汇总，知名度高",
        "risk_note": "⚠️ 无开源协议（默认版权保留）+ 2023-08 后未更新，资料汇编类请终审拍板",
        "copyright_tier": RESOURCE_COPYRIGHT_CAUTION,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/xiaolei565/aimto408",
                "stars": 4631,
                "pushed_at": "2023-08-21",
                "license": None,
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "awesome-nuaa-cs-kaoyan · 南航计算机考研",
        "url": "https://github.com/nuaa-cs-kaoyan/awesome-nuaa-cs-kaoyan",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "南航计算机考研单校 awesome 清单（GPL-3.0）：单校深度藏货的样板形态",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/nuaa-cs-kaoyan/awesome-nuaa-cs-kaoyan",
                "stars": 369,
                "pushed_at": "2025-04-03",
                "license": "GPL-3.0",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "Benature/WordReview · 单词制卡工具",
        "url": "https://github.com/Benature/WordReview",
        "track": "kaoyan",
        "category": "tool",
        "note": "677 star 开源 Anki 制卡工具（LGPL-3.0），考研英语单词复习工作流",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/Benature/WordReview",
                "stars": 677,
                "pushed_at": "2024-02-07",
                "license": "LGPL-3.0",
                "verdict": "ok",
                "checked_at": _CHECKED,
            }
        ],
    },
    {
        "name": "kaoyan-navigator-skill · AI 择校导航",
        "url": "https://github.com/mcxiaoxiao/kaoyan-navigator-skill",
        "track": "kaoyan",
        "category": RESOURCE_CATEGORY_KAOYAN,
        "note": "面向 AI Agent 的考研择校 Skill（MIT）：证据分级+来源保留的择校调研方法论，AI 原生新品类",
        "copyright_tier": RESOURCE_COPYRIGHT_ORIGINAL,
        "added_via": RESOURCE_ADDED_VIA_AI,
        "sources": [
            {
                "title": "仓库活跃度（GitHub API）",
                "url": "https://github.com/mcxiaoxiao/kaoyan-navigator-skill",
                "stars": 30,
                "pushed_at": "2026-06-08",
                "license": "MIT",
                "verdict": "ok",
                "checked_at": _CHECKED,
                "note": "star 低但属'不搜不知道'的 AI 原生藏货",
            }
        ],
    },
    # >>> 用户点名区：站长给出的网站清单在此追加，逐条实测后按同结构入池 <<<
]

# 性质核对拦截记录（不收录，只留档防回踩）：
# - daxianz.fun：2026-10-03 实测 200 但 title=「死去的她」——域名易主内容已换，性质核对不通过
# - qiuxu13534/learn-english：1 star、2017 停滞、含他人课程笔记整理——对抗审查 P1-4 判"大概率杀"，不入池免稀释信噪比；站长点名可复活
# - CodePanda66/CSPostgraduate-408：5675 star 但 archived=True（作者归档）+ 无 License——归档仓不收
# - D1N910/yzchsihelper：0 star、2023-04 后停滞——价值不足
# - itiaoji.com 考研调剂网：商业机构运营的信息聚合站（"北大博士后团队"营销话术）——通用层大站纪律
# - Senhai-k/cs-kaoyan-ai：明示无开源许可证（RIGHTS.md 不授予使用权）——版权不明不收
# - delivery 排除清单（研新生/睿博/kaoyan.run/文都/跨考/医考帮/桔子新传/B站合集/
#   ddy-ddy/导师评价UGC/posstos11-star 等）照单沿用，永不入池


def seed_resource_links(db: Session) -> tuple[int, int]:
    """幂等导入资源导航候选：按 url 去重，已存在跳过。

    Returns:
        (inserted, skipped)
    """
    inserted = 0
    skipped = 0
    existing = {row[0] for row in db.query(ResourceLink.url).with_entities(ResourceLink.url)}
    for spec in _LINKS:
        if spec["url"] in existing:
            skipped += 1
            continue
        db.add(
            ResourceLink(
                name=spec["name"],
                url=spec["url"],
                track=spec["track"],
                category=spec["category"],
                note=spec["note"],
                risk_note=spec.get("risk_note"),
                copyright_tier=spec.get("copyright_tier", RESOURCE_COPYRIGHT_ORIGINAL),
                status=RESOURCE_STATUS_PENDING,
                added_via=spec.get("added_via", RESOURCE_ADDED_VIA_AI),
                user_approved=False,
                sources=spec["sources"],
                recently_added=True,
            )
        )
        inserted += 1
    db.commit()
    logger.info(
        "资源导航 seed 完成：新增 %d，跳过 %d（共 %d 条定义，全部 pending 待终审）",
        inserted,
        skipped,
        len(_LINKS),
    )
    return inserted, skipped
