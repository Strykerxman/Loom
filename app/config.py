import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]


def load_env(*, override: bool = False) -> None:
    """Load the dotenv file selected by ENV_FILE.

    Defaults to `.env`. Tests set ENV_FILE to `.env.test` and use
    `override=True` so test settings win over already-loaded dev settings.
    """
    env_file = os.getenv("ENV_FILE", ".env")
    load_dotenv(ROOT_DIR / env_file, override=override)
