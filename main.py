"""Uppcoder entrypoint. Runtime credentials stay in the private data directory."""
import json
import os
from pathlib import Path
import secrets

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('DEMO_MODE', 'true')
os.environ.setdefault('COOKIE_SECURE', 'true')
data_dir = Path(os.getenv('DATA_DIR', str(Path(__file__).parent / 'data'))).resolve()
data_dir.mkdir(parents=True, exist_ok=True)
os.environ['DATA_DIR'] = str(data_dir)
credentials_path = data_dir / 'cloud-credentials.json'
if not credentials_path.exists():
    credentials = {
        'BOOTSTRAP_PASSWORD': os.getenv('BOOTSTRAP_PASSWORD') or secrets.token_urlsafe(24),
        'JWT_SECRET': os.getenv('JWT_SECRET') or secrets.token_urlsafe(48),
    }
    try:
        with credentials_path.open('x', encoding='utf-8') as file:
            file.write(json.dumps(credentials))
        credentials_path.chmod(0o600)
    except FileExistsError:
        pass
credentials = json.loads(credentials_path.read_text(encoding='utf-8'))
for key, value in credentials.items():
    os.environ.setdefault(key, value)
access_path = data_dir / 'initial-access.txt'
if not access_path.exists():
    access_path.write_text(
        'Tenant administrator: admin1@demo.local\n'
        'Front desk: front1@demo.local\n'
        'Kitchen: kitchen1@demo.local\n'
        'Wiki editor: editor1@demo.local\n'
        'Platform administrator: platform@demo.local\n'
        'Initial password: ' + os.environ['BOOTSTRAP_PASSWORD'] + '\n',
        encoding='utf-8',
    )
    access_path.chmod(0o600)

from app.main import app  # noqa: E402,F401
