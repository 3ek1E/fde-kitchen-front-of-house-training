"""Run against a demo instance without editing its persistent records."""
import os

import httpx

base = os.getenv('TEST_BASE_URL', 'http://127.0.0.1:8000')
password = os.environ['BOOTSTRAP_PASSWORD']
with httpx.Client(base_url=base, headers={'X-Requested-With': 'kitchen'}, timeout=20) as client:
    assert client.get('/healthz').json()['status'] == 'ok'
    assert client.get('/').status_code == 200
    assert client.get('/api/wiki').status_code == 401
    assert client.post('/api/auth/login', json={'email': 'front1@demo.local', 'password': password}).status_code == 200
    pages = client.get('/api/wiki').json()
    assert pages
    reply = client.post('/api/chat', json={'question': '过敏备注缺失怎么办'}).json()
    assert reply['sources']
    source = client.get(reply['sources'][0]['url'])
    assert source.status_code == 200
    assert client.post('/api/wiki/1/publish').status_code == 403
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/auth/me').status_code == 401
print('HTTP smoke passed: health, login, Wiki, RAG, citation, permissions, logout')
