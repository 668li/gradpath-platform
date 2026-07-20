# tests/test_skills.py
"""Skill 单元测试 — 验证各 skill 的注册、激活与实例化。"""
from __future__ import annotations

import sys
import os

# 确保 backend/app 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def test_salary_negotiation_skill():
    """验证 SalaryNegotiationSkill 元信息与激活逻辑。"""
    from app.skills.salary_negotiation import SalaryNegotiationSkill

    skill = SalaryNegotiationSkill()

    assert skill.code == "salary_negotiation"
    assert skill.name == "salary_negotiation"
    assert skill.icon == "dollar-sign"

    # 触发词激活
    assert skill.should_activate("我想谈谈薪资", {})
    assert skill.should_activate("帮我做个 salary negotiation", {})
    assert skill.should_activate("准备工资谈判策略", {})
    assert not skill.should_activate("帮我写个爬虫", {})

    # system prompt 包含关键词
    sys_prompt = skill.build_system_prompt("用户背景：3年经验", [])
    assert "薪资谈判" in sys_prompt
    assert "GradPath" in sys_prompt

    # user prompt
    user_prompt = skill.build_user_prompt("帮我谈薪")
    assert "薪资谈判咨询" in user_prompt

    # parse_response 兜底
    result = skill.parse_response("原始文本")
    assert result["content"] == "原始文本"
    assert result["salary_negotiation"] is None


def test_find_salary_negotiation():
    """验证 registry.find_skill_instance 能找到 SalaryNegotiationSkill。"""
    from app.skills.registry import find_skill_instance, get_skill

    # 元信息存在
    info = get_skill("salary_negotiation")
    assert info is not None
    assert info["display_name"] == "薪资谈判助手"

    # 实例化匹配
    instance = find_skill_instance("我想谈谈薪资", {})
    assert instance is not None
    assert instance.code == "salary_negotiation"

    # 非触发词返回 default
    default_inst = find_skill_instance("帮我写个爬虫", {})
    assert default_inst is not None
    assert default_inst.code == "default"


# ======================================================================
# IndustryAnalyzerSkill tests
# ======================================================================

import json

from app.skills.industry_analyzer import IndustryAnalyzerSkill
from app.skills.company_review import CompanyReviewSkill
from app.skills.user_referral import UserReferralSkill
from app.skills import registry


class TestIndustryAnalyzerActivate:
    def setup_method(self):
        self.skill = IndustryAnalyzerSkill()

    def test_activate_hang_ye_fen_xi(self):
        assert self.skill.should_activate("我想做行业分析", {}) is True

    def test_activate_hang_ye_qushi(self):
        assert self.skill.should_activate("行业趋势如何", {}) is True

    def test_activate_hang_ye_qianjing(self):
        assert self.skill.should_activate("这个行业前景怎么样", {}) is True

    def test_activate_industry(self):
        assert self.skill.should_activate("industry outlook", {}) is True

    def test_activate_hang_ye_fen_xi_qi(self):
        assert self.skill.should_activate("打开行业分析器", {}) is True

    def test_not_activate_other(self):
        assert self.skill.should_activate("我想找工作", {}) is False

    def test_not_activate_plain(self):
        assert self.skill.should_activate("你好", {}) is False

    def test_metadata(self):
        assert self.skill.code == "industry_analyzer"
        assert self.skill.name == "industry_analyzer"
        assert self.skill.icon == "bar-chart"


