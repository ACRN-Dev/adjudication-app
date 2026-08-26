"""One-shot production database initialiser.

Run inside the application container against the external production Postgres:

    docker compose -f docker-compose.yml -f docker-compose.prod.yml \
        run --rm app python backend/scripts/init_prod.py

Every step is idempotent, so this is safe to re-run on each deployment. Unlike the
application itself, this script never falls back to SQLite: if the production Postgres
is unreachable it aborts, so a misconfigured deployment can never silently initialise
a throwaway local database.

Steps:
  1. Verify the Postgres connection (hard fail).
  2. Create any missing tables from the SQLAlchemy models.
  3. Apply backend/migrations/versions/*.sql in filename order.
  4. Purge synthetic/demo data so no test records exist in production.
  5. Provision the bootstrap ADMIN accounts (SSO-only, no password).
  6. Verify the end state and report.

Pass --dry-run to preview the purge and provisioning without writing anything.
"""
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote_plus

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BACKEND_DIR)
MIGRATIONS_DIR = os.path.join(BACKEND_DIR, "migrations", "versions")
sys.path.insert(0, BACKEND_DIR)

# Accounts that must be able to sign in via Microsoft SSO on a freshly initialised
# production database. They authenticate purely through Entra ID -- no password is set.
# portal_role=ADMIN is the full administrative permission set, which includes
# 'users.manage' so these accounts can provision everyone else through the Admin Portal.
BOOTSTRAP_ADMINS = [
    ("emmanuel.buruvuru@acrnhealth.com", "Emmanuel Buruvuru"),
    ("tinotenda.chibongore@acrnhealth.com", "Tinotenda Chibongore"),
    ("tariro.makadzange@acrnhealth.com", "Tariro Makadzange"),
    ("kudakwashe.takarinda@acrnhealth.com", "Kudakwashe Takarinda"),
]

DRY_RUN = "--dry-run" in sys.argv


def say(message=""):
    print(message, flush=True)


def step(number, title):
    say()
    say(f"[{number}/6] {title}")


def fail(message):
    say()
    say(f"ERROR: {message}")
    sys.exit(1)


DB_NAME = os.getenv("DB_NAME", "")


def postgres_url(database=None):
    """Mirrors backend/database.py so this script targets exactly the same server.

    Pass `database` to reach a different database on that same server -- used to connect to
    the maintenance database when the application database does not exist yet."""
    user = os.getenv("DB_USER", "")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "")
    port = os.getenv("DB_PORT", "5432")
    missing = [k for k in ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME") if not os.getenv(k)]
    if missing:
        fail(f"Missing required database settings: {', '.join(missing)}. Check .env.prod.")
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database or DB_NAME}"


# ── 1. Verify Postgres before importing anything that touches the DB ────────────────
step(1, "Verifying the production Postgres connection")

from sqlalchemy import create_engine, inspect, text  # noqa: E402

ssl_mode = os.getenv("DB_SSL_MODE")
connect_args = {"sslmode": ssl_mode} if ssl_mode else {}


def connect_to_target():
    eng = create_engine(postgres_url(), pool_pre_ping=True, connect_args=connect_args)
    with eng.connect() as conn:
        return eng, conn.execute(text("SHOW server_version")).scalar(), \
            conn.execute(text("SELECT current_database()")).scalar()


def is_missing_database(exc):
    """Postgres reports a non-existent database as SQLSTATE 3D000 (invalid_catalog_name)."""
    if getattr(getattr(exc, "orig", None), "pgcode", None) == "3D000":
        return True
    return f'database "{DB_NAME}" does not exist' in str(exc)


