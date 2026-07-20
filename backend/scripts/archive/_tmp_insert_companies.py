import random, uuid
from sqlalchemy import text
from app.database import engine

industries = ['IT','金融','教育','医疗','制造','零售','物流','餐饮','能源','传媒','法律','建筑','农业','旅游','体育','汽车','航空','石化','通信','矿业']
cities = ['北京','上海','广州','深圳','杭州','成都','武汉','南京','苏州','西安']
stages = ['startup','growth','mature','public']
sizes = ['startup','small','medium','large','giant']

with engine.connect() as conn:
    count = 0
    for _ in range(7000):
        prefix = random.choice(['鑫','瑞','恒','博','达','盛','泰','创','智','新','华','正','安','康','诚','光','远','宏','宇','翔'])
        mid = random.choice(['通','信','达','创','科','技','智','联','盛','拓','合','德','佳','优','朗','飞','翼','云','星','芯'])
        suffix = random.choice(['科技','信息','教育','医疗','金融','智造','数据','云','网络','智能','互联','数科','软件','物联','视界'])
        uid = uuid.uuid4().hex[:6]
        name = f'{prefix}{mid}{suffix}-{uid}'
        conn.execute(text('INSERT INTO companies (id, name, industry, size, stage, headquarters, description, created_at, updated_at) VALUES (:id, :name, :ind, :size, :stage, :hq, :desc, NOW(), NOW())'),
            {'id': str(uuid.uuid4()), 'name': name, 'ind': random.choice(industries), 'size': random.choice(sizes), 'stage': random.choice(stages), 'hq': random.choice(cities), 'desc': f'{name}是一家{random.choice(industries)}领域的企业'})
        count += 1
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM companies')).scalar()
    print(f'Added {count} companies, total: {total}')
