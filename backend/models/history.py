"""Patient History and Risk Summary domain models.

Stores subject-level medical, obstetric, family, social, and baseline history
ingested from RealTime EAV exports with 21 CFR Part 11 audit trails and strict blinding.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class PatientHistory(Base):
    __tablename__ = "patient_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("longitudinal_participants.id"), nullable=False, index=True)
    subject_id = Column(String(40), nullable=False, index=True)
    source_form = Column(String(120), nullable=False)
    form_version = Column(String(40))
    source_file = Column(String(255))
    completeness_score = Column(Float, default=0.0)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    participant = relationship("LongitudinalParticipant", backref="histories")


class PatientHistoryField(Base):
    __tablename__ = "patient_history_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("longitudinal_participants.id"), nullable=False, index=True)
    subject_id = Column(String(40), nullable=False, index=True)
    domain = Column(String(40), nullable=False, index=True)  # obstetric, medical, family, social, allergy_surgery, baseline
    field_key = Column(String(120), nullable=False, index=True)
    field_label_raw = Column(String(255), nullable=False)
    field_type = Column(String(40))  # yes_no, radio_group, numeric, text, date_time, checklist, dropdown
    value = Column(Text)
    value_precision = Column(String(20))  # full, month-year, year-only, null
    instance_index = Column(Integer)  # null for single, 1..N for repeating
    confidence = Column(String(30), default="single-source")  # confirmed, single-source, missing
    amber_flag = Column(Boolean, default=False)
    flag_reason = Column(String(255))
    signed_at = Column(DateTime)
    audit_actor_hash = Column(String(64))  # one-way sha256 hash
    source_batch_id = Column(UUID(as_uuid=True), ForeignKey("rt_import_batches.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("participant_id", "domain", "field_key", "instance_index", "source_batch_id", name="uq_patient_history_field"),
    )


class PatientRiskSummary(Base):
    __tablename__ = "patient_risk_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("longitudinal_participants.id"), nullable=False, unique=True, index=True)
    subject_id = Column(String(40), nullable=False, index=True)
    chips = Column(JSON, default=list)  # list of risk chip strings
    parity_summary = Column(String(100))  # G2 P1 +1M +0SB · 1 SVD / 0 CS
    gravidity = Column(Integer)
    parity = Column(Integer)
    miscarriages = Column(Integer, default=0)
    stillbirths = Column(Integer, default=0)
    vaginal_deliveries = Column(Integer, default=0)
    c_sections = Column(Integer, default=0)
    chronic_htn = Column(Boolean, default=False)
    pregestational_diabetes = Column(Boolean, default=False)
    completeness_score = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    participant = relationship("LongitudinalParticipant", backref="risk_summary")
