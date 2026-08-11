import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine

from database.session import get_session
from main import app


TEST_DATABASE_URL = "sqlite:///./test.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={
        "check_same_thread": False
    }
)


@pytest.fixture
def client():
    # Create tables in the test database
    SQLModel.metadata.create_all(
        test_engine
    )

    # Provide the test database session
    def get_test_session():
        with Session(test_engine) as session:
            yield session

    # Override the application's database dependency
    app.dependency_overrides[get_session] = (
        get_test_session
    )

    # Disable the production database startup
    original_startup = getattr(
        app.router,
        "on_startup",
        []
    )

    app.router.on_startup = []

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        # Restore startup handlers
        app.router.on_startup = original_startup

        # Remove dependency override
        app.dependency_overrides.clear()

        # Remove test tables
        SQLModel.metadata.drop_all(
            test_engine
        )


@pytest.fixture
def test_user():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }


@pytest.fixture
def auth_headers(client, test_user):
    response = client.post(
        "/register",
        json=test_user
    )

    assert response.status_code == 201

    response = client.post(
        "/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }