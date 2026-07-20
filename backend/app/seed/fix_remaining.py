import re

with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find entries with 1 answer and add 2 more
# The entries are identified by their titles
fixes = [
    ("高等数学极限应用", [
        "极限是高数的基础，掌握洛必达法则和等价无穷小替换是关键。多做题多总结，形成自己的解题套路。",
        "建议结合王道辅导书和真题来复习，重点理解核心概念，多做练习题巩固。祝复习顺利！"
    ]),
    ("考研英语小三门", [
        "小三门指完形填空、新题型和翻译。完形性价比低但不能放弃，新题型有套路可循，翻译要练习长难句拆分。",
        "英语复习贵在坚持，每天保持一定的学习量。真题是最好的复习资料，建议反复精读。"
    ]),
    ("408 数据结构 KMP 算法 next 数组怎么", [
        "KMP的next数组通过递推计算：next[0]=-1，next[j]是s[0..j-1]最长相等前后缀长度。理解这个定义是关键。",
        "建议结合王道辅导书和真题来复习，重点理解核心概念，多做练习题巩固。祝复习顺利！"
    ]),
]

for title_part, new_answers in fixes:
    # Find the entry
    pos = content.find(title_part)
    if pos == -1:
        print(f"Could not find: {title_part}")
        continue
    
    # Find the answers array for this entry
    # Go back to find the opening brace
    entry_start = content.rfind('{', 0, pos)
    # Find the answers array
    answers_start = content.find('"answers":', entry_start)
    if answers_start == -1:
        print(f"Could not find answers for: {title_part}")
        continue
    
    # Find the opening bracket of answers
    bracket_start = content.find('[', answers_start)
    # Find the closing bracket
    bracket_end = content.find(']', bracket_start)
    
    # Get current answers
    current_answers = content[bracket_start:bracket_end+1]
    answer_count = current_answers.count('"') // 2
    
    if answer_count == 1:
        # Add 2 more answers
        # Find the position before the closing bracket
        insert_pos = bracket_end
        # Add comma and new answers
        new_text = ',\n            "' + new_answers[0] + '",\n            "' + new_answers[1] + '"'
        content = content[:insert_pos] + new_text + content[insert_pos:]
        print(f"Fixed: {title_part}")

with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
