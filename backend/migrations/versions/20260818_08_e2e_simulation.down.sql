-- Migration: 20260818_08_e2e_simulation.down.sql
-- Reversible Rollback: drops subject_assignments table and removes added columns.

BEGIN;

DROP TABLE IF EXISTS subject_assignments;

ALTER TABLE participants DROP COLUMN IF EXISTS qc_approved;
ALTER TABLE participants DROP COLUMN IF EXISTS visit_count;

ALTER TABLE adjudication_records DROP COLUMN IF EXISTS date_of_diagnosis;
ALTER TABLE committee_decisions DROP COLUMN IF EXISTS date_of_diagnosis;

COMMIT;
