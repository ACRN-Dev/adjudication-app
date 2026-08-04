-- Additive RealTime longitudinal revision. Existing data is never reset or dropped.
CREATE TABLE IF NOT EXISTS realtime_schema_migrations(revision VARCHAR(40) PRIMARY KEY,applied_at TIMESTAMP NOT NULL,description TEXT NOT NULL);
INSERT INTO realtime_schema_migrations SELECT '20260804_03',CURRENT_TIMESTAMP,'RealTime longitudinal import domain' WHERE NOT EXISTS(SELECT 1 FROM realtime_schema_migrations WHERE revision='20260804_03');
