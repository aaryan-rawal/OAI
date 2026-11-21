"""Versioned, no-imputation feature contract shared by serving and training."""
from __future__ import annotations
from typing import Any

FEATURE_SCHEMA_VERSION = "1.0"
FEATURES = (
    "cargo_weight_kg",
    "available_payload_kg",
    "payload_utilization",
    "extra_distance_km",
    "extra_active_minutes",
    "pickup_offset_km",
    "drop_offset_km",
    "original_route_distance_km",
    "net_contribution_inr",
    "pickup_window_slack_minutes",
)
RISK_FEATURES = tuple(name for name in FEATURES if name != "net_contribution_inr")


def build_features(candidate: dict, route: dict, feature_names: tuple[str, ...] = FEATURES) -> dict[str, float] | None:
    """Return a complete numeric vector or None; missing values are never zero-filled."""
    weight = candidate.get("weight_kg")
    capacity = candidate.get("available_payload_kg")
    if weight is None or capacity is None or float(capacity) <= 0:
        return None
    net = (candidate.get("net_inr") or {}).get("expected")
    start = candidate.get("pickup_window_start")
    end = candidate.get("pickup_window_end")
    slack = candidate.get("pickup_window_slack_minutes")
    if slack is None and start and end:
        from datetime import datetime
        try:
            a = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
            b = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
            slack = (b - a).total_seconds() / 60
        except (TypeError, ValueError):
            return None
    values: dict[str, Any] = {
        "cargo_weight_kg": weight,
        "available_payload_kg": capacity,
        "payload_utilization": float(weight) / float(capacity),
        "extra_distance_km": candidate.get("extra_distance_km"),
        "extra_active_minutes": candidate.get("extra_active_minutes"),
        "pickup_offset_km": candidate.get("pickup_at_km"),
        "drop_offset_km": candidate.get("drop_at_km"),
        "original_route_distance_km": route.get("distance_km"),
        "net_contribution_inr": net,
        "pickup_window_slack_minutes": slack,
    }
    result = {}
    for key in feature_names:
        value = values.get(key)
        if value is None:
            return None
        number = float(value)
        if not __import__("math").isfinite(number):
            return None
        result[key] = number
    return result
