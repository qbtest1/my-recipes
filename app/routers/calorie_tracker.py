from __future__ import annotations

from datetime import date as entry_date
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_family
from app.database import get_db
from app.models import CalorieEntry, User

router = APIRouter(prefix="/calorie-tracker")
templates = Jinja2Templates(directory="app/templates")
MEALS = ("breakfast", "lunch", "dinner")


@router.get("")
def list_entries(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Group only the current user's entries by day and meal."""
    entries = (
        db.query(CalorieEntry)
        .filter(CalorieEntry.user_id == current_user.id)
        .order_by(CalorieEntry.date.desc(), CalorieEntry.id.asc())
        .all()
    )
    grouped_entries = {}
    for entry in entries:
        if entry.date not in grouped_entries:
            grouped_entries[entry.date] = {meal: [] for meal in MEALS}
        grouped_entries[entry.date][entry.meal].append(entry)

    return templates.TemplateResponse(
        "calorie_tracker.html",
        {
            "request": request,
            "current_user": current_user,
            "grouped_entries": grouped_entries,
        },
    )


@router.post("/add")
def add_entry(
    request: Request,
    food_name: str = Form(...),
    servings: float = Form(...),
    serving_size: str = Form(...),
    meal: str = Form(...),
    date: str = Form(...),
    calories: int = Form(...),
    protein: Optional[str] = Form(None),
    carbs: Optional[str] = Form(None),
    fat: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Record per-serving nutrition privately for the current user."""
    if meal not in MEALS:
        raise HTTPException(status_code=422, detail="Choose breakfast, lunch, or dinner")
    try:
        recorded_date = entry_date.fromisoformat(date)
        protein_value = float(protein) if protein else None
        carbs_value = float(carbs) if carbs else None
        fat_value = float(fat) if fat else None
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date or nutrition value")

    entry = CalorieEntry(
        user_id=current_user.id,
        food_name=food_name.strip(),
        servings=servings,
        serving_size=serving_size.strip(),
        meal=meal,
        date=recorded_date,
        calories=calories,
        protein=protein_value,
        carbs=carbs_value,
        fat=fat_value,
    )
    db.add(entry)
    db.commit()
    return RedirectResponse(
        url="/calorie-tracker",
        status_code=status.HTTP_303_SEE_OTHER,
    )
