import re

with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the 3 entries with 1 answer and add 2 more
# We'll search for patterns that indicate 1-answer entries

# Pattern 1: Find entries where answers array has only 1 string
# Look for "answers": ["..."] pattern (single string in array)
pattern = r'"answers":\s*\[\s*"([^"]+)"\s*\]'
matches = list(re.finditer(pattern, content))

for match in matches:
    # Get the answer text
    answer = match.group(1)
    # Generate 2 more answers based on context
    # Find the title of this entry
    pos = match.start()
    # Go back to find the title
    title_search = content.rfind('"title":', 0, pos)
    if title_search == -1:
        continue
    title_end = content.find('"', title_search + 9)
    title = content[title_search + 9:title_end]
    
    # Generate appropriate additional answers
    new_answers = []
    if '408' in title or '数据结构' in title or 'KMP' in title:
        new_answers = [
            "KMP的next数组通过递推计算：next[0]=-1，next[j]是s[0..j-1]最长相等前后缀长度。理解这个定义是关键。",
            "建议结合王道辅导书和真题来复习，重点理解核心概念，多做练习题巩固。祝复习顺利！"
        ]
    elif '高等数学' in title or '极限' in title:
        new_answers = [
            "极限是高数的基础，掌握洛必达法则和等价无穷小替换是关键。多做题多总结，形成自己的解题套路。",
            "建议结合王道辅导书和真题来复习，重点理解核心概念，多做练习题巩固。祝复习顺利！"
        ]
    elif '英语' in title or '小三门' in title:
        new_answers = [
            "小三门指完形填空、新题型和翻译。完形性价比低但不能放弃，新题型有套路可循，翻译要练习长难句拆分。",
            "英语复习贵在坚持，每天保持一定的学习量。真题是最好的复习资料，建议反复精读。"
        ]
    else:
        new_answers = [
            "建议多做真题，总结出题规律。保持良好的复习节奏，相信自己一定能成功。",
            "祝考研顺利！坚持就是胜利，相信自己的努力一定会有回报。"
        ]
    
    # Replace the single answer with 3 answers
    old_text = match.group(0)
    new_text = f'"answers": [\n            "{answer}",\n            "{new_answers[0]}",\n            "{new_answers[1]}",\n        ]'
    content = content.replace(old_text, new_text, 1)
    print(f'Fixed: {title[:50]}')

with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done fixing remaining entries!")
