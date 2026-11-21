# OptiFreight AI — Intelligent Freight Optimization

OptiFreight AI is a full-stack post-delivery backhaul cargo matching application. It evaluates additional cargo against a truck's already-planned onward route. The original route remains fixed; deterministic eligibility checks run before any ranking or ML; unknown checks are never eligible; no live GPS is used.

## Current integrated structure

- `backend/` — FastAPI API, PostgreSQL persistence, authentication, cargo listings, matching, fleet and shipment endpoints.
- `frontend/` — supplied React + TypeScript + Vite interface, preserved exactly as uploaded. Configure its existing HTTP adapter with `VITE_API_MODE=http` when ready; it otherwise uses its built-in mock mode.
- `DATASETS/` — uploaded raw files, extracted datasets, processed copies, selected research repositories and manifests. Original source ZIPs are preserved in the companion `OAI_dataset_source_archives.zip`.
- `routing/` — OSRM configuration and demo corridor references.
- `docs/` — requirements, architecture, decisions, formulas, test plan and implementation progress.

## Locked rules

- Post-delivery backhaul matching only.
- The original onward route is fixed and must not be changed to fit a cargo listing.
- On-route delivery is the default.
- Optional off-route delivery is driver-controlled; each off-route stop's round-trip road excursion must be no more than 40.0 km. Exactly 40.0 km passes; 40.001 km fails.
- Job caps depend on original route distance; band edges belong to the lower band. Daily caps reset at midnight Asia/Kolkata and count the pickup date.
- Compatible bundles require same-category cargo, pickup and drop clusters each to have a smallest-enclosing-circle radius no greater than 5 km, aggregate payload and route-order load feasibility, compatible pickup windows, and aggregate distance/time budgets.
- Whole-trip distance and active-time budgets are checked separately.
- Unknown is not zero. Missing route, time, capacity, or cost information cannot be silently treated as a pass.
- Synthetic listings and synthetic-trained models must be labelled as such.
- Truck location is simulated or user-selected; no live GPS.
- Net contribution is revenue minus incremental costs, not gross revenue labelled as profit.

## Run on Windows

Prerequisites: Python 3.11+ (3.13 recommended for dependency compatibility), Node.js 20+, PostgreSQL 16+ with PostGIS if using the legacy route-geometry migration.

1. Preserve the existing root `.env`. Do not overwrite it. `.env.example` is only a template for a new setup.
2. Run `setup.bat` to create/reuse `.venv` and install Python requirements.
3. Ensure PostgreSQL is running and the database named in `.env` exists.
4. Review all revisions in `backend/alembic/versions/` (currently 0001–0004), back up the database, then run `migrate.bat` to apply pending migrations. Migrations are never run automatically by the app launcher.
5. Run `run_all.bat` to launch the FastAPI backend (`http://127.0.0.1:8000`) and Vite frontend (`http://localhost:5173`).
6. API docs: `http://127.0.0.1:8000/docs`; health: `http://127.0.0.1:8000/health`; database readiness: `http://127.0.0.1:8000/health/ready`.

The supplied frontend is preserved unchanged and defaults to its browser-only mock API. To use the backend, create `frontend/.env.local` with `VITE_API_MODE=http`; the HTTP adapter targets the backend `/api` routes. The original `frontend.zip` and both lockfiles are retained unchanged.

## Important implementation status

This is an active build, not a claim of production readiness. The API foundation, persistence models, auth, manual cargo CRUD, matching-run endpoint, shipment lifecycle and fleet endpoints have been implemented in this working copy. Bundling, stricter OSRM verification, fail-closed regulatory assessment gating and ML artifact/training scaffolds have been added. Backend database migrations and end-to-end runtime checks still require the user's PostgreSQL environment. Regulatory checks remain unknown until a trusted authority adapter is configured. Missing handling/time/cost/routing inputs remain unknown. No ML model has been trained; no model artifacts are bundled. Dataset integration is research-only until a schema and licensing review maps a dataset to a legitimate cargo source or training target.

See `docs/IMPLEMENTATION_PROGRESS.md`, `docs/STATUS.md`, `docs/REGULATORY_COMPLIANCE.md`, `ml/README.md`, and `DATASETS/README.md`.

## Optional integrations and compliance modules
See `docs/FINAL_CODE_PASS_NOTES.md` for the optional E-Way Bill and identity-provider adapter contracts, Google Maps configuration, private document upload endpoints, hazardous-cargo evidence, fleet compliance fields, driver rest log and Indian axle/GVW reference calculation. These modules remain unverified until provider access, the local database, private file storage, actual documents and route data are configured and tested.

The integrated frontend defaults to the HTTP backend. Set `VITE_API_MODE=mock` only when intentionally running the demonstration adapter. The root `.env` may contain `VITE_GOOGLE_MAPS_EMBED_KEY`; without it the existing Leaflet minimap remains active.


## Registration and sign-in update

New registrations now require a phone number and a one-time phone verification step. After verification, users sign in with their exact account name, verified phone number, or email plus password. If an account name is not unique, sign-in requires phone or email. Existing accounts without a phone number retain email/name password sign-in until their profile is updated.

**OTP delivery status:** no SMS provider credentials or provider contract were supplied. In local development (`APP_ENV=development`), the OTP is displayed in the registration UI and logged by the backend so the flow can be tested. Production registration fails closed with HTTP 503 until an authorized SMS provider adapter is configured. This is not live SMS delivery. No paid SMS service or SMS notification feature has been added.

Apply the new migration after backing up your PostgreSQL database: `alembic upgrade head` from `backend`. The migration adds nullable phone fields and an OTP challenge table; it does not modify existing user passwords.

## Belgium OBU dataset

See `DATASETS/BELGIUM_OBU_PROFILE.md`. The raw dataset remains on the workstation and is not bundled into this ZIP. The inventory script now treats CSV files as headerless pending documentation, because the initial inventory showed that first-row data values had been misidentified as headers.
