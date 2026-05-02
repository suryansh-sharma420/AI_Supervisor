import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import AsyncGroq

from app.config import settings
from app.routers import events, runs, supervisors

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler for startup and shutdown events."""
    logger.info("Order Supervisor starting")
    
    # Initialize Groq client for Phase 3 LLM operations
    app.state.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    
    yield
    
    # Cleanup Groq client
    await app.state.groq_client.close()
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
app.include_router(events.router)  # CRITICAL: Added the missing events router


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}
