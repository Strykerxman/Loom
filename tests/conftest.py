import pytest
from sqlalchemy import text

from tests.support.test_stack import (
    assert_test_database,
    configure_test_environment,
    running_uvicorn_server,
    start_test_database,
    stop_test_database,
)


configure_test_environment()

from app.database.database import get_session_factory, reset_session_factory_cache  # noqa: E402

reset_session_factory_cache()


def pytest_addoption(parser):
    parser.addoption(
        "--run-e2e",
        action="store_true",
        help="run full-stack tests that start Uvicorn/workers",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-e2e"):
        return

    skip_e2e = pytest.mark.skip(reason="need --run-e2e to run full-stack E2E tests")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)


@pytest.fixture(scope="session")
def test_database():
    try:
        start_test_database()
        yield
    finally:
        stop_test_database()


@pytest.fixture(scope="session")
def uvicorn_server(test_database):
    with running_uvicorn_server() as base_url:
        yield base_url


@pytest.fixture
def db_session(test_database):
    assert_test_database()

    SessionLocal = get_session_factory()
    db = SessionLocal()

    try:
        db.execute(text("TRUNCATE TABLE tasks, jobs RESTART IDENTITY CASCADE"))
        db.commit()
        yield db
    finally:
        db.rollback()
        db.close()
