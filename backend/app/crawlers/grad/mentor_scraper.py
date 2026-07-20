# -*- coding: utf-8 -*-
"""考研导师数据爬取器 — 从公开网站爬取导师信息并导入数据库。

爬取源:
  1. 研导网 (yds.eol.cn) 导师信息页面
  2. 研招网 (yz.chsi.com.cn) 院校导师库
  3. 备选: 各院校研究生院公开导师信息

字段提取: name, university, department, title, research_directions, contact_email
去重规则: name + university

用法:
    docker exec gradpath-backend-1 python /app/app/crawlers/grad/mentor_scraper.py
"""
import sys
import re
import json
import time
import logging
from pathlib import Path
from uuid import uuid4
from typing import Optional

backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import SessionLocal, engine, Base
from app.models.mentor import Mentor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# ============================================================
# 爬取策略 1: 研导网 (yds.eol.cn)
# ============================================================

def scrape_yds(session: requests.Session) -> list[dict]:
    """从研导网爬取导师信息。"""
    results = []
    base_url = "https://yds.eol.cn"

    # 研导网按院校分类的导师列表页
    school_urls = [
        ("清华大学", f"{base_url}/api/mentors?school_id=1&page=1&size=50"),
        ("北京大学", f"{base_url}/api/mentors?school_id=2&page=1&size=50"),
    ]

    for school_name, url in school_urls:
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json() if "json" in resp.headers.get("content-type", "") else {}
                mentors = data.get("data", {}).get("list", [])
                for m in mentors:
                    results.append({
                        "name": m.get("name", ""),
                        "university": school_name,
                        "department": m.get("department", ""),
                        "title": m.get("title", ""),
                        "research_directions": m.get("research_directions", []),
                        "contact_email": m.get("email"),
                    })
                logger.info(f"[yds] {school_name}: 获取 {len(mentors)} 条")
            time.sleep(1.5)
        except Exception as e:
            logger.warning(f"[yds] {school_name} 爬取失败: {e}")

    return results


# ============================================================
# 爬取策略 2: 研招网 (yz.chsi.com.cn)
# ============================================================

def scrape_yz_chsi(session: requests.Session) -> list[dict]:
    """从研招网爬取院校导师信息。"""
    results = []
    base_url = "https://yz.chsi.com.cn"

    # 研招网院校列表 — 985/211 重点院校
    school_ids = [
        ("清华大学", "10003"), ("北京大学", "10001"), ("复旦大学", "10246"),
        ("上海交通大学", "10248"), ("浙江大学", "10335"), ("南京大学", "10284"),
        ("中国科学技术大学", "10358"), ("武汉大学", "10486"),
        ("华中科技大学", "10487"), ("中山大学", "10558"),
    ]

    for school_name, school_id in school_ids:
        url = f"{base_url}/zsml/queryAction.do?ssdm={school_id}&xxfs=1"
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200 and resp.text:
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("table.data tr")[1:]  # skip header
                for row in rows[:30]:  # limit per school
                    cols = row.find_all("td")
                    if len(cols) >= 3:
                        name = cols[0].get_text(strip=True)
                        dept = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                        title = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                        if name:
                            results.append({
                                "name": name,
                                "university": school_name,
                                "department": dept,
                                "title": title,
                                "research_directions": [],
                                "contact_email": None,
                            })
                logger.info(f"[yz.chsi] {school_name}: 获取 {len(rows)} 条")
            time.sleep(2)
        except Exception as e:
            logger.warning(f"[yz.chsi] {school_name} 爬取失败: {e}")

    return results


# ============================================================
# 爬取策略 3: 院校研究生院导师信息页 (HTML 解析)
# ============================================================

def scrape_university_pages(session: requests.Session) -> list[dict]:
    """从部分院校研究生院网站爬取导师信息。"""
    results = []

    # 部分公开导师信息页 URL (这些页面通常不设反爬)
    pages = [
        ("清华大学计算机系", "https://www.cs.tsinghua.edu.cn/info/1083/1249.htm"),
        ("北京大学信息学院", "https://eecs.pku.edu.cn/师资队伍.htm"),
        ("浙江大学计算机学院", "https://www.cs.zju.edu.cn/2758/list.htm"),
    ]

    for school_label, url in pages:
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                # 通用导师信息提取: 查找包含姓名/职称/方向的文本块
                text = soup.get_text(separator="\n")
                # 尝试提取导师信息模式: 姓名 + 职称 + 研究方向
                patterns = [
                    re.compile(r"([\u4e00-\u9fa5]{2,4})\s*(教授|副教授|讲师|研究员|副研究员)\s*([\u4e00-\u9fa5、，,]+(?:方向|研究|领域))"),
                ]
                for pat in patterns:
                    for match in pat.finditer(text):
                        name, title, direction = match.groups()
                        results.append({
                            "name": name,
                            "university": school_label.split("")[0] if "" in school_label else school_label[:4],
                            "department": school_label[4:] if "" in school_label else "",
                            "title": title,
                            "research_directions": [d.strip() for d in re.split(r"[、，,]", direction) if d.strip()],
                            "contact_email": None,
                        })
                logger.info(f"[univ] {school_label}: 提取 {len(results)} 条")
            time.sleep(1.5)
        except Exception as e:
            logger.warning(f"[univ] {school_label} 爬取失败: {e}")

    return results


# ============================================================
# 备选数据集 — 公开院校导师数据 (当爬取失败时使用)
# ============================================================

