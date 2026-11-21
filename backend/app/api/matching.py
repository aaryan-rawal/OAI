from __future__ import annotations
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models import ManualCargo, MatchRun, Shipment, User
from app.schemas import MatchIn
from app.authentication.dependencies import current_user
from app.domain.routes import get_route, verify_route
from app.domain.geo import nearest_route_point, haversine_km
from app.domain.rules import evaluate_candidate, trip_caps, budget_multiplier, ROUTE_TOLERANCE_KM, CONFIG_VERSION, IST
from app.domain.finance import calculate_extra_active_minutes, calculate_incremental_cost_and_net
from app.domain.scoring import baseline_score as calculate_baseline_score
from app.domain.bundling import generate_bundle_candidates
from app.ml_wrappers.gating import Gating
from app.ml_wrappers.model_a import ModelA
from app.ml_wrappers.model_b import ModelB
from app.ml_features import build_features, RISK_FEATURES
from app.routing_adapters.client import RoutingClient, RoutingUnavailable

router = APIRouter(prefix="/matching", tags=["matching"])

def point_at_fraction(polyline: list[dict], fraction: float) -> dict:
    if len(polyline) < 2: return polyline[0]
    lengths = [haversine_km(polyline[i], polyline[i+1]) for i in range(len(polyline)-1)]
    total = sum(lengths); target = total * fraction; walked = 0.0
    for i, length in enumerate(lengths):
        if walked + length >= target:
            t = 0 if length == 0 else (target-walked)/length
            return {"lat": polyline[i]["lat"] + (polyline[i+1]["lat"]-polyline[i]["lat"])*t,
                    "lng": polyline[i]["lng"] + (polyline[i+1]["lng"]-polyline[i]["lng"])*t}
        walked += length
    return dict(polyline[-1])

def demo_cargo(route: dict, truck: dict) -> list[dict]:
    line = route["polyline"]
    if len(line) < 2: return []
    now = datetime.now(timezone.utc)
    end = (now + timedelta(days=2)).isoformat()
    start = now.isoformat()
    examples = [(0.24,0.43,1800,"Packaged FMCG","fmcg_packaged"),(0.38,0.62,4200,"Steel sections","steel_coils_sections"),(0.56,0.78,6500,"Textiles","textiles_garments"),(0.72,0.88,12000,"Machinery","machinery_heavy")]
    out=[]
    for i,(a,b,w,title,category) in enumerate(examples,1):
        out.append({"id":f"demo-{route['id']}-{i}","title":title,"category":category,"weight_kg":w,
                    "rate_inr":None,"pickup":{**point_at_fraction(line,a),"name":f"Demo pickup {i}"},
                    "drop":{**point_at_fraction(line,b),"name":f"Demo drop {i}"},"pickup_window_start":start,
                    "pickup_window_end":end,"loading_minutes":30.0,"unloading_minutes":30.0,"waiting_minutes":0.0,
                    "status":"open","source_type":"synthetic","verification_status":"demonstration"})
    return out

