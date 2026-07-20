# -*- coding: utf-8 -*-
"""优化版批量生成脚本 — 批量插入+内存去重，目标50,000条"""
import sys, random, os, time
sys.stdout.reconfigure(encoding='utf-8')
random.seed(42)

sys.path.insert(0, r"D:\职业规划\职业规划\backend")
os.environ.setdefault("ENVIRONMENT", "development")

from app.database import SessionLocal
from app.models.grad_intel import GradSchoolIntel
from app.models.qa import QA
from app.models.qa_answer import QAAnswer
from app.models.user import User
from app.models.knowledge_article import KnowledgeArticle
from app.models.experience_post import ExperiencePost
from uuid import UUID
from sqlalchemy import text

SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

# ===== 学校和专业列表 =====
SCHOOLS = (
    ["清华大学","北京大学","浙江大学","复旦大学","上海交通大学","中国科学技术大学","南京大学","武汉大学","华中科技大学","中山大学",
     "哈尔滨工业大学","西安交通大学","北京航空航天大学","天津大学","四川大学","中南大学","东南大学","同济大学","北京理工大学","华东师范大学",
     "厦门大学","山东大学","大连理工大学","吉林大学","东北大学","重庆大学","湖南大学","兰州大学","西北工业大学","中国农业大学",
     "北京师范大学","中国人民大学","南开大学","电子科技大学","华南理工大学","南京航空航天大学","南京理工大学","河海大学","江南大学","苏州大学",
     "华东理工大学","北京交通大学","北京化工大学","北京林业大学","华北电力大学","中国矿业大学","中国石油大学","上海大学","东华大学","上海外国语大学",
     "合肥工业大学","安徽大学","福州大学","南昌大学","郑州大学","武汉理工大学","华中农业大学","华中师范大学","湖南师范大学","暨南大学",
     "华南师范大学","广西大学","四川农业大学","西南大学","西南交通大学","云南大学","贵州大学","西北大学","长安大学","西安电子科技大学",
     "陕西师范大学","宁夏大学","延边大学","海南大学","西藏大学","青海大学","石河子大学","新疆大学","太原理工大学","内蒙古大学",
     "辽宁大学","东北师范大学","东北农业大学","东北林业大学","南方科技大学","上海科技大学","中国科学院大学","湘潭大学","南京信息工程大学",
     "广州医科大学","华南农业大学","宁波大学","西南石油大学","南京医科大学","首都医科大学","西湖大学","河南大学","山西大学","南京邮电大学",
     "浙江工业大学","杭州电子科技大学","深圳大学","广东工业大学","南京工业大学","燕山大学","扬州大学","集美大学","华侨大学","黑龙江大学",
     "西南政法大学","上海海事大学","上海理工大学","重庆邮电大学","昆明理工大学","成都信息工程大学","桂林电子科技大学","长春理工大学","沈阳工业大学","兰州理工大学"]
)

MAJORS = ["计算机科学与技术","软件工程","人工智能","数据科学与大数据","电子信息","通信工程","自动化","电气工程",
           "机械工程","材料科学与工程","土木工程","化学工程","金融学","经济学","会计学","工商管理",
           "法学","教育学","临床医学","口腔医学","药学","中国语言文学","外国语言文学","新闻传播学",
           "数学","物理学","化学","生物学","统计学","环境科学","哲学","历史学","社会学","护理学",
           "艺术设计","广播电视编导","公共管理","政治学","图书馆学","马克思主义理论"]

