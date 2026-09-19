# Plan 009：考研线收敛

- **Created**: 2026-09-19｜**执行**: 执行会话（本会话=规格/验收席位，git 写不碰）

## 纪律前置（按项目铁律）

1. **开工闸**：`git -C . status` 确认在飞批（考研删除 + 008 ponytail）已全部 commit；跑 topology.sh 对账三线；`git log --oneline` 找到在飞批 commit SHA 并 `git show --stat` 逐笔核内容——**009 增量绝不与在飞批混 commit**。
2. 数字复测：spec §0 的行数/残留是 2026-09-19 快照，动手前照"快照必须现场复测"纪律重测。
3. 部署闸：gp-preflight 四闸 → bundle → scp → update_from_bundle.sh → converge → `git show --stat` → HTTPS 冒烟绑本次特有断言（/kaoyan/vault 带源角标 + 旧路由 404）。

## 任务切分（每项独立 commit，逐项收敛）

| # | 内容 | 触碰面 | commit 语义 |
|---|---|---|---|
| T1 | SelfPositioning drop 迁移 + service 残留清尾 + **kaoyan_news 存量清空（双份备份→事务清零，管道代码休眠）** + 负例测试（旧端点 404）+ 全仓 grep 对账 | backend models/schemas/service/tests + 一条迁移 + 生产 DB 清理 | `feat(009-t1): self_positionings drop 迁移、定位链清尾与资讯存量清空（备份先行）` |
| T2 | kaoyan 主页归口（时间线/社区 + 目录区块 + 橱窗入口，**资讯 tab 隐藏**） | `kaoyan/page.tsx`（含 001 时间线路由核实） | `feat(009-t2): 考研信息站主页归口` |
| T3 | 信任锚橱窗 /kaoyan/vault（带源角标 + 未命中外链纪律） | 新页 + 现存只读 API 消费 | `feat(009-t3): 信任锚橱窗` |
| T4 | 外链目录常量（空清单）+ 考研区块 + civil-service label 更名"外部工具" | `lib/toolLinks.ts` 新增 + 两页 | `feat(009-t4): 外链目录两线复用（点名制零预填）` |
| T5 | ~~收录点名制~~ **转挂账（拍板⑨）**：资讯供给重建——爬取目标用户未定，不施工；仅保留 T1 管道休眠 + T2 入口隐藏 | — | 挂账项，随未来另案立项 |

## 关键实现约束

- T1 备份纪律：kaoyan_news 2803 行清空前**双份备份**（容器 /tmp + 宿主机 ~/，容器重建会丢 /tmp），备份核过行数再在事务中清空（先例：三假表归零备份）。
- T3 数据面只读：消费现存 grad-intel 列表端点，**不为橱窗新建写路径**；yanzhao/intel 路由名以实测 openapi 为准（"冒烟断言先读真实 response_model"先例）。
- T4 目录零后端：静态常量起步，未来站点多了再议入库（防过度设计）；ugc/archive 必附风险注记。
- T5 红线域判定用完整域名匹配（防整域误放先例：gaokao.chsi.com.cn 豁免 ≠ *.chsi.com.cn 放行）。
- 文案纪律：不说"一站式/智能推荐/基于真实院校数据"（已证伪话术全禁）；橱窗空态引导文案用候车室口径。

## 验收对账

按 spec §3 逐条实测并记入交付报告；验收证据包五件套（构建/测试/负例/grep/生产冒烟）随最后一个 commit 附带。
