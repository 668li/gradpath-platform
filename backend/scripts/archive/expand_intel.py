import random, uuid
from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    existing_unis = [r[0] for r in conn.execute(text('SELECT DISTINCT school_name FROM grad_school_intel')).fetchall()]
    existing_majors = [r[0] for r in conn.execute(text('SELECT DISTINCT major_name FROM grad_school_intel')).fetchall()]
    print(f'Existing schools: {len(existing_unis)}, majors: {len(existing_majors)}')

# Add some extra schools/majors if pool is small
extra_unis = ['西华大学','成都理工大学','西南财经大学','西南交通大学','电子科技大学','北京理工大学','北京航空航天大学','中国农业大学','中央民族大学','中国政法大学','对外经济贸易大学','北京邮电大学','北京科技大学','北京工业大学','首都师范大学','华北电力大学','天津大学','天津师范大学','河北大学','燕山大学','太原理工大学','内蒙古大学','东北大学','东北师范大学','延边大学','哈尔滨工程大学','东北林业大学','东北农业大学','华东理工大学','华东师范大学','上海大学','上海师范大学','上海财经大学','上海外国语大学','东华大学','河海大学','南京航空航天大学','南京理工大学','南京农业大学','中国矿业大学','江南大学','苏州大学','南京师范大学','中国药科大学','合肥工业大学','安徽大学','安徽师范大学','福州大学','南昌大学','中国海洋大学','中国石油大学','郑州大学','武汉理工大学','华中农业大学','华中师范大学','中南大学','湖南大学','湖南师范大学','国防科技大学','暨南大学','华南理工大学','华南师范大学','广西大学','海南大学','西南大学','西南财经大学','西南政法大学','贵州大学','云南大学','西藏大学','西北大学','西安交通大学','西北工业大学','西安电子科技大学','长安大学','西北农林科技大学','陕西师范大学','兰州大学','青海大学','宁夏大学','新疆大学','石河子大学']
extra_majors = ['物理','化学','生物','数学','统计','材料','化工','环境','地理','历史','哲学','政治','经济','新闻','艺术','音乐','美术','体育','外语','翻译','护理','药学','农学','林学','畜牧','兽医','食品','纺织','轻工','矿业','冶金','测控','自动化','通信','微电子','光学','力学','热能','核能','水利','测绘','建筑','城乡规划','风景园林','船舶','航空','兵器','核工程','生物医学','安全','物流','电子商务','旅游管理','公共管理','行政管理','社会学','人类学','考古学','天文学','大气科学','海洋科学','地球物理','地质学','生态学','遗传学','细胞生物','神经科学','人工智能','大数据','网络安全','机器人','智能制造','新能源','储能','集成电路','量子信息','空天信息']

all_unis = list(set(existing_unis + extra_unis))
all_majors = list(set(existing_majors + extra_majors))
print(f'Total schools pool: {len(all_unis)}, majors pool: {len(all_majors)}')

tiers = ['985','211','双一流','普通']
admission_ratios = ['5%','10%','15%','20%','25%','30%','35%','40%']
push_ratios = ['10%','20%','30%','40%','50%','60%','70%','80%']
retest_weights = ['30%','35%','40%','45%','50%','55%','60%','65%','70%']
retest_formats = ['笔试','面试','笔试+面试','综合考核','机试','实验考核']
score_suppressions = ['是','否']
transfer_friendlies = ['友好','一般','不友好']

# Build existing combos to avoid unique constraint violations
existing_combos = set()
with engine.connect() as conn:
    rows = conn.execute(text('SELECT school_name, major_name, year FROM grad_school_intel')).fetchall()
    for r in rows:
        existing_combos.add((r[0], r[1], r[2]))
    print(f'Existing combos: {len(existing_combos)}')

SQL = """INSERT INTO grad_school_intel (id, user_id, school_name, major_name, school_tier, year, background_discrimination, first_choice_protection, admission_ratio, push_ratio, actual_quota, score_line, retest_weight, retest_format, score_suppression, transfer_friendly, insider_notes, data_sources, tags, ai_summary, is_ai_generated, created_at, updated_at) VALUES (gen_random_uuid(), '00000000-0000-0000-0000-000000000000', :uni, :maj, :tier, :yr, :bd, :fcp, :ar, :pr, :aq, :sl, :rw, :rf, :ss, :tf, :notes, :ds, :tags, :summary, true, NOW(), NOW())"""

years = list(range(2020, 2027))
attempt = 0
max_attempts = 50000

with engine.connect() as conn:
    count = 0
    while count < 20000 and attempt < max_attempts:
        attempt += 1
        uni = random.choice(all_unis)
        maj = random.choice(all_majors)
        yr = random.choice(years)
        
        if (uni, maj, yr) in existing_combos:
            continue
        
        existing_combos.add((uni, maj, yr))
        
        conn.execute(text(SQL), {
            'uni': uni, 'maj': maj, 'tier': random.choice(tiers), 'yr': yr,
            'bd': random.choice(['无','轻度','中度','严重']),
            'fcp': random.choice(['是','否','部分保护']),
            'ar': random.choice(admission_ratios),
            'pr': random.choice(push_ratios),
            'aq': random.randint(5, 100),
            'sl': random.randint(300, 400),
            'rw': random.choice(retest_weights),
            'rf': random.choice(retest_formats),
            'ss': random.choice(score_suppressions),
            'tf': random.choice(transfer_friendlies),
            'notes': 'generated data',
            'ds': '["generated"]',
            'tags': '["intel"]',
            'summary': f'{uni}{maj}{yr}年考研情报'
        })
        count += 1
        if count % 5000 == 0:
            conn.commit()
            print(f'Progress: {count}')
    
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM grad_school_intel')).scalar()
    print(f'Added {count}, attempts {attempt}, total: {total}')
