# Final code-side integration pass — implementation notes

## Optional API configuration
The root `.env` now has blank placeholders for E-Way Bill provider credentials, identity verification provider credentials, and `VITE_GOOGLE_MAPS_EMBED_KEY`. Existing values were retained. Do not commit `.env`.

- Google Maps: Vite reads the root `.env` and exposes only `VITE_GOOGLE_MAPS_EMBED_KEY` to the browser. Shipment minimaps use Google Maps only when this key is present; otherwise they continue using the existing Leaflet/OpenStreetMap minimap. Restrict the key by HTTP referrer and the Maps Embed API in Google Cloud. This is a browser-visible key, not a server secret.
- E-Way Bill: optional backend endpoints are provided at `GET /api/integrations/status` and `POST /api/integrations/ewaybill`. No payment page, checkout, or purchase flow has been added. The adapter is disabled when its environment variables are blank.
- Identity verification: `POST /api/integrations/identity/verify` forwards data only when an explicit provider base URL, API key, and provider name are configured. It does not store raw Aadhaar, PAN or driving-licence values.

**Provider caveat:** a key alone cannot make an arbitrary commercial/Government API work. The provider must be selected and its authentication, endpoint paths, request schema, response schema, IP allowlisting, onboarding and legal permissions must be known. The current adapters use a small normalized provider contract (`POST /verify` and `POST /ewaybill`). A provider with a different contract needs a provider-specific adapter; do not paste credentials until the provider confirms its contract. E-Way Bill credentials may be issued by an authorized GSP/provider rather than being a single generic government API key.

## Fleet records and documents
- Company fleet driver records now accept optional licence number, date of birth and address fields.
- Company vehicle records retain structured truck specifications and now have a private document metadata field.
- Private upload endpoints accept PDF/JPG/JPEG/PNG for vehicle RC, transport permits, over-dimensional permits, and driver licence/PAN/Aadhaar document files. Uploads are size-limited and file signatures are checked; they are marked `uploaded_unverified`, never treated as government-verified.
- Upload bytes are stored under `backend/uploads` by default. Keep this directory private and excluded from source control. Before production, use private object storage, malware scanning, access auditing, retention/deletion controls and encrypted backups.

## Database
Migration `0005_fleet_compliance` adds nullable driver profile fields, vehicle document metadata and a rest-event ledger. It is additive/non-destructive. No migration was applied to any database in this workspace. The previously identified legacy/current migration history discrepancy remains a pre-deployment review item; do not run migrations against a production database until its current Alembic revision and legacy table ownership have been checked.

## Not represented as verified
- Uploaded RC/permit/identity documents are not OCR-verified by this pass. A document upload is evidence supplied by a user, not proof that the government record is valid.
- No live VAHAN/Sarathi/Aadhaar/PAN or state transport authority access is assumed.
- E-Way Bill is not live until a paid/authorized provider and its exact API contract are configured and tested.
- India-wide HGV routing, city entry windows, state restrictions and vehicle-specific legal dimensions/weights still require current authoritative source data and a validated truck routing engine. Do not mark a route compliant from OpenStreetMap tags alone.
- Driver rest logging is available in the driver portal. A backend monitor checks every 60 seconds and permanently blacklists a driver when an assigned active shipment has had no self-reported rest record and no final delivery completion for the configured 24-hour policy window. New assignments are blocked for blacklisted drivers. This is a company policy implementation, not a statement of statutory Indian driver-hour law. A driver-entered rest record cannot prove the vehicle was actually parked; this project has no GPS/telematics by design.
- Hazardous cargo now has a dedicated checkbox/description and a vehicle-securement evidence upload. ODC and transport permit documents, expiry dates and permitted routes can be entered against a company vehicle. These documents are stored as unverified evidence; permit authenticity, route restrictions and hazardous-goods legal eligibility are not automatically adjudicated yet.

## Frontend API mode
The integrated frontend now defaults to the HTTP backend unless `VITE_API_MODE=mock` is explicitly set. `.env.example` documents `http` as the integrated default. The mock/demo API remains available by explicitly setting mock mode.

## Indian load-limit reference implemented
`backend/app/domain/india_vehicle_limits.py` and `TruckIn` validation now provide a fail-closed reference calculation from MoRTH's 16 July 2018 axle-load notification as amended 6 August 2018. It supports the notified axle-group categories and caps rigid vehicles at 49,000 kg and semi-articulated/truck-trailer vehicles at 55,000 kg. The result is the lowest of axle-group capacity, overall cap, vehicle type-approved GVW and total tyre capacity. If vehicle-specific type approval, tyre capacity or axle configuration is missing, the assessment remains `unknown`; the code does not guess. The company fleet form captures these values and the axle-group JSON. This is a reference check, not a legal certificate: verify the actual RC/type approval, tyre specifications, vehicle configuration and current amendments before operating.

Primary sources: MoRTH advisory summarizing S.O. 3467(E) dated 16-07-2018 and S.O. 3881(E) dated 06-08-2018; official Gazette notification S.O. 3881(E).

Company-entered permitted states, restricted cities and city entry windows are retained on the vehicle record. They are not yet matched against a maintained official state/city restriction dataset or used to authorize a route; treat their status as unknown until that rules engine/data source is implemented.

## Verification performed in the build workspace
- Backend Python compilation: passed.
- Backend pytest suite: 39 passed.
- Alembic graph: one head (`0006_hazardous_cargo`).
- Alembic offline SQL generation: passed; no migration was applied to a live database.
- Frontend TypeScript typecheck: passed before removing platform-specific `node_modules` from the distributable ZIP.
- Frontend production Vite build: not verified in this Linux workspace because the supplied `node_modules` contained Windows-only esbuild binaries. The ZIP omits `node_modules` and `dist`; run `npm ci` then `npm run build` on the Windows development machine.
- PostgreSQL live connectivity, live external APIs, Docker/OSRM graph build, route validation and end-to-end UI/API tests: not run.
