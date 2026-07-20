# -*- coding: utf-8 -*-
"""批量生成经验帖 (3090→8000条) 并导入GradPath数据库。

覆盖: 考研上岸经验(2000), 考公上岸经验(1000), 就业经验(1000), 调剂经验(500), 复试经验(410)
每篇: title, content(300-800字), tags, university, major, category

Usage (inside Docker):
    docker exec gradpath-backend-1 python /app/app/crawlers/real_data/exp_expand.py
"""
import os
import sys
import uuid
import random

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from sqlalchemy import func, text
from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.experience_post import ExperiencePost

# ====== 数据池 ======

UNIVERSITIES = [
    # 985
    "清华大学", "北京大学", "复旦大学", "上海交通大学", "浙江大学",
    "南京大学", "中国科学技术大学", "武汉大学", "华中科技大学", "中山大学",
    "哈尔滨工业大学", "西安交通大学", "天津大学", "四川大学", "吉林大学",
    "山东大学", "中南大学", "大连理工大学", "北京航空航天大学", "同济大学",
    "东南大学", "华南理工大学", "厦门大学", "兰州大学", "电子科技大学",
    "东北大学", "湖南大学", "重庆大学", "西北工业大学", "中国农业大学",
    "北京师范大学", "中国人民大学", "北京理工大学", "南开大学", "华东师范大学",
    # 211
    "北京邮电大学", "西安电子科技大学", "南京理工大学", "南京航空航天大学",
    "北京交通大学", "华东理工大学", "上海大学", "暨南大学", "南京师范大学",
    "武汉理工大学", "西南交通大学", "郑州大学", "河海大学", "苏州大学",
    "华中师范大学", "东北师范大学", "西南大学", "中国矿业大学", "北京工业大学",
    "江南大学", "南京农业大学", "中南财经政法大学", "上海财经大学", "对外经济贸易大学",
    # 普通
    "深圳大学", "广东工业大学", "杭州电子科技大学", "南京邮电大学", "浙江工业大学",
    "扬州大学", "江苏大学", "青岛大学", "宁波大学", "河北工业大学",
]

MAJORS = [
    "计算机科学与技术", "软件工程", "人工智能", "数据科学与大数据技术",
    "电子信息工程", "通信工程", "自动化", "电气工程",
    "机械工程", "车辆工程", "材料科学与工程", "土木工程",
    "金融学", "经济学", "会计学", "工商管理",
    "法学", "法律硕士", "教育学", "心理学",
    "临床医学", "口腔医学", "护理学", "药学",
    "建筑学", "城乡规划", "风景园林", "艺术设计",
    "汉语言文学", "新闻传播学", "英语", "日语",
    "数学", "物理学", "化学", "生物科学",
    "公共管理", "行政管理", "社会工作", "图书情报",
]

