# ---- Stage 1: deps ----
FROM node:20-alpine AS deps

# 国内服务器构建时可传国内 npm 镜像：--build-arg NPM_REGISTRY=https://registry.npmmirror.com
ARG NPM_REGISTRY=https://registry.npmjs.org

WORKDIR /app

COPY package.json package-lock.json ./
# npm 缓存挂载：lockfile 变更时重装依赖不必重新下载全部包
RUN --mount=type=cache,target=/root/.npm \
    npm config set registry "${NPM_REGISTRY}" && npm ci

# ---- Stage 2: build ----
FROM node:20-alpine AS build

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .
# webpack 持久缓存挂载：.next/cache 跨构建复用，二次构建大幅提速（BuildKit cache mount）
ENV NEXT_TELEMETRY_DISABLED=1
RUN --mount=type=cache,target=/app/.next/cache npm run build

# ---- Stage 3: production ----
FROM node:20-alpine AS production

WORKDIR /app

ENV NODE_ENV=production

COPY --from=build /app/.next/standalone ./
COPY --from=build /app/public ./public
COPY --from=build /app/.next/static ./.next/static

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["node", "-e", "require('http').get('http://localhost:3000', r => { process.exit(r.statusCode === 200 ? 0 : 1) })"]

CMD ["node", "server.js"]
