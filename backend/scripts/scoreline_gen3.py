#!/usr/bin/env python3
import random, os, time
random.seed(42)
os.environ.setdefault('ENVIRONMENT', 'development')
from app.database import SessionLocal
from sqlalchemy import text

SCHOOLS = ['清华大学','北京大学','浙江大学','复旦大学','上海交通大学','中国科学技术大学','南京大学','武汉大学','华中科技大学','中山大学','哈尔滨工业大学','西安交通大学','北京航空航天大学','天津大学','四川大学','中南大学','东南大学','同济大学','北京理工大学','华东师范大学','厦门大学','山东大学','大连理工大学','吉林大学','东北大学','重庆大学','湖南大学','兰州大学','西北工业大学','中国农业大学','北京师范大学','中国人民大学','南开大学','电子科技大学','华南理工大学','南京航空航天大学','南京理工大学','河海大学','江南大学','苏州大学','华东理工大学','北京交通大学','北京化工大学','华北电力大学','中国矿业大学','上海大学','合肥工业大学','福州大学','南昌大学','郑州大学','武汉理工大学','华中农业大学','华中师范大学','暨南大学','华南师范大学','广西大学','西南大学','西南交通大学','云南大学','西北大学','长安大学','西安电子科技大学','陕西师范大学','延边大学','海南大学','太原理工大学','辽宁大学','东北师范大学','南方科技大学','上海科技大学','中国科学院大学','湘潭大学','广州医科大学','华南农业大学','宁波大学','南京医科大学','首都医科大学','西湖大学','河南大学','山西大学','杭州电子科技大学','深圳大学','广东工业大学']
MAJORS = ['计算机科学与技术','软件工程','人工智能','数据科学与大数据','电子信息','通信工程','自动化','电气工程','机械工程','材料科学与工程','土木工程','化学工程','金融学','经济学','会计学','工商管理','法学','教育学','临床医学','口腔医学','药学','中国语言文学','外国语言文学','新闻传播学','数学','物理学','化学','生物学','统计学','环境科学','公共管理','政治学','图书馆学','马克思主义理论','护理学','艺术设计','广播电视编导']
DEGREE_TYPES = ['学术型硕士','专业型硕士']
YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
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
    year = random.choice(YEARS)
    key = (school, major, year)
    if key in existing or key in seen:
        continue
    seen.add(key)
    batch.append((school, major, random.choice(DEGREE_TYPES), year,
                  random.randint(280, 420), random.randint(30, 80),
                  random.randint(30, 80), random.randint(60, 150),
                  random.randint(60, 150), random.randint(5, 200),
                  random.randint(100, 1000), random.randint(0, 30),
                  random.choice(DATA_SOURCES)))
    count += 1

for i in range(0, len(batch), 200):
    chunk = batch[i:i+200]
    values = []
    params = {}
    for j, rec in enumerate(chunk):
        values.append(f'(:u{j}, :m{j}, :d{j}, :y{j}, :t{j}, :p{j}, :f{j}, :b1{j}, :b2{j}, :e{j}, :a{j}, :adj{j}, :ds{j})')
        params[f'u{j}'] = rec[0]
        params[f'm{j}'] = rec[1]
        params[f'd{j}'] = rec[2]
        params[f'y{j}'] = rec[3]
        params[f't{j}'] = rec[4]
        params[f'p{j}'] = rec[5]
        params[f'f{j}'] = rec[6]
        params[f'b1{j}'] = rec[7]
        params[f'b2{j}'] = rec[8]
        params[f'e{j}'] = rec[9]
        params[f'a{j}'] = rec[10]
        params[f'adj{j}'] = rec[11]
        params[f'ds{j}'] = rec[12]
    sql = f"INSERT INTO grad_scoreline_records (university_name, major_name, degree_type, year, total_score_line, politics_score, foreign_language_score, business_1_score, business_2_score, enrollment_count, application_count, adjustment_count, data_sources) VALUES ({', '.join(values)})"
    db.execute(text(sql), params)
    db.commit()

elapsed = time.time() - start
r = db.execute(text('SELECT COUNT(*) FROM grad_scoreline_records'))
print(f"Inserted: {len(batch)}, Total scorelines: {r.scalar()}, Time: {elapsed:.1f}s")
db.close()
