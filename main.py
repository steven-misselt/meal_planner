from nutrition import Person
from datetime import date

def main():
    # Example usage of the Person class and BMR calculations
    p = Person(sex="male")
    p.set_weight(weight=205, units="lb")
    p.set_height_feet_inches(feet=6, inches=2)
    p.birthday = date(year=1999, month=7, day=21)

    print(f"The person's BMR is: {p.bmr} kcal/day")

if __name__ == "__main__":
    main()