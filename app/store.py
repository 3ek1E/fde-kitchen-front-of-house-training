import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from pwdlib import PasswordHash

passwords = PasswordHash.recommended()


def directory():
    default = '/tmp/kitchen-data' if os.getenv('VERCEL') else './data'
    path = Path(os.getenv('DATA_DIR', default))
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def database():
    conn = sqlite3.connect(directory() / 'kitchen.sqlite', timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def secret():
    configured = os.getenv('JWT_SECRET')
    if configured:
        return configured
    path = directory() / '.jwt-secret'
    if not path.exists():
        try:
            with path.open('x') as file:
                file.write(secrets.token_urlsafe(48))
        except FileExistsError:
            pass
    return path.read_text()


def audit(db, user, action, target):
    db.execute('INSERT INTO audit(tenant_id, actor, action, target) VALUES(?,?,?,?)',
               (user['tenant_id'], user['email'], action, str(target)))


def initialize():
    with database() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS tenants(id INTEGER PRIMARY KEY, name TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, tenant_id INTEGER REFERENCES tenants(id), email TEXT UNIQUE NOT NULL,
          password TEXT NOT NULL, role TEXT NOT NULL, station TEXT NOT NULL DEFAULT 'front', enabled INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS pages(id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL REFERENCES tenants(id), title TEXT NOT NULL,
          published_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY, page_id INTEGER NOT NULL REFERENCES pages(id), version INTEGER NOT NULL,
          content TEXT NOT NULL, author TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(page_id,version));
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL REFERENCES tenants(id), source TEXT NOT NULL,
          event_id TEXT NOT NULL, order_no TEXT NOT NULL, line_no TEXT NOT NULL, version INTEGER NOT NULL, remark TEXT NOT NULL,
          outcome TEXT NOT NULL, front_ack TEXT, kitchen_ack TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(tenant_id,source,event_id));
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL REFERENCES tenants(id), order_no TEXT NOT NULL,
          line_no TEXT NOT NULL, version INTEGER NOT NULL, remark TEXT NOT NULL, source TEXT NOT NULL, state TEXT DEFAULT '待确认',
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(tenant_id,order_no,line_no));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, tenant_id INTEGER, actor TEXT NOT NULL, action TEXT NOT NULL,
          target TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        ''')
        if db.execute('SELECT count(*) FROM users').fetchone()[0]:
            return
        bootstrap = os.getenv('BOOTSTRAP_PASSWORD', '')
        if len(bootstrap) < 12:
            raise RuntimeError('Set BOOTSTRAP_PASSWORD to at least 12 characters before first startup')
        hashed = passwords.hash(bootstrap)
        db.execute("INSERT INTO users(email,password,role) VALUES('platform@demo.local',?,'platform_admin')", (hashed,))
        if os.getenv('DEMO_MODE', 'false').lower() != 'true':
            return
        for tenant_id, name in [(1, '知味餐饮'), (2, '隔离测试门店')]:
            db.execute('INSERT INTO tenants(id,name) VALUES(?,?)', (tenant_id, name))
            for prefix, role, station in [('admin', 'tenant_admin', 'dispatch'), ('editor', 'editor', 'dispatch'),
                                           ('front', 'member', 'front'), ('kitchen', 'member', 'kitchen')]:
                email = f'{prefix}{tenant_id}@demo.local'
                db.execute('INSERT INTO users(tenant_id,email,password,role,station) VALUES(?,?,?,?,?)',
                           (tenant_id, email, hashed, role, station))
            docs = [('加单与出品交接', '合成演示 SOP。纸质加单与 POS 系统单冲突时暂停相关订单行，调度联系前厅核对原订单号和菜品，保留关键备注，前厅与后厨分别确认。出品和送达分别记录。'),
                    ('过敏备注人工复核', '合成演示 SOP。过敏备注缺失时暂停出品，请食品安全负责人核实过敏原、食品温度和替代方案，人工确认并留痕后继续。'),
                    ('断线恢复与对账', '合成演示 SOP。接口断开后使用纸单与电话交接，显示暂未更新与快照时间。恢复后按业务编号和事件编号去重补齐，逐单对账。')]
            if tenant_id == 2:
                docs.append(('租户专属资料', '第二租户专属暗号是青柠望远镜。'))
            for title, content in docs:
                page_id = db.execute('INSERT INTO pages(tenant_id,title) VALUES(?,?)', (tenant_id, title)).lastrowid
                revision_id = db.execute('INSERT INTO revisions(page_id,version,content,author) VALUES(?,1,?,?)',
                                         (page_id, content, 'seed')).lastrowid
                db.execute('UPDATE pages SET published_id=? WHERE id=?', (revision_id, page_id))
