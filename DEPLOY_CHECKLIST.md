# GradPath 上线部署手册（DEPLOY_CHECKLIST）

> 目标环境：一台国内云服务器（Ubuntu 22.04/24.04，2C4G 起）+ Docker。
> 全流程分五段，按序执行；⭐=需要你人工操作/花钱的部分。

---

## 0️⃣ 前置准备 ⭐

| 事项 | 说明 |
|---|---|
| 购买服务器 | 腾讯云/阿里云轻量 2核4G，Ubuntu 22.04+；安全组放行 80/443/22 |
| 注册域名并实名 | 任意注册商；完成后立即提交 **ICP 备案**（2-3 周，与部署并行推进）|
| SSH 密钥 | 本地生成密钥对，公钥入服务器 `~/.ssh/authorized_keys` |

服务器装 Docker（官方脚本即可）：

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # 重新登录生效
```

## 1️⃣ 首次部署

```bash
# 服务器上拉代码
git clone https://github.com/668li/gradpath-platform.git && cd gradpath-platform

# 生成生产配置（逐项填写，密码用模板里的命令现场生成）
cp .env.prod.example .env
vim .env   # 至少填：POSTGRES_PASSWORD / REDIS_PASSWORD / SECRET_KEY /
           #        CORS_ORIGINS(先填 http://服务器IP) / FLOWER_PASSWORD
```

方式 A —— CI 出镜像（推荐，`deploy.yml` 手动触发已构建推送到 GHCR）：

```bash
# GitHub Actions 页面手动跑 Deploy 工作流后：
docker compose -f docker-compose.prod.yml pull
# 私有镜像仓库需先登录：echo <PAT> | docker login ghcr.io -u 668li --password-stdin
```

方式 B —— 服务器本地构建：

```bash
docker compose -f docker-compose.prod.yml build
```

启动并自检：

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps          # 全部 healthy
curl -s localhost/api/health ; curl -s localhost/ready # 经 nginx 转发应为 ok
```

建首个管理员：

```bash
docker compose -f docker-compose.prod.yml exec backend \
    python scripts/bootstrap_local_admin.py    # 输出初始邮箱/密码，首次登录后改掉
```

此时浏览器访问 `http://<服务器IP>` 即可灰度使用（备案期间过渡态）。

## 2️⃣ 数据迁移日（把本机 SQLite 数据搬上线）

> 迁移工具 `backend/scripts/migrate_sqlite_to_pg.py` 已在本地完成 92 表
> 58,860 行全量演练（行数零差异）。以下命令在**服务器项目根目录**执行。

```bash
# 1) 上传权威库（本机执行；D:\职业规划\职业规划\backend\gradpath.db）
scp backend/gradpath.db user@server:/tmp/gradpath.db

# 2) 服务器上执行迁移（默认指向 compose 内 db，需要临时暴露或走一次性容器）
#    简化路径：临时在宿主机映射一个迁移专用 PG 亦可，正式库建议直接：
MIGRATE_SRC=/tmp/gradpath.db \
MIGRATE_TGT="postgresql://gradpath:<POSTGRES_PASSWORD>@localhost:5432/gradpath" \
    py -3.13 backend/scripts/migrate_sqlite_to_pg.py --drop-existing --stamp-head

# 3) 序列对齐 + varchar 加宽（脚本配套修复，容器内直连）
docker cp backend/scripts/pg_post_migrate_fixes.sql gradpath-prod-db-1:/tmp/f.sql
docker exec gradpath-prod-db-1 psql -U gradpath -d gradpath -f //tmp/f.sql

# 4) 冒烟（宿主机对 127.0.0.1:8001）
curl -s localhost/api/health                       # ok
curl -s "localhost/api/gwy-positions?page=1&page_size=2" | head -c 300   # 真实数据
```

预期输出含 `RESULT: OK — 全部表迁移且行数一致` 与 NOTICE `[A] SERIAL 序列已全部对齐`。

## 3️⃣ 域名与 HTTPS（备案通过后）

```nginx
# nginx/nginx.conf 的 server 段补 443 + 证书后：
#   docker compose -f docker-compose.prod.yml restart nginx
# 证书建议宿主机 certbot --nginx 或面板申请，再挂载进容器
```

同时更新 `.env`：`CORS_ORIGINS=https://你的域名` 并重启 backend。
`deploy.yml` 取消 on.push 注释恢复自动部署，并在 GitHub Secrets 配置
`DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_SSH_KEY`。

## 4️⃣ 日常运维速查

| 操作 | 命令 |
|---|---|
| 服务日志 | `docker compose -f docker-compose.prod.yml logs -f backend` |
| 任务队列监控 | 浏览器开 SSH 隧道后访问 `http://127.0.0.1:5555/flower` |
| 定时采集管理 | 管理员后台 `/schedules`（rsshub_research 默认每日 02:30）|
| 备份 | 自动：每日 02:00 DB、02:30 Redis、周日校验；卷 `gradpath-prod_backup_data` |
| 备份手工验证 | `docker exec gradpath-prod-backup-1 tail -20 /var/log/backup_verify.log` |
| 回滚 | `docker compose ... down && git checkout <上个tag> && up -d --build` |

## 5️⃣ 已知边界（如实记录）

- 知乎/贴吧等站对数据中心 IP 有 WAF，线上只保留 RSSHub(自建)/公开 API 类数据源，
  重爬虫不上生产——符合「停止泛爬、做决策引擎」的方向。
- 数据中心 IP 对研招网等源的连通性以线上实测为准；RSSHub 路由 503 属上游抖动常态，
  当日数据缺失不影响已有库存。
- LLM_API_KEY 不填则 AgentChat 关闭，其余功能不受影响。