class TestIndustryAnalyzerParse:
    def setup_method(self):
        self.skill = IndustryAnalyzerSkill()

    def test_parse_valid_json(self):
        payload = {
            "content": "行业分析总览",
            "industry_analysis": {
                "industry_name": "人工智能",
                "market_size": "2024年中国市场规模达5000亿元",
                "growth_trend": "快速增长",
                "key_drivers": ["政策支持", "技术突破"],
                "opportunities": ["AI+医疗", "AI+教育"],
                "challenges": ["人才短缺", "数据安全"],
                "salary_range": "30-80万/年",
                "entry_barrier": "高",
                "recommendation": "建议从基础算法岗入手",
            },
        }
        result = self.skill.parse_response(json.dumps(payload, ensure_ascii=False))
        assert result["content"] == "行业分析总览"
        assert result["industry_analysis"]["industry_name"] == "人工智能"
        assert result["industry_analysis"]["growth_trend"] == "快速增长"
        assert result["career_plan"] is None

    def test_parse_invalid_json(self):
        raw = "这不是一个JSON格式的回复"
        result = self.skill.parse_response(raw)
        assert result["content"] == raw
        assert result["industry_analysis"] is None
        assert result["career_plan"] is None

    def test_parse_markdown_code_block(self):
        payload = {"content": "代码块回复", "industry_analysis": {"industry_name": "互联网"}}
        raw = f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
        result = self.skill.parse_response(raw)
        assert result["content"] == "代码块回复"
        assert result["industry_analysis"]["industry_name"] == "互联网"


class TestRegistryIndustryAnalyzer:
    def test_find_industry_analyzer(self):
        skill = registry.find_skill_instance("帮我做行业分析", {})
        assert skill is not None
        assert skill.code == "industry_analyzer"

    def test_find_industry_trend(self):
        skill = registry.find_skill_instance("行业趋势怎么样", {})
        assert skill is not None
        assert skill.code == "industry_analyzer"

    def test_list_skills_includes_industry_analyzer(self):
        skills = registry.list_skills()
        codes = [s["code"] for s in skills]
        assert "industry_analyzer" in codes


# ======================================================================
# InterviewCoachSkill tests
# ======================================================================


def test_interview_coach_skill():
    """验证 InterviewCoachSkill 元信息与激活逻辑。"""
    from app.skills.interview_coach import InterviewCoachSkill

    skill = InterviewCoachSkill()

    assert skill.code == "interview_coach"
    assert skill.name == "interview_coach"
    assert skill.icon == "message-circle"

    # 触发词激活
    assert skill.should_activate("帮我提升面试技巧", {})
    assert skill.should_activate("面试准备怎么做", {})
    assert skill.should_activate("面试心态调整", {})
    assert skill.should_activate("面试指导建议", {})
    assert skill.should_activate("interview coach help", {})
    assert not skill.should_activate("帮我写个爬虫", {})

    # system prompt 包含关键词
    sys_prompt = skill.build_system_prompt("用户背景：求职者", [])
    assert "面试教练" in sys_prompt
    assert "GradPath" in sys_prompt

    # user prompt
    user_prompt = skill.build_user_prompt("帮我准备面试")
    assert "面试教练咨询" in user_prompt

    # parse_response 兜底
    result = skill.parse_response("原始文本")
    assert result["content"] == "原始文本"
    assert result["interview_coach"] is None


def test_interview_coach_parse_json():
    """验证 InterviewCoachSkill 的 JSON 解析能力。"""
    from app.skills.interview_coach import InterviewCoachSkill

    skill = InterviewCoachSkill()

    # 有效 JSON 输入
    json_input = json.dumps({
        "content": "面试技巧",
        "interview_coach": {
            "tips": [{"category": "表达", "tip": "条理清晰", "why": "加分"}],
            "common_questions": [{"question": "自我介绍", "answer_strategy": "STAR法则", "pitfall": "背稿"}],
            "mindset": {"title": "放松", "suggestions": ["深呼吸"], "exercises": ["冥想"]},
            "preparation_checklist": [{"item": "简历", "priority": "high", "description": "多份"}],
        },
    }, ensure_ascii=False)
    result = skill.parse_response(json_input)
    assert result["content"] == "面试技巧"
    assert result["interview_coach"] is not None
    assert len(result["interview_coach"]["tips"]) == 1
    assert len(result["interview_coach"]["common_questions"]) == 1
    assert result["interview_coach"]["mindset"]["title"] == "放松"
    assert len(result["interview_coach"]["preparation_checklist"]) == 1

    # markdown 代码块包裹
    md_payload = {"content": "技巧", "interview_coach": {"tips": [], "common_questions": [], "mindset": {}, "preparation_checklist": []}}
    md_input = f"```json\n{json.dumps(md_payload, ensure_ascii=False)}\n```"
    result = skill.parse_response(md_input)
    assert result["content"] == "技巧"


