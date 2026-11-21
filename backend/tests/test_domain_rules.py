from app.domain.rules import trip_caps, budget_multiplier, OFF_ROUTE_CAP_KM
from app.domain.geo import haversine_km, nearest_route_point

def test_trip_caps_boundaries():
    assert trip_caps(500)["max_jobs_total"] == 3
    assert trip_caps(500.001)["max_jobs_total"] == 5
    assert trip_caps(1250)["max_jobs_total"] == 5
    assert trip_caps(1250.001)["max_jobs_total"] == 8
    assert trip_caps(2000)["max_jobs_total"] == 8
    assert trip_caps(2000.001)["max_jobs_total"] == 10

def test_budget_multiplier_boundaries():
    assert budget_multiplier(1000) == 1.25
    assert budget_multiplier(1250) == 1.30
    assert budget_multiplier(1500) == 1.35

def test_exact_excursion_limit_is_inclusive():
    assert OFF_ROUTE_CAP_KM == 40.0
    assert 40.0 <= OFF_ROUTE_CAP_KM
    assert 40.001 > OFF_ROUTE_CAP_KM

def test_haversine_same_point_zero():
    point={"lat":28.61,"lng":77.21}
    assert haversine_km(point,point) == 0

def test_nearest_route_point_on_segment():
    line=[{"lat":0,"lng":0},{"lat":0,"lng":1}]
    near, distance, fraction=nearest_route_point({"lat":0,"lng":0.5},line)
    assert distance < 0.001
    assert 0.49 < fraction < 0.51

from datetime import datetime, timedelta, timezone
from app.domain.rules import evaluate_candidate

class FakeRouting:
    def __init__(self, excursion): self.excursion = excursion
    def round_trip_excursion_km(self, route_point, stop):
        return self.excursion if stop["lat"] > 0.05 else 0.0

def base_candidate():
    now=datetime.now(timezone.utc)
    return {"id":"c1","title":"Steel","category":"steel_coils_sections","weight_kg":3000,
            "pickup":{"lat":0.1,"lng":0.2,"name":"Pickup"},"drop":{"lat":0,"lng":0.8,"name":"Drop"},
            "pickup_window_start":now.isoformat(),"pickup_window_end":(now+timedelta(days=2)).isoformat(),"status":"open"}

def base_truck():
    return {"body_type":"open_body","available_payload_kg":5000,"max_payload_kg":10000,
            "available_from":datetime.now(timezone.utc).isoformat()}

def base_route():
    return {"verified":True,"polyline":[{"lat":0,"lng":0},{"lat":0,"lng":1}],"distance_km":100,"baseline_driving_minutes":100}

def test_exact_40km_off_route_excursion_passes():
    result=evaluate_candidate(base_candidate(),base_truck(),base_route(),True,FakeRouting(40.0))
    pickup=next(c for c in result["checks"] if c["rule_code"]=="pickup_excursion")
    assert pickup["verdict"]=="pass"
    assert pickup["value"]==40.0

def test_40_001km_off_route_excursion_fails():
    result=evaluate_candidate(base_candidate(),base_truck(),base_route(),True,FakeRouting(40.001))
    pickup=next(c for c in result["checks"] if c["rule_code"]=="pickup_excursion")
    assert pickup["verdict"]=="fail"
    assert result["eligible"]=="fail"

def test_unverified_route_never_passes_route_check():
    route=base_route(); route["verified"]=False
    result=evaluate_candidate(base_candidate(),base_truck(),route,False,FakeRouting(0))
    route_check=next(c for c in result["checks"] if c["rule_code"]=="route_mode")
    assert route_check["verdict"]=="unknown"
    assert result["eligible"]!="pass"

def test_max_payload_does_not_replace_available_payload():
    truck=base_truck(); truck["available_payload_kg"]=2500; truck["max_payload_kg"]=10000
    result=evaluate_candidate(base_candidate(),truck,base_route(),False,FakeRouting(0))
    capacity=next(c for c in result["checks"] if c["rule_code"]=="capacity")
    assert capacity["verdict"]=="fail"

from app.domain.bundling import smallest_enclosing_circle_radius_km, bundle_is_compatible

def test_bundle_radius_uses_smallest_enclosing_circle():
    points=[{"lat":0,"lng":0},{"lat":0,"lng":0.04}]
    radius=smallest_enclosing_circle_radius_km(points)
    assert radius is not None and 2.2 < radius < 2.3

def test_bundle_requires_both_pickup_and_drop_clusters_within_five_km():
    cargos=[{"pickup":{"lat":0,"lng":0},"drop":{"lat":0,"lng":0}},
            {"pickup":{"lat":0,"lng":0.02},"drop":{"lat":0,"lng":0.02}}]
    ok,pr,dr=bundle_is_compatible(cargos)
    assert ok and pr is not None and dr is not None and pr<=5 and dr<=5
    cargos[1]["drop"]={"lat":0,"lng":0.2}
    ok,_,dr=bundle_is_compatible(cargos)
    assert not ok and dr is not None and dr>5

from app.domain.finance import calculate_extra_active_minutes, calculate_incremental_cost_and_net

def test_active_time_requires_every_component():
    assert calculate_extra_active_minutes(10,20,30,40,0)==100
    assert calculate_extra_active_minutes(10,20,30,None,0) is None

def test_net_contribution_requires_all_explicit_cost_inputs():
    overrides={"diesel_inr_per_l":90,"mileage_km_per_l":4,"toll_inr_per_km":2,"driver_inr_per_hour":120,"handling_fee_inr":50}
    cost,net=calculate_incremental_cost_and_net(5000,40,60,overrides)
    assert cost==1150.0
    assert net==3850.0
    partial={**overrides,"handling_fee_inr":None}
    assert calculate_incremental_cost_and_net(5000,40,60,partial)==(None,None)
