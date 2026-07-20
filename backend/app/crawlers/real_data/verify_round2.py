import json

with open(r"D:\职业规划\职业规划\backend\app\crawlers\real_data\kaoyan_round2.json", encoding='utf-8') as f:
    data = json.load(f)

print(f"Total articles: {len(data)}")
print(f"Total chars: {sum(a['char_count'] for a in data):,}")

cats = {}
for a in data:
    cat = a["category"]
    if cat not in cats:
        cats[cat] = {"count": 0, "chars": 0}
    cats[cat]["count"] += 1
    cats[cat]["chars"] += a["char_count"]

print("\nBy category:")
for cat, stats in cats.items():
    print(f"  {cat}: {stats['count']} articles, {stats['chars']:,} chars")