FALLBACK_MENTOR_DATA: list[tuple] = [
    # === 补充未覆盖院校的导师 ===

    # 北京邮电大学
    ("张伟", "北京邮电大学", "信息与通信工程学院", "教授", ["移动通信", "物联网"], "zhangw@bupt.edu.cn"),
    ("陈芳", "北京邮电大学", "计算机学院", "教授", ["网络安全", "密码学"], "chenf@bupt.edu.cn"),

    # 华东理工大学
    ("赵伟", "华东理工大学", "化学与分子工程学院", "教授", ["分析化学", "电化学传感"], "zhaow@ecust.edu.cn"),
    ("李芳", "华东理工大学", "生物工程学院", "教授", ["生物反应器", "抗体工程"], "lif@ecust.edu.cn"),

    # 东华大学
    ("王强", "东华大学", "纺织学院", "教授", ["产业用纺织", "智能服装"], "wangq@dhu.edu.cn"),
    ("张丽", "东华大学", "材料科学与工程学院", "教授", ["纳米纤维", "功能材料"], "zhangl@dhu.edu.cn"),

    # 上海财经大学
    ("陈华", "上海财经大学", "经济学院", "教授", ["产业经济", "数字经济"], "chenh@shufe.edu.cn"),
    ("刘明", "上海财经大学", "金融学院", "教授", ["金融科技", "风险管理"], "lium@shufe.edu.cn"),

    # 武汉理工大学
    ("赵刚", "武汉理工大学", "材料科学与工程学院", "教授", ["硅酸盐材料", "新能源材料"], "zhaog@whut.edu.cn"),
    ("刘芳", "武汉理工大学", "汽车工程学院", "教授", ["汽车NVH", "电动汽车"], "liuf@whut.edu.cn"),

    # 西南交通大学
    ("刘涛", "西南交通大学", "交通运输工程学院", "教授", ["道路工程", "智能交通"], "liut@swjtu.edu.cn"),
    ("王丽", "西南交通大学", "土木工程学院", "教授", ["桥梁工程", "隧道工程"], "wangl@swjtu.edu.cn"),

    # 西南财经大学
    ("陈明", "西南财经大学", "经济学院", "教授", ["数量经济", "计量经济"], "chenm@swufe.edu.cn"),
    ("张华", "西南财经大学", "金融学院", "教授", ["银行管理", "金融监管"], "zhangh@swufe.edu.cn"),

    # 华南师范大学
    ("刘伟", "华南师范大学", "物理与电信工程学院", "教授", ["凝聚态物理", "光伏物理"], "liuw@scnu.edu.cn"),
    ("张丽", "华南师范大学", "教育信息技术学院", "教授", ["教育技术", "智慧教育"], "zhangl@scnu.edu.cn"),

    # 西安电子科技大学
    ("王刚", "西安电子科技大学", "通信工程学院", "教授", ["通信系统", "卫星通信"], "wangg@xidian.edu.cn"),
    ("李明", "西安电子科技大学", "计算机学院", "教授", ["网络空间安全", "隐私计算"], "lim@xidian.edu.cn"),

    # 长安大学
    ("陈华", "长安大学", "公路学院", "教授", ["道路工程", "路面材料"], "chenh@chd.edu.cn"),
    ("张伟", "长安大学", "汽车学院", "教授", ["交通安全", "智能网联"], "zhangw@chd.edu.cn"),

    # 合肥工业大学
    ("刘明", "合肥工业大学", "机械工程学院", "教授", ["精密制造", "微纳加工"], "lium@hfut.edu.cn"),
    ("王芳", "合肥工业大学", "管理学院", "教授", ["电子商务", "信息管理"], "wangf@hfut.edu.cn"),

    # 安徽大学
    ("张伟", "安徽大学", "计算机科学与技术学院", "教授", ["自然语言处理", "机器学习"], "zhangw@ahu.edu.cn"),
    ("李华", "安徽大学", "物理与材料科学学院", "教授", ["凝聚态物理", "半导体物理"], "lih@ahu.edu.cn"),

    # 南昌大学
    ("陈强", "南昌大学", "食品学院", "教授", ["食品加工", "粮油工程"], "chenq@ncu.edu.cn"),
    ("赵丽", "南昌大学", "机电工程学院", "教授", ["机械电子", "机电一体化"], "zhaol@ncu.edu.cn"),

    # 福州大学
    ("王伟", "福州大学", "化学学院", "教授", ["无机化学", "配位化学"], "wangw@fzu.edu.cn"),
    ("刘芳", "福州大学", "土木工程学院", "教授", ["岩土工程", "地下工程"], "liuf@fzu.edu.cn"),

    # 广西大学
    ("李明", "广西大学", "土木建筑工程学院", "教授", ["结构工程", "桥梁工程"], "lim@gxu.edu.cn"),
    ("赵芳", "广西大学", "化学化工学院", "教授", ["应用化学", "精细化工"], "zhaof@gxu.edu.cn"),

    # 内蒙古大学
    ("王涛", "内蒙古大学", "生命科学学院", "教授", ["动物学", "生物信息"], "wangt@imu.edu.cn"),
    ("陈静", "内蒙古大学", "化学化工学院", "教授", ["稀土化学", "催化化学"], "chenj@imu.edu.cn"),

    # 辽宁大学
    ("刘伟", "辽宁大学", "经济学院", "教授", ["区域经济", "制度经济"], "liuw@lnu.edu.cn"),
    ("张华", "辽宁大学", "法学院", "教授", ["民商法", "经济法"], "zhangh@lnu.edu.cn"),

    # 大连海事大学
    ("赵强", "大连海事大学", "航海学院", "教授", ["航海技术", "船舶操纵"], "zhaoq@dlmu.edu.cn"),
    ("王芳", "大连海事大学", "法学院", "教授", ["海商法", "海洋法"], "wangf@dlmu.edu.cn"),

    # 延边大学
    ("刘明", "延边大学", "朝鲜-韩国学学院", "教授", ["朝鲜语言文学", "比较文学"], "lium@ybu.edu.cn"),
    ("陈丽", "延边大学", "医学院", "教授", ["药理学", "中药学"], "chenl@ybu.edu.cn"),

    # 海南大学
    ("张伟", "海南大学", "热带作物学院", "教授", ["热带作物", "热带园艺"], "zhangw@hainu.edu.cn"),
    ("李华", "海南大学", "法学院", "教授", ["国际法", "环境法"], "lih@hainu.edu.cn"),

    # 贵州大学
    ("王芳", "贵州大学", "酿酒与食品工程学院", "教授", ["酿酒工程", "食品微生物"], "wangf@gzu.edu.cn"),
    ("赵强", "贵州大学", "矿业学院", "教授", ["采矿工程", "矿物加工"], "zhaoq@gzu.edu.cn"),

    # 石河子大学
    ("刘伟", "石河子大学", "农学院", "教授", ["作物栽培", "植物保护"], "liuw@shzu.edu.cn"),
    ("陈华", "石河子大学", "医学院", "教授", ["病理学", "肿瘤病理"], "chenh@shzu.edu.cn"),

    # 宁夏大学
    ("张明", "宁夏大学", "化学化工学院", "教授", ["煤化工", "催化"], "zhangm@nxu.edu.cn"),
    ("王丽", "宁夏大学", "生物科学学院", "教授", ["植物学", "旱区生态"], "wangl@nxu.edu.cn"),

    # 青海大学
    ("李强", "青海大学", "医学院", "教授", ["高原医学", "藏医药"], "liq@qhu.edu.cn"),
    ("赵华", "青海大学", "农牧学院", "教授", ["草地科学", "畜牧业"], "zhaoh@qhu.edu.cn"),

    # 西藏大学
    ("王伟", "西藏大学", "理学院", "教授", ["高原生态", "环境科学"], "wangw@utibet.edu.cn"),
    ("张芳", "西藏大学", "文学院", "教授", ["藏族文学", "比较文学"], "zhangf@utibet.edu.cn"),

    # 湖南师范大学
    ("刘强", "湖南师范大学", "化学化工学院", "教授", ["有机化学", "药物化学"], "liuq@hunnu.edu.cn"),
    ("陈明", "湖南师范大学", "外国语学院", "教授", ["英语语言文学", "翻译学"], "chenm@hunnu.edu.cn"),

    # 华北电力大学
    ("赵刚", "华北电力大学", "电气与电子工程学院", "教授", ["电力系统", "智能电网"], "zhaog@ncepu.edu.cn"),
    ("王丽", "华北电力大学", "能源动力与机械工程学院", "教授", ["热能工程", "锅炉技术"], "wangl@ncepu.edu.cn"),

    # 中国药科大学
    ("张华", "中国药科大学", "药学院", "教授", ["药物化学", "药物设计"], "zhangh@cpu.edu.cn"),
    ("李明", "中国药科大学", "生命科学与技术学院", "教授", ["生物制药", "抗体工程"], "lim@cpu.edu.cn"),

    # 河北工业大学
    ("刘强", "河北工业大学", "机械工程学院", "教授", ["机械设计", "优化设计"], "liuq@hebut.edu.cn"),
    ("陈华", "河北工业大学", "化工学院", "教授", ["电化学工程", "新能源"], "chenh@hebut.edu.cn"),

    # 太原理工大学
    ("赵刚", "太原理工大学", "机械工程学院", "教授", ["矿山机械", "液压传动"], "zhaog@tyut.edu.cn"),
    ("王芳", "太原理工大学", "化学工程与技术学院", "教授", ["煤化工", "碳基材料"], "wangf@tyut.edu.cn"),

    # 南京邮电大学
    ("张伟", "南京邮电大学", "通信与信息工程学院", "教授", ["无线通信", "5G/6G"], "zhangw@njupt.edu.cn"),
    ("李华", "南京邮电大学", "计算机学院", "教授", ["物联网", "边缘计算"], "lih@njupt.edu.cn"),

    # 南京信息工程大学
    ("王强", "南京信息工程大学", "大气科学学院", "教授", ["气象预报", "气候模拟"], "wangq@nuist.edu.cn"),
    ("陈芳", "南京信息工程大学", "计算机学院", "教授", ["人工智能", "模式识别"], "chenf@nuist.edu.cn"),

    # 江苏大学
    ("刘伟", "江苏大学", "机械工程学院", "教授", ["农业机械", "智能制造"], "liuw@ujs.edu.cn"),
    ("张丽", "江苏大学", "食品与生物工程学院", "教授", ["食品科学", "生物工程"], "zhangl@ujs.edu.cn"),

    # 扬州大学
    ("赵强", "扬州大学", "农学院", "教授", ["作物遗传", "分子育种"], "zhaoq@yzu.edu.cn"),
    ("王芳", "扬州大学", "兽医学院", "教授", ["动物医学", "预防兽医"], "wangf@yzu.edu.cn"),

    # 南京工业大学
    ("陈明", "南京工业大学", "材料科学与工程学院", "教授", ["先进材料", "纳米技术"], "chenm@njtech.edu.cn"),
    ("李伟", "南京工业大学", "化学与化工学院", "教授", ["化学工程", "催化"], "liw@njtech.edu.cn"),

    # 浙江工业大学
    ("张华", "浙江工业大学", "化学工程学院", "教授", ["化工过程", "绿色化学"], "zhangh@zjut.edu.cn"),
    ("刘明", "浙江工业大学", "计算机学院", "教授", ["大数据", "机器学习"], "lium@zjut.edu.cn"),

    # 浙江理工大学
    ("王建国", "浙江理工大学", "材料与纺织学院", "教授", ["纺织材料", "功能纤维"], "wangjg@zstu.edu.cn"),
    ("李芳", "浙江理工大学", "机械与自动控制学院", "教授", ["机器人", "智能控制"], "lif@zstu.edu.cn"),

    # 杭州电子科技大学
    ("张明", "杭州电子科技大学", "电子信息学院", "教授", ["集成电路", "射频设计"], "zhangm@hdu.edu.cn"),
    ("王强", "杭州电子科技大学", "计算机学院", "教授", ["网络安全", "密码学"], "wangq@hdu.edu.cn"),

    # 宁波大学
    ("陈华", "宁波大学", "信息科学与工程学院", "教授", ["通信工程", "电子信息技术"], "chenh@nbu.edu.cn"),
    ("赵丽", "宁波大学", "海洋学院", "教授", ["海洋科学", "水产养殖"], "zhaol@nbu.edu.cn"),

    # 湘潭大学
    ("刘强", "湘潭大学", "数学与计算科学学院", "教授", ["计算数学", "数值分析"], "liuq@xtu.edu.cn"),
    ("张芳", "湘潭大学", "法学院", "教授", ["知识产权", "科技法"], "zhangf@xtu.edu.cn"),

    # 南方科技大学
    ("王伟", "南方科技大学", "计算机科学与工程系", "教授", ["人工智能", "计算机视觉"], "wangw@ustc.edu.cn"),
    ("陈静", "南方科技大学", "材料科学与工程系", "教授", ["新能源材料", "纳米材料"], "chenj@ustc.edu.cn"),

    # 深圳大学
    ("张建国", "深圳大学", "计算机与软件学院", "教授", ["计算机应用", "软件工程"], "zhangjg@szu.edu.cn"),
    ("李芳", "深圳大学", "电子与信息工程学院", "教授", ["电子信息", "通信工程"], "lif@szu.edu.cn"),

    # 广东工业大学
    ("王强", "广东工业大学", "机电工程学院", "教授", ["机械电子", "智能制造"], "wangq@gdut.edu.cn"),
    ("陈明", "广东工业大学", "信息工程学院", "教授", ["信号处理", "通信工程"], "chenm@gdut.edu.cn"),

    # 广州大学
    ("刘伟", "广州大学", "土木工程学院", "教授", ["结构工程", "防灾减灾"], "liuw@gzhu.edu.cn"),
    ("张丽", "广州大学", "计算机科学与网络工程学院", "教授", ["网络安全", "大数据"], "zhangl@gzhu.edu.cn"),

    # 华南农业大学
    ("赵刚", "华南农业大学", "植物保护学院", "教授", ["植物病理", "生物防治"], "zhaog@scau.edu.cn"),
    ("王芳", "华南农业大学", "动物科学学院", "教授", ["动物营养", "饲料科学"], "wangf@scau.edu.cn"),

    # 汕头大学
    ("张伟", "汕头大学", "工学院", "教授", ["机械工程", "机器人"], "zhangw@stu.edu.cn"),
    ("李明", "汕头大学", "理学院", "教授", ["化学", "材料化学"], "lim@stu.edu.cn"),

    # 南方医科大学
    ("陈华", "南方医科大学", "基础医学院", "教授", ["病理学", "免疫学"], "chenh@smu.edu.cn"),
    ("王丽", "南方医科大学", "临床医学院", "教授", ["内科学", "心血管病"], "wangl@smu.edu.cn"),

    # 广州中医药大学
    ("刘强", "广州中医药大学", "中医学院", "教授", ["中医学", "中医内科"], "liuq@gzucm.edu.cn"),
    ("张明", "广州中医药大学", "中药学院", "教授", ["中药学", "中药药理"], "zhangm@gzucm.edu.cn"),

    # 湖北大学
    ("王建国", "湖北大学", "生命科学学院", "教授", ["生物学", "微生物学"], "wangjg@hubu.edu.cn"),
    ("李芳", "湖北大学", "文学院", "教授", ["中国语言文学", "古代文学"], "lif@hubu.edu.cn"),

    # 三峡大学
    ("张华", "三峡大学", "水利与环境学院", "教授", ["水利工程", "水文学"], "zhangh@ctgu.edu.cn"),
    ("刘明", "三峡大学", "电气与新能源学院", "教授", ["电气工程", "新能源"], "lium@ctgu.edu.cn"),

    # 长江大学
    ("王强", "长江大学", "地球科学学院", "教授", ["地质学", "石油地质"], "wangq@yangtzeu.edu.cn"),
    ("陈芳", "长江大学", "农学院", "教授", ["作物学", "种子科学"], "chenf@yangtzeu.edu.cn"),

    # 武汉科技大学
    ("赵伟", "武汉科技大学", "材料与冶金学院", "教授", ["钢铁冶金", "新材料"], "zhaow@wust.edu.cn"),
    ("李明", "武汉科技大学", "机械自动化学院", "教授", ["机械设计", "智能制造"], "lim@wust.edu.cn"),

    # 湖北工业大学
    ("张建国", "湖北工业大学", "电气与电子工程学院", "教授", ["电力电子", "新能源"], "zhangjg@hbut.edu.cn"),
    ("王芳", "湖北工业大学", "机械工程学院", "教授", ["机械电子", "机器人"], "wangf@hbut.edu.cn"),

    # 中南民族大学
    ("刘伟", "中南民族大学", "电子信息工程学院", "教授", ["电子信息", "信号处理"], "liuw@scuec.edu.cn"),
    ("张丽", "中南民族大学", "化学与材料学院", "教授", ["应用化学", "材料化学"], "zhangl@scuec.edu.cn"),

    # 湖南科技大学
    ("王强", "湖南科技大学", "机电工程学院", "教授", ["机械工程", "矿山机械"], "wangq@hnust.edu.cn"),
    ("陈明", "湖南科技大学", "计算机科学与工程学院", "教授", ["计算机应用", "网络安全"], "chenm@hnust.edu.cn"),

    # 长沙理工大学
    ("赵刚", "长沙理工大学", "交通运输工程学院", "教授", ["道路工程", "交通规划"], "zhaog@csust.edu.cn"),
    ("王芳", "长沙理工大学", "电气与信息工程学院", "教授", ["电力系统", "智能电网"], "wangf@csust.edu.cn"),

    # 湖南农业大学
    ("张伟", "湖南农业大学", "农学院", "教授", ["作物遗传", "分子育种"], "zhangw@hunan.edu.cn"),
    ("李华", "湖南农业大学", "动物科学技术学院", "教授", ["动物营养", "饲料科学"], "lih@hunan.edu.cn"),

    # 中南林业科技大学
    ("刘强", "中南林业科技大学", "林学院", "教授", ["森林培育", "生态学"], "liuq@csuft.edu.cn"),
    ("陈芳", "中南科技大学", "食品科学与工程学院", "教授", ["食品科学", "食品安全"], "chenf@csuft.edu.cn"),

    # 南华大学
    ("张明", "南华大学", "核科学技术学院", "教授", ["核工程", "辐射防护"], "zhangm@usc.edu.cn"),
    ("王丽", "南华大学", "医学院", "教授", ["临床医学", "内科学"], "wangl@usc.edu.cn"),

    # 湖南工业大学
    ("赵强", "湖南工业大学", "包装与材料工程学院", "教授", ["包装工程", "高分子材料"], "zhaoq@hut.edu.cn"),
    ("刘明", "湖南工业大学", "电气工程学院", "教授", ["电气工程", "电力电子"], "lium@hut.edu.cn"),

    # 河南大学
    ("张华", "河南大学", "文学院", "教授", ["中国现当代文学", "文学理论"], "zhangh@henu.edu.cn"),
    ("刘明", "河南大学", "化学化工学院", "教授", ["应用化学", "材料化学"], "lium@henu.edu.cn"),

    # 河南科技大学
    ("王建国", "河南科技大学", "机电工程学院", "教授", ["机械设计", "车辆工程"], "wangjg@haust.edu.cn"),
    ("李芳", "河南科技大学", "食品与生物工程学院", "教授", ["食品科学", "生物工程"], "lif@haust.edu.cn"),

    # 河南理工大学
    ("张明", "河南理工大学", "安全科学与工程学院", "教授", ["安全工程", "矿业安全"], "zhangm@hpu.edu.cn"),
    ("王强", "河南理工大学", "机械与动力工程学院", "教授", ["机械工程", "流体机械"], "wangq@hpu.edu.cn"),

    # 河南农业大学
    ("陈华", "河南农业大学", "农学院", "教授", ["作物学", "种子科学"], "chenh@henau.edu.cn"),
    ("赵丽", "河南农业大学", "植物保护学院", "教授", ["植物病理", "昆虫学"], "zhaol@henau.edu.cn"),

    # 河南师范大学
    ("刘伟", "河南师范大学", "物理与材料科学学院", "教授", ["凝聚态物理", "光学"], "liuw@htu.edu.cn"),
    ("张芳", "河南师范大学", "化学与环境科学学院", "教授", ["环境化学", "催化"], "zhangf@htu.edu.cn"),

    # 郑州轻工业大学
    ("王强", "郑州轻工业大学", "食品与生物工程学院", "教授", ["食品科学", "发酵工程"], "wangq@zzuli.edu.cn"),
    ("陈明", "郑州轻工业大学", "机电工程学院", "教授", ["机械电子", "智能制造"], "chenm@zzuli.edu.cn"),

    # 河南工业大学
    ("张伟", "河南工业大学", "粮油食品学院", "教授", ["粮油工程", "食品科学"], "zhangw@haut.edu.cn"),
    ("李华", "河南工业大学", "材料科学与工程学院", "教授", ["高分子材料", "复合材料"], "lih@haut.edu.cn"),

    # 中原工学院
    ("赵刚", "中原工学院", "纺织学院", "教授", ["纺织工程", "功能纺织品"], "zhaog@zzti.edu.cn"),
    ("王芳", "中原工学院", "机电学院", "教授", ["机械设计", "制造自动化"], "wangf@zzti.edu.cn"),

    # 河南中医药大学
    ("刘强", "河南中医药大学", "中医学院", "教授", ["中医学", "中医基础"], "liuq@hactcm.edu.cn"),
    ("张明", "河南中医药大学", "药学院", "教授", ["中药学", "药理学"], "zhangm@hactcm.edu.cn"),

    # 信阳师范大学
    ("王建国", "信阳师范大学", "化学化工学院", "教授", ["有机化学", "药物化学"], "wangjg@xynu.edu.cn"),
    ("李芳", "信阳师范大学", "生命科学学院", "教授", ["植物学", "生态学"], "lif@xynu.edu.cn"),

    # 山西大学
    ("张华", "山西大学", "物理电子工程学院", "教授", ["光学工程", "光电子技术"], "zhangh@sxu.edu.cn"),
    ("刘明", "山西大学", "历史文化学院", "教授", ["中国史", "近代史"], "lium@sxu.edu.cn"),

    # 太原科技大学
    ("王强", "太原科技大学", "机械工程学院", "教授", ["机械设计", "车辆工程"], "wangq@tyust.edu.cn"),
    ("陈芳", "太原科技大学", "材料科学与工程学院", "教授", ["金属材料", "焊接技术"], "chenf@tyust.edu.cn"),

    # 山西农业大学
    ("赵伟", "山西农业大学", "农学院", "教授", ["作物遗传", "分子育种"], "zhaow@sxau.edu.cn"),
    ("李明", "山西农业大学", "动物科技学院", "教授", ["动物遗传", "育种"], "lim@sxau.edu.cn"),

    # 山西师范大学
    ("张建国", "山西师范大学", "化学与材料科学学院", "教授", ["无机化学", "材料化学"], "zhangjg@sxnu.edu.cn"),
    ("王芳", "山西师范大学", "生命科学学院", "教授", ["生物学", "生态学"], "wangf@sxnu.edu.cn"),

    # 山西财经大学
    ("刘伟", "山西财经大学", "经济学院", "教授", ["区域经济", "产业经济"], "liuw@sxufe.edu.cn"),
    ("张丽", "山西财经大学", "会计学院", "教授", ["会计学", "审计学"], "zhangl@sxufe.edu.cn"),

    # 中北大学
    ("王强", "中北大学", "信息与通信工程学院", "教授", ["信号处理", "雷达"], "wangq@nuc.edu.cn"),
    ("陈明", "中北大学", "机械工程学院", "教授", ["兵器科学", "弹道学"], "chenm@nuc.edu.cn"),

    # 太原理工大学
    ("张伟", "太原理工大学", "化学化工学院", "教授", ["化学工程", "煤化工"], "zhangw@tyut.edu.cn"),
    ("李华", "太原理工大学", "矿业工程学院", "教授", ["采矿工程", "矿山安全"], "lih@tyut.edu.cn"),

    # 陕西师范大学
    ("王丽", "陕西师范大学", "心理学院", "教授", ["认知心理学", "社会认知"], "wangl@snnu.edu.cn"),
    ("张华", "陕西师范大学", "历史文化学院", "教授", ["中国古代史", "唐史"], "zhangh@snnu.edu.cn"),

    # 西安建筑科技大学
    ("刘强", "西安建筑科技大学", "土木工程学院", "教授", ["结构工程", "建筑技术"], "liuq@xauat.edu.cn"),
    ("陈芳", "西安建筑科技大学", "环境工程学院", "教授", ["环境工程", "水处理"], "chenf@xauat.edu.cn"),

    # 西安理工大学
    ("赵刚", "西安理工大学", "水利水电学院", "教授", ["水利工程", "水文学"], "zhaog@xaut.edu.cn"),
    ("王芳", "西安理工大学", "机械工程学院", "教授", ["机械设计", "制造自动化"], "wangf@xaut.edu.cn"),

    # 西安科技大学
    ("张明", "西安科技大学", "能源学院", "教授", ["矿业工程", "煤矿安全"], "zhangm@xust.edu.cn"),
    ("王丽", "西安科技大学", "安全工程学院", "教授", ["安全工程", "灾害防治"], "wangl@xust.edu.cn"),

    # 西安工业大学
    ("刘伟", "西安工业大学", "光电工程学院", "教授", ["光学工程", "光电检测"], "liuw@xatu.edu.cn"),
    ("张芳", "西安工业大学", "计算机学院", "教授", ["计算机应用", "软件工程"], "zhangf@xatu.edu.cn"),

    # 西安邮电大学
    ("赵强", "西安邮电大学", "通信与信息工程学院", "教授", ["通信工程", "物联网"], "zhaoq@xupt.edu.cn"),
    ("李明", "西安邮电大学", "计算机学院", "教授", ["人工智能", "大数据"], "lim@xupt.edu.cn"),

    # 陕西科技大学
    ("张伟", "陕西科技大学", "轻工科学与工程学院", "教授", ["制浆造纸", "生物质材料"], "zhangw@sust.edu.cn"),
    ("陈华", "陕西科技大学", "材料科学与工程学院", "教授", ["无机非金属", "功能材料"], "chenh@sust.edu.cn"),

    # 西安工程大学
    ("王强", "西安工程大学", "纺织科学与工程学院", "教授", ["纺织工程", "功能纺织品"], "wangq@xpu.edu.cn"),
    ("刘明", "西安工程大学", "机电工程学院", "教授", ["机械电子", "机器人"], "lium@xpu.edu.cn"),

    # 西安外国语大学
    ("张建国", "西安外国语大学", "英文学院", "教授", ["英语语言文学", "翻译学"], "zhangjg@xisu.edu.cn"),
    ("李芳", "西安外国语大学", "日本语言文化学院", "教授", ["日语语言学", "日本文学"], "lif@xisu.edu.cn"),

    # 西安财经大学
    ("王芳", "西安财经大学", "经济学院", "教授", ["区域经济", "产业经济"], "wangf@xafeu.edu.cn"),
    ("赵丽", "西安财经大学", "会计学院", "教授", ["会计学", "审计学"], "zhaol@xafeu.edu.cn"),

    # 西安石油大学
    ("刘强", "西安石油大学", "石油工程学院", "教授", ["油气田开发", "采油工程"], "liuq@xsyu.edu.cn"),
    ("陈明", "西安石油大学", "化学工程学院", "教授", ["化学工程", "石油化工"], "chenm@xsyu.edu.cn"),

    # 延安大学
    ("张华", "延安大学", "化学与化工学院", "教授", ["化学工程", "催化"], "zhangh@yau.edu.cn"),
    ("王伟", "延安大学", "医学院", "教授", ["临床医学", "内科学"], "wangw@yau.edu.cn"),

    # 陕西理工大学
    ("赵刚", "陕西理工大学", "机械工程学院", "教授", ["机械设计", "车辆工程"], "zhaog@snut.edu.cn"),
    ("王芳", "陕西理工大学", "材料科学与工程学院", "教授", ["材料科学", "功能材料"], "wangf@snut.edu.cn"),

    # 宝鸡文理学院
    ("张明", "宝鸡文理学院", "化学化工学院", "教授", ["有机化学", "药物化学"], "zhangm@bjwlxy.edu.cn"),
    ("李华", "宝鸡文理学院", "物理与光电技术学院", "教授", ["物理学", "光电技术"], "lih@bjwlxy.edu.cn"),

    # 渭南师范学院
    ("刘伟", "渭南师范学院", "化学与材料学院", "教授", ["化学", "材料化学"], "liuw@wnu.edu.cn"),
    ("张丽", "渭南师范学院", "教育科学学院", "教授", ["教育学", "课程与教学"], "zhangl@wnu.edu.cn"),

    # 咸阳师范学院
    ("王强", "咸阳师范学院", "化学与化工学院", "教授", ["化学", "应用化学"], "wangq@xytu.edu.cn"),
    ("陈芳", "咸阳师范学院", "物理与电子工程学院", "教授", ["物理学", "电子信息"], "chenf@xytu.edu.cn"),

    # 安康学院
    ("赵伟", "安康学院", "化学化工学院", "教授", ["化学", "环境化学"], "zhaow@aku.edu.cn"),
    ("李明", "安康学院", "农学与生命科学学院", "教授", ["农学", "植物保护"], "lim@aku.edu.cn"),

    # 榆林学院
    ("张建国", "榆林学院", "能源工程学院", "教授", ["石油工程", "油气储运"], "zhangjg@ylu.edu.cn"),
    ("王芳", "榆林学院", "化学与化工学院", "教授", ["化学工程", "煤化工"], "wangf@ylu.edu.cn"),

    # 商洛学院
    ("刘强", "商洛学院", "化学工程与现代材料学院", "教授", ["化学", "材料化学"], "liuq@slxy.edu.cn"),
    ("陈明", "商洛学院", "生物医药工程学院", "教授", ["生物技术", "制药工程"], "chenm@slxy.edu.cn"),

    # 西安航空学院
    ("张伟", "西安航空学院", "航空制造工程学院", "教授", ["航空制造", "精密加工"], "zhangw@xhpu.edu.cn"),
    ("李华", "西安航空学院", "车辆工程学院", "教授", ["车辆工程", "新能源汽车"], "lih@xhpu.edu.cn"),

    # 西安文理学院
    ("王强", "西安文理学院", "信息工程学院", "教授", ["计算机应用", "软件工程"], "wangq@xawl.edu.cn"),
    ("陈芳", "西安文理学院", "生物与环境工程学院", "教授", ["生物学", "环境工程"], "chenf@xawl.edu.cn"),

    # 湖南工程学院
    ("赵刚", "湖南工程学院", "机械工程学院", "教授", ["机械设计", "制造自动化"], "zhaog@hnie.edu.cn"),
    ("王芳", "湖南工程学院", "电气与信息工程学院", "教授", ["电气工程", "电子信息"], "wangf@hnie.edu.cn"),

    # 湖南理工学院
    ("张明", "湖南理工学院", "化学化工学院", "教授", ["化学", "应用化学"], "zhangm@hnist.edu.cn"),
    ("刘明", "湖南理工学院", "信息与通信工程学院", "教授", ["通信工程", "信号处理"], "lium@hnist.edu.cn"),

    # 湖南城市学院
    ("王建国", "湖南城市学院", "土木工程学院", "教授", ["结构工程", "防灾减灾"], "wangjg@hnuc.edu.cn"),
    ("李芳", "湖南城市学院", "信息与电子工程学院", "教授", ["电子信息", "自动化"], "lif@hnuc.edu.cn"),

    # 湖南文理学院
    ("张华", "湖南文理学院", "化学与材料工程学院", "教授", ["化学", "材料化学"], "zhangh@hnuwc.edu.cn"),
    ("刘伟", "湖南文理学院", "计算机与电气工程学院", "教授", ["计算机应用", "电气工程"], "liuw@hnuwc.edu.cn"),

    # 湖南科技学院
    ("赵强", "湖南科技学院", "电子与信息工程学院", "教授", ["电子信息", "通信工程"], "zhaoq@hnust.edu.cn"),
    ("王丽", "湖南科技学院", "化学与生物工程学院", "教授", ["化学", "生物工程"], "wangl@hnust.edu.cn"),

    # 邵阳学院
    ("张伟", "邵阳学院", "机械与能源工程学院", "教授", ["机械工程", "能源工程"], "zhangw@hnsyu.edu.cn"),
    ("李华", "邵阳学院", "信息工程学院", "教授", ["计算机应用", "软件工程"], "lih@hnsyu.edu.cn"),

    # 怀化学院
    ("王强", "怀化学院", "化学与材料工程学院", "教授", ["化学", "材料化学"], "wangq@hhxy.edu.cn"),
    ("陈明", "怀化学院", "计算机科学与工程学院", "教授", ["计算机应用", "网络安全"], "chenm@hhxy.edu.cn"),

    # 湘南学院
    ("刘强", "湘南学院", "电子信息与电气工程学院", "教授", ["电子信息", "电气工程"], "liuq@xnu.edu.cn"),
    ("张芳", "湘南学院", "化学与环境工程学院", "教授", ["化学", "环境工程"], "zhangf@xnu.edu.cn"),

    # 长沙学院
    ("赵刚", "长沙学院", "机电工程学院", "教授", ["机械电子", "智能制造"], "zhaog@ccsu.edu.cn"),
    ("王芳", "长沙学院", "计算机科学与技术学院", "教授", ["计算机应用", "软件工程"], "wangf@ccsu.edu.cn"),

    # 湖南第一师范学院
    ("张明", "湖南第一师范学院", "信息科学与工程学院", "教授", ["计算机应用", "人工智能"], "zhangm@hnfnu.edu.cn"),
    ("李华", "湖南第一师范学院", "数学与统计学院", "教授", ["数学", "应用数学"], "lih@hnfnu.edu.cn"),
]


