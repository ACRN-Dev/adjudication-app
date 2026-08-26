BEGIN;

CREATE TYPE diagnosis_code_v2 AS ENUM ('PE', 'SEVERE_PE', 'ECLAMPSIA', 'HELLP', 'OTHER');

CREATE TABLE adjudication_visits (
    id UUID PRIMARY KEY,
    participant_id UUID NOT NULL REFERENCES participants(id),
    visit_number INTEGER NOT NULL CHECK (visit_number > 0),
    visit_code VARCHAR(40) NOT NULL,
    visit_date TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_subject_visit_number UNIQUE (participant_id, visit_number),
    CONSTRAINT uq_subject_visit_code UNIQUE (participant_id, visit_code)
);

CREATE INDEX ix_adjudication_visits_participant_id ON adjudication_visits(participant_id);
CREATE INDEX ix_adjudication_visits_visit_date ON adjudication_visits(visit_date);

CREATE TABLE visit_measurement_dates (
    id UUID PRIMARY KEY,
    visit_id UUID NOT NULL REFERENCES adjudication_visits(id) ON DELETE CASCADE,
    measurement_type VARCHAR(50) NOT NULL,
    measured_at TIMESTAMP NOT NULL,
    source_reference VARCHAR(255),
    CONSTRAINT uq_visit_measurement_timestamp UNIQUE (visit_id, measurement_type, measured_at)
);

CREATE INDEX ix_visit_measurement_dates_sequence
    ON visit_measurement_dates(visit_id, measured_at, measurement_type);

-- Backfill one durable subject+visit row for every legacy decision visit.
INSERT INTO adjudication_visits (id, participant_id, visit_number, visit_code, visit_date)
SELECT gen_random_uuid(), p.id, n.visit_number, 'V' || LPAD(n.visit_number::text, 2, '0'),
       MIN(n.measurement_date)
FROM participants p
JOIN (
    SELECT participant_id, COALESCE(visit_number, 1) AS visit_number,
           date_of_diagnosis AS measurement_date FROM adjudication_records
    UNION ALL
    SELECT participant_id, COALESCE(visit_number, 1), date_of_diagnosis FROM committee_decisions
) n ON n.participant_id = p.id
GROUP BY p.id, n.visit_number
ON CONFLICT (participant_id, visit_number) DO NOTHING;

ALTER TABLE adjudication_records ADD COLUMN visit_id UUID;
ALTER TABLE adjudication_records ADD COLUMN comment TEXT;
ALTER TABLE adjudication_records ADD COLUMN other_rationale TEXT;
UPDATE adjudication_records r SET visit_id = v.id
FROM adjudication_visits v
WHERE v.participant_id = r.participant_id AND v.visit_number = COALESCE(r.visit_number, 1);
ALTER TABLE adjudication_records ALTER COLUMN visit_id SET NOT NULL;
ALTER TABLE adjudication_records ADD CONSTRAINT fk_adjudication_record_visit
    FOREIGN KEY (visit_id) REFERENCES adjudication_visits(id);
ALTER TABLE adjudication_records ADD CONSTRAINT uq_visit_reviewer_role UNIQUE (visit_id, reviewer_role);

ALTER TABLE committee_decisions ADD COLUMN visit_id UUID;
UPDATE committee_decisions c SET visit_id = v.id
FROM adjudication_visits v
WHERE v.participant_id = c.participant_id AND v.visit_number = COALESCE(c.visit_number, 1);
ALTER TABLE committee_decisions ALTER COLUMN visit_id SET NOT NULL;
ALTER TABLE committee_decisions ADD CONSTRAINT fk_committee_decision_visit
    FOREIGN KEY (visit_id) REFERENCES adjudication_visits(id);
ALTER TABLE committee_decisions ADD CONSTRAINT uq_committee_decision_visit UNIQUE (visit_id);
ALTER TABLE committee_decisions DROP CONSTRAINT IF EXISTS committee_decisions_participant_id_key;

ALTER TABLE adjudication_records ALTER COLUMN diagnosis TYPE diagnosis_code_v2
USING CASE diagnosis::text
    WHEN 'PREECLAMPSIA' THEN 'PE'::diagnosis_code_v2
    WHEN 'ECLAMPSIA' THEN 'ECLAMPSIA'::diagnosis_code_v2
    WHEN 'HELLP' THEN 'HELLP'::diagnosis_code_v2
    ELSE NULL
END;
ALTER TABLE committee_decisions ALTER COLUMN final_diagnosis TYPE diagnosis_code_v2
USING CASE final_diagnosis::text
    WHEN 'PREECLAMPSIA' THEN 'PE'::diagnosis_code_v2
    WHEN 'ECLAMPSIA' THEN 'ECLAMPSIA'::diagnosis_code_v2
    WHEN 'HELLP' THEN 'HELLP'::diagnosis_code_v2
    ELSE NULL
END;

ALTER TABLE adjudication_records ADD CONSTRAINT ck_other_reviewer_c_rationale CHECK (
    diagnosis <> 'OTHER' OR
    (reviewer_role = 'REVIEWER_C' AND other_rationale IS NOT NULL AND length(trim(other_rationale)) > 0)
);

ALTER TABLE committee_decisions ADD CONSTRAINT ck_committee_other_from_reviewer_c CHECK (
    final_diagnosis <> 'OTHER' OR
    (adopted_reviewer = 'REVIEWER_C' AND reviewer_c_rationale IS NOT NULL AND length(trim(reviewer_c_rationale)) > 0)
);

COMMIT;
