# AI对话增强实施计划

> **For agentic workers:** 使用 compose:subagent 或 compose:execute 逐步实施此计划。

**Goal:** 增强GradPath的AI对话系统，支持多轮对话、上下文感知、新增Skill

**Architecture:** 在现有Skill框架基础上，扩展对话状态管理、改进Skill匹配、新增2个Skill

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Pydantic

---

### Task 1: 新增SalaryNegotiationSkill

**Covers:** [S3]

**Files:**
- Create: `backend/app/skills/salary_negotiation.py`
- Modify: `backend/app/skills/registry.py`
- Test: `tests/test_skills.py`

- [ ] **Step 1: 创建Skill文件**

```python
# backend/app/skills/salary_negotiation.py
"""薪资谈判助手 Skill — 帮助用户准备薪资谈判策略。"""
from __future__ import annotations
import json
import re
from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = ["薪资谈判", "谈薪", "工资谈判", "薪资", "salary", "negotiation"]

class SalaryNegotiationSkill(BaseSkill):
    code = "salary_negotiation"
    name = "薪资谈判助手"
    description = "帮助用户准备薪资谈判策略，分析市场行情，制定谈判方案"
    icon = "dollar-sign"
    
    def should_activate(self, message: str, context: dict) -> bool:
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in ACTIVATE_KEYWORDS)
    
    def build_system_prompt(self, user_context: str, knowledge: list[dict]) -> str:
        return f"""你是GradPath薪资谈判顾问，帮助用户制定薪资谈判策略。

你的任务：
1. 分析用户背景和目标岗位
2. 提供市场薪资参考
3. 制定谈判策略和话术
4. 回答薪资相关问题

{user_context}"""
    
    def build_user_prompt(self, message: str) -> str:
        return f"【用户问题】\n{message}"
    
    def parse_response(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
            return {"content": data.get("content", raw)}
        except json.JSONDecodeError:
            return {"content": raw}
```

- [ ] **Step 2: 在注册表中注册**

在 `backend/app/skills/registry.py` 的 `_SKILLS` 列表中添加：

```python
SkillInfo(
    code="salary_negotiation",
    name="salary_negotiation",
    display_name="薪资谈判助手",
    description="帮助用户准备薪资谈判策略，分析市场行情，制定谈判方案",
    trigger_words=["薪资谈判", "谈薪", "工资谈判", "薪资", "salary", "negotiation"],
    use_cases=["用户需要薪资谈判建议", "分析市场薪资行情"],
    capabilities=["分析市场薪资", "制定谈判策略", "提供谈判话术"],
    limitations=["不用于具体劳动合同审核"],
    category="advisor",
    icon="dollar-sign",
),
```

在 `_SKILL_CLASSES` 映射中添加：

```python
from app.skills.salary_negotiation import SalaryNegotiationSkill
_SKILL_CLASSES["salary_negotiation"] = SalaryNegotiationSkill
```

- [ ] **Step 3: 编写测试**

```python
# tests/test_skills.py 添加
def test_salary_negotiation_skill():
    from app.skills.salary_negotiation import SalaryNegotiationSkill
    skill = SalaryNegotiationSkill()
    assert skill.code == "salary_negotiation"
    assert skill.should_activate("我想谈谈薪资", {})
    assert not skill.should_activate("今天天气不错", {})

def test_find_salary_negotiation():
    from app.skills import registry
    skill = registry.find_skill_instance("我想谈谈薪资", {})
    assert skill is not None
    assert skill.code == "salary_negotiation"
```

- [ ] **Step 4: 运行测试**

Run: `docker exec gradpath-backend-1 python -m pytest tests/test_skills.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/skills/salary_negotiation.py backend/app/skills/registry.py tests/test_skills.py
git commit -m "feat: add SalaryNegotiationSkill"
```

---

### Task 2: 新增IndustryAnalyzerSkill

**Covers:** [S3]

