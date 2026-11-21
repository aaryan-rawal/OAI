"""Explicit-input active-time and incremental-cost calculations."""
from __future__ import annotations
from typing import Any

def calculate_extra_active_minutes(
    pickup_excursion_minutes: float | None,
    drop_excursion_minutes: float | None,
    loading_minutes: float | None,
    unloading_minutes: float | None,
    waiting_minutes: float | None,
) -> float | None:
    values=(pickup_excursion_minutes,drop_excursion_minutes,loading_minutes,unloading_minutes,waiting_minutes)
    if any(value is None for value in values):
        return None
    return float(sum(values))

def calculate_incremental_cost_and_net(
    revenue_inr: float | None,
    extra_distance_km: float | None,
    extra_active_minutes: float | None,
    overrides: dict[str, Any] | None,
) -> tuple[float | None,float | None]:
    required=("diesel_inr_per_l","mileage_km_per_l","toll_inr_per_km","driver_inr_per_hour","handling_fee_inr")
    if revenue_inr is None or extra_distance_km is None or extra_active_minutes is None or overrides is None:
        return None,None
    if any(overrides.get(key) is None for key in required):
        return None,None
    mileage=float(overrides["mileage_km_per_l"])
    if mileage <= 0: return None,None
    fuel=(extra_distance_km/mileage)*float(overrides["diesel_inr_per_l"])
    toll=extra_distance_km*float(overrides["toll_inr_per_km"])
    driver=(extra_active_minutes/60)*float(overrides["driver_inr_per_hour"])
    handling=float(overrides["handling_fee_inr"])
    cost=float(fuel+toll+driver+handling)
    return round(cost,2),round(float(revenue_inr)-cost,2)
