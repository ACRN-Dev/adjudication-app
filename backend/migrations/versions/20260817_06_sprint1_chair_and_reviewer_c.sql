BEGIN;

-- Add visit-level & Reviewer C fields to adjudication_records
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS visit_number INTEGER DEFAULT 1;
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS date_of_diagnosis TIMESTAMP;

-- Add visit-level & Reviewer C / consensus fields to committee_decisions
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

-- Create committee_meetings table
CREATE TABLE IF NOT EXISTS committee_meetings (
    id UUID PRIMARY KEY,
    meeting_title VARCHAR(255) NOT NULL,
    batch_id VARCHAR(100),
    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    convened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chair_upn VARCHAR(255) NOT NULL,
    chair_name VARCHAR(255),
    attendees JSONB DEFAULT '[]'::jsonb,
    quorum_met BOOLEAN DEFAULT TRUE,
    minutes TEXT,
    case_ids JSONB DEFAULT '[]'::jsonb,
    signed BOOLEAN DEFAULT FALSE,
    signed_at TIMESTAMP,
    signature_hash VARCHAR(255),
    status VARCHAR(50) DEFAULT 'CLOSED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
