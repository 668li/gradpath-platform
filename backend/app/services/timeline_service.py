"""考公时间线服务（feature 001）— 骨架定义 + 证据链硬闸 + 诚实状态机。

宪法 1/4 + spec §2.5 的实现真身。本文件是唯一合法写路径：

- ``require_evidence_fetch``：OFFICIAL 的 fetch 通道。真实 HTTP 抓取 → 200 +
  正文 ≥2KB（排 SPA/跳转壳）+ 正文归一化命中目标日期 → 产证据行。
- ``record_manual_paste``：OFFICIAL 的 manual_paste 通道。粘贴官方公告原文 +
  官方域 URL，校验粘贴文本含日期才放行，全文留档可审计。
- ``validate_honesty``：诚实字段组合单点闸（UNKNOWN⇒日期必空；OFFICIAL⇒证据必填）。
- ``apply_evidence_date``：节点日期写入唯一入口，串起以上三闸 + 状态机禁回退。
- ``derive_predicted_next_year``：FR-E6 预测锚点链——只有上一年同环节存在
  已证（OFFICIAL 带证据）日期时，次年节点才允许 PREDICTED（平移一年），
  否则一律 UNKNOWN。推算的推算还是编造。

骨架常量（SKELETON_12）只允许 stage_key/标题/材料清单/入口 URL——
**所有日期字段零默认值**（FR-E3），凭模型记忆手填日期在构造上不可能。
"""

from __future__ import annotations

import hashlib
import html as html_lib
import ipaddress
import logging
import re
import socket
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.exam_timeline import (
    DateStatus,
    EvidenceChannel,
    Exam,
    ExamNode,
    NodeStage,
    TimelineEvidence,
)

logger = logging.getLogger(__name__)

# 测试/脚本可注入的 fetcher：返回 (status_code, body_bytes)。默认走 httpx。
Fetcher = Callable[[str], tuple[int, bytes]]


class EvidenceRejected(Exception):
    """证据闸拒绝——消息必须说明拒在哪一条，供 seed 日志审计。"""


# ----------------------------------------------------------------------
# 骨架常量：12 环节（无日期！FR-E3）
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class StageSpec:
    stage: NodeStage
    seq: int
    title: str
    entry_hint: str  # "kl2026"=挂考次专题网站 / ""=无固定入口
    materials: tuple[str, ...]
    action_guide: str


SKELETON_12: tuple[StageSpec, ...] = (
    StageSpec(
        NodeStage.announce,
        1,
        "公告发布",
        "",
        ("无（信息准备期）",),
        "关注国家公务员局专题网站公告发布；公告含招录职位表、报考政策与日程。公告后 3 日内定目标岗位区间。",
    ),
    StageSpec(
        NodeStage.registration,
        2,
        "网上报名",
        "kl",
        ("身份证", "学历学位证书（学信网可查）", "报名需填写的学习经历/工作经历信息"),
        "登录专题网站报名，每次只能选报 1 个职位；报名期内未通过资格审查可改报其他职位。",
    ),
    StageSpec(
        NodeStage.payment,
        3,
        "报名确认与缴费",
        "kl",
        ("银行卡/支付宝/微信（缴费通道）", "报名序号（查询后务必牢记）"),
        "通过资格审查后登录专题网站进行网上报名确认并缴费；未确认缴费视为放弃。",
    ),
    StageSpec(
        NodeStage.admission_ticket,
        4,
        "打印准考证",
        "kl",
        ("报名序号+密码（登录打印）", "多备 2 份纸质版"),
        "在报名确认成功的专题网站打印准考证，务必留意准考证上的考点与入场时间要求。",
    ),
    StageSpec(
        NodeStage.written,
        5,
        "笔试",
        "",
        ("准考证", "有效身份证件", "考试用品（黑色字迹钢笔/签字笔、2B铅笔、橡皮）"),
        "公共科目为行政职业能力测验和申论；8个非通用语职位外语水平测试及金融监管、证监、公安专业科目笔试时间以公告为准。",
    ),
    StageSpec(
        NodeStage.score,
        6,
        "成绩与合格分数线查询",
        "kl",
        ("准考证号+身份证号"),
        "登录专题网站查询笔试成绩和合格分数线（具体开放时间在公告发布后另行通知，以官方页面为准）。",
    ),
    StageSpec(
        NodeStage.adjustment,
        7,
        "调剂",
        "kl",
        ("笔试成绩", "未通过首批入围的备选职位清单"),
        "达到笔试合格线但未进入首批面试名单的考生关注调剂公告与职位，按公告要求在专题网站报名调剂。",
    ),
    StageSpec(
        NodeStage.interview,
        8,
        "面试",
        "",
        ("身份证+准考证（按各招录机关要求）", "学历学位证书原件等资格审查材料"),
        "面试人员名单在专题网站公布；各招录机关面试时间、地点详见其在本部门网站和专题网站发布的面试公告。",
    ),
    StageSpec(
        NodeStage.medical,
        9,
        "体检",
        "",
        ("身份证", "近期免冠照片（按招录机关要求）"),
        "招录机关按综合成绩从高到低确定体检考察人选；留意招录机关通知的体检集合时间与空腹等要求。",
    ),
    StageSpec(
        NodeStage.political,
        10,
        "考察（政审）",
        "",
        ("学习工作表现证明", "档案材料配合核查", "无违法犯罪记录等证明（按考察组清单）"),
        "招录机关负责考察实施；如实配合档案核查与座谈，提前联系可能出证的单位/学校。",
    ),
    StageSpec(
        NodeStage.publicity,
        11,
        "拟录用公示",
        "",
        ("无（监督期）",),
        "体检考察合格后，招录机关在本部门网站和专题网站公示拟录用人员，公示期 5 个工作日。",
    ),
    StageSpec(
        NodeStage.hire,
        12,
        "备案录用",
        "",
        ("毕业证学位证原件", "报到通知要求的其他材料"),
        "公示期满无异议办理备案手续；录用报到与入职培训按招录机关通知执行。",
    ),
)

