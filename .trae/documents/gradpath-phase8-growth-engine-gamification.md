# GradPath Phase 8: AI 成长引擎 + 游戏化激励

## Summary

Phase 8 adds a **growth engine** and **gamification layer** to GradPath, transforming it from a passive data-tracking tool into an active coaching platform. Three pillars:

1. **Gamification** — XP/level system + badge registry, calculated from existing data (no stored XP field), with lazy badge awarding on profile access.
2. **AI Growth Insights** — LLM analyzes a user's career events, skills, and decisions over a selectable time period, producing structured growth analysis with score, trend, strengths, gaps, and recommendations. Cached by event count.
3. **AI Retro Assistant** — LLM generates structured retrospective draft from period events, complementing the existing rule-based draft.
4. **Interactive Skill Tree** — D3-based DAG visualization for the existing skill tree, with zoom/pan and node click-to-detail.
5. **Data Export** — PDF timeline (reportlab), JSON backup, and shareable public skill page.

Research basis: developer-roadmap (345K stars, interactive DAG), SkillTree (NSA gamification), Resume Matcher (27K stars, PDF export), AI Career Navigator (skill gap analysis).

---

## Current State Analysis

### Backend
- **18 models**: User, DestinationDecision, CareerEvent, SkillNode, Retrospective, ReferenceSnapshot, School, ReportRecord, EmploymentData, CommunityReport, InterviewReport, DataSource, Post, Company, SalaryBenchmark, MarketData
- **14 services**: ai_service, auth_service, community_service, dashboard_service, decision_advice_service, decision_service, employment_service, event_service, external_data_service, interview_service, pipeline_service, post_service, retrospective_service, skill_service
- **12 API routers**: ai, auth, community, dashboard, decisions, employment, events, interview, pipeline, posts, retrospectives, skills
- **213 tests** across 21 test files
- **AI infrastructure**: `AIService` class (httpx POST to GLM-4), `AIServiceNotConfigured` exception, `_parse_llm_json` fallback pattern, degradation strategy (503/504/500)

### Frontend
- **10 pages**: dashboard, explore, community, interview, decisions, timeline, skills, retrospectives, pipeline/ingest, pipeline/sources
- **14 components**: ai-advice, auth-guard, charts, decision-form, discussion-section, employment-charts, event-form, nav, retro-form, skill-form, stat-card + UI kit (empty, form-controls, modal, toast)
- **API client**: `request<T>()` wrapper with JWT injection, `buildQuery()`, token management

### Key Patterns (must follow)
- Models: `UUIDMixin` + `TimestampMixin` + `Base` from `app.models.base`, `JSONB` cross-dialect type
- Services: function-style (not class), `db: Session` + `user_id: UUID` as first params
- API: `APIRouter(tags=[...])`, `Depends(get_current_user)`, `Depends(get_db)`, degradation via try/except
- Tests: `conftest.py` provides `client` + `auth_headers` fixtures (SQLite in-memory, `StaticPool`)
- Frontend: `"use client"`, `useCallback`/`useEffect` data loading, `useToast` for notifications, `card` class for cards

---

## Proposed Changes

### Wave A: Core Growth Engine

#### Task 1: Gamification Models

**Files to create:**
- `backend/app/models/user_badge.py` — UserBadge model
- `backend/app/models/growth_insight.py` — GrowthInsight model  
- `backend/app/models/user_setting.py` — UserSetting model

**UserBadge schema:**
```python
class UserBadge(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_code", name="uq_user_badge_code"),)
    user_id: Mapped[UUID] = ForeignKey("users.id"), nullable=False, index=True
    badge_code: Mapped[str] = String(50), nullable=False
    awarded_at: Mapped[datetime] = DateTime(timezone=True), default=_utcnow
```

**GrowthInsight schema:**
```python
class GrowthInsight(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "growth_insights"
    user_id: Mapped[UUID] = ForeignKey("users.id"), nullable=False, index=True
    period_start: Mapped[date] = Date, nullable=False
    period_end: Mapped[date] = Date, nullable=False
    insight_data: Mapped[dict] = JSONB, nullable=False  # {growth_score, trend, strengths[], gaps[], recommendations[]}
    event_count: Mapped[int] = Integer, nullable=False  # cache key
    generated_at: Mapped[datetime] = DateTime(timezone=True), default=_utcnow
```

**UserSetting schema:**
```python
class UserSetting(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_settings"
    user_id: Mapped[UUID] = ForeignKey("users.id"), nullable=False, unique=True, index=True
    share_skills_enabled: Mapped[bool] = Boolean, default=False, nullable=False
    share_token: Mapped[str | None] = String(64), nullable=True, unique=True, index=True
```

**Files to modify:**
- `backend/app/models/__init__.py` — register 3 new models + `__all__` entries

**Why:** Isolated models with clear single responsibility. XP is NOT stored — it's calculated on-the-fly from existing data, avoiding data drift. Badges are awarded lazily (checked when profile is accessed, not on every event creation).

---

#### Task 2: Gamification Service

**File to create:** `backend/app/services/gamification_service.py`

**Core functions:**
```python
# XP calculation from existing data (real-time, no stored field)
def calculate_xp(db: Session, user_id: UUID) -> int:
    """Sum XP from: decisions (10 each), events (5 each, +10 for promotion/certification),
    skills (level * 5 each), retrospectives (15 each), community reports (20 each),
    interview reports (20 each)."""

# Level system — 7 levels with exponential thresholds
LEVEL_THRESHOLDS = [0, 50, 150, 350, 700, 1200, 2000]
LEVEL_NAMES = ["萌新", "探索者", "前行者", "进阶者", "达人", "专家", "大师"]

def get_level(xp: int) -> tuple[int, str, int, int]:
    """Returns (level_number, level_name, current_level_min_xp, next_level_min_xp)."""

# Badge registry — 15 badges in code (not DB)
BADGE_REGISTRY = [
    {"code": "first_decision", "name": "破冰决策", "description": "创建第一个去向决策", "icon": "compass", "check": lambda ctx: ctx.decisions_count >= 1},
    {"code": "first_event", "name": "成长起步", "description": "记录第一个职业事件", "icon": "sparkles", "check": lambda ctx: ctx.events_count >= 1},
    {"code": "first_skill", "name": "技能初成", "description": "添加第一个技能节点", "icon": "wrench", "check": lambda ctx: ctx.skills_count >= 1},
    {"code": "first_retro", "name": "复盘达人", "description": "完成第一次阶段复盘", "icon": "clipboard", "check": lambda ctx: ctx.retros_count >= 1},
    {"code": "first_community", "name": "社区贡献", "description": "提交第一份社区报告", "icon": "users", "check": lambda ctx: ctx.community_count >= 1},
    {"code": "first_interview", "name": "经验分享", "description": "提交第一份面试经验", "icon": "briefcase", "check": lambda ctx: ctx.interview_count >= 1},
    {"code": "decision_master", "name": "决策大师", "description": "创建 5 个以上去向决策", "icon": "compass", "check": lambda ctx: ctx.decisions_count >= 5},
    {"code": "event_master", "name": "事件达人", "description": "记录 10 个以上职业事件", "icon": "sparkles", "check": lambda ctx: ctx.events_count >= 10},
    {"code": "skill_master", "name": "技能专家", "description": "拥有 10 个以上技能节点", "icon": "wrench", "check": lambda ctx: ctx.skills_count >= 10},
    {"code": "retro_master", "name": "复盘行者", "description": "完成 5 次以上复盘", "icon": "clipboard", "check": lambda ctx: ctx.retros_count >= 5},
    {"code": "community_master", "name": "社区先锋", "description": "提交 3 份以上社区报告", "icon": "users", "check": lambda ctx: ctx.community_count >= 3},
    {"code": "interview_master", "name": "面经达人", "description": "提交 3 份以上面试经验", "icon": "briefcase", "check": lambda ctx: ctx.interview_count >= 3},
    {"code": "level_explorer", "name": "探索者", "description": "达到等级 2", "icon": "star", "check": lambda ctx: ctx.level >= 2},
    {"code": "level_expert", "name": "专家", "description": "达到等级 5", "icon": "star", "check": lambda ctx: ctx.level >= 5},
    {"code": "level_master", "name": "大师", "description": "达到等级 7", "icon": "crown", "check": lambda ctx: ctx.level >= 7},
]

@dataclass
class GamificationContext:
    decisions_count: int
    events_count: int
    skills_count: int
    retros_count: int
    community_count: int
    interview_count: int
    level: int

def build_context(db: Session, user_id: UUID) -> GamificationContext:
    """Query counts from existing tables and compute level."""

def get_profile(db: Session, user_id: UUID) -> dict:
    """Return full gamification profile: xp, level, level_name, progress_to_next,
    earned_badges (from DB), available_badges (registry - earned), newly_eligible."""

def check_and_award_badges(db: Session, user_id: UUID) -> list[dict]:
    """Check all badges, award newly-eligible ones to DB, return list of newly awarded.
    Called lazily on profile access."""

def get_or_create_settings(db: Session, user_id: UUID) -> UserSetting:
    """Get user settings, creating default if not exists."""

def update_settings(db: Session, user_id: UUID, share_skills: bool | None) -> UserSetting:
    """Update share_skills_enabled. If enabling and no share_token, generate one (secrets.token_hex(16)).
    If disabling, keep the token (can re-enable)."""
```

**Why:** Function-style matching existing services. XP calculated from existing data avoids drift. Badge registry in code (not DB) keeps it version-controlled and testable. Lazy badge awarding avoids coupling to every event creation endpoint.

---

#### Task 3: Gamification API + Tests

**File to create:** `backend/app/api/gamification.py`

**Endpoints:**
- `GET /api/gamification/profile` — returns `{xp, level, level_name, progress: {current, needed, percent}, earned_badges[], available_badges[], newly_awarded[]}`. Calls `check_and_award_badges` lazily.
- `GET /api/gamification/settings` — returns `{share_skills_enabled, share_token}`
- `PATCH /api/gamification/settings` — body `{share_skills_enabled: bool}`, returns updated settings

**File to modify:** `backend/app/main.py` — import and register `gamification_router`

**Schemas to create:** `backend/app/schemas/gamification.py` — `GamificationProfileResponse`, `UserSettingResponse`, `UserSettingUpdate`

**Tests to create:** `backend/tests/test_gamification.py` — ~15 tests:
- XP calculation with various data combinations (empty, decisions only, all types)
- Level threshold boundaries (0→L1, 50→L2, 150→L3, etc.)
- Badge awarding: first_decision, first_event, decision_master, level_explorer
- Badge idempotency (awarding same badge twice doesn't duplicate)
- Profile endpoint: 401 without auth, correct XP, correct level, newly_awarded on first access
- Settings: default creation, update share_skills, token generation, idempotent

---

#### Task 4: Growth Insight Service

**File to create:** `backend/app/services/growth_insight_service.py`

**Core functions:**
```python
def generate_growth_insight(db: Session, user_id: UUID, period_start: date, period_end: date) -> dict:
    """1. Query events, skills, decisions, retros in period.
    2. Build context string (summaries, not full text).
    3. Check cache: if GrowthInsight exists with same period + event_count, return it.
    4. Call AIService.chat() with system prompt (career coach) + context.
    5. Parse JSON: {growth_score: 0-100, trend: "rising"|"stable"|"declining",
       strengths: [str], gaps: [str], recommendations: [str], summary: str}
    6. Save to DB as GrowthInsight.
    7. Return insight_data dict.
    Raises AIServiceNotConfigured if LLM_API_KEY empty."""

def get_latest_insight(db: Session, user_id: UUID) -> dict | None:
    """Return most recent GrowthInsight.insight_data, or None."""
```

**System prompt:** "你是一位职业成长教练。根据用户提供的职业事件、技能和决策数据，分析用户的成长状况。输出严格 JSON 格式..." (detailed format spec in prompt string)

**Context builder:** Summarizes events (title + type + date), skills (name + level + category), decisions (type + status), retros (title + satisfaction). Limits to 50 most recent items to control token usage.

**Cache logic:** `event_count` field stores the count of events in period at generation time. If user requests same period and event_count hasn't changed, return cached insight. If changed, regenerate.

---

#### Task 5: Growth Insight API + Tests

**File to modify:** `backend/app/api/ai.py` — add 2 endpoints:
- `POST /api/ai/growth-insight` — body `{period_start: date, period_end: date}`, returns insight_data. Degradation: 503 (not configured), 504 (timeout), 500 (other).
- `GET /api/ai/growth-insight/latest` — returns latest cached insight or 404.

**Schemas to add:** `backend/app/schemas/ai.py` — `GrowthInsightRequest`, `GrowthInsightResponse`

**Tests to add:** `backend/tests/test_api_ai.py` — ~8 new tests:
- POST growth-insight: 401, 503 (no key), success with mock, cache hit (same period+count → no new LLM call), cache miss (different count → new call)
- GET latest: 404 (no insight), 200 (returns cached)

---

#### Task 6: AI Retro Assistant Service

**File to create:** `backend/app/services/retro_ai_service.py`

**Core function:**
```python
def generate_ai_retro_draft(db: Session, user_id: UUID, period_start: date, period_end: date) -> dict:
    """1. Query events in period (same as existing generate_draft).
    2. Build context with STAR details (situation/task/action/result) for events that have them.
    3. Call AIService.chat() with system prompt (retrospective coach).
    4. Parse JSON: {achievements: [str], challenges: str, lessons_learned: str,
       next_steps: [str], suggested_satisfaction: int, summary: str}
    5. Return dict (does NOT save to DB — user reviews and creates retro normally).
    Raises AIServiceNotConfigured if LLM_API_KEY empty."""
```

**System prompt:** "你是一位职业复盘教练。根据用户在指定时间段内的职业事件，帮助生成一份结构化复盘草稿。输出严格 JSON..."

**Key difference from existing `generate_draft`:** Existing rule-based draft only lists event titles and suggests achievements by type. AI draft reads STAR details, synthesizes challenges/lessons, and suggests satisfaction score. Both are available — user can choose.

---

#### Task 7: AI Retro API + Tests

**File to modify:** `backend/app/api/retrospectives.py` — add 1 endpoint:
- `POST /api/retrospectives/ai-draft` — body `{period_start, period_end}`, returns AI draft. Degradation: 503/504/500.

**Schemas to add:** `backend/app/schemas/retrospective.py` — `AIRetroDraftRequest`, `AIRetroDraftResponse`

**Tests to add:** `backend/tests/test_retrospectives.py` — ~5 new tests:
- POST ai-draft: 401, 503 (no key), success with mock, empty period (no events → still generates), timeout (504)

---

#### Task 8: Frontend Gamification Components

**Files to create:**
- `frontend/components/gamification/level-progress.tsx` — circular progress ring showing current level, XP, and progress to next level
- `frontend/components/gamification/badge-card.tsx` — single badge display (icon, name, description, earned/locked state)
- `frontend/components/gamification/badge-wall.tsx` — grid of BadgeCards (earned + locked)
- `frontend/components/gamification/new-badge-toast.tsx` — toast notification for newly awarded badges

**Files to modify:**
- `frontend/types/index.ts` — add `GamificationProfile`, `Badge`, `UserSetting` types
- `frontend/lib/api.ts` — add `gamificationApi` object: `{profile, getSettings, updateSettings}`

**Component interfaces:**
```tsx
// level-progress.tsx
interface LevelProgressProps {
  xp: number;
  level: number;
  levelName: string;
  progress: { current: number; needed: number; percent: number };
}

// badge-card.tsx
interface BadgeCardProps {
  badge: Badge;
  earned: boolean;
}

// badge-wall.tsx
interface BadgeWallProps {
  earnedBadges: Badge[];
  availableBadges: Badge[];
}

// new-badge-toast.tsx
interface NewBadgeToastProps {
  badges: Badge[]; // newly awarded
  onDismiss: () => void;
}
```

---

#### Task 9: Frontend Growth Insight + Retro AI Components

**Files to create:**
- `frontend/components/growth-insight.tsx` — period selector (date range), generate button, loading state, insight display (growth score gauge, trend arrow, strengths/gaps/recommendations lists, summary text). Handles 503/504 errors with user-friendly messages.
- `frontend/components/retro-ai-panel.tsx` — embedded in retrospectives page. Period selector, "AI 生成草稿" button, loading state, draft preview (achievements/challenges/lessons/next_steps/satisfaction), "使用此草稿" button that fills the retro form.

**Files to modify:**
- `frontend/lib/api.ts` — add to `aiApi`: `{growthInsight, getLatestInsight}`, add to `retrospectivesApi`: `{aiDraft}`
- `frontend/types/index.ts` — add `GrowthInsight`, `GrowthInsightRequest`, `AIRetroDraft`, `AIRetroDraftRequest` types

---

#### Task 10: Frontend Pages Integration

**Files to create:**
- `frontend/app/(app)/insights/page.tsx` — new page: LevelProgress at top, GrowthInsight component below, "最近成就" badge wall section
- `frontend/app/(app)/achievements/page.tsx` — new page: full BadgeWall, LevelProgress, export buttons (Wave B will add export functionality)

**Files to modify:**
- `frontend/components/nav.tsx` — add 2 nav items: "成长洞察" (insights, icon: TrendingUp) and "成就" (achievements, icon: Award). Insert after "阶段复盘".
- `frontend/app/(app)/retrospectives/page.tsx` — add RetroAIPanel above the retro list/modal
- `frontend/app/(app)/dashboard/page.tsx` — add compact LevelProgress + latest badges preview in dashboard overview

---

### Wave B: Enhancement Features

#### Task 11: Interactive Skill Tree (D3)

**File to create:** `frontend/components/skill-tree-graph.tsx`

**Implementation:**
- Uses `d3-hierarchy` for tree layout and `d3-zoom` for pan/zoom
- Renders SVG nodes with category-based color coding
- Clicking a node opens the existing skill edit modal
- Zoom controls (+ / - / reset buttons)
- Responsive: full width, min height 400px
- Falls back to existing list view if no skills or D3 fails to load

**File to modify:**
- `frontend/app/(app)/skills/page.tsx` — add toggle between "树形图" and "列表" views, default to tree view

**Dependencies to install:** `d3-hierarchy`, `d3-zoom`, `@types/d3-hierarchy`, `@types/d3-zoom`

---

#### Task 12: Data Export Service + API + Frontend

**File to create:** `backend/app/services/export_service.py`

**Functions:**
```python
def export_timeline_pdf(db: Session, user_id: UUID) -> bytes:
    """Generate PDF timeline using reportlab.
    Sections: Profile header, XP/Level summary, Timeline (decisions + events sorted by date),
    Skills summary, Retrospectives list.
    Returns PDF bytes."""

def export_profile_json(db: Session, user_id: UUID) -> dict:
    """Export all user data as JSON: profile, decisions, events, skills,
    retrospectives, community_reports, interview_reports, gamification profile.
    Returns dict (serialized to JSON by FastAPI)."""

def get_shareable_skills(db: Session, share_token: str) -> dict | None:
    """Public endpoint: look up UserSetting by share_token, if share_skills_enabled
    and token exists, return user name + skill tree (no other personal data).
    Returns None if not found or disabled."""
```

**File to create:** `backend/app/api/export.py`

**Endpoints:**
- `GET /api/export/timeline.pdf` — returns `Response(content=pdf_bytes, media_type="application/pdf")`, requires auth
- `GET /api/export/profile.json` — returns full profile dict, requires auth
- `GET /api/share/skills/{token}` — public endpoint, returns shareable skills or 404

**File to modify:** `backend/app/main.py` — register `export_router`

**Dependency to install:** `reportlab`

**Frontend:**
- `frontend/components/export-button.tsx` — dropdown with "导出 PDF 时间线", "导出 JSON 备份" options. Triggers download via `window.open()` or `fetch` + blob.
- `frontend/app/share/skills/[token]/page.tsx` — public page (no auth), displays user name + skill tree in read-only mode
- `frontend/types/index.ts` — add `ShareableSkills` type
- `frontend/lib/api.ts` — add `exportApi` object
- Modify `achievements/page.tsx` — add ExportButton and share settings toggle

**Tests to create:** `backend/tests/test_export.py` — ~10 tests:
- PDF export: 401, success (returns bytes, content-type correct), empty data
- JSON export: 401, success (returns dict with all sections), data completeness
- Share skills: valid token returns skills, invalid token 404, disabled share returns 404, no token returns 404

---

## Implementation Order

### Wave A (Tasks 1-10): Core Growth Engine
1. Task 1: Models → 2. Task 2: Gamification service → 3. Task 3: Gamification API + tests
4. Task 4: Growth insight service → 5. Task 5: Growth insight API + tests
6. Task 6: AI retro service → 7. Task 7: AI retro API + tests
8. Task 8: Frontend gamification components (parallel with 9)
9. Task 9: Frontend growth insight + retro AI components (parallel with 8)
10. Task 10: Frontend pages + nav integration

### Wave B (Tasks 11-12): Enhancement
11. Task 11: Interactive skill tree (D3)
12. Task 12: Data export (PDF/JSON/share)

---

## Assumptions & Decisions

1. **XP is calculated, not stored** — avoids data drift when existing data changes. Cost: O(n) query per profile access. Acceptable for a single-user-per-request system.
2. **Badge registry in code, not DB** — keeps badges version-controlled and testable. Awarded badges stored in `user_badges` table (just user_id + badge_code).
3. **Growth insight cached by event_count** — if user adds events in the same period, insight is regenerated. If no new events, cached insight is returned. Trade-off: editing an existing event (without adding new ones) won't trigger regeneration, but this is rare and acceptable.
4. **AI retro draft does NOT auto-save** — user reviews and creates retro manually. Avoids creating low-quality retrospectives from unreviewed AI output.
5. **Share token is permanent per user** — generated once, kept even when sharing is disabled. Re-enabling uses the same token. Simpler than token rotation.
6. **D3 skill tree is a toggle, not a replacement** — existing list view remains for accessibility and fallback.
7. **reportlab for PDF** — mature, pure-Python, no system dependencies. Matches Resume Matcher's approach.
8. **All AI endpoints follow existing degradation pattern** — 503 (not configured), 504 (timeout), 500 (other). Consistent with Phase 7.
9. **New nav items inserted after "阶段复盘"** — logical grouping: tracking tools first, then growth/coaching tools.
10. **Public share page at `/share/skills/[token]`** — outside `(app)` group, no auth required, no nav sidebar.

---

## Verification Steps

### Backend
1. Run `cd /workspace/backend && python -m pytest -q` — all tests pass (213 existing + ~38 new = ~251)
2. Verify `Base.metadata.create_all()` creates all new tables (automatic via `__init__.py` registration)
3. Verify API endpoints return correct status codes:
   - `GET /api/gamification/profile` → 200 with correct XP/level/badges
   - `POST /api/ai/growth-insight` → 503 without LLM_API_KEY, 200 with mock
   - `POST /api/retrospectives/ai-draft` → 503 without LLM_API_KEY, 200 with mock
   - `GET /api/export/timeline.pdf` → 200 with `application/pdf` content-type
   - `GET /api/share/skills/{token}` → 200 or 404

### Frontend
1. Run `cd /workspace/frontend && npx tsc --noEmit` — no type errors
2. Run `cd /workspace/frontend && npm run build` — build succeeds
3. E2E verification:
   - Navigate to `/insights` → see level progress + growth insight form
   - Fill growth insight form → click generate → see 503 (no LLM key) or insight data
   - Navigate to `/achievements` → see badge wall with earned/locked badges
   - Navigate to `/retrospectives` → see AI retro panel → click generate → see draft or 503
   - Navigate to `/skills` → toggle tree view → see D3 visualization
   - Click export button → download PDF/JSON

### Integration
1. Login → create decisions/events/skills → check `/insights` shows correct XP and level
2. Create enough data to trigger badge → check `/achievements` shows newly awarded badge
3. Enable share settings → visit `/share/skills/{token}` → see public skill page
