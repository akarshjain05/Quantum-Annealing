import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app_name": settings.APP_NAME,
        "env": settings.ENV,
        "database": db_status,
        "redis": "not required for synchronous demo-scale optimization (see docs/limitations.md)",
        "optimizer": "ok",
        "llm_status": "enabled" if (settings.LLM_PROVIDER and settings.ANTHROPIC_API_KEY) else "disabled (deterministic agent fallback active)",
        "knowledge_base": "ok",
        "model_version": settings.MODEL_VERSION,
        "qubo_version": settings.QUBO_VERSION,
    }
