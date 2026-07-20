#!/usr/bin/env python3
"""Fix QA entries that have fewer than 3 answers by adding appropriate 3rd answers."""

import re
import sys

def generate_third_answer(title, existing_answers):
    """Generate a contextually appropriate 3rd answer based on the question."""
    title_lower = title.lower()
    
    # 408 specific topics
    if '408' in title or '数据结构' in title or '操作系统' in title or '计算机组成' in title or '计算机网络' in title or '计组' in title or '计网' in title:
        return "建议结合王道辅导书和真题来复习，重点理解核心概念，多做练习题巩固。祝复习顺利！"
    
    # 数学相关
    if '数学' in title or '高数' in title or '线代' in title or '概率' in title:
        return "数学复习关键是打好基础，多做题多总结。推荐建立错题本，定期回顾易错知识点。"
    
    # 英语相关
    if '英语' in title or '作文' in title or '阅读' in title or '翻译' in title or '单词' in title:
        return "英语复习贵在坚持，每天保持一定的学习量。真题是最好的复习资料，建议反复精读。"
    
    # 政治相关
    if '政治' in title or '肖' in title or '马原' in title:
        return "政治复习重点在选择题，大题紧跟肖四肖八即可。时政热点也要关注。"
    
    # 复试相关
    if '复试' in title or '面试' in title or '导师' in title or '简历' in title:
        return "复试准备要全面，专业知识、英语口语、综合素质都要兼顾。保持自信，展现真实的自己。"
    
    # 调剂相关
    if '调剂' in title:
        return "调剂要主动出击，多关注各校调剂信息。心态很重要，不要轻易放弃任何机会。"
    
    # 择校相关
    if '择校' in title or '院校' in title or '选学校' in title:
        return "择校要综合考虑自身实力、专业兴趣、就业前景等因素。适合自己的才是最好的。"
    
    # 跨考相关
    if '跨考' in title or '跨专业' in title:
        return "跨考需要付出更多努力，但只要方向正确、坚持复习，成功上岸是完全可能的。加油！"
    
    # 二战相关
    if '二战' in title:
        return "二战要总结一战的经验教训，调整复习策略。保持良好心态，相信自己一定能成功。"
    
    # 心态相关
    if '心态' in title or '焦虑' in title or '压力' in title:
        return "心态调整很重要，适当运动、保证睡眠、与朋友交流都有助于缓解压力。"
    
    # 时间管理
    if '时间' in title or '作息' in title or '计划' in title:
        return "合理规划时间，劳逸结合。制定切实可行的计划并坚持执行是成功的关键。"
    
    # 专硕/学硕
    if '专硕' in title or '学硕' in title:
        return "选择专硕还是学硕要根据自己的职业规划来决定。两者各有优势，关键是适合自己。"
    
    # 保研
    if '保研' in title or '推免' in title or '夏令营' in title:
        return "保研需要提前准备，成绩、科研、英语都很重要。积极参加目标院校的夏令营。"
    
    # 信息获取
    if '信息' in title or '渠道' in title or '资料' in title:
        return "信息获取渠道要多元化，研招网、目标院校官网、考研论坛、学长学姐都是重要来源。"
    
    # 默认回答
    return "祝考研顺利！坚持就是胜利，相信自己的努力一定会有回报。"

def fix_qa_answers(filepath):
    """Fix QA entries with fewer than 3 answers."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find QA_SEEDS section
    start_marker = 'QA_SEEDS = ['
    start = content.find(start_marker)
    if start == -1:
        print("ERROR: QA_SEEDS not found")
        return False
    
    # Find the end of QA_SEEDS by tracking bracket depth
    depth = 0
    end = start
    for i in range(start + len(start_marker), len(content)):
        if content[i] == '[':
            depth += 1
        elif content[i] == ']':
            if depth == 0:
                end = i
                break
            depth -= 1
    
    qa_section = content[start:end+1]
    
    # Split into entries
    entries = qa_section.split('{')[1:]  # skip first empty split
    
    fixed_count = 0
    for idx, entry in enumerate(entries):
        # Find title
        title_match = re.search(r'"title":\s*"(.*?)"', entry)
        if not title_match:
            continue
        title = title_match.group(1)
        
        # Find answers
        answers_match = re.search(r'"answers":\s*\[(.*?)\]', entry, re.DOTALL)
        if not answers_match:
            continue
        
        answers_text = answers_match.group(1)
        answer_count = answers_text.count('"') // 2
        
        if answer_count < 3:
            # Generate appropriate 3rd answer
            third_answer = generate_third_answer(title, answers_text)
            
            # Find the position to insert the new answer
            # Find the last answer in the list
            last_quote_pos = answers_text.rfind('"')
            if last_quote_pos == -1:
                continue
            
            # Insert after the last answer
            insert_pos = last_quote_pos + 1
            new_answers_text = answers_text[:insert_pos] + ',\n            "' + third_answer + '"' + answers_text[insert_pos:]
            
            # Replace in the entry
            new_entry = entry.replace(answers_text, new_answers_text)
            
            # Replace in the full content
            content = content.replace(entry, new_entry, 1)
            fixed_count += 1
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed {fixed_count} entries")
    return True

if __name__ == '__main__':
    filepath = r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py'
    fix_qa_answers(filepath)
