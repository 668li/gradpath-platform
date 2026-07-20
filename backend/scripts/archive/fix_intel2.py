import random, uuid
from sqlalchemy import text
from app.database import engine
unis = ['清华大学','北京大学','浙江大学','复旦大学','上海交通大学','南京大学','武汉大学','华中科技大学','中山大学','北京师范大学']
majors = ['计算机','电子信息','机械','金融','法学','教育','医学','工商管理','中文','数学','物理','化学','生物','英语','历史']
# get a valid user_id first
with engine.connect() as conn:
    uid = conn.execute(text("SELECT id FROM users LIMIT 1")).scalar()
    if not uid:
        uid = str(uuid.uuid4())
        conn.execute(text("INSERT INTO users (id, username, email, hashed_password, created_at) VALUES (:id, :u, :e, :p, NOW())"), {'id': uid, 'u': 'seed_user', 'e': 'seed@test.com', 'p': 'x'})
        conn.commit()
    print(f'Using user_id: {uid}')
    count = 0
    for _ in range(20000):
        uni = random.choice(unis)
        maj = random.choice(majors)
        yr = random.randint(2020, 2026)
        conn.execute(text("INSERT INTO grad_school_intel (id, user_id, school_name, major_name, year, background_discrimination, first_choice_protection, score_line, transfer_friendly, data_sources, tags, created_at, updated_at) VALUES (gen_random_uuid(), :uid, :uni, :maj, :yr, :bd, :fcp, :sl, :af, CAST(:ds AS jsonb), CAST(:tags AS jsonb), NOW(), NOW())"),
            {'uid': uid, 'uni': uni, 'maj': maj, 'yr': yr, 'bd': random.choice(['none','light','medium','heavy']), 'fcp': random.choice(['yes','no','partial']), 'sl': random.randint(300, 400), 'af': random.choice(['friendly','normal','unfriendly']), 'ds': '["gen3"]', 'tags': '[]'})
        count += 1
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM grad_school_intel')).scalar()
    print(f'Added {count}, total: {total}')
