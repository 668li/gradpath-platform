import re

with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find QA_SEEDS section
start = content.find('QA_SEEDS = [')
if start == -1:
    print("QA_SEEDS not found")
    exit()

# Find the end - look for the closing bracket at the right indentation level
bracket_count = 0
pos = start + len('QA_SEEDS = [')
for i in range(pos, len(content)):
    if content[i] == '[':
        bracket_count += 1
    elif content[i] == ']':
        if bracket_count == 0:
            end = i
            break
        bracket_count -= 1

qa_section = content[start:end]

# Count entries by counting 'title' keys
entries = re.findall(r'"title"', qa_section)
print(f'Current QA_SEEDS entries: {len(entries)}')

# Check how many have 3 answers
answer_groups = re.findall(r'"answers":\s*\[', qa_section)
print(f'Answer groups: {len(answer_groups)}')
