import pytest
from fastapi.testclient import TestClient

from app.main import app

PASSWORD = 'test-password-for-local-checks'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DATA_DIR', str(tmp_path))
    monkeypatch.setenv('BOOTSTRAP_PASSWORD', PASSWORD)
    monkeypatch.setenv('DEMO_MODE', 'true')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    with TestClient(app, headers={'X-Requested-With': 'kitchen'}) as client:
        yield client


def login(client, account):
    r = client.post('/api/auth/login', json={'email': account + '@demo.local', 'password': PASSWORD})
    assert r.status_code == 200, r.text


def test_isolation_and_wiki_revision(client):
    login(client, 'front1')
    assert client.get('/healthz').status_code == 200
    assert client.get('/').status_code == 200
    assert client.post('/api/users', json={'email': 'x@y.com', 'password': PASSWORD}).status_code == 403
    assert client.post('/api/wiki/1/publish').status_code == 403
    assert client.get('/api/wiki/4').status_code == 404
    assert client.get('/api/wiki/4/revisions/1').status_code == 404
    answer = client.post('/api/chat', json={'question': '纸质加单与系统单冲突怎么办'}).json()
    assert answer['sources'] and answer['mode'] == 'extractive'
    assert '核对' in answer['answer']
    hidden = client.post('/api/chat', json={'question': '青柠望远镜'}).json()
    assert not hidden['sources'] and '青柠望远镜' not in hidden['answer']
    login(client, 'editor1')
    page = client.post('/api/wiki', json={'title': '新SOP', 'content': '紫色青椒必须调度确认后再交接。'}).json()['id']
    assert client.post(f'/api/wiki/{page}/publish').status_code == 200
    assert client.put(f'/api/wiki/{page}', json={'title': '新SOP', 'content': '紫色青椒改为两人签收后交接。'}).status_code == 200
    assert client.post(f'/api/wiki/{page}/publish').status_code == 200
    login(client, 'front1')
    result = client.post('/api/chat', json={'question': '紫色青椒'}).json()
    relevant = [s for s in result['sources'] if s['page_id'] == page]
    assert relevant and '两人签收' in relevant[0]['excerpt']
    assert client.get(relevant[0]['url']).json()['version'] == 2
    assert client.get(f'/api/wiki/{page}/revisions/1').status_code == 404


def test_event_idempotency_and_handoff(client):
    login(client, 'front1')
    body = {'source': 'pos', 'event_id': 'event-v2', 'order_no': 'A1', 'line_no': '1', 'version': 2, 'remark': '青椒肉丝 无特殊备注'}
    event = client.post('/api/events', json=body).json()
    assert event['outcome'] == 'applied'
    assert client.post('/api/events', json=body).json()['id'] == event['id']
    old = client.post('/api/events', json=body | {'event_id': 'event-v1', 'version': 1}).json()
    assert old['outcome'] == 'ignored'
    assert client.get('/api/orders').json()['orders'][0]['version'] == 2
    assert client.post(f"/api/events/{event['id']}/ack").status_code == 200
    assert client.post(f"/api/events/{event['id']}/ack").status_code == 200
    login(client, 'kitchen1')
    assert client.post(f"/api/events/{event['id']}/ack").status_code == 200
    order = client.get('/api/orders').json()['orders'][0]
    assert client.post(f"/api/orders/{order['id']}/status", json={'state': '已出品'}).status_code == 200
    login(client, 'front1')
    assert client.post(f"/api/orders/{order['id']}/status", json={'state': '已送达'}).status_code == 200
    conflict = client.post('/api/events', json=body | {'event_id': 'paper1', 'source': 'paper', 'remark': '纸单加辣'}).json()
    assert conflict['outcome'] == 'conflict'
    assert client.post(f"/api/events/{conflict['id']}/resolve").status_code == 403
    login(client, 'admin1')
    assert client.post(f"/api/events/{conflict['id']}/resolve").status_code == 200
    login(client, 'front2')
    assert client.get('/api/orders').json()['orders'] == []
    assert client.post(f"/api/events/{event['id']}/ack").status_code == 404


def test_disabled_tenant_and_request_origin(client):
    login(client, 'front1')
    assert client.post('/api/auth/logout', headers={'Origin': 'https://other.example'}).status_code == 403
    login(client, 'platform')
    assert client.get('/api/wiki').status_code == 403
    assert client.patch('/api/platform/tenants/1', json={'enabled': False}).status_code == 200
    assert client.post('/api/auth/login', json={'email': 'front1@demo.local', 'password': PASSWORD}).status_code == 403


def test_restart_preserves_data(client):
    from app.store import initialize
    login(client, 'editor1')
    page = client.post('/api/wiki', json={'title': '持久化检查', 'content': '重启后保留这份草稿。'}).json()['id']
    initialize()
    assert client.get(f'/api/wiki/{page}').json()['content'] == '重启后保留这份草稿。'
