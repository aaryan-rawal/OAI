"""Fail-closed routing fallback. Approximate distance must never be returned as road distance."""
from app.routing_adapters.client import RoutingClient, RoutingUnavailable

class RoutingFallback:
    def __init__(self):
        self.client = RoutingClient()
    def get_route(self, origin: dict, destination: dict):
        try:
            return self.client.route([origin, destination])
        except RoutingUnavailable:
            return {"distance_km": None, "duration_minutes": None, "polyline": [], "source": "unavailable", "verified": False}
