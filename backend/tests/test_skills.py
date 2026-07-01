def test_create_skill(auth_headers, client):
    resp = client.post(
        "/api/skills",
        headers=auth_headers,
        json={
            "name": "Python",
            "category": "后端",
            "level": 4,
            "acquired_date": "2024-09-01",
            "notes": "主力语言",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Python"
    assert resp.json()["level"] == 4


def test_skill_tree_with_parent(auth_headers, client):
    parent = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "后端开发", "category": "后端", "level": 4},
    )
    pid = parent.json()["id"]
    child = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "FastAPI", "category": "后端", "level": 3, "parent_id": pid},
    )
    assert child.status_code == 201
    assert child.json()["parent_id"] == pid


def test_get_skill_tree(auth_headers, client):
    root = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "前端", "category": "前端", "level": 3},
    )
    rid = root.json()["id"]
    client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "React", "category": "前端", "level": 4, "parent_id": rid},
    )
    client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "Vue", "category": "前端", "level": 3, "parent_id": rid},
    )
    resp = client.get("/api/skills", headers=auth_headers)
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 1  # 只有一个根节点
    assert len(tree[0]["children"]) == 2


def test_skill_stats(auth_headers, client):
    for cat in ["后端", "后端", "前端", "软技能"]:
        client.post(
            "/api/skills",
            headers=auth_headers,
            json={"name": f"技能-{cat}", "category": cat, "level": 3},
        )
    resp = client.get("/api/skills/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["后端"] == 2
    assert data["前端"] == 1
    assert data["软技能"] == 1


def test_delete_skill(auth_headers, client):
    create = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "待删", "category": "其他", "level": 1},
    )
    sid = create.json()["id"]
    resp = client.delete(f"/api/skills/{sid}", headers=auth_headers)
    assert resp.status_code == 204


# ======================================================================
# Phase 12: Skill 插件测试（GradSchoolPlanning / CareerTransition）
# ======================================================================

import json

from app.skills.career_transition import CareerTransitionSkill
from app.skills.grad_school_planning import GradSchoolPlanningSkill
from app.skills import registry


# ----- GradSchoolPlanningSkill.should_activate -----

class TestGradSchoolPlanningActivate:
    def setup_method(self):
        self.skill = GradSchoolPlanningSkill()

    def test_activate_kao_yan(self):
        assert self.skill.should_activate("我想考研", {}) is True

    def test_activate_bao_yan(self):
        assert self.skill.should_activate("如何保研", {}) is True

    def test_activate_yan_jiu_sheng(self):
        assert self.skill.should_activate("研究生方向选择", {}) is True

    def test_activate_du_yan(self):
        assert self.skill.should_activate("我想读研", {}) is True

    def test_activate_shuo_shi(self):
        assert self.skill.should_activate("硕士项目推荐", {}) is True

    def test_not_activate_other(self):
        assert self.skill.should_activate("我想找工作", {}) is False

    def test_not_activate_plain(self):
        assert self.skill.should_activate("你好", {}) is False

    def test_metadata(self):
        assert self.skill.code == "grad_school_planning"
        assert self.skill.name == "考研规划"
        assert self.skill.icon == "🎓"


# ----- CareerTransitionSkill.should_activate -----

class TestCareerTransitionActivate:
    def setup_method(self):
        self.skill = CareerTransitionSkill()

    def test_activate_zhuan_hang(self):
        assert self.skill.should_activate("我想转行做产品经理", {}) is True

    def test_activate_zhuan_xing(self):
        assert self.skill.should_activate("职业转型建议", {}) is True

    def test_activate_kua_hang(self):
        assert self.skill.should_activate("跨行业发展", {}) is True

    def test_activate_huan_sai_dao(self):
        assert self.skill.should_activate("想换赛道", {}) is True

    def test_activate_kua_gang_wei(self):
        assert self.skill.should_activate("跨岗位调动", {}) is True

    def test_not_activate_other(self):
        assert self.skill.should_activate("我想跳槽涨薪", {}) is False

    def test_not_activate_plain(self):
        assert self.skill.should_activate("今天天气不错", {}) is False

    def test_metadata(self):
        assert self.skill.code == "career_transition"
        assert self.skill.name == "职业转型"
        assert self.skill.icon == "🔄"


# ----- parse_response -----

