import re

# Count GRAD_INTEL
with open('backend/app/seed/seed_grad_intel.py', 'r', encoding='utf-8') as f:
    gi_content = f.read()

gi_section = gi_content.split('GRAD_INTEL = [')[1].split(']\n\n\ndef ')[0]
gi_count = len(re.findall(r'    \("[^"]+",', gi_section))
print(f'GRAD_INTEL entries: {gi_count}')

# Count DARK_KNOWLEDGE in seed_grad_intel.py
dk_section = gi_content.split('DARK_KNOWLEDGE = [')[1].split(']\n\n\ndef ')[0]
dk_count = len(re.findall(r'    \("[^"]+", "[^"]+", "[^"]+",', dk_section))
print(f'DARK_KNOWLEDGE (seed_grad_intel): {dk_count}')

# Count DARK_KNOWLEDGE_SEED in grad_intel_service.py
with open('backend/app/services/grad_intel_service.py', 'r', encoding='utf-8') as f:
    svc_content = f.read()

svc_section = svc_content.split('DARK_KNOWLEDGE_SEED = [')[1].split('\n]\n\n\n# ')[0]
svc_count = len(re.findall(r'    "stage":', svc_section))
print(f'DARK_KNOWLEDGE_SEED (service): {svc_count}')

# Count experience posts
with open('backend/app/seed/seed_kaoyan_community.py', 'r', encoding='utf-8') as f:
    comm_content = f.read()

ep_section = comm_content.split('EXPERIENCE_POSTS = [')[1].split(']\n\n# =====')[0]
ep_count = ep_section.count('"title"')
print(f'EXPERIENCE_POSTS: {ep_count}')

qa_section = comm_content.split('QA_SEEDS = [')[1].split(']\n\n\ndef _get')[0]
qa_count = qa_section.count('"title"')
print(f'QA_SEEDS: {qa_count}')

# Count community authors
auth_section = comm_content.split('COMMUNITY_AUTHORS = [')[1].split(']\n\n# =====')[0]
auth_count = len(re.findall(r'\("', auth_section))
print(f'COMMUNITY_AUTHORS: {auth_count}')
