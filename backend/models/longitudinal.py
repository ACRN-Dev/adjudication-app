"""Additive longitudinal RealTime import domain.

Raw identity data is isolated in ``restricted_identity_crosswalk``.  No model
serializer in the adjudicator API imports that class.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class RTImportBatch(Base):
    __tablename__ = "rt_import_batches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_system = Column(String(40), nullable=False, default="RealTime")
    filename = Column(String(255), nullable=False)
    checksum = Column(String(64), nullable=False, unique=True, index=True)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    row_count = Column(Integer, default=0); participant_count = Column(Integer, default=0); visit_count = Column(Integer, default=0)
    rows_processed = Column(Integer, default=0); prohibited_count = Column(Integer, default=0)
    mapping_version = Column(String(40), nullable=False, default="RT-MAP-1.0")
    status = Column(String(50), nullable=False, default="UPLOADED", index=True)
    validation_result = Column(JSON, default=dict); blinding_result = Column(JSON, default=dict)
    error_count = Column(Integer, default=0); warning_count = Column(Integer, default=0)
    error_summary = Column(Text); processing_started_at = Column(DateTime); processing_finished_at = Column(DateTime)
    published_at = Column(DateTime); cancel_requested = Column(Boolean, default=False)
    superseded_batch_id = Column(UUID(as_uuid=True), ForeignKey("rt_import_batches.id"))
    source_path = Column(String(500))  # server-restricted staging path; never serialized


class LongitudinalParticipant(Base):
    __tablename__ = "longitudinal_participants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blinded_subject_id = Column(String(40), nullable=False, index=True)
    study = Column(String(80), nullable=False, default="PROTECT-Africa", index=True)
    site_code = Column(String(30)); participant_status = Column(String(40), default="IMPORTED")
    available_visit_count = Column(Integer, default=0); first_visit_date = Column(DateTime); latest_visit_date = Column(DateTime)
    pregnancy_status = Column(String(40), default="UNKNOWN"); workflow_status = Column(String(60), default="MONITOR_QC_REQUIRED", index=True)
    first_qualifying_visit_id = Column(UUID(as_uuid=True)); derived_onset_date = Column(DateTime); derived_onset_classification = Column(String(30))
    maximum_severity = Column(String(50)); packet_completeness = Column(Float, default=0); open_data_issues = Column(Integer, default=0)
    history_completeness = Column(Float, default=0.0)
    source_batch_id = Column(UUID(as_uuid=True), ForeignKey("rt_import_batches.id"), nullable=False, index=True)
    provenance_type = Column(String(30), default="SOURCE_RECORDED"); created_at = Column(DateTime, default=datetime.utcnow)
    visits = relationship("VisitInstance", back_populates="participant")
    reviewer_assignments = relationship("ReviewerAssignment", back_populates="participant")
    __table_args__ = (UniqueConstraint("blinded_subject_id","source_batch_id",name="uq_blinded_subject_batch"),)


class RestrictedIdentityCrosswalk(Base):
    __tablename__ = "restricted_identity_crosswalk"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("longitudinal_participants.id"), nullable=False, unique=True)
    protected_mrn = Column(Text, nullable=False); screening_number = Column(Text); restricted_randomisation_reference = Column(Text)
    source_system = Column(String(40), default="RealTime"); created_at = Column(DateTime, default=datetime.utcnow)
    access_classification = Column(String(50), default="RESTRICTED_IDENTITY")


class VisitInstance(Base):
    __tablename__ = "visit_instances"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("longitudinal_participants.id"), nullable=False, index=True)
    source_batch_id = Column(UUID(as_uuid=True), ForeignKey("rt_import_batches.id"), nullable=False, index=True)
    source_system = Column(String(40), default="RealTime"); form_title = Column(String(255)); form_version = Column(String(30))
    scheduled_visit_code = Column(String(40), index=True); visit_type = Column(String(40)); visit_occurrence = Column(Integer, default=1); visit_sequence = Column(Integer)
    visit_datetime = Column(DateTime, index=True); gestational_age_days = Column(Integer); source_instance_id = Column(String(100))
    reconstruction_method = Column(String(80), nullable=False); reconstruction_confidence = Column(String(20), nullable=False)
    qc_status = Column(String(40), default="PENDING", index=True); superseded = Column(Boolean, default=False)
    participant = relationship("LongitudinalParticipant", back_populates="visits")
    observations = relationship("CanonicalObservation", back_populates="visit")
    __table_args__ = (UniqueConstraint("participant_id","source_batch_id","form_title","visit_occurrence",name="uq_rt_visit_occurrence"),)


class CanonicalObservation(Base):
    __tablename__ = "canonical_observations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("longitudinal_participants.id"), nullable=False, index=True)
    visit_id = Column(UUID(as_uuid=True), ForeignKey("visit_instances.id"), nullable=False, index=True)
    source_batch_id = Column(UUID(as_uuid=True), ForeignKey("rt_import_batches.id"), nullable=False)
    canonical_variable = Column(String(80), nullable=False, index=True); raw_source_value = Column(Text)
    parsed_text_value = Column(Text); numeric_value = Column(Float); datetime_value = Column(DateTime); coded_value = Column(String(100)); unit = Column(String(40))
    observation_datetime = Column(DateTime, index=True); date_confidence = Column(String(20), default="MISSING")
    source_form = Column(String(255)); source_page = Column(String(255)); source_field_label = Column(String(500)); source_row_number = Column(Integer)
    mapping_version = Column(String(40)); quality_status = Column(String(40), default="VALID"); provenance_type = Column(String(30), default="SOURCE_RECORDED")
    prohibited_flag = Column(Boolean, default=False); superseded = Column(Boolean, default=False); source_fingerprint = Column(String(64), index=True)
    visit = relationship("VisitInstance", back_populates="observations")
    __table_args__ = (Index("ix_obs_participant_variable_date","participant_id","canonical_variable","observation_datetime"),)


class VisitDerivation(Base):
    __tablename__ = "visit_derivations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), nullable=False, index=True); visit_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    dv_identifier = Column(String(10), nullable=False); result = Column(JSON); status = Column(String(40)); inputs = Column(JSON); missing_inputs = Column(JSON)
    rule_version = Column(String(40), default="ISSHP-2021-v1.3"); derived_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("visit_id","dv_identifier",name="uq_visit_dv"),)


class LongitudinalCaseDerivation(Base):
    __tablename__ = "longitudinal_case_derivations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    earliest_hypertension_date = Column(DateTime); earliest_bp_confirmation_date = Column(DateTime); earliest_qualifying_confirmation_date = Column(DateTime)
    earliest_qualifying_pe_date = Column(DateTime); first_qualifying_visit_id = Column(UUID(as_uuid=True)); gestational_age_at_onset_days = Column(Integer)
    onset_classification = Column(String(30)); maximum_severity = Column(String(50)); packet_completeness = Column(Float)
    certainty_restriction = Column(String(30)); trigger_status = Column(String(30)); recorded_site_diagnosis = Column(String(100)); recorded_site_diagnosis_date = Column(DateTime)
    recorded_versus_derived_discrepancy = Column(JSON); explanation = Column(Text); derivation_version = Column(String(40), default="RT-LONG-1.0")
    monitor_confirmation_status = Column(String(40), default="PENDING"); derived_at = Column(DateTime, default=datetime.utcnow)


class ImportIssue(Base):
    __tablename__ = "rt_import_issues"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), nullable=False, index=True); participant_id = Column(UUID(as_uuid=True), index=True); visit_id = Column(UUID(as_uuid=True), index=True)
    source_row = Column(Integer); issue_type = Column(String(50), nullable=False, index=True); severity = Column(String(20), nullable=False); description = Column(Text, nullable=False)
    resolution_status = Column(String(30), default="OPEN"); resolution_note = Column(Text); resolved_by = Column(String(255)); resolved_at = Column(DateTime)


class ReviewerAssignment(Base):
    __tablename__ = "reviewer_assignments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("longitudinal_participants.id"), nullable=False, index=True)
    reviewer_upn = Column(String(255), nullable=False, index=True)
    reviewer_role = Column(String(20), nullable=False); status = Column(String(30), default="ASSIGNED"); assigned_at = Column(DateTime, default=datetime.utcnow)
    participant = relationship("LongitudinalParticipant", back_populates="reviewer_assignments")
    __table_args__ = (UniqueConstraint("participant_id","reviewer_role",name="uq_participant_reviewer_role"),)


class LongitudinalAuditEvent(Base):
    __tablename__ = "longitudinal_audit_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4); timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    actor = Column(String(255), nullable=False); actor_role = Column(String(80)); action = Column(String(80), nullable=False, index=True)
    entity_type = Column(String(50)); entity_id = Column(String(80)); safe_details = Column(JSON, default=dict); record_hash = Column(String(64), nullable=False)


class LabReferenceRange(Base):
    """Configurable Normal/Abnormal thresholds for a lab analyte.

    A row with site_code=NULL is the global default for that analyte; a row
    with site_code set overrides the default for that site only. lab_code
    optionally scopes a range to a specific reporting laboratory when a site
    uses more than one lab with different assay ranges.
    """
    __tablename__ = "lab_reference_ranges"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analyte = Column(String(80), nullable=False, index=True)  # canonical_variable, e.g. PLATELETS, CREATININE, AST
    site_code = Column(String(30), nullable=True, index=True)  # NULL = global default
    lab_code = Column(String(60), nullable=True)  # optional reporting-lab override
    unit = Column(String(40))
    low = Column(Float, nullable=True)   # inclusive lower bound of normal range; NULL = no lower bound
    high = Column(Float, nullable=True)  # inclusive upper bound of normal range; NULL = no upper bound
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("analyte", "site_code", "lab_code", name="uq_lab_reference_scope"),)
