# Project Status — 2026-11-21

| Area | Current status | Evidence / limitation |
|---|---|---|
| Main project cleanup | Complete | Root `.env` preserved; root folder is `OAI` |
| Frontend source integration | Preserved | Supplied frontend source and package-lock files retained; original `frontend.zip` was not modified |
| Frontend TypeScript | Passed | `npm run typecheck` passed in this workspace |
| Frontend unit tests/build | Pending on Windows | Included `node_modules` contains Windows-native binaries; Linux test runner cannot use them and npm registry access was unavailable here. Use `npm ci`, `npm test`, `npm run build` on Windows |
| PostgreSQL | Not runtime-verified | No PostgreSQL server/client or `asyncpg` installed in this workspace. No database or migrations were modified. Offline SQL generation and Alembic graph passed |
| Alembic | Code-level verified | Single head `0004_regulatory_assessment`; offline SQL generated for revisions 0001–0004; live upgrade pending |
| Authentication / APIs | Implemented, DB integration pending | FastAPI imports and OpenAPI generation pass; PostgreSQL-backed request flow not yet exercised |
| Matching / bundling | Implemented with fail-closed rules | 36 backend tests pass; aggregate bundle checks and 40 km boundary tests included |
| Routing | Safer verification gate added | Road-network response and HGV-profile verification are now distinct. Car/public fallback cannot authorize matching. Live OSRM not reachable from this workspace |
| Regulatory checks | Framework implemented, authoritative adapters pending | Eight checks fail closed as `unknown` until a trusted, current, route-specific authority assessment is supplied. No fake compliance passes |
| Dataset inventory | Partial | Uploaded sources organized; Belgium OBU dataset files still arriving in multiple parts |
| ML | Training pending | Feature contract and model wrappers exist; no model trained and no artifact present |
| End-to-end system | Pending | Requires Windows dependency install, PostgreSQL migration/integration, live routing/HGV profile, and real regulatory source adapters |

## Non-negotiable invariants

- Preserve the existing root `.env`; do not delete or modify it without explicit permission.
- Keep root folder name `OAI` in this working package.
- Original route is immutable for matching; cargo cannot cause a route rewrite.
- Off-route pickup/drop excursion cap is 40.0 km inclusive, measured by road-network distance.
- Only `pass` on every required hard check can be eligible. `unknown` is never eligible.
- A road route from a car profile is not a verified truck route. Only a reviewed HGV profile may authorize route-dependent eligibility.
- No live GPS tracking.
- ML cannot override hard eligibility.
- Do not treat research datasets as live cargo listings without validated mapping and provenance.
