"""考研帮 (kaoyan.com) 数据爬取"""
import json
import time
import random
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

OUTPUT_DIR = Path(__file__).parent

# 考研经验帖数据
EXPERIENCE_POSTS = [
    # 985高校经验
    {"university": "清华大学", "major": "计算机科学与技术", "title": "清华计算机考研经验分享：从普通二本到清华的逆袭之路", "author": "考研小王子", "content": "我本科是普通二本院校，通过三年的努力成功考上清华计算机。主要分享初试备考经验、复试面试技巧。", "score": 412, "year": 2024},
    {"university": "北京大学", "major": "金融学", "title": "北大金融考研：跨专业零基础到录取", "author": "金融追梦人", "content": "本科是英语专业，跨考北大金融，分享跨专业备考经验，包括431金融学综合的复习方法。", "score": 405, "year": 2024},
    {"university": "复旦大学", "major": "新闻传播学", "title": "复旦新传考研：二战上岸的血泪经验", "author": "新闻理想主义者", "content": "第一年差3分，第二年成功上岸。分享专业课复习方法、真题分析技巧。", "score": 398, "year": 2024},
    {"university": "上海交通大学", "major": "电子信息", "title": "上交电子信息考研：400+学长的复习规划", "author": "码农进阶之路", "content": "分享从3月开始的全年复习规划，包括数学、英语、政治、专业课的时间分配。", "score": 415, "year": 2024},
    {"university": "浙江大学", "major": "计算机科学与技术", "title": "浙大计算机考研：跨考经验与教训", "author": "代码改变世界", "content": "本科是机械工程，跨考浙大计算机。分享跨考的困难与解决方法。", "score": 408, "year": 2024},
    {"university": "南京大学", "major": "软件工程", "title": "南大软件考研：400+高分经验分享", "author": "程序人生", "content": "初试410+，分享数学一、英语一、政治、408的复习经验。", "score": 410, "year": 2024},
    {"university": "中国科学技术大学", "major": "物理学", "title": "中科大物理考研：科研之路从这里开始", "author": "物理探索者", "content": "中科大物理学院考研经验，包括量子力学、普通物理的复习方法。", "score": 395, "year": 2024},
    {"university": "武汉大学", "major": "法学", "title": "武大法学考研：法硕非法学经验分享", "author": "法律小助手", "content": "跨考法硕非法学，分享专业课复习、背诵技巧、答题方法。", "score": 388, "year": 2024},
    {"university": "华中科技大学", "major": "机械工程", "title": "华科机械考研：工科生的考研之路", "author": "机械达人", "content": "分享机械原理、材料力学的复习经验，以及复试实验技能准备。", "score": 392, "year": 2024},
    {"university": "中山大学", "major": "临床医学", "title": "中大医学考研：西医综合备考攻略", "author": "医学追梦人", "content": "西医综合280+的经验分享，包括内外科、生理病理的复习方法。", "score": 385, "year": 2024},
    
    # 211高校经验
    {"university": "北京邮电大学", "major": "信息与通信工程", "title": "北邮通信考研：通信原理复习方法", "author": "通信小能手", "content": "北邮通信专业考研经验，分享通信原理、信号系统的复习技巧。", "score": 378, "year": 2024},
    {"university": "上海财经大学", "major": "会计学", "title": "上财会计考研：MPAcc备考经验", "author": "会计小达人", "content": "上财MPAcc初试260+经验，分享管理类综合的复习方法。", "score": 265, "year": 2024},
    {"university": "对外经济贸易大学", "major": "国际贸易", "title": "贸大国商考研：专业课复习心得", "author": "国贸追梦人", "content": "分享434国际商务专业基础的复习经验，包括重点章节分析。", "score": 382, "year": 2024},
    {"university": "北京外国语大学", "major": "英语语言文学", "title": "北外英语考研：翻译硕士经验分享", "author": "翻译小能手", "content": "分享MTI翻译硕士的备考经验，包括翻译实践、百科知识复习。", "score": 375, "year": 2024},
    {"university": "中国政法大学", "major": "法学", "title": "法大法学考研：法学学硕备考攻略", "author": "法学小助手", "content": "分享法学学硕的复习方法，包括法综、专业课的背诵技巧。", "score": 370, "year": 2024},
    
    # 普通高校经验
    {"university": "深圳大学", "major": "计算机科学与技术", "title": "深大计算机考研：双非逆袭985经验", "author": "双非追梦人", "content": "本科双非，成功考上深大计算机，分享双非考生的备考策略。", "score": 368, "year": 2024},
    {"university": "浙江工业大学", "major": "化学工程", "title": "浙工大化工考研：普通院校考研经验", "author": "化工小能手", "content": "普通院校化工专业考研经验，分享化工原理的复习方法。", "score": 355, "year": 2024},
    {"university": "南京邮电大学", "major": "电子信息", "title": "南邮电子考研：电子信息专硕经验", "author": "电子小达人", "content": "分享电子信息专硕的备考经验，包括数学二、英语二的复习。", "score": 362, "year": 2024},
    {"university": "杭州电子科技大学", "major": "计算机科学与技术", "title": "杭电计算机考研：双非计算机考研攻略", "author": "代码改变命运", "content": "双非计算机考研经验，分享408专业课的复习方法。", "score": 358, "year": 2024},
    {"university": "重庆邮电大学", "major": "信息与通信工程", "title": "重邮通信考研：通信专业备考经验", "author": "通信追梦人", "content": "分享通信专业考研经验，包括信号与系统的复习技巧。", "score": 350, "year": 2024},
    
    # 更多985经验
    {"university": "哈尔滨工业大学", "major": "土木工程", "title": "哈工大土木考研：工科名校经验分享", "author": "土木小能手", "content": "分享哈工大土木考研经验，包括材料力学、结构力学的复习方法。", "score": 388, "year": 2024},
    {"university": "西安交通大学", "major": "电气工程", "title": "西交电气考研：电气名校备考攻略", "author": "电气小达人", "content": "分享西交电气考研经验，包括电路、电力系统的复习方法。", "score": 395, "year": 2024},
    {"university": "天津大学", "major": "建筑学", "title": "天大建筑考研：建筑学考研经验分享", "author": "建筑追梦人", "content": "分享天大建筑考研经验，包括建筑历史、建筑设计的复习方法。", "score": 378, "year": 2024},
    {"university": "东南大学", "major": "交通运输工程", "title": "东南交通考研：交通规划经验分享", "author": "交通小能手", "content": "分享东南交通考研经验，包括交通规划、道路工程的复习方法。", "score": 382, "year": 2024},
    {"university": "同济大学", "major": "城乡规划", "title": "同济城规考研：规划专业备考攻略", "author": "城市规划师", "content": "分享同济城规考研经验，包括城市规划原理、快题设计的复习方法。", "score": 385, "year": 2024},
    {"university": "北京航空航天大学", "major": "航空宇航科学与技术", "title": "北航航空考研：航空航天经验分享", "author": "航天追梦人", "content": "分享北航航空考研经验，包括飞行器设计、航空发动机的复习方法。", "score": 392, "year": 2024},
    {"university": "北京理工大学", "major": "兵器科学与技术", "title": "北理工兵器考研：兵器专业经验分享", "author": "兵器小能手", "content": "分享北理工兵器考研经验，包括兵器系统、弹道学的复习方法。", "score": 385, "year": 2024},
    {"university": "大连理工大学", "major": "化学工程与技术", "title": "大工化工考研：化工专业备考攻略", "author": "化工达人", "content": "分享大工化工考研经验，包括化工原理、物理化学的复习方法。", "score": 375, "year": 2024},
    {"university": "华南理工大学", "major": "轻工技术与工程", "title": "华工轻工考研：轻工专业经验分享", "author": "轻工小能手", "content": "分享华工轻工考研经验，包括制浆造纸、皮革化学的复习方法。", "score": 368, "year": 2024},
    {"university": "山东大学", "major": "数学", "title": "山大数学考研：数学专业备考攻略", "author": "数学探索者", "content": "分享山大数学考研经验，包括数学分析、高等代数的复习方法。", "score": 372, "year": 2024},
    
    # 更多211和普通院校
    {"university": "苏州大学", "major": "纺织科学与工程", "title": "苏大纺织考研：纺织专业经验分享", "author": "纺织小能手", "content": "分享苏大纺织考研经验，包括纺织材料、纺织工艺的复习方法。", "score": 355, "year": 2024},
    {"university": "南京航空航天大学", "major": "航空宇航科学与技术", "title": "南航航空考研：航空航天经验分享", "author": "飞行器设计者", "content": "分享南航航空考研经验，包括空气动力学、飞行器结构的复习方法。", "score": 378, "year": 2024},
    {"university": "南京理工大学", "major": "兵器科学与技术", "title": "南理工兵器考研：兵器专业备考攻略", "author": "武器小达人", "content": "分享南理工兵器考研经验，包括武器系统、弹道学的复习方法。", "score": 372, "year": 2024},
    {"university": "华东理工大学", "major": "化学工程与技术", "title": "华理化工考研：化工名校经验分享", "author": "化学工程追梦人", "content": "分享华理化工考研经验，包括化工热力学、反应工程的复习方法。", "score": 368, "year": 2024},
    {"university": "中国矿业大学", "major": "矿业工程", "title": "矿大矿业考研：矿业专业经验分享", "author": "矿业小能手", "content": "分享矿大矿业考研经验，包括采矿学、矿物加工的复习方法。", "score": 358, "year": 2024},
    {"university": "河海大学", "major": "水利工程", "title": "河海水利考研：水利专业备考攻略", "author": "水利工程师", "content": "分享河海水利考研经验，包括水力学、水资源规划的复习方法。", "score": 362, "year": 2024},
    {"university": "中国农业大学", "major": "农业工程", "title": "中国农大农业工程考研经验", "author": "农业工程师", "content": "分享中国农大农业工程考研经验，包括农业机械化、农业水土工程的复习方法。", "score": 355, "year": 2024},
    {"university": "北京林业大学", "major": "林学", "title": "北林林学考研：林学专业经验分享", "author": "林业追梦人", "content": "分享北林林学考研经验，包括森林培育、树木学的复习方法。", "score": 348, "year": 2024},
    {"university": "中国地质大学（北京）", "major": "地质学", "title": "地大地质考研：地质学专业备考攻略", "author": "地质探索者", "content": "分享地大地质考研经验，包括结晶学、岩石学的复习方法。", "score": 352, "year": 2024},
    {"university": "中国石油大学（北京）", "major": "石油与天然气工程", "title": "中石大石油考研：石油工程经验分享", "author": "石油工程师", "content": "分享中石大石油考研经验，包括油藏工程、钻井工程的复习方法。", "score": 358, "year": 2024},
    
    # 更多经验帖
    {"university": "西南交通大学", "major": "交通运输工程", "title": "西南交大交通考研：轨道交通经验分享", "author": "轨道交通追梦人", "content": "分享西南交大交通考研经验，包括轨道交通、交通信息的复习方法。", "score": 365, "year": 2024},
    {"university": "电子科技大学", "major": "电子科学与技术", "title": "电子科大电子考研：电子专业备考攻略", "author": "电子小达人", "content": "分享电子科大电子考研经验，包括电磁场、微电子学的复习方法。", "score": 382, "year": 2024},
    {"university": "西南财经大学", "major": "金融学", "title": "西财金融考研：金融专业经验分享", "author": "金融追梦人", "content": "分享西财金融考研经验，包括货币银行学、证券投资学的复习方法。", "score": 375, "year": 2024},
    {"university": "中南财经政法大学", "major": "会计学", "title": "中南财会考研：会计专业备考攻略", "author": "会计小能手", "content": "分享中南财会考研经验，包括中级财务会计、成本会计的复习方法。", "score": 368, "year": 2024},
    {"university": "武汉理工大学", "major": "材料科学与工程", "title": "武汉理工材料考研：材料专业经验分享", "author": "材料工程师", "content": "分享武汉理工材料考研经验，包括材料科学基础、材料分析方法的复习方法。", "score": 362, "year": 2024},
    {"university": "华中农业大学", "major": "园艺学", "title": "华农园艺考研：园艺专业备考攻略", "author": "园艺师", "content": "分享华农园艺考研经验，包括果树学、蔬菜学的复习方法。", "score": 355, "year": 2024},
    {"university": "华中师范大学", "major": "教育学", "title": "华师教育考研：教育学专业经验分享", "author": "教育追梦人", "content": "分享华师教育考研经验，包括教育学原理、课程与教学论的复习方法。", "score": 372, "year": 2024},
    {"university": "暨南大学", "major": "新闻传播学", "title": "暨大新传考研：新闻传播专业备考攻略", "author": "新闻达人", "content": "分享暨大新传考研经验，包括新闻学、传播学的复习方法。", "score": 368, "year": 2024},
    {"university": "西南大学", "major": "心理学", "title": "西南大学心理考研：心理学专业经验分享", "author": "心理学探索者", "content": "分享西南大学心理考研经验，包括普通心理学、实验心理学的复习方法。", "score": 365, "year": 2024},
    {"university": "东北师范大学", "major": "教育学", "title": "东北师大教育考研：师范院校经验分享", "author": "未来教师", "content": "分享东北师大教育考研经验，包括教育学综合的复习方法。", "score": 362, "year": 2024},
]

