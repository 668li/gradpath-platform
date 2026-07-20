# -*- coding: utf-8 -*-
"""Company data expansion — generate 5000 new companies for GradPath.

Covers 15 industries with realistic Chinese company names and metadata.
Generates company_expand.json and imports into the companies table.

Usage (inside Docker):
    docker exec gradpath-backend-1 python /app/app/crawlers/real_data/company_expand.py
"""
import json
import os
import random
import sys
import uuid

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(DATA_DIR, "company_expand.json")
sys.path.insert(0, os.path.join(DATA_DIR, '..', '..', '..'))

from sqlalchemy import text, func, select
from app.database import SessionLocal, engine, Base
from app.models.company import Company, CompanySize

# ── Industry definitions ──────────────────────────────────────────────
INDUSTRIES = {
    "IT/互联网": {
        "prefixes": ["字节", "星辰", "云翼", "蓝海", "极光", "灵犀", "锐创", "智联",
                     "慧通", "飞翼", "博云", "易联", "创智", "万维", "鼎信", "天玑",
                     "数澜", "光年", "深势", "元象"],
        "suffixes": ["科技", "信息技术", "数据", "智能", "网络", "软件", "数字科技",
                     "信息", "云计算", "大数据"],
        "description_templates": [
            "专注于{sub}领域的科技公司，致力于为客户提供高效的数字化解决方案",
            "领先的{sub}技术服务商，深耕行业多年，拥有丰富的项目经验",
            "创新型{sub}企业，以技术驱动业务增长，服务覆盖全国多个城市",
        ],
        "sub_fields": ["人工智能", "大数据", "云计算", "物联网", "区块链", "网络安全",
                       "SaaS", "企业服务", "移动互联网", "游戏开发"],
    },
    "金融/银行": {
        "prefixes": ["中银", "汇丰", "恒信", "泰和", "安信", "嘉实", "博时", "华泰",
                     "国信", "海通", "广发", "光大", "民生", "华夏", "交银", "招银",
                     "建信", "工银", "农信", "中金"],
        "suffixes": ["证券", "基金", "资产管理", "投资", "信托", "银行", "保险",
                     "金融科技", "资本", "理财"],
        "description_templates": [
            "综合性{sub}机构，提供全方位的金融服务和解决方案",
            "专业的{sub}服务商，以风控为核心，为客户创造稳健收益",
            "领先的{sub}平台，融合传统金融与科技创新",
        ],
        "sub_fields": ["银行", "证券", "基金", "保险", "信托", "期货", "资产管理",
                       "财富管理", "金融科技", "支付结算"],
    },
    "教育/培训": {
        "prefixes": ["启航", "新知", "博学", "明德", "弘文", "育才", "树人", "培优",
                     "知行", "翰林", "青云", "学海", "智学", "优学", "立德", "致远",
                     "笃学", "思源", "求知", "卓越"],
        "suffixes": ["教育", "培训", "学习", "学院", "学堂", "教育科技", "在线教育",
                     "教育咨询", "职业培训", "教育集团"],
        "description_templates": [
            "专业的{sub}教育机构，助力学员实现职业发展目标",
            "领先的{sub}培训平台，提供优质的教学资源和服务",
            "创新型{sub}教育企业，以科技赋能教育",
        ],
        "sub_fields": ["K12教育", "职业教育", "语言培训", "IT培训", "艺术培训",
                       "在线教育", "留学咨询", "考证培训", "学历教育", "企业内训"],
    },
    "医疗/健康": {
        "prefixes": ["康健", "仁和", "瑞康", "博爱", "华医", "泰康", "美年", "爱尔",
                     "恒瑞", "药明", "迈瑞", "微创", "百济", "信达", "君实", "荣昌",
                     "科伦", "石药", "齐鲁", "扬子江"],
        "suffixes": ["医药", "医疗", "生物科技", "制药", "医疗器械", "健康", "药业",
                     "生物技术", "生命科学", "医疗服务"],
        "description_templates": [
            "致力于{sub}领域的创新型企业，为人类健康事业贡献力量",
            "专业的{sub}服务商，拥有先进的技术和丰富的行业经验",
            "领先的{sub}企业，以研发创新驱动企业发展",
        ],
        "sub_fields": ["创新药", "仿制药", "医疗器械", "体外诊断", "医疗服务",
                       "生物制品", "中药", "医药流通", "健康管理", "基因检测"],
    },
    "制造/工程": {
        "prefixes": ["三一", "中联", "徐工", "柳工", "潍柴", "格力", "美的", "海尔",
                     "比亚迪", "吉利", "长城", "奇瑞", "江淮", "陕汽", "重汽", "东风",
                     "一汽", "上汽", "北汽", "广汽"],
        "suffixes": ["重工", "机械", "电器", "制造", "工业", "装备", "汽车",
                     "新能源", "智能装备", "精密制造"],
        "description_templates": [
            "大型{sub}企业，产品远销海内外市场",
            "专业的{sub}制造商，以品质赢得客户信赖",
            "创新型{sub}企业，持续推动制造业转型升级",
        ],
        "sub_fields": ["工程机械", "汽车制造", "家电制造", "精密仪器", "新能源汽车",
                       "智能制造", "航空航天", "轨道交通", "船舶制造", "新材料"],
    },
    "零售/电商": {
        "prefixes": ["优品", "优选", "乐购", "惠享", "淘金", "好物", "严选", "聚美",
                     "小红", "有品", "考拉", "当当", "唯品", "蘑菇", "美丽", "尚品",
                     "名创", "KK", "喜茶", "奈雪"],
        "suffixes": ["电商", "零售", "商贸", "购物", "优品", "生活", "超市",
                     "百货", "新零售", "折扣"],
        "description_templates": [
            "创新型{sub}平台，为消费者提供优质的商品和服务",
            "专业的{sub}企业，以用户需求为导向，打造极致购物体验",
            "领先的{sub}品牌，覆盖线上线下全渠道",
        ],
        "sub_fields": ["综合电商", "跨境电商", "生鲜电商", "社交电商", "社区团购",
                       "新零售", "便利店", "百货", "奢侈品", "潮玩"],
    },
    "物流/供应链": {
        "prefixes": ["顺丰", "中通", "圆通", "韵达", "申通", "极兔", "德邦", "百世",
                     "京东", "菜鸟", "丰网", "壹米", "安能", "壹站", "福佑", "运满满",
                     "货拉拉", "快狗", "日日顺", "苏宁"],
        "suffixes": ["物流", "快递", "供应链", "速递", "货运", "仓储", "供应链管理",
                     "国际物流", "冷链物流", "智慧物流"],
        "description_templates": [
            "专业的{sub}服务商，提供高效便捷的物流解决方案",
            "领先的{sub}企业，网络覆盖全国主要城市",
            "创新型{sub}平台，以科技驱动物流效率提升",
        ],
        "sub_fields": ["快递", "快运", "仓储", "冷链", "跨境物流", "同城配送",
                       "供应链管理", "即时配送", "大宗物流", "农产品物流"],
    },
    "餐饮/食品": {
        "prefixes": ["海底", "呷哺", "西贝", "外婆", "全聚", "便宜", "老乡", "喜茶",
                     "奈雪", "瑞幸", "蜜雪", "书亦", "古茗", "茶百", "沪上", "益禾",
                     "霸王", "库迪", "Manner", "Seesaw"],
        "suffixes": ["餐饮", "食品", "美食", "饮品", "茶饮", "咖啡", "火锅",
                     "快餐", "小吃", "烘焙"],
        "description_templates": [
            "知名的{sub}品牌，以优质的产品和服务赢得消费者喜爱",
            "快速发展的{sub}企业，门店遍布全国多个城市",
            "创新的{sub}品牌，引领行业潮流",
        ],
        "sub_fields": ["中式餐饮", "西式餐饮", "茶饮", "咖啡", "烘焙", "快餐",
                       "火锅", "小吃", "预制菜", "食品加工"],
    },
    "能源/环保": {
        "prefixes": ["国电", "华能", "大唐", "华电", "国投", "中广核", "三峡", "中核",
                     "隆基", "通威", "晶科", "天合", "阳光", "金风", "远景", "宁德",
                     "亿纬", "国轩", "欣旺达", "蜂巢"],
        "suffixes": ["能源", "电力", "新能源", "光伏", "风电", "储能", "环保",
                     "清洁", "氢能", "锂电"],
        "description_templates": [
            "大型{sub}企业，致力于清洁能源的开发和利用",
            "专业的{sub}技术服务商，为客户提供一站式能源解决方案",
            "领先的{sub}企业，推动能源结构转型升级",
        ],
        "sub_fields": ["光伏发电", "风力发电", "储能", "氢能", "核电", "水电",
                       "环保工程", "碳交易", "动力电池", "充电桩"],
    },
    "传媒/文化": {
        "prefixes": ["华谊", "光线", "博纳", "万达", "爱奇艺", "优酷", "腾讯", "芒果",
                     "字节", "快手", "B站", "微博", "知乎", "小红书", "豆瓣", "虎扑",
                     "陌陌", "YY", "映客", "花椒"],
        "suffixes": ["传媒", "文化", "娱乐", "影视", "动漫", "游戏", "传媒集团",
                     "文化传媒", "数字娱乐", "内容"],
        "description_templates": [
            "知名的{sub}企业，创作了大量优质内容作品",
            "领先的{sub}平台，拥有庞大的用户群体",
            "创新型{sub}公司，以内容为核心竞争力",
        ],
        "sub_fields": ["影视制作", "游戏开发", "动漫", "短视频", "直播", "音乐",
                       "出版", "广告", "MCN", "数字阅读"],
    },
    "法律/咨询": {
        "prefixes": ["金杜", "中伦", "君合", "方达", "海问", "通商", "大成", "锦天城",
                     "德恒", "国浩", "竞天", "康达", "汉坤", "安理", "天元", "环球",
                     "天驰", "盈科", "京师", "隆安"],
        "suffixes": ["律师事务所", "律师事务所", "律所", "法律", "律所", "法务",
                     "咨询", "管理咨询", "战略咨询", "会计"],
        "description_templates": [
            "知名的{sub}机构，为客户提供专业的法律/咨询服务",
            "综合性的{sub}事务所，业务覆盖多个领域",
            "领先的{sub}机构，拥有丰富的行业经验",
        ],
        "sub_fields": ["民商事", "刑事辩护", "知识产权", "公司法", "劳动法",
                       "房地产", "国际贸易", "资本市场", "破产重组", "税务"],
    },
    "建筑/房地产": {
        "prefixes": ["万科", "碧桂园", "融创", "保利", "中海", "华润", "龙湖", "绿城",
                     "金地", "招商", "远洋", "中国建筑", "中国中铁", "中国交建", "中国铁建",
                     "中国电建", "中国能建", "中国冶建", "上海建工", "北京建工"],
        "suffixes": ["地产", "置业", "建设", "建筑工程", "房地产", "建筑集团",
                     "装饰", "幕墙", "园林", "设计院"],
        "description_templates": [
            "大型{sub}企业，业务覆盖全国多个城市",
            "专业的{sub}服务商，以品质和口碑赢得市场",
            "领先的{sub}企业，持续推动行业发展",
        ],
        "sub_fields": ["住宅开发", "商业地产", "物业管理", "建筑工程", "室内设计",
                       "景观设计", "市政工程", "桥梁隧道", "钢结构", "装配式建筑"],
    },
    "农业/食品": {
        "prefixes": ["中粮", "新希望", "温氏", "牧原", "正邦", "双汇", "雨润", "蒙牛",
                     "伊利", "光明", "三元", "完达山", "飞鹤", "澳优", "圣牧", "现代",
                     "壹号", "温氏", "正大", "大北农"],
        "suffixes": ["农业", "牧业", "食品", "乳业", "畜牧", "种业", "农化",
                     "饲料", "肉业", "粮油"],
        "description_templates": [
            "大型{sub}企业，致力于为消费者提供安全优质的农产品",
            "专业的{sub}服务商，从源头把控产品质量",
            "领先的{sub}企业，推动农业现代化发展",
        ],
        "sub_fields": ["种植业", "养殖业", "乳业", "肉制品", "水产", "饲料",
                       "种业", "农机", "农药化肥", "农产品加工"],
    },
    "旅游/酒店": {
        "prefixes": ["携程", "飞猪", "马蜂窝", "途牛", "同程", "去哪儿", "Booking",
                     "Airbnb", "华住", "锦江", "首旅", "如家", "汉庭", "亚朵", "全季",
                     "桔子", "维也纳", "格林", "尚美", "都市"],
        "suffixes": ["旅行", "旅游", "酒店", "民宿", "度假", "航空", "景区",
                     "文旅", "会展", "商旅"],
        "description_templates": [
            "知名的{sub}企业，为消费者提供优质的旅行服务",
            "专业的{sub}服务商，覆盖国内外热门目的地",
            "领先的{sub}品牌，以优质服务赢得口碑",
        ],
        "sub_fields": ["在线旅游", "酒店连锁", "民宿", "景区运营", "旅行社",
                       "航空", "邮轮", "会展", "主题公园", "免税"],
    },
    "体育/健身": {
        "prefixes": ["安踏", "李宁", "特步", "361", "匹克", "鸿星", "贵人鸟", "乔丹",
                     "耐克", "阿迪达斯", "彪马", "lululemon", "Keep", "咕咚", "薄荷",
                     "乐刻", "超级猩猩", "光猪", "威尔", "一兆"],
        "suffixes": ["体育", "运动", "健身", "体育用品", "运动科技", "健康",
                     "户外", "瑜伽", "体育产业", "体育文化"],
        "description_templates": [
            "知名的{sub}品牌，致力于推广全民运动健身",
            "专业的{sub}服务商，提供优质的运动体验",
            "领先的{sub}企业，以科技赋能运动健康",
        ],
        "sub_fields": ["运动品牌", "健身房", "户外运动", "体育赛事", "运动科技",
                       "体育培训", "体育媒体", "体育旅游", "电子竞技", "体育场馆"],
    },
}

# ── City lists by tier ────────────────────────────────────────────────
CITY_TIERS = {
    "一线": ["北京", "上海", "广州", "深圳"],
    "新一线": ["杭州", "成都", "武汉", "南京", "重庆", "苏州", "西安", "长沙", "天津", "郑州"],
    "二线": ["青岛", "大连", "宁波", "厦门", "合肥", "佛山", "东莞", "无锡", "昆明", "福州"],
    "三线": ["贵阳", "南宁", "兰州", "太原", "乌鲁木齐", "哈尔滨", "长春", "沈阳", "济南", "南昌"],
}

SIZE_OPTIONS = [
    ("startup", 10, 50),
    ("small", 50, 200),
    ("medium", 200, 2000),
    ("large", 2000, 10000),
    ("giant", 10000, 100000),
]

STAGES = ["初创期", "成长期", "扩张期", "成熟期", "稳定期", "转型期"]

WEBSITES = [
    "www.{name}.com", "www.{name}.cn", "www.{name}.com.cn",
    "{name}.com", "{name}.cn",
]


def generate_company_name(industry_data: dict) -> str:
    prefix = random.choice(industry_data["prefixes"])
    suffix = random.choice(industry_data["suffixes"])
    return f"{prefix}{suffix}"


def generate_companies(target_count: int = 5000) -> list[dict]:
    companies = []
    seen_names = set()
    all_cities = []
    for tier_cities in CITY_TIERS.values():
        all_cities.extend(tier_cities)

    industry_list = list(INDUSTRIES.keys())
    per_industry = target_count // len(industry_list)
    remainder = target_count % len(industry_list)

    for industry_name, industry_data in INDUSTRIES.items():
        count = per_industry + (1 if remainder > 0 else 0)
        remainder -= 1

        for _ in range(count):
            # Generate unique name
            for attempt in range(50):
                name = generate_company_name(industry_data)
                if name not in seen_names:
                    seen_names.add(name)
                    break
            else:
                # Fallback: append random number
                name = f"{name}{random.randint(100, 999)}"

            size_enum, size_min, size_max = random.choice(SIZE_OPTIONS)
            actual_size = random.randint(size_min, size_max)
            city = random.choice(all_cities)
            stage = random.choice(STAGES)
            sub = random.choice(industry_data["sub_fields"])
            template = random.choice(industry_data["description_templates"])
            description = template.format(sub=sub)

            website = random.choice(WEBSITES).format(
                name=name[:4].lower().replace("/", "")
            )

            companies.append({
                "name": name,
                "industry": industry_name,
                "size": size_enum,
                "actual_size": actual_size,
                "city": city,
                "stage": stage,
                "description": description,
                "website": f"https://{website}",
            })

    random.shuffle(companies)
    return companies[:target_count]


def import_companies(db, companies: list[dict]) -> tuple[int, int]:
    existing_names = set(
        row[0] for row in db.execute(select(Company.name)).fetchall()
    )
    print(f"  DB already has {len(existing_names)} companies")

    new_count = 0
    skip_count = 0

    size_map = {
        "startup": CompanySize.startup,
        "small": CompanySize.small,
        "medium": CompanySize.medium,
        "large": CompanySize.large,
        "giant": CompanySize.giant,
    }

    for item in companies:
        name = item["name"]
        if name in existing_names:
            skip_count += 1
            continue

        company = Company(
            id=uuid.uuid4(),
            name=name,
            industry=item["industry"],
            size=size_map.get(item["size"], CompanySize.medium),
            stage=item.get("stage"),
            headquarters=item.get("city"),
            description=item.get("description"),
        )
        db.add(company)
        existing_names.add(name)
        new_count += 1

        if new_count % 500 == 0:
            db.commit()
            print(f"  ... imported {new_count} companies")

    db.commit()
    return new_count, skip_count


def main():
    print("=" * 60)
    print("Company Data Expansion (5000 new companies)")
    print("=" * 60)

    companies = generate_companies(5000)

    # Save JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(companies, f, ensure_ascii=False, indent=2)
    print(f"Generated {len(companies)} companies → {OUTPUT_FILE}")

    # Import into DB
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("\n--- Before Import ---")
        before_count = db.execute(select(func.count(Company.id))).scalar()
        print(f"  companies: {before_count}")

        print("\nImporting companies → companies table ...")
        new_count, skip_count = import_companies(db, companies)
        print(f"  New: {new_count}, Skipped (dup): {skip_count}")

        print("\n--- After Import ---")
        after_count = db.execute(select(func.count(Company.id))).scalar()
        print(f"  companies: {after_count} (+{after_count - before_count})")

        # Industry breakdown
        print("\n--- Companies by Industry ---")
        rows = db.execute(
            text("SELECT industry, COUNT(*) FROM companies GROUP BY industry ORDER BY COUNT(*) DESC")
        ).fetchall()
        for row in rows:
            print(f"  {row[0]}: {row[1]}")

        # Size breakdown
        print("\n--- Companies by Size ---")
        rows = db.execute(
            text("SELECT size, COUNT(*) FROM companies GROUP BY size ORDER BY COUNT(*) DESC")
        ).fetchall()
        for row in rows:
            print(f"  {row[0]}: {row[1]}")

        print("\n" + "=" * 60)
        print(f"Company expansion complete! Added {new_count} companies.")
        print(f"Total companies: {after_count}")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
