# Urgent build update — 21 November 2026

This update is based on `OptiFreight_AI_Updated_Fixed.zip`.

## Implemented in this pass

- Added a role-aware `/portals` workspace and routed the authenticated portal home to it.
- Platform owner workspace: company onboarding decisions, blacklist/restore controls, audit history, notifications.
- Company owner workspace: company profile submission for the second approval stage.
- Company administrator workspace: driver cargo request review and notifications.
- Driver workspace: company cargo discovery, request submission, approved assignment view, notifications.
- Added exclusive cargo assignment fields and Alembic migration `0009_cargo_assignment`.
- Approving a driver request now locks the cargo row and assigns the cargo to that driver; concurrent/repeated approvals fail closed.
- Added `/api/driver/assignments`.
- Added local OCR preview endpoint `/api/documents/ocr/preview`, PaddleOCR primary with Tesseract fallback, and explicit human-review warning. Optional dependencies are in `backend/requirements-ocr.txt`; the Tesseract executable is an OS dependency.
- Added unique-request conflict handling.

## Verification performed

- Python compileall: passed.
- Backend automated tests: 46 passed.
- FastAPI import: passed; 55 routes registered.
- Alembic head: `0009_cargo_assignment`.
- TypeScript/TSX syntax parsing for changed frontend files: passed.
- ZIP integrity: checked after packaging.
- `.env` SHA-256 before packaging: `6c1d70af40e13e80cde3d66c0c439bd3fd6c7f825c5cfdc40c7566673446866a`; file was not edited.

## Not verified / still dependent on user's environment or external providers

- Full frontend typecheck/build and browser E2E: npm dependency installation timed out in this environment; `vite/client` typings are unavailable here.
- PostgreSQL migration execution and live DB workflows: not run; user must back up DB and run `alembic upgrade head` locally.
- SMS OTP delivery: Twilio/provider credentials and approved sender are required in `.env`.
- Maps and HGV road routing: Google Maps key and a configured road-routing service/data are required; route approval must fail closed when road-network verification is unavailable.
- E-Way Bill and identity verification: provider-specific API credentials, endpoints, certificates/registration and contracts are required. Adapter scaffolding is not proof of live integration.
- OCR runtime: install `backend/requirements-ocr.txt` and Tesseract or configure PaddleOCR; OCR remains candidate extraction only, not authenticity or licence validity verification.
- ML model training/evaluation, Belgium OBU schema validation/integration, full hazardous-goods regulatory verification and end-to-end production tests remain separate work.

## Important scope limitation

The new portal page connects existing API workflows; it does not mean every legacy page, company-admin provisioning process, every vehicle/document workflow, or every operational edge case is production-complete. No live database, third-party provider, or production deployment was available to verify in this environment.
