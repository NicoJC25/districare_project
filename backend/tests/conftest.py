import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.api.router import router
from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.messaging.rabbitmq import RabbitMQPublisher


@pytest.fixture()
def db_session(monkeypatch):
    monkeypatch.setattr(RabbitMQPublisher, "publish", lambda self, routing_key, payload: True)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, headers={"X-API-Key": settings.api_key}) as test_client:
        yield test_client
    app.dependency_overrides.clear()