def create_database():
    """Create the application database by connecting to a maintenance database on the
    same server. CREATE DATABASE cannot run inside a transaction, hence AUTOCOMMIT."""
    # The name is interpolated into DDL, so allow only plain identifiers.
    if not DB_NAME or not DB_NAME.replace("_", "").replace("$", "").isalnum() or DB_NAME[0].isdigit():
        fail(f"DB_NAME '{DB_NAME}' is not a plain identifier; refusing to build a CREATE DATABASE "
             "statement from it. Use letters, digits and underscores only.")

    last_error = None
    for maintenance in ("postgres", "template1"):
        try:
            eng = create_engine(postgres_url(maintenance), connect_args=connect_args,
                                isolation_level="AUTOCOMMIT")
            with eng.connect() as conn:
                exists = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": DB_NAME}
                ).scalar()
                if not exists:
                    conn.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
                    say(f"      Created database '{DB_NAME}'.")
                else:
                    say(f"      Database '{DB_NAME}' already exists.")
            eng.dispose()
            return
        except Exception as exc:  # try the next maintenance database
            last_error = exc

    fail(
        f"Database '{DB_NAME}' does not exist and could not be created: {last_error}\n"
        f"       The user '{os.getenv('DB_USER')}' likely lacks the CREATEDB privilege, or cannot\n"
        "       reach the 'postgres'/'template1' maintenance databases. Ask the DBA to run:\n"
        f"           CREATE DATABASE \"{DB_NAME}\" OWNER \"{os.getenv('DB_USER')}\";\n"
        "       then re-run this script."
    )


try:
    engine, server_version, current_db = connect_to_target()
except Exception as exc:
    if not is_missing_database(exc):
        fail(
            f"Cannot reach the production Postgres server: {exc}\n"
            "       Check DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD / DB_SSL_MODE in .env.prod, "
            "and that this server's IP is allowed through the database firewall."
        )
    say(f"      Database '{DB_NAME}' does not exist on {os.getenv('DB_HOST')} -- creating it.")
    if DRY_RUN:
        say("      (dry run: the database would be created here; nothing further can be checked)")
        sys.exit(0)
    create_database()
    try:
        engine, server_version, current_db = connect_to_target()
    except Exception as retry_exc:
        fail(f"Database '{DB_NAME}' was created but is still unreachable: {retry_exc}")

say(f"      Connected to '{current_db}' on {os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')} "
    f"(Postgres {server_version}, sslmode={ssl_mode or 'not set'})")

# Importing the models also imports backend/database.py, which connects to the same
# Postgres. That succeeds here because the check above already passed.
from database import Base  # noqa: E402
from models import admin as admin_models  # noqa: F401,E402
from models import auth as auth_models  # noqa: F401,E402
from models import canonical as canonical_models  # noqa: F401,E402
from models import longitudinal as longitudinal_models  # noqa: F401,E402
from models import monitor as monitor_models  # noqa: F401,E402
from models.auth import AuthAuditEvent, PortalUser  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── 2. Create any missing tables ────────────────────────────────────────────────────
step(2, "Creating any missing tables from the SQLAlchemy models")

before = set(inspect(engine).get_table_names())
Base.metadata.create_all(bind=engine)
created = sorted(set(inspect(engine).get_table_names()) - before)

if created:
    say(f"      Created {len(created)} table(s): {', '.join(created)}")
else:
    say(f"      No new tables needed; {len(before)} already present.")


# ── 3. Apply the SQL migrations ─────────────────────────────────────────────────────
step(3, "Applying SQL migrations")

# Forward migrations only. A *.down.sql file is a rollback script -- applying one here
# would DROP the tables and columns the matching forward migration created, destroying
# their data on every deployment.
all_sql = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
sql_files = [f for f in all_sql if not f.endswith(".down.sql")]
rollbacks = [f for f in all_sql if f.endswith(".down.sql")]

if not sql_files:
    fail(f"No forward migration files found in {MIGRATIONS_DIR}.")

for filename in rollbacks:
    say(f"      skipped  {filename}  (rollback script -- never applied automatically)")

