"""Smallest-enclosing-circle checks for cargo pickup/drop bundling.

Coordinates are projected into a local kilometre plane. This is appropriate for the short
5 km bundle radius; it is not used for road distance or the 40 km excursion rule.
"""
from __future__ import annotations
from math import cos, radians, sqrt
from itertools import combinations

def _xy(points: list[dict]) -> list[tuple[float,float]]:
    lat0=sum(float(p["lat"]) for p in points)/len(points)
    lon0=sum(float(p["lng"]) for p in points)/len(points)
    sx=111.320*cos(radians(lat0)); sy=110.574
    return [((float(p["lng"])-lon0)*sx,(float(p["lat"])-lat0)*sy) for p in points]

def _circle_from_three(a,b,c):
    ax,ay=a; bx,by=b; cx,cy=c
    d=2*(ax*(by-cy)+bx*(cy-ay)+cx*(ay-by))
    if abs(d)<1e-12: return None
    aa=ax*ax+ay*ay; bb=bx*bx+by*by; cc=cx*cx+cy*cy
    ux=(aa*(by-cy)+bb*(cy-ay)+cc*(ay-by))/d
    uy=(aa*(cx-bx)+bb*(ax-cx)+cc*(bx-ax))/d
    return (ux,uy,sqrt((ux-ax)**2+(uy-ay)**2))

def smallest_enclosing_circle_radius_km(points: list[dict]) -> float | None:
    if not points: return None
    xy=_xy(points)
    if len(xy)==1: return 0.0
    candidates=[]
    for p in xy: candidates.append((p[0],p[1],0.0))
    for a,b in combinations(xy,2):
        cx=(a[0]+b[0])/2; cy=(a[1]+b[1])/2
        candidates.append((cx,cy,sqrt((a[0]-b[0])**2+(a[1]-b[1])**2)/2))
    for a,b,c in combinations(xy,3):
        circle=_circle_from_three(a,b,c)
        if circle: candidates.append(circle)
    valid=[]
    for cx,cy,r in candidates:
        if all(sqrt((x-cx)**2+(y-cy)**2) <= r+1e-9 for x,y in xy): valid.append(r)
    return min(valid) if valid else None

def bundle_is_compatible(cargos: list[dict], pickup_radius_km: float=5.0, drop_radius_km: float=5.0) -> tuple[bool,float|None,float|None]:
    if len(cargos)<2: return False,None,None
    pickups=[c["pickup"] for c in cargos]; drops=[c["drop"] for c in cargos]
    pr=smallest_enclosing_circle_radius_km(pickups); dr=smallest_enclosing_circle_radius_km(drops)
    return bool(pr is not None and dr is not None and pr<=pickup_radius_km and dr<=drop_radius_km),pr,dr


def _centroid(points: list[dict]) -> dict:
    return {
        "lat": sum(float(p["lat"]) for p in points) / len(points),
        "lng": sum(float(p["lng"]) for p in points) / len(points),
        "name": f"{len(points)}-cargo cluster",
    }


