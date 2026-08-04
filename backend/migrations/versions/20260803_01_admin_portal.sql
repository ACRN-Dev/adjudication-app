-- Additive Admin Portal schema. Production deployment must run via Alembic in a controlled change window.
-- The SQLAlchemy definitions in models/admin.py are authoritative for this prototype and create the
-- same tables in standalone SQLite demo mode. No clinical/adjudication table is altered or dropped.
-- Revision: 20260803_01; down migration intentionally omitted to prevent destructive rollback.
CREATE TABLE IF NOT EXISTS admin_schema_migrations (
  revision VARCHAR(40) PRIMARY KEY,
  applied_at TIMESTAMP NOT NULL,
  description TEXT NOT NULL
);
INSERT INTO admin_schema_migrations (revision, applied_at, description)
SELECT '20260803_01', CURRENT_TIMESTAMP, 'Add versioned ACRN Admin Portal domain'
WHERE NOT EXISTS (SELECT 1 FROM admin_schema_migrations WHERE revision='20260803_01');