def gen_intel_batch(db, target_new=4000):
    """批量生成院校情报到目标总数"""
    from app.models.grad_intel import GradSchoolIntel
    current = db.query(GradSchoolIntel).count()
    needed = max(0, target_new)
    
    # Get existing keys
    existing = set()
    for row in db.query(GradSchoolIntel.school_name, GradSchoolIntel.major_name).all():
        existing.add((row[0], row[1]))
    
    print(f"  现有院校情报: {current}, 需要新增: {needed}")
    
    DISCRIM = ["severe", "moderate", "mild", "none"]
    PROTECT = ["yes", "no", "partial"]
    FORMATS = ["面试为主", "机试+面试", "笔试+面试", "综合面试"]
    SUPPRESS = ["severe", "moderate", "mild", "none"]
    TRANSFER = ["yes", "no", "partial"]
    TIER_BASE = {"985": 380, "211": 340, "双一流": 330, "普通": 310}
    
    def get_tier(school):
        if school in SCHOOLS[:40]: return "985"
        if school in SCHOOLS[40:80]: return "211"
        if school in SCHOOLS[80:100]: return "双一流"
        return "普通"
    
    batch = []
    seen = set()
    for school in SCHOOLS:
        tier = get_tier(school)
        base = TIER_BASE.get(tier, 310)
        majors = random.sample(MAJORS, min(4, len(MAJORS)))
        for major in majors:
            if (school, major) in existing or (school, major) in seen:
                continue
            seen.add((school, major))
            batch.append(GradSchoolIntel(
                user_id=SYSTEM_USER_ID, school_name=school, major_name=major,
                school_tier=tier, year=2026,
                background_discrimination=random.choice(DISCRIM),
                first_choice_protection=random.choice(PROTECT),
                admission_ratio=f"{random.randint(5,35)}:1",
                push_ratio=f"{random.randint(20,80)}%",
                actual_quota=random.randint(10, 200),
                score_line=base + random.randint(-30, 30),
                retest_weight=f"{random.randint(30,60)}%",
                retest_format=random.choice(FORMATS),
                score_suppression=random.choice(SUPPRESS),
                transfer_friendly=random.choice(TRANSFER),
            ))
            if len(batch) >= needed:
                break
        if len(batch) >= needed:
            break
    
    # Fill remaining with random
    while len(batch) < needed:
        school = random.choice(SCHOOLS)
        major = random.choice(MAJORS)
        if (school, major) in existing or (school, major) in seen:
            continue
        seen.add((school, major))
        tier = "985" if school in SCHOOLS[:40] else "211" if school in SCHOOLS[40:80] else "普通"
        base = TIER_BASE.get(tier, 310)
        batch.append(GradSchoolIntel(
            user_id=SYSTEM_USER_ID, school_name=school, major_name=major,
            school_tier=tier, year=2026,
            background_discrimination=random.choice(DISCRIM),
            first_choice_protection=random.choice(PROTECT),
            admission_ratio=f"{random.randint(5,35)}:1",
            push_ratio=f"{random.randint(20,80)}%",
            actual_quota=random.randint(10, 200),
            score_line=base + random.randint(-30, 30),
            retest_weight=f"{random.randint(30,60)}%",
            retest_format=random.choice(FORMATS),
            score_suppression=random.choice(SUPPRESS),
            transfer_friendly=random.choice(TRANSFER),
        ))
    
    db.bulk_save_objects(batch)
    db.commit()
    print(f"  院校情报: 新增 {len(batch)} 条 (总计 {current + len(batch)})")
    return len(batch)

