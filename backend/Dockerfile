# ---- Stage 1: deps — 只认 pyproject.toml 变化 ----
# 源码改动不再触发依赖重装：dependencies 全部有 manylinux 二进制 wheel，
# 无需 gcc/apt（也绕开了 debian 官方源在国内服务器断流的问题）。
FROM python:3.11-slim AS deps

ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

WORKDIR /build
COPY pyproject.toml .
# 造空包满足 setuptools packages.find，仅为把 dependencies 装进 /install；
# 该层被 pyproject.toml 指纹缓存，日常源码更新完全不重跑
RUN mkdir -p app && touch app/__init__.py && \
    pip install --no-cache-dir --prefix=/install .

# ---- Stage 2: builder — 源码层，只装项目本身（--no-deps，秒级）----
FROM deps AS builder

WORKDIR /build
COPY app/ app/
RUN pip install --no-cache-dir --no-deps --prefix=/install .

# ---- Stage 3: production — 运行时 ----
FROM python:3.11-slim AS production

RUN groupadd -r gradpath && useradd --no-log-init -r -g gradpath gradpath

WORKDIR /app

# 依赖 + 项目包一次性并入系统目录（/install/lib→site-packages, /install/bin→bin）
COPY --from=builder /install/ /usr/local/

COPY pipeline/ pipeline/
COPY migrations/ migrations/
COPY scripts/ scripts/
COPY alembic.ini .

RUN chown -R gradpath:gradpath /app

USER gradpath

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["python", "-c", "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
