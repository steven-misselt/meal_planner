# load_from_json.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

from sqlalchemy.orm import Session

from db import get_engine, init_db
from models import Recipe, Ingredient, Step, MealType, ScalingCategory


def load_recipe_dict(d: Dict[str, Any], session: Session) -> Recipe:
    # Build Recipe
    r = Recipe(
        name=d.get("name"),
        description=d.get("description"),
        cuisine=d.get("cuisine"),
        meal_type=MealType(d["meal_type"]) if d.get("meal_type") else None,
        scaling_category=ScalingCategory(d["scaling_category"]) if d.get("scaling_category") else None,
        active_time_length=(d.get("active_time") or {}).get("length"),
        active_time_units=(d.get("active_time") or {}).get("units"),
        total_time_length=(d.get("total_time") or {}).get("length"),
        total_time_units=(d.get("total_time") or {}).get("units"),
        number_of_servings=d.get("number_of_servings"),
        calories_per_serving=d.get("calories_per_serving"),
        nova_score=d.get("nova_score"),
    )

    # Ingredients
    for ing in d.get("ingredients", []) or []:
        r.ingredients.append(Ingredient(
            name=ing.get("name"),
            amount=ing.get("amount"),
            nova_score=ing.get("nova_score"),
            calories=ing.get("calories"),
            units=ing.get("units"),
        ))

    # Steps
    for st in d.get("steps", []) or []:
        r.steps.append(Step(
            step_number=st.get("step_number"),
            description=st.get("description") or "",
        ))

    session.add(r)
    return r


def load_recipe_file(path: str, db_url: str = "sqlite:///recipes.db") -> int:
    engine = get_engine(db_url)
    init_db(engine)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with Session(engine) as session:
        r = load_recipe_dict(data, session)

        # Optional: compute calories_per_serving if missing
        if r.calories_per_serving is None and r.number_of_servings and r.number_of_servings > 0:
            total_cals = sum((ing.calories or 0.0) for ing in r.ingredients)
            r.calories_per_serving = total_cals / r.number_of_servings

        session.commit()
        return r.id


if __name__ == "__main__":
    # Example: python load_from_json.py ./recipes/jsons/roasted_carrots.json
    import sys
    recipe_json_path = sys.argv[1]
    rid = load_recipe_file(recipe_json_path)
    print(f"Inserted recipe id={rid}")
