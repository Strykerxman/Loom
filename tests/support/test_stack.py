"""Quarantined Docker/Uvicorn plumbing for integration and E2E tests.

Keep this file boring and isolated so normal tests stay readable.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import unquote, urlparse

import requests

from app.config import load_env


__test__ = False  # this is support code, not a pytest test module

ROOT_DIR = Path(__file__).resolve().parents[2]
TEST_ENV_FILE = ".env.test"
DEFAULT_TEST_BASE_URL = "http://127.0.0.1:8001"


def configure_test_environment() -> None:
    """Load `.env.test` once, before DB/session factories are imported."""
    os.environ.setdefault("ENV_FILE", TEST_ENV_FILE)
    os.environ.setdefault("BASE_URL", DEFAULT_TEST_BASE_URL)
    load_env(override=True)


def test_base_url() -> str:
    return os.getenv("BASE_URL", DEFAULT_TEST_BASE_URL)


def test_env() -> dict[str, str]:
    env = os.environ.copy()
    env["ENV_FILE"] = TEST_ENV_FILE
    env.setdefault("BASE_URL", test_base_url())
    env["PYTHONPATH"] = str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def assert_test_database() -> None:
    database_url = os.getenv("DATABASE_URL", "")

    if "test" not in database_url.lower():
        raise RuntimeError(
            "Refusing to run destructive test cleanup against a non-test database. "
            "Set ENV_FILE=.env.test or use a DATABASE_URL containing 'test'."
        )


def start_test_database() -> None:
    """Start Postgres from docker-compose.test.yml and apply migrations."""
    _run(_compose_cmd("up", "-d", "db_test"))
    _wait_for_test_db()
    _run([sys.executable, "-m", "alembic", "upgrade", "head"])


def stop_test_database() -> None:
    if os.getenv("KEEP_TEST_STACK") == "1":
        return

    subprocess.run(
        _compose_cmd("down", "-v"),
        cwd=ROOT_DIR,
        env=test_env(),
        check=False,
    )


@contextmanager
def running_uvicorn_server() -> Iterator[str]:
    """Run FastAPI on the host/port from BASE_URL for the lifetime of the context."""
    base_url = test_base_url()
    host, port = _host_and_port(base_url)

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=ROOT_DIR,
        env=test_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        _wait_for_http(f"{base_url}/", process)
        yield base_url
    finally:
        _stop_process(process)


def _compose_cmd(*args: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--env-file",
        str(ROOT_DIR / TEST_ENV_FILE),
        "-f",
        str(ROOT_DIR / "docker-compose.test.yml"),
        *args,
    ]


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT_DIR, env=test_env(), check=True)


def _wait_for_test_db(timeout_seconds: float = 30.0) -> None:
    db_user, db_name = _test_database_identity()
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        result = subprocess.run(
            _compose_cmd(
                "exec",
                "-T",
                "db_test",
                "pg_isready",
                "-U",
                db_user,
                "-d",
                db_name,
            ),
            cwd=ROOT_DIR,
            env=test_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        if result.returncode == 0:
            return

        time.sleep(0.5)

    raise RuntimeError("Timed out waiting for test Postgres container to become ready")


def _test_database_identity() -> tuple[str, str]:
    """Return pg_isready user/database from the loaded `.env.test` DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL", "")
    parsed = urlparse(database_url)

    if not parsed.scheme.startswith("postgresql"):
        raise RuntimeError("Test DATABASE_URL must be a PostgreSQL URL")

    db_user = unquote(parsed.username or "")
    db_name = unquote(parsed.path.lstrip("/"))

    if not db_user or not db_name:
        raise RuntimeError("Test DATABASE_URL must include a username and database name")

    return db_user, db_name


def _wait_for_http(
    url: str,
    process: subprocess.Popen,
    timeout_seconds: float = 30.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Uvicorn exited early with code {process.returncode}")

        try:
            response = requests.get(url, timeout=0.5)
            if response.status_code < 500:
                return
        except requests.RequestException:
            pass

        time.sleep(0.5)

    raise RuntimeError(f"Timed out waiting for Uvicorn at {url}")


def _host_and_port(base_url: str) -> tuple[str, int]:
    parsed = urlparse(base_url)
    return parsed.hostname or "127.0.0.1", parsed.port or 8001


def _stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
