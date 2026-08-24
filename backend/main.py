"""
ACRN PROTECT-Africa Adjudication Platform
FastAPI Backend — Main Application Entry Point

Standards: ICH E6(R2) GCP | 21 CFR Part 11 | EU Annex 11 | GAMP 5
Protocol: PROTECT-Africa (EOPE, A202501 v1.2) & LOPE-Nigeria (ACRN-202503 v1.1)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
            "adjudication_records": {
                "visit_number": "INTEGER DEFAULT 1",
                "date_of_diagnosis": "TIMESTAMP",
            },
            "committee_decisions": {
                "visit_number": "INTEGER DEFAULT 1",
                "date_of_diagnosis": "TIMESTAMP",
                "reviewer_c_upn": "VARCHAR(255)",
                "reviewer_c_name": "VARCHAR(255)",
                "reviewer_c_diagnosis": "VARCHAR(100)",
                "reviewer_c_rationale": "TEXT",
                "concordance_status": "VARCHAR(50) DEFAULT 'DISCORDANT'",
                "meeting_id": "VARCHAR(100)",
                "closed": "BOOLEAN DEFAULT 0",
                "closed_at": "TIMESTAMP",
            },
            "longitudinal_participants": {
                "history_completeness": "FLOAT DEFAULT 0.0",
            },
        }
        with engine.begin() as connection:
            for table_name, columns in compatibility_columns.items():
                existing_columns = {column["name"] for column in inspect(engine).get_columns(table_name)}
                for column_name, definition in columns.items():
                    if column_name not in existing_columns:
                        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))
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

# ── CORS (frontend on localhost:5173 / Next.js on :3000) ───────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://acrn-adjudicate.azurewebsites.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ────────────────────────────────────────────────────────
app.include_router(import_api.router,       prefix="/api/import",       tags=["Data Import"])
app.include_router(mapping.router,          prefix="/api/mappings",     tags=["Field Mapping"])
app.include_router(reconcile.router,        prefix="/api/reconcile",    tags=["Reconciliation"])
app.include_router(derive.router,           prefix="/api/derive",       tags=["Clinical Derivation"])
app.include_router(derive_inline.router,    prefix="/api",              tags=["Inline Derivation"])
app.include_router(narrative.router,        prefix="/api/narrative",    tags=["AI Narrative"])
app.include_router(adjudication.router,     prefix="/api/adjudication", tags=["Adjudication"])
app.include_router(committee.router,        prefix="/api/committee",    tags=["Committee Review"])
app.include_router(chairperson.router,      prefix="/api/chairperson",  tags=["Chairperson Portal"])
app.include_router(audit.router,            prefix="/api/audit",        tags=["Audit Trail"])
app.include_router(assignment.router,       prefix="/api/assignment",   tags=["Assignment"])

app.include_router(export.router,           prefix="/api/export",       tags=["Export"])
app.include_router(auth.router,             prefix="/api/auth",         tags=["Authentication"])
app.include_router(admin.router,            prefix="/api/admin",        tags=["Admin Portal"])
app.include_router(monitor.router,          prefix="/api/monitor",      tags=["Monitor/QC Portal"])
app.include_router(realtime.router, prefix="/api/realtime", tags=["RealTime Longitudinal Database"])
if WORKFLOW_AVAILABLE:
    app.include_router(workflow_api.router, prefix="/api/workflow",     tags=["Workflow Gates"])



import traceback, logging
logger = logging.getLogger("acrn.error")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    err = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Global exception on {request.url.path}:\n{err}")
    return JSONResponse(status_code=500, content={"detail": str(exc), "traceback": err})

@app.get("/health", include_in_schema=False)
def health_check():
    return JSONResponse({
        "status": "ok",
        "service": "ACRN Adjudication API",
        "version": "1.0.0",
        "blinding": "SOP-ADJ-002 active — sFlt-1/PlGF withheld",
    })

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
            return FileResponse(target)
        return FileResponse(os.path.join(dist_path, "index.html"))

