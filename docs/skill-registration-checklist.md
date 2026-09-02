# Skill 注册检查清单（新 Skill 上线零摩擦）

> 供你后续指定 skill 内容时套模板上线。框架已就绪，只差"内容"与"注册"两步。
> 模板蓝本：`backend/app/skills/_skill_template.py`

一个 Skill 要真正可用，需要注册 **3 处**，缺一处都会出现"列表里有、却点不了/匹配不到"的割裂。

---

## 1. 元信息注册进注册表（决定"列表可见 + 触发词匹配"）

文件：`backend/app/skills/registry.py` → `_SKILLS` 列表，追加一个 `SkillInfo(...)`：

| 字段 | 说明 |
|------|------|
| `code` / `name` | 唯一标识，**小写下划线**，通常相同（如 `your_skill_name`） |
| `display_name` | 展示名（用户看到的标题） |
| `description` | 一句人话：帮用户解决什么问题 |
| `trigger_words` | 触发词（正则风格子串，长词权重更高；与 skill 文件 `ACTIVATE_KEYWORDS` 保持一致） |
| `category` | `builder` / `advisor` / `generator` |
| `icon` | lucide 图标名 |
| `is_active` | `True` 才在 `/api/chat/skills` 里对外可见 |

- 注册后即出现在 `GET /api/chat/skills`。
- 若希望**前端 AI 下拉**里出现，保持 `is_active=True`（默认即是）。

---

## 2. 类注册进实例注册表（决定"能被实例化 & 被匹配选中"）

文件：`backend/app/skills/registry.py` → `_load_skill_classes()`，两处都要改：

```python
# ① import 区追加
from app.skills.your_skill_name import YourSkillNameSkill

# ② 列表追加（for cls in [...] 里）
YourSkillNameSkill,
```

- `_SKILL_CLASSES[cls.code] = cls` — `code` 必须与类属性 `code` 一致。
- `find_skill_instance` 按 `s.name in _SKILL_CLASSES` 校验，所以 **`SkillInfo.name` 必须 == 类 `name`**。

---

## 3.（可选但推荐）接入情景组（Phase C1）

文件：`backend/app/skills/registry.py` → `_SCENARIOS`。

- 想让用户**模糊一句话也能命中**本 skill（如"这个学校上岸要多少分" → 你的 skill），把 `SkillInfo.code` 加进 `_SCENARIOS` 对应情景的 `"skills"` 列表。
- 不加：只有精确触发词才能命中，零历史新用户可能匹配不到。

---

## 4.（数据型 Skill 必做）接数据注入钩子（Phase C2 差异化）

文件：你的 skill 类里覆写 `inject_data(self, db, user_id, content) -> str`。

- 返回一段**真实专有数据**文本，`chat_service` 会在 `build_system_prompt` 之后自动追加 `【专有数据】` 区块。
- 通用 coach skill 不用覆写，继承基类默认返回 `""` 即可。
- **红线**：只用真实数据（进面线/条件账本/测评/专业前景），数据不足时诚实降级（返回说明"暂无专有数据"），绝不编造。

---

## 上线索自检（5 条，全绿才算完成）

```bash
# 1. 后端单测（至少跑 skills + chat）
cd backend && python -m pytest tests/test_skills.py tests/test_chat.py -q

# 2. 确认列表可见 & 可实例化
python -c "
from app.skills.registry import list_skills, get_skill_instance
assert any(s['code']=='your_skill_name' for s in list_skills()), '列表不可见'
inst = get_skill_instance('your_skill_name')
assert inst is not None, '实例不可用'
print('注册链路 OK')
"

# 3. 后端全量回归（防 import 漂移）
python -m pytest -q

# 4. 前端类型检查
cd frontend && npx tsc --noEmit

# 5. 部署
#   本仓库更新纪律：commit → bundle → scp → /home/ubuntu/update_from_bundle.sh → 生产冒烟
```

---

## 常见坑（开发时优先看这里）

- **只加了 `_SKILLS` 没加 `_SKILL_CLASSES`** → 列表有、`find_skill_instance` 永远命中不了（返回 default）。
- **`code` / `name` 不一致** → `name in _SKILL_CLASSES` 校验失败，被静默跳过。
- **`inject_data` 里查了空数据** → 道德边界：必须返回诚实提示而非硬塞一句无来源结论。
- **触发词与情景组都没设** → 只能靠 `default` skill 兜底，体验打折。
