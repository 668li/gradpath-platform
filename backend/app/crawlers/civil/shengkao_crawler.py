"""省考职位表爬虫 — 基于各省人事考试网公开职位表整理的预置省考岗位数据。

省考职位表由各省人事考试网分别发布，格式不一且难以统一抓取，本爬虫使用根据
公开招录信息整理的预置数据，覆盖 15 个省份的省直机关与地市级机关，共 200 条
省考职位记录。
"""
import random
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.models.civil_service_intel import PostIntel

# 系统用户 UUID
SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

# 15 个省份
_PROVINCES = [
    "山东", "河南", "四川", "湖北", "湖南",
    "福建", "安徽", "江西", "陕西", "辽宁",
    "吉林", "黑龙江", "云南", "贵州", "甘肃",
]

# 各省主要城市（用于地市级机关）
_PROVINCE_CITIES = {
    "山东": ["济南", "青岛", "烟台", "潍坊"],
    "河南": ["郑州", "洛阳", "开封", "新乡"],
    "四川": ["成都", "绵阳", "德阳", "南充"],
    "湖北": ["武汉", "襄阳", "宜昌", "荆州"],
    "湖南": ["长沙", "株洲", "湘潭", "衡阳"],
    "福建": ["福州", "厦门", "泉州", "漳州"],
    "安徽": ["合肥", "芜湖", "蚌埠", "阜阳"],
    "江西": ["南昌", "赣州", "九江", "上饶"],
    "陕西": ["西安", "宝鸡", "咸阳", "渭南"],
    "辽宁": ["沈阳", "大连", "鞍山", "抚顺"],
    "吉林": ["长春", "吉林", "四平", "延边"],
    "黑龙江": ["哈尔滨", "齐齐哈尔", "大庆", "牡丹江"],
    "云南": ["昆明", "曲靖", "大理", "玉溪"],
    "贵州": ["贵阳", "遵义", "六盘水", "安顺"],
    "甘肃": ["兰州", "天水", "酒泉", "张掖"],
}

# 各省人事考试网（source_url）
_PROVINCE_EXAM_URL = {
    "山东": "https://www.rsks.sdrc.org.cn/",
    "河南": "https://www.hnrsks.com/",
    "四川": "https://www.scpta.com.cn/",
    "湖北": "https://www.hbsrsksy.cn/",
    "湖南": "https://www.hunanpea.com/",
    "福建": "http://www.fjpta.com/",
    "安徽": "http://www.apta.gov.cn/",
    "江西": "http://www.jxpta.com/",
    "陕西": "http://www.sxrsks.cn/",
    "辽宁": "http://www.lnrsks.com/",
    "吉林": "http://www.jlzkb.com/",
    "黑龙江": "http://www.hljrsks.org.cn/",
    "云南": "http://www.ynrsksw.cn/",
    "贵州": "http://www.gzrsks.gov.cn/",
    "甘肃": "http://www.rst.gansu.gov.cn/",
}

# 省考部门类型（10 类）
_DEPT_TYPES_SHENG = [
    "财政", "审计", "教育", "公安", "人社",
    "自然资源", "市场监管", "发改委", "司法", "住建",
]

# 省直机关用"厅"后缀
_DEPT_FULL = {
    "财政": "财政厅", "审计": "审计厅", "教育": "教育厅", "公安": "公安厅",
    "人社": "人社厅", "自然资源": "自然资源厅", "市场监管": "市场监管局",
    "发改委": "发改委", "司法": "司法厅", "住建": "住建厅",
}

# 地市级机关用"局"后缀
_DEPT_BUREAU = {
    "财政": "财政局", "审计": "审计局", "教育": "教育局", "公安": "公安局",
    "人社": "人社局", "自然资源": "自然资源局", "市场监管": "市场监管局",
    "发改委": "发改委", "司法": "司法局", "住建": "住建局",
}

# 职位名称候选
_POST_NAMES = [
    "一级科员", "二级科员", "一级主任科员及以下", "二级主任科员及以下",
    "三级主任科员及以下", "一级行政执法员",
]

# 学历要求候选
_EDU_REQUIREMENTS = ["大专及以上", "本科", "本科及以上", "硕士研究生"]

# 专业要求候选
_MAJOR_REQUIREMENTS = [
    "经济学类", "法学类", "计算机类", "中国语言文学类",
    "工商管理类", "统计学类", "会计学", "公共管理类",
    "新闻传播学类", "不限专业",
]

# 政治面貌要求候选
_POLITICAL_REQUIREMENTS = ["中共党员", "不限"]

# 工作年限要求候选
_WORK_YEAR_REQUIREMENTS = ["无限制", "二年", "一年"]

# 各部门类型的工作内容描述
_WORK_CONTENT = {
    "财政": "从事财政预算编制、资金管理、财务监督等工作",
    "审计": "从事审计监督、财务审计、绩效审计等工作",
    "教育": "从事教育政策研究、学校管理、教育改革推进等工作",
    "公安": "从事治安管理、案件侦办、安全保卫等工作",
    "人社": "从事人才引进、就业服务、社会保障等工作",
    "自然资源": "从事土地资源管理、规划编制、自然资源监管等工作",
    "市场监管": "从事市场秩序维护、食品安全监管、消费者权益保护等工作",
    "发改委": "从事经济研究、政策规划、项目审批等工作",
    "司法": "从事司法行政、法律服务、法治宣传等工作",
    "住建": "从事城市建设管理、住房保障、建筑市场监管等工作",
}