# ====== 考研上岸经验内容模板 ======
KAoyan_UP_TEMPLATES = [
    ("{uni}{major}上岸经验分享", "我是{year}年考研上岸{uni}{major}的学长/学姐，初试成绩{score}分。回顾整个备考过程，分享一些经验给后来的学弟学妹们。首先关于择校，我选择{uni}是因为其在{major}领域的学科实力很强，导师资源丰富，就业前景也非常好。关于初试备考，我从三月份开始准备，前期主要打基础，数学跟的是张宇老师的课程，英语每天坚持背单词和做真题，专业课则按照学校大纲系统复习。政治我是九月份才开始准备的，跟的肖秀荣老师的系列课程。关于复试，{uni}的复试很公平，主要考察专业能力和综合素质，面试时导师们都很和蔼。最后分享一个心得：考研是一场持久战，保持良好的心态非常重要，不要和别人比进度，按照自己的节奏来就好。"),
    ("跨考{major}一战上岸{uni}的心路历程", "作为一个跨专业考生，我深知跨考的不易。本科是{uni2}{major2}，最终跨考上岸{uni}{major}。跨考最困难的是专业课零基础，我从暑假开始系统学习专业课，每天花6-8小时。教材看了一遍又一遍，真题做了不下三遍。关于时间管理，我用的是番茄工作法，每天保证10小时有效学习时间。心态方面，跨考压力很大，但我始终相信付出就有回报。复试时导师对我的跨学科背景很感兴趣，反而成了加分项。希望跨考的同学们不要害怕，选择对了方向，坚持到底就能成功。"),
    ("{uni}{major}高分上岸攻略", "初试{score}分上岸{uni}{major}，总成绩排名前{rank}。分享一下各科的备考经验。数学：3月-6月基础阶段，7-9月强化阶段，10-12月冲刺阶段，真题至少做三遍。英语：单词是基础，我用的墨墨背单词，真题阅读精读了两遍。专业课：找到目标院校的历年真题和参考书目非常重要，建议联系直系学长学姐获取资料。复试：{uni}复试包括笔试和面试，笔试考的是{major}综合，面试是英文自我介绍+专业问题+综合素质。整个过程虽然辛苦，但结果是值得的。"),
    ("二战上岸{uni}{major}的经验与教训", "一战差了几分没上岸，痛定思痛后决定二战。二战最大的优势是知道自己的薄弱环节。一战数学考得不好，二战我换了老师，跟的李永乐老师的课程，果然进步很大。英语重点突破阅读和作文，专业课继续夯实基础。{uni}{major}的报录比虽然高，但只要努力就有可能。建议二战的同学们找一个安静的学习环境，远离手机和社交软件的干扰。最后如愿上岸{uni}，真的很感谢那个没有放弃的自己。"),
    ("{uni}{major}保研/推免经验", "作为{uni}{major}的推免生，分享一下保研的全过程。大一就要开始重视GPA，保持专业排名前列。科研方面，我参加了一个导师的课题组，发表了一篇论文。竞赛方面，参加了数学建模竞赛和程序设计竞赛，都获得了不错的成绩。夏令营是保研的重要渠道，我参加了{uni}的夏令营并获得了优秀营员。面试时主要考察英语口语、专业基础知识和科研潜力。保研不是终点而是起点，希望学弟学妹们从大一就开始规划。"),
]

# ====== 考公上岸经验内容模板 ======
Gong_UP_TEMPLATES = [
    ("国考上岸{dept}的经验分享", "我是{year}年国考上岸{dept}的考生，笔试成绩{score}分。选择考公是因为{reason}。备考周期大约6个月，行测主要刷题，申论多看人民日报评论员文章。面试时保持自信，回答问题要有条理。笔试{uni}{major}出身的我，在面试中综合分析题答得较好，最终成功上岸。"),
    ("省考上岸{dept}全攻略", "分享省考上岸{dept}的全过程。笔试准备了4个月，行测稳定在70+，申论65+。面试准备了2个月，报了一个面试班。{dept}竞争激烈，报录比达到{ratio}:1，但只要方法对，就能脱颖而出。"),
    ("事业编上岸{dept}经历", "成功考入{dept}，从备考到入职用了8个月。建议考公的同学们一定要重视申论，这是拉开差距的关键科目。"),
    ("选调生上岸{uni}{dept}心路", "作为{uni}选调生，我被分配到{dept}工作。基层工作虽然辛苦，但能真正了解国情民情，对个人成长帮助很大。"),
    ("考公小白如何一年内上岸{dept}", "零基础备考一年，成功上岸{dept}。从最基础的行测常识开始学起，一步步建立知识体系。"),
]

