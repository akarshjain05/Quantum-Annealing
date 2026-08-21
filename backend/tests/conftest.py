import os
import sys
import tempfile
import pytest

TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "nostroq_test.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import Base, engine  # noqa: E402
from app.seed.seed_data import run_seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    Base.metadata.create_all(bind=engine)
    run_seed(reset=True)
    yield


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_headers(client):
    resp = client.post("/api/auth/login", json={"email": "treasury@demo-bank.com", "password": "DemoPassword123!"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
