-- Contract fields added to PortalUser (models/auth.py) without a matching migration; the
-- SQLite startup patch in database.py covers local dev, this covers Postgres. Existing users
-- default to a valid contract, mirroring the model defaults.
ALTER TABLE portal_users ADD COLUMN IF NOT EXISTS contract_valid BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE portal_users ADD COLUMN IF NOT EXISTS contract_period VARCHAR(100) DEFAULT '1 Year (Active)';
