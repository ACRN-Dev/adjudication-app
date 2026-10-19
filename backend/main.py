"""
ACRN PROTECT-Africa Adjudication Platform
FastAPI Backend — Main Application Entry Point

Standards: ICH E6(R2) GCP | 21 CFR Part 11 | EU Annex 11 | GAMP 5
Protocol: PROTECT-Africa (EOPE, A202501 v1.2) & LOPE-Nigeria (ACRN-202503 v1.1)
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from urllib.parse import urlsplit
import hashlib
import hmac
import json
import logging
import os
import time
import uuid

from api import import_api, mapping, reconcile, derive, narrative, adjudication, committee, chairperson, audit, export, derive_inline, admin, monitor, realtime, auth, assignment
from models import canonical, longitudinal, auth as auth_models, history as history_models
from services.auth_service import maybe_seed_demo_accounts
try:
    from api import workflow as workflow_api
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False
from database import engine, Base, DB_OFFLINE
from sqlalchemy import inspect, text
from services.runtime_policy import is_production, legacy_unsafe_routes_enabled, validate_runtime_environment
from services.import_jobs import dispatch_pending_jobs
from services.operational_controls import matching_policy, rate_limits_enabled, request_subject, consume_rate_limit, metrics

# Production must never continue on the demo SQLite fallback or with prototype
# bypass features enabled. Validate before startup creates or seeds any tables.
validate_runtime_environment(database_is_fallback=DB_OFFLINE)

# ── Create all database tables on startup (graceful if DB offline) ──────────
try:
    Base.metadata.create_all(bind=engine)
    if DB_OFFLINE:
        inspector = inspect(engine)
        compatibility_columns = {
            "participants": {
                "qc_approved": "BOOLEAN NOT NULL DEFAULT 0",
                "visit_count": "INTEGER DEFAULT 0",
            },
            "adjudication_visits": {
                "status": "VARCHAR(40) NOT NULL DEFAULT 'IN_REVIEW'",
                "resolution_type": "VARCHAR(40)",
                "final_record_id": "VARCHAR(36)",
                "finalized_at": "TIMESTAMP",
                "filing_status": "VARCHAR(30) NOT NULL DEFAULT 'NOT_READY'",
                "filing_error": "TEXT",
            },
            "adjudication_records": {
                "visit_id": "VARCHAR(36)",
                "visit_number": "INTEGER DEFAULT 1",
                "date_of_diagnosis": "TIMESTAMP",
                "comment": "TEXT",
                "longitudinal_comment": "TEXT",
                "first_pe_visit_number": "INTEGER",
                "first_pe_date": "TIMESTAMP",
                "other_rationale": "TEXT",
                "differential_diagnosis": "VARCHAR(500)",
                "signature_payload": "JSON",
                "signature_meaning": "VARCHAR(255)",
                "authentication_method": "VARCHAR(30)",
                "authentication_session_id": "VARCHAR(36)",
            },
            "signed_case_artifacts": {
                "filing_status": "VARCHAR(30) NOT NULL DEFAULT 'PENDING'",
                "filing_attempts": "INTEGER NOT NULL DEFAULT 0",
                "filing_error": "TEXT",
                "filing_verified_at": "TIMESTAMP",
                "manifest_sha256": "VARCHAR(64)",
                "filing_receipt": "JSON",
            },
            "committee_decisions": {
                "visit_id": "VARCHAR(36)",
                "visit_number": "INTEGER DEFAULT 1",
                "date_of_diagnosis": "TIMESTAMP",
                "reviewer_c_upn": "VARCHAR(255)",
                "reviewer_c_name": "VARCHAR(255)",
                "reviewer_c_diagnosis": "VARCHAR(100)",
                "reviewer_c_diagnosis": "VARCHAR(100)",
                "reviewer_c_rationale": "TEXT",
                "concordance_status": "VARCHAR(50) DEFAULT 'DISCORDANT'",
                "meeting_id": "VARCHAR(100)",
                "closed": "BOOLEAN DEFAULT 0",
                "closed_at": "TIMESTAMP",
                "signature_payload": "JSON",
                "authentication_method": "VARCHAR(30)",
                "authentication_session_id": "VARCHAR(36)",
            },
            "committee_meetings": {
                "signature_payload": "JSON",
                "authentication_method": "VARCHAR(30)",
                "authentication_session_id": "VARCHAR(36)",
                "report_sha256": "VARCHAR(64)",
                "filing_verified_at": "TIMESTAMP",
                "filing_receipt": "JSON",
            },
            "longitudinal_participants": {
                "history_completeness": "FLOAT DEFAULT 0.0",
            },
            "longitudinal_audit_events": {
                "previous_hash": "VARCHAR(64)",
                "chain_sequence": "INTEGER NOT NULL DEFAULT 1",
                "integrity_version": "VARCHAR(20) NOT NULL DEFAULT 'LEGACY-UNCHAINED'",
            },
            "portal_users": {
                "contract_valid": "BOOLEAN NOT NULL DEFAULT 1",
                "contract_period": "VARCHAR(100) DEFAULT '1 Year (Active)'",
            },
            "auth_sessions": {
                "authentication_method": "VARCHAR(30) NOT NULL DEFAULT 'PASSWORD'",
                "mfa_verified_at": "TIMESTAMP",
            },
            "admin_access_reviews": {
                "snapshot": "JSON",
                "snapshot_hash": "VARCHAR(64)",
                "completed_by": "VARCHAR(255)",
                "certification": "TEXT",
                "created_at": "TIMESTAMP",
            },
            "canonical_observations": {
                "supersedes_observation_id": "VARCHAR(36)",
                "correction_id": "VARCHAR(36)",
            },
        }
        with engine.begin() as connection:
            for table_name, columns in compatibility_columns.items():
                existing_columns = {column["name"] for column in inspect(engine).get_columns(table_name)}
                for column_name, definition in columns.items():
                    if column_name not in existing_columns:
                        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))
            # Legacy demo rows may contain historical enum labels. SQLAlchemy
            # validates enum names when reading records, so normalize old labels
            # before adjudication queries load them.
            connection.execute(text(
                "UPDATE adjudication_records "
                "SET diagnosis = CASE diagnosis "
                "WHEN 'PREECLAMPSIA' THEN 'PE' "
                "WHEN 'SEVERE_PREECLAMPSIA' THEN 'SEVERE_PE' "
                "WHEN 'Severe PE' THEN 'SEVERE_PE' "
                "WHEN 'Eclampsia' THEN 'ECLAMPSIA' "
                "WHEN 'Other' THEN 'OTHER' "
                "ELSE diagnosis END "
                "WHERE diagnosis IN ('PREECLAMPSIA', 'SEVERE_PREECLAMPSIA', 'Severe PE', 'Eclampsia', 'Other')"
            ))
            connection.execute(text(
                "UPDATE committee_decisions "
                "SET final_diagnosis = CASE final_diagnosis "
                "WHEN 'PREECLAMPSIA' THEN 'PE' "
                "WHEN 'SEVERE_PREECLAMPSIA' THEN 'SEVERE_PE' "
                "WHEN 'Severe PE' THEN 'SEVERE_PE' "
                "WHEN 'Eclampsia' THEN 'ECLAMPSIA' "
                "WHEN 'Other' THEN 'OTHER' "
                "ELSE final_diagnosis END "
                "WHERE final_diagnosis IN ('PREECLAMPSIA', 'SEVERE_PREECLAMPSIA', 'Severe PE', 'Eclampsia', 'Other')"
            ))
    from database import SessionLocal
    db = SessionLocal()
    try:
        maybe_seed_demo_accounts(db)
    finally:
        db.close()
except Exception as e:
    import logging
    logging.getLogger('acrn').warning(f'Table creation skipped (DB offline): {e}')

app = FastAPI(
    title="ACRN Adjudication API",
    description=(
        "Backend for the PROTECT-Africa & LOPE-Nigeria Independent OAC "
        "Endpoint Adjudication Platform. All endpoints require authentication. "
        "Biomarker outputs (sFlt-1/PlGF, sEng, POC) are programmatically withheld "
        "per SOP-ADJ-002."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS (frontend on localhost:5173 / Next.js on :3000 / deployed origin) ─
import os as _os

_extra_origins = [
    o.strip() for o in _os.getenv("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()
]
_cors_origins = [
    "https://acrn-adjudicate.azurewebsites.net",
    "https://adjudication.acrncloud.com",
] + _extra_origins
if not is_production():
    _cors_origins += ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def recover_durable_import_jobs():
    dispatch_pending_jobs()


@app.middleware("http")
async def browser_security_headers(request, call_next):
    state_changing = request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
    has_session_cookie = bool(request.cookies.get("acrn_demo_session"))
    if is_production() and state_changing and has_session_cookie:
        origin = request.headers.get("origin", "")
        expected = urlsplit(_os.getenv("APP_BASE_URL", ""))
        supplied = urlsplit(origin)
        same_origin = (
            supplied.scheme == expected.scheme
            and supplied.netloc == expected.netloc
            and supplied.scheme == "https"
        )
        if not same_origin:
            response = JSONResponse(
                status_code=403,
                content={"detail": "Cross-site state-changing request denied."},
            )
        else:
            response = await call_next(request)
    else:
        response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; object-src 'none'; "
        "script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "font-src 'self' data:; connect-src 'self'",
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("Pragma", "no-cache")
    if is_production():
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


request_logger = logging.getLogger("acrn.request")


@app.middleware("http")
async def operational_request_controls(request: Request, call_next):
    """Attach correlation IDs, enforce shared limits, and publish bounded metrics."""
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    started = time.perf_counter()
    metrics.start()
    response = None
    policy = matching_policy(request.method.upper(), request.url.path) if rate_limits_enabled() else None
    if policy:
        from database import SessionLocal
        action, limit, window_seconds = policy
        rate_db = SessionLocal()
        try:
            allowed, retry_after, observed = consume_rate_limit(
                rate_db, subject_hash=request_subject(request), action=action,
                limit=limit, window_seconds=window_seconds,
            )
            if not allowed:
                metrics.limited(action)
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Request rate limit exceeded.", "correlation_id": correlation_id},
                    headers={"Retry-After": str(retry_after)},
                )
        except Exception:
            rate_db.rollback()
            if is_production():
                response = JSONResponse(
                    status_code=503,
                    content={"detail": "Request-control service unavailable.", "correlation_id": correlation_id},
                )
        finally:
            rate_db.close()
    if response is None:
        response = await call_next(request)
    duration = time.perf_counter() - started
    route = getattr(request.scope.get("route"), "path", None) or request.url.path
    metrics.finish(request.method.upper(), route, response.status_code, duration)
    response.headers["X-Correlation-ID"] = correlation_id
    request_logger.info(json.dumps({
        "event": "http_request", "correlation_id": correlation_id,
        "method": request.method.upper(), "route": route,
        "status": response.status_code, "duration_ms": round(duration * 1000, 2),
    }, separators=(",", ":")))
    return response

# ── Register routers ────────────────────────────────────────────────────────
LEGACY_UNSAFE_ROUTES_ENABLED = legacy_unsafe_routes_enabled()
if LEGACY_UNSAFE_ROUTES_ENABLED:
    app.include_router(import_api.router,       prefix="/api/import",       tags=["Data Import"])
    app.include_router(mapping.router,          prefix="/api/mappings",     tags=["Field Mapping"])
    app.include_router(reconcile.router,        prefix="/api/reconcile",    tags=["Reconciliation"])
    app.include_router(derive.router,           prefix="/api/derive",       tags=["Clinical Derivation"])
    app.include_router(derive_inline.router,    prefix="/api",              tags=["Inline Derivation"])
    app.include_router(narrative.router,        prefix="/api/narrative",    tags=["AI Narrative"])
    app.include_router(committee.router,        prefix="/api/committee",    tags=["Committee Review"])
    app.include_router(audit.router,            prefix="/api/audit",        tags=["Audit Trail"])
app.include_router(chairperson.router,      prefix="/api/chairperson",  tags=["Chairperson Portal"])
app.include_router(assignment.router,       prefix="/api/assignment",   tags=["Assignment"])
app.include_router(adjudication.router,     prefix="/api/adjudication", tags=["Adjudication"])

app.include_router(export.router,           prefix="/api/export",       tags=["Export"])
app.include_router(auth.router,             prefix="/api/auth",         tags=["Authentication"])
app.include_router(admin.router,            prefix="/api/admin",        tags=["Admin Portal"])
app.include_router(monitor.router,          prefix="/api/monitor",      tags=["Monitor/QC Portal"])
app.include_router(realtime.router, prefix="/api/realtime", tags=["RealTime Longitudinal Database"])
if WORKFLOW_AVAILABLE and LEGACY_UNSAFE_ROUTES_ENABLED:
    app.include_router(workflow_api.router, prefix="/api/workflow",     tags=["Workflow Gates"])



import logging
import uuid
logger = logging.getLogger("acrn.error")

from fastapi.exceptions import RequestValidationError
from services.auth_service import SENSITIVE_KEYS

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    # FastAPI's default handler echoes back the raw submitted value for invalid fields.
    # Redact credential fields (password, reviewer_password, etc.) so they never leak
    # into API responses, browser devtools or access logs.
    safe_errors = []
    for err in exc.errors():
        err = dict(err)
        loc = err.get("loc") or ()
        if any(str(part).lower() in SENSITIVE_KEYS for part in loc):
            err["input"] = "***REDACTED***"
        safe_errors.append(err)
    return JSONResponse(status_code=422, content={"detail": safe_errors})

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    correlation_id = str(uuid.uuid4())
    logger.exception(
        "Unhandled API exception correlation_id=%s path=%s",
        correlation_id,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "correlation_id": correlation_id,
        },
    )

@app.get("/health", include_in_schema=False)
@app.get("/health/live", include_in_schema=False)
def health_check():
    return JSONResponse({
        "status": "ok",
        "service": "ACRN Adjudication API",
        "version": "1.0.0",
        "blinding": "SOP-ADJ-002 active — sFlt-1/PlGF withheld",
    })


@app.get("/metrics", include_in_schema=False)
def service_metrics(request: Request):
    expected = os.getenv("METRICS_BEARER_TOKEN", "")
    supplied = request.headers.get("authorization", "")
    authorized = supplied.startswith("Bearer ") and expected and hmac.compare_digest(supplied[7:], expected)
    if is_production() and not authorized:
        return JSONResponse(status_code=401, content={"detail": "Metrics authentication required."})
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")


@app.get("/health/ready", include_in_schema=False)
def readiness_check():
    """Fail closed when durable storage or integrity controls are unavailable."""
    from datetime import datetime
    from database import SessionLocal
    from models.longitudinal import RTImportJob
    from services.realtime_pipeline import verify_audit_chain

    db = SessionLocal()
    checks = {"database": False, "audit_chain": False, "abandoned_import_jobs": 0}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
        checks["audit_chain"] = verify_audit_chain(db)
        checks["abandoned_import_jobs"] = db.query(RTImportJob).filter(
            RTImportJob.status == "RUNNING",
            RTImportJob.lease_expires_at < datetime.utcnow(),
        ).count()
        ready = checks["database"] and checks["audit_chain"] and checks["abandoned_import_jobs"] == 0
        return JSONResponse(status_code=200 if ready else 503, content={"status":"ready" if ready else "not_ready","checks":checks})
    except Exception:
        return JSONResponse(status_code=503, content={"status":"not_ready","checks":checks})
    finally:
        db.close()

# ── Serve Compiled Frontend Static Assets (Production Cloud Hosting) ───────
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException

# Resolve dist/ relative to the repo root regardless of --app-dir or CWD
_here = os.path.dirname(os.path.abspath(__file__))  # .../backend
dist_path = os.path.join(os.path.dirname(_here), "dist")
if os.path.exists(dist_path):
    assets_path = os.path.join(dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        target = os.path.join(dist_path, full_path)
        if full_path and os.path.exists(target) and os.path.isfile(target):
            if target.endswith(".html"):
                return FileResponse(target, headers={"Cache-Control": "no-cache"})
            return FileResponse(target)
        return FileResponse(
            os.path.join(dist_path, "index.html"),
            headers={"Cache-Control": "no-cache"},
        )
