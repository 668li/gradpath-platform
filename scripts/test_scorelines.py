# -*- coding: utf-8 -*-
import sys; sys.stdout.reconfigure(encoding='utf-8')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
resp = client.get('/api/grad-intel/scorelines?limit=5')
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    count = len(data) if isinstance(data, list) else 'N/A'
    print(f'Items: {count}')
    if data and isinstance(data, list):
        print(f'First: {data[0].get("university_name", "")}')
else:
    print(f'Error: {resp.text[:300]}')
