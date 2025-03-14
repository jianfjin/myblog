import pytest
import asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from myblog.database import get_db  # Replace with your actual import
from myblog.models import User  # Replace with your actual import
from myblog.routers.auth import (router as auth_router, get_password_hash, create_access_token, login, login_page, logout, verify_password, 
                                 signup_page, signup, get_current_user,  # Replace with your actual import
                                 SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES)  # Replace with your actual import


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

# FastAPI app for testing
test_app = FastAPI()
test_app.include_router(auth_router, prefix="/auth")

# Dependency override for get_db
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

test_app.dependency_overrides[get_db] = override_get_db

# Event loop fixture
@pytest.fixture(scope="session")
def event_loop():
    """Provide an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Async session fixture
@pytest.fixture(scope="function")
async def test_session():
    """Provide an async session for database operations."""
    async with TestingSessionLocal() as session:
        yield session

# Async client fixture
@pytest.fixture(scope="function")
async def client():
    """Provide an async test client."""
    async with AsyncClient(app=test_app, base_url="http://testserver") as ac:
        yield ac

# Test user fixture
@pytest.fixture(scope="function")
async def test_user(test_session: AsyncSession):
    """Create a test user in the database."""
    user = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password="hashed_testpassword"  # Replace with your password hashing logic
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user

def test_verify_password():
    """Test password verification with correct and incorrect passwords."""
    password = "testpassword"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_get_password_hash():
    """Test that password hashing produces a verifiable hash."""
    password = "testpassword"
    hashed = get_password_hash(password)
    assert hashed != password  # Hash should differ from plain password
    assert verify_password(password, hashed) is True

def test_create_access_token():
    """Test JWT token creation with default and custom expiration."""
    data = {"sub": "testuser"}
    
    # Test default expiration (15 minutes)
    token = create_access_token(data)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "testuser"
    assert "exp" in payload
    assert payload["exp"] > int(datetime.utcnow().timestamp())

    # Test custom expiration (5 minutes)
    expires_delta = timedelta(minutes=5)
    token = create_access_token(data, expires_delta)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["exp"] <= int((datetime.utcnow() + timedelta(minutes=5)).timestamp()) + 1  # 1-second leeway

def test_login_page(client):
    """Test that the login page returns a 200 status and HTML content."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    """Test successful login with valid credentials."""
    form_data = {"username": "testuser", "password": "testpassword"}
    response = await client.post("/auth/login", data=form_data)
    assert response.status_code == 200
    # Add additional assertions as needed, e.g., checking cookies or response content

@pytest.mark.asyncio
async def test_login_invalid_username(client: AsyncClient):
    """Test login with an invalid username raises 401."""
    form_data = {"username": "nonexistentuser", "password": "testpassword"}
    response = await client.post("/auth/login", data=form_data)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_user: User):
    """Test login with an invalid password raises 401."""
    form_data = {"username": "testuser", "password": "wrongpassword"}
    response = await client.post("/auth/login", data=form_data)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_login_missing_username(client: AsyncClient):
    """Test login with missing username raises 401."""
    form_data = {"password": "testpassword"}
    response = await client.post("/auth/login", data=form_data)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_login_missing_password(client: AsyncClient):
    """Test login with missing password raises 401."""
    form_data = {"username": "testuser"}
    response = await client.post("/auth/login", data=form_data)
    assert response.status_code == 401

@pytest.mark.asyncio
def test_signup_page(client):
    """Test that the signup page returns a 200 status and HTML content."""
    response = client.get("/auth/signup")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_signup_new_user(client, test_session):
    """Test signing up a new user creates the user and sets a token."""
    form_data = {"username": "newuser", "password": "newpassword"}
    response = client.post("/auth/signup", data=form_data)
    assert response.status_code == 303
    assert response.headers["location"] == "/articles"
    assert "access_token" in response.cookies

    # Verify user in database
    query = select(User).where(User.username == "newuser")
    result = await test_session.execute(query)
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.username == "newuser"

@pytest.mark.asyncio
async def test_signup_existing_user(client, test_user, test_session):
    """Test signing up with an existing username redirects to login."""
    form_data = {"username": "testuser", "password": "testpassword"}
    response = client.post("/auth/signup", data=form_data)
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"

    # Verify no duplicate user created
    query = select(User).where(User.username == "testuser")
    result = await test_session.execute(query)
    users = result.scalars().all()
    assert len(users) == 1  # Only the original test_user


@pytest.mark.asyncio
def test_logout(client):
    """Test logout deletes the access_token cookie."""
    # Set a cookie first (simulating a logged-in state)
    response = client.get("/auth/logout")
    assert response.status_code == 200
    # Check if cookie is deleted (TestClient sets empty value or removes it)
    assert "access_token" not in response.cookies or response.cookies["access_token"] == ""

@pytest.mark.asyncio
def test_token_success(client, test_user):
    """Test token endpoint with valid credentials returns a token."""
    form_data = {"username": "testuser", "password": "testpassword"}
    response = client.post("/auth/token", data=form_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    payload = jwt.decode(response.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "testuser"

@pytest.mark.asyncio
def test_token_invalid_credentials(client):
    """Test token endpoint with invalid credentials raises 401."""
    form_data = {"username": "testuser", "password": "wrongpassword"}
    response = client.post("/auth/token", data=form_data)
    assert response.status_code == 401
    assert "access_token" not in response.json()

from starlette.requests import Request

@pytest.mark.asyncio
async def test_get_current_user_valid_cookie_token(test_session, test_user):
    """Test get_current_user with a valid token in cookie."""
    token = create_access_token({"sub": "testuser"})
    request = Request({"type": "http", "headers": {}, "cookies": {"access_token": f"Bearer {token}"}})
    user = await get_current_user(request=request, db=test_session)
    assert user.username == "testuser"

@pytest.mark.asyncio
async def test_get_current_user_valid_header_token(test_session, test_user):
    """Test get_current_user with a valid token in Authorization header."""
    token = create_access_token({"sub": "testuser"})
    request = Request({"type": "http", "headers": {"authorization": f"Bearer {token}"}})
    user = await get_current_user(request=request, token=token, db=test_session)
    assert user.username == "testuser"

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(test_session):
    """Test get_current_user with an invalid token raises 401."""
    token = "invalidtoken"
    request = Request({"type": "http", "cookies": {"access_token": f"Bearer {token}"}})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(request=request, db=test_session)
    assert exc.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user_missing_token(test_session):
    """Test get_current_user with no token redirects to login."""
    request = Request({"type": "http", "headers": {}, "cookies": {}})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(request=request, db=test_session)
    assert exc.value.status_code == 303
    assert exc.value.headers["Location"] == "/login"
