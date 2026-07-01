# backend/app/seed/seed_companies.py
"""公司元数据种子数据 — 50+ 知名企业，覆盖互联网/金融/通信/外企/国企/独角兽。"""
from sqlalchemy.orm import Session

from app.models.company import Company, CompanySize

# (name, industry, size, stage, headquarters, description)
COMPANIES = [
    # ===== 互联网大厂 =====
    ("腾讯", "互联网", CompanySize.giant, "已上市", "深圳", "中国领先的互联网增值服务提供商，业务涵盖社交、游戏、金融科技、云服务等。"),
    ("阿里巴巴", "互联网", CompanySize.giant, "已上市", "杭州", "全球领先的电子商务与科技公司，业务涵盖电商、云计算、数字媒体、金融科技。"),
    ("字节跳动", "互联网", CompanySize.giant, "未上市", "北京", "抖音、今日头条、TikTok 母公司，全球领先的内容与人工智能科技公司。"),
    ("百度", "互联网", CompanySize.giant, "已上市", "北京", "中国领先的搜索引擎与人工智能公司，深耕自动驾驶、大模型等领域。"),
    ("美团", "互联网", CompanySize.giant, "已上市", "北京", "中国领先的生活服务电子商务平台，覆盖外卖、到店、酒店旅游、出行等。"),
    ("京东", "互联网", CompanySize.giant, "已上市", "北京", "中国领先的技术驱动型电商和零售基础设施服务商。"),
    ("网易", "互联网", CompanySize.giant, "已上市", "杭州", "中国领先的互联网技术公司，涵盖游戏、音乐、教育、电商等业务。"),
    ("拼多多", "互联网", CompanySize.giant, "已上市", "上海", "中国领先的社交电商平台，以农产品上行和性价比消费著称。"),
    ("快手", "互联网", CompanySize.giant, "已上市", "北京", "中国领先的短视频与直播平台。"),
    ("小红书", "互联网", CompanySize.large, "战略融资", "上海", "年轻人的生活方式社区和消费决策入口。"),
    ("哔哩哔哩", "互联网", CompanySize.large, "已上市", "上海", "中国年轻人高度聚集的综合性视频社区，泛二次元文化代表。"),
    ("滴滴出行", "互联网", CompanySize.large, "未上市", "北京", "全球领先的一站式多元化出行平台。"),
    ("58同城", "互联网", CompanySize.large, "已上市", "北京", "中国领先的生活服务平台，覆盖招聘、房产、二手等。"),
    ("携程", "互联网", CompanySize.large, "已上市", "上海", "全球领先的一站式旅行服务平台。"),
    ("知乎", "互联网", CompanySize.medium, "已上市", "北京", "中文互联网高质量的问答社区和原创内容平台。"),
    ("米哈游", "互联网", CompanySize.medium, "未上市", "上海", "《原神》《崩坏》系列开发商，全球知名游戏公司。"),

    # ===== 金融 =====
    ("工商银行", "金融", CompanySize.giant, "已上市", "北京", "中国最大的国有商业银行，资产规模全球前列。"),
    ("建设银行", "金融", CompanySize.giant, "已上市", "北京", "中国四大国有商业银行之一。"),
    ("招商银行", "金融", CompanySize.giant, "已上市", "深圳", "中国领先的股份制商业银行，零售银行标杆。"),
    ("中国银行", "金融", CompanySize.giant, "已上市", "北京", "中国四大国有商业银行之一，国际化程度最高的中资银行。"),
    ("农业银行", "金融", CompanySize.giant, "已上市", "北京", "中国四大国有商业银行之一，服务三农为特色。"),
    ("中金公司", "金融", CompanySize.large, "已上市", "北京", "中国首家中外合资的投资银行，顶尖投行之一。"),
    ("中信证券", "金融", CompanySize.large, "已上市", "北京", "中国规模最大的综合性证券公司之一。"),
    ("蚂蚁集团", "金融", CompanySize.giant, "未上市", "杭州", "支付宝母公司，全球领先的金融科技公司。"),

    # ===== 通信 =====
    ("华为", "通信", CompanySize.giant, "未上市", "深圳", "全球领先的ICT基础设施和智能终端提供商。"),
    ("中兴通讯", "通信", CompanySize.giant, "已上市", "深圳", "全球领先的综合通信信息解决方案提供商。"),
    ("小米", "通信", CompanySize.giant, "已上市", "北京", "以智能手机、智能硬件和IoT平台为核心的互联网公司。"),
    ("荣耀", "通信", CompanySize.large, "未上市", "深圳", "全球领先的智能终端品牌。"),

    # ===== 外企 =====
    ("微软", "互联网", CompanySize.giant, "已上市", "美国雷德蒙德", "全球最大的软件公司，Azure 云、Office、Windows 等产品矩阵。"),
    ("谷歌", "互联网", CompanySize.giant, "已上市", "美国山景城", "全球领先的搜索与人工智能公司。"),
    ("亚马逊", "互联网", CompanySize.giant, "已上市", "美国西雅图", "全球最大的电商平台与 AWS 云服务提供商。"),
    ("苹果", "互联网", CompanySize.giant, "已上市", "美国库比蒂诺", "全球领先的消费电子与软件公司。"),
    ("Meta", "互联网", CompanySize.giant, "已上市", "美国门洛帕克", "Facebook、Instagram、WhatsApp 母公司，元宇宙探索者。"),
    ("英伟达", "半导体", CompanySize.giant, "已上市", "美国圣克拉拉", "全球 GPU 与 AI 芯片龙头。"),
    ("高通", "半导体", CompanySize.giant, "已上市", "美国圣迭戈", "全球领先的无线通信芯片厂商。"),

    # ===== 国企/能源 =====
    ("国家电网", "能源", CompanySize.giant, "未上市", "北京", "全球最大的公用事业企业，负责中国电网运营。"),
    ("中石油", "能源", CompanySize.giant, "已上市", "北京", "中国最大的油气生产和供应商。"),
    ("中石化", "能源", CompanySize.giant, "已上市", "北京", "中国最大的成品油供应商和石化企业。"),
    ("中国移动", "通信", CompanySize.giant, "已上市", "北京", "全球用户规模最大的移动通信运营商。"),
    ("中国电信", "通信", CompanySize.giant, "已上市", "北京", "中国领先的全业务综合信息服务提供商。"),

    # ===== 独角兽/新能源 =====
    ("大疆", "制造", CompanySize.large, "未上市", "深圳", "全球领先的民用无人机与航拍技术公司。"),
    ("理想汽车", "制造", CompanySize.large, "已上市", "北京", "中国领先的新能源汽车制造商。"),
    ("蔚来", "制造", CompanySize.large, "已上市", "上海", "全球化的智能电动汽车公司。"),
    ("小鹏汽车", "制造", CompanySize.large, "已上市", "广州", "中国领先的智能电动汽车设计及制造商。"),
    ("比亚迪", "制造", CompanySize.giant, "已上市", "深圳", "全球新能源汽车销量冠军，覆盖电池、电子、汽车全产业链。"),

    # ===== 半导体/硬科技 =====
    ("中芯国际", "半导体", CompanySize.large, "已上市", "上海", "中国大陆规模最大、技术最先进的集成电路晶圆代工企业。"),
    ("长江存储", "半导体", CompanySize.large, "未上市", "武汉", "中国领先的3D NAND闪存设计制造一体化企业。"),

    # ===== 物流/制造 =====
    ("顺丰", "物流", CompanySize.giant, "已上市", "深圳", "中国领先的综合物流服务商。"),
    ("联想", "制造", CompanySize.giant, "已上市", "北京", "全球领先的PC与智能设备制造商。"),

    # ===== 在线教育/医疗 =====
    ("好未来", "教育", CompanySize.large, "已上市", "北京", "中国领先的智慧教育科技公司。"),
    ("京东健康", "医疗", CompanySize.large, "已上市", "北京", "中国领先的医疗健康服务平台。"),

    # ===== 其他知名企业 =====
    ("得物", "互联网", CompanySize.large, "未上市", "上海", "新一代潮流网购社区，年轻人喜爱的潮流电商平台。"),
    ("SHEIN", "互联网", CompanySize.giant, "未上市", "广州", "全球领先的跨境快时尚电商平台。"),
]


def seed_companies(db: Session) -> int:
    """插入公司元数据种子数据（幂等：已存在的公司跳过）。

    Returns:
        新插入的公司数量
    """
    inserted = 0
    for name, industry, size, stage, hq, desc in COMPANIES:
        existing = db.query(Company).filter(Company.name == name).first()
        if existing:
            continue
        db.add(
            Company(
                name=name,
                industry=industry,
                size=size,
                stage=stage,
                headquarters=hq,
                description=desc,
            )
        )
        inserted += 1
    db.commit()
    return inserted
