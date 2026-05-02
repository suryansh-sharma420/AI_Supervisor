import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.routers import events, runs, supervisors, trigger, wake
from app.scheduler.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Order Supervisor starting")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    app.state.async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    start_scheduler(app)

    try:
        yield
    finally:
        stop_scheduler()
        await app.state.groq_client.close()
        await engine.dispose()
        logger.info("Order Supervisor shutting down")


app = FastAPI(title="Order Supervisor", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(supervisors.router)
app.include_router(runs.router)
app.include_router(events.router)
app.include_router(trigger.router)
app.include_router(wake.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}
