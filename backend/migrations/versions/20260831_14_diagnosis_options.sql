-- Extend diagnosis and onset enums for explicit negative and postpartum outcomes.
-- Required by reviewer submission and Chairperson concordance views.
ALTER TABLE adjudication_records
    ADD COLUMN IF NOT EXISTS differential_diagnosis VARCHAR(500);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'diagnosis_code_v2') THEN
        ALTER TYPE diagnosis_code_v2 ADD VALUE IF NOT EXISTS 'NOT_PE';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'onsetclass') THEN
        ALTER TYPE onsetclass ADD VALUE IF NOT EXISTS 'POSTPARTUM';
        ALTER TYPE onsetclass ADD VALUE IF NOT EXISTS 'UNCLASSIFIABLE';
    END IF;
END $$;
