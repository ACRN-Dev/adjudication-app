BEGIN;

CREATE TABLE signed_case_artifacts (
    id UUID PRIMARY KEY,
    participant_id UUID NOT NULL REFERENCES participants(id),
    visit_id UUID NOT NULL UNIQUE REFERENCES adjudication_visits(id),
    determination_record_id UUID NOT NULL REFERENCES adjudication_records(id),
    pdf_sha256 VARCHAR(64) NOT NULL,
    storage_provider VARCHAR(30) NOT NULL,
    storage_reference VARCHAR(1000) NOT NULL,
    filed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_signed_case_artifacts_participant_id ON signed_case_artifacts(participant_id);

CREATE TABLE adjudicator_profiles (
    id VARCHAR(36) PRIMARY KEY,
    adjudicator_upn VARCHAR(255) NOT NULL UNIQUE,
    contract_signed_at TIMESTAMP,
    billing_status VARCHAR(30) NOT NULL DEFAULT 'NOT_READY',
    billing_note TEXT,
    updated_by VARCHAR(255),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_adjudicator_profiles_upn ON adjudicator_profiles(adjudicator_upn);
CREATE INDEX ix_adjudicator_profiles_billing ON adjudicator_profiles(billing_status);

ALTER TABLE committee_meetings ADD COLUMN delegated_to_upn VARCHAR(255);
ALTER TABLE committee_meetings ADD COLUMN delegated_by_upn VARCHAR(255);
ALTER TABLE committee_meetings ADD COLUMN delegation_note TEXT;
ALTER TABLE committee_meetings ADD COLUMN delegated_at TIMESTAMP;

COMMIT;
