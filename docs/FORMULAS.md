# OptiFreight AI — Rules and Formula Reference

This document records project-owner decisions. Units: km, minutes, kg, m³, INR. Unknown inputs remain null and must not be substituted with zero.

## 1. Off-route excursion cap (D-010)

For each off-route pickup and each off-route drop independently:

`excursion_km = road_distance(route_departure_point -> off_route_stop -> route_reentry_point)`

The permitted limit is `40.0 km` inclusive. `40.000 km` passes; `40.001 km` fails. Straight-line distance is not an acceptable substitute for road distance. If the road-routing service cannot verify the complete excursion, the check is `unknown`, and the cargo is not eligible.

## 2. Extra-job caps (D-011–D-014)

| Original route distance | Total extra jobs | Per IST pickup calendar day |
|---|---:|---:|
| `L <= 500 km` | 3 | No separate daily cap |
| `500 < L <= 1,250 km` | 5 | 3 |
| `1,250 < L <= 2,000 km` | 8 | 4 |
| `L > 2,000 km` | 10 | 4 |

Band edges belong to the lower band. The day resets at 00:00 Asia/Kolkata. A job counts on its pickup date. Cancelled jobs do not count.

## 3. Bundling (D-015–D-016)

Two or more compatible cargo listings can count as one job only when both conditions hold:

- The smallest enclosing circle of all pickup coordinates has radius `<= 5.0 km`.
- The smallest enclosing circle of all drop coordinates has radius `<= 5.0 km`.

Capacity, cargo-type, safety and all other hard checks still apply to the bundle. A bundle is not a way to bypass an individual cargo restriction.

## 4. Whole-trip detour budget (D-017–D-018)

Let `L` be the original route distance in km. The allowed multiplier is:

- `1.25` for `L <= 1,000 km`.
- `1.25 + 0.10 * (L - 1,000) / 500` for `1,000 < L < 1,500 km`.
- `1.35` for `L >= 1,500 km`.

Distance and active time are checked separately:

`distance_limit = L * (multiplier - 1)`

`active_time_limit = baseline_active_time * (multiplier - 1)`

`extra_active_time = pickup_excursion_driving + drop_excursion_driving + loading + unloading + waiting`

Active time includes driving, loading, unloading and waiting; rest is excluded. The truck form must supply the original route's baseline active time, and each cargo listing must supply loading, unloading and waiting durations (use explicit `0` when known to be none). Missing values mean the active-time check is unknown, not zero. Off-route driving durations must come from OSRM.

## 5. Net contribution (FR-19 / D-007)

`net_contribution = cargo_revenue - incremental_costs`

The current explicit-input calculation is:

`fuel = extra_distance_km / loaded_mileage_km_per_l * diesel_inr_per_l`

`toll = extra_distance_km * toll_inr_per_km`

`driver = extra_active_minutes / 60 * driver_inr_per_hour`

`incremental_costs = fuel + toll + driver + handling_fee_inr`

Incremental costs may include fuel, tolls, driver allowances and loading/unloading fees. If a required cost input is missing, the corresponding net contribution is unknown. Gross revenue must never be presented as profit.

## 6. Route corridor tolerance

The current implementation uses a provisional `0.5 km` cross-track tolerance for classifying a stop as on-route against a verified OSRM polyline. This is a configurable technical tolerance, not a substitute for the off-route 40 km road-excursion rule. It should be reviewed against the owner's intended route corridor policy before production release.

## 7. Eligibility invariant

A candidate is eligible only when every mandatory check is `pass`. Any `fail` makes it ineligible; any `unknown` prevents eligibility. ML ranking is downstream of this gate and cannot override it.
