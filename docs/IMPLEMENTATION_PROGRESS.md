# OptiFreight AI — Implementation Progress

Last updated: 2026-11-21. Status reflects this working build assembled from the uploaded main project, the unchanged frontend archive and dataset files. A code file existing is not the same as a feature being runtime-verified.

## Part 1 — Dataset preparation and inventory

**Status: PARTIALLY COMPLETE — uploaded sources organized; Belgium OBU pending.**

- Organized uploaded CSVs under `DATASETS/raw/`.
- Retained source ZIPs under `DATASETS/source_archives/` and extracted Olist/AnonNet datasets under `DATASETS/extracted/`.
- Extracted SimMD, supply-chain disruption monitoring and SynDelay research repositories under `DATASETS/repositories/`.
- Created `DATASETS/manifests/dataset_manifest.json` and `DATASETS/README.md`.
- Belgium OBU (Kaggle `giobbu/belgium-obu`) is not present in this workspace and remains pending inspection.
- Previous claims about a separate 34-file traffic parquet collection were not verifiable from the uploaded dataset files in this build and are not marked as re-verified.

## Part 2 — Environment and launch infrastructure

**Status: IMPLEMENTED; Windows runtime verification pending.**

- Root `requirements.txt` is the canonical Python dependency list.
- Root `.env` was preserved byte-for-byte from the supplied cleaned archive. No `.env` values are reproduced in documentation.
- Added `.env.example` as a template only; it must not overwrite an existing `.env`.
- Added/updated `setup.bat`, `run.bat`, `run_frontend.bat`, `run_all.bat`, and `migrate.bat`.
- `scripts/check_db.py` uses SQLAlchemy 2.x `text()` and does not print credentials.

## Part 3 — Database models and migrations

**Status: IMPLEMENTED, NOT DATABASE-VERIFIED.**

- Added SQLAlchemy 2.x models for app users, manual cargo, matching runs, shipments, fleet drivers and fleet containers.
- Added Alembic revision `0002_operational_app` while preserving the existing `0001_initial` revision identity.
- New application identities use `app_users` so the older legacy `users` table is not silently repurposed.
- Migration execution is manual and requires a database backup. No database was accessed or modified during this build.

## Part 4 — Authentication

**Status: IMPLEMENTED IN CODE; DATABASE/HTTP VERIFICATION PENDING.**

- Added JSON registration and login endpoints.
- Passwords use Argon2 hashing; JWTs use the root `.env` secret.
- Added bearer-token current-user dependency and administrator profile guard.
- Password minimum matches the supplied frontend validation (8 characters).

## Part 5 — Backend API

**Status: IMPLEMENTED IN CODE; DATABASE/HTTP VERIFICATION PENDING.**