# 政府域名白名单（证据 source_url 硬约束）：*.gov.cn
_GOV_DOMAIN_RE = re.compile(r"(^|\.)gov\.cn$", re.IGNORECASE)
# 正文最小字节数：排除跳转壳/SPA 壳（09-12 探针：985B 跳转壳 / 4276B SPA 壳）
_MIN_BODY_BYTES = 2000


# ----------------------------------------------------------------------
# URL 安全：仅 http/https + 政府域 + 非内网（SSRF 防护，对齐安全约束）
# ----------------------------------------------------------------------


def _validated_gov_url(url: str) -> str:
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise EvidenceRejected(f"URL 协议必须是 http/https：{url!r}")
    host = p.hostname
    if not host:
        raise EvidenceRejected(f"URL 无法解析主机名：{url!r}")
    if not _GOV_DOMAIN_RE.search(host):
        raise EvidenceRejected(f"证据来源域名必须是政府域 *.gov.cn，实际：{host!r}")
    # host 是 *.gov.cn 时仍拒绝字面 IP/内网伪装（纵深防御）
    try:
        infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80))
    except socket.gaierror as e:  # pragma: no cover - 网络故障
        raise EvidenceRejected(f"主机解析失败：{host} ({e})") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local or ip.is_multicast:
            raise EvidenceRejected(f"主机解析到非公网地址，拒绝：{host} → {ip}")
    return url


def _default_fetcher(url: str) -> tuple[int, bytes]:
    """真实 HTTP 抓取（低频率单页，合规红线 3）。"""
    import httpx

    resp = httpx.get(
        url,
        timeout=25.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; GradPath-Evidence/1.0)"},
    )
    return resp.status_code, resp.content


# ----------------------------------------------------------------------
# 正文归一化 + 日期命中
# ----------------------------------------------------------------------

_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_ANY_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def html_to_text(raw: bytes) -> str:
    """HTML → 去标签去空白噪声的纯文本（含实体解码）。"""
    s = raw.decode("utf-8", errors="ignore")
    s = _TAG_RE.sub(" ", s)
    s = _ANY_TAG_RE.sub(" ", s)
    s = html_lib.unescape(s)
    return _WS_RE.sub(" ", s).strip()


def _date_forms(d: date) -> list[str]:
    return [
        f"{d.year}年{d.month}月{d.day}日",
        f"{d.year}年{d.month:02d}月{d.day:02d}日",
        d.isoformat(),
        f"{d.year}.{d.month}.{d.day}",
    ]


