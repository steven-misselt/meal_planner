from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional
from enum import Enum
from datetime import date
from pint import UnitRegistry

ureg = UnitRegistry()
Quantity = ureg.Quantity

class BmrMode(Enum):
    """Enumeration for BMR calculation modes."""
    MIFFLIN_ST_JEOR = "mifflin_st_jeor"
    HARRIS_BENEDICT_REVISED = "harris_benedict_revised"
    KATCH_MCARDLE = "katch_mcardle"

    def __str__(self) -> str:
        return self.value

@dataclass
class Person:
    """Container for basic anthropometrics."""
    sex: Literal["male", "female"]
    _weight: Quantity = Quantity(0.0, "kg")  # Default weight in kg
    _height: Quantity = Quantity(0.0, "cm")  # Default height in cm
    _birthday: Optional[date] = None  # Optional birthday for age calculation
    _pal_category: Literal["sedentary", "low active", "active", "very active", "athlete"] = "sedentary"  # Physical Activity Level, default to sedentary
    body_fat_percent: Optional[float] = None  # needed for Katch–McArdle
    bmr_mode: BmrMode = BmrMode.MIFFLIN_ST_JEOR
    _weight_change_rate: Quantity = Quantity(0.0, "kg/week")  # Default weight change rate in kg/week

    @property
    def weight_change_rate(self, units: Literal["kg/week", "lb/week"] = "kg/week") -> float:
        """Weight change rate in specified units."""
        return self._weight_change_rate.to(units).magnitude
    
    def set_weight_change_rate(self, rate: float, units: Literal["kg/week", "lb/week"] = "kg/week") -> None:
        """Set weight change rate in specified units."""
        self._weight_change_rate = Quantity(rate, units).to("kg/week")

    def _get_daily_caloric_deviation(self) -> float:
        """Calculate daily caloric deviation based on weight change rate."""
        if self._weight_change_rate.magnitude == 0:
            return 0.0
        # 1 kg of body weight is approximately 7700 kcal
        return self._weight_change_rate.to("kg/week").magnitude * 7700 / 7.0
    
    @property
    def pal(self) -> float:
        """Physical Activity Level (PAL) multiplier based on category."""
        pal_values = {
            "sedentary": 1.2,
            "low active": 1.5,
            "active": 1.75,
            "very active": 2.2,
            "athlete": 2.5
        }
        return pal_values.get(self._pal_category, 1.0)

    def set_pal_category(self, category: Literal["sedentary", "low active", "active", "very active", "athlete"]) -> None:
        """Set the Physical Activity Level category."""
        if category not in ["sedentary", "low active", "active", "very active", "athlete"]:
            raise ValueError(f"Invalid PAL category: {category}")
        self._pal_category = category

    def get_pal_category(self) -> Literal["sedentary", "low active", "active", "very active", "athlete"]:
        """Get the current Physical Activity Level category."""
        return self._pal_category

    @property
    def age_years(self) -> float:
        """Age in years, calculated from birthday if available."""
        if self._birthday:
            today = date.today()
            return (today - self._birthday).days / 365.25

        raise ValueError("Birthday is not set, cannot calculate age.")
    
    @property
    def birthday(self) -> Optional[date]:
        """Birthday as a date object."""
        return self._birthday
    
    @birthday.setter
    def birthday(self, value: date) -> None:
        """Set the birthday."""
        if not isinstance(value, date):
            raise ValueError("Birthday must be a date object.")
        self._birthday = value
    
    def get_weight(self, units: Literal["lb", "kg"] = "kg") -> float:
        """Weight in units of 'lb' or 'kg'."""
        return self._weight.to(units).magnitude
    
    def set_weight(self, weight: float, units: Literal["lb", "kg"] = "kg") -> None:
        """Set weight in units of 'lb' or 'kg'."""
        self._weight = Quantity(weight, units).to("kg")

    def get_height(self, units: Literal["in", "cm"] = "cm") -> float:
        """Height in units of 'in' or 'cm'."""
        return self._height.to(units).magnitude
    
    def set_height(self, height: float, units: Literal["in", "cm"] = "cm") -> None:
        """Set height in units of 'in' or 'cm'."""
        self._height = Quantity(height, units).to("cm")

    def set_height_feet_inches(self, feet: int, inches: int) -> None:
        """Set height in feet and inches."""
        total_inches = feet * 12 + inches
        self.set_height(total_inches, "in")

    @property
    def bmr(self) -> float:
        """Calculate BMR based on the selected mode."""
        if self.bmr_mode == BmrMode.MIFFLIN_ST_JEOR:
            return self.bmr_mifflin_st_jeor()
        elif self.bmr_mode == BmrMode.HARRIS_BENEDICT_REVISED:
            return self.bmr_harris_benedict_revised()
        elif self.bmr_mode == BmrMode.KATCH_MCARDLE:
            return self.bmr_katch_mcardle()
        else:
            raise ValueError(f"Unknown BMR mode: {self.bmr_mode}")
        

    def bmr_mifflin_st_jeor(self) -> float:
        """BMR (kcal/day) via Mifflin–St Jeor.
        """
        s = 5 if self.sex == "male" else -161
        return 10*self.get_weight(units="kg") + 6.25*self.get_height(units="cm") - 5*self.age_years + s

    def bmr_harris_benedict_revised(self, p: Person) -> float:
        """BMR (kcal/day) via Harris–Benedict (Roza & Shizgal, 1984).
        """
        if p.sex == "male":
            return 13.397*self.get_weight(units="kg") + 4.799*self.get_height(units="cm") - 5.677*p.age_years + 88.362
        else:
            return 9.247*self.get_weight(units="kg") + 3.098*self.get_height(units="cm") - 4.330*p.age_years + 447.593

    def bmr_katch_mcardle(self, p: Person) -> float:
        """RMR/BMR (kcal/day) via Katch–McArdle using fat-free mass.
        Notes
        -----
        Requires `body_fat_percent`.
        """
        if p.body_fat_percent is None:
            raise ValueError("Katch–McArdle requires body_fat_percent.")
        ffm_kg = self.get_weight(units="kg") * (1 - p.body_fat_percent/100.0)
        return 370 + 21.6 * ffm_kg

    @property
    def tdee(self) -> float:
        """Total Daily Energy Expenditure (kcal/day) from BMR and PAL.
        Notes
        -----
        PAL bands (DRI): sedentary 1.0–<1.4, low active 1.4–<1.6,
        active 1.6–<1.9, very active 1.9–<2.5.
        """
        if self.pal <= 0:
            raise ValueError("PAL must be > 0.")
        return self.bmr * self.pal

    def daily_tci(self) -> float:
        """Daily Total Caloric Intake (kcal/day) based on weight change rate."""
        return self.tdee + self._get_daily_caloric_deviation()