class TestGradSchoolPlanningParse:
    def setup_method(self):
        self.skill = GradSchoolPlanningSkill()

    def test_parse_valid_json(self):
        payload = {
            "content": "考研规划总览",
            "target_schools": ["清华大学", "北京大学"],
            "target_major": "计算机科学与技术",
            "exam_subjects": ["政治", "英语一", "数学一", "408"],
            "timeline": "基础3个月，强化2个月，冲刺1个月",
            "prep_strategy": "分阶段复习，注重真题",
        }
        result = self.skill.parse_response(json.dumps(payload, ensure_ascii=False))
        assert result["content"] == "考研规划总览"
        assert result["target_schools"] == ["清华大学", "北京大学"]
        assert result["target_major"] == "计算机科学与技术"
        assert result["exam_subjects"] == ["政治", "英语一", "数学一", "408"]
        assert result["timeline"] == "基础3个月，强化2个月，冲刺1个月"
        assert result["prep_strategy"] == "分阶段复习，注重真题"
        assert result["career_plan"] is None

    def test_parse_invalid_json(self):
        raw = "这不是一个JSON格式的回复"
        result = self.skill.parse_response(raw)
        assert result["content"] == raw
        assert result["target_schools"] == []
        assert result["target_major"] == ""
        assert result["exam_subjects"] == []
        assert result["timeline"] == ""
        assert result["prep_strategy"] == ""
        assert result["career_plan"] is None

    def test_parse_markdown_code_block(self):
        payload = {"content": "代码块回复", "target_schools": ["浙大"]}
        raw = f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
        result = self.skill.parse_response(raw)
        assert result["content"] == "代码块回复"
        assert result["target_schools"] == ["浙大"]


class TestCareerTransitionParse:
    def setup_method(self):
        self.skill = CareerTransitionSkill()

    def test_parse_valid_json(self):
        payload = {
            "content": "转型可行性分析",
            "current_field": "传统制造业生产管理",
            "target_field": "互联网产品经理",
            "transferable_skills": ["项目管理", "跨部门沟通"],
            "gaps": ["用户研究方法", "数据分析能力"],
            "transition_steps": ["补充产品知识", "积累产品案例", "寻找过渡岗位"],
        }
        result = self.skill.parse_response(json.dumps(payload, ensure_ascii=False))
        assert result["content"] == "转型可行性分析"
        assert result["current_field"] == "传统制造业生产管理"
        assert result["target_field"] == "互联网产品经理"
        assert result["transferable_skills"] == ["项目管理", "跨部门沟通"]
        assert result["gaps"] == ["用户研究方法", "数据分析能力"]
        assert result["transition_steps"] == [
            "补充产品知识",
            "积累产品案例",
            "寻找过渡岗位",
        ]
        assert result["career_plan"] is None

    def test_parse_invalid_json(self):
        raw = "无法解析的纯文本内容"
        result = self.skill.parse_response(raw)
        assert result["content"] == raw
        assert result["current_field"] == ""
        assert result["target_field"] == ""
        assert result["transferable_skills"] == []
        assert result["gaps"] == []
        assert result["transition_steps"] == []
        assert result["career_plan"] is None


# ----- registry -----

class TestRegistryMatching:
    def test_find_skill_grad_school(self):
        skill = registry.find_skill("我想考研读研究生", {})
        assert skill.code == "grad_school_planning"

    def test_find_skill_career_transition(self):
        skill = registry.find_skill("我想转行到互联网行业", {})
        assert skill.code == "career_transition"

    def test_find_skill_default_fallback(self):
        skill = registry.find_skill("你好呀", {})
        assert skill.code == "default"


class TestRegistryList:
    def test_list_skills_includes_new(self):
        skills = registry.list_skills()
        codes = [s["code"] for s in skills]
        assert "grad_school_planning" in codes
        assert "career_transition" in codes
        # default 始终最后
        assert codes[-1] == "default"

    def test_list_skills_count(self):
        skills = registry.list_skills()
        assert len(skills) == 6

    def test_list_skills_new_metadata(self):
        skills = {s["code"]: s for s in registry.list_skills()}
        grad = skills["grad_school_planning"]
        assert grad["name"] == "考研规划"
        assert grad["icon"] == "🎓"
        assert "考研" in grad["description"]

        trans = skills["career_transition"]
        assert trans["name"] == "职业转型"
        assert trans["icon"] == "🔄"
        assert "转型" in trans["description"]