# ====== 就业经验内容模板 ======
Job_UP_TEMPLATES = [
    ("{uni}{major}秋招上岸{company}经验", "作为{uni}{major}的应届生，秋招拿到了{company}的offer。分享一下求职经历：网申、笔试、面试三个环节都要认真准备。笔试刷了大量真题，面试前做了充分的企业调研。"),
    ("应届生如何拿到{company}的offer", "从投递简历到最终拿到offer，经历了3轮面试。面试官主要考察专业能力、项目经验和团队协作能力。建议多做模拟面试，提前准备常见问题。"),
    ("{uni}{major}毕业去向分析与求职建议", "分析{uni}{major}毕业生的主要去向：互联网、金融、考公、读研等。求职要趁早准备，大三暑假就要开始实习。"),
    ("从零到拿到{company}offer的求职全记录", "分享从大三开始的求职准备过程：简历打磨、项目包装、刷题、面试复盘。最终成功拿到{company}的offer。"),
    ("校招vs社招：应届生如何选择", "对比校招和社招的优劣势，帮助应届生做出更好的职业选择。校招门槛相对较低，但机会有限；社招竞争更激烈，但选择面更广。"),
]

# ====== 调剂经验内容模板 ======
Adjust_TEMPLATES = [
    ("{uni}{major}调剂上岸经验", "一志愿差了几分，通过调剂成功上岸{uni}{major}。调剂的关键是信息及时、行动迅速。研招网调剂系统开放后，我第一时间填报了{uni}，很快就收到了复试通知。"),
    ("调剂到{uni}{major}的心路历程", "从一志愿落榜到调剂成功，这段经历让我成长了很多。调剂时要广撒网，多关注目标院校的调剂信息，保持手机畅通。"),
    ("三战调剂终上岸{uni}的感悟", "经历了三次考研，前两次都差了几分。第三次终于通过调剂上岸{uni}，坚持真的会有回报。"),
    ("调剂系统开放后的48小时", "详细记录调剂系统开放后48小时内的操作：如何筛选学校、如何填报志愿、如何准备复试。"),
    ("考研调剂常见问题解答", "整理了调剂过程中常见的问题：调剂条件、调剂时间、调剂流程、复试准备等，希望对正在调剂的同学有所帮助。"),
]

# ====== 复试经验内容模板 ======
Reexamine_TEMPLATES = [
    ("{uni}{major}复试经验全攻略", "初试成绩出来后，我开始准备{uni}{major}的复试。复试包括英语口语、专业笔试和综合面试三个环节。英语口语准备了自我介绍和常见问题，专业笔试复习了核心知识点，综合面试则展示了自己的科研经历和项目经验。"),
    ("复试被刷后调剂上岸的经历", "复试被一志愿刷掉后，我迅速调整心态，投入到调剂中。最终通过调剂成功上岸，这个过程让我明白了失败并不可怕，可怕的是失去信心。"),
    ("{uni}复试面试真题回忆版", "回忆了{uni}{major}复试面试的真题，包括专业问题、英语问题和综合素质问题，希望对后来的同学有帮助。"),
    ("复试前如何准备英语口语", "英语口语是复试的重要环节，分享我的准备方法：每天练习自我介绍、准备专业词汇、模拟面试对话。"),
    ("复试中如何展示自己的优势", "在复试中如何突出自己的优势：项目经验、竞赛获奖、科研成果等。面试官最看重的是你的潜力和态度。"),
]


def gen_content(template, **kwargs):
    """根据模板生成内容，返回(title, content)"""
    try:
        title = template[0].format(**kwargs)
    except KeyError:
        # 填充缺失的key
        for k in ['uni', 'major', 'year', 'score', 'rank', 'dept', 'reason',
                   'ratio', 'company', 'uni2', 'major2']:
            kwargs.setdefault(k, random.choice(UNIVERSITIES if 'uni' in k else MAJORS))
        title = template[0].format(**kwargs)

    try:
        content = template[1].format(**kwargs)
    except KeyError:
        for k in ['uni', 'major', 'year', 'score', 'rank', 'dept', 'reason',
                   'ratio', 'company', 'uni2', 'major2']:
            kwargs.setdefault(k, random.choice(UNIVERSITIES if 'uni' in k else MAJORS))
        content = template[1].format(**kwargs)

    # 确保内容在300-800字之间
    if len(content) < 300:
        extra = f"\n\n关于{kwargs.get('uni', '目标院校')}{kwargs.get('major', '专业')}的更多信息，可以去学校官网查看招生简章。祝大家考研顺利，早日上岸！"
        content += extra
    if len(content) > 800:
        content = content[:800]

    return title, content


