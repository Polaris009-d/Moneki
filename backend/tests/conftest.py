import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.config import settings  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _ensure_db():
    """数据库不存在时（如全新 clone）自动跑 init_db.py 建库。"""
    if not settings.db_path.exists():
        subprocess.run(
            [sys.executable, str(BACKEND / "scripts" / "init_db.py")],
            check=True,
        )


@pytest.fixture()
def db():
    from app.database import SessionLocal

    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
