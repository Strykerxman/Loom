from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.health import check_database

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
def health() -> dict[str, str]:
    """Liveness: the API process can receive and answer HTTP requests."""
    return {
        "status": "ok",
        "service": "loom-api",
    }


@router.get("/health/live", status_code=status.HTTP_200_OK)
def liveness() -> dict[str, str]:
    """Explicit liveness endpoint for systems that prefer /live naming."""
    return health()


@router.get("/health/db", status_code=status.HTTP_200_OK)
def database_health(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Dependency check: the API can talk to PostgreSQL."""
    database = check_database(db)

    if not database.is_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "checks": {database.name: database.status},
            },
        )

    return {
        "status": "ok",
        "checks": {database.name: database.status},
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK)
def readiness(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Readiness: the API is alive and its required DB dependency responds."""
    database = check_database(db)

    if not database.is_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "checks": {
                    "api": "ok",
                    database.name: database.status,
                },
            },
        )

    return {
        "status": "ok",
        "checks": {
            "api": "ok",
            database.name: database.status,
        },
    }