- Routes catalogue: `GET /api/routes` and `GET /api/routes/{route_id}`.
- Authentication: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`.
- Manual cargo CRUD: `GET/POST /api/cargo/manual`, `DELETE /api/cargo/manual/{id}`.
- Matching: `POST /api/matching/run`.
- Shipments: create/accept, list, read, assign, advance and cancel under `/api/shipments`.
- Fleet drivers and containers under `/api/fleet`.
- Admin profile: `GET /api/admin/profile`.
- Health/readiness: `/health`, `/health/ready`.

## Part 6 — Deterministic matching engine

**Status: PARTIALLY IMPLEMENTED; IMPORTANT HARD RULES ARE FAIL-CLOSED.**

- Added WGS84 Haversine and route-polyline nearest-point helpers.
- Added route-distance job caps and piecewise trip budget multiplier.
- Added vehicle-body compatibility checks based on the frontend's documented matrix.
- Added route verification gating, pickup-before-drop ordering, pickup-window ETA check, per-stop road excursion checks and total/daily job-cap checks.
- Added conservative bundle alternatives from individually eligible same-category cargo. Bundles recheck smallest-enclosing-circle pickup/drop radii, combined payload, route-order load profile, aggregate trip distance and active-time budgets. Bundle generation remains unavailable until all member regulatory and other hard checks pass.
- Added a fail-closed regulatory assessment gate for e-way bill, heavy-vehicle access, hazardous-goods requirements, over-dimensional permits, driver-hours/rest, vehicle documents, route permits and registered GVW/axle-load limits. No legal thresholds are guessed; a current trusted jurisdiction adapter is still required.
- OSRM road geometry is used only when the routing call succeeds. Seed/demo route geometry remains unverified otherwise.
- Off-route excursion is measured by OSRM round trip from the nearest point on the route polyline to the stop and back. Exactly 40 km is accepted by the comparison; above 40 km fails.
- Whole-trip distance and active-time budgets are checked separately. Active time uses truck-supplied baseline active minutes plus OSRM off-route driving durations and explicit per-cargo loading/unloading/waiting minutes; missing values remain unknown.
- Net contribution is calculated only when revenue, extra distance, active time, diesel, loaded mileage, toll, driver rate and handling fee are all explicitly available.
- A transparent provisional baseline score ranks only candidates whose every hard check passes and whose net contribution and payload utilization are known. No ML model score is fabricated.
- Bundle candidate generation and aggregate checks are implemented, but additional cargo-specific volume/handling/segregation constraints and multi-stop sequencing need expansion before production.
- Regulatory assessment framework is implemented. Live e-way bill, local heavy-vehicle access, hazardous-goods, ODC, driver-hours/rest, vehicle-document, transport-permit and axle-load verification remain blocked on trusted data adapters and approved jurisdiction policy.
- Driver-hours/rest policy values and authoritative financial assumptions remain unimplemented; no unverified legal limits or cost assumptions are invented.
- No trained ML score is returned. A provisional deterministic baseline score is separate from ML. Unknown checks are never eligible.

## Part 7 — Routing and mapping

**Status: PARTIALLY IMPLEMENTED.**

- Added OSRM HTTP adapter using configurable root `.env` `OSRM_URL` and fallback URL.
- Added response-code, geometry-coordinate, positive metric, endpoint-snap and endpoint-geometry checks before marking a road route verified.
- Added `POST /api/routes/{route_id}/verify`; matching uses the same verification function.
- Per-stop round-trip road excursion is implemented through OSRM as route-departure -> stop -> route-re-entry.
- Automated mock-response tests cover successful verification, bad response code, invalid coordinates and excessive endpoint snapping.
- Live OSRM route calls, local OSRM deployment, caching policy, rate-limit policy and real-map end-to-end verification remain pending.

## Part 8 — Cargo ingestion

**Status: PARTIALLY IMPLEMENTED.**

- Manual cargo persistence/API is implemented.
- Uploaded datasets are inventoried and stored as research inputs.
- DataCo/Olist/AnonNet/SimMD/SynDelay/disruption-monitoring datasets are not automatically treated as live freight listings.
- CSV normalization, deduplication, source-specific field mapping and authorized public cargo API ingestion remain pending.
- UNCTAD transport-cost indicators are not cargo listings; the old placeholder UNCTAD endpoints were disabled rather than retained as false integrations.

## Part 9 — Machine learning

**Status: DEVELOPMENT SCAFFOLD IMPLEMENTED; NOT TRAINED OR EVALUATED.**

- Added one versioned serving/training feature contract. Missing feature values are not imputed as zero.
- Model A loads a versioned LightGBM ranking artifact only when its metadata matches the feature schema.
- Model B loads p10/p50/p90 LightGBM quantile artifacts for delay and incremental-cost estimates.
- Matching calls ML only after all deterministic checks pass. ML can never override eligibility.
- Added reproducible training CLI scaffolding; no training was run and no model artifacts were created.
- SynDelay's three-class target has not been mapped to a project label. Dataset suitability, owner-approved labels, final leakage-safe split design, training, calibration and locked test evaluation remain for the dedicated ML phase.

## Frontend integration

**Status: SUPPLIED FRONTEND PRESERVED BYTE-FOR-BYTE; TYPECHECK PASSED; TEST/BUILD BLOCKED BY WINDOWS NODE_MODULES IN THIS LINUX WORKSPACE.**

- Restored `frontend/` from the user's supplied `frontend.zip` without changing its source, package files, lockfiles, `node_modules`, or `dist`.
- Verified all 7,949 files from `frontend.zip` match the integrated `frontend/` copy byte-for-byte. The uploaded ZIP itself remains untouched.
- The supplied frontend defaults to its browser-only mock API. Its HTTP adapter contains proposed paths matching the backend; enable it locally with `VITE_API_MODE=http` in `frontend/.env.local` when ready.
- `npm run typecheck` passed.
- Vitest/build are blocked in this Linux workspace because the supplied `node_modules` contains Windows `esbuild` binaries. On Windows, use `npm ci` (not copied `node_modules`) before running the frontend test/build commands.

## Verification performed in this build environment

- Python syntax compilation: performed on backend Python files.
- Backend domain/security/advanced-rule tests: 34 passed.
- FastAPI health and OpenAPI import checks: passed without opening a database connection.
- Frontend TypeScript typecheck: passed against the unchanged supplied frontend.
- Frontend Vitest/build: blocked by cross-platform native `esbuild` binary mismatch.
- PostgreSQL migration and API integration: not run; the user's local database was not accessed.
- OSRM live requests: not verified from this environment.

## Next implementation priorities

1. Review migration history, back up PostgreSQL, then apply migrations on the user's Windows environment only after explicit approval.
2. Run backend and HTTP integration tests on Windows with the actual `.env`.
3. Configure an authoritative regulatory source adapter and approve current jurisdiction policy; until then regulatory checks correctly remain unknown.
4. Expand remaining handling/volume/special-cargo, driver-hours/rest and full trip-sequencing rules using approved policies.
5. Verify route excursions and trip-budget boundaries against live/local OSRM and a set of real road scenarios.
6. Inspect the downloaded Belgium OBU dataset when it is provided; assess license, privacy, fields and suitability before using it.
7. Approve label definitions and leakage-safe splits, then train/evaluate Model A and Model B. Model C remains optional.
8. Enable HTTP mode and complete frontend-to-backend end-to-end tests on Windows.
