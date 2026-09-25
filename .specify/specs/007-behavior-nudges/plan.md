# Implementation Plan 007：行为设计微机制（T1–T3 轻量）

> 方法论：planning-and-task-breakdown（轻量档——规格本身即小，任务收敛为 3 个）。
> 实施窗口=A 类 commit 后；与 005/006 零文件冲突；C3 触发点可后置到 006 之后。

## 1. Overview

新增前端微机制层：庆祝反馈组件+文案生成器（M1）、福格式触发文案规则与落点对齐（M2）。纯前端，零后端改动、零新页面、零新依赖。

## 2. 依赖图

```
T1 文案生成器+组件（新文件，无依赖）
      │
T2 四触发点接入（C1 exam-timeline / C2 condition-checklist / C4 micro-action；C3 后置 006）
      │
T3 M2 文案规则对齐（005 hint / 006 下回动作 / 微行动卡）+ 样例集测试
```

## 3. Task List

- [ ] **T1 庆祝组件与文案生成器**（S：2-3 文件）
  - Description：`frontend/lib/celebration.ts`（`pickCelebration(event, seed)`：按事件分组≥4 条、去重、禁用词表）+ `frontend/components/celebration.tsx`（轻量确认条：自动消失 <2s、可关闭、不阻塞、375px 可读）。
  - Acceptance：① 分组/去重/禁用词单测绿；② 组件无新依赖、无网络请求；③ 失败路径不调用（负例覆盖）。
  - Verify：`cd frontend && npx tsc --noEmit && npx vitest run`；手工 375px。
  - Files：`frontend/lib/celebration.ts`（新）、`frontend/components/celebration.tsx`（新）、`frontend/lib/__tests__/celebration.test.ts`（新）。
  - Deps：None。

- [ ] **T2 触发点接入**（S：2-4 文件）
  - Description：C1 节点"已完成"回传成功回调（`exam-timeline.tsx` 的 `sendFeedback(done)`）；C2 条件账本补充成功（执行期核实 UI 文件）；C4 微行动完成（`micro-action-card.tsx`）。C3（006 原则入库）标记为后置项，待 006 T5 落地后补。
  - Acceptance：① 三处操作成功即见反馈、<2s 消失；② 操作失败无反馈（负例）；③ 不破坏既有交互（点击/提交行为不变）。
  - Verify：本地手测三处 + `npx tsc --noEmit` + vitest 不红。
  - Files：`frontend/components/civil-service/exam-timeline.tsx`（**仅回调处 1-2 行调用，不重构**）、`frontend/components/dashboard/micro-action-card.tsx`、条件账本 UI（执行期定）。
  - Deps：T1。

- [ ] **T3 M2 文案规则落地 + 样例集**（S：1-3 文件）
  - Description：核对并改写 005 缺口条目 `hint` 语义（"当 X 时做 Y"）、微行动卡文案；与 006 原则卡"下回动作"一致性核对；建样例集测试（正则：锚点+动作动词）。
  - Acceptance：① 样例集全绿；② 与 006 quickstart 样例复用一致；③ 不新增文案位置（只改既有）。
  - Verify：vitest 全绿；文案人工过目（方向席位）。
  - Files：005/006 实施产物对应文件（本任务在其后执行）、测试文件。
  - Deps：T2（可与 005/006 实施任务合并执行）。

### Checkpoint
- [ ] 前端三绿 + 375px + 三触发点手测 + 文案样例全绿；C3 挂后置清单（006 后补）。
- [ ] 部署冒烟绑特有断言（操作后反馈出现且类型正确）；方向席位验收。

## 4. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| 反馈打扰操作（模态/阻塞） | 中 | 形态=轻量确认条+自动消失；验收含"不阻塞"断言 |
| 文案空洞或虚假 | 中 | 禁用词表+分组文案纪律（说意义不说空话）；失败路径无反馈 |
| 与 006 交付时序耦合（C3） | 低 | C3 明确后置，不阻塞 T1/T2 上线 |
| 改动 exam-timeline.tsx 与 A4/005 冲突 | 低 | 仅回调处 1-2 行；实施窗口与 005 同批协调，先对账后动手 |

## 5. Open Questions
- C2（条件账本）触发点 UI 文件在 005/006 实施后核实登记。
- 是否需要在 006 复盘页给"原则入库"庆祝更高权重（同组件不同文案即可，无需新形态）。