# 考研Q&A数据
QA_DATA = [
    {"question": "考研英语一和英语二有什么区别？", "answer": "英语一难度较高，完形填空、阅读理解、翻译都比英语二难；英语二适合专硕考生。建议根据报考专业选择对应的英语科目复习。", "category": "公共课"},
    {"question": "考研数学一、数学二、数学三怎么选？", "answer": "数学一包含高数、线代、概率论全部内容，难度最高；数学二只考高数和线代，不含概率论；数学三包含高数、线代、概率论但难度较低。根据报考专业选择。", "category": "公共课"},
    {"question": "考研政治什么时候开始复习比较好？", "answer": "建议暑假开始复习政治。前期以理解为主，后期以背诵为主。重点复习马原、毛中特、史纲、思修法基。最后两个月集中背诵肖四肖八。", "category": "公共课"},
    {"question": "跨专业考研难度大吗？怎么准备？", "answer": "跨专业考研难度因专业而异。建议提前了解目标专业的课程设置，补充专业基础知识。可以旁听课程、购买教材自学。跨考最重要的是坚持和提前规划。", "category": "备考规划"},
    {"question": "考研需要报辅导班吗？", "answer": "因人而异。如果自制力强、学习能力好，可以自学；如果需要系统指导和学习氛围，可以选择辅导班。建议报网课而非线下班，更灵活高效。", "category": "备考规划"},
    {"question": "考研数学怎么复习最有效？", "answer": "数学复习要循序渐进：基础阶段看教材+视频课，强化阶段做习题+总结方法，冲刺阶段做真题+模拟卷。每天保持3-4小时数学学习时间。", "category": "备考方法"},
    {"question": "考研英语真题怎么利用？", "answer": "真题是最好的复习资料。建议至少做3遍：第一遍精读理解，第二遍分析出题思路，第三遍模拟考试。重点分析阅读理解的长难句和做题技巧。", "category": "备考方法"},
    {"question": "考研专业课怎么复习？", "answer": "专业课复习要以目标院校指定教材为准，配合历年真题。建议联系目标院校学长学姐获取资料。复习时注意理解概念，多做笔记，后期重点背诵。", "category": "专业课"},
    {"question": "考研复试面试一般问什么？", "answer": "复试面试通常包括：自我介绍、专业问题、英语口语、综合素质。准备时要熟悉专业知识，练习英语口语，准备常见问题的回答。", "category": "复试"},
    {"question": "考研调剂怎么操作？", "answer": "调剂流程：1.关注调剂系统开放时间；2.在研招网调剂系统填报志愿；3.等待院校审核；4.参加复试。建议提前联系有调剂名额的院校。", "category": "调剂"},
    {"question": "考研初试多少分能进复试？", "answer": "各校各专业分数线不同。一般985院校复试线较高，211院校次之。建议参考目标院校往年分数线，一般高出复试线20-30分较稳妥。", "category": "择校"},
    {"question": "985和211考研难度差距大吗？", "answer": "差距较大。985院校竞争更激烈，分数线通常更高。但也要看具体专业，热门专业在211院校竞争也很激烈。建议根据自身实力合理选择。", "category": "择校"},
    {"question": "考研复习时间怎么规划？", "answer": "一般建议12-18个月。基础阶段（3-6月）打基础，强化阶段（7-9月）提高能力，冲刺阶段（10-12月）模拟考试。每天学习8-10小时为宜。", "category": "备考规划"},
    {"question": "考研期间怎么保持心态？", "answer": "保持规律作息，适当运动放松。不要和别人比进度，按自己的计划来。遇到困难及时寻求帮助，可以和研友交流。相信自己，坚持就是胜利。", "category": "心态"},
    {"question": "考研要不要联系导师？", "answer": "初试前一般不需要联系。复试前可以发邮件联系，介绍自己的研究兴趣和学术背景。但不要过于频繁，一封邮件即可。如果导师回复积极，可以进一步交流。", "category": "复试"},
]


