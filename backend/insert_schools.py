import random
import uuid
import unicodedata
from sqlalchemy import text
from app.database import engine

levels = ['985','211','双一流','普通本科','高职高专']
provinces = ['北京','上海','广东','浙江','江苏','四川','湖北','山东','河南','河北','湖南','安徽','福建','江西','辽宁','吉林','黑龙江','陕西','甘肃','云南','贵州','广西','海南','山西','内蒙古','宁夏','青海','新疆','西藏','重庆','天津']

regions = ['华东','华南','华北','西南','东北','中南','西北']
fields = ['理工','师范','科技','工商','财经','政法','医科','农业','林业','体育']
suffixes = ['大学','学院','职业技术学院']

def to_pinyin_initials(name):
    result = ''
    for ch in name:
        if '\u4e00' <= ch <= '\u9fff':
            result += ch
        elif ch.isascii() and ch.isalnum():
            result += ch
    return result[:10].lower() if result else 'uni'

with engine.connect() as conn:
    count = 0
    for i in range(1500):
        base = random.choice(regions) + random.choice(fields) + random.choice(suffixes)
        name = base + str(i)
        slug = f"uni-{uuid.uuid4().hex[:8]}"
        code = f"{random.randint(10000,99999)}"
        province = random.choice(provinces)
        level = random.choice(levels)
        conn.execute(text(
            "INSERT INTO schools (id, name, slug, code, province, level, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :name, :slug, :code, :province, :level, NOW(), NOW())"
        ), {'name': name, 'slug': slug, 'code': code, 'province': province, 'level': level})
        count += 1
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM schools')).scalar()
    print(f'Added {count} schools, total: {total}')
