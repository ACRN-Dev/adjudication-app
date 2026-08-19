-- Migration: 20260818_08_e2e_simulation.up.sql
-- Forward: adds qc_approved and visit_count to participants, creates subject_assignments table,
-- and adds date_of_diagnosis support.
-- Compatible with PostgreSQL 14+ and SQLite.

BEGIN;

-- 1. Add QC approval gate and visit_count to participants
ALTER TABLE participants ADD COLUMN IF NOT EXISTS qc_approved BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE participants ADD COLUMN IF NOT EXISTS visit_count INTEGER DEFAULT 1;

CREATE INDEX IF NOT EXISTS ix_participants_qc_approved
    ON participants (qc_approved);

-- 2. Subject assignments (adjudicator pairing with cross-visit stickiness)
CREATE TABLE IF NOT EXISTS subject_assignments (
    id                  VARCHAR(36) PRIMARY KEY,
    participant_id      UUID        NOT NULL REFERENCES participants (id) ON DELETE CASCADE,
    reviewer_a_upn      VARCHAR(255) NOT NULL,
    reviewer_b_upn      VARCHAR(255) NOT NULL,
    reviewer_c_upn      VARCHAR(255),
    target_cases        INTEGER,
    due_date            TIMESTAMP,
    assigned_by         VARCHAR(255) DEFAULT 'monitor@test.acrn',
    assigned_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              VARCHAR(40)  NOT NULL DEFAULT 'ACTIVE',
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_subject_assignment_participant UNIQUE (participant_id)
);

CREATE INDEX IF NOT EXISTS ix_subject_assignments_reviewer_a
    ON subject_assignments (reviewer_a_upn);
CREATE INDEX IF NOT EXISTS ix_subject_assignments_reviewer_b
    ON subject_assignments (reviewer_b_upn);
CREATE INDEX IF NOT EXISTS ix_subject_assignments_status
    ON subject_assignments (status);

-- 3. Ensure date_of_diagnosis exists on adjudication_records and committee_decisions
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS date_of_diagnosis TIMESTAMP;
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS date_of_diagnosis TIMESTAMP;

COMMIT;
