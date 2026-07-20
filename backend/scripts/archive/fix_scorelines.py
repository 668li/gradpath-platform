import random, uuid
from sqlalchemy import text
from app.database import engine
unis = ['清华大学','北京大学','浙江大学','复旦大学','上海交通大学','南京大学','武汉大学','华中科技大学','中山大学','北京师范大学','同济大学','南开大学','四川大学','山东大学','厦门大学','兰州大学','吉林大学','大连理工大学','重庆大学','哈尔滨工业大学']
majors = ['计算机','电子信息','机械','金融','法学','教育','医学','工商管理','中文','数学','物理','化学','生物','英语','历史','哲学','艺术','新闻','公共管理','农业']
with engine.connect() as conn:
    count = 0
    for _ in range(20000):
        base = random.randint(290, 390)
        conn.execute(text('INSERT INTO grad_scoreline_records (id, university_name, major_name, year, total_score_line, politics_score, foreign_language_score, business_1_score, business_2_score, data_sources, created_at, updated_at) VALUES (gen_random_uuid(), :uni, :maj, :yr, :tl, :pol, :eng, :m1, :m2, CAST(:ds AS jsonb), NOW(), NOW())'),
            {'uni': random.choice(unis), 'maj': random.choice(majors), 'yr': random.randint(2020, 2026), 'tl': base, 'pol': random.randint(45, 60), 'eng': random.randint(45, 60), 'm1': random.randint(70, 130), 'm2': random.randint(70, 130), 'ds': '["gen3"]'})
        count += 1
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM grad_scoreline_records')).scalar()
    print(f'Added {count}, total: {total}')