raw = engine.raw_connection()
try:
    raw.autocommit = True
    for filename in sql_files:
        path = os.path.join(MIGRATIONS_DIR, filename)
        with open(path, encoding="utf-8") as handle:
            sql = handle.read()
        cursor = raw.cursor()
        try:
            # Each migration is written to be idempotent (CREATE ... IF NOT EXISTS,
            # ALTER ... IF NOT EXISTS, guarded INSERTs), so replaying them is a no-op.
            cursor.execute(sql)
            say(f"      applied  {filename}")
        except Exception as exc:
            fail(f"Migration {filename} failed: {exc}")
        finally:
            cursor.close()
finally:
    raw.close()

# create_all() only ever CREATES MISSING TABLES -- it never adds a column to a table that
# already exists. So a column added to a model after its table was first created is invisible
# to it, and every query naming that column fails at runtime with UndefinedColumn. Catch that
# here, at deploy time, instead of when a user hits the endpoint.
inspector = inspect(engine)
live_tables = set(inspector.get_table_names())
schema_drift = []
for table in Base.metadata.sorted_tables:
    if table.name not in live_tables:
        continue
    live_columns = {c["name"] for c in inspector.get_columns(table.name)}
    for column in table.columns:
        if column.name not in live_columns:
            ddl = column.type.compile(dialect=engine.dialect)
            schema_drift.append((table.name, column.name, ddl))

if schema_drift:
    say()
    say(f"      {len(schema_drift)} model column(s) missing from the database:")
    for table_name, column_name, ddl in schema_drift:
        say(f'        ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {ddl};')
else:
    say(f"      Schema matches the models across {len(live_tables)} tables.")


# ── 4. Purge synthetic / demo data ──────────────────────────────────────────────────
step(4, "Purging synthetic demo data")

# Tables carrying an is_demo flag are the Admin and Monitor portal fixture domains.
# Clinical tables (canonical, longitudinal) have no such flag and are never touched here.
demo_tables = [t for t in reversed(Base.metadata.sorted_tables) if "is_demo" in t.c]

session = Session()
purged = {}
try:
    for table in demo_tables:
        count = session.execute(
            text(f"SELECT COUNT(*) FROM {table.name} WHERE is_demo IS TRUE")
        ).scalar() or 0
        if count:
            purged[table.name] = count
            if not DRY_RUN:
                session.execute(text(f"DELETE FROM {table.name} WHERE is_demo IS TRUE"))

    demo_accounts = session.query(PortalUser).filter(PortalUser.is_demo_account.is_(True)).all()
    if demo_accounts:
        purged["portal_users"] = len(demo_accounts)
        if not DRY_RUN:
            for row in demo_accounts:
                session.execute(text("DELETE FROM auth_sessions WHERE user_id = :uid"), {"uid": row.id})
                session.delete(row)

    if DRY_RUN:
        session.rollback()
    else:
        session.commit()
except Exception as exc:
    session.rollback()
    fail(f"Demo data purge failed: {exc}")

if purged:
    verb = "would remove" if DRY_RUN else "removed"
    for name, count in sorted(purged.items()):
        say(f"      {verb} {count} row(s) from {name}")
else:
    say(f"      No demo rows found across {len(demo_tables) + 1} candidate tables.")


# ── 5. Provision the bootstrap administrators ───────────────────────────────────────
step(5, "Provisioning bootstrap administrators")

