# GradPath 上线部署手册（DEPLOY_CHECKLIST）

> **现状（2026-08-29）：已上线** http://82.156.236.152（IP 灰度态，备案中）。
> 本手册 = 日常更新 + 备案后收尾 + 故障速查。全新重建服务器的步骤见文末附录。

---

## 1️⃣ 日常更新（最常用）

```bash
# 本地：改代码 → 测试 → 推送
git push

# 服务器（我方执行；一条命令完成 pull+重建+重启+迁移）：
ssh gradpath
sh ~/gradpath-platform/scripts/update_server_from_bundle.sh            # 全量
sh ~/gradpath-platform/scripts/update_server_from_bundle.sh backend    # 只重建后端
sh ~/gradpath-platform/scripts/update_server_from_bundle.sh frontend   # 只重建前端
```

- 代码打在镜像里（无挂载卷），任何代码变更都需要重建对应镜像
- 依赖没变时：backend ≈1 分钟；frontend 首次后靠 webpack 持久缓存 ≈1-2 分钟
- 用户可感知中断仅重启一二十秒，建议挑清晨
- **改了 `pyproject.toml` / `package.json` 会全量重装依赖**（首次 10 分钟级），非必要别动

## 2️⃣ 备案通过后收尾（域名+HTTPS）

1. 腾讯云控制台解析域名 A 记录 → 82.156.236.152
2. 服务器装证书（宿主机 certbot 或面板申请，nginx.conf 加 443 server 块 + 挂载证书）
3. 改 `~/gradpath-platform/.env`：`CORS_ORIGINS=https://你的域名` → 重启 backend
4. **弃用灰度覆盖**：以后更新命令去掉 `-f docker-compose.grey.yml`（改用纯 prod compose，nginx 回到 127.0.0.1:80，由宿主 nginx/caddy 承接 443）——或保留容器 nginx 直面公网并加 443 端口映射
5. GitHub Actions：配置 `DEPLOY_HOST`/`DEPLOY_USER`/`DEPLOY_SSH_KEY` secrets，恢复 deploy.yml 的 push 自动触发（现在是手动跑）

## 3️⃣ 运维速查

| 操作 | 命令 |
|---|---|
| 服务状态 | `cd ~/gradpath-platform && docker compose -f docker-compose.prod.yml -f docker-compose.grey.yml ps` |
| 后端日志 | `docker logs -f gradpath-prod-backend-1` |
| 数据库备份验证 | `docker exec gradpath-prod-backup-1 tail -5 /var/log/backup_verify.log`（每日 02:00 自动备份） |
| 管理员重置 | 容器内跑 `python /app/scripts/bootstrap_local_admin.py`（镜像已含 scripts/） |
| 容器名冲突残骸 | `docker ps -a \| grep -E "^[0-9a-f]{12}_"` → `docker rm -f <名>` |
| 磁盘体检 | `df -h / && docker system df`（构建缓存>12GB 再考虑 `docker builder prune --keep-storage 8GB -f`） |

## 4️⃣ 服务器网络特性（踩坑备忘）

- github.com:443 被墙；SSH 通道 ssh.github.com:443 已配只读 Deploy Key，服务器 `git pull` 直连可用
- 构建镜像必须带国内源参数（脚本已内置）：PyPI=aliyun / npm=npmmirror
- Dockerfile 已砍 gcc（依赖全是二进制 wheel），debian 源问题免疫
- nginx 用 Docker 内置 DNS 动态解析（valid=10s）：后端/前端重建换 IP 自动跟随，无需重启 nginx
- LLM_API_KEY 未配置 → AgentChat 线上关闭；要开就改 .env 加 key 后重启 backend

## 附录：全新服务器重建（灾难恢复）

1. 腾讯云重装系统 Ubuntu 24.04 → `ssh-copy-id` 装公钥 → 装 docker（阿里云 apt 源）+ /etc/docker/daemon.json 配腾讯内网 mirror + 2G swap
2. 生成 SSH deploy key，加到 GitHub 仓库 Deploy keys（只读）
3. `git clone git@github.com:668li/gradpath-platform.git`（走 ssh.github.com:443，~/.ssh/config 指过去）
4. `cp .env.prod.example .env` 逐项填写强密钥
5. `sh scripts/update_server_from_bundle.sh SKIP_PULL=1`（SKIP_PULL=1 环境变量跳过 pull）——首次构建约 15 分钟（国内源已内置）
6. 数据恢复：最近的 pg_backup 卷 或 从本地跑 `backend/scripts/migrate_sqlite_to_pg.py` + `pg_post_migrate_fixes.sql`（见脚本头注释）
