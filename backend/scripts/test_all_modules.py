"""全模块 API 烟雾测试 - 验证所有功能模块"""
import requests

base_url = 'http://localhost:8000/api'

modules = [
    # 职业规划核心模块
    ('职业决策', '/decisions'),
    ('职业事件', '/events'),
    ('技能评估', '/skills'),
    ('回顾反思', '/retrospectives'),
    ('仪表盘', '/dashboard'),
    ('职业档案', '/career-profile'),
    ('职业规划', '/career-plans'),
    ('评估测试', '/assessment'),
    
    # 社区功能
    ('社区帖子', '/posts'),
    ('社区评论', '/community'),
    
    # AI 功能
    ('AI 对话', '/chat/conversations'),
    ('AI 导师', '/mentors/personas'),
    
    # 护城河功能
    ('生命之轮', '/life-wheel'),
    ('成长模式', '/growth-patterns'),
    ('连续打卡', '/streaks'),
    ('主动洞察', '/proactive-insights'),
    ('决策日志', '/decision-journal'),
    ('生命设计', '/life-design'),
    ('决策分析', '/decision-analyses'),
    
    # 考研模块
    ('考研导师', '/mentors/kaoyan-mentors'),
    ('考研情报', '/grad-intel/dark-knowledge/list'),
    ('考研经验贴', '/kaoyan/experience-posts'),
    ('考研问答', '/kaoyan/qa'),
    
    # 求职模块
    ('求职情报', '/career-intel/companies'),
    ('公务员情报', '/civil-service-intel/posts'),
]

print('=' * 70)
print('全模块 API 烟雾测试')
print('=' * 70)

success_count = 0
fail_count = 0

for name, endpoint in modules:
    try:
        resp = requests.get(f'{base_url}{endpoint}', timeout=3)
        status = '✅' if resp.status_code == 200 else '❌'
        if resp.status_code == 200:
            success_count += 1
        else:
            fail_count += 1
        print(f'{status} {name:15s} {endpoint:40s} -> {resp.status_code}')
    except Exception as e:
        fail_count += 1
        print(f'❌ {name:15s} {endpoint:40s} -> ERROR: {str(e)[:30]}')

print('=' * 70)
print(f'测试结果: 成功 {success_count} / 失败 {fail_count} / 总计 {len(modules)}')
print('=' * 70)