def contains_date(text: str, target: date) -> str | None:
    """正文是否含 target 日期。返回命中片段（±60字），无命中返回 None。

    匹配规则（宁严勿松）：
    ① 全形日期直接命中（YYYY年M月D日 / YYYY-MM-DD / YYYY.M.D）；
    ② 句内命中——同一句（。；;\\n 切分）中先出现"YYYY年"、其后才出现"M月D日"，
       覆盖公告"10月15日8:00至10月24日18:00"式的省略年份写法。
    """
    for form in _date_forms(target):
        idx = text.find(form)
        if idx >= 0:
            return _excerpt(text, idx, len(form))
    # 句内省略年份：定位所有 "{m}月{d}日"，其前必须有 "{y}年" 且中间再无其他 "YYYY年"
    md = re.compile(rf"(?<!\d){target.month}月{target.day}日")
    year_pos = [(m.start(), int(m.group(1))) for m in re.finditer(r"(?<!\d)(\d{4})年", text)]
    for m in md.finditer(text):
        prev = [pos for pos, y in year_pos if pos < m.start()]
        if not prev:
            continue
        p = prev[-1]
        between = text[p : m.start()]
        y_full = re.search(r"\d{4}年", between)
        if not y_full or int(y_full.group(0)[:4]) != target.year:
            continue
        # 年份 token 距月日 token 过远（跨段）不算命中
        if m.start() - p > 120:
            continue
        return _excerpt(text, m.start(), m.end() - m.start())
    return None


def _excerpt(text: str, start: int, length: int) -> str:
    a = max(0, start - 60)
    b = min(len(text), start + length + 60)
    return text[a:b]


# ----------------------------------------------------------------------
# 证据通道一：真实 fetch（FR-E1）
# ----------------------------------------------------------------------


def require_evidence_fetch(
    db: Session,
    source_url: str,
    on_date: date,
    *,
    recorded_by: str = "seed_fetch",
    fetcher: Fetcher | None = None,
) -> TimelineEvidence:
    """fetch 证据通道：真实 HTTP 200 + 正文≥2KB + 正文含目标日期 → 产证据行。

    三条件缺一不可；任何一条不满足抛 EvidenceRejected（FR-E5 负例在此实现）。
    """
    _validated_gov_url(source_url)
    fetch = fetcher or _default_fetcher
    try:
        status, body = fetch(source_url)
    except Exception as e:
        raise EvidenceRejected(f"抓取失败：{source_url} ({e})") from e
    if status != 200:
        raise EvidenceRejected(f"来源页 HTTP 状态 {status}≠200：{source_url}")
    if len(body) < _MIN_BODY_BYTES:
        raise EvidenceRejected(
            f"正文仅 {len(body)}B < {_MIN_BODY_BYTES}B（疑似跳转壳/SPA 壳，无正文）：{source_url}"
        )
    text = html_to_text(body)
    excerpt = contains_date(text, on_date)
    if excerpt is None:
        raise EvidenceRejected(
            f"正文未出现目标日期 {on_date.isoformat()}——拒绝以无源日期落 OFFICIAL：{source_url}"
        )
    ev = TimelineEvidence(
        channel=EvidenceChannel.fetch,
        source_url=source_url,
        fetched_at=datetime.now(timezone.utc),
        content_sha=hashlib.sha256(body).hexdigest(),
        matched_excerpt=excerpt,
        pasted_text=None,
        recorded_by=recorded_by,
    )
    db.add(ev)
    db.flush()
    return ev


# ----------------------------------------------------------------------
# 证据通道二：manual_paste（FR-E2）
# ----------------------------------------------------------------------


