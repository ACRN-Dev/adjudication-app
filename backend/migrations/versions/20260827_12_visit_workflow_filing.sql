BEGIN;

ALTER TABLE adjudication_visits ADD COLUMN status VARCHAR(40) NOT NULL DEFAULT 'IN_REVIEW';
ALTER TABLE adjudication_visits ADD COLUMN resolution_type VARCHAR(40);
ALTER TABLE adjudication_visits ADD COLUMN final_record_id UUID REFERENCES adjudication_records(id);
ALTER TABLE adjudication_visits ADD COLUMN finalized_at TIMESTAMP;
ALTER TABLE adjudication_visits ADD COLUMN filing_status VARCHAR(30) NOT NULL DEFAULT 'NOT_READY';
ALTER TABLE adjudication_visits ADD COLUMN filing_error TEXT;
CREATE INDEX ix_adjudication_visits_status ON adjudication_visits(status);
CREATE INDEX ix_adjudication_visits_filing_status ON adjudication_visits(filing_status);

ALTER TABLE signed_case_artifacts ALTER COLUMN storage_provider DROP NOT NULL;
ALTER TABLE signed_case_artifacts ALTER COLUMN storage_reference DROP NOT NULL;
ALTER TABLE signed_case_artifacts ALTER COLUMN filed_at DROP NOT NULL;
ALTER TABLE signed_case_artifacts ADD COLUMN filing_status VARCHAR(30) NOT NULL DEFAULT 'PENDING';
ALTER TABLE signed_case_artifacts ADD COLUMN filing_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE signed_case_artifacts ADD COLUMN filing_error TEXT;
CREATE INDEX ix_signed_case_artifacts_filing_status ON signed_case_artifacts(filing_status);

-- Migration guard: do not silently erase an unexpected historical diagnosis.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM adjudication_records WHERE signed = TRUE AND diagnosis IS NULL) THEN
    RAISE EXCEPTION 'Signed adjudication records with NULL diagnosis found; repair legacy diagnosis mapping before release';
  END IF;
END $$;

COMMIT;
