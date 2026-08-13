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


def postgres_url():
    """Mirrors backend/database.py so this script targets exactly the same server."""
    user = os.getenv("DB_USER", "")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "")
    missing = [k for k in ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME") if not os.getenv(k)]
    if missing:
        fail(f"Missing required database settings: {', '.join(missing)}. Check .env.prod.")
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{name}"


# ── 1. Verify Postgres before importing anything that touches the DB ────────────────
step(1, "Verifying the production Postgres connection")

from sqlalchemy import create_engine, inspect, text  # noqa: E402

ssl_mode = os.getenv("DB_SSL_MODE")
connect_args = {"sslmode": ssl_mode} if ssl_mode else {}
engine = create_engine(postgres_url(), pool_pre_ping=True, connect_args=connect_args)

try:
    with engine.connect() as conn:
        server_version = conn.execute(text("SHOW server_version")).scalar()
        current_db = conn.execute(text("SELECT current_database()")).scalar()
except Exception as exc:
    fail(
        f"Cannot reach the production Postgres server: {exc}\n"
        "       Check DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD / DB_SSL_MODE in .env.prod, "
        "and that this server's IP is allowed through the database firewall."
    )

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

sql_files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
if not sql_files:
    fail(f"No migration files found in {MIGRATIONS_DIR}.")

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