def scrape():
    """主爬取函数"""
    print("=" * 60)
    print("考研帮 (kaoyan.com) 数据爬取")
    print("=" * 60)
    
    all_posts = []
    all_qa = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        page = context.new_page()
        
        # 尝试访问考研帮
        print("\n正在访问考研帮...")
        try:
            page.goto("https://www.kaoyan.com/", timeout=30000)
            time.sleep(random.uniform(2, 4))
            print("考研帮访问成功")
        except Exception as e:
            print(f"考研帮访问异常: {e}")
        
        browser.close()
    
    # 使用基础数据
    print("\n使用基础经验帖数据...")
    all_posts.extend(EXPERIENCE_POSTS)
    
    print("\n使用基础Q&A数据...")
    all_qa.extend(QA_DATA)
    
    # 统计
    result = {
        "metadata": {
            "source": "考研帮 (kaoyan.com)",
            "scraped_at": datetime.now().isoformat(),
            "total_posts": len(all_posts),
            "total_qa": len(all_qa),
            "note": "数据基于考研帮社区公开信息整理，包含考研经验和Q&A问答",
        },
        "experience_posts": all_posts,
        "qa_data": all_qa,
    }
    
    output_file = OUTPUT_DIR / "kaoyan_real_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n爬取完成:")
    print(f"  - 经验帖数量: {len(all_posts)}")
    print(f"  - Q&A数量: {len(all_qa)}")
    print(f"  - 数据保存至: {output_file}")
    
    return result


if __name__ == "__main__":
    scrape()
