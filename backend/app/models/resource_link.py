"""资源导航链接模型 — 资源导航聚合中心的目录条目（2026-10-03 RN-1）。

一条 = 一个实测可达的外部资源：链接 + 一句话定位 + 实测记录。
零搬运纪律：只存链接与定位，禁存目标站内容原文。

收录纪律（任务书 2026-10-03 约束）：
- 点名制：AI/调研候选一律 status=pending，用户终审是唯一转正闸，
  禁止任何"自动转正/批量转正"逻辑；
- 版权三档：original（原创）✅ / caution（真题整理灰区）⚠️ /
  forbidden（网盘合集·机构课程搬运·书籍扫描）❌ 仅枚举留位，禁入库；
- 每条链接须带实测记录（sources JSONB：HTTP 状态/核验时间/性质判定）。

藏货层灵魂 = 个人匠人站/开源仓库/AI 原生知识站；通用层大站默认不收。
"""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin

# track（身份线）
RESOURCE_TRACK_KAOYAN = "kaoyan"
RESOURCE_TRACK_EMPLOYMENT = "employment"
RESOURCE_TRACK_COMMON = "common"

# 分类（前端 tabs 口径：干货/官方入口/就业求职/开源精选/工具）
RESOURCE_CATEGORY_KAOYAN = "kaoyan_resources"  # 考研干货（藏货层主推）
RESOURCE_CATEGORY_OFFICIAL = "official"  # 官方入口（只挂外链）
RESOURCE_CATEGORY_EMPLOYMENT = "employment"  # 就业求职
RESOURCE_CATEGORY_OPEN_SOURCE = "open_source"  # 开源精选
RESOURCE_CATEGORY_TOOL = "tool"  # 工具

# 版权三档（forbidden 仅枚举留位，seed/API 双闸禁入库）
RESOURCE_COPYRIGHT_ORIGINAL = "original"
RESOURCE_COPYRIGHT_CAUTION = "caution"
RESOURCE_COPYRIGHT_FORBIDDEN = "forbidden"

# 状态机：pending（候选，带"待站长终审"徽章）→ active（用户终审转正）
# → retired（资源老化下架）/ killed（终审否决）。永不自动 pending→active。
RESOURCE_STATUS_PENDING = "pending"
RESOURCE_STATUS_ACTIVE = "active"
RESOURCE_STATUS_RETIRED = "retired"
RESOURCE_STATUS_KILLED = "killed"

# 来源：user（用户点名）/ ai_research（AI 定向调研，过审后仍需终审）
RESOURCE_ADDED_VIA_USER = "user"
RESOURCE_ADDED_VIA_AI = "ai_research"


class ResourceLink(UUIDMixin, TimestampMixin, Base):
    """资源导航条目 — 全站公共目录（无 user_id），镜像 intel_cards 形态。"""

    __tablename__ = "resource_links"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    track: Mapped[str] = mapped_column(String(20), nullable=False, default=RESOURCE_TRACK_KAOYAN, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # 一句话定位（必填）：这站是干什么的 / 为什么收录它
    note: Mapped[str] = mapped_column(String(300), nullable=False)
    risk_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    copyright_tier: Mapped[str] = mapped_column(String(20), nullable=False, default=RESOURCE_COPYRIGHT_ORIGINAL)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RESOURCE_STATUS_PENDING, index=True)
    added_via: Mapped[str] = mapped_column(String(20), nullable=False, default=RESOURCE_ADDED_VIA_AI)
    # 用户终审唯一转正闸：AI 候选永不自动置 true
    user_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # [{http_status, checked_at, title, verdict, note}] — 实测记录，禁存目标站原文
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 近期上新标记（前端"最近收录"角标用，转正时由 seed 维护）
    recently_added: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
