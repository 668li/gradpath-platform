import re

# Count DARK_KNOWLEDGE
with open(r'D:\职业规划\职业规划\backend\app\seed\seed_grad_intel.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('DARK_KNOWLEDGE = [')
depth = 0
end = start
for i in range(start + len('DARK_KNOWLEDGE = ['), len(content)):
    if content[i] == '[':
        depth += 1
    elif content[i] == ']':
        if depth == 0:
            end = i
            break
        depth -= 1
dk_section = content[start:end+1]
entries = dk_section.count('{')
print(f'DARK_KNOWLEDGE entries: {entries}')

# Check answers per QA entry
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

# Count answers per entry
# Split by entries (each starts with {)
entries_list = qa_section.split('{')[1:]  # skip first empty split
total_answers = 0
for entry in entries_list:
    answers_match = re.search(r'"answers":\s*\[(.*?)\]', entry, re.DOTALL)
    if answers_match:
        answers_text = answers_match.group(1)
        # Count quoted strings (each answer is a quoted string)
        answer_count = answers_text.count('"') // 2
        total_answers += answer_count

print(f'Total QA entries: {len(entries_list)}')
print(f'Total answers: {total_answers}')
print(f'Average answers per entry: {total_answers / len(entries_list):.1f}')

# Check if all entries have exactly 3 answers
entries_with_3 = 0
for entry in entries_list:
    answers_match = re.search(r'"answers":\s*\[(.*?)\]', entry, re.DOTALL)
    if answers_match:
        answers_text = answers_match.group(1)
        answer_count = answers_text.count('"') // 2
        if answer_count == 3:
            entries_with_3 += 1
print(f'Entries with exactly 3 answers: {entries_with_3}/{len(entries_list)}')
