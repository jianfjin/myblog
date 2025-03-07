import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import Base, get_db
import os

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Override the get_db dependency
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

# Test client
client = TestClient(app)

# Setup and teardown
@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    if os.path.exists("./test.db"):
        os.remove("./test.db")

# Test cases
def test_signup():
    response = client.post(
        "/auth/signup",
        data={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/articles"

def test_login():
    # First create a user
    client.post(
        "/auth/signup",
        data={"username": "testuser", "password": "testpass"}
    )
    
    # Then try to login
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    assert "access_token" in response.cookies

def test_invalid_login():
    response = client.post(
        "/auth/login",
        data={"username": "wronguser", "password": "wrongpass"}
    )
    assert response.status_code == 401

def test_logout():
    # First create and login a user
    client.post(
        "/auth/signup",
        data={"username": "testuser", "password": "testpass"}
    )
    client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass"}
    )
    
    # Then logout
    response = client.get("/auth/logout")
    assert response.status_code == 200
    assert "access_token" not in response.cookies