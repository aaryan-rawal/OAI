"""Conservative reference limits transcribed from MoRTH 2018 axle-load notifications.

These are NOT a complete per-model legal determination. The binding limit is the lowest of
manufacturer/type-approved GVW, notified axle-group capacity and tyre load capacity. Vehicle
registration certificate/type approval and state/road restrictions remain authoritative.
"""
from dataclasses import dataclass

AXLE_GROUP_LIMIT_KG = {
    "single_1_tyre": 3000,
    "single_2_tyres": 7000,
    "single_4_tyres": 11500,
    "tandem_rigid": 21000,
    "tandem_puller": 28500,
    "tridem_rigid": 27000,
    "modular_axle_row": 18000,
}
OVERALL_GVW_CAP_KG = {"rigid": 49000, "semi_articulated": 55000}

@dataclass(frozen=True)
class LegalLoadAssessment:
    status: str
    maximum_gvw_kg: int | None
    axle_capacity_kg: int | None
    reasons: tuple[str, ...]

def assess_india_gvw(*, vehicle_form: str, axle_groups: list[dict], type_approved_gvw_kg: float | None,
                     tyre_capacity_gvw_kg: float | None, pneumatic_suspension: bool = False) -> LegalLoadAssessment:
    if vehicle_form not in OVERALL_GVW_CAP_KG:
        return LegalLoadAssessment("unknown", None, None, ("Vehicle form must be rigid or semi_articulated.",))
    if not axle_groups or type_approved_gvw_kg is None or tyre_capacity_gvw_kg is None:
        return LegalLoadAssessment("unknown", None, None,
            ("Enter the vehicle-specific type-approved GVW, tyre load capacity and axle-group configuration from authoritative vehicle documents.",))
    total = 0
    for group in axle_groups:
        kind = group.get("kind")
        count = int(group.get("count", 1))
        if kind not in AXLE_GROUP_LIMIT_KG or count < 1:
            return LegalLoadAssessment("unknown", None, None, (f"Unsupported or incomplete axle group: {kind!r}.",))
        capacity = AXLE_GROUP_LIMIT_KG[kind]
        if pneumatic_suspension and kind in {"single_1_tyre", "single_2_tyres", "single_4_tyres", "tandem_rigid", "tridem_rigid"}:
            # Notification permits +1 tonne per axle for pneumatic suspension, subject to all caps.
            axles = 1 if kind.startswith("single") else (2 if kind == "tandem_rigid" else 3)
            capacity += 1000 * axles
        total += capacity * count
    overall = OVERALL_GVW_CAP_KG[vehicle_form]
    maximum = int(min(total, overall, type_approved_gvw_kg, tyre_capacity_gvw_kg))
    return LegalLoadAssessment("calculated_reference_cap", maximum, total,
        ("Calculated as the lowest of axle-group notification capacity, overall vehicle-form cap, type-approved GVW and tyre capacity.",
         "Verify the exact make/model, axle/tyre configuration, registration certificate and applicable amendments before operational use."))
