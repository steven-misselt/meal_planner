from nutrition import Person
from datetime import date
from recipes import add_recipe, select_file
from load_from_json import load_recipe_file
import os

def main():
    # # Example usage of the Person class and BMR calculations
    # p = Person(sex="male")
    # p.set_weight(weight=205, units="lb")
    # p.set_height_feet_inches(feet=6, inches=2)
    # p.birthday = date(year=1999, month=7, day=21)
    # p.set_pal_category(category="low active")  # Set PAL category
    # p.set_weight_change_rate(rate=-2.0, units="lb/week")
    # print(f"The person's BMR is: {p.bmr} kcal/day")
    # print(f"The person's TDEE is: {p.tdee} kcal/day")
    # print(f"The person's daily TCI is: {p.daily_tci()} kcal/day")

    add_recipe(add_to_database=True)

    # recipe_path = select_file()
    # recipe_id = load_recipe_file(os.fspath(recipe_path))
    # print(f"Recipe added to database with ID: {recipe_id}")

if __name__ == "__main__":
    main()