BEGIN;

ALTER TABLE participants ADD COLUMN IF NOT EXISTS qc_approved BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE participants ADD COLUMN IF NOT EXISTS visit_count INTEGER DEFAULT 0;
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS visit_number INTEGER DEFAULT 1;
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS date_of_diagnosis TIMESTAMP;
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS visit_number INTEGER DEFAULT 1;
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS date_of_diagnosis TIMESTAMP;
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS reviewer_c_upn VARCHAR(255);
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS reviewer_c_name VARCHAR(255);
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS reviewer_c_diagnosis VARCHAR(100);
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS reviewer_c_rationale TEXT;
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS concordance_status VARCHAR(50) DEFAULT 'DISCORDANT';
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS meeting_id VARCHAR(100);
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS closed BOOLEAN DEFAULT FALSE;
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP;

COMMIT;