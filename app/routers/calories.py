from __future__ import annotations

from datetime import date, timedelta
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_login
from app.database import get_db
from app.models import MEAL_TYPES, FoodEntry, User

router = APIRouter(prefix="/calories")
templates = Jinja2Templates(directory="app/templates")

def _parse_date(date_str: Optional[str]) -> date:
    if date_str:
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            pass
    return date.today()


def _parse_amount(value: Optional[str]) -> Optional[float]:
    """Parse an optional non-negative number from a form field."""
    if value is None or value.strip() == "":
        return None
    amount = float(value)
    if amount < 0:
        raise ValueError("Nutrition values cannot be negative")
    return amount


def _redirect(day: date, message: Optional[str] = None) -> RedirectResponse:
    params = {"date": day.isoformat()}
    if message:
        params["message"] = message
    url = f"/calories?{urlencode(params)}"
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


def _totals(entries: list[FoodEntry]) -> dict[str, float]:
    return {
        "calories": sum(e.calories or 0 for e in entries),
        "protein_g": sum(e.protein_g or 0 for e in entries),
        "carbs_g": sum(e.carbs_g or 0 for e in entries),
        "fat_g": sum(e.fat_g or 0 for e in entries),
    }


@router.get("")
def calorie_log(
    request: Request,
    date_str: Optional[str] = Query(None, alias="date"),
    message: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """Show the current user's food log for a single day, grouped by meal."""
    day = _parse_date(date_str)
    entries = (
        db.query(FoodEntry)
        .filter(FoodEntry.user_id == current_user.id, FoodEntry.date == day)
        .order_by(FoodEntry.created_at.asc(), FoodEntry.id.asc())
        .all()
    )
    meals = {
        meal: [e for e in entries if e.meal == meal] for meal in MEAL_TYPES
    }
    return templates.TemplateResponse(
        "calories.html",
        {
            "request": request,
            "current_user": current_user,
            "day": day,
            "prev_day": day - timedelta(days=1),
            "next_day": day + timedelta(days=1),
            "is_today": day == date.today(),
            "meals": meals,
            "meal_totals": {meal: _totals(items) for meal, items in meals.items()},
            "day_totals": _totals(entries),
            "message": message,
        },
    )


@router.post("/add")
def add_food_entry(
    request: Request,
    entry_date: str = Form(...),
    meal: str = Form(...),
    food_name: str = Form(...),
    serving_size: Optional[str] = Form(None),
    calories: str = Form(...),
    protein_g: Optional[str] = Form(None),
    carbs_g: Optional[str] = Form(None),
    fat_g: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """Log a food item for one of the user's meals."""
    day = _parse_date(entry_date)
    if meal not in MEAL_TYPES:
        return _redirect(day, "Error: Invalid meal")
    if not food_name.strip():
        return _redirect(day, "Error: Food name is required")
    try:
        calorie_amount = _parse_amount(calories)
        protein = _parse_amount(protein_g)
        carbs = _parse_amount(carbs_g)
        fat = _parse_amount(fat_g)
    except ValueError:
        return _redirect(day, "Error: Nutrition values must be non-negative numbers")
    if calorie_amount is None:
        return _redirect(day, "Error: Calories are required")

    db.add(
        FoodEntry(
            user_id=current_user.id,
            date=day,
            meal=meal,
            food_name=food_name.strip(),
            serving_size=(serving_size or "").strip() or None,
            calories=calorie_amount,
            protein_g=protein,
            carbs_g=carbs,
            fat_g=fat,
        )
    )
    db.commit()
    return _redirect(day, f"Added {food_name.strip()} to {meal}")


@router.post("/{entry_id}/delete")
def delete_food_entry(
    request: Request,
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """Delete one of the user's food entries."""
    entry = (
        db.query(FoodEntry)
        .filter(FoodEntry.id == entry_id, FoodEntry.user_id == current_user.id)
        .first()
    )
    if not entry:
        return _redirect(date.today(), "Error: Entry not found")
    day = entry.date
    db.delete(entry)
    db.commit()
    return _redirect(day, "Entry deleted")
