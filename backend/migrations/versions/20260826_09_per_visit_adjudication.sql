-- Migration: 20260826_09_per_visit_adjudication
-- Forward: introduces the subject+visit adjudication unit and re-keys adjudication
-- records and committee decisions onto it.
--
-- Every statement is guarded. init_prod.py runs Base.metadata.create_all() (step 2)
-- BEFORE it replays these files (step 3), so on a production database the model tables
-- -- adjudication_visits, visit_measurement_dates -- already exist by the time this file
-- runs, and the whole set is replayed on every deployment. Bare CREATE TABLE /
-- CREATE INDEX / ADD COLUMN / ADD CONSTRAINT aborts the deploy with
-- 'relation "adjudication_visits" already exists', which is what this file used to do.

BEGIN;

DO $$
BEGIN
    CREATE TYPE diagnosis_code_v2 AS ENUM ('PE', 'SEVERE_PE', 'ECLAMPSIA', 'HELLP', 'OTHER');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS adjudication_visits (
    id UUID PRIMARY KEY,
    participant_id UUID NOT NULL REFERENCES participants(id),
    visit_number INTEGER NOT NULL CHECK (visit_number > 0),
    visit_code VARCHAR(40) NOT NULL,
    visit_date TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_subject_visit_number UNIQUE (participant_id, visit_number),
    CONSTRAINT uq_subject_visit_code UNIQUE (participant_id, visit_code)
);

CREATE INDEX IF NOT EXISTS ix_adjudication_visits_participant_id ON adjudication_visits(participant_id);
CREATE INDEX IF NOT EXISTS ix_adjudication_visits_visit_date ON adjudication_visits(visit_date);

CREATE TABLE IF NOT EXISTS visit_measurement_dates (
    id UUID PRIMARY KEY,
    visit_id UUID NOT NULL REFERENCES adjudication_visits(id) ON DELETE CASCADE,
    measurement_type VARCHAR(50) NOT NULL,
    measured_at TIMESTAMP NOT NULL,
    source_reference VARCHAR(255),
    CONSTRAINT uq_visit_measurement_timestamp UNIQUE (visit_id, measurement_type, measured_at)
);

CREATE INDEX IF NOT EXISTS ix_visit_measurement_dates_sequence
    ON visit_measurement_dates(visit_id, measured_at, measurement_type);

-- When create_all() built adjudication_visits, it built it from the model, which declares
-- status/filing_status/created_at NOT NULL but supplies their defaults in Python only --
-- a SQLAlchemy default= never reaches the database. The backfill below is raw SQL and
-- names none of those columns, so without a real server default it fails with
--   null value in column "status" of relation "adjudication_visits" violates not-null
-- on any database that already holds adjudication records. The CREATE TABLE above and
-- 20260827_12 both give these columns a DEFAULT; assert the same on a table create_all()
-- made, and on one this migration made before those columns existed.
DO $$
DECLARE
    target_column text;
    default_expr  text;
BEGIN
    FOR target_column, default_expr IN
        SELECT * FROM (VALUES ('status', '''IN_REVIEW'''),
                              ('filing_status', '''NOT_READY'''),
                              ('created_at', 'CURRENT_TIMESTAMP')) AS d(c, e)
    LOOP
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'adjudication_visits'
                     AND column_name = target_column) THEN
            EXECUTE format('ALTER TABLE adjudication_visits ALTER COLUMN %I SET DEFAULT %s',
                           target_column, default_expr);
        END IF;
    END LOOP;
END $$;

-- Backfill one durable subject+visit row for every legacy decision visit.
INSERT INTO adjudication_visits (id, participant_id, visit_number, visit_code, visit_date)
SELECT gen_random_uuid(), p.id, n.visit_number, 'V' || LPAD(n.visit_number::text, 2, '0'),
       MIN(n.measurement_date)
FROM participants p
JOIN (
    SELECT participant_id, COALESCE(visit_number, 1) AS visit_number,
           date_of_diagnosis AS measurement_date FROM adjudication_records
    UNION ALL
    SELECT participant_id, COALESCE(visit_number, 1), date_of_diagnosis FROM committee_decisions
) n ON n.participant_id = p.id
GROUP BY p.id, n.visit_number
ON CONFLICT (participant_id, visit_number) DO NOTHING;

ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS visit_id UUID;
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS comment TEXT;
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS other_rationale TEXT;
UPDATE adjudication_records r SET visit_id = v.id
FROM adjudication_visits v
WHERE r.visit_id IS NULL
  AND v.participant_id = r.participant_id AND v.visit_number = COALESCE(r.visit_number, 1);
ALTER TABLE adjudication_records ALTER COLUMN visit_id SET NOT NULL;

