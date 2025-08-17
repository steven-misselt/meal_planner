from openai import OpenAI
import os
import json
import re
from pydantic import BaseModel
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_float(x: Any, default: float = 0.0) -> float:
    """Return x as float if possible, else default."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def annotate_recipe_json(path: str) -> Dict[str, Any]:
    """
    Read a recipe JSON file, add calories_per_serving and nova_score, and
    overwrite the file (atomically) with the updated content.

    Notes
    -----
    - **Authored by ChatGPT.**
    - `calories_per_serving` = (sum of ingredient calories) / `number_of_servings`
    - `nova_score` is computed as a calories-weighted average of ingredient NOVA
      scores: sum(nova_i * calories_i) / sum(calories_i).
      *If total weighted calories are 0*, falls back to the simple mean of
      available `nova_score`s. If no NOVA scores are present, sets `nova_score`
      to `None`.

    Parameters
    ----------
    path : str
        Path to the JSON recipe file.

    Returns
    -------
    Dict[str, Any]
        The updated recipe dictionary.

    Raises
    ------
    FileNotFoundError
        If `path` does not exist.
    ValueError
        If the JSON is missing required fields or is malformed.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No file found at: {path}")

    # Load
    with open(path, "r", encoding="utf-8") as f:
        try:
            data: Dict[str, Any] = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from e

    # Basic validation
    ingredients = data.get("ingredients")
    servings = data.get("number_of_servings")
    if not isinstance(ingredients, list):
        raise ValueError("'ingredients' must be a list.")
    if servings is None:
        raise ValueError("'number_of_servings' is required.")
    servings_f = _safe_float(servings, default=float("nan"))
    if not (servings_f > 0):
        raise ValueError("'number_of_servings' must be a positive number.")

    # Collect per-ingredient calories and nova
    cals: List[float] = []
    nova: List[Optional[float]] = []

    for ing in ingredients:
        if not isinstance(ing, dict):
            # Skip malformed entries but don't crash
            continue
        cal_i = _safe_float(ing.get("calories"), 0.0)
        # Clamp negatives to zero (defensive)
        cal_i = max(0.0, cal_i)
        cals.append(cal_i)

        nova_val = ing.get("nova_score")
        nova.append(float(nova_val) if isinstance(nova_val, (int, float)) else None)

    total_recipe_calories = sum(cals)
    calories_per_serving = total_recipe_calories / servings_f

    # Weighted NOVA by calories where NOVA is present
    weighted_num = 0.0
    weighted_den = 0.0
    plain_nova_vals: List[float] = []

    for cal_i, nova_i in zip(cals, nova):
        if nova_i is not None:
            plain_nova_vals.append(float(nova_i))
            if cal_i > 0:
                weighted_num += float(nova_i) * cal_i
                weighted_den += cal_i

    if weighted_den > 0:
        nova_score = weighted_num / weighted_den
    elif plain_nova_vals:
        # Fallback: unweighted mean if all calories are zero
        nova_score = sum(plain_nova_vals) / len(plain_nova_vals)
    else:
        nova_score = None  # No NOVA info available

    # Inject results at top level (overwrite if already present)
    data["calories_per_serving"] = calories_per_serving
    data["nova_score"] = nova_score

    # Atomic write (tmp + replace)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, path)

    return data


if __name__ == "__main__":
    # Example:
    # updated = annotate_recipe_json(r"C:\path\to\Buttermilk Yogurt Ranch Dressing.json")
    # print(updated["calories_per_serving"], updated["nova_score"])
    pass

class Ingredient(BaseModel):
    name: str | None
    amount: float | None
    nova_score: float | None
    calories: float | None
    units: str | None

class TimeInfo(BaseModel):
    length: float | None
    units: str | None

class Step(BaseModel):
    step_number: int
    description: str

class Recipe(BaseModel):
    name: str | None
    description: str | None
    cuisine: str | None
    meal_type: str | None
    ingredients: list[Ingredient] | None
    active_time: TimeInfo | None
    total_time: TimeInfo | None
    number_of_servings: float | None
    steps: list[Step] | None

def select_file(
    title="Select a file",
    filetypes=(("All files", "*.*"),),
    initialdir=None,
    multiple=False,
):
    """Open the native Windows file picker and return a path (or list of paths).

    Parameters
    ----------
    title : str
        Dialog window title.
    filetypes : tuple[tuple[str, str], ...]
        Filter patterns like (("Images", "*.png;*.jpg"), ("All files", "*.*")).
    initialdir : str | None
        Starting folder path.
    multiple : bool
        If True, allow selecting multiple files (returns list[str]).
    """
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()  # hide the empty root window
    root.update()    # fixes some focus issues on Windows

    if multiple:
        paths = filedialog.askopenfilenames(
            title=title, filetypes=filetypes, initialdir=initialdir
        )
        return list(paths) if paths else []
    else:
        path = filedialog.askopenfilename(
            title=title, filetypes=filetypes, initialdir=initialdir
        )
        return path or None


def create_file(client, file_path):
    # Function to create a file with the Files API

    with open(file_path, "rb") as file_content:
        result = client.files.create(
            file=file_content,
            purpose="vision",
        )
        return result.id


def add_recipe():
    
    # Create client using API key from environment
    client = OpenAI(api_key=os.environ.get("OPENAI_MEAL_PLANNER_API_KEY"))

    schema_instructions = """
        You are a recipe extraction assistant. 
        From the image provided, extract all available recipe information and return it in the given structure.

        Rules:
        - If any field is missing from the recipe, set its value to null.
        - Step numbers should be sequential starting from 1.
        - Times should be in minutes.
        - If a range is given for any number, use the average value.
        - Remember that things like Servings may be called something else like "Serves", "Makes", etc.
        - If the image is not a recipe, return null for all fields.
        - If a cuisine is not specified, do your best to infer it from the ingredients or context.
        - If the meal type is not specified, estimate it based on the ingredients and context. The options are: breakfast, lunch, dinner, snack, dessert, or beverage.
        - If calories are not specified, estimate for each ingredient.
        - If NOVA score is not specified, estimate for each ingredient and its processing level.
        - There maybe fragments of other recipes in the image, ignore them and focus on the main recipe.
        - If the recipe is in a different language, translate it to English.
        """

    print("Please select the recipe image file.")
    # Getting the file ID
    file_id = create_file(client, select_file())
    print("File uploaded successfully. File ID:", file_id)
    print("Parsing the recipe...")
    response = client.responses.parse(
        model="gpt-5",
        input=[
            {
                "role": "system",
                "content": schema_instructions,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "file_id": file_id,
                    },
                ],
            }
        ],
        text_format=Recipe,
    )
    print("Recipe parsing completed.")
    recipe: Recipe = response.output_parsed  # this is the parsed model

    
    # Convert to a plain dict (JSON-safe) and write to a file
    data = recipe.model_dump()
    recipe_name = data["name"]

    # Ensure folder exists
    recipes_dir = Path("recipes/jsons")
    recipes_dir.mkdir(parents=True, exist_ok=True)

    # Make a filesystem-safe name
    safe_name = re.sub(r'[\\/:*?"<>|]+', "_", recipe_name).strip()

    # Build the path object
    recipe_path = recipes_dir / f"{safe_name}.json"

    # Write the file (ignore the returned int)
    recipe_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Pass a real path to the function (str or Path both fine if the function handles it)
    data = annotate_recipe_json(os.fspath(recipe_path))
