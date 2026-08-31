-- Migration: 20260826_11_adjudicator_activity_billing
-- Forward: adjudicator contracts, committee memberships, the activity ledger, and billing.
--
-- Guarded throughout: init_prod.py creates the model tables via create_all() before it
-- replays these files, and replays the whole set on every deployment.

BEGIN;

CREATE TABLE IF NOT EXISTS adjudicator_study_contracts (
    id VARCHAR(36) PRIMARY KEY, adjudicator_upn VARCHAR(255) NOT NULL, study_code VARCHAR(80) NOT NULL,
    contract_signed_at TIMESTAMP NOT NULL, contract_reference VARCHAR(255) NOT NULL,
    terms_of_reference_url VARCHAR(1000), effective_from TIMESTAMP NOT NULL, effective_to TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE', changed_by VARCHAR(255), created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_adjudicator_study_contract UNIQUE(adjudicator_upn, study_code, effective_from)
);
CREATE INDEX IF NOT EXISTS ix_adjudicator_study_contracts_upn ON adjudicator_study_contracts(adjudicator_upn);
CREATE TABLE IF NOT EXISTS adjudicator_committee_memberships (
    id VARCHAR(36) PRIMARY KEY, adjudicator_upn VARCHAR(255) NOT NULL, committee_name VARCHAR(160) NOT NULL,
    membership_role VARCHAR(30) NOT NULL DEFAULT 'MEMBER', effective_from TIMESTAMP NOT NULL,
    effective_to TIMESTAMP, status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE', changed_by VARCHAR(255), created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS adjudication_activity_ledger (
    id VARCHAR(36) PRIMARY KEY, adjudicator_upn VARCHAR(255) NOT NULL, study_code VARCHAR(80) NOT NULL,
    blinded_case_reference VARCHAR(100) NOT NULL, subject_visit_id VARCHAR(36), role_served VARCHAR(30) NOT NULL,
    event_type VARCHAR(50) NOT NULL, event_at TIMESTAMP NOT NULL, billable BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(30) NOT NULL DEFAULT 'RECORDED', source_record_id VARCHAR(36), idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    metadata_json JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_activity_event UNIQUE(adjudicator_upn, blinded_case_reference, role_served, event_type)
);
CREATE INDEX IF NOT EXISTS ix_activity_ledger_upn_date ON adjudication_activity_ledger(adjudicator_upn, event_at);
CREATE TABLE IF NOT EXISTS billing_rate_cards (
    id VARCHAR(36) PRIMARY KEY, study_code VARCHAR(80) NOT NULL, role_served VARCHAR(30) NOT NULL,
    event_type VARCHAR(50) NOT NULL, currency CHAR(3) NOT NULL DEFAULT 'USD', rate_amount INTEGER NOT NULL CHECK(rate_amount >= 0),
    effective_from TIMESTAMP NOT NULL, effective_to TIMESTAMP, status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE', approved_by VARCHAR(255), created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS billing_periods (
    id VARCHAR(36) PRIMARY KEY, period_code VARCHAR(40) NOT NULL UNIQUE, starts_at TIMESTAMP NOT NULL, ends_at TIMESTAMP NOT NULL,
    due_at TIMESTAMP, status VARCHAR(30) NOT NULL DEFAULT 'OPEN', created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(ends_at > starts_at)
);
CREATE TABLE IF NOT EXISTS billing_payments (
    id VARCHAR(36) PRIMARY KEY, adjudicator_upn VARCHAR(255) NOT NULL, billing_period_id VARCHAR(36) NOT NULL REFERENCES billing_periods(id),
    amount_minor INTEGER NOT NULL CHECK(amount_minor >= 0), currency CHAR(3) NOT NULL DEFAULT 'USD', paid_at TIMESTAMP,
    payment_reference VARCHAR(255), status VARCHAR(30) NOT NULL DEFAULT 'OUTSTANDING', recorded_by VARCHAR(255), created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE committee_meetings ADD COLUMN IF NOT EXISTS delegated_to_upn VARCHAR(255);
ALTER TABLE committee_meetings ADD COLUMN IF NOT EXISTS delegated_by_upn VARCHAR(255);
ALTER TABLE committee_meetings ADD COLUMN IF NOT EXISTS delegation_note TEXT;
ALTER TABLE committee_meetings ADD COLUMN IF NOT EXISTS delegated_at TIMESTAMP;
COMMIT;