def record_manual_paste(
    db: Session,
    source_url: str,
    on_date: date,
    pasted_text: str,
    *,
    recorded_by: str,
) -> TimelineEvidence:
    """manual_paste 通道：官方域 URL + 粘贴公告原文，正文含日期才放行，全文留档。"""
    _validated_gov_url(source_url)
    text = _WS_RE.sub(" ", pasted_text).strip()
    if len(text.encode("utf-8")) < _MIN_BODY_BYTES:
        raise EvidenceRejected(f"粘贴正文 <{_MIN_BODY_BYTES}B，不足以作为公告原文")
    excerpt = contains_date(text, on_date)
    if excerpt is None:
        raise EvidenceRejected(f"粘贴文本未出现目标日期 {on_date.isoformat()}——拒绝")
    ev = TimelineEvidence(
        channel=EvidenceChannel.manual_paste,
        source_url=source_url,
        fetched_at=datetime.now(timezone.utc),
        content_sha=hashlib.sha256(pasted_text.encode("utf-8")).hexdigest(),
        matched_excerpt=excerpt,
        pasted_text=pasted_text,
        recorded_by=recorded_by,
    )
    db.add(ev)
    db.flush()
    return ev


# ----------------------------------------------------------------------
# 诚实闸 + 状态机（data-model 负例闸）
# ----------------------------------------------------------------------


def validate_honesty(
    *,
    date_status: DateStatus,
    planned_date: date | None,
    planned_end_date: date | None,
    predict_basis: str | None,
    source_url: str | None,
    collected_at: datetime | None,
    evidence_id: str | None,
) -> None:
    """诚实字段组合单点校验——不合法直接抛，服务层/seed 统一经此。"""
    if date_status == DateStatus.UNKNOWN:
        if planned_date or planned_end_date or predict_basis or evidence_id:
            raise EvidenceRejected("UNKNOWN 节点日期/预测依据/证据必须全空（宪法 4）")
        return
    if date_status == DateStatus.OFFICIAL:
        if planned_date is None:
            raise EvidenceRejected("OFFICIAL 节点 planned_date 必非空")
        if not source_url or collected_at is None or evidence_id is None:
            raise EvidenceRejected(
                "OFFICIAL 节点 source_url/collected_at/evidence_id 必填（FR-E1）"
            )
        return
    if date_status == DateStatus.PREDICTED:
        if planned_date is None or not predict_basis:
            raise EvidenceRejected("PREDICTED 节点 planned_date 与 predict_basis 必填（D1）")
        if evidence_id or source_url:
            raise EvidenceRejected("PREDICTED 节点不得挂证据/来源（那是 OFFICIAL 的凭证）")
        return


ALLOWED_TRANSITIONS: dict[DateStatus, set[DateStatus]] = {
    DateStatus.UNKNOWN: {DateStatus.PREDICTED, DateStatus.OFFICIAL},
    # PREDICTED→PREDICTED = 按最新锚点重算推算值（derive 幂等重跑所需）；禁回退 UNKNOWN
    DateStatus.PREDICTED: {DateStatus.OFFICIAL, DateStatus.PREDICTED},
    DateStatus.OFFICIAL: {DateStatus.OFFICIAL},  # 仅官方更正重采
}


def _check_transition(cur: DateStatus, new: DateStatus) -> None:
    if new not in ALLOWED_TRANSITIONS[cur]:
        raise EvidenceRejected(f"非法状态转换 {cur.value}→{new.value}（禁止 OFFICIAL 回退）")


# ----------------------------------------------------------------------
# 节点日期写入唯一入口
# ----------------------------------------------------------------------


def apply_evidence_date(
    db: Session,
    node: ExamNode,
    *,
    on_date: date,
    source_url: str,
    recorded_by: str = "seed_fetch",
    end_date: date | None = None,
    pasted_text: str | None = None,
    fetcher: Fetcher | None = None,
) -> TimelineEvidence:
    """以证据把节点置 OFFICIAL。

    pasted_text 非空 → manual_paste 通道；否则 fetch 通道。日期含 end_date 时
    **每个日期各自过闸**（报名窗口起止都要在正文出现）。禁 OFFICIAL 回退。

    幂等短路：同节点同来源同日期且已有证据行 → 复用证据不再抓取
    （seed 跑两遍计数不变，quickstart §1）。
    """
    _check_transition(node.date_status, DateStatus.OFFICIAL)
    if (
        pasted_text is None
        and node.date_status == DateStatus.OFFICIAL
        and node.source_url == source_url
        and node.planned_date == on_date
        and node.planned_end_date == end_date
        and node.evidence_id is not None
    ):
        existing = db.get(TimelineEvidence, node.evidence_id)
        if existing is not None:
            return existing
    dates = [on_date] + ([end_date] if end_date else [])
    for d in dates:
        if pasted_text is not None:
            ev = record_manual_paste(db, source_url, d, pasted_text, recorded_by=recorded_by)
        else:
            ev = require_evidence_fetch(db, source_url, d, recorded_by=recorded_by, fetcher=fetcher)
        node.source_url = source_url
        node.collected_at = ev.fetched_at
        node.evidence_id = str(ev.id)
    node.planned_date = on_date
    node.planned_end_date = end_date
    node.predict_basis = None
    node.date_status = DateStatus.OFFICIAL
    validate_honesty(
        date_status=node.date_status,
        planned_date=node.planned_date,
        planned_end_date=node.planned_end_date,
        predict_basis=node.predict_basis,
        source_url=node.source_url,
        collected_at=node.collected_at,
        evidence_id=node.evidence_id,
    )
    db.flush()
    return ev


