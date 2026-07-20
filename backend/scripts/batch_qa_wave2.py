# -*- coding: utf-8 -*-
"""第二波问答+回答批量插入"""
import sys, random, uuid, time, json
sys.stdout.reconfigure(encoding='utf-8')
random.seed(99)

import psycopg2
conn = psycopg2.connect("postgresql://gradpath:gradpath123@db:5432/gradpath")
cur = conn.cursor()
SYSTEM_USER = "00000000-0000-0000-0000-000000000000"

start = time.time()

# ===== 1. 新增5000问答 =====
print("1. 新增问答...")
cur.execute("SELECT title FROM qas")
existing = set(r[0] for r in cur.fetchall())

CATS = [
    ("专业课408", ["数据结构","操作系统","计算机网络","组成原理","算法","编译原理","软件工程","数据库"]),
    ("考研数学", ["高数上册","高数下册","线性代数","概率论","数学建模","数值分析"]),
    ("考研英语", ["阅读A","阅读B","完形填空","翻译","大小作文","词汇","长难句","新题型"]),
    ("考研政治", ["马原唯物论","马原辩证法","毛中特","近代史","思修法基","时政热点"]),
    ("复试准备", ["英语听力","英语口语","专业课笔试","综合面试","导师邮件","简历优化","实验技能","政治面貌"]),
    ("调剂策略", ["调剂系统操作","B区院校","科研院所调剂","调剂时间线","调剂邮件","调剂面试","调剂心态"]),
    ("择校分析", ["985内部对比","211性价比","双一流新兴","地域选择","专业排名","学硕专硕","非全选择","中外合作"]),
    ("心态管理", ["考前焦虑","考中紧张","考后等待","出分崩溃","调剂绝望","二战孤独","家庭压力","同辈比较"]),
    ("时间规划", ["大三规划","暑假规划","秋季冲刺","考前一个月","考后规划","复试时间线","调剂时间线","毕业论文"]),
    ("跨考攻略", ["跨计算机","跨金融","跨法学","跨教育","跨新闻","跨心理学","跨会计","跨行政管理"]),
    ("在职考研", ["时间管理","精力分配","单位沟通","面试技巧","毕业论文","学费投资","学历提升","职业转型"]),
    ("备考资源", ["网课选择","资料购买","真题获取","答疑渠道","自习室","研友选择","APP推荐","公众号"]),
]

TEMPLATES = [
    ("{cat}的{sub}怎么高效复习？", "核心方法：1）先通读教材建立框架；2）重点章节精读；3）真题反复做；4）错题本归纳。效率>时长。"),
    ("{cat}{sub}有什么好的参考书？", "参考书推荐：1）教育部大纲指定书；2）历年真题解析；3）名师讲义；4）学长学姐笔记。不要贪多。"),
    ("{cat}{sub}的复习顺序怎么安排？", "建议按知识体系逻辑：先基础后应用，先重点后次要。每天固定时间段复习，保持节奏。"),
    ("{cat}{sub}真题怎么利用？", "真题是最好的复习资料：1）第一遍了解题型；2）第二遍精做分析；3）第三遍查漏补缺。"),
    ("{cat}{sub}冲刺阶段怎么复习？", "冲刺期重点：1）回顾错题；2）模拟考试找感觉；3）查漏补缺；4）调整心态。"),
    ("{cat}{sub}最容易犯的错误？", "常见错误：1）只看不练；2）不做真题；3）忽视基础；4）题海战术无总结；5）心态崩了就放弃。"),
    ("{cat}{sub}多少分算高分？", "因校因专业而异。一般来说：985热门专业380+算高分，211专业350+算高分。"),
    ("{cat}{sub}有没有速成方法？", "没有真正的速成。但可以：1）抓重点；2）做真题；3）背核心知识点；4）找学长学姐经验。"),
    ("跨考{sub}需要注意什么？", "跨考要点：1）提前补专业课基础；2）了解目标院校是否歧视跨考；3）找真题和参考书；4）联系在读学长学姐。"),
    ("{cat}{sub}和就业怎么平衡？", "平衡策略：1）确定优先级；2）制定时间表；3）碎片时间利用；4）保持健康作息。"),
    ("{cat}{sub}的复习资料在哪里找？", "资料渠道：1）目标院校官网；2）考研帮/知乎；3）学长学姐；4）网课平台；5）淘宝/京东。"),
    ("{cat}{sub}每天需要多少小时？", "因人而异。一般建议：基础阶段4-6h，强化阶段6-8h，冲刺阶段8-10h。关键是效率。"),
]

CAT_NAMES = [c[0] for c in CATS]
CAT_SUBS = {c[0]: c[1] for c in CATS}

qa_rows = []
seen = set()
count = 0
needed = 5000

while count < needed:
    cat = random.choice(CAT_NAMES)
    sub = random.choice(CAT_SUBS[cat])
    tmpl = random.choice(TEMPLATES)
    title = tmpl[0].format(cat=cat, sub=sub) + f"（第二波{count+1}）"
    
    if title in existing or title in seen:
        continue
    seen.add(title)
    
    rid = str(uuid.uuid4())
    tags = json.dumps([cat, sub], ensure_ascii=False)
    cur.execute(
        "INSERT INTO qas (id,user_id,title,content,tags,status,view_count,answer_count,is_resolved,created_at,updated_at) VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,now(),now())",
        (rid, SYSTEM_USER, title, tmpl[1], tags, "approved", random.randint(50,3000), random.randint(1,5), random.random() > 0.3)
    )
    count += 1
    
    if count % 1000 == 0:
        conn.commit()
        print(f"  已插入 {count}/{needed}...")

conn.commit()
cur.execute("SELECT COUNT(*) FROM qas")
qa_total = cur.fetchone()[0]
print(f"问答新增: {count} 条 (总计 {qa_total})")

# ===== 2. 为新问答插入回答 =====
print("\n2. 为新问答插入回答...")
cur.execute("SELECT id::text FROM qas ORDER BY created_at DESC LIMIT 5000")
qa_ids = [r[0] for r in cur.fetchall()]

ans_count = 0
for qa_id in qa_ids:
    for j in range(3):
        rid = str(uuid.uuid4())
        try:
            cur.execute(
                "INSERT INTO qa_answers (id,qa_id,user_id,content,is_best,like_count,status,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,'approved',now(),now())",
                (rid, qa_id, SYSTEM_USER, f"建议{j+1}：制定计划+执行+复盘。参考高分经验，结合真题多做多练。", j == 0, random.randint(0,30))
            )
            ans_count += 1
        except:
            pass
    if ans_count % 5000 == 0 and ans_count > 0:
        conn.commit()
        print(f"  已插入 {ans_count} 回答...")
conn.commit()

elapsed = time.time() - start
cur.execute("SELECT COUNT(*) FROM qa_answers")
ans_total = cur.fetchone()[0]
print(f"回答新增: {ans_count} 条 (总计 {ans_total})")
print(f"耗时: {elapsed:.1f}秒")

# ===== Final =====
print("\n最终DB数据量:")
total = 0
for t, l in [("experience_posts","经验帖"),("knowledge_articles","知识文章"),("schools","院校"),
             ("qas","问答"),("qa_answers","回答"),("dark_knowledge","暗知识"),
             ("grad_school_intel","院校情报"),("grad_scoreline_records","分数线"),
             ("companies","公司"),("salary_benchmarks","薪资基准")]:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    c = cur.fetchone()[0]; total += c
    print(f"  {l}: {c}")
print(f"\n  总计: {total}")
conn.close()
