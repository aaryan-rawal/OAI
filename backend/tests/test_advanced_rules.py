from datetime import datetime, timedelta, timezone

from app.domain.bundling import build_bundle_candidate
from app.domain.regulatory import evaluate_regulatory_assessment
from app.domain.routes import verify_route
from app.routing_adapters.client import RoutingUnavailable


def _candidate(cid, pickup_lng, drop_lng, pickup_km, drop_km, weight=1000):
    day = datetime.now(timezone.utc).replace(microsecond=0)
    return {
        "id": cid, "title": cid, "category": "steel_coils_sections", "weight_kg": weight,
        "pickup": {"lat": 0, "lng": pickup_lng}, "drop": {"lat": 0, "lng": drop_lng},
        "pickup_window_start": day.isoformat(), "pickup_window_end": (day + timedelta(hours=8)).isoformat(),
        "pickup_at_km": pickup_km, "drop_at_km": drop_km, "pickup_fraction": pickup_km / 100, "drop_fraction": drop_km / 100,
        "available_from": (day - timedelta(hours=1)).isoformat(), "baseline_driving_minutes": 100.0, "baseline_route_distance_km": 100.0,
        "loading_minutes": 2.0, "unloading_minutes": 2.0, "waiting_minutes": 1.0,
        "pickup_excursion_minutes": 0.0, "drop_excursion_minutes": 0.0, "route_class": "on_route",
        "eligible": "pass", "checks": [{"rule_code": "capacity", "verdict": "pass"}],
        "extra_distance_km": 2.0, "extra_active_minutes": 10.0,
        "revenue_inr": 1000.0, "incremental_cost_inr": 100.0,
        "budget_after": {"distance_limit_km": 20.0, "time_limit_minutes": 100.0},
        "source_type": "manual",
    }


def test_bundle_requires_aggregate_payload_and_preserves_load_profile():
    a = _candidate("a", 0.00, 0.10, 10, 40, 1000)
    b = _candidate("b", 0.01, 0.11, 12, 42, 1200)
    bundle = build_bundle_candidate([a, b], max_payload_kg=2500)
    assert bundle is not None
    assert bundle["is_bundle"] is True
    assert bundle["bundle_size"] == 2
    assert bundle["weight_kg"] == 2200
    assert bundle["eligible"] == "pass"
    assert bundle["load_profile"][-1]["load_kg"] == 0


def test_bundle_rejects_aggregate_capacity_overflow():
    a = _candidate("a", 0.00, 0.10, 10, 40, 1500)
    b = _candidate("b", 0.01, 0.11, 12, 42, 1500)
    assert build_bundle_candidate([a, b], max_payload_kg=2500) is None


def test_bundle_rejects_member_that_has_unknown_or_failed_check():
    a = _candidate("a", 0.00, 0.10, 10, 40)
    b = _candidate("b", 0.01, 0.11, 12, 42)
    b["checks"].append({"rule_code": "permit", "verdict": "unknown"})
    assert build_bundle_candidate([a, b], max_payload_kg=2500) is None


def test_regulatory_gate_is_unknown_without_authoritative_assessment():
    checks = evaluate_regulatory_assessment(None)
    assert len(checks) == 8
    assert {c["verdict"] for c in checks} == {"unknown"}


class FakeRouting:
    def __init__(self, fail=False):
        self.fail = fail

    def route(self, points):
        if self.fail:
            raise RoutingUnavailable("offline")
        return {"distance_km": 123.4, "duration_minutes": 200.0,
                "polyline": [{"lat": points[0]["lat"], "lng": points[0]["lng"]},
                             {"lat": points[-1]["lat"], "lng": points[-1]["lng"]}],
                "source": "osrm", "road_network_verified": True, "truck_profile_verified": True, "verified": True,
                "verification": {"provider": "OSRM", "checked_at": "test"}}


def test_route_verification_uses_road_provider_result():
    route = verify_route("surat_mumbai", FakeRouting())
    assert route["verified"] is True
    assert route["verification_status"] == "verified_truck_profile"
    assert route["distance_km"] == 123.4
    assert len(route["polyline"]) == 2


def test_route_verification_fails_closed_when_provider_unavailable():
    route = verify_route("surat_mumbai", FakeRouting(fail=True))
    assert route["verified"] is False
    assert route["verification_status"] == "unavailable"
    assert route["source"] == "illustrative_seed_only"


def test_eway_bill_distance_validity_uses_regular_and_odc_rates():
    from app.domain.regulatory import expected_eway_bill_validity_days
    assert expected_eway_bill_validity_days(200) == 1
    assert expected_eway_bill_validity_days(201) == 2
    assert expected_eway_bill_validity_days(20, over_dimensional_cargo=True) == 1
    assert expected_eway_bill_validity_days(21, over_dimensional_cargo=True) == 2


