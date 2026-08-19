BEGIN;

CREATE TABLE IF NOT EXISTS committee_assignments (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    assignment_type VARCHAR(40) NOT NULL DEFAULT 'CHAIRPERSON',
    committee_name VARCHAR(120),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    assigned_by VARCHAR(36),
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    assignment_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_committee_assignments_user_id
    ON committee_assignments (user_id);
CREATE INDEX IF NOT EXISTS ix_committee_assignments_assignment_type
    ON committee_assignments (assignment_type);
CREATE INDEX IF NOT EXISTS ix_committee_assignments_is_active
    ON committee_assignments (is_active);
CREATE INDEX IF NOT EXISTS ix_committee_assignments_status
    ON committee_assignments (status);
CREATE INDEX IF NOT EXISTS ix_committee_assignments_assigned_at
    ON committee_assignments (assigned_at);
CREATE INDEX IF NOT EXISTS ix_committee_assignments_expires_at
    ON committee_assignments (expires_at);

COMMIT;
