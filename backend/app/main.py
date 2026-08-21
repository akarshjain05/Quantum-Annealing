from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
import logging

from app.core.config import settings
from app.api import auth, core_data, optimization, qubo, scenarios, stress_tests, agent, audit, health

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("nostroq")

app = FastAPI(
    title=settings.APP_NAME,
    description=f"{settings.APP_TAGLINE} - decision-support prototype. No live financial transactions are executed.",
    version=settings.MODEL_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENV == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_and_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(f"request_id={request_id} path={request.url.path} unhandled_exception")
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(f"request_id={request_id} method={request.method} path={request.url.path} "
                f"status={response.status_code} duration_ms={duration_ms:.1f}")
    return response


for router_module in (health, auth, core_data, optimization, qubo, scenarios, stress_tests, agent, audit):
    app.include_router(router_module.router)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "tagline": settings.APP_TAGLINE,
        "docs": "/docs",
        "health": "/api/health",
        "notice": "Decision-support prototype for the GIFT City / GIFT IFIH Young Builders' Program hackathon. "
                   "Synthetic data only. No live financial transactions.",
    }
