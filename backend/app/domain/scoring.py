"""Transparent deterministic baseline ranker; no untrained model is presented as AI."""
from __future__ import annotations

def baseline_score(candidate: dict) -> float | None:
    if candidate.get("eligible") != "pass":
        return None
    weight = candidate.get("weight_kg")
    net = candidate.get("net_inr", {}).get("expected")
    if weight is None or net is None:
        return None
    # Transparent demo baseline: reward positive net contribution and moderate payload use.
    capacity = candidate.get("available_payload_kg")
    utilization = (weight / capacity) if capacity and capacity > 0 else None
    if utilization is None:
        return None
    net_component = max(-1.0, min(1.0, net / 10000.0))
    utilization_component = 1.0 - min(1.0, abs(utilization - 0.65))
    return round(0.7 * net_component + 0.3 * utilization_component, 4)