def test_find_interview_coach():
    """验证 registry.find_skill_instance 能找到 InterviewCoachSkill。"""
    from app.skills.registry import find_skill_instance, get_skill

    # 元信息存在
    info = get_skill("interview_coach")
    assert info is not None
    assert info["display_name"] == "面试教练"

    # 实例化匹配
    instance = find_skill_instance("我想提升面试技巧", {})
    assert instance is not None
    assert instance.code == "interview_coach"

    # 非触发词返回 default
    default_inst = find_skill_instance("帮我写个爬虫", {})
    assert default_inst is not None
    assert default_inst.code == "default"


# ======================================================================
# ResumeOptimizerSkill tests
# ======================================================================


def test_resume_optimizer_skill():
    """验证 ResumeOptimizerSkill 元信息与激活逻辑。"""
    from app.skills.resume_optimizer import ResumeOptimizerSkill

    skill = ResumeOptimizerSkill()

    assert skill.code == "resume_optimizer"
    assert skill.name == "resume_optimizer"
    assert skill.icon == "file-text"

    # 触发词激活
    assert skill.should_activate("帮我简历优化", {})
    assert skill.should_activate("简历分析一下", {})
    assert skill.should_activate("优化简历内容", {})
    assert skill.should_activate("帮我做resume", {})
    assert not skill.should_activate("帮我写个爬虫", {})

    # system prompt 包含关键词
    sys_prompt = skill.build_system_prompt("用户背景：3年经验", [])
    assert "简历优化" in sys_prompt
    assert "GradPath" in sys_prompt

    # user prompt
    user_prompt = skill.build_user_prompt("帮我优化简历")
    assert "简历内容" in user_prompt

    # parse_response 兜底
    result = skill.parse_response("原始文本")
    assert result["content"] == "原始文本"
    assert result["career_plan"] is None


def test_resume_optimizer_parse_json():
    """验证 ResumeOptimizerSkill 的 JSON 解析能力。"""
    from app.skills.resume_optimizer import ResumeOptimizerSkill

    skill = ResumeOptimizerSkill()

    # 有效 JSON 输入
    json_input = '{"content": "简历分析报告", "suggestions": ["建议1", "建议2"], "score": 80, "improved_sections": {"项目经历": "优化后内容"}}'
    result = skill.parse_response(json_input)
    assert result["content"] == "简历分析报告"
    assert result["suggestions"] == ["建议1", "建议2"]
    assert result["score"] == 80
    assert result["improved_sections"] == {"项目经历": "优化后内容"}

    # markdown 代码块包裹
    md_input = '```json\n{"content": "报告", "score": 90}\n```'
    result = skill.parse_response(md_input)
    assert result["score"] == 90


def test_find_resume_optimizer():
    """验证 registry.find_skill_instance 能找到 ResumeOptimizerSkill。"""
    from app.skills.registry import find_skill_instance, get_skill

    # 元信息存在
    info = get_skill("resume_optimizer")
    assert info is not None
    assert info["display_name"] == "简历优化器"

    # 实例化匹配 — 使用唯一触发词避免与 resume_diagnosis 冲突
    instance = find_skill_instance("帮我简历检查", {})
    assert instance is not None
    assert instance.code == "resume_optimizer"


# ======================================================================
# CompanyReviewSkill tests
# ======================================================================


class TestCompanyReviewActivate:
    def setup_method(self):
        self.skill = CompanyReviewSkill()

    def test_activate_gongsi_pingjia(self):
        assert self.skill.should_activate("我想看看公司评价", {}) is True

    def test_activate_gongsi_koubei(self):
        assert self.skill.should_activate("这家公司口碑怎么样", {}) is True

    def test_activate_gongsi_zenmeyang(self):
        assert self.skill.should_activate("腾讯公司怎么样", {}) is True

    def test_activate_company_review(self):
        assert self.skill.should_activate("give me a company review", {}) is True

    def test_activate_gongzuo_tiyan(self):
        assert self.skill.should_activate("工作体验如何", {}) is True

    def test_not_activate_other(self):
        assert self.skill.should_activate("我想找工作", {}) is False

    def test_not_activate_plain(self):
        assert self.skill.should_activate("你好", {}) is False

    def test_metadata(self):
        assert self.skill.code == "company_review"
        assert self.skill.name == "company_review"
        assert self.skill.icon == "building"


class TestCompanyReviewParse:
    def setup_method(self):
        self.skill = CompanyReviewSkill()

    def test_parse_valid_json(self):
        payload = {
            "content": "公司评价分析总览",
            "company_review": {
                "company_name": "阿里巴巴",
                "overall_rating": "8.5",
                "work_culture": "创新驱动，结果导向",
                "work_life_balance": "加班较多，996文化",
                "compensation": "薪资竞争力强，股票激励",
                "management": "扁平化管理，开放沟通",
                "growth_opportunity": "技术成长空间大",
                "strengths": ["技术氛围好", "薪资有竞争力"],
                "concerns": ["加班文化严重", "竞争压力大"],
                "target_candidates": "适合有技术追求、能接受高强度工作的求职者",
                "summary": "技术氛围好但工作压力大",
            },
        }
        result = self.skill.parse_response(json.dumps(payload, ensure_ascii=False))
        assert result["content"] == "公司评价分析总览"
        assert result["company_review"]["company_name"] == "阿里巴巴"
        assert result["company_review"]["overall_rating"] == "8.5"
        assert len(result["company_review"]["strengths"]) == 2
        assert result["career_plan"] is None

    def test_parse_invalid_json(self):
        raw = "这不是一个JSON格式的回复"
        result = self.skill.parse_response(raw)
        assert result["content"] == raw
        assert result["company_review"] is None
        assert result["career_plan"] is None

    def test_parse_markdown_code_block(self):
        payload = {"content": "代码块回复", "company_review": {"company_name": "字节跳动"}}
        raw = f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
        result = self.skill.parse_response(raw)
        assert result["content"] == "代码块回复"
        assert result["company_review"]["company_name"] == "字节跳动"

    def test_parse_fallback_on_malformed(self):
        result = self.skill.parse_response("some random text {incomplete")
        assert result["content"] is not None
        assert result["company_review"] is None


class TestRegistryCompanyReview:
    def test_find_company_review(self):
        skill = registry.find_skill_instance("我想看看公司评价", {})
        assert skill is not None
        assert skill.code == "company_review"

    def test_find_gongsi_koubei(self):
        skill = registry.find_skill_instance("这家公司口碑怎么样", {})
        assert skill is not None
        assert skill.code == "company_review"

    def test_list_skills_includes_company_review(self):
        skills = registry.list_skills()
        codes = [s["code"] for s in skills]
        assert "company_review" in codes


# ======================================================================
# SalaryBenchmarkSkill tests
# ======================================================================