DO $$
BEGIN
    ALTER TABLE adjudication_records ADD CONSTRAINT fk_adjudication_record_visit
        FOREIGN KEY (visit_id) REFERENCES adjudication_visits(id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE adjudication_records ADD CONSTRAINT uq_visit_reviewer_role UNIQUE (visit_id, reviewer_role);
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS visit_id UUID;
UPDATE committee_decisions c SET visit_id = v.id
FROM adjudication_visits v
WHERE c.visit_id IS NULL
  AND v.participant_id = c.participant_id AND v.visit_number = COALESCE(c.visit_number, 1);
ALTER TABLE committee_decisions ALTER COLUMN visit_id SET NOT NULL;

DO $$
BEGIN
    ALTER TABLE committee_decisions ADD CONSTRAINT fk_committee_decision_visit
        FOREIGN KEY (visit_id) REFERENCES adjudication_visits(id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE committee_decisions ADD CONSTRAINT uq_committee_decision_visit UNIQUE (visit_id);
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

ALTER TABLE committee_decisions DROP CONSTRAINT IF EXISTS committee_decisions_participant_id_key;

-- The models declare both diagnosis CHECKs, so create_all() may already have built them
-- against the old enum. Their stored 'OTHER'::diagnosiscode literal does not survive the
-- retype below -- Postgres rewrites the column but not the literal, and the constraint
-- then fails to re-parse with 'operator does not exist: diagnosis_code_v2 <> diagnosiscode'.
-- Drop them here and re-add them against the new type once the retype is done.
ALTER TABLE adjudication_records DROP CONSTRAINT IF EXISTS ck_other_reviewer_c_rationale;
ALTER TABLE committee_decisions DROP CONSTRAINT IF EXISTS ck_committee_other_from_reviewer_c;

-- Retype the diagnosis columns onto diagnosis_code_v2. Skipped once already converted,
-- so a redeploy does not pay for a full table rewrite on every run.
DO $do$
BEGIN
    IF (SELECT atttypid FROM pg_attribute
        WHERE attrelid = 'adjudication_records'::regclass AND attname = 'diagnosis')
       <> 'diagnosis_code_v2'::regtype THEN
        EXECUTE $sql$
            ALTER TABLE adjudication_records ALTER COLUMN diagnosis TYPE diagnosis_code_v2
            USING CASE diagnosis::text
                WHEN 'PREECLAMPSIA' THEN 'PE'::diagnosis_code_v2
                WHEN 'PE' THEN 'PE'::diagnosis_code_v2
                WHEN 'SEVERE_PREECLAMPSIA' THEN 'SEVERE_PE'::diagnosis_code_v2
                WHEN 'SEVERE_PE' THEN 'SEVERE_PE'::diagnosis_code_v2
                WHEN 'ECLAMPSIA' THEN 'ECLAMPSIA'::diagnosis_code_v2
                WHEN 'HELLP' THEN 'HELLP'::diagnosis_code_v2
                ELSE diagnosis::text::diagnosis_code_v2
            END
        $sql$;
    END IF;
END
$do$;

DO $do$
BEGIN
    IF (SELECT atttypid FROM pg_attribute
        WHERE attrelid = 'committee_decisions'::regclass AND attname = 'final_diagnosis')
       <> 'diagnosis_code_v2'::regtype THEN
        EXECUTE $sql$
            ALTER TABLE committee_decisions ALTER COLUMN final_diagnosis TYPE diagnosis_code_v2
            USING CASE final_diagnosis::text
                WHEN 'PREECLAMPSIA' THEN 'PE'::diagnosis_code_v2
                WHEN 'PE' THEN 'PE'::diagnosis_code_v2
                WHEN 'SEVERE_PREECLAMPSIA' THEN 'SEVERE_PE'::diagnosis_code_v2
                WHEN 'SEVERE_PE' THEN 'SEVERE_PE'::diagnosis_code_v2
                WHEN 'ECLAMPSIA' THEN 'ECLAMPSIA'::diagnosis_code_v2
                WHEN 'HELLP' THEN 'HELLP'::diagnosis_code_v2
                ELSE final_diagnosis::text::diagnosis_code_v2
            END
        $sql$;
    END IF;
END
$do$;

-- Both were dropped above, so these always apply cleanly against diagnosis_code_v2.
ALTER TABLE adjudication_records ADD CONSTRAINT ck_other_reviewer_c_rationale CHECK (
    diagnosis <> 'OTHER' OR
    (reviewer_role = 'REVIEWER_C' AND other_rationale IS NOT NULL AND length(trim(other_rationale)) > 0)
);

ALTER TABLE committee_decisions ADD CONSTRAINT ck_committee_other_from_reviewer_c CHECK (
    final_diagnosis <> 'OTHER' OR
    (adopted_reviewer = 'REVIEWER_C' AND reviewer_c_rationale IS NOT NULL AND length(trim(reviewer_c_rationale)) > 0)
);

COMMIT;