**Files:**
- Create: `backend/app/skills/industry_analyzer.py`
- Modify: `backend/app/skills/registry.py`
- Test: `tests/test_skills.py`

- [ ] **Step 1: 创建Skill文件**

```python
# backend/app/skills/industry_analyzer.py
"""行业分析器 Skill — 分析目标行业的趋势和机会。"""
from __future__ import annotations
import json
import re
from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = ["行业分析", "行业趋势", "行业前景", "industry", "行业分析器"]

class IndustryAnalyzerSkill(BaseSkill):
    code = "industry_analyzer"
    name = "行业分析器"
    description = "分析目标行业的趋势和机会，帮助用户做出职业决策"
    icon = "bar-chart"
    
    def should_activate(self, message: str, context: dict) -> bool:
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in ACTIVATE_KEYWORDS)
    
    def build_system_prompt(self, user_context: str, knowledge: list[dict]) -> str:
        return f"""你是GradPath行业分析师，帮助用户分析目标行业的趋势和机会。

你的任务：
1. 分析目标行业的发展趋势
2. 评估行业机会和风险
3. 提供行业进入建议
4. 回答行业相关问题

{user_context}"""
    
    def build_user_prompt(self, message: str) -> str:
        return f"【用户问题】\n{message}"
    
    def parse_response(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
            return {"content": data.get("content", raw)}
        except json.JSONDecodeError:
            return {"content": raw}
```

- [ ] **Step 2: 在注册表中注册**

在 `backend/app/skills/registry.py` 的 `_SKILLS` 列表中添加：

```python
SkillInfo(
    code="industry_analyzer",
    name="industry_analyzer",
    display_name="行业分析器",
    description="分析目标行业的趋势和机会，帮助用户做出职业决策",
    trigger_words=["行业分析", "行业趋势", "行业前景", "industry", "行业分析器"],
    use_cases=["用户需要行业分析", "评估行业机会"],
    capabilities=["分析行业趋势", "评估行业机会", "提供行业建议"],
    limitations=["不用于具体公司分析"],
    category="advisor",
    icon="bar-chart",
),
```

在 `_SKILL_CLASSES` 映射中添加：

```python
from app.skills.industry_analyzer import IndustryAnalyzerSkill
_SKILL_CLASSES["industry_analyzer"] = IndustryAnalyzerSkill
```

- [ ] **Step 3: 编写测试**

```python
def test_industry_analyzer_skill():
    from app.skills.industry_analyzer import IndustryAnalyzerSkill
    skill = IndustryAnalyzerSkill()
    assert skill.code == "industry_analyzer"
    assert skill.should_activate("我想分析互联网行业", {})
    assert not skill.should_activate("今天天气不错", {})

def test_find_industry_analyzer():
    from app.skills import registry
    skill = registry.find_skill_instance("我想分析互联网行业", {})
    assert skill is not None
    assert skill.code == "industry_analyzer"
```

- [ ] **Step 4: 运行测试**

Run: `docker exec gradpath-backend-1 python -m pytest tests/test_skills.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/skills/industry_analyzer.py backend/app/skills/registry.py tests/test_skills.py
git commit -m "feat: add IndustryAnalyzerSkill"
```

---

### Task 3: 增强InterviewSimulationSkill多轮对话

**Covers:** [S2]

**Files:**
- Modify: `backend/app/skills/interview_simulation.py`
- Test: `tests/test_chat.py`

- [ ] **Step 1: 增强Skill的多轮对话能力**

修改 `backend/app/skills/interview_simulation.py`，在 `parse_response` 方法中支持多轮状态：

```python
def parse_response(self, raw: str) -> dict:
    try:
        data = json.loads(raw)
        return {
            "content": data.get("content", raw),
            "questions": data.get("questions", []),
            "feedback": data.get("feedback", ""),
            "score": data.get("score", 0),
            "round": data.get("round", 1),
        }
    except json.JSONDecodeError:
        return {"content": raw}
```

- [ ] **Step 2: 编写多轮对话测试**

