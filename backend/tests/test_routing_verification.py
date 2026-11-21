from types import SimpleNamespace
import pytest
from app.routing_adapters.client import RoutingClient, RoutingUnavailable


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        return None
    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.headers = {}
        self.url = None
    def get(self, url, params, timeout):
        self.url = url
        return FakeResponse(self.payload)


def payload(start=(77.21, 28.61), end=(72.88, 19.08), code="Ok", snap=0.0):
    return {
        "code": code,
        "routes": [{"distance": 100000, "duration": 7200,
                    "geometry": {"coordinates": [list(start), list(end)]}}],
        "waypoints": [{"distance": snap}, {"distance": snap}],
    }


def test_osrm_response_requires_code_ok_and_valid_metrics():
    client = RoutingClient(base_url="http://local")
    client.session = FakeSession(payload())
    result = client._request_route("http://local", [
        {"lat": 28.61, "lng": 77.21}, {"lat": 19.08, "lng": 72.88}
    ])
    assert result["road_network_verified"] is True
    assert result["verified"] is False
    assert result["truck_profile_verified"] is False
    assert result["distance_km"] == 100
    assert result["duration_minutes"] == 120
    assert result["verification"]["provider"] == "OSRM"


def test_osrm_response_with_non_ok_code_is_rejected():
    client = RoutingClient(base_url="http://local")
    client.session = FakeSession(payload(code="NoRoute"))
    with pytest.raises(RoutingUnavailable):
        client._request_route("http://local", [
            {"lat": 28.61, "lng": 77.21}, {"lat": 19.08, "lng": 72.88}
        ])


def test_osrm_endpoint_snap_beyond_configured_limit_is_rejected(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "OSRM_MAX_SNAP_DISTANCE_KM", 1.0)
    client = RoutingClient(base_url="http://local")
    client.session = FakeSession(payload(snap=1500))
    with pytest.raises(RoutingUnavailable):
        client._request_route("http://local", [
            {"lat": 28.61, "lng": 77.21}, {"lat": 19.08, "lng": 72.88}
        ])


def test_osrm_malformed_coordinate_is_rejected():
    bad = payload()
    bad["routes"][0]["geometry"]["coordinates"] = [[999, 999], [72.88, 19.08]]
    client = RoutingClient(base_url="http://local")
    client.session = FakeSession(bad)
    with pytest.raises(RoutingUnavailable):
        client._request_route("http://local", [
            {"lat": 28.61, "lng": 77.21}, {"lat": 19.08, "lng": 72.88}
        ])


def test_osrm_route_is_truck_verified_only_when_primary_hgv_profile_is_confirmed(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "OSRM_TRUCK_PROFILE_CONFIRMED", True)
    client = RoutingClient(base_url="http://local")
    client.session = FakeSession(payload())
    result = client._request_route("http://local", [
        {"lat": 28.61, "lng": 77.21}, {"lat": 19.08, "lng": 72.88}
    ], truck_profile_confirmed=True)
    assert result["road_network_verified"] is True
    assert result["truck_profile_verified"] is True
    assert result["verified"] is True
