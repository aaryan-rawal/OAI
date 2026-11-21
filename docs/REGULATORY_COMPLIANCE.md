# Regulatory Compliance Rules — Implementation and Evidence Register

Last reviewed: 2026-11-21. Jurisdiction assumed for this first policy research pass: India. This is a software evidence register, not legal advice.

## Implementation rule

The matching engine uses a fail-closed regulatory assessment gate. It does not invent legal thresholds, infer that a permit is unnecessary, or trust a user-entered `compliant=true` flag. A candidate can pass regulatory checks only when a current server-side adapter provides all required checks, a trusted source ID, a policy version, an assessment timestamp, an expiry timestamp, a source reference, and an explicit pass/fail decision.

The configured trust allow-list is `REGULATORY_TRUSTED_SOURCES` in the root `.env`. It is empty by default. No external authority adapter is currently configured, so regulatory checks remain `unknown` and candidates cannot be accepted until this integration is completed. This is intentional, not a successful compliance claim.

## Regulatory domains represented in the engine

| Check code | Scope | Current status |
|---|---|---|
| `eway_bill` | E-way bill applicability, Part-B/vehicle details, validity and any applicable exemption/extension | Framework implemented; live record/authority verification not integrated |
| `heavy_vehicle_access` | City/state entry restrictions, vehicle class/emission standard, local time windows, exemptions and effective dates | Framework implemented; route geofences and current municipal/CAQM policy adapters pending |
| `hazardous_goods` | Hazard classification, vehicle authorization/equipment, consignor information, driver training and emergency panel/documents | Framework implemented; cargo classification and document verification adapter pending |
| `over_dimensional` | Vehicle/load dimensions, applicable vehicle class, route clearances and required permits/escorts | Framework implemented; vehicle/load dimensions and route clearance source pending |
| `driver_hours_rest` | Applicable driver duty/driving limits, rest breaks and route schedule | Framework implemented; approved jurisdiction/employment/permit policy and driver duty records pending |
| `vehicle_documents` | Registration, certificate of fitness, insurance, PUC and validity dates | Framework implemented; document/VAHAN/insurer verification pending |
| `transport_permit` | National/state permit type, route/state coverage, validity and operating conditions | Framework implemented; permit verification adapter pending |
| `vehicle_load_limits` | Registered GVW and axle-load limits against tare and loaded weight | Framework implemented; vehicle RC/axle specification and weighment data pending |

## Official sources reviewed

### E-way bill

- Official E-Way Bill System home: https://docs.ewaybillgst.gov.in/
- Official FAQ: https://docs.ewaybillgst.gov.in/html/faq_new.html
- Official rules PDF: https://docs.ewaybillgst.gov.in/Documents/EWBRules.pdf

The portal describes the general e-way bill requirement for movement of goods above ₹50,000, subject to statutory exemptions and special cases. The FAQ says regular movement validity is one day for every 200 km or part thereof; over-dimensional cargo uses one day for every 20 km or part thereof. Validity starts on the first Part-B entry for road movement. These facts are recorded as a planning helper only; the software must verify the actual e-way bill record, exemptions, amendments and validity with an authorized source before granting a pass.

`expected_eway_bill_validity_days(distance_km, over_dimensional_cargo)` implements the 200 km / 20 km arithmetic as a helper. It does not establish whether an e-way bill is required or whether a particular bill is authentic/valid.

### Hazardous goods

- Central Motor Vehicles Rules, 1989, official India Code PDF: https://upload.indiacode.nic.in/showfile?actid=AC_CG_61_1084_00001_00001_1554966634246&filename=the_central_motor_vehicles_rules%2C_1989.pdf&type=rule

The reviewed text covers hazardous-goods carriage in Rules 129–137, including class labels, consignor responsibilities, transporter/owner responsibilities, driver responsibilities, emergency information panels and driver instruction/training. The matching engine must not infer that a generic `chemicals` category is safe or that a vehicle is authorized. Classification against the applicable tables and evidence for the actual consignment/vehicle/driver are required.

