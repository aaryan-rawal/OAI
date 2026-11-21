"""WGS84 geometry helpers. Straight-line distances are never labelled as road distances."""
from __future__ import annotations
from math import asin, cos, radians, sin, sqrt
from typing import Sequence

EARTH_RADIUS_KM = 6371.0088

def haversine_km(a: dict, b: dict) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (float(a["lat"]), float(a["lng"]), float(b["lat"]), float(b["lng"])))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(min(1.0, sqrt(h)))

def project_point_to_segment(point: dict, start: dict, end: dict) -> tuple[dict, float]:
    """Return nearest point and straight-line cross-track distance using local projection."""
    lat0 = radians((float(start["lat"]) + float(end["lat"]) + float(point["lat"])) / 3)
    scale_x = 111.320 * cos(lat0)
    scale_y = 110.574
    ax, ay = float(start["lng"]) * scale_x, float(start["lat"]) * scale_y
    bx, by = float(end["lng"]) * scale_x, float(end["lat"]) * scale_y
    px, py = float(point["lng"]) * scale_x, float(point["lat"]) * scale_y
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    t = 0.0 if denom == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    nearest = {"lat": (ay + t * dy) / scale_y, "lng": (ax + t * dx) / scale_x}
    return nearest, haversine_km(point, nearest)

def nearest_route_point(point: dict, polyline: Sequence[dict]) -> tuple[dict | None, float | None, float | None]:
    if len(polyline) < 2:
        return None, None, None
    best = (None, float("inf"), None)
    traversed = 0.0
    total = sum(haversine_km(polyline[i], polyline[i + 1]) for i in range(len(polyline) - 1))
    for i in range(len(polyline) - 1):
        start, end = polyline[i], polyline[i + 1]
        seg_len = haversine_km(start, end)
        nearest, cross = project_point_to_segment(point, start, end)
        along = traversed + haversine_km(start, nearest)
        if cross < best[1]:
            best = (nearest, cross, along)
        traversed += seg_len
    return best[0], best[1], (best[2] / total if total else 0.0)
