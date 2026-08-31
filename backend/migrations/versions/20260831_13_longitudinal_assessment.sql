-- Per-reviewer longitudinal assessment retained with each immutable visit decision.
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS longitudinal_comment TEXT;
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS first_pe_visit_number INTEGER;
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS first_pe_date TIMESTAMP;

ALTER TABLE adjudication_records DROP CONSTRAINT IF EXISTS ck_first_pe_visit_number;
ALTER TABLE adjudication_records ADD CONSTRAINT ck_first_pe_visit_number
    CHECK (first_pe_visit_number IS NULL OR first_pe_visit_number > 0);