def test_salary_benchmark_skill():
    """验证 SalaryBenchmarkSkill 元信息与激活逻辑。"""
    from app.skills.salary_benchmark import SalaryBenchmarkSkill

    skill = SalaryBenchmarkSkill()

    assert skill.code == "salary_benchmark"
    assert skill.name == "salary_benchmark"
    assert skill.icon == "trending-up"

    assert skill.should_activate("我想看看薪资基准", {})
    assert skill.should_activate("帮我做个 salary benchmark", {})
    assert skill.should_activate("工资水平怎么样", {})
    assert skill.should_activate("做一份薪资分析报告", {})
    assert not skill.should_activate("帮我写个爬虫", {})

    sys_prompt = skill.build_system_prompt("用户背景：3年经验", [])
    assert "薪资基准分析" in sys_prompt
    assert "GradPath" in sys_prompt

    user_prompt = skill.build_user_prompt("分析一下我的薪资水平")
    assert "薪资基准分析" in user_prompt

    result = skill.parse_response("原始文本")
    assert result["content"] == "原始文本"
    assert result["salary_benchmark"] is None


def test_salary_benchmark_parse_json():
    """验证 SalaryBenchmarkSkill 的 JSON 解析能力。"""
    from app.skills.salary_benchmark import SalaryBenchmarkSkill

    skill = SalaryBenchmarkSkill()

    payload = {
        "content": "薪资基准分析报告",
        "salary_benchmark": {
            "summary": "整体薪资偏上",
            "industry": "互联网",
            "position": "后端开发",
            "region": "北京",
            "salary_distribution": {"min": 15000, "max": 35000, "median": 25000, "p25": 20000, "p75": 30000, "currency": "CNY", "sample_size": 500},
            "factors": [{"factor": "学历", "impact": "高", "description": "硕士及以上有明显优势"}],
            "trends": {"direction": "上涨", "annual_growth": "8%", "forecast": "持续上涨"},
            "comparisons": [{"name": "行业平均", "value": "25000", "benchmark": "22000"}],
            "recommendations": [{"title": "提升技能", "detail": "学习新技术", "priority": "high"}],
        },
    }
    result = skill.parse_response(json.dumps(payload, ensure_ascii=False))
    assert result["content"] == "薪资基准分析报告"
    assert result["salary_benchmark"]["industry"] == "互联网"
    assert result["salary_benchmark"]["position"] == "后端开发"
    assert result["salary_benchmark"]["region"] == "北京"
    assert result["salary_benchmark"]["salary_distribution"]["median"] == 25000
    assert len(result["salary_benchmark"]["factors"]) == 1
    assert result["salary_benchmark"]["trends"]["direction"] == "上涨"
    assert len(result["salary_benchmark"]["comparisons"]) == 1
    assert len(result["salary_benchmark"]["recommendations"]) == 1

    md_input = f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
    result = skill.parse_response(md_input)
    assert result["content"] == "薪资基准分析报告"
    assert result["salary_benchmark"]["industry"] == "互联网"


def test_find_salary_benchmark():
    """验证 registry.find_skill_instance 能找到 SalaryBenchmarkSkill。"""
    from app.skills.registry import find_skill_instance, get_skill

    info = get_skill("salary_benchmark")
    assert info is not None
    assert info["display_name"] == "薪资基准分析"

    instance = find_skill_instance("我想看看薪资基准", {})
    assert instance is not None
    assert instance.code == "salary_benchmark"

    instance2 = find_skill_instance("帮我做个 salary benchmark", {})
    assert instance2 is not None
    assert instance2.code == "salary_benchmark"

    default_inst = find_skill_instance("帮我写个爬虫", {})
    assert default_inst is not None
    assert default_inst.code == "default"


# ======================================================================
# UserReferralSkill tests
# ======================================================================