def build_bundle_candidate(candidates: list[dict], max_payload_kg: float) -> dict | None:
    """Build a conservative bundle from individually eligible candidate records.

    All member cargo must already have passed every individual hard check. The
    bundle then rechecks aggregate payload, route-order load profile, cluster
    radii, and aggregate trip distance/time budgets. No member can be used to
    bypass a failed or unknown individual rule.
    """
    if len(candidates) < 2:
        return None
    if any(c.get("eligible") != "pass" or not c.get("checks") or any(x.get("verdict") != "pass" for x in c["checks"]) for c in candidates):
        return None
    categories = {c.get("category") for c in candidates}
    pickup_days = {str(c.get("pickup_window_start", ""))[:10] for c in candidates}
    route_ids = {c.get("route_id") for c in candidates}
    if len(categories) != 1 or len(pickup_days) != 1 or "" in pickup_days or len(route_ids) > 1:
        return None
    members = [
        {"pickup": c["pickup"], "drop": c["drop"]}
        for c in candidates
    ]
    compatible, pickup_radius, drop_radius = bundle_is_compatible(members)
    if not compatible:
        return None
    total_weight = sum(float(c["weight_kg"]) for c in candidates if c.get("weight_kg") is not None)
    if any(c.get("weight_kg") is None for c in candidates):
        return None
    if total_weight > float(max_payload_kg):
        return None

    # A route-distance load profile must never go below zero or exceed available
    # payload. Drop events at a shared route position are processed before pickups.
    events = []
    for c in candidates:
        if c.get("pickup_at_km") is None or c.get("drop_at_km") is None:
            return None
        if float(c["pickup_at_km"]) > float(c["drop_at_km"]):
            return None
        events.append((float(c["pickup_at_km"]), 1, float(c["weight_kg"])))
        events.append((float(c["drop_at_km"]), 0, -float(c["weight_kg"])))
    events.sort(key=lambda x: (x[0], x[1]))
    load = 0.0
    peak = 0.0
    load_profile = [{"km": 0.0, "load_kg": 0.0}]
    for km, _, delta in events:
        load += delta
        if load < -1e-6:
            return None
        peak = max(peak, load)
        load_profile.append({"km": round(km, 2), "load_kg": round(load, 2)})
    if abs(load) > 1e-6 or peak > float(max_payload_kg):
        return None

    # Build a route-ordered pickup/drop schedule. Each member must carry explicit
    # handling, waiting, excursion-duration and baseline-route timing inputs.
    # This conservatively accounts for earlier bundle stops delaying later pickups.
    from datetime import datetime, timedelta, timezone
    try:
        available_values = {c.get("available_from") for c in candidates}
        baseline_values = {float(c["baseline_driving_minutes"]) for c in candidates if c.get("baseline_driving_minutes") is not None}
        route_distance_values = {float(c["baseline_route_distance_km"]) for c in candidates if c.get("baseline_route_distance_km") is not None}
        if len(available_values) != 1 or None in available_values or len(baseline_values) != 1 or len(route_distance_values) != 1:
            return None
        available_from = datetime.fromisoformat(str(next(iter(available_values))).replace("Z", "+00:00"))
        if available_from.tzinfo is None:
            return None
        baseline_minutes = next(iter(baseline_values))
        route_distance = next(iter(route_distance_values))
        if baseline_minutes <= 0 or route_distance <= 0:
            return None
        events = []
        for c in candidates:
            required = (c.get("pickup_fraction"), c.get("drop_fraction"), c.get("loading_minutes"),
                        c.get("unloading_minutes"), c.get("waiting_minutes"),
                        c.get("pickup_excursion_minutes"), c.get("drop_excursion_minutes"),
                        c.get("pickup_window_start"), c.get("pickup_window_end"))
            if any(value is None for value in required):
                return None
            pickup_start = datetime.fromisoformat(str(c["pickup_window_start"]).replace("Z", "+00:00"))
            pickup_end = datetime.fromisoformat(str(c["pickup_window_end"]).replace("Z", "+00:00"))
            if pickup_start.tzinfo is None or pickup_end.tzinfo is None or pickup_start > pickup_end:
                return None
            events.append((float(c["pickup_fraction"]), 0, c, pickup_start, pickup_end))
            events.append((float(c["drop_fraction"]), 1, c, None, None))
        events.sort(key=lambda event: (event[0], event[1]))
        pickup_starts = [datetime.fromisoformat(str(c["pickup_window_start"]).replace("Z", "+00:00")) for c in candidates]
        pickup_ends = [datetime.fromisoformat(str(c["pickup_window_end"]).replace("Z", "+00:00")) for c in candidates]
        bundle_window_start = max(pickup_starts)
        bundle_window_end = min(pickup_ends)
        if bundle_window_start > bundle_window_end:
            return None
        cumulative_minutes = 0.0
        bundle_early_wait = 0.0
        for fraction, event_type, c, window_start, window_end in events:
            excursion_minutes = float(c["pickup_excursion_minutes"] if event_type == 0 else c["drop_excursion_minutes"])
            base_arrival = available_from + timedelta(minutes=baseline_minutes * fraction + cumulative_minutes + excursion_minutes)
            if event_type == 0:
                if base_arrival > window_end:
                    return None
                early_wait = max(0.0, (window_start - base_arrival).total_seconds() / 60.0)
                bundle_early_wait += early_wait
                cumulative_minutes += early_wait + float(c["loading_minutes"]) + float(c["waiting_minutes"]) + excursion_minutes
            else:
                cumulative_minutes += float(c["unloading_minutes"]) + excursion_minutes
        # Aggregate distance and active time are separately bounded by the same
        # whole-trip budgets carried by each member candidate.
        extras = [c.get("extra_distance_km") for c in candidates]
        times = [c.get("extra_active_minutes") for c in candidates]
        distance_limit = candidates[0].get("budget_after", {}).get("distance_limit_km")
        time_limit = candidates[0].get("budget_after", {}).get("time_limit_minutes")
        if any(x is None for x in extras) or distance_limit is None:
            return None
        total_extra = sum(float(x) for x in extras)
        if total_extra > float(distance_limit):
            return None
        if any(x is None for x in times) or time_limit is None:
            return None
        total_time = sum(float(x) for x in times) + bundle_early_wait
        if total_time > float(time_limit):
            return None
    except (KeyError, TypeError, ValueError, OverflowError):
        return None

    revenue_values = [c.get("revenue_inr") for c in candidates]
    cost_values = [c.get("incremental_cost_inr") for c in candidates]
    revenue = sum(float(x) for x in revenue_values) if all(x is not None for x in revenue_values) else None
    costs = sum(float(x) for x in cost_values) if all(x is not None for x in cost_values) else None
    net = round(revenue - costs, 2) if revenue is not None and costs is not None else None
    checks = []
    seen = set()
    for candidate in candidates:
        for item in candidate["checks"]:
            code = item.get("rule_code")
            # Each member's own checks remain in the audit trail. Preserve each
            # distinct cargo-specific check; aggregate checks below are separate.
            checks.append({**item, "member_id": candidate.get("id")})
    checks.extend([
        {"rule_code": "bundle_pickup_cluster", "label": "Pickup cluster radius", "verdict": "pass", "value": round(float(pickup_radius), 3), "threshold": 5.0, "unit": "km", "claim_tag": "calculation", "message": "The smallest enclosing circle of all bundle pickups is within 5 km."},
        {"rule_code": "bundle_drop_cluster", "label": "Drop cluster radius", "verdict": "pass", "value": round(float(drop_radius), 3), "threshold": 5.0, "unit": "km", "claim_tag": "calculation", "message": "The smallest enclosing circle of all bundle drops is within 5 km."},
        {"rule_code": "bundle_capacity", "label": "Combined bundle payload", "verdict": "pass", "value": round(total_weight, 2), "threshold": float(max_payload_kg), "unit": "kg", "claim_tag": "calculation", "message": "The combined cargo weight fits the available payload across the route load profile."},
        {"rule_code": "bundle_trip_distance", "label": "Combined whole-trip distance budget", "verdict": "pass", "value": round(total_extra, 3), "threshold": float(distance_limit), "unit": "km", "claim_tag": "calculation", "message": "The aggregate additional road distance is within the whole-trip distance budget."},
        {"rule_code": "bundle_trip_time", "label": "Combined whole-trip active-time budget", "verdict": "pass", "value": round(total_time, 2), "threshold": float(time_limit), "unit": "minutes", "claim_tag": "calculation", "message": "The aggregate additional active time, including additional pickup-window waiting, is within the whole-trip active-time budget."},
        {"rule_code": "bundle_pickup_schedule", "label": "Pickup windows remain feasible in route order", "verdict": "pass", "value": round(bundle_early_wait, 2), "threshold": "all pickup windows", "unit": "minutes of additional waiting", "claim_tag": "calculation", "message": "The route-ordered bundle schedule accounts for prior stops and remains within every pickup-window close."},
    ])
    pickup_points = [c["pickup"] for c in candidates]
    drop_points = [c["drop"] for c in candidates]
    sources = {c.get("source_type") for c in candidates}
    return {
        "id": "bundle:" + "+".join(str(c["id"]) for c in candidates),
        "member_ids": [c["id"] for c in candidates],
        "title": " + ".join(c.get("title", "Cargo") for c in candidates),
        "category": next(iter(categories)), "category_label": "Compatible cargo bundle",
        "weight_kg": round(total_weight, 2), "available_payload_kg": max_payload_kg,
        "is_bundle": True, "bundle_size": len(candidates),
        "source_type": next(iter(sources)) if len(sources) == 1 else "mixed",
        "listing_status": "open", "pickup": _centroid(pickup_points), "drop": _centroid(drop_points),
        "pickup_stops": pickup_points, "drop_stops": drop_points,
        "pickup_window_start": bundle_window_start.isoformat(),
        "pickup_window_end": bundle_window_end.isoformat(),
        "member_pickup_windows": [{"cargo_id": c["id"], "start": c["pickup_window_start"], "end": c["pickup_window_end"]} for c in candidates],
        "pickup_at_km": min(float(c["pickup_at_km"]) for c in candidates),
        "drop_at_km": max(float(c["drop_at_km"]) for c in candidates),
        "route_class": "bundle", "pickup_excursion_km": sum(float(c.get("pickup_excursion_km") or 0) for c in candidates),
        "drop_excursion_km": sum(float(c.get("drop_excursion_km") or 0) for c in candidates),
        "extra_distance_km": round(total_extra, 3), "extra_active_minutes": round(total_time, 2),
        "revenue_inr": round(revenue, 2) if revenue is not None else None,
        "incremental_cost_inr": round(costs, 2) if costs is not None else None,
        "net_inr": {"low": net, "expected": net, "high": net},
        "checks": checks, "eligible": "pass", "rejection_codes": [],
        "baseline_score": None, "model_score": None,
        "explanation": [{"text": f"This bundle contains {len(candidates)} individually eligible cargo listings.", "tag": "fact"},
                        {"text": f"Pickup and drop cluster radii are {pickup_radius:.2f} km and {drop_radius:.2f} km, respectively.", "tag": "calculation"},
                        {"text": "Every member passed its own hard checks; aggregate payload and trip budgets were checked again.", "tag": "fact"}],
        "load_profile": load_profile,
        "budget_after": {**candidates[0].get("budget_after", {}), "distance_used_fraction": total_extra / float(distance_limit) if float(distance_limit) > 0 else 0.0,
                         "time_used_fraction": total_time / float(time_limit) if float(time_limit) > 0 else 0.0},
    }


def generate_bundle_candidates(candidates: list[dict], available_payload_kg: float, max_bundle_size: int = 3, max_source_candidates: int = 20) -> list[dict]:
    """Generate bounded-size bundle alternatives; singles remain untouched."""
    from itertools import combinations
    eligible = [c for c in candidates if c.get("eligible") == "pass"][:max_source_candidates]
    bundles = []
    for size in range(2, min(max_bundle_size, len(eligible)) + 1):
        for group in combinations(eligible, size):
            bundle = build_bundle_candidate(list(group), available_payload_kg)
            if bundle is not None:
                bundles.append(bundle)
    return bundles
