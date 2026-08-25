-- Migration: 20260825_09_history_completeness
-- Forward: adds longitudinal_participants.history_completeness on PostgreSQL.
--
-- models/longitudinal.py has carried this column since the patient-history work, and
-- api/realtime.py selects it on every participant query, but no migration added it to
-- Postgres. main.py does add it, inside a block guarded by `if DB_OFFLINE:` -- so it only
-- ever ran against the SQLite fallback, never against a real database. On production the
-- column was therefore absent and the RealTime pipeline failed with:
--
--   (psycopg2.errors.UndefinedColumn) column longitudinal_participants.history_completeness
--   does not exist
--
-- Additive and idempotent. No existing data is read or modified; new rows default to 0.0
-- until the history parser recalculates them.

BEGIN;

ALTER TABLE longitudinal_participants
    ADD COLUMN IF NOT EXISTS history_completeness DOUBLE PRECISION DEFAULT 0.0;

COMMIT;