class TestUserReferralActivate:
    def setup_method(self):
        self.skill = UserReferralSkill()

    def test_activate_tuijian_pengyou(self):
        assert self.skill.should_activate("我想推荐朋友", {}) is True

    def test_activate_yaoqing_haoyou(self):
        assert self.skill.should_activate("帮我邀请好友", {}) is True

    def test_activate_tuijian_lianjie(self):
        assert self.skill.should_activate("给我一个推荐链接", {}) is True

    def test_activate_user_referral(self):
        assert self.skill.should_activate("user referral link", {}) is True

    def test_activate_yaoqing_zhuce(self):
        assert self.skill.should_activate("邀请注册链接", {}) is True

    def test_not_activate_other(self):
        assert self.skill.should_activate("我想找工作", {}) is False

    def test_not_activate_plain(self):
        assert self.skill.should_activate("你好", {}) is False

    def test_metadata(self):
        assert self.skill.code == "user_referral"
        assert self.skill.name == "user_referral"
        assert self.skill.icon == "users"


class TestUserReferralParse:
    def setup_method(self):
        self.skill = UserReferralSkill()

    def test_parse_valid_json(self):
        payload = {
            "content": "推荐方案生成成功",
            "referral_info": {
                "referral_code": "GP2024ABC",
                "referral_link": "https://gradpath.com/ref/GP2024ABC",
                "reward_tiers": [
                    {"tier": "铜牌", "referrals_needed": 3, "reward": "VIP会员7天", "description": "推荐3位好友"},
                    {"tier": "银牌", "referrals_needed": 10, "reward": "VIP会员30天", "description": "推荐10位好友"},
                    {"tier": "金牌", "referrals_needed": 30, "reward": "VIP会员1年", "description": "推荐30位好友"},
                ],
                "share_templates": {
                    "wechat": "我正在用GradPath做职业规划，一起加入吧！",
                    "weibo": "#GradPath# 超棒的职业规划工具，强烈推荐！",
                },
                "tracking": {
                    "total_referrals": 5,
                    "successful_referrals": 3,
                    "pending_referrals": 2,
                    "rewards_earned": 1,
                },
                "faq": [
                    {"question": "推荐链接有效期多久？", "answer": "永久有效"},
                    {"question": "奖励如何领取？", "answer": "自动发放到账户"},
                ],
            },
        }
        result = self.skill.parse_response(json.dumps(payload, ensure_ascii=False))
        assert result["content"] == "推荐方案生成成功"
        assert result["referral_info"]["referral_code"] == "GP2024ABC"
        assert result["referral_info"]["referral_link"] == "https://gradpath.com/ref/GP2024ABC"
        assert len(result["referral_info"]["reward_tiers"]) == 3
        assert result["referral_info"]["tracking"]["total_referrals"] == 5
        assert len(result["referral_info"]["faq"]) == 2
        assert "career_plan" not in result

    def test_parse_invalid_json(self):
        raw = "这不是一个JSON格式的回复"
        result = self.skill.parse_response(raw)
        assert result["content"] == raw
        assert result["referral_info"] is None
        assert "career_plan" not in result

    def test_parse_markdown_code_block(self):
        payload = {"content": "代码块回复", "referral_info": {"referral_code": "TEST123"}}
        raw = f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
        result = self.skill.parse_response(raw)
        assert result["content"] == "代码块回复"
        assert result["referral_info"]["referral_code"] == "TEST123"

    def test_parse_fallback_on_malformed(self):
        result = self.skill.parse_response("some random text {incomplete")
        assert result["content"] is not None
        assert result["referral_info"] is None


class TestRegistryUserReferral:
    def test_find_user_referral(self):
        skill = registry.find_skill_instance("我想推荐朋友", {})
        assert skill is not None
        assert skill.code == "user_referral"

    def test_find_tuijian_lianjie(self):
        skill = registry.find_skill_instance("给我一个推荐链接", {})
        assert skill is not None
        assert skill.code == "user_referral"

    def test_list_skills_includes_user_referral(self):
        skills = registry.list_skills()
        codes = [s["code"] for s in skills]
        assert "user_referral" in codes

    def test_get_skill_metadata(self):
        info = registry.get_skill("user_referral")
        assert info is not None
        assert info["display_name"] == "用户推荐助手"
        assert info["category"] == "generator"
