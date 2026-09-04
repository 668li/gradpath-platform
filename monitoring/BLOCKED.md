# BLOCKED — 待裁决清单（2026-09-04）

1. **企业微信 webhook 未提供**：/home/ubuntu/.sec_webhook_url 不存在。需领导在企业微信群添加机器人后执行：
   `echo '<webhook地址>' | ssh gradpath "tee /home/ubuntu/.sec_webhook_url >/dev/null && chmod 600 /home/ubuntu/.sec_webhook_url"`
   影响：任务 3 的 --test 与假日志 CRITICAL 推送验证无法完成；watcher 脚本与 cron 照常部署，地址写入后无需改动即生效。
2. 顺手活（未碰）：磁盘 89% 的 docker prune 决策；/admin 307 与基线 body 大小偏差已记 PROGRESS.md 非阻塞。
