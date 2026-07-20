import re
content = open('backend/app/seed/seed_kaoyan_community.py', 'r', encoding='utf-8').read()

# Count EXPERIENCE_POSTS
ep_section = content.split('EXPERIENCE_POSTS = [')[1].split(']\n\n# =====')[0]
ep_count = ep_section.count('"title"')
print(f'EXPERIENCE_POSTS: {ep_count}')

# Count QA_SEEDS
qa_match = re.search(r'QA_SEEDS = \[(.*?)\]', content, re.DOTALL)
if qa_match:
    qa_content = qa_match.group(1)
    qa_count = qa_content.count('"title"')
    print(f'QA_SEEDS: {qa_count}')
else:
    print('QA_SEEDS: not found')

# Check if _get_or_create_authors exists
if '_get_or_create_authors' in content:
    print('_get_or_create_authors: exists')
else:
    print('_get_or_create_authors: MISSING')