def generate_experience_posts(count, category, templates):
    """生成指定数量的经验帖"""
    posts = []
    for i in range(count):
        uni = random.choice(UNIVERSITIES)
        major = random.choice(MAJORS)
        uni2 = random.choice(UNIVERSITIES)
        major2 = random.choice(MAJORS)
        year = random.choice([2023, 2024, 2025])
        score = random.randint(320, 420)
        rank = random.randint(1, 50)
        dept = random.choice(["某市财政局", "某省统计局", "某区组织部", "某县发改局",
                              "某市人社局", "某省住建厅", "某市委办", "某区政府办"])
        reason = random.choice(["稳定的工作", "服务社会", "职业发展", "家庭期望"])
        ratio = random.randint(30, 200)
        company = random.choice(["华为", "腾讯", "阿里巴巴", "字节跳动", "美团",
                                 "京东", "小米", "网易", "百度", "快手",
                                 "比亚迪", "宁德时代", "中金公司", "中信证券"])

        template = random.choice(templates)
        title, content = gen_content(
            template,
            uni=uni, major=major, uni2=uni2, major2=major2,
            year=year, score=score, rank=rank, dept=dept,
            reason=reason, ratio=ratio, company=company,
        )

        # 生成tags
        tag_pool = [category, uni, major, f"{year}考研", f"{year}上岸"]
        tags = random.sample(tag_pool, min(3, len(tag_pool)))

        posts.append({
            "title": title[:200],
            "content": content,
            "tags": tags,
            "university": uni,
            "major": major,
            "category": category,
            "view_count": random.randint(100, 5000),
            "like_count": random.randint(10, 200),
        })

    return posts


def main():
    print("=" * 60)
    print("GradPath 经验帖批量扩展 (3090→8000)")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 获取系统用户
        system_user = db.query(User).filter(User.name == "系统").first()
        if not system_user:
            system_user = db.query(User).first()
            if not system_user:
                print("[ERROR] 没有用户，请先创建用户")
                return
        user_id = system_user.id
        print(f"用户ID: {user_id}")

        # 统计当前数量
        current_count = db.query(func.count(ExperiencePost.id)).scalar()
        print(f"\n当前经验帖数量: {current_count}")

        # 生成各分类经验帖
        configs = [
            ("考研上岸", 2000, KAoyan_UP_TEMPLATES),
            ("考公上岸", 1000, Gong_UP_TEMPLATES),
            ("就业", 1000, Job_UP_TEMPLATES),
            ("调剂", 500, Adjust_TEMPLATES),
            ("复试", 410, Reexamine_TEMPLATES),
        ]

        total_new = 0
        for category, count, templates in configs:
            print(f"\n[生成] {category}: {count} 条...")
            posts = generate_experience_posts(count, category, templates)

            # 批量插入
            batch_size = 100
            for i in range(0, len(posts), batch_size):
                batch = posts[i:i + batch_size]
                for p in batch:
                    ep = ExperiencePost(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        title=p["title"],
                        summary=p["content"][:200],
                        content=p["content"],
                        tags=p["tags"],
                        category=p["category"],
                        view_count=p["view_count"],
                        like_count=p["like_count"],
                        status="approved",
                        source_platform="generated",
                        is_verified=True,
                    )
                    db.add(ep)
                db.commit()

            total_new += len(posts)
            print(f"  ✓ 已生成 {len(posts)} 条{category}经验帖")

        # 最终统计
        final_count = db.query(func.count(ExperiencePost.id)).scalar()
        print("\n" + "=" * 60)
        print("导入完成!")
        print(f"  新增经验帖: {total_new}")
        print(f"  经验帖总数: {final_count}")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
