# -*- coding: utf-8 -*-
"""下载GitHub考研数据集"""
import sys, os, json, urllib.request, zipfile, io
sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = r"D:\职业规划\职业规划\backend\app\crawlers\real_data"

repos = [
    ("EvanYoy826/china-university-admission", "高校录取分数线"),
    ("LuoDaa/CN-Grad-Consult-Dataset", "考研咨询数据集"),
]

for repo, label in repos:
    print(f"Downloading {label} from {repo}...")
    try:
        url = f"https://github.com/{repo}/archive/main.zip"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib.request.urlopen(req, timeout=30)
        z = zipfile.ZipFile(io.BytesIO(response.read()))
        z.extractall(OUTPUT_DIR)
        print(f"  Extracted to {OUTPUT_DIR}/{repo.split('/')[1]}-main/")
    except Exception as e:
        print(f"  Error: {str(e)[:100]}")

print("\nDone!")
