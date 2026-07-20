"""MCP 工具注册 — 将 GradPath 核心工具暴露给 AI 代理。

修复: 此模块从 main.py 下沉而来，遵循分层架构：
- main.py 只做 FastAPI app 装配和 MCP server 挂载
- services/mcp_service.py 负责具体工具实现

工具实现保持原样搬迁，未做行为变更。
"""


def register_mcp_tools(mcp):
    """注册所有 GradPath MCP 工具到给定的 FastMCP 实例。

    Args:
        mcp: FastMCP 实例（已创建，由 main.py 传入）
    """
    @mcp.tool()
    async def search_knowledge(query: str) -> str:
        """搜索 GradPath 知识库（经验帖/QA/知识文章/暗知识）"""
        from app.api.ai_agent import _db_search
        results = _db_search(query, limit=5)
        if not results:
            return f"未找到与「{query}」相关的内容"
        lines = []
        for r in results:
            lines.append(f"[{r['type']}] {r['title']}: {r['content'][:150]}")
        return "\n".join(lines)

    @mcp.tool()
    async def search_web(query: str) -> str:
        """搜索互联网获取最新信息"""
        from app.services.web_search import WebSearchService
        ws = WebSearchService()
        results = await ws.search(query, max_results=5)
        if not results:
            return f"未找到关于「{query}」的网络结果"
        lines = []
        for r in results:
            lines.append(f"{r.title}\n  {r.url}\n  {r.snippet[:100]}")
        return "\n".join(lines)

    @mcp.tool()
    async def get_user_profile(user_id: str) -> str:
        """获取用户职业画像（技能/规划/决策/测评）"""
        from uuid import UUID
        from app.database import SessionLocal
        from app.services.chat_service import build_user_context
        db = SessionLocal()
        try:
            return build_user_context(db, UUID(user_id))
        finally:
            db.close()

    @mcp.tool()
    async def get_school_intel(school_name: str) -> str:
        """查询考研院校情报"""
        from app.database import SessionLocal
        from app.models.grad_intel import GradSchoolIntel
        db = SessionLocal()
        try:
            schools = db.query(GradSchoolIntel).filter(
                GradSchoolIntel.school_name.contains(school_name)
            ).limit(3).all()
            if not schools:
                return f"未找到「{school_name}」的情报"
            lines = []
            for s in schools:
                lines.append(f"{s.school_name} ({s.province}) — {s.major_name}: 分数线{s.min_scoreline or 'N/A'}")
            return "\n".join(lines)
        finally:
            db.close()

    @mcp.tool()
    async def get_salary_benchmark(industry: str, city: str = "") -> str:
        """查询就业薪资基准数据"""
        from app.database import SessionLocal
        from app.models.market_data import MarketData
        db = SessionLocal()
        try:
            q = db.query(MarketData).filter(MarketData.industry.contains(industry))
            if city:
                q = q.filter(MarketData.city.contains(city))
            items = q.limit(5).all()
            if not items:
                return f"未找到{industry}行业的薪资数据"
            lines = []
            for i in items:
                lines.append(f"{i.company or i.industry} — {i.position or ''}: ¥{i.salary_min or 0}-{i.salary_max or 0}")
            return "\n".join(lines)
        finally:
            db.close()

    @mcp.tool()
    async def get_civil_service_intel(region: str = "") -> str:
        """查询考公岗位情报"""
        from app.database import SessionLocal
        from app.models.civil_service_intel import CivilServicePostIntel
        db = SessionLocal()
        try:
            q = db.query(CivilServicePostIntel)
            if region:
                q = q.filter(CivilServicePostIntel.region.contains(region))
            items = q.limit(5).all()
            if not items:
                return f"未找到{region or ''}的考公岗位情报"
            lines = []
            for i in items:
                lines.append(f"{i.department} — {i.position}: 招{i.recruit_count or '?'}人")
            return "\n".join(lines)
        finally:
            db.close()
