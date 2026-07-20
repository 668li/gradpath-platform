# ADR-001: Tech Stack Selection

## Status
Accepted

## Date
2026-07-11

## Context
GradPath is a career planning platform for Chinese graduate school candidates. The system needs to handle:
- User authentication and profile management
- Real-time WebSocket notifications
- Crawler-based data collection from multiple sources
- AI-powered career recommendations
- Dashboard visualizations and analytics
- Admin tools for crawler management

## Decision
We adopt a three-tier stack:

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Backend** | FastAPI (Python 3.11+) | Async support, automatic OpenAPI docs, Pydantic validation, mature ecosystem |
| **Frontend** | Next.js 14 (React 18, TypeScript) | SSR/SSG, App Router, type safety, React Server Components |
| **Database** | PostgreSQL 16 | ACID compliance, JSON support for flexible schemas, full-text search, production-ready |

### Supporting Technologies
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic for schema versioning
- **Cache**: Redis (optional, for rate limiting and session storage)
- **Task Queue**: FastAPI BackgroundTasks + APScheduler for crawler scheduling
- **AI/LLM**: ZhiPu GLM-4 via OpenAI-compatible API
- **Deployment**: Docker + docker-compose

## Consequences

### Positive
- FastAPI auto-generates OpenAPI 3.1 docs at `/docs` and `/redoc`
- Next.js provides excellent DX with hot reload and TypeScript
- PostgreSQL handles concurrent crawls and complex queries efficiently
- SQLAlchemy 2.0 supports both sync and async patterns

### Negative
- PostgreSQL requires more setup than SQLite for development
- Three separate services increase deployment complexity
- Python GIL limits CPU-bound processing (mitigated by async I/O for crawlers)

### Risks
- GLM-4 API dependency for AI features (mitigated by configurable base URL)
- WebSocket scalability requires Redis pub/sub in multi-instance deployments
