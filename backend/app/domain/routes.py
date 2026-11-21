"""Named demo corridors and a single road-route verification path."""
from __future__ import annotations
from copy import deepcopy
from app.routing_adapters.client import RoutingClient, RoutingUnavailable

ROUTES = [
 {"id":"delhi_mumbai","corridor_id":"delhi_mumbai","name":"Delhi to Mumbai","origin":{"name":"Delhi","lat":28.61,"lng":77.21},"destination":{"name":"Mumbai","lat":19.08,"lng":72.88},"polyline":[{"lat":28.61,"lng":77.21},{"lat":28.46,"lng":77.03},{"lat":26.91,"lng":75.79},{"lat":26.1,"lng":74.32},{"lat":24.58,"lng":73.68},{"lat":23.6,"lng":72.97},{"lat":23.02,"lng":72.57},{"lat":22.31,"lng":73.18},{"lat":21.17,"lng":72.83},{"lat":20.37,"lng":72.91},{"lat":19.7,"lng":72.78},{"lat":19.08,"lng":72.88}],"distance_km":1400.0,"baseline_driving_minutes":1867,"verified":False,"version":1},
 {"id":"surat_mumbai","corridor_id":"surat_mumbai","name":"Surat to Mumbai","origin":{"name":"Surat","lat":21.17,"lng":72.83},"destination":{"name":"Mumbai","lat":19.08,"lng":72.88},"polyline":[{"lat":21.17,"lng":72.83},{"lat":20.37,"lng":72.91},{"lat":19.7,"lng":72.78},{"lat":19.08,"lng":72.88}],"distance_km":280.0,"baseline_driving_minutes":373,"verified":False,"version":1},
 {"id":"mumbai_bengaluru","corridor_id":"mumbai_bengaluru","name":"Mumbai to Bengaluru","origin":{"name":"Mumbai","lat":19.08,"lng":72.88},"destination":{"name":"Bengaluru","lat":12.97,"lng":77.59},"polyline":[{"lat":19.08,"lng":72.88},{"lat":18.52,"lng":73.86},{"lat":17.69,"lng":74.0},{"lat":16.7,"lng":74.24},{"lat":15.85,"lng":74.5},{"lat":15.36,"lng":75.12},{"lat":14.46,"lng":75.92},{"lat":13.34,"lng":77.1},{"lat":12.97,"lng":77.59}],"distance_km":1000.0,"baseline_driving_minutes":1333,"verified":False,"version":1},
 {"id":"delhi_chennai","corridor_id":"delhi_chennai","name":"Delhi to Chennai","origin":{"name":"Delhi","lat":28.61,"lng":77.21},"destination":{"name":"Chennai","lat":13.08,"lng":80.27},"polyline":[{"lat":28.61,"lng":77.21},{"lat":27.18,"lng":78.02},{"lat":26.22,"lng":78.18},{"lat":25.45,"lng":78.57},{"lat":23.26,"lng":77.41},{"lat":21.15,"lng":79.09},{"lat":17.38,"lng":78.48},{"lat":16.51,"lng":80.65},{"lat":14.44,"lng":79.99},{"lat":13.08,"lng":80.27}],"distance_km":2200.0,"baseline_driving_minutes":2933,"verified":False,"version":1},
]

def get_route(route_id: str):
    route = next((r for r in ROUTES if r["id"] == route_id), None)
    return deepcopy(route) if route else None

def verify_route(route_id: str, routing=None) -> dict:
    """Return a verified road route or a fail-closed unverified route snapshot."""
    route = get_route(route_id)
    if route is None:
        raise KeyError(route_id)
    client = routing or RoutingClient()
    try:
        road = client.route([route["origin"], route["destination"]])
        route.update(road)
        route["baseline_driving_minutes"] = road["duration_minutes"]
        if road.get("truck_profile_verified"):
            route["verified"] = True
            route["verification_status"] = "verified_truck_profile"
        else:
            route["verified"] = False
            route["verification_status"] = "road_route_only_truck_profile_unverified"
            route["verification_warning"] = (
                "A road route was returned, but the configured OSRM endpoint is not confirmed "
                "to use a reviewed heavy-goods-vehicle profile. It cannot authorize matching."
            )
    except RoutingUnavailable as exc:
        route["verified"] = False
        route["verification_status"] = "unavailable"
        route["verification_error"] = str(exc)
        route["source"] = "illustrative_seed_only"
    return route
