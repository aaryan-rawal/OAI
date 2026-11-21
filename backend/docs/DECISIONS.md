# Backend Decision Notes

The project-wide authoritative decisions are in `../../docs/DECISIONS.md`. This file records backend implementation choices only.

- FastAPI is the HTTP application framework.
- SQLAlchemy 2.x async sessions use PostgreSQL through asyncpg; Alembic migrations use synchronous psycopg.
- The root `.env` is the only authoritative local secret/configuration file. Do not create `backend/.env`.
- Passwords are hashed with Argon2; access tokens use PyJWT (HS256) and require a signing secret of at least 32 characters.
- Operational user records use `app_users` so the legacy `users` table created by the original migration is not silently repurposed.
- Deterministic eligibility checks run before ranking. A candidate is eligible only if every mandatory check is `pass`; unknown never passes.
- OSRM must provide road-network distance and duration. Straight-line geometry is not accepted as road distance.
- No trained ML artifact is bundled. Model scores remain null until a trained/versioned artifact is installed.
- UNCTAD transport-cost indicators are not cargo listings; unverified placeholder endpoints remain disabled.
