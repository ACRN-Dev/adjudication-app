"""
Database connection and session management.
Uses SQLAlchemy with PostgreSQL via psycopg2.
Falls back to SQLite when Postgres is not reachable — this allows
the inline derivation engine and demo endpoints to operate without a live database.
"""

import os
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger("acrn.database")

_POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://acrn_user:acrn_dev_password@localhost:5432/acrn_adjudication"
)
_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "acrn_demo.db")
_SQLITE_URL = f"sqlite:///{_SQLITE_PATH}"
_DB_SSL_MODE = os.getenv("DB_SSL_MODE")

DB_OFFLINE = False


def _build_postgres_connect_args():
    """Optional psycopg2 sslmode, e.g. DB_SSL_MODE=require for an external managed Postgres."""
    return {"sslmode": _DB_SSL_MODE} if _DB_SSL_MODE else {}


def _create_engine_with_fallback():
    global DB_OFFLINE
    try:
        eng = create_engine(_POSTGRES_URL, pool_pre_ping=True, connect_args=_build_postgres_connect_args())
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ PostgreSQL connection established.")
        return eng, False
    except Exception as e:
        logger.warning(
            f"⚠ PostgreSQL unavailable ({e}). "
            "Falling back to SQLite (demo / offline mode). "
            "DB-dependent API routes will return 503."
        )
        eng = create_engine(
            _SQLITE_URL,
            connect_args={"check_same_thread": False, "timeout": 30},
            poolclass=NullPool,
        )
        # Enable WAL journal mode and busy timeout on every new connection
        @event.listens_for(eng, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
        return eng, True

engine, DB_OFFLINE = _create_engine_with_fallback()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
