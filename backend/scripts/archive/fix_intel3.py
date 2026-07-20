import random, uuid
from sqlalchemy import text
from app.database import engine
unis = ['清华大学','北京大学','浙江大学','复旦大学','上海交通大学','南京大学','武汉大学','华中科技大学','中山大学','北京师范大学']
majors = ['计算机','电子信息','机械','金融','法学','教育','医学','工商管理','中文','数学','物理','化学','生物','英语','历史']
tiers = ['985','211','双一流','普通本科']
suppressions = ['none','light','moderate','heavy']
with engine.connect() as conn:
    uid = conn.execute(text("SELECT id FROM users LIMIT 1")).scalar()
    print(f'Using user_id: {uid}')
    count = 0
    for _ in range(20000):
        uni = random.choice(unis)
        maj = random.choice(majors)
        yr = random.randint(2020, 2026)
        conn.execute(text("""
            INSERT INTO grad_school_intel (id, user_id, school_name, major_name, school_tier, year,
                background_discrimination, first_choice_protection, score_suppression, transfer_friendly,
                data_sources, tags, is_ai_generated, created_at, updated_at)
            VALUES (gen_random_uuid(), :uid, :uni, :maj, :tier, :yr, :bd, :fcp, :ss, :tf,
                CAST(:ds AS jsonb), CAST(:tags AS jsonb), false, NOW(), NOW())
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
    print(f'Added {count}, total: {total}')
