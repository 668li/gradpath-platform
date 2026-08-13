# ---- Stage 1: builder (install build deps, build) ----
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.* \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY app/__init__.py app/__init__.py

RUN pip install --no-cache-dir build && \
    python -m build --wheel --outdir /wheels

# ---- Stage 2: production (runtime only, no dev deps) ----
FROM python:3.11-slim AS production

RUN groupadd -r gradpath && useradd --no-log-init -r -g gradpath gradpath

WORKDIR /app

COPY --from=builder /wheels/*.whl /wheels/

# 修复: 旧版 wheel 安装遗漏 tenacity/redis/prometheus_client 等运行时依赖,
# 导致路由自动发现全部被跳过,前端所有"加载X失败"均源于此。
# 直接从 pyproject.toml 安装全部依赖,确保不遗漏。
COPY pyproject.toml .
RUN pip install --no-cache-dir . && \
    rm -rf /wheels

COPY app/ app/
COPY pipeline/ pipeline/
COPY migrations/ migrations/
COPY alembic.ini .

RUN chown -R gradpath:gradpath /app

USER gradpath

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["python", "-c", "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]