def gen_qa_batch(db, target_new=5000):
    """批量生成问答到目标总数"""
    current = db.query(QA).count()
    needed = max(0, target_new)
    
    # Get existing titles
    existing = set()
    for row in db.query(QA.title).all():
        existing.add(row[0])
    
    print(f"  现有问答: {current}, 需要新增: {needed}")
    
    CATEGORIES = [
        ("408计算机", ["数据结构","操作系统","计算机网络","组成原理","算法"]),
        ("考研数学", ["高等数学","线性代数","概率论","数理统计"]),
        ("考研英语", ["阅读理解","完形填空","翻译","作文","单词"]),
        ("考研政治", ["马原","毛中特","近代史","思修","时政"]),
        ("复试", ["面试","英语口语","简历","导师联系","专业课"]),
        ("调剂", ["调剂系统","B区院校","科研院所","调剂策略"]),
        ("择校", ["985vs211","学硕vs专硕","跨考","分数线"]),
        ("心态", ["焦虑","时间管理","动力","家庭沟通"]),
        ("备考", ["基础阶段","强化阶段","冲刺阶段","真题使用"]),
    ]
    
    TEMPLATES = [
        ("{cat}的{sub}怎么学？", "建议：1）制定详细计划；2）分阶段执行；3）定期复盘。参考高分学长学姐经验。"),
        ("{cat}看什么书？推荐哪些老师？", "结合目标院校大纲选择。看指定书目+口碑辅导书。"),
        ("{cat}每天学多长时间？", "基础阶段6-8h，强化8-10h，冲刺10-12h。关键是效率。"),
        ("{cat}怎么规划复习进度？", "基础(3-6月)→强化(7-10月)→冲刺(11-12月)，每阶段有目标。"),
        ("跨考{cat}难吗？", "需要补专业课基础，建议提前半年开始，找学长学姐获取真题。"),
        ("{cat}就业前景怎么样？", "看招聘网站数据，联系在读学长学姐，关注行业趋势。"),
        ("二战考研值不值得？", "评估差距、压力承受力、是否有更好选择。差分不大且目标明确，成功率较高。"),
        ("{cat}的参考书怎么选？", "1）看目标院校指定书目；2）参考高分经验；3）选口碑好的。不要贪多。"),
        ("{cat}真题怎么用？", "近10年真题至少做3遍：第一遍摸底，第二遍精做，第三遍模拟。"),
        ("{cat}冲刺阶段怎么复习？", "查漏补缺为主，回归基础知识，模拟考试找感觉，调整心态。"),
    ]
    
    qa_batch = []
    ans_batch = []
    seen = set()
    count = 0
    
    while count < needed:
        cat = random.choice(CATEGORIES)
        sub = random.choice(cat[1])
        tmpl = random.choice(TEMPLATES)
        title = tmpl[0].format(cat=cat[0], sub=sub) + f"（{count+1}）"
        
        if title in existing or title in seen:
            continue
        seen.add(title)
        
        # Create QA
        qa = QA(
            user_id=SYSTEM_USER_ID,
            title=title,
            content=tmpl[1],
            tags=[cat[0], sub],
            is_resolved=random.random() > 0.3,
            view_count=random.randint(50, 2000),
            answer_count=random.randint(1, 5),
        )
        db.add(qa)
        db.flush()
        
        # Create answers (3 per QA)
        for i in range(3):
            ans_batch.append(QAAnswer(
                qa_id=qa.id,
                user_id=SYSTEM_USER_ID,
                content=f"关于{sub}的建议{i+1}：制定计划+坚持执行+定期复盘。结合真题多做多练。",
                is_best=(i == 0),
                like_count=random.randint(0, 30),
            ))
        count += 1
        
        if count % 1000 == 0:
            db.flush()
            print(f"    已生成 {count}/{needed}...")
    
    db.bulk_save_objects(ans_batch)
    db.commit()
    print(f"  问答: 新增 {count} 条, 回答: 新增 {len(ans_batch)} 条")
    return count, len(ans_batch)

def main():
    print("=" * 50)
    print("优化版批量生成脚本 — 目标50,000条")
    print("=" * 50)
    
    db = SessionLocal()
    start = time.time()
    try:
        # Ensure system user
        user = db.query(User).filter(User.id == SYSTEM_USER_ID).first()
        if not user:
            user = User(id=SYSTEM_USER_ID, email="system@gradpath.local", name="系统", password_hash="")
            db.add(user)
            db.commit()
        
        # 1. 院校情报 → 10,000
        print("\n1. 院校情报...")
        gen_intel_batch(db, target_new=10000)
        
        # 2. 问答+回答 → 10,000问答+30,000回答
        print("\n2. 问答+回答...")
        qa_count, ans_count = gen_qa_batch(db, target_new=10000)
        
        elapsed = time.time() - start
        print(f"\n总耗时: {elapsed:.1f}秒")
        
        # Final counts
        print("\n" + "=" * 50)
        print("最终DB数据量")
        print("=" * 50)
        total = 0
        tables = [
            ("experience_posts", "经验帖"), ("knowledge_articles", "知识文章"),
            ("schools", "院校"), ("qas", "问答"), ("qa_answers", "回答"),
            ("dark_knowledge", "暗知识"), ("grad_school_intel", "院校情报"),
            ("grad_scoreline_records", "分数线"), ("companies", "公司"),
            ("salary_benchmarks", "薪资基准"),
        ]
        for t, l in tables:
            r = db.execute(text(f"SELECT COUNT(*) FROM {t}"))
            c = r.scalar()
            total += c
            print(f"  {l:8s}: {c}")
        print(f"\n  总计: {total}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback; traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
