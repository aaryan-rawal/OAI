"""Fail-closed deterministic backhaul rules. Scoring is intentionally separate."""
from __future__ import annotations
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any
from app.domain.geo import nearest_route_point
from app.domain.regulatory import evaluate_regulatory_assessment

IST = ZoneInfo("Asia/Kolkata")
OFF_ROUTE_CAP_KM = 40.0
ROUTE_TOLERANCE_KM = 0.5
CONFIG_VERSION = 1

def trip_caps(route_km: float) -> dict:
    if route_km <= 500: return {"max_jobs_total": 3, "max_jobs_per_day": None, "band_label": "Up to 500 km"}
    if route_km <= 1250: return {"max_jobs_total": 5, "max_jobs_per_day": 3, "band_label": "500 to 1,250 km"}
    if route_km <= 2000: return {"max_jobs_total": 8, "max_jobs_per_day": 4, "band_label": "1,250 to 2,000 km"}
    return {"max_jobs_total": 10, "max_jobs_per_day": 4, "band_label": "Over 2,000 km"}

def budget_multiplier(route_km: float) -> float:
    if route_km <= 1000: return 1.25
    if route_km >= 1500: return 1.35
    return 1.25 + 0.10 * (route_km - 1000) / 500

def check(code: str, label: str, verdict: str, value: Any, threshold: Any, unit: str | None, tag: str, message: str) -> dict:
    return {"rule_code": code, "label": label, "verdict": verdict, "value": value, "threshold": threshold, "unit": unit, "claim_tag": tag, "message": message}

def evaluate_candidate(cargo: dict, truck: dict, route: dict, off_route_enabled: bool, routing: Any) -> dict:
    checks: list[dict] = []
    weight = cargo.get("weight_kg")
    capacity = truck.get("available_payload_kg")
    if weight is None or capacity is None:
        checks.append(check("capacity", "Fits available payload", "unknown", weight, capacity, "kg", "fact", "Cargo weight or available payload is missing; capacity cannot be verified."))
    elif weight <= capacity:
        checks.append(check("capacity", "Fits available payload", "pass", weight, capacity, "kg", "calculation", "Cargo weight fits the truck's available payload."))
    else:
        checks.append(check("capacity", "Fits available payload", "fail", weight, capacity, "kg", "calculation", "Cargo weight exceeds the truck's available payload."))

    if cargo.get("status", "open") != "open":
        checks.append(check("listing_status", "Listing is available", "fail", cargo.get("status"), "open", None, "fact", "This listing is not open."))
    else:
        checks.append(check("listing_status", "Listing is available", "pass", "open", "open", None, "fact", "The listing is open."))

    body_order = ["open_body", "closed_body", "flatbed_trailer", "container_carrier", "tanker", "reefer", "tipper"]
    compatibility = {
        "fmcg_packaged": "CYNYNCN", "steel_coils_sections": "YNYNNNN", "cement_bags": "CYCCNNN",
        "building_materials": "YCYNNNN", "auto_parts": "CYNYNNN", "machinery_heavy": "CNYCNNN",
        "container_20ft": "NNYYNNN", "container_40ft": "NNYYNNN", "agri_grain_bags": "CYNCNNN",
        "fresh_produce": "CCNNNYN", "frozen_pharma": "NNNCNYN", "chemicals_packaged_hazardous": "NCNCNNN",
        "liquid_bulk": "NNNNYNN", "textiles_garments": "CYNYNNN", "furniture_household": "CYNCNNN",
        "ecommerce_parcels": "NYNCNNN", "over_dimensional_project": "CNYNNNN", "bulk_aggregates_coal": "CNNNNNY",
    }
    category = str(cargo.get("category", "")).lower()
    body = truck.get("body_type")
    row = compatibility.get(category)
    code = row[body_order.index(body)] if row and body in body_order else None
    if code == "Y":
        checks.append(check("body_compatibility", "Cargo suits truck body", "pass", body, category, None, "fact", "The configured compatibility matrix allows this cargo in the selected body type."))
    elif code == "N":
        checks.append(check("body_compatibility", "Cargo suits truck body", "fail", body, category, None, "fact", "The configured compatibility matrix does not allow this cargo in the selected body type."))
    else:
        checks.append(check("body_compatibility", "Cargo suits truck body", "unknown", body, category, None, "fact", "Cargo category or conditional body requirements are not sufficiently verified."))

    polyline = route.get("polyline") or []
    pickup_near, pickup_cross, _ = nearest_route_point(cargo["pickup"], polyline)
    drop_near, drop_cross, _ = nearest_route_point(cargo["drop"], polyline)
    if not route.get("verified") or pickup_near is None or drop_near is None:
        checks.append(check("route_mode", "Stops are on or acceptably near the original route", "unknown", None, ROUTE_TOLERANCE_KM, "km", "fact", "A verified road route is not available, so route proximity cannot be confirmed."))
        pickup_excursion = drop_excursion = None
        pickup_excursion_minutes = drop_excursion_minutes = None
    else:
        pickup_on = pickup_cross <= ROUTE_TOLERANCE_KM
        drop_on = drop_cross <= ROUTE_TOLERANCE_KM
        if pickup_on and drop_on:
            checks.append(check("route_mode", "Stops are on or acceptably near the original route", "pass", "on_route", ROUTE_TOLERANCE_KM, "km", "calculation", "Both cargo stops are within the route corridor tolerance."))
            pickup_excursion = drop_excursion = 0.0
            pickup_excursion_minutes = drop_excursion_minutes = 0.0
        elif not off_route_enabled:
            checks.append(check("route_mode", "Stops are on or acceptably near the original route", "fail", "off_route", "on_route_only", None, "fact", "At least one stop is off the original route and off-route delivery is disabled."))
            pickup_excursion = drop_excursion = None
            pickup_excursion_minutes = drop_excursion_minutes = None
        else:
            checks.append(check("route_mode", "Stops are on or acceptably near the original route", "pass", "off_route_enabled", None, None, "fact", "Off-route delivery is enabled; each stop is checked against the 40 km excursion cap."))
            pickup_metrics = {"distance_km":0.0,"duration_minutes":0.0} if pickup_on else (routing.round_trip_excursion(pickup_near, cargo["pickup"]) if hasattr(routing,"round_trip_excursion") else None)
            drop_metrics = {"distance_km":0.0,"duration_minutes":0.0} if drop_on else (routing.round_trip_excursion(drop_near, cargo["drop"]) if hasattr(routing,"round_trip_excursion") else None)
            if pickup_metrics is None and not hasattr(routing,"round_trip_excursion"):
                value=routing.round_trip_excursion_km(pickup_near,cargo["pickup"]); pickup_metrics={"distance_km":value,"duration_minutes":None} if value is not None else None
            if drop_metrics is None and not hasattr(routing,"round_trip_excursion"):
                value=routing.round_trip_excursion_km(drop_near,cargo["drop"]); drop_metrics={"distance_km":value,"duration_minutes":None} if value is not None else None
            pickup_excursion = pickup_metrics["distance_km"] if pickup_metrics else None
            drop_excursion = drop_metrics["distance_km"] if drop_metrics else None
            pickup_excursion_minutes = pickup_metrics.get("duration_minutes") if pickup_metrics else None
            drop_excursion_minutes = drop_metrics.get("duration_minutes") if drop_metrics else None

    for code, label, value in [("pickup_excursion", "Pickup round-trip road excursion", pickup_excursion), ("drop_excursion", "Drop round-trip road excursion", drop_excursion)]:
        if value is None:
            checks.append(check(code, label, "unknown", None, OFF_ROUTE_CAP_KM, "km", "fact", "Road-network excursion distance is unavailable; this stop cannot be verified."))
        elif value <= OFF_ROUTE_CAP_KM:
            checks.append(check(code, label, "pass", round(value, 3), OFF_ROUTE_CAP_KM, "km", "calculation", f"Round-trip road excursion is {value:.2f} km, within the 40 km cap."))
        else:
            checks.append(check(code, label, "fail", round(value, 3), OFF_ROUTE_CAP_KM, "km", "calculation", f"Round-trip road excursion is {value:.2f} km, above the 40 km cap."))

    start, end = cargo.get("pickup_window_start"), cargo.get("pickup_window_end")
    available_from = truck.get("available_from")
    if not start or not end or not available_from or not route.get("baseline_driving_minutes") or not route.get("verified"):
        checks.append(check("time_window", "Pickup window is feasible", "unknown", None, None, None, "fact", "Pickup window, truck availability, or verified route duration is missing."))
    else:
        try:
            eta_base = datetime.fromisoformat(str(available_from).replace("Z", "+00:00"))
            start_dt = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
            _, _, pickup_fraction = nearest_route_point(cargo["pickup"], polyline)
            eta = eta_base + timedelta(minutes=float(route["baseline_driving_minutes"]) * float(pickup_fraction or 0))
            if eta.tzinfo is None and start_dt.tzinfo is not None: eta = eta.replace(tzinfo=start_dt.tzinfo)
            if end_dt.tzinfo is None and eta.tzinfo is not None: end_dt = end_dt.replace(tzinfo=eta.tzinfo)
            if eta <= end_dt:
                checks.append(check("time_window", "Pickup window is feasible", "pass", eta.isoformat(), end_dt.isoformat(), None, "calculation", "Estimated route arrival is no later than the pickup-window close."))
            else:
                checks.append(check("time_window", "Pickup window is feasible", "fail", eta.isoformat(), end_dt.isoformat(), None, "calculation", "Estimated route arrival is after the pickup window closes."))
        except (TypeError, ValueError):
            checks.append(check("time_window", "Pickup window is feasible", "unknown", None, None, None, "fact", "Pickup or availability timestamps could not be interpreted safely."))

    # Regulatory obligations are jurisdiction- and date-dependent. They pass only
    # when a current trusted-source assessment is supplied by a server-side adapter.
    checks.extend(evaluate_regulatory_assessment(cargo.get("compliance_assessment")))
    eligible = "pass" if all(c["verdict"] == "pass" for c in checks) else ("fail" if any(c["verdict"] == "fail" for c in checks) else "unknown")
    return {"checks": checks, "eligible": eligible, "rejection_codes": [c["rule_code"] for c in checks if c["verdict"] == "fail"], "pickup_excursion_km": pickup_excursion, "drop_excursion_km": drop_excursion,
            "pickup_excursion_minutes": pickup_excursion_minutes, "drop_excursion_minutes": drop_excursion_minutes}
