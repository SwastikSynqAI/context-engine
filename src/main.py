"""
Context Engine — Data Intelligence Layer
FastAPI application entry point.

Data entry model: human-first.
All entities, relationships, and context enter through deliberate human action —
either via the /entities and /relationships CRUD endpoints, or by manually
triggering an ingestion pull via POST /ingest/{source}.
Nothing runs automatically in the background.
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import context, decisions, entities, evals, health, ingest, oversight, rules as rules_module
from src.api.routes import hr as hr_module
from src.api.routes import auth as auth_module
from src.api.routes import hr_dashboard as hr_dashboard_module
from src.config import get_settings

settings = get_settings()

# ── Logging ───────────────────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(
    format="%(message)s",
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
)

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Scheduler paused — re-enable after HR rubric refinement
    # from src.workers.scheduler import create_scheduler
    # scheduler = create_scheduler()
    # scheduler.start()
    logging.getLogger(__name__).info("AI Hire — scheduler disabled (paused for HR review)")
    yield
    # scheduler.shutdown(wait=False)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    lifespan=lifespan,
    title="Context Engine",
    description=(
        "Data Intelligence Layer for YourCompany. "
        "Human-first: all data enters through deliberate human action. "
        "Use /entities and /relationships to add data manually, "
        "or POST /ingest/{source} to manually pull from a connected source."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.careers_form_origin,   # https://yourcompany.com — careers form
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(context.router)
app.include_router(decisions.router)
app.include_router(entities.router)
app.include_router(ingest.router)
app.include_router(rules_module.router)
app.include_router(rules_module.conflicts_router)
app.include_router(evals.router)
app.include_router(oversight.router)
app.include_router(hr_module.router)
app.include_router(auth_module.router)
app.include_router(hr_dashboard_module.router)

