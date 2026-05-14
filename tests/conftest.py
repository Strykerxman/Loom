import os

import pytest
from sqlalchemy import text

from app.config import load_env


os.environ.setdefault("ENV_FILE", ".env.test")
load_env(override=True)

from app.database.database import SessionLocal  # noqa: E402


def _assert_test_database() -> None:
    database_url = os.getenv("DATABASE_URL", "")

    if "test" not in database_url.lower():
        raise RuntimeError(
            "Refusing to run destructive test cleanup against a non-test database. "
            "Set ENV_FILE=.env.test or use a DATABASE_URL containing 'test'."
        )


@pytest.fixture
def db_session():
    _assert_test_database()

    db = SessionLocal()

    try:
        db.execute(text("TRUNCATE TABLE tasks, jobs RESTART IDENTITY CASCADE"))
        db.commit()

        yield db

    finally:
        db.rollback()
        db.close()
