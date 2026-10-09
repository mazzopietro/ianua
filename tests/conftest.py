import logging
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from ianua.api.dependencies import get_db
from ianua.core.config import settings
from ianua.main import app

@pytest.fixture
def client():
    yield TestClient(app)

    app.dependency_overrides.clear()

@pytest.fixture(scope="session")
def db_engine():
    if settings.test_database_url is None:
        raise RuntimeError("TEST_DATABASE_URL is not configured")

    engine = create_engine(settings.test_database_url)

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option(
        "sqlalchemy.url",
        settings.test_database_url,
    )

    command.upgrade(alembic_config, "head")

    yield engine

    command.downgrade(alembic_config, "base")
    engine.dispose()

@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()

    session = Session(bind=connection)

    session.begin_nested() # Crea una transazione annidata [PostgreSQL SAVEPOINT] 

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture
def db_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()