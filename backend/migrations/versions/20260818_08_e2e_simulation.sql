-- Migration: 20260818_08_e2e_simulation
-- Forward: adds qc_approved to participants and creates subject_assignments table
-- Reversible: see ROLLBACK section at bottom
-- Author: E2E Simulation build (2026-08-18)

BEGIN;

-- 1. Add QC approval gate to participants
ALTER TABLE participants ADD COLUMN IF NOT EXISTS qc_approved BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS ix_participants_qc_approved
    ON participants (qc_approved);

-- 2. Subject assignments (adjudicator pairing with stickiness)
CREATE TABLE IF NOT EXISTS subject_assignments (
    id                  VARCHAR(36) PRIMARY KEY,
    participant_id      UUID        NOT NULL REFERENCES participants (id) ON DELETE CASCADE,
    reviewer_a_upn      VARCHAR(255) NOT NULL,
    reviewer_b_upn      VARCHAR(255) NOT NULL,
    reviewer_c_upn      VARCHAR(255),
    target_cases        INTEGER,
    due_date            TIMESTAMP,
    assigned_by         VARCHAR(255) NOT NULL,
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

COMMIT;

-- ROLLBACK (execute to reverse):
-- BEGIN;
-- DROP TABLE IF EXISTS subject_assignments;
-- ALTER TABLE participants DROP COLUMN IF EXISTS qc_approved;
-- COMMIT;
