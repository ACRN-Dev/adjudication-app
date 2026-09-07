"""
Database connection and session management.
Uses SQLAlchemy with PostgreSQL via psycopg2.
Falls back to SQLite when Postgres is not reachable — this allows
the inline derivation engine and demo endpoints to operate without a live database.
"""

import os
import logging
from urllib.parse import quote_plus
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger("acrn.database")


def _build_postgres_url():
    """Assembles the Postgres URL from discrete DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT vars."""
    user = os.getenv("DB_USER", "acrn_user")
    password = os.getenv("DB_PASSWORD", "acrn_dev_password")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "acrn_adjudication")
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{name}"


_POSTGRES_URL = _build_postgres_url()
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


def _migrate_sqlite_schema(eng):
    """Ensure newly added columns exist in existing SQLite databases."""
    try:
        with eng.connect() as conn:
            # Check adjudication_visits
            res = conn.execute(text("PRAGMA table_info(adjudication_visits)"))
            cols = {row[1] for row in res.fetchall()}
            if cols and "final_fetal_assessments" not in cols:
                conn.execute(text("ALTER TABLE adjudication_visits ADD COLUMN final_fetal_assessments JSON"))

            # Check adjudication_records
            res = conn.execute(text("PRAGMA table_info(adjudication_records)"))
            cols = {row[1] for row in res.fetchall()}
            if cols:
                for col_name, col_type in (
                    ("fetal_neonatal_assessments", "JSON"),
                    ("gestational_age_at_delivery", "FLOAT"),
                    ("pregnancy_outcome", "VARCHAR(100)"),
                    ("fetal_assessment_status", "VARCHAR(50)"),
                    ("fetal_neonatal_provenance", "JSON"),
                ):
                    if col_name not in cols:
                        conn.execute(text(f"ALTER TABLE adjudication_records ADD COLUMN {col_name} {col_type}"))

            # Check committee_decisions
            res = conn.execute(text("PRAGMA table_info(committee_decisions)"))
            cols = {row[1] for row in res.fetchall()}
            if cols:
                for col_name, col_type in (
                    ("final_fetal_assessments", "JSON"),
                    ("final_ga_at_delivery", "FLOAT"),
                    ("final_pregnancy_outcome", "VARCHAR(100)"),
                    ("fetal_neonatal_provenance", "JSON"),
                ):
                    if col_name not in cols:
                        conn.execute(text(f"ALTER TABLE committee_decisions ADD COLUMN {col_name} {col_type}"))
            conn.commit()
    except Exception as exc:
        logger.debug(f"Schema migration note: {exc}")


_migrate_sqlite_schema(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
