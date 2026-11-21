# Remaining Integration Gates

Updated: 2026-11-21

This register intentionally distinguishes code-level tests from checks that require the owner's Windows machine, PostgreSQL service, network access, authoritative credentials, or the remaining Belgium OBU dataset files.

## Verified in the build workspace

- Backend pytest suite: 36 passed.
- FastAPI application import and OpenAPI generation: passed.
- Alembic migration graph: single head `0004_regulatory_assessment`.
- Offline SQL generation for migrations 0001–0004: passed. This does **not** apply migrations to a database.
- Frontend TypeScript typecheck: passed before dependency reinstall was attempted.
- Root `.env` was not edited by this integration pass.
- Original `frontend.zip` was re-extracted into the working project after the Linux dependency attempt; frontend source and package lock files remain as supplied.

## Not verified here, and why

### Frontend unit tests and production build

The uploaded `node_modules` contains Windows-native esbuild binaries. The Linux workspace cannot execute them. A clean `npm ci` requires npm registry access, which was unavailable in this environment. Run `npm ci`, `npm run typecheck`, `npm test`, and `npm run build` on Windows using the supplied `package-lock.json`. The original uploaded `frontend.zip` remains untouched.

### PostgreSQL integration

This workspace has no PostgreSQL client/server and the backend runtime `asyncpg` package is not installed. No connection or migration was attempted against the owner's database. Run `setup.bat`, start PostgreSQL, start the backend, and use `scripts/verify_windows.ps1`. Apply migrations only after a backup and explicit `-ApplyMigrations` confirmation.

### Live OSRM and truck suitability

Outbound network DNS is unavailable in this workspace, so a live OSRM request could not be completed. More importantly, a normal OSRM `car.lua` route is not proof that a loaded truck can legally or physically use the roads. The backend now distinguishes `road_network_verified` from `truck_profile_verified`. A road route from a car/unknown profile cannot authorize matching. Set `OSRM_TRUCK_PROFILE_CONFIRMED=true` only after the primary OSRM endpoint actually runs a reviewed HGV profile that models the needed restrictions. The public demo fallback is never treated as HGV-verified.

The current `routing/` folder contains a local OSRM setup guide, not built map data or a completed HGV profile. The HGV profile and a real route check remain a release gate.

### Regulatory authority integrations

The engine intentionally fails closed. India-wide official sources do not provide one unauthenticated API that can answer every route/date-specific check for E-way bills, state permits, municipal/CAQM entry restrictions, hazardous cargo, driver duty records, vehicle documents, and axle limits. The E-way bill portal's distance arithmetic is implemented only as a planning helper; it does not validate a real bill. The other checks require authorized records, jurisdiction-specific policy sources, credentials/agreements where applicable, and a legal review. Do not add a trusted source ID or mark these checks `pass` without a real adapter and evidence. Until then, the engine must keep those checks `unknown` and must not accept the candidate.

See `docs/REGULATORY_COMPLIANCE.md` for the source register and required assessment contract.

### Belgium OBU dataset

The remaining OBU dataset files have not yet appeared in the current workspace. The user indicated that they will upload the dataset in multiple subsequent messages. Do not declare OBU ingestion complete or train on a partial dataset. Inspect all parts, reconstruct/validate the original archive if split, verify checksums and licensing, then document schema and quality before feature design.

## Windows verification procedure

1. Extract the current `OAI_build.zip` to a stable path.
2. Confirm the owner's root `.env` is present; this project never overwrites it.
3. Run `setup.bat`.
4. Start PostgreSQL and verify the database backup.
5. Start the backend with `run.bat` in one terminal.
6. In another PowerShell terminal, run `scripts/verify_windows.ps1`.
7. If migrations are approved, run `scripts/verify_windows.ps1 -ApplyMigrations` and type `APPLY` at the confirmation prompt.
8. Configure and verify a real HGV OSRM endpoint before enabling `OSRM_TRUCK_PROFILE_CONFIRMED`.
9. Only after OBU dataset intake and schema review should model training begin.

## Release readiness

The project is **not yet at a truthful “only training/testing remains” state**. The code-level matching/bundling and fail-closed frameworks are present, but the external integration gates above are still open. This is deliberate: a fabricated live route, database pass, or legal compliance pass would make the product unsafe and the project report inaccurate.
