-- Additive Monitor/QC Portal revision. No clinical table is changed or dropped.
CREATE TABLE IF NOT EXISTS monitor_schema_migrations (revision VARCHAR(40) PRIMARY KEY, applied_at TIMESTAMP NOT NULL, description TEXT NOT NULL);
INSERT INTO monitor_schema_migrations SELECT '20260803_02',CURRENT_TIMESTAMP,'Add Monitor/QC operational domain' WHERE NOT EXISTS (SELECT 1 FROM monitor_schema_migrations WHERE revision='20260803_02');
