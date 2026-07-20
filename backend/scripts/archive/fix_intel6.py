import random, uuid
from sqlalchemy import text
from app.database import engine
tiers = ['985','211','双一流','普通本科']
suppressions = ['none','light','moderate','heavy']
with engine.connect() as conn:
    uid = conn.execute(text("SELECT id FROM users LIMIT 1")).scalar()
    # Get existing combos
    existing = set()
    rows = conn.execute(text("SELECT school_name, major_name, year FROM grad_school_intel")).fetchall()
    for r in rows:
        existing.add((r[0], r[1], r[2]))
    print(f"Existing combos: {len(existing)}")
    # Get all schools and majors
    schools = [r[0] for r in conn.execute(text("SELECT DISTINCT school_name FROM grad_school_intel")).fetchall()]
    majors = [r[0] for r in conn.execute(text("SELECT DISTINCT major_name FROM grad_school_intel")).fetchall()]
    years = list(range(2020, 2027))
    print(f"Schools: {len(schools)}, Majors: {len(majors)}, Years: {len(years)}")
    target = 100000
    needed = target - len(existing)
    print(f"Need {needed} more combos")
    count = 0
    attempts = 0
    while count < needed and attempts < needed * 3:
        attempts += 1
        combo = (random.choice(schools), random.choice(majors), random.choice(years))
        if combo in existing:
            continue
        existing.add(combo)
        uni, maj, yr = combo
        conn.execute(text("""
            INSERT INTO grad_school_intel (id, user_id, school_name, major_name, school_tier, year,
                background_discrimination, first_choice_protection, score_suppression, transfer_friendly,
                data_sources, tags, is_ai_generated, created_at, updated_at)
            VALUES (gen_random_uuid(), :uid, :uni, :maj, :tier, :yr, :bd, :fcp, :ss, :tf,
                CAST(:ds AS jsonb), CAST(:tags AS jsonb), false, NOW(), NOW())
        """), {
            'uid': uid, 'uni': uni, 'maj': maj, 'tier': random.choice(tiers), 'yr': yr,
            'bd': random.choice(['none','light','medium','heavy']),
            'fcp': random.choice(['yes','no','partial']),
            'ss': random.choice(suppressions),
            'tf': random.choice(['friendly','normal','unfriendly']),
            'ds': '["gen3"]', 'tags': '[]'
        })
        count += 1
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM grad_school_intel')).scalar()
    print(f"Added {count}, total: {total}")
