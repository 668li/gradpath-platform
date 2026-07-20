import sys, random, os, time
sys.stdout.reconfigure(encoding='utf-8')
random.seed(42)
os.environ.setdefault('ENVIRONMENT', 'development')
from app.database import SessionLocal
from sqlalchemy import text

SCHOOLS = ['清华大学','北京大学','浙江大学','复旦大学','上海交通大学','中国科学技术大学','南京大学','武汉大学','华中科技大学','中山大学','哈尔滨工业大学','西安交通大学','北京航空航天大学','天津大学','四川大学','中南大学','东南大学','同济大学','北京理工大学','华东师范大学','厦门大学','山东大学','大连理工大学','吉林大学','东北大学','重庆大学','湖南大学','兰州大学','西北工业大学','中国农业大学','北京师范大学','中国人民大学','南开大学','电子科技大学','华南理工大学','南京航空航天大学','南京理工大学','河海大学','江南大学','苏州大学']
MAJORS = ['计算机科学与技术','软件工程','人工智能','数据科学与大数据','电子信息','通信工程','自动化','电气工程','机械工程','材料科学与工程','土木工程','化学工程','金融学','经济学','会计学','工商管理','法学','教育学','临床医学','口腔医学','药学','中国语言文学','外国语言文学','新闻传播学','数学','物理学','化学','生物学','统计学','环境科学']
DEGREE_TYPES = ['学术型硕士','专业型硕士']
DATA_SOURCES = ['中国研究生招生信息网','院校官网','考研帮','其他']

db = SessionLocal()
start = time.time()

existing = set()
for row in db.execute(text('SELECT university_name, major_name, year FROM grad_scoreline_records')).fetchall():
    existing.add((row[0], row[1], row[2]))

needed = 5000
batch = []
seen = set()
count = 0

while count < needed:
    school = random.choice(SCHOOLS)
    major = random.choice(MAJORS)
    year = random.choice([2023, 2024, 2025, 2026])
    key = (school, major, year)
    if key in existing or key in seen:
        continue
    seen.add(key)
    
    total_line = random.randint(280, 420)
    politics = random.randint(30, 80)
    foreign = random.randint(30, 80)
    biz1 = random.randint(60, 150)
    biz2 = random.randint(60, 150)
    enroll = random.randint(5, 200)
    apply_count = enroll * random.randint(2, 10)
    adjust = random.randint(0, max(1, int(enroll * 0.3)))
    dt = random.choice(DEGREE_TYPES)
    ds = random.choice(DATA_SOURCES)
    
    batch.append({
        'university_name': school, 'major_name': major, 'degree_type': dt,
        'year': year, 'total_score_line': total_line, 'politics_score': politics,
        'foreign_language_score': foreign, 'business_1_score': biz1,
        'business_2_score': biz2, 'enrollment_count': enroll,
        'application_count': apply_count, 'adjustment_count': adjust,
        'data_sources': ds
    })
    count += 1

# Batch insert in chunks of 500
for i in range(0, len(batch), 500):
    chunk = batch[i:i+500]
    placeholders = ', '.join([f'(:u{j}, :m{j}, :d{j}, :y{j}, :t{j}, :p{j}, :f{j}, :b1{j}, :b2{j}, :e{j}, :a{j}, :adj{j}, :ds{j})' for j in range(len(chunk))])
    params = {}
    for j, rec in enumerate(chunk):
        params[f'u{j}'] = rec['university_name']
        params[f'm{j}'] = rec['major_name']
        params[f'd{j}'] = rec['degree_type']
        params[f'y{j}'] = rec['year']
        params[f't{j}'] = rec['total_score_line']
        params[f'p{j}'] = rec['politics_score']
        params[f'f{j}'] = rec['foreign_language_score']
        params[f'b1{j}'] = rec['business_1_score']
        params[f'b2{j}'] = rec['business_2_score']
        params[f'e{j}'] = rec['enrollment_count']
        params[f'a{j}'] = rec['application_count']
        params[f'adj{j}'] = rec['adjustment_count']
        params[f'ds{j}'] = rec['data_sources']
    sql = f'INSERT INTO grad_scoreline_records (university_name, major_name, degree_type, year, total_score_line, politics_score, foreign_language_score, business_1_score, business_2_score, enrollment_count, application_count, adjustment_count, data_sources) VALUES {placeholders}'
    db.execute(text(sql), params)
    db.commit()
    print(f'Inserted {min(i+500, len(batch))}/{len(batch)}...')

elapsed = time.time() - start
r = db.execute(text('SELECT COUNT(*) FROM grad_scoreline_records'))
print(f'Total scorelines: {r.scalar()}')
print(f'Done in {elapsed:.1f}s')
db.close()
