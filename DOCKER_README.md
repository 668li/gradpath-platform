# GradPath Docker 部署指南

## 快速启动

```bash
# 1. 构建并启动所有服务
docker-compose up -d

# 2. 查看日志
docker-compose logs -f

# 3. 停止服务
docker-compose down
```

## 服务说明

| 服务 | 容器端口 | 宿主端口 | 说明 |
|------|---------|---------|------|
| db | 5432 | 不暴露 | PostgreSQL 数据库（仅 docker network 内通信） |
| redis | 6379 | 不暴露 | Redis 缓存（仅 docker network 内通信，已启用密码） |
| backend | 8000 | 127.0.0.1:8001 | FastAPI 后端（端口 8000 被 ai-goofish 占用，宿主改用 8001） |
| frontend | 3000 | 4001 | Next.js 前端 |
| n8n | 5678 | 127.0.0.1:5678 | n8n 工作流 |

> 端口映射格式：`宿主端口:容器端口`。容器之间互访用容器名 + 容器端口（如 `http://backend:8000`），宿主访问用宿主端口。

## 访问地址

- 前端: http://localhost:4001
- 后端 API: http://localhost:8001/docs (Swagger UI)
- 数据库: 不暴露到宿主；如需本地调试，临时取消 `docker-compose.yml` 中 db 服务的 `ports: - "127.0.0.1:5432:5432"` 注释

## 必需的环境变量（强密码）

`docker-compose.yml` 强制要求以下环境变量，请在启动前生成强密码并写入 `.env`：

```bash
# 生成强密码（每次输出不同，请妥善保存）
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

需要设置的环境变量：
- `POSTGRES_PASSWORD` — PostgreSQL 数据库密码
- `REDIS_PASSWORD` — Redis 认证密码

## 首次启动

1. 启动服务后，后端会自动创建数据库表
2. 访问 http://localhost:4001 注册账号
3. 开始使用 GradPath

## 运行爬虫

```bash
# 进入后端容器
docker-compose exec backend bash

# 运行暗知识爬虫
python -m app.crawlers.run --category grad --crawler dark_knowledge

# 运行所有考研爬虫
python -m app.crawlers.run --category grad
```

## 常见问题

### 数据库连接失败
确保 db 服务已启动且健康：
```bash
docker-compose ps
docker-compose logs db
```

### 后端启动失败
检查后端日志：
```bash
docker-compose logs backend
```

### 前端无法连接后端
确保后端服务已启动，且 BACKEND_URL 环境变量正确。