def derive_predicted_next_year(db: Session, exam: Exam, prev_exam: Exam) -> int:
    """FR-E6 锚点链：prev_exam 同 stage 存在已证 OFFICIAL 日期 → 本考次该环节 PREDICTED(+1年)。

    覆盖场景：UNKNOWN→PREDICTED、PREDICTED→PREDICTED（重算）。
    prev 无证据的环节绝不动（保持 UNKNOWN——宁可无日期不编造）。
    返回新写/更新的 PREDICTED 数。
    """
    changed = 0
    prev_nodes = {n.stage_key: n for n in prev_exam.nodes}
    for node in exam.nodes:
        if node.date_status == DateStatus.OFFICIAL:
            continue  # 已是官方值，预测靠边站
        prev = prev_nodes.get(node.stage_key)
        if (
            prev is None
            or prev.date_status != DateStatus.OFFICIAL
            or prev.evidence_id is None
            or prev.planned_date is None
        ):
            continue
        _check_transition(node.date_status, DateStatus.PREDICTED)
        node.planned_date = prev.planned_date.replace(year=prev.planned_date.year + 1)
        node.planned_end_date = (
            prev.planned_end_date.replace(year=prev.planned_end_date.year + 1)
            if prev.planned_end_date
            else None
        )
        node.predict_basis = f"按 {prev_exam.year} 同环节已证实日期平移一年（证据#{prev.evidence_id}）推算，公告后自动更新"
        node.date_status = DateStatus.PREDICTED
        changed += 1
    if changed:
        db.flush()
    return changed


# ----------------------------------------------------------------------
# 骨架 seed（幂等 upsert；永不触碰日期字段——那是证据通道的专属权力）
# ----------------------------------------------------------------------


def upsert_skeleton(db: Session, exam: Exam) -> int:
    """补齐 12 环节节点。只写骨架字段；已存在节点保留其诚实状态与日期。返回新建数。"""
    existing = {n.stage_key: n for n in exam.nodes}
    created = 0
    for spec in SKELETON_12:
        entry_url = ""
        if spec.entry_hint == "kl":
            entry_url = exam.official_home_url
        node = existing.get(spec.stage)
        if node is None:
            node = ExamNode(
                exam_id=exam.id,
                stage_key=spec.stage,
                node_seq=spec.seq,
                title=spec.title,
                date_status=DateStatus.UNKNOWN,
                official_entry_url=entry_url or None,
                materials=list(spec.materials),
                action_guide=spec.action_guide,
            )
            db.add(node)
            created += 1
        else:
            # 仅同步文案类骨架，日期诚实字段不动
            node.title = spec.title
            node.materials = list(spec.materials)
            node.action_guide = spec.action_guide
    db.flush()
    # 新建节点经 db.add 进入会话而非 relationship 集合——expire 一次，
    # 保证调用方随后访问 exam.nodes 立刻拿到全 12 环节（seed 同事务内要用）
    db.expire(exam, ["nodes"])
    return created


__all__ = [
    "SKELETON_12",
    "StageSpec",
    "EvidenceRejected",
    "require_evidence_fetch",
    "record_manual_paste",
    "validate_honesty",
    "apply_evidence_date",
    "derive_predicted_next_year",
    "upsert_skeleton",
    "contains_date",
    "html_to_text",
]
