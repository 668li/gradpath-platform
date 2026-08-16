# -*- coding: utf-8 -*-
"""Probe: parse embedded escaped JSON from Fortune China 500 ranking page."""
import json
import re
import sys

path = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\_company_probe\cf500.html"
html = open(path, encoding="utf-8").read()

# literal marker in file: {\"data\":[
marker = '{\\"data\\":'
i = html.find(marker)
print("marker at:", i)
if i < 0:
    sys.exit("marker not found")

window = html[i:]
# unescape one level of JS string escaping
window = window.replace('\\"', '"').replace("\\\\", "\\")
obj, end = json.JSONDecoder().raw_decode(window)
recs = obj["data"]
print("records:", len(recs))
print("keys:", sorted(recs[0].keys()))
for r in recs[:3] + recs[-2:]:
    print({k: r.get(k) for k in ("rk", "nm", "ind", "prov", "city", "emp")})

# check website-ish fields
sample_keys = set()
for r in recs:
    sample_keys.update(r.keys())
print("all keys union:", sorted(sample_keys))
# check company detail link pattern in html
links = re.findall(r'href="(/fortune500/company/china500/\d+/[^"]*)"', html)
print("detail links:", len(links), links[:3])
