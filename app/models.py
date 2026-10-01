from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional, List
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text, DateTime, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


# ── Auth & Family ──────────────────────────────────────────────

class Family(Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    invite_code: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    members: Mapped[list["User"]] = relationship(
        "User", back_populates="family", foreign_keys="User.family_id"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color: Mapped[str] = mapped_column(String, default="#666666")
    family_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("families.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    family: Mapped[Optional["Family"]] = relationship(
        "Family", back_populates="members", foreign_keys=[family_id]
    )

    @property
    def display_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name


# ── Default colors for family members ─────────────────────────

DEFAULT_COLORS = [
    "#b5451b",  # burnt sienna
    "#2d6a4f",  # forest green
    "#1e4a7a",  # navy blue
    "#7b2d8b",  # purple
    "#c77b18",  # amber
    "#1a8a8a",  # teal
    "#a83253",  # rose
    "#4a6741",  # sage
]


# ── Recipes ────────────────────────────────────────────────────

class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    servings: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    prep_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cook_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    total_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    is_modified: Mapped[bool] = mapped_column(Boolean, default=False)
    family_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("families.id"), nullable=True
    )

    ingredients: Mapped[list["Ingredient"]] = relationship(
        "Ingredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    directions: Mapped[list["Direction"]] = relationship(
        "Direction", back_populates="recipe", cascade="all, delete-orphan"
    )
    tools: Mapped[list["Tool"]] = relationship(
        "Tool", back_populates="recipe", cascade="all, delete-orphan"
    )
    spices: Mapped[list["Spice"]] = relationship(
        "Spice", back_populates="recipe", cascade="all, delete-orphan"
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE")
    )
    text: Mapped[str] = mapped_column(String)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="ingredients")


class Direction(Base):
    __tablename__ = "directions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE")
    )
    step_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="directions")


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="tools")


class Spice(Base):
    __tablename__ = "spices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="spices")


# ── Calendar ───────────────────────────────────────────────────

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    family_members: Mapped[str] = mapped_column(String)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    family_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("families.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def member_list(self) -> list:
        """Return family_members as a list of names."""
        return [n.strip() for n in self.family_members.split(",") if n.strip()]

    @property
    def member_colors(self) -> list:
        """Return list of (name, color) tuples for template rendering."""
        from app.database import SessionLocal
        colors = []
        db = SessionLocal()
        try:
            for name in self.member_list:
                user = db.query(User).filter(
                    User.first_name == name, User.family_id == self.family_id
                ).first()
                color = user.color if user else "#666666"
                colors.append((name, color))
        finally:
            db.close()
        return colors

    @property
    def primary_color(self) -> str:
        """Return the first member's color (for single-color contexts)."""
        colors = self.member_colors
        return colors[0][1] if colors else "#666666"


# ── Tasks ──────────────────────────────────────────────────────────────────

class TaskList(Base):
    __tablename__ = "task_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    list_type: Mapped[str] = mapped_column(String, nullable=False, default="shopping")
    assigned_to: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    family_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("families.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[list["TaskItem"]] = relationship(
        "TaskItem", back_populates="task_list", cascade="all, delete-orphan"
    )
    assignee: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_to]
    )


class TaskItem(Base):
    __tablename__ = "task_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_list_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("task_lists.id", ondelete="CASCADE")
    )
    text: Mapped[str] = mapped_column(String, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_to: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)

    task_list: Mapped["TaskList"] = relationship("TaskList", back_populates="items")
    assignee: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_to]
    )


# ── Calorie Tracker ───────────────────────────────────────────────────────────

class CalorieEntry(Base):
    __tablename__ = "calorie_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    food_name: Mapped[str] = mapped_column(String)
    servings: Mapped[float] = mapped_column(Float)
    serving_size: Mapped[str] = mapped_column(String)
    meal: Mapped[str] = mapped_column(String)
    date: Mapped[date] = mapped_column(Date, index=True)
    calories: Mapped[int] = mapped_column(Integer)
    protein: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carbs: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
