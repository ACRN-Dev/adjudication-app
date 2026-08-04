CREATE TABLE IF NOT EXISTS portal_users (
  id VARCHAR(36) PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  display_name VARCHAR(160) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(30) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
  is_demo_account BOOLEAN NOT NULL DEFAULT TRUE,
  must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
  failed_login_count INTEGER NOT NULL DEFAULT 0,
  locked_until TIMESTAMP NULL,
  last_login_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_portal_users_email ON portal_users(email);
CREATE INDEX IF NOT EXISTS ix_portal_users_role ON portal_users(role);
CREATE INDEX IF NOT EXISTS ix_portal_users_status ON portal_users(status);

CREATE TABLE IF NOT EXISTS auth_sessions (
  id VARCHAR(36) PRIMARY KEY,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  user_id VARCHAR(36) NOT NULL,
  created_at TIMESTAMP NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  revoked_at TIMESTAMP NULL,
  user_agent VARCHAR(255),
  ip_address VARCHAR(80)
);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_token_hash ON auth_sessions(token_hash);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_id ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_expires_at ON auth_sessions(expires_at);

CREATE TABLE IF NOT EXISTS auth_audit_events (
  id VARCHAR(36) PRIMARY KEY,
  timestamp TIMESTAMP NOT NULL,
  actor_user_id VARCHAR(36),
  actor_email VARCHAR(255),
  actor_role VARCHAR(30),
  affected_user_id VARCHAR(36),
  affected_email VARCHAR(255),
  event_type VARCHAR(80) NOT NULL,
  outcome VARCHAR(30) NOT NULL,
  request_metadata JSON,
  details JSON,
  reason TEXT
);
CREATE INDEX IF NOT EXISTS ix_auth_audit_events_timestamp ON auth_audit_events(timestamp);
CREATE INDEX IF NOT EXISTS ix_auth_audit_events_event_type ON auth_audit_events(event_type);
