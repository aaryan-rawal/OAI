"""Stable, explicit descriptions for core deterministic decision codes."""
DECISIONS = {
    "capacity": "Cargo weight must fit within the truck's available payload, not merely its maximum payload.",
    "route_mode": "Cargo pickup and drop must remain on the original route unless the driver enables off-route delivery.",
    "pickup_excursion": "The round-trip road excursion for the pickup must not exceed 40 km.",
    "drop_excursion": "The round-trip road excursion for the drop must not exceed 40 km.",
    "time_window": "The estimated arrival must fit the recorded pickup window.",
    "trip_distance_budget": "The additional road distance must remain within the whole-trip distance budget.",
    "trip_time_budget": "The added active time must remain within the whole-trip active-time budget.",
    "stop_order": "Pickup must occur before drop on the truck's unchanged original route.",
}
def human_readable_decision(decision_id: str) -> str:
    return DECISIONS.get(decision_id, f"{decision_id}: no verified description is registered.")
