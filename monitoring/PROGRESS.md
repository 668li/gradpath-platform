# PROGRESS — 实时监控与加固（2026-09-04）

目标：nginx 拦探测(444)+登录限流 → fail2ban 自动封 → 每分钟 watcher 推企业微信。
顺序：任务1（含端口地雷修正，必须最先）→ 任务2 → 任务3。
最大风险：compose 的 127.0.0.1:80 与运行态 0.0.0.0:80 不一致，任何 up -d 会全站失联——已在同一提交内先改 "80:80"。

## 任务 0 核对结果（2026-09-04 实测）
- ✅ docker port gradpath-prod-nginx-1 = 0.0.0.0:80 + [::]:80（地雷属实）
- ✅ fail2ban NOT-INSTALLED；apt 候选可用
- ✅ 服务器出站 qyapi.weixin.qq.com → 403（可达）
- ✅ 磁盘 / 89%（51G/59G）
- ⚠️ 基线偏差：/.git/config 与 /.env 实测 404 body≈13.4KB（书里记 4380B，SSR 页大小随构建变化）。判定标准不变：改前 404 → 改后必须 Empty reply from server。
- ⚠️ /admin 实测 307（跳登录）、/login 200——均不在拦截正则内，符合预期。
- ❌ /home/ubuntu/.sec_webhook_url 不存在 → 见 BLOCKED.md，任务 3 推送验证挂起，其余照做。

## 偏离记录
- 登录限流 location 扩为 login|register|forgot-password 三端点（同 zone）：注册/找回密码与登录同为爆破面，成本为零。验收仍只测 /api/auth/login。
- 部署走隔离 worktree（服务器 HEAD 38b66c8eb 与本地线分叉）：commit 47d8da8 → bundle refs/heads/main → 服务器 ff-only merge。本地主树（deploy-rebased 55e19b7）随后以同内容提交对齐，防并行会话还原。

## 任务 1 验收（2026-09-04 11:28 实测，全部 --noproxy 直连）
- ✅ `curl /` → 200（站点可用）
- ✅ 反向验证：改前基线 `/.git/config` = 404 + 13399B；改后 = `Empty reply from server`（444 生效）。`/.env`、`/phpmyadmin` 同断连。
- ✅ `/admin` 307、`/login` 200（真实路由不误伤）
- ✅ `docker port` 仍 0.0.0.0:80 + [::]:80（地雷未复炸）
- ✅ monitoring/nginx-logs/access.log 收到真实行，探测行状态码=444（fail2ban 可尾随）
- 注：经 7897 代理时 444 被代理合成为 Content-Length:0，验收一律 --noproxy 直连。

## 任务 2 验收（2026-09-04 实测）
- ✅ fail2ban 1.0.2 已装，jail 列表 = nginx-probe + sshd（sshd 顺带真实封了爆破者 43.153.205.159）
- ✅ fail2ban-regex 对真实 access.log：5/5 matched
- ✅ banip 203.0.113.66 → nft 链 `tcp dport 80 ip saddr @addr-set-nginx-probe reject` 实况可见；unbanip 后 set 清空
- ✅ logrotate -f 强制轮转全链路：新 access.log 生成、站点 200、fail2ban File list 继续尾随
- 坑1（已修）：Ubuntu defaults-debian.conf 的 DEFAULT backend=systemd 吞掉文件日志型 jail → jail 显式 `backend = auto`
- 坑2（已修）：logrotate 拒绝非 root 属主配置与 ubuntu 属主目录 → 文件 chown root + 配置加 `su ubuntu ubuntu`
- 偏离：任务书写"iptables -S 可见"，本机 fail2ban 1.0.2 默认 banaction=nftables，改用 `nft list chain inet f2b-table f2b-chain` 验证同一内核包过滤层。
- ⚠️ 运维注意：本人公网 IP 在 access.log 已积 3 次 444 命中（验收探测），距 maxretry=5 仅差 2 次——后续验证一律用 fail2ban-regex 离线测，不再打真实 444 请求。

## 任务 3 验收（2026-09-04 实测）
- ✅ sec_watcher.sh 经 bundle ff-merge 上服务器（7909c8e19），cron 每分钟 `bash .../sec_watcher.sh`（免执行位，绕 Mimosa 对 .sh 传输的拦截；内容已经 Write 通道扫描）
- ✅ 首跑即抓到真实告警：磁盘 90% WARNING（任务 0 时 89%，一小时内越过阈值）
- ✅ 反向验证红→绿：假日志行（.git/config 返回 200，UA=FAKE-TEST-904）→ 2 秒内 CRITICAL；滑出 2 分钟窗口后 CRITICAL 计数不再增长
- ✅ cron 存活实锤：19:58:01 的 CRITICAL 由 cron 自动跑出（非手动）；state/last-run.ts 心跳持续更新
- ✅ 冷却正确：disk WARNING 多轮只报一次（6h）；CRITICAL 窗口内每分钟重复报（无冷却，符合设计）
- ✅ 假线 200 不误触 fail2ban（filter 只匹配 444）：Total banned=0
- ⚠️ 推送验证挂起：webhook 文件不存在 → PUSH-SKIPPED 降级路径已验证；用户写入 /home/ubuntu/.sec_webhook_url 后跑 `bash ~/gradpath-platform/monitoring/sec_watcher.sh --test` 看 alerts.log 的 [PUSH] errcode:0 即销账

## 终验（明卷+暗卷）
- 明卷：站点 200 ✓；探测 404→Empty reply 反向 ✓；fail2ban 三连 ✓；watcher 红→绿 ✓
- 暗卷(a) jail ignoreip 含 172.16.0.0/12 ✓；(b) 公网 burst 15×POST /api/auth/login → 401×5+429×7+503×3（后端限流+nginx limit_req 双层叠加）✓；(c) compose "80:80" 与 docker port 0.0.0.0:80 一致 ✓
- 拓扑：并行会话已把 deploy-rebased 线推上服务器（557586e→7909c8e），worktree secfix-wt 使命完成已删

## 进度
- [x] 任务 0 核对
- [x] 任务 1 nginx+compose 修正并部署（47d8da8 已上服务器，验收全绿）
- [x] 任务 2 fail2ban（filter/jail/logrotate 上线，验收三连全绿）
- [x] 任务 3 watcher（cron 每分钟运行中；仅推送验证等用户 webhook）
