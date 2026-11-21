"""Safe database connectivity check. Never prints the connection URL or credentials."""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
from app.db import engine

async def main():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        print("[OK] PostgreSQL connection succeeded.")
        return 0
    except Exception as exc:
        print(f"[ERROR] PostgreSQL connection failed ({type(exc).__name__}). Check PostgreSQL service and root .env configuration.")
        return 1
    finally:
        await engine.dispose()

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
