import re

# Count QA_SEEDS
with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('QA_SEEDS = [')
if start == -1:
    print("QA_SEEDS not found")
else:
    # Find the end by tracking bracket depth
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
    # Count entries by counting opening braces after the initial [
    entries = qa_section.count('{')
    print(f'QA_SEEDS entries: {entries}')

# Count GRAD_INTEL
with open(r'D:\职业规划\职业规划\backend\app\seed\seed_grad_intel.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('GRAD_INTEL = [')
if start == -1:
    print("GRAD_INTEL not found")
else:
    depth = 0
    end = start
    for i in range(start + len('GRAD_INTEL = ['), len(content)):
        if content[i] == '[':
            depth += 1
        elif content[i] == ']':
            if depth == 0:
                end = i
                break
            depth -= 1
    gi_section = content[start:end+1]
    # Count tuples
    entries = gi_section.count('("')
    print(f'GRAD_INTEL entries: {entries}')

# Count DARK_KNOWLEDGE
try:
    with open(r'D:\职业规划\职业规划\backend\app\seed\seed_dark_knowledge.py', 'r', encoding='utf-8') as f:
        content = f.read()
    start = content.find('DARK_KNOWLEDGE = [')
    if start == -1:
        print("DARK_KNOWLEDGE not found in file")
    else:
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
except FileNotFoundError:
    print('seed_dark_knowledge.py not found')
