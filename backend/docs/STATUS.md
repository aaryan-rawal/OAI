# Backend Status

Last updated: 2026-11-21.

- **Application/API code**: FastAPI app import and OpenAPI generation verified. PostgreSQL-backed request flow remains pending.
- **Database**: SQLAlchemy operational models and Alembic revisions 0001–0004. Revision 0004 adds a server-managed JSONB regulatory assessment field. Alembic has one head (`0004_regulatory_assessment`); offline SQL generation passed. No live migration was run and no database was modified.
- **Authentication**: Argon2 password hashing and PyJWT implemented. The root `.env` secret must meet the 32-character minimum; the owner must rotate it manually if required.
- **Matching**: Fail-closed deterministic checks for capacity, body compatibility, route corridor, route order, per-stop 40 km road excursion, pickup timing, trip job caps, daily caps, whole-trip distance and active-time budgets.
- **Bundling**: Candidate generation for compatible, individually eligible same-category cargo. Aggregate pickup/drop cluster radii, capacity, route-order load profile, distance and active time are rechecked.
- **Regulatory**: Fail-closed checks for e-way bill, heavy-vehicle access, hazardous goods, ODC, driver-hours/rest, vehicle documents, route permits and registered GVW/axle-load limits. No single unauthenticated official API supplies all route/date-specific decisions. Trusted jurisdiction adapters, credentials/agreements where applicable, and legal review remain release blockers.
- **Finance**: Net contribution is calculated only when revenue, extra distance/time and every explicit cost input are present.
- **Routing**: OSRM road-network verification is separated from truck-profile verification. Public/demo car routing cannot authorize truck matching. `OSRM_TRUCK_PROFILE_CONFIRMED=true` is permitted only for a primary endpoint running a reviewed HGV profile. Live requests were blocked by this workspace's unavailable outbound DNS.
- **Cargo**: Manual cargo CRUD; research datasets are not automatically treated as live freight listings.
- **Shipments/fleet**: API lifecycle implemented; PostgreSQL integration pending.
- **ML**: Feature contract, artifact loaders and training scaffolds implemented. No training/evaluation was run; no model artifacts exist. Model inference is downstream of the hard eligibility gate.
- **Tests**: 36 backend tests pass in this workspace. Frontend typecheck passes. Frontend unit tests/build and Windows/PostgreSQL end-to-end verification remain pending.
