BEGIN;

ALTER TABLE portal_users ADD COLUMN IF NOT EXISTS portal_role VARCHAR(40);
ALTER TABLE portal_users ADD COLUMN IF NOT EXISTS study_scope VARCHAR(500) DEFAULT '*';
ALTER TABLE portal_users ALTER COLUMN password_hash DROP NOT NULL;

UPDATE portal_users SET portal_role = 'ADMIN' WHERE role = 'ADMIN' AND portal_role IS NULL;
UPDATE portal_users SET portal_role = 'MONITOR_QC_REVIEWER' WHERE role = 'MONITOR' AND portal_role IS NULL;

COMMIT;