@router.post("/run")
async def run_matching(payload: MatchIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    route_seed = get_route(payload.route_id)
    if not route_seed: raise HTTPException(404, "Route not found.")
    if payload.route_version != route_seed["version"]: raise HTTPException(409, "The selected route version is out of date. Refresh routes and run matching again.")
    routing = RoutingClient()
    route = verify_route(payload.route_id, routing=routing)
    # The route returned by OSRM is the immutable baseline for this run. If OSRM is
    # unavailable, the seed corridor remains illustrative and every route-dependent
    # eligibility check must stay unknown.
    manual_rows = (await db.scalars(select(ManualCargo).where(ManualCargo.owner_id == user.id))).all()
    manual = [{"id":r.id,"title":r.title,"category":r.category,"weight_kg":r.weight_kg,"rate_inr":r.rate_inr,
               "pickup":r.pickup,"drop":r.drop,"pickup_window_start":r.pickup_window_start,"pickup_window_end":r.pickup_window_end,
               "loading_minutes":r.loading_minutes,"unloading_minutes":r.unloading_minutes,"waiting_minutes":r.waiting_minutes,
               "compliance_assessment":r.compliance_assessment,
               "status":"open","source_type":"manual","verification_status":"user_entered"} for r in manual_rows]
    cargos = demo_cargo(route, payload.truck.model_dump()) + manual
    caps = trip_caps(float(route["distance_km"]))
    active_shipments = (await db.scalars(select(Shipment).where(Shipment.user_id == user.id, Shipment.route_id == route["id"], Shipment.status.notin_(["cancelled", "delivered"])))).all()
    active_total = len(active_shipments)
    multiplier = budget_multiplier(float(route["distance_km"]))
    distance_limit = float(route["distance_km"]) * (multiplier - 1)
    candidates=[]
    for cargo in cargos:
        result = evaluate_candidate(cargo, payload.truck.model_dump(), route, payload.off_route_enabled, routing)
        if route.get("verified"):
            pickup_near, pickup_cross, pickup_fraction = nearest_route_point(cargo["pickup"], route["polyline"])
            drop_near, drop_cross, drop_fraction = nearest_route_point(cargo["drop"], route["polyline"])
            route_class = "on_route" if pickup_cross is not None and drop_cross is not None and max(pickup_cross,drop_cross) <= ROUTE_TOLERANCE_KM else "off_route"
        else:
            pickup_near = drop_near = pickup_cross = drop_cross = pickup_fraction = drop_fraction = None
            route_class = "unknown"
        extra = None
        if result["pickup_excursion_km"] is not None and result["drop_excursion_km"] is not None:
            extra = result["pickup_excursion_km"] + result["drop_excursion_km"]
        elif route_class == "on_route" and route.get("verified"): extra = 0.0
        extra_active=calculate_extra_active_minutes(
            result.get("pickup_excursion_minutes"), result.get("drop_excursion_minutes"),
            cargo.get("loading_minutes"), cargo.get("unloading_minutes"), cargo.get("waiting_minutes"))
        if not route.get("verified"):
            extra_active=None
        baseline_active=payload.truck.baseline_active_minutes
        time_limit=(float(baseline_active)*(multiplier-1)) if baseline_active is not None and route.get("verified") else None
        if pickup_fraction is not None and drop_fraction is not None and pickup_fraction > drop_fraction:
            result["checks"].append({"rule_code":"stop_order","label":"Pickup precedes drop on original route","verdict":"fail","value": [pickup_fraction,drop_fraction],"threshold":"pickup before drop","unit":None,"claim_tag":"calculation","message":"The cargo drop is located before its pickup on the original route; the original route cannot be reversed or changed."})
            result["eligible"]="fail"; result["rejection_codes"].append("stop_order")
        if not route.get("verified"):
            result["checks"].append({"rule_code":"job_cap_total","label":"Within total trip job limit","verdict":"unknown","value":None,"threshold":caps["max_jobs_total"],"unit":"jobs","claim_tag":"fact","message":"The original road distance is unverified, so the applicable route-distance job-cap band is unknown."})
        elif active_total < caps["max_jobs_total"]:
            result["checks"].append({"rule_code":"job_cap_total","label":"Within total trip job limit","verdict":"pass","value":active_total+1,"threshold":caps["max_jobs_total"],"unit":"jobs","claim_tag":"calculation","message":"The candidate would remain within the route-distance-based total job cap."})
        else:
            result["checks"].append({"rule_code":"job_cap_total","label":"Within total trip job limit","verdict":"fail","value":active_total+1,"threshold":caps["max_jobs_total"],"unit":"jobs","claim_tag":"calculation","message":"The trip has reached its total extra-job cap."})
            result["eligible"]="fail"; result["rejection_codes"].append("job_cap_total")
        if caps["max_jobs_per_day"] is not None:
            pickup_start = cargo.get("pickup_window_start")
            if not route.get("verified"):
                day_verdict="unknown"; day_message="The original route distance is unverified, so the applicable daily job cap is unknown."; day_value=None
            elif not pickup_start:
                day_verdict="unknown"; day_message="Pickup date is missing, so the Indian-calendar-day cap cannot be checked."; day_value=None
            else:
                try:
                    pickup_dt=datetime.fromisoformat(str(pickup_start).replace("Z","+00:00"))
                    pickup_day=(pickup_dt.astimezone(IST) if pickup_dt.tzinfo else pickup_dt.replace(tzinfo=IST)).date()
                    same_day=0
                    unknown_existing_date=False
                    for existing in active_shipments:
                        old_start=existing.candidate.get("pickup_window_start")
                        if not old_start:
                            unknown_existing_date=True
                            break
                        old_dt=datetime.fromisoformat(str(old_start).replace("Z","+00:00"))
                        old_day=(old_dt.astimezone(IST) if old_dt.tzinfo else old_dt.replace(tzinfo=IST)).date()
                        same_day += int(old_day == pickup_day)
                    if unknown_existing_date:
                        day_verdict="unknown"; day_value=None
                        day_message="An existing active shipment has no verifiable pickup date; the daily cap cannot be safely checked."
                    else:
                        day_value=same_day+1
                        day_verdict="pass" if day_value <= caps["max_jobs_per_day"] else "fail"
                        day_message="Candidate remains within the per-day pickup cap." if day_verdict=="pass" else "The per-day pickup cap has been reached."
                except ValueError:
                    day_verdict="unknown"; day_message="Pickup timestamp could not be interpreted safely."; day_value=None
            result["checks"].append({"rule_code":"job_cap_daily","label":"Within Indian-calendar-day job limit","verdict":day_verdict,"value":day_value,"threshold":caps["max_jobs_per_day"],"unit":"jobs","claim_tag":"calculation","message":day_message})
            if day_verdict=="fail": result["eligible"]="fail"; result["rejection_codes"].append("job_cap_daily")
        if extra is None or not route.get("verified"):
            result["checks"].append({"rule_code":"trip_distance_budget","label":"Within whole-trip distance budget","verdict":"unknown","value":None,"threshold":round(distance_limit,2) if route.get("verified") else None,"unit":"km","claim_tag":"fact","message":"The original road distance or additional road distance is unverified, so the whole-trip distance budget cannot be checked."})
        elif extra <= distance_limit:
            result["checks"].append({"rule_code":"trip_distance_budget","label":"Within whole-trip distance budget","verdict":"pass","value":round(extra,3),"threshold":round(distance_limit,3),"unit":"km","claim_tag":"calculation","message":"The additional road distance is within the whole-trip distance budget."})
        else:
            result["checks"].append({"rule_code":"trip_distance_budget","label":"Within whole-trip distance budget","verdict":"fail","value":round(extra,3),"threshold":round(distance_limit,3),"unit":"km","claim_tag":"calculation","message":"The additional road distance exceeds the whole-trip distance budget."})
            result["eligible"]="fail"; result["rejection_codes"].append("trip_distance_budget")
        if extra_active is None or time_limit is None:
            result["checks"].append({"rule_code":"trip_time_budget","label":"Within whole-trip active-time budget","verdict":"unknown","value":extra_active,"threshold":round(time_limit,1) if time_limit is not None else None,"unit":"minutes","claim_tag":"fact","message":"Verified baseline active time and all added loading, unloading, waiting and road-excursion durations are required."})
        elif extra_active <= time_limit:
            result["checks"].append({"rule_code":"trip_time_budget","label":"Within whole-trip active-time budget","verdict":"pass","value":round(extra_active,2),"threshold":round(time_limit,2),"unit":"minutes","claim_tag":"calculation","message":"The added active time is within the configured whole-trip active-time budget."})
        else:
            result["checks"].append({"rule_code":"trip_time_budget","label":"Within whole-trip active-time budget","verdict":"fail","value":round(extra_active,2),"threshold":round(time_limit,2),"unit":"minutes","claim_tag":"calculation","message":"The added active time exceeds the whole-trip active-time budget."})
            result["eligible"]="fail"; result["rejection_codes"].append("trip_time_budget")
        if result["eligible"] == "pass" and any(c["verdict"] != "pass" for c in result["checks"]): result["eligible"]="unknown"
        checks = result["checks"]
        eligible = result["eligible"]
        pickup_km = round(float(pickup_fraction) * float(route["distance_km"]),2) if pickup_fraction is not None and route.get("verified") else None
        drop_km = round(float(drop_fraction) * float(route["distance_km"]),2) if drop_fraction is not None and route.get("verified") else None
        revenue=cargo.get("rate_inr")
        costs=payload.cost_overrides.model_dump() if payload.cost_overrides else {}
        incremental_cost,net_value=calculate_incremental_cost_and_net(revenue,extra,extra_active,costs)
        candidate_record = {
            "id":cargo["id"],"title":cargo["title"],"category":cargo["category"],"category_label":cargo["title"],
            "weight_kg":cargo.get("weight_kg"),"is_bundle":False,"bundle_size":1,"source_type":cargo["source_type"],"listing_status":"open",
            "pickup":cargo["pickup"],"drop":cargo["drop"],"pickup_window_start":cargo.get("pickup_window_start"),"pickup_window_end":cargo.get("pickup_window_end"),"pickup_at_km":pickup_km,"drop_at_km":drop_km,"route_class":route_class,
            "pickup_excursion_km":result["pickup_excursion_km"],"drop_excursion_km":result["drop_excursion_km"],"extra_distance_km":extra,
            "extra_active_minutes":round(extra_active,2) if extra_active is not None else None,"revenue_inr":revenue,"incremental_cost_inr":round(incremental_cost,2) if incremental_cost is not None else None,
            "net_inr":{"low":round(net_value,2) if net_value is not None else None,"expected":round(net_value,2) if net_value is not None else None,"high":round(net_value,2) if net_value is not None else None},"checks":checks,"eligible":eligible,
            "rejection_codes":result["rejection_codes"],"baseline_score":None,"model_score":None,"available_payload_kg":payload.truck.available_payload_kg,
            "explanation":[{"text":"Synthetic listing for interface demonstration." if cargo["source_type"]=="synthetic" else "Manually entered listing; source details are user-provided.","tag":"fact"},
                           {"text":"Only a verified road-network route can establish eligibility. Unknown checks are not eligible.","tag":"fact"}],
            "load_profile":[{"km":0,"load_kg":0},{"km":pickup_km,"load_kg":cargo.get("weight_kg") or 0},{"km":drop_km,"load_kg":0}],"timeline":[],
            "budget_after":{"multiplier":multiplier,"distance_limit_km":round(distance_limit,2),"time_limit_minutes":round(time_limit,1) if time_limit is not None else None,"distance_used_fraction":(extra/distance_limit if extra is not None and distance_limit>0 else (0 if extra==0 else None)),"time_used_fraction":None,"verified":bool(route["verified"])}
        }
        candidate_record["baseline_score"] = calculate_baseline_score(candidate_record)
        candidates.append(candidate_record)
    # Bundle alternatives are generated only from individually eligible listings.
    # The bundler rechecks aggregate capacity, route-order load, cluster radii,
    # whole-trip distance and active-time budgets. Original single listings remain.
    bundles = generate_bundle_candidates(candidates, payload.truck.available_payload_kg)
    for bundle in bundles:
        bundle["baseline_score"] = calculate_baseline_score(bundle)
    candidates.extend(bundles)

    # Learned inference is strictly downstream of deterministic eligibility.
    # Missing/incompatible artifacts leave model_score null and preserve baseline ranking.
    gate, model_a, model_b = Gating(), ModelA(), ModelB()
    eligible_candidates = [c for c in candidates if gate.is_allowed(c)]
    for candidate in eligible_candidates:
        features = build_features(candidate, route)
        risk_features = build_features(candidate, route, RISK_FEATURES)
        candidate["model_score"] = model_a.predict(features) if features is not None else None
        candidate["risk_estimates"] = model_b.predict(risk_features) if risk_features is not None else None
        candidate["model_version"] = model_a.model_version
        candidate["risk_model_version"] = model_b.model_version
    model_ranking_active = bool(eligible_candidates) and model_a.model_version is not None and all(c.get("model_score") is not None for c in eligible_candidates)
    for candidate in candidates:
        candidate.setdefault("model_score", None)
        candidate.setdefault("risk_estimates", None)
    candidates.sort(key=lambda c:(c["eligible"]!="pass", -((c.get("model_score") if model_ranking_active else c.get("baseline_score")) or 0), c["title"].lower()))
    response={"run_id":str(uuid4()),"route_id":route["id"],"route_version":route["version"],"config_version":CONFIG_VERSION,
              "generated_at":datetime.now(timezone.utc).isoformat(),"off_route_enabled":payload.off_route_enabled,"routing_source":"osrm" if route["verified"] else "mock",
              "route":route,"data_label":"mixed" if manual else "demonstration","caps":{**caps,"verified":bool(route["verified"])},
              "budget":{"multiplier":multiplier,"distance_limit_km":round(distance_limit,2),"time_limit_minutes":round(time_limit,1) if time_limit is not None else None,"distance_used_fraction":None,"time_used_fraction":None,"verified":bool(route["verified"])},
              "candidates":candidates,"ranking_method":"model_a" if model_ranking_active else "deterministic_baseline_or_unranked",
              "model_versions":{"model_a":model_a.model_version,"model_b":model_b.model_version},
              "notices":["Synthetic listings are demonstration data, not live freight offers.","Unknown checks are never eligible.","Regulatory checks remain unknown until a current trusted jurisdiction-policy adapter is configured.","Active-time eligibility requires baseline active time and explicit handling/waiting durations; net contribution requires complete explicit cost inputs.","The original route is never changed to accommodate a cargo listing."]}
    run=MatchRun(user_id=user.id,route_id=route["id"],route_version=route["version"],off_route_enabled=payload.off_route_enabled,response=response)
    db.add(run); await db.commit()
    response["run_id"]=run.id
    run.response=response
    await db.commit()
    return response