### Vehicle dimensions / over-dimensional loads

The reviewed Central Motor Vehicles Rules include Rule 93 on overall vehicle dimensions and load projection. The applicable limit depends on vehicle configuration and exceptions; an exceptional/indivisible load may require additional permissions and route-specific clearance. The engine therefore does not use one generic ODC threshold. Vehicle configuration, loaded dimensions, permits, escort/route clearances and current amendments must be evaluated by a jurisdiction-aware adapter.

### City entry restrictions

- CAQM official website: https://caqm.nic.in/
- CAQM Direction No. 88 and amendment materials are linked from the official site.
- CAQM amendment PDF reviewed: https://caqm.nic.in/WriteReadData/LINKS/Amendment%20to%20Direction%20No-88%20dt%2017102025c52ddd7a-d5b9-4f09-a68a-77d6005fea5e.pdf
- PIB release reviewed: https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2317093&lang=2&reg=48

Delhi restrictions depend on vehicle category, emission standard, registration, date and active GRAP orders. The reviewed CAQM material includes Direction No. 88 and amendments, and the 2026 PIB review refers to its enforcement alongside other vehicle-related directions. Delhi Transport Department/CAQM restrictions depend on vehicle category, emission standard, registration, date and applicable GRAP stage. A static city-wide time window is not a sufficient implementation; current orders must be retrieved and versioned at runtime. The route engine needs current official zone/policy data and vehicle fields before it can decide entry eligibility.

## Not yet encoded as hard-coded values

- No generic driver-hours/rest limit has been inserted. A verified applicable rule and the relevant state/permit/employment context must be established before encoding it.
- No generic city-entry schedule has been inserted. Restrictions vary by city, road, vehicle class, registration/emission category, date and emergency pollution stage.
- No universal ODC permit threshold has been inserted. Vehicle type, axle configuration, dimensions, load type and route/authority permissions matter.
- No E-way bill applicability decision is inferred from `rate_inr`; cargo rate is not necessarily consignment value or taxable value.

## Server-side assessment contract

A trusted adapter may persist a `compliance_assessment` object on a cargo record:

```json
{
  "source_id": "approved-authority-adapter-id",
  "policy_version": "jurisdiction-policy-version",
  "assessed_at": "2026-11-21T00:00:00Z",
  "expires_at": "2026-11-21T06:00:00Z",
  "checks": [
    {"code": "eway_bill", "status": "pass", "source_reference": "authority-record-reference", "message": "Bill verified and valid through planned delivery."},
    {"code": "heavy_vehicle_access", "status": "pass", "source_reference": "official-order-reference", "message": "Vehicle is permitted for the relevant zone and arrival time."},
    {"code": "hazardous_goods", "status": "pass", "source_reference": "document-verification-reference", "message": "Not applicable under the verified cargo classification."},
    {"code": "over_dimensional", "status": "pass", "source_reference": "permit-reference", "message": "Not applicable under verified dimensions and vehicle configuration."},
    {"code": "driver_hours_rest", "status": "pass", "source_reference": "approved-driver-policy-reference", "message": "Verified driver duty and rest record meets the applicable policy."},
    {"code": "vehicle_documents", "status": "pass", "source_reference": "vehicle-document-verification-reference", "message": "Registration, fitness, insurance and PUC records are valid."},
    {"code": "transport_permit", "status": "pass", "source_reference": "permit-verification-reference", "message": "Permit scope covers the planned route and operation."},
    {"code": "vehicle_load_limits", "status": "pass", "source_reference": "vehicle-specification-reference", "message": "Registered gross and axle load limits are not exceeded."}
  ]
}
```

The example is a schema illustration only, not a real assessment. Only server-side integrations may write this object. The public manual-cargo endpoint does not accept it.

## Release blocker

Before production, obtain a current legal review of the applicable central/state/city rules, implement official-source adapters and route-zone coverage, test effective-date transitions and exemptions, and have the owner approve the compliance policy version. Until then, all regulatory checks remain `unknown` and the engine must not accept a candidate.
