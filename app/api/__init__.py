from fastapi import APIRouter
from .endpoints.evaluate import router as eval_router
from .endpoints.health import router as health_router
from .endpoints.status import router as status_router
from .endpoints.report import router as report_router

router = APIRouter()

router.include_router(health_router, tags=["Health"])
router.include_router(eval_router, tags=["Evaluation"], prefix="/eval")
router.include_router(status_router, tags=["Status"], prefix="/eval")
router.include_router(report_router, tags=["Report"], prefix="/eval")

__all__ = ["router"]