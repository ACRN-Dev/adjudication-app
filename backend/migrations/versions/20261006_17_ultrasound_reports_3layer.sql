-- Migration 17: Ultrasound Reports 3-Layer Schema
-- Generated: 2026-10-06
-- Implements Dr. Makadzange & Codex plan:
--   Layer 1: Raw report text & metadata (traceable source evidence)
--   Layer 2: Structured biometric measurements & Doppler observations
--   Layer 3: Controlled clinical prose narrative

CREATE TABLE IF NOT EXISTS ultrasound_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES longitudinal_participants(id) ON DELETE CASCADE,
    visit_id UUID REFERENCES visit_instances(id) ON DELETE SET NULL,
    source_batch_id UUID NOT NULL REFERENCES rt_import_batches(id),

    -- Layer 1: Raw report text & scan metadata
    scan_date TIMESTAMP WITHOUT TIME ZONE,
    gestational_age_weeks DOUBLE PRECISION,
    gestational_age_days INTEGER,
    fetal_number INTEGER DEFAULT 1,
    raw_report_text TEXT,
    sonographer_notes TEXT,
    technical_limitations TEXT,

    -- Layer 2: Normalized structured biometric & clinical observations
    viability VARCHAR(30),
    fetal_heart_rate DOUBLE PRECISION,
    fetal_presentation VARCHAR(50),
    placenta_position VARCHAR(100),
    bpd_mm DOUBLE PRECISION,
    hc_mm DOUBLE PRECISION,
    ac_mm DOUBLE PRECISION,
    fl_mm DOUBLE PRECISION,
    efw_g DOUBLE PRECISION,
    efw_centile DOUBLE PRECISION,
    afi_cm DOUBLE PRECISION,
    dvp_cm DOUBLE PRECISION,
    cervical_length_mm DOUBLE PRECISION,
    ua_doppler_flow VARCHAR(50),
    structural_anomalies TEXT,

    -- Status & quality flags
    documentation_status VARCHAR(40) DEFAULT 'Documented',
    quality_status VARCHAR(40) DEFAULT 'VALID',
    review_flag BOOLEAN DEFAULT FALSE,
    review_note TEXT,

    -- Layer 3: Controlled clinical prose narrative
    generated_narrative TEXT,

    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_us_reports_participant_date
    ON ultrasound_reports (participant_id, scan_date);

CREATE INDEX IF NOT EXISTS ix_us_reports_visit
    ON ultrasound_reports (visit_id)
    WHERE visit_id IS NOT NULL;