def test_eway_bill_validity_rejects_unknown_or_invalid_distance():
    from app.domain.regulatory import expected_eway_bill_validity_days
    import pytest
    with pytest.raises(ValueError):
        expected_eway_bill_validity_days(0)
    with pytest.raises(ValueError):
        expected_eway_bill_validity_days(float("nan"))


def test_fastapi_app_and_openapi_load_without_opening_database_connection():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    schema = client.get("/openapi.json").json()
    assert "/api/routes/{route_id}/verify" in schema["paths"]
    assert "/api/matching/run" in schema["paths"]


def test_ml_features_do_not_impute_missing_values():
    from app.ml_features import build_features, RISK_FEATURES
    candidate = {"weight_kg": 500, "available_payload_kg": 2000,
                 "extra_distance_km": 5, "extra_active_minutes": 30,
                 "pickup_at_km": 10, "drop_at_km": 50,
                 "net_inr": {"expected": None},
                 "pickup_window_start": "2026-11-21T08:00:00+00:00",
                 "pickup_window_end": "2026-11-21T10:00:00+00:00"}
    route = {"distance_km": 100}
    assert build_features(candidate, route) is None
    risk = build_features(candidate, route, RISK_FEATURES)
    assert risk is not None
    assert "net_contribution_inr" not in risk


def test_ml_wrappers_return_no_prediction_without_versioned_artifacts(tmp_path):
    from app.ml_wrappers.model_a import ModelA
    from app.ml_wrappers.model_b import ModelB
    assert ModelA(tmp_path).predict({}) is None
    assert ModelB(tmp_path).predict({}) is None


def test_bundle_rejects_pickup_window_broken_by_earlier_bundle_stop():
    a = _candidate("a", 0.00, 0.10, 10, 40, 1000)
    b = _candidate("b", 0.01, 0.11, 12, 42, 1000)
    a["loading_minutes"] = 120.0
    b["pickup_window_end"] = (datetime.fromisoformat(b["pickup_window_start"]) + timedelta(minutes=30)).isoformat()
    assert build_bundle_candidate([a, b], max_payload_kg=2500) is None


def test_regulatory_assessment_requires_trusted_source_and_complete_current_checks(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from app.config import settings
    from app.domain.regulatory import evaluate_regulatory_assessment, REQUIRED_REGULATORY_CHECKS
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(settings, "REGULATORY_TRUSTED_SOURCES", "approved-test-source")
    assessment = {
        "source_id": "approved-test-source", "policy_version": "test-policy-1",
        "assessed_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=5)).isoformat(),
        "checks": [{"code": code, "status": "pass", "source_reference": f"ref:{code}", "message": "Verified test assessment."}
                   for code in REQUIRED_REGULATORY_CHECKS],
    }
    results = evaluate_regulatory_assessment(assessment)
    assert len(results) == len(REQUIRED_REGULATORY_CHECKS)
    assert {item["verdict"] for item in results} == {"pass"}


def test_regulatory_assessment_from_untrusted_source_stays_unknown(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from app.config import settings
    from app.domain.regulatory import evaluate_regulatory_assessment, REQUIRED_REGULATORY_CHECKS
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(settings, "REGULATORY_TRUSTED_SOURCES", "approved-source")
    assessment = {
        "source_id": "user-supplied", "policy_version": "test-policy-1",
        "assessed_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=5)).isoformat(),
        "checks": [{"code": code, "status": "pass", "source_reference": f"ref:{code}", "message": "User claim."}
                   for code in REQUIRED_REGULATORY_CHECKS],
    }
    assert {item["verdict"] for item in evaluate_regulatory_assessment(assessment)} == {"unknown"}


def test_road_route_without_confirmed_hgv_profile_cannot_authorize_matching():
    from app.domain.routes import verify_route
    class CarOnlyRouting:
        def route(self, points):
            return {"distance_km": 123.4, "duration_minutes": 200.0,
                    "polyline": [{"lat": points[0]["lat"], "lng": points[0]["lng"]},
                                 {"lat": points[-1]["lat"], "lng": points[-1]["lng"]}],
                    "source": "osrm", "road_network_verified": True,
                    "truck_profile_verified": False, "verified": False,
                    "verification": {"provider": "OSRM", "profile": "unverified-car-or-unknown"}}
    route = verify_route("surat_mumbai", CarOnlyRouting())
    assert route["road_network_verified"] is True
    assert route["verified"] is False
    assert route["verification_status"] == "road_route_only_truck_profile_unverified"
