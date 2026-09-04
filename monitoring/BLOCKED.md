# BLOCKED — 待裁决清单（2026-09-04）

1. **Server酱 SendKey 未提供**（09-04 用户拍板：企业微信走不通，改用 Server酱微信推送）：/home/ubuntu/.sec_webhook_url 不存在。需领导手机微信扫 https://sct.ftqq.com 登录后复制 SendKey（SCT 开头）发给 agent，由 agent 写入服务器并跑 --test 验证。脚本已改为 Server酱格式并含每日 5 条配额封顶。
   影响：推送验证挂起；watcher 照常落盘告警，地址写入后无需改动即生效。
2. 顺手活（未碰）：磁盘 89% 的 docker prune 决策；/admin 307 与基线 body 大小偏差已记 PROGRESS.md 非阻塞。