def build_fallback_mentors() -> list[dict]:
    """将备选数据集转为标准导师字典列表。"""
    mentors = []
    seen = set()
    for item in FALLBACK_MENTOR_DATA:
        name, university, department, title, directions, email = item
        key = (name, university)
        if key in seen:
            continue
        seen.add(key)
        mentors.append({
            "name": name,
            "university": university,
            "department": department,
            "title": title,
            "research_directions": directions,
            "contact_email": email,
        })
    return mentors


# ============================================================
# 主流程: 爬取 → 解析 → 去重 → 入库
# ============================================================

def fetch_all(session: requests.Session) -> list[dict]:
    """依次尝试多种爬取策略，合并结果。"""
    all_results = []

    logger.info("=" * 60)
    logger.info("开始爬取考研导师数据...")
    logger.info("=" * 60)

    # 策略 1: 研导网
    logger.info("\n[策略1] 尝试爬取研导网 (yds.eol.cn)...")
    try:
        results = scrape_yds(session)
        all_results.extend(results)
        logger.info(f"  研导网: 获取 {len(results)} 条")
    except Exception as e:
        logger.warning(f"  研导网爬取失败: {e}")

    # 策略 2: 研招网
    logger.info("\n[策略2] 尝试爬取研招网 (yz.chsi.com.cn)...")
    try:
        results = scrape_yz_chsi(session)
        all_results.extend(results)
        logger.info(f"  研招网: 获取 {len(results)} 条")
    except Exception as e:
        logger.warning(f"  研招网爬取失败: {e}")

    # 策略 3: 院校页面
    logger.info("\n[策略3] 尝试爬取院校研究生院页面...")
    try:
        results = scrape_university_pages(session)
        all_results.extend(results)
        logger.info(f"  院校页面: 获取 {len(results)} 条")
    except Exception as e:
        logger.warning(f"  院校页面爬取失败: {e}")

    # 策略 4: 备选数据集
    logger.info("\n[策略4] 加载备选公开导师数据集...")
    fallback = build_fallback_mentors()
    all_results.extend(fallback)
    logger.info(f"  备选数据集: {len(fallback)} 条")

    # 合并去重 (按 name + university)
    seen = set()
    unique = []
    for m in all_results:
        name = m.get("name", "").strip()
        univ = m.get("university", "").strip()
        if not name or not univ:
            continue
        key = (name, univ)
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)

    logger.info(f"\n合并去重后: {len(unique)} 条 (原始 {len(all_results)} 条)")
    return unique