```python
def test_interview_simulation_multi_round():
    from app.skills.interview_simulation import InterviewSimulationSkill
    skill = InterviewSimulationSkill()
    
    # 第一轮
    result1 = skill.parse_response('{"content": "面试开始", "questions": ["请自我介绍"], "round": 1}')
    assert result1["round"] == 1
    assert len(result1["questions"]) == 1
    
    # 第二轮
    result2 = skill.parse_response('{"content": "好的", "questions": ["为什么选择这个专业"], "round": 2}')
    assert result2["round"] == 2
```

- [ ] **Step 3: 运行测试**

Run: `docker exec gradpath-backend-1 python -m pytest tests/test_chat.py -v -k interview`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add backend/app/skills/interview_simulation.py tests/test_chat.py
git commit -m "feat: enhance InterviewSimulationSkill with multi-round support"
```

---

### Task 4: 改进Skill匹配的上下文感知

**Covers:** [S2]

**Files:**
- Modify: `backend/app/skills/registry.py`
- Test: `tests/test_skills.py`

- [ ] **Step 1: 改进find_skill_instance支持上下文感知**

修改 `backend/app/skills/registry.py` 的 `find_skill_instance` 函数：

```python
def find_skill_instance(content: str, context: dict | None = None) -> BaseSkill | None:
    """根据消息内容和对话上下文匹配最适合的 BaseSkill 实例。"""
    _load_skill_classes()
    
    if not content:
        return _SKILL_CLASSES.get("default", lambda: None)()
    
    content_lower = content.lower()
    best_match = None
    best_score = 0
    
    for s in _SKILLS:
        if s.code == "default":
            continue
        score = 0
        for trigger in s.trigger_words:
            if trigger in content_lower:
                score += len(trigger)
        
        # 上下文加成：如果对话历史中出现过相关关键词，加分
        if context and "history" in context:
            for msg in context["history"]:
                if isinstance(msg, dict):
                    msg_content = msg.get("content", "").lower()
                    for trigger in s.trigger_words:
                        if trigger in msg_content:
                            score += len(trigger) * 0.5  # 上下文加成50%
        
        if score > best_score and s.name in _SKILL_CLASSES:
            best_score = score
            best_match = _SKILL_CLASSES[s.name]()
    
    return best_match if best_match else _SKILL_CLASSES.get("default", lambda: None)()
```

- [ ] **Step 2: 编写上下文感知测试**

```python
def test_find_skill_with_context():
    from app.skills import registry
    
    # 第一轮：用户问考研问题
    skill1 = registry.find_skill_instance("我想考研", {})
    assert skill1.code == "grad_school_planning"
    
    # 第二轮：用户继续问相关问题，应该继续匹配grad_school_planning
    context = {"history": [{"role": "user", "content": "我想考研"}]}
    skill2 = registry.find_skill_instance("选哪个学校", context)
    assert skill2.code == "grad_school_planning"
```

- [ ] **Step 3: 运行测试**

Run: `docker exec gradpath-backend-1 python -m pytest tests/test_skills.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add backend/app/skills/registry.py tests/test_skills.py
git commit -m "feat: improve skill matching with context awareness"
```

---

### Task 5: 集成测试验证

**Covers:** [S4, S5, S6]

**Files:**
- Test: `tests/test_chat.py`

- [ ] **Step 1: 运行所有聊天相关测试**

Run: `docker exec gradpath-backend-1 python -m pytest tests/test_chat.py -v`
Expected: All tests PASS

- [ ] **Step 2: 运行所有Skill相关测试**

Run: `docker exec gradpath-backend-1 python -m pytest tests/test_skills.py -v`
Expected: All tests PASS

- [ ] **Step 3: 运行完整测试套件**

Run: `docker exec gradpath-backend-1 python -m pytest tests/ -v`
Expected: All 423+ tests PASS

- [ ] **Step 4: 提交最终版本**

```bash
git add -A
git commit -m "feat: complete AI dialog enhancement with new skills and context awareness"
```
