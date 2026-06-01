from dataclasses import dataclass
from typing import Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

HealthState = Literal["ok", "unhealthy"]


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: HealthState

    @property
    def is_ok(self) -> bool:
        return self.status == "ok"


def check_database(db: Session) -> HealthCheck:
    """Return whether the database accepts a minimal query."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return HealthCheck(name="database", status="unhealthy")

    return HealthCheck(name="database", status="ok")
