# ADR-003: Deployment Strategy

## Status
Accepted

## Date
2026-07-11

## Context
GradPath needs reliable deployment supporting:
- Development environment with hot reload
- Production environment with health checks
- Scheduled crawler jobs
- Database migrations on deploy
- Static asset serving

## Decision
We deploy via Docker Compose with the following architecture:

### Services
```yaml
services:
  postgres:       # PostgreSQL 16 database
  redis:          # Redis 7 (optional, for caching)
  backend:        # FastAPI application
  frontend:       # Next.js application
  nginx:          # Reverse proxy + static serving
```

### Container Configuration
- **backend**: Python 3.11-slim, runs uvicorn with 4 workers
- **frontend**: Node 20 Alpine, Next.js standalone output
- **postgres**: Alpine with persistent volume
- **nginx**: Alpine with custom config for routing

### Deployment Flow
1. Build images: `docker compose build`
2. Run migrations: `docker compose exec backend alembic upgrade head`
3. Start services: `docker compose up -d`
4. Health check: `curl http://localhost/health`

### Environment Management
- `.env` file for local development
- Environment variables for production (SECRET_KEY, DATABASE_URL, etc.)
- `ENVIRONMENT` variable controls development vs production mode

### Health Checks
- `/health`: Liveness probe (database connectivity, disk space)
- `/ready`: Readiness probe (all dependencies available)
- Container healthchecks configured for all services

### Scheduler (APScheduler)
- Integrated into backend process
- Runs crawlers on cron schedule
- Persists job state to database
- Admin API for schedule management

## Consequences

### Positive
- Single `docker compose up` for full stack
- Nginx handles SSL termination and static caching
- Health probes enable Kubernetes migration
- Volume mounts for development hot reload

### Negative
- Docker Compose not suitable for high-availability (single-node only)
- No built-in load balancing (mitigated by nginx upstream)
- Log aggregation requires external tooling

### Risks
- Database volume backup strategy needed (not automated)
- Secret management in production requires external vault
