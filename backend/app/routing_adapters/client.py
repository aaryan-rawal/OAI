"""Road-network routing adapter with explicit response and endpoint verification.

A route is never considered verified from straight-line geometry or a cached/demo
polyline. The adapter requires a successful OSRM road response, valid geometry,
positive distance/duration, and acceptable endpoint snapping.
"""
from __future__ import annotations
from datetime import datetime, timezone
import math
import requests
from app.config import settings
from app.domain.geo import haversine_km

class RoutingUnavailable(RuntimeError):
    pass

class RoutingClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.OSRM_URL).rstrip("/")
        self.fallback_url = settings.OSRM_FALLBACK_URL.rstrip("/") if settings.OSRM_FALLBACK_URL else None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "OptiFreightAI/1.0"})

    @staticmethod
    def _valid_point(point: dict) -> bool:
        try:
            lat, lng = float(point["lat"]), float(point["lng"])
            return math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180
        except (KeyError, TypeError, ValueError):
            return False

    def _request_route(self, base_url: str, points: list[dict], *, truck_profile_confirmed: bool = False) -> dict:
        if len(points) < 2 or not all(self._valid_point(p) for p in points):
            raise ValueError("At least two valid WGS84 coordinates are required.")
        coords = ";".join(f'{float(p["lng"]):.6f},{float(p["lat"]):.6f}' for p in points)
        response = self.session.get(
            f"{base_url}/route/v1/driving/{coords}",
            params={"overview": "full", "geometries": "geojson", "steps": "false", "alternatives": "false"},
            timeout=settings.OSRM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != "Ok":
            raise RoutingUnavailable(f"OSRM returned code {payload.get('code', 'missing')}.")
        routes = payload.get("routes") or []
        if not routes:
            raise RoutingUnavailable("OSRM returned no route.")
        route = routes[0]
        geometry = (route.get("geometry") or {}).get("coordinates") or []
        distance_m, duration_s = route.get("distance"), route.get("duration")
        if len(geometry) < 2 or distance_m is None or duration_s is None:
            raise RoutingUnavailable("OSRM response omitted geometry, distance, or duration.")
        if not math.isfinite(float(distance_m)) or not math.isfinite(float(duration_s)) or distance_m <= 0 or duration_s <= 0:
            raise RoutingUnavailable("OSRM returned non-positive or invalid route metrics.")
        polyline = []
        for coordinate in geometry:
            if not isinstance(coordinate, (list, tuple)) or len(coordinate) < 2:
                raise RoutingUnavailable("OSRM returned malformed route geometry.")
            lng, lat = float(coordinate[0]), float(coordinate[1])
            point = {"lat": lat, "lng": lng}
            if not self._valid_point(point):
                raise RoutingUnavailable("OSRM returned coordinates outside WGS84 bounds.")
            polyline.append(point)
        waypoints = payload.get("waypoints") or []
        max_snap_km = float(getattr(settings, "OSRM_MAX_SNAP_DISTANCE_KM", 1.0))
        snap_distances = [float(w.get("distance", 0.0)) / 1000.0 for w in waypoints]
        if waypoints and any(not math.isfinite(d) or d > max_snap_km for d in snap_distances):
            raise RoutingUnavailable("OSRM snapped an endpoint farther than the configured limit.")
        # Verify geometry starts and ends close to the requested endpoints. This guards
        # malformed responses and unexpected snapping, without calling the route straight-line.
        endpoint_errors = [haversine_km(points[0], polyline[0]), haversine_km(points[-1], polyline[-1])]
        if any(error > max_snap_km for error in endpoint_errors):
            raise RoutingUnavailable("Returned road geometry does not connect to the requested endpoints.")
        return {
            "distance_km": float(distance_m) / 1000.0,
            "duration_minutes": float(duration_s) / 60.0,
            "polyline": polyline,
            "source": "osrm",
            # Road geometry can be valid while truck suitability is not.
            # Only a separately reviewed HGV profile can authorize eligibility.
            "road_network_verified": True,
            "truck_profile_verified": bool(truck_profile_confirmed),
            "verified": bool(truck_profile_confirmed),
            "verification": {
                "provider": "OSRM",
                "profile": "truck" if truck_profile_confirmed else "unverified-car-or-unknown",
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "endpoint_snap_distances_km": [round(x, 4) for x in snap_distances],
                "endpoint_geometry_errors_km": [round(x, 4) for x in endpoint_errors],
                "max_endpoint_snap_km": max_snap_km,
            },
        }

    def route(self, points: list[dict]) -> dict:
        if len(points) < 2:
            raise ValueError("At least two coordinates are required.")
        urls = [self.base_url]
        if self.fallback_url and self.fallback_url != self.base_url:
            urls.append(self.fallback_url)
        errors = []
        for index, url in enumerate(urls):
            try:
                # The trusted HGV-profile flag applies only to the explicitly
                # configured primary endpoint. A public fallback is not trusted.
                truck_profile_confirmed = bool(settings.OSRM_TRUCK_PROFILE_CONFIRMED and index == 0)
                return self._request_route(url, points, truck_profile_confirmed=truck_profile_confirmed)
            except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, RoutingUnavailable) as exc:
                errors.append(f"{url}: {type(exc).__name__}")
        raise RoutingUnavailable("Road routing unavailable from configured OSRM endpoints (" + "; ".join(errors) + ").")

    def round_trip_excursion(self, route_point: dict, stop: dict) -> dict | None:
        try:
            result = self.route([route_point, stop, route_point])
            return {"distance_km": float(result["distance_km"]), "duration_minutes": float(result["duration_minutes"]), "verification": result["verification"]}
        except (RoutingUnavailable, ValueError):
            return None

    def round_trip_excursion_km(self, route_point: dict, stop: dict) -> float | None:
        result = self.round_trip_excursion(route_point, stop)
        return result["distance_km"] if result else None
