import random, uuid
from sqlalchemy import text
from app.database import engine
unis = ['清华大学','北京大学','浙江大学','复旦大学','上海交通大学','南京大学','武汉大学','华中科技大学','中山大学','北京师范大学','同济大学','南开大学','四川大学','山东大学','厦门大学','兰州大学','吉林大学','大连理工大学','重庆大学','哈尔滨工业大学','中南大学','湖南大学','电子科技大学','西安交通大学','东南大学','北京理工大学','华南理工大学','华东师范大学','中国农业大学','中国海洋大学','西北工业大学','东北大学','北京科技大学','北京交通大学','河海大学','南京理工大学','南京航空航天大学','西南交通大学','武汉理工大学','西安电子科技大学','华中农业大学','中国地质大学','中国矿业大学','北京化工大学','北京邮电大学','东华大学','上海大学','苏州大学','南京师范大学','郑州大学']
majors = ['计算机','电子信息','机械','金融','法学','教育','医学','工商管理','中文','数学','物理','化学','生物','英语','历史','哲学','艺术','新闻','公共管理','农业','土木','材料','环境','能源','食品','药学','护理','建筑','城市规划','园艺','水产','林学','畜牧','兽医','马克思主义','政治','社会','民族','心理','统计','力学','光学','天文','大气','海洋','地球','地理','测绘']
tiers = ['985','211','双一流','普通本科']
suppressions = ['none','light','moderate','heavy']
with engine.connect() as conn:
    uid = conn.execute(text("SELECT id FROM users LIMIT 1")).scalar()
    print(f'Using user_id: {uid}')
    # Generate all unique combos first
    combos = set()
    for _ in range(25000):
        combos.add((random.choice(unis), random.choice(majors), random.randint(2020, 2026)))
    print(f'Generated {len(combos)} unique combos')
    count = 0
    for uni, maj, yr in combos:
        conn.execute(text("""
            INSERT INTO grad_school_intel (id, user_id, school_name, major_name, school_tier, year,
                background_discrimination, first_choice_protection, score_suppression, transfer_friendly,
                data_sources, tags, is_ai_generated, created_at, updated_at)
            VALUES (gen_random_uuid(), :uid, :uni, :maj, :tier, :yr, :bd, :fcp, :ss, :tf,
                CAST(:ds AS jsonb), CAST(:tags AS jsonb), false, NOW(), NOW())
            ON CONFLICT (school_name, major_name, year) DO NOTHING
        """), {
            'uid': uid, 'uni': uni, 'maj': maj, 'tier': random.choice(tiers), 'yr': yr,
            'bd': random.choice(['none','light','medium','heavy']),
            'fcp': random.choice(['yes','no','partial']),
            'ss': random.choice(suppressions),
            'tf': random.choice(['friendly','normal','unfriendly']),
            'ds': '["gen3"]', 'tags': '[]'
        })
        count += 1
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM grad_school_intel')).scalar()
    print(f'Attempted {count}, total: {total}')
