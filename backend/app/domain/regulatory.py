"""Fail-closed regulatory assessment gate.

No legal thresholds are hard-coded here. E-way bill applicability/validity,
heavy-vehicle access windows, hazardous-goods obligations, and over-dimensional
permits vary by jurisdiction, route, consignment, vehicle, and effective date.
A trusted jurisdiction adapter must supply a current, source-referenced
assessment before a candidate can pass this gate.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from app.config import settings

REQUIRED_REGULATORY_CHECKS = (
    "eway_bill",
    "heavy_vehicle_access",
    "hazardous_goods",
    "over_dimensional",
    "driver_hours_rest",
    "vehicle_documents",
    "transport_permit",
    "vehicle_load_limits",
)


def expected_eway_bill_validity_days(distance_km: float, over_dimensional_cargo: bool = False) -> int:
    """Return the portal's distance-based EWB validity-day count.

    This is a planning helper only; actual applicability, start time, extensions,
    exemptions and validity must be checked against the live EWB record.
    Current portal FAQ: regular movement uses 200 km/day; ODC uses 20 km/day.
    """
    import math
    distance = float(distance_km)
    if not math.isfinite(distance) or distance <= 0:
        raise ValueError("Distance must be a finite positive number of kilometres.")
    increment = 20.0 if over_dimensional_cargo else 200.0
    return int(math.ceil(distance / increment))


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def evaluate_regulatory_assessment(assessment: dict | None) -> list[dict]:
    """Return pass/fail/unknown checks from a trusted, unexpired policy assessment."""
    trusted = {x.strip() for x in settings.REGULATORY_TRUSTED_SOURCES.split(",") if x.strip()}
    now = datetime.now(timezone.utc)
    if not isinstance(assessment, dict):
        return [{"rule_code": code, "label": label, "verdict": "unknown", "value": None,
                 "threshold": None, "unit": None, "claim_tag": "fact",
                 "message": "No authoritative, route-specific regulatory assessment is available; applicability and compliance cannot be verified."}
                for code, label in zip(REQUIRED_REGULATORY_CHECKS, ("E-way bill", "Heavy-vehicle access", "Hazardous-goods compliance", "Over-dimensional permits", "Driver hours and rest", "Vehicle documents", "Transport permit", "Vehicle and axle load limits"))]
    source = assessment.get("source_id")
    version = assessment.get("policy_version")
    assessed_at = _parse_dt(assessment.get("assessed_at"))
    expires_at = _parse_dt(assessment.get("expires_at"))
    source_ok = bool(source and source in trusted and version and assessed_at and expires_at and assessed_at <= now <= expires_at)
    supplied = {item.get("code"): item for item in assessment.get("checks", []) if isinstance(item, dict) and item.get("code")}
    labels = {
        "eway_bill": "E-way bill applicability and validity",
        "heavy_vehicle_access": "Heavy-vehicle city-entry restrictions",
        "hazardous_goods": "Hazardous-goods requirements",
        "over_dimensional": "Over-dimensional cargo permits",
        "driver_hours_rest": "Driver hours and rest compliance",
        "vehicle_documents": "Vehicle registration, fitness, insurance and PUC",
        "transport_permit": "National/state transport permit coverage",
        "vehicle_load_limits": "Registered GVW and axle-load limits",
    }
    results = []
    for code in REQUIRED_REGULATORY_CHECKS:
        item = supplied.get(code)
        status = item.get("status") if item else None
        reference = item.get("source_reference") if item else None
        message = item.get("message") if item else None
        if not source_ok:
            verdict = "unknown"
            detail = "Regulatory assessment is missing a current trusted source, policy version, or validity period."
        elif status not in {"pass", "fail"} or not reference or not message:
            verdict = "unknown"
            detail = "The authoritative assessment did not provide a complete decision and source reference for this check."
        else:
            verdict = status
            detail = str(message)
        results.append({"rule_code": code, "label": labels[code], "verdict": verdict,
                        "value": status, "threshold": "current jurisdiction policy", "unit": None,
                        "claim_tag": "fact", "source_reference": reference, "message": detail})
    return results
