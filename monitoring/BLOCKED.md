# BLOCKED — 待裁决清单（2026-09-04）

1. ~~Server酱 SendKey 未提供~~ **已销账（09-04 21:17）**：用户拍板弃企业微信改 Server酱，SendKey 已写入 /home/ubuntu/.sec_webhook_url（600 权限，未入库），--test 实测返回 `{"code":0,"error":"SUCCESS"}`，推送链路打通。脚本已含每日 5 条配额封顶。
2. ~~磁盘 prune 决策~~ **已销账（09-04 21:3x）**：用户授权清理。实测磁盘已自行从 90% 回落到 49%（并行会话/其他清理释放约 23G）；`docker builder prune` 仅安全回收 680MB（剩余 15GB 缓存为 ACTIVE，删需 `--all` 致下次构建跑满 45min，不值当）；1.5GB 未用镜像留作回滚保险。站点 200、容器全 healthy，磁盘告警解除。
