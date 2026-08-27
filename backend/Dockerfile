# ---- Stage 1: builder (install build deps, build full wheel) ----
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.* \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY app/ app/

RUN pip install --no-cache-dir "build==1.2.2.post1" && \
    python -m build --wheel --outdir /wheels

# ---- Stage 2: production (runtime only, no dev deps) ----
FROM python:3.11-slim AS production

RUN groupadd -r gradpath && useradd --no-log-init -r -g gradpath gradpath

WORKDIR /app

# 完整 wheel（含 app 全量源码 + pyproject 全部依赖），保证依赖不遗漏。
# 历史坑：曾用 `pip install .` 于无源码目录装依赖，配合 packages.find 显式声明后
# 会报 0 matches，故统一从 Stage 1 的完整 wheel 安装。
COPY --from=builder /wheels/*.whl /wheels/
RUN pip install --no-cache-dir /wheels/*.whl && \
    rm -rf /wheels

COPY pipeline/ pipeline/
COPY migrations/ migrations/
COPY alembic.ini .

RUN chown -R gradpath:gradpath /app

USER gradpath

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["python", "-c", "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
