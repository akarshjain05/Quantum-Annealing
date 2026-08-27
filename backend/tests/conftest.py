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


from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db
    
    def override_get_db():
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def auth_headers(client):
    resp = client.post("/api/auth/login", json={"email": "treasury@demo-bank.com", "password": "DemoPassword123!"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