try:
    for email, display_name in BOOTSTRAP_ADMINS:
        normalized = email.strip().lower()
        row = session.query(PortalUser).filter_by(email=normalized).first()

        if row is None:
            if DRY_RUN:
                say(f"      would create  {normalized}  (ADMIN / ADMIN)")
                continue
            row = PortalUser(
                email=normalized,
                display_name=display_name,
                password_hash=None,          # SSO-only: no local password is ever set
                role="ADMIN",
                portal_role="ADMIN",
                study_scope="*",
                status="ACTIVE",
                is_demo_account=False,
                must_change_password=False,
                failed_login_count=0,
            )
            session.add(row)
            session.flush()
            session.add(AuthAuditEvent(
                affected_user_id=row.id,
                affected_email=row.email,
                event_type="BOOTSTRAP_ADMIN_PROVISIONED",
                outcome="SUCCESS",
                reason="Created by backend/scripts/init_prod.py during production initialisation",
                details={"role": "ADMIN", "portal_role": "ADMIN", "authentication": "SSO"},
            ))
            say(f"      created  {normalized}  (ADMIN / ADMIN)")
            continue

        # Already present: repair only what would block an SSO login, leave the rest alone.
        repairs = {}
        if row.role != "ADMIN":
            repairs["role"] = (row.role, "ADMIN")
        if row.portal_role != "ADMIN":
            repairs["portal_role"] = (row.portal_role, "ADMIN")
        if row.status != "ACTIVE":
            repairs["status"] = (row.status, "ACTIVE")
        if row.locked_until is not None:
            repairs["locked_until"] = (str(row.locked_until), None)
        if row.is_demo_account:
            repairs["is_demo_account"] = (True, False)
        if not row.study_scope:
            repairs["study_scope"] = (row.study_scope, "*")

        if not repairs:
            say(f"      ok       {normalized}  (already an active ADMIN)")
            continue

        if DRY_RUN:
            say(f"      would repair  {normalized}: {', '.join(sorted(repairs))}")
            continue

        row.role = "ADMIN"
        row.portal_role = "ADMIN"
        row.status = "ACTIVE"
        row.locked_until = None
        row.failed_login_count = 0
        row.is_demo_account = False
        row.study_scope = row.study_scope or "*"
        session.add(AuthAuditEvent(
            affected_user_id=row.id,
            affected_email=row.email,
            event_type="BOOTSTRAP_ADMIN_REPAIRED",
            outcome="SUCCESS",
            reason="Reconciled by backend/scripts/init_prod.py during production initialisation",
            details={k: {"previous": v[0], "new": v[1]} for k, v in repairs.items()},
        ))
        say(f"      repaired {normalized}: {', '.join(sorted(repairs))}")

    if DRY_RUN:
        session.rollback()
    else:
        session.commit()
except Exception as exc:
    session.rollback()
    fail(f"Bootstrap administrator provisioning failed: {exc}")


# ── 6. Verify the end state ─────────────────────────────────────────────────────────
step(6, "Verifying the initialised database")

active_admins = session.query(PortalUser).filter(
    PortalUser.role == "ADMIN", PortalUser.status == "ACTIVE"
).all()
remaining_demo = sum(
    session.execute(text(f"SELECT COUNT(*) FROM {t.name} WHERE is_demo IS TRUE")).scalar() or 0
    for t in demo_tables
) + session.query(PortalUser).filter(PortalUser.is_demo_account.is_(True)).count()
total_users = session.query(PortalUser).count()
session.close()

say(f"      Portal users:        {total_users}")
say(f"      Active admins:       {len(active_admins)}")
for row in sorted(active_admins, key=lambda r: r.email):
    say(f"        - {row.email} ({row.portal_role or 'no portal_role'})")
say(f"      Demo rows remaining: {remaining_demo}")

if DRY_RUN:
    say()
    say("Dry run complete. Nothing was written. Re-run without --dry-run to apply.")
    sys.exit(0)

problems = []
if schema_drift:
    problems.append(
        f"{len(schema_drift)} model column(s) missing from the database "
        f"({', '.join(f'{t}.{c}' for t, c, _ in schema_drift)}) -- every query touching them "
        "will fail at runtime. Add the ALTER statements printed in step 3 to a new migration "
        "under backend/migrations/versions/ and re-run"
    )
if not active_admins:
    problems.append("no active ADMIN account exists -- nobody would be able to sign in")
if remaining_demo:
    problems.append(f"{remaining_demo} demo row(s) still present")
if os.getenv("ENABLE_DEMO_ACCOUNTS", "false").lower() == "true":
    problems.append("ENABLE_DEMO_ACCOUNTS is true -- demo seeding is active in this environment")

if problems:
    fail("Post-initialisation verification failed:\n       - " + "\n       - ".join(problems))

say()
say("Production database initialised successfully at "
    f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}.")
