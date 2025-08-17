# models.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, Text, ForeignKey, Enum, DateTime, UniqueConstraint, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    pass


# Optional enums (keep values aligned with your JSON)
class MealType(str, enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    dessert = "dessert"
    snack = "snack"
    beverage = "beverage"
    condiment = "condiment"


class ScalingCategory(str, enum.Enum):
    discrete = "discrete"
    continuous = "continuous"


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    cuisine: Mapped[Optional[str]] = mapped_column(String(64))
    meal_type: Mapped[Optional[MealType]] = mapped_column(Enum(MealType), default=None)
    scaling_category: Mapped[Optional[ScalingCategory]] = mapped_column(Enum(ScalingCategory), default=None)

    # Times (store as length + units to match your JSON)
    active_time_length: Mapped[Optional[float]] = mapped_column(Float)
    active_time_units: Mapped[Optional[str]] = mapped_column(String(32))
    total_time_length: Mapped[Optional[float]] = mapped_column(Float)
    total_time_units: Mapped[Optional[str]] = mapped_column(String(32))

    number_of_servings: Mapped[Optional[float]] = mapped_column(Float)
    calories_per_serving: Mapped[Optional[float]] = mapped_column(Float)
    nova_score: Mapped[Optional[float]] = mapped_column(Float)

    # Timestamps & basic uniqueness
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    ingredients: Mapped[List["Ingredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="Ingredient.id"
    )
    steps: Mapped[List["Step"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="Step.step_number"
    )

    __table_args__ = (
        UniqueConstraint("name", "cuisine", name="uq_recipe_name_cuisine"),  # tweak for your needs
        Index("ix_recipe_name", "name"),
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[Optional[str]] = mapped_column(String(255))
    amount: Mapped[Optional[float]] = mapped_column(Float)
    nova_score: Mapped[Optional[float]] = mapped_column(Float)
    calories: Mapped[Optional[float]] = mapped_column(Float)
    units: Mapped[Optional[str]] = mapped_column(String(64))

    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)

    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="steps")
