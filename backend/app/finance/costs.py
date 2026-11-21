"""Incremental cost calculator requiring explicit, configurable assumptions.

No diesel, mileage, toll or allowance defaults are invented here. A missing input returns None.
"""
from dataclasses import dataclass

@dataclass
class CostInputs:
    distance_km: float | None
    diesel_inr_per_l: float | None
    mileage_km_per_l: float | None
    toll_inr: float | None
    driver_hours: float | None
    driver_inr_per_hour: float | None
    handling_inr: float | None = None

class CostCalculator:
    def __init__(self, inputs: CostInputs):
        self.inputs = inputs

    def fuel_cost(self) -> float | None:
        x=self.inputs
        if x.distance_km is None or x.diesel_inr_per_l is None or x.mileage_km_per_l is None or x.mileage_km_per_l <= 0: return None
        return (x.distance_km / x.mileage_km_per_l) * x.diesel_inr_per_l

    def driver_cost(self) -> float | None:
        x=self.inputs
        if x.driver_hours is None or x.driver_inr_per_hour is None: return None
        return x.driver_hours * x.driver_inr_per_hour

    def total(self) -> float | None:
        values=[self.fuel_cost(), self.inputs.toll_inr, self.driver_cost(), self.inputs.handling_inr]
        return None if any(v is None for v in values) else float(sum(values))
