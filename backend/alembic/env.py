from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
import sys
from pathlib import Path

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))
from app.config import settings
from app.models import Base

# Alembic uses the synchronous psycopg driver; the application uses asyncpg.
url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://").replace("postgresql+psycopg2://", "postgresql+psycopg://").replace("postgresql://", "postgresql+psycopg://")
config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle":"named"}, compare_type=True)
    with context.begin_transaction(): context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.",
                                     poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction(): context.run_migrations()

if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
