from openai import OpenAI
import os
import json
from pydantic import BaseModel
from pathlib import Path

class Ingredient(BaseModel):
    name: str | None
    amount: float | None
    units: str | None

class TimeInfo(BaseModel):
    length: float | None
    units: str | None

class Step(BaseModel):
    step_number: int
    description: str

class Recipe(BaseModel):
    name: str | None
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


def main():
    
    # Create client using API key from environment
    client = OpenAI(api_key=os.environ.get("OPENAI_MEAL_PLANNER_API_KEY"))

    schema_instructions = """
        You are a recipe extraction assistant. 
        From the image provided, extract all available recipe information and return it in the given structure.

        Rules:
        - If any field is missing from the recipe, set its value to null.
        - Step numbers should be sequential starting from 1.
        - Times should be in minutes.
        """

    # Getting the file ID
    file_id = create_file(client, select_file())

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

    recipe: Recipe = response.output_parsed  # this is the parsed model

    # Convert to a plain dict (JSON-safe) and write to a file
    data = recipe.model_dump()
    recipe_name = data["name"]
    Path(f"recipes\\jsons\\{recipe_name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(data)


if __name__ == "__main__":
    main()
