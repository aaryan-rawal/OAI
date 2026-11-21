# Changelog

All notable changes are recorded here. Each entry names the files added or changed.

## [Unreleased]

### 2026-11-20
- Completed Part 1: Curated and verified dataset inventory (34 canonical files in `DATASETS/extracted/archive2`, 9 raw Olist CSVs in `DATASETS/raw`, duplicates removed from `DATASETS_extracted/archive1`, manifest created).
- Completed Part 2: Added automated Windows environment setup and launcher:
  - Added root canonical `requirements.txt` with required dependencies including `pydantic-settings`.
  - Added `setup.bat` for environment bootstrap, dependency installation, and PostgreSQL connectivity verification.
  - Added `scripts/check_db.py` for safe database connectivity diagnostics without credential exposure.
  - Added `run.bat` for automated setup check and Uvicorn backend launch.
  - Updated backend configuration in `backend/app/config.py` for Pydantic V2 compatibility (`pydantic-settings`) and SQLAlchemy asyncpg async driver alignment.

### 2026-11-17
- Added project root files: `README.md`, `.gitignore`, `.gitattributes`, `.editorconfig`,
  `.env.example`, `CHANGELOG.md`.
- Added `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/ARCHITECTURE.md`.
- Created the empty folder structure (no code yet).
- Added `docs/REQUIREMENTS.md`, `docs/DATA_MODEL.md`, `docs/FORMULAS.md`, `docs/ML_PLAN.md`,
  `docs/TEST_PLAN.md`.
## 2026-11-21 — Full-stack integration build

- Integrated the supplied frontend source into the `OAI/frontend` project tree; the uploaded `frontend.zip` archive itself was not modified.
- Switched the integrated frontend default to the FastAPI HTTP adapter and connected Vite's `/api` proxy.
- Added PostgreSQL-backed app-user, manual cargo, matching-run, shipment and fleet models plus additive Alembic revisions 0002 and 0003.
- Implemented Argon2 password hashing, PyJWT bearer auth, manual cargo CRUD, route catalogue, matching-run persistence, shipment lifecycle and fleet APIs.
- Added fail-closed route/capacity/compatibility/time-window/40 km excursion/job-cap/distance-budget/active-time checks, explicit finance calculations and a transparent baseline score.
- Added OSRM local-first/public-fallback routing adapter. Approximate demo corridor geometry cannot grant eligibility.
- Replaced random model scores, fake UNCTAD endpoints and zero-distance routing fallback with explicit unavailable/null behaviour.
- Organized uploaded dataset files under `DATASETS/`, created dataset and SHA-256 manifests, and created sanitized DataCo/access-log modelling copies.
- Added Windows launch/migration scripts and expanded tests/documentation.
- Verified: backend domain/security tests 16 passed; frontend TypeScript typecheck passed. Database/API runtime and frontend Vitest/build remain pending due unavailable PostgreSQL and Windows-native frontend binaries in this Linux build workspace.
