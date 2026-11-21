from app.domain.india_vehicle_limits import assess_india_gvw

def test_rigid_vehicle_is_capped_by_overall_gvw():
    result = assess_india_gvw(vehicle_form="rigid", axle_groups=[{"kind":"single_2_tyres"},{"kind":"tandem_rigid"},{"kind":"single_2_tyres"}], type_approved_gvw_kg=60000, tyre_capacity_gvw_kg=60000)
    assert result.maximum_gvw_kg == 35000

def test_missing_vehicle_specific_inputs_fail_closed():
    result = assess_india_gvw(vehicle_form="rigid", axle_groups=[], type_approved_gvw_kg=None, tyre_capacity_gvw_kg=None)
    assert result.status == "unknown" and result.maximum_gvw_kg is None

def test_semi_articulated_overall_cap():
    result = assess_india_gvw(vehicle_form="semi_articulated", axle_groups=[{"kind":"single_2_tyres","count":2},{"kind":"tandem_rigid","count":2}], type_approved_gvw_kg=70000, tyre_capacity_gvw_kg=70000)
    assert result.maximum_gvw_kg == 55000
