# ---- Stage 1: deps ----
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# ---- Stage 2: build ----
FROM node:20-alpine AS build

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---- Stage 3: production ----
FROM node:20-alpine AS production

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

WORKDIR /app

ENV NODE_ENV=production

RUN mkdir -p /app/.next/standalone && \
    mkdir -p /app/.next/static && \
    chown -R nextjs:nodejs /app

COPY --from=build /app/.next/standalone ./
COPY --from=build /app/public ./public
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["node", "-e", "require('http').get('http://localhost:3000', r => { process.exit(r.statusCode === 200 ? 0 : 1) })"]

CMD ["node", "server.js"]
