from __future__ import annotations

import logging
import os
from datetime import date
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status
from starlette.middleware.sessions import SessionMiddleware

from app.auth import get_current_user, _LoginRequired, _FamilyRequired
from app.database import Base, engine, get_db
from app.models import Recipe, Event, User, TaskList
from app.family import get_family_members
from app.routers import recipes, calendar, auth
from app.routers import family_routes
from app.routers import tasks
from app.routers import calories

# ── Logging ──────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),                         # keep console output
        RotatingFileHandler(                             # write to logs/app.log
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,                    # rotate at 5 MB
            backupCount=3,                               # keep 3 old files
        ),
    ],
)

# Quiet down noisy libraries; bump up for debugging
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Create FastAPI app instance
app = FastAPI(title="Family Portal")

# Session middleware for auth (change the secret in production!)
app.add_middleware(SessionMiddleware, secret_key="change-me-to-a-real-secret-key")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(family_routes.router)
app.include_router(recipes.router)
app.include_router(calendar.router)
app.include_router(tasks.router)
app.include_router(calories.router)

# Setup templates
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def startup_event():
    """Create all database tables on startup."""
    Base.metadata.create_all(bind=engine)
    logger.info("Family Portal started — logging to %s", LOG_FILE)


@app.exception_handler(_LoginRequired)
async def login_required_handler(request: Request, exc: _LoginRequired):
    """Redirect to login when user is not authenticated."""
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.exception_handler(_FamilyRequired)
async def family_required_handler(request: Request, exc: _FamilyRequired):
    """Redirect to family setup when user has no family."""
    return RedirectResponse(url="/family", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/")
def dashboard(request: Request):
    """Family portal dashboard."""
    db = next(get_db())
    try:
        current_user = get_current_user(request, db)
        if current_user is None:
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

        if current_user.family_id is None:
            return RedirectResponse(url="/family", status_code=status.HTTP_303_SEE_OTHER)

        family_id = current_user.family_id

        recent_recipes = (
            db.query(Recipe)
            .filter(Recipe.family_id == family_id)
            .order_by(Recipe.created_at.desc())
            .limit(4)
            .all()
        )

        today = date.today()
        upcoming_events = (
            db.query(Event)
            .filter(Event.family_id == family_id, Event.date >= today)
            .order_by(Event.date.asc(), Event.start_time.asc())
            .limit(5)
            .all()
        )

        family_members = get_family_members(family_id)

        recent_task_lists = (
            db.query(TaskList)
            .filter(TaskList.family_id == family_id)
            .order_by(TaskList.created_at.desc())
            .limit(5)
            .all()
        )
    finally:
        db.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user,
        "recent_recipes": recent_recipes,
        "upcoming_events": upcoming_events,
        "family_members": family_members,
        "recent_task_lists": recent_task_lists,
    })