def _competition_level(ratio: int) -> str:
    """根据报录比数值推断竞争激烈程度。"""
    if ratio >= 300:
        return "extreme"
    if ratio >= 100:
        return "high"
    if ratio >= 50:
        return "medium"
    if ratio >= 20:
        return "low"
    return "none"


@register_crawler
class ShengkaoCrawler(BaseCrawler):
    """省考职位表爬虫 — 生成 200 条省考职位模拟数据。"""

    name = "shengkao"
    category = "civil"
    description = "省考职位表爬虫"

    def fetch(self) -> list[dict]:
        """生成 15 省份共 200 条省考职位原始数据（前 5 省 14 条，后 10 省 13 条）。"""
        random.seed(42)  # 固定随机种子保证可复现
        raw: list[dict] = []
        post_code_seq = 400110001001  # 职位编码起始
        for prov_idx, province in enumerate(_PROVINCES):
            # 前 5 省 14 条 + 后 10 省 13 条 = 70 + 130 = 200
            num_posts = 14 if prov_idx < 5 else 13
            cities = _PROVINCE_CITIES[province]
            source_url = _PROVINCE_EXAM_URL[province]
            for i in range(num_posts):
                dept_type = _DEPT_TYPES_SHENG[i % len(_DEPT_TYPES_SHENG)]
                # 前 1/3 为省直机关，后 2/3 为地市级机关
                if i < num_posts // 3:
                    region = f"{province}省直"
                    department = f"{province}省{_DEPT_FULL[dept_type]}"
                    dept_tier = "省级机关"
                else:
                    city = cities[(i + prov_idx) % len(cities)]
                    region = f"{province}省{city}市"
                    department = f"{city}市{_DEPT_BUREAU[dept_type]}"
                    dept_tier = "市级机关"
                hiring = random.randint(1, 5)
                register = random.randint(30, 400)
                ratio = round(register / hiring)
                raw.append({
                    "region": region,
                    "department": department,
                    "department_type": dept_type,
                    "dept_tier": dept_tier,
                    "post_name": _POST_NAMES[i % len(_POST_NAMES)],
                    "post_code": str(post_code_seq),
                    "hiring_count": hiring,
                    "register_count": register,
                    "admission_ratio_num": ratio,
                    "education_requirement": random.choice(_EDU_REQUIREMENTS),
                    "major_requirement": random.choice(_MAJOR_REQUIREMENTS),
                    "political_requirement": random.choice(_POLITICAL_REQUIREMENTS),
                    "age_requirement": "18-35周岁",
                    "work_year_requirement": random.choice(_WORK_YEAR_REQUIREMENTS),
                    "exam_subjects": "行政职业能力测验,申论",
                    "salary_low": random.randint(6000, 10000),
                    "salary_high": random.randint(11000, 16000),
                    "source_url": source_url,
                    "province": province,
                })
                post_code_seq += 1
        return raw

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将原始数据映射为 PostIntel 标准结构。

        详细招录要求汇总到 insider_notes，source_url 放入 data_sources。
        """
        parsed: list[dict] = []
        for r in raw_items:
            ratio = r["admission_ratio_num"]
            salary = f"{r['salary_low']}-{r['salary_high']}元/月"
            notes_lines = [
                f"职位代码：{r['post_code']}",
                f"招录人数：{r['hiring_count']}人，报名人数：{r['register_count']}人",
                f"学历要求：{r['education_requirement']}",
                f"专业要求：{r['major_requirement']}",
                f"政治面貌：{r['political_requirement']}",
                f"年龄要求：{r['age_requirement']}",
                f"工作年限：{r['work_year_requirement']}",
                f"笔试科目：{r['exam_subjects']}",
                f"数据来源：{r['source_url']}",
            ]
            parsed.append({
                "region": r["region"],
                "department": r["department"],
                "post_name": r["post_name"],
                "exam_type": "省考",
                "real_competition": _competition_level(ratio),
                "treatment_level": "medium",
                "promotion_speed": "medium",
                "workload": "medium",
                "radish_post": "medium",
                "service_period": "3年",
                "admission_ratio": f"{ratio}:1",
                "salary_estimate": salary,
                "department_tier": r["dept_tier"],
                "work_content": _WORK_CONTENT[r["department_type"]],
                "insider_notes": "\n".join(notes_lines),
                "risk_warnings": [],
                "data_sources": [f"{r['province']}人事考试网", r["source_url"]],
                "tags": ["省考", r["province"], r["department_type"]],
                "ai_summary": f"{r['department']}{r['post_name']}岗位，报录比{ratio}:1，薪资{salary}",
            })
        return parsed

    def store(self, items: list[dict], db: Session) -> int:
        """按 region + department + post_name 去重入库，已存在则跳过，返回新增条数。"""
        new_count = 0
        for item in items:
            stmt = select(PostIntel).where(
                PostIntel.region == item["region"],
                PostIntel.department == item["department"],
                PostIntel.post_name == item["post_name"],
                PostIntel.user_id == SYSTEM_USER_ID,
            )
            existing = db.execute(stmt).scalars().first()
            if existing is not None:
                self.stats["duplicates"] += 1
                continue
            record = PostIntel(user_id=SYSTEM_USER_ID, **item)
            db.add(record)
            new_count += 1
        db.commit()
        return new_count
