-- Governed access-review snapshots, retention policies, legal holds and
-- dual-controlled disposition evidence.
ALTER TABLE admin_access_reviews ADD COLUMN IF NOT EXISTS snapshot JSONB DEFAULT '[]'::jsonb;
ALTER TABLE admin_access_reviews ADD COLUMN IF NOT EXISTS snapshot_hash VARCHAR(64);
ALTER TABLE admin_access_reviews ADD COLUMN IF NOT EXISTS completed_by VARCHAR(255);
ALTER TABLE admin_access_reviews ADD COLUMN IF NOT EXISTS certification TEXT;
ALTER TABLE admin_access_reviews ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL;

CREATE TABLE IF NOT EXISTS admin_retention_policies (
  id VARCHAR(36) PRIMARY KEY, record_type VARCHAR(80) NOT NULL, version INTEGER NOT NULL,
  retention_days INTEGER NOT NULL CHECK (retention_days >= 1), trigger_event VARCHAR(80) NOT NULL,
  legal_basis TEXT NOT NULL, status VARCHAR(30) NOT NULL, created_by VARCHAR(255) NOT NULL,
  approved_by VARCHAR(255), approved_at TIMESTAMP, reason TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, is_demo BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT uq_retention_policy_version UNIQUE (record_type, version, is_demo)
);
CREATE INDEX IF NOT EXISTS ix_retention_policy_record_type ON admin_retention_policies(record_type);

CREATE TABLE IF NOT EXISTS admin_legal_holds (
  id VARCHAR(36) PRIMARY KEY, name VARCHAR(160) NOT NULL, scope_type VARCHAR(40) NOT NULL,
  scope_value VARCHAR(160) NOT NULL, status VARCHAR(30) NOT NULL, reason TEXT NOT NULL,
  created_by VARCHAR(255) NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  released_by VARCHAR(255), released_at TIMESTAMP, release_reason TEXT,
  is_demo BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_legal_hold_scope_value ON admin_legal_holds(scope_value);

CREATE TABLE IF NOT EXISTS admin_disposition_requests (
  id VARCHAR(36) PRIMARY KEY, record_type VARCHAR(80) NOT NULL, record_reference VARCHAR(160) NOT NULL,
  scope_value VARCHAR(160) NOT NULL, policy_id VARCHAR(36) NOT NULL REFERENCES admin_retention_policies(id),
  eligible_at TIMESTAMP NOT NULL, status VARCHAR(30) NOT NULL, requested_by VARCHAR(255) NOT NULL,
  requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, approved_by VARCHAR(255), approved_at TIMESTAMP,
  executed_by VARCHAR(255), executed_at TIMESTAMP, reason TEXT NOT NULL, evidence JSONB DEFAULT '{}'::jsonb,
  is_demo BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_disposition_record_type ON admin_disposition_requests(record_type);
CREATE INDEX IF NOT EXISTS ix_disposition_scope_value ON admin_disposition_requests(scope_value);
