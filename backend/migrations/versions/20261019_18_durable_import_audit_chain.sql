-- Durable import queue and tamper-evident audit chain.
CREATE TABLE IF NOT EXISTS rt_import_jobs (
    id UUID PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES rt_import_batches(id),
    operation VARCHAR(30) NOT NULL DEFAULT 'PROCESS',
    status VARCHAR(30) NOT NULL DEFAULT 'QUEUED',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    queued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    lease_owner VARCHAR(100),
    lease_expires_at TIMESTAMP,
    last_heartbeat_at TIMESTAMP,
    error_summary TEXT
);
CREATE INDEX IF NOT EXISTS ix_rt_import_jobs_batch_id ON rt_import_jobs(batch_id);
CREATE INDEX IF NOT EXISTS ix_rt_import_jobs_status ON rt_import_jobs(status);
CREATE INDEX IF NOT EXISTS ix_rt_import_jobs_lease_expires_at ON rt_import_jobs(lease_expires_at);

ALTER TABLE longitudinal_audit_events ADD COLUMN IF NOT EXISTS previous_hash VARCHAR(64);
ALTER TABLE longitudinal_audit_events ADD COLUMN IF NOT EXISTS chain_sequence INTEGER;
ALTER TABLE longitudinal_audit_events ADD COLUMN IF NOT EXISTS integrity_version VARCHAR(20);

-- Preserve historical records as explicit legacy anchors. New records use SHA256-CHAIN-1.
WITH ordered AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY timestamp, id) AS sequence
    FROM longitudinal_audit_events
)
UPDATE longitudinal_audit_events e
SET chain_sequence = ordered.sequence,
    integrity_version = COALESCE(e.integrity_version, 'LEGACY-UNCHAINED')
FROM ordered WHERE e.id = ordered.id AND e.chain_sequence IS NULL;

ALTER TABLE longitudinal_audit_events ALTER COLUMN chain_sequence SET NOT NULL;
ALTER TABLE longitudinal_audit_events ALTER COLUMN integrity_version SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_longitudinal_audit_chain_sequence ON longitudinal_audit_events(chain_sequence);

CREATE TABLE IF NOT EXISTS clinical_data_queries (
    id UUID PRIMARY KEY,
    participant_id UUID NOT NULL REFERENCES longitudinal_participants(id),
    visit_id UUID REFERENCES visit_instances(id),
    category VARCHAR(60) NOT NULL,
    query_text TEXT NOT NULL,
    raised_by VARCHAR(255) NOT NULL,
    raised_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    response_text TEXT,
    responded_by VARCHAR(255),
    responded_at TIMESTAMP,
    closed_by VARCHAR(255),
    closed_at TIMESTAMP,
    closure_reason TEXT
);
CREATE INDEX IF NOT EXISTS ix_clinical_data_queries_participant_id ON clinical_data_queries(participant_id);
CREATE INDEX IF NOT EXISTS ix_clinical_data_queries_status ON clinical_data_queries(status);

CREATE TABLE IF NOT EXISTS reviewer_recusals (
    id UUID PRIMARY KEY,
    participant_id UUID NOT NULL REFERENCES longitudinal_participants(id),
    assignment_id UUID NOT NULL REFERENCES reviewer_assignments(id),
    reviewer_upn VARCHAR(255) NOT NULL,
    reviewer_role VARCHAR(20) NOT NULL,
    reason_code VARCHAR(50) NOT NULL,
    comments TEXT NOT NULL,
    declared_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    replacement_upn VARCHAR(255),
    replacement_assigned_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_reviewer_recusals_participant_id ON reviewer_recusals(participant_id);
CREATE INDEX IF NOT EXISTS ix_reviewer_recusals_reviewer_upn ON reviewer_recusals(reviewer_upn);

ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS authentication_method VARCHAR(30) NOT NULL DEFAULT 'PASSWORD';
ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS mfa_verified_at TIMESTAMP;
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS signature_payload JSONB;
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS signature_meaning VARCHAR(255);
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS authentication_method VARCHAR(30);
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS authentication_session_id VARCHAR(36);

CREATE TABLE IF NOT EXISTS observation_corrections (
    id UUID PRIMARY KEY,
    participant_id UUID NOT NULL REFERENCES longitudinal_participants(id),
    original_observation_id UUID NOT NULL REFERENCES canonical_observations(id),
    replacement_observation_id UUID REFERENCES canonical_observations(id),
    proposed_values JSONB NOT NULL,
    request_reason TEXT NOT NULL,
    requested_by VARCHAR(255) NOT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING_APPROVAL',
    approval_reason TEXT,
    approved_by VARCHAR(255),
    approved_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_observation_corrections_participant_id ON observation_corrections(participant_id);
CREATE INDEX IF NOT EXISTS ix_observation_corrections_original_observation_id ON observation_corrections(original_observation_id);
CREATE INDEX IF NOT EXISTS ix_observation_corrections_status ON observation_corrections(status);
ALTER TABLE canonical_observations ADD COLUMN IF NOT EXISTS supersedes_observation_id UUID REFERENCES canonical_observations(id);
ALTER TABLE canonical_observations ADD COLUMN IF NOT EXISTS correction_id UUID REFERENCES observation_corrections(id);
CREATE INDEX IF NOT EXISTS ix_canonical_observations_supersedes_observation_id ON canonical_observations(supersedes_observation_id);
CREATE INDEX IF NOT EXISTS ix_canonical_observations_correction_id ON canonical_observations(correction_id);

ALTER TABLE signed_case_artifacts ADD COLUMN IF NOT EXISTS filing_verified_at TIMESTAMP;
ALTER TABLE signed_case_artifacts ADD COLUMN IF NOT EXISTS manifest_sha256 VARCHAR(64);
ALTER TABLE signed_case_artifacts ADD COLUMN IF NOT EXISTS filing_receipt JSONB;

ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS signature_payload JSONB;
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS authentication_method VARCHAR(30);
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS authentication_session_id VARCHAR(36);
ALTER TABLE committee_meetings ADD COLUMN IF NOT EXISTS signature_payload JSONB;
ALTER TABLE committee_meetings ADD COLUMN IF NOT EXISTS authentication_method VARCHAR(30);
ALTER TABLE committee_meetings ADD COLUMN IF NOT EXISTS authentication_session_id VARCHAR(36);
ALTER TABLE committee_meetings ADD COLUMN IF NOT EXISTS report_sha256 VARCHAR(64);
ALTER TABLE committee_meetings ADD COLUMN IF NOT EXISTS filing_verified_at TIMESTAMP;
ALTER TABLE committee_meetings ADD COLUMN IF NOT EXISTS filing_receipt JSONB;

CREATE TABLE IF NOT EXISTS api_rate_limit_buckets (
    id VARCHAR(36) PRIMARY KEY,
    subject_hash VARCHAR(64) NOT NULL,
    action VARCHAR(40) NOT NULL,
    window_started_at TIMESTAMP NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMP NOT NULL,
    CONSTRAINT uq_api_rate_limit_window UNIQUE (subject_hash, action, window_started_at)
);
CREATE INDEX IF NOT EXISTS ix_api_rate_limit_buckets_expires_at ON api_rate_limit_buckets(expires_at);
