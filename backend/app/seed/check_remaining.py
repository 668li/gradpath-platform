import re

with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('QA_SEEDS = [')
depth = 0
end = start
for i in range(start + len('QA_SEEDS = ['), len(content)):
    if content[i] == '[':
        depth += 1
    elif content[i] == ']':
        if depth == 0:
            end = i
            break
        depth -= 1
qa_section = content[start:end+1]

entries = qa_section.split('{')[1:]
for idx, entry in enumerate(entries):
    answers_match = re.search(r'"answers":\s*\[(.*?)\]', entry, re.DOTALL)
    if answers_match:
        answers_text = answers_match.group(1)
        answer_count = answers_text.count('"') // 2
        if answer_count != 3:
            title_match = re.search(r'"title":\s*"(.*?)"', entry)
            title = title_match.group(1) if title_match else 'Unknown'
            print(f'Entry {idx+1}: {answer_count} answers - {title[:60]}')