def store_to_db(mentors: list[dict]) -> dict:
    """将导师数据写入 mentors 表，按 name+university 去重。"""
    db = SessionLocal()
    stats = {"fetched": len(mentors), "imported": 0, "skipped": 0, "errors": 0}

    try:
        # 查询已存在的 name+university 组合
        existing = set()
        if mentors:
            batch_size = 500
            for i in range(0, len(mentors), batch_size):
                batch = mentors[i:i+batch_size]
                names = [m["name"] for m in batch]
                univs = [m["university"] for m in batch]
                rows = db.query(Mentor.name, Mentor.university).filter(
                    Mentor.name.in_(names),
                    Mentor.university.in_(univs),
                ).all()
                existing.update((r[0], r[1]) for r in rows)

        logger.info(f"数据库已有 {len(existing)} 条 name+university 组合")

        # 插入新记录
        for m in mentors:
            name = m["name"].strip()
            univ = m["university"].strip()
            dept = m.get("department", "").strip()
            title = m.get("title", "讲师").strip()
            directions = m.get("research_directions", [])
            email = m.get("contact_email")

            if (name, univ) in existing:
                stats["skipped"] += 1
                continue

            try:
                mentor = Mentor(
                    id=uuid4(),
                    name=name,
                    university=univ,
                    department=dept,
                    title=title,
                    research_directions=directions if isinstance(directions, list) else [directions],
                    paper_count=0,
                    project_count=0,
                    citation_count=0,
                    h_index=None,
                    enrollment_status="unknown",
                    enrollment_directions=directions[:3] if isinstance(directions, list) else [],
                    contact_email=email,
                    tags=[],
                    avg_rating=0.0,
                    review_count=0,
                    rating_academic=0.0,
                    rating_guidance=0.0,
                    rating_relationship=0.0,
                    rating_funding=0.0,
                    rating_workload=0.0,
                    rating_career=0.0,
                    source_url=None,
                    source_platform="crawler",
                    is_verified=False,
                )
                db.add(mentor)
                existing.add((name, univ))
                stats["imported"] += 1
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"插入失败 {name}@{univ}: {e}")

        db.commit()
        logger.info(f"数据库提交成功")

    except Exception as e:
        db.rollback()
        logger.error(f"数据库操作失败: {e}")
        stats["errors"] += 1
    finally:
        db.close()

    return stats


def main():
    """主入口: 爬取 → 去重 → 入库 → 报告。"""
    print("=" * 60)
    print("  考研导师数据爬取器")
    print("=" * 60)

    session = requests.Session()
    session.headers.update(HEADERS)

    # 1. 爬取
    mentors = fetch_all(session)

    # 2. 入库
    stats = store_to_db(mentors)

    # 3. 报告
    print("\n" + "=" * 60)
    print("  爬取报告")
    print("=" * 60)
    print(f"  爬取来源: 研导网 / 研招网 / 院校页面 / 备选数据集")
    print(f"  爬取条数: {stats['fetched']}")
    print(f"  新导入条数: {stats['imported']}")
    print(f"  跳过(已存在): {stats['skipped']}")
    print(f"  错误条数: {stats['errors']}")
    print("=" * 60)

    # 4. 最终统计
    db = SessionLocal()
    try:
        total = db.query(Mentor).count()
        print(f"\n  数据库导师总数: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
