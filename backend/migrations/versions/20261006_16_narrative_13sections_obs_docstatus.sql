-- Migration 16: Narrative 13-section expansion + observation documentation_status
-- Generated: 2026-10-06
-- Safe to re-run: all statements use IF NOT EXISTS or are idempotent.

-- ── narratives: add sections 6-13 (ai and edited) ─────────────────────────────
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS ai_section_6   TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS ai_section_7   TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS ai_section_8   TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS ai_section_9   TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS ai_section_10  TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS ai_section_11  TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS ai_section_12  TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS ai_section_13  TEXT;

ALTER TABLE narratives ADD COLUMN IF NOT EXISTS edited_section_6   TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS edited_section_7   TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS edited_section_8   TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS edited_section_9   TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS edited_section_10  TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS edited_section_11  TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS edited_section_12  TEXT;
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS edited_section_13  TEXT;

-- Per-section documentation-status summary (JSON object)
-- Uses 7-value taxonomy: Documented | Not documented | Not assessed |
-- Unable to assess | Not applicable | Conflicting | Pending verification
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS ai_documentation_status JSONB;

-- ── canonical_observations: add documentation_status ──────────────────────────
-- Stores the 7-value documentation status for each captured observation.
-- Defaults to NULL (not yet classified). The pipeline will populate this
-- during Phase 5 validation once the classification logic is in place.
ALTER TABLE canonical_observations
    ADD COLUMN IF NOT EXISTS documentation_status VARCHAR(40);

-- Index to allow fast filtering of observations by documentation status
-- (e.g. "show me all fields where status = 'Conflicting' for this participant")
CREATE INDEX IF NOT EXISTS ix_obs_documentation_status
    ON canonical_observations (participant_id, documentation_status)
    WHERE documentation_status IS NOT NULL;
