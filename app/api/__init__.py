from fastapi import APIRouter
from .endpoints.evaluate import router as eval_router
from .endpoints.status import router as status_router

router = APIRouter()

router.include_router(eval_router, tags=["Evaluation"], prefix="/evaluate")
router.include_router(status_router, tags=["Status"])

__all__ = ["router"]