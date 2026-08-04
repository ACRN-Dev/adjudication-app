"""
SQLAlchemy ORM Models — Canonical Data Model
============================================
Every field stores both its EDC value, eSource value, and the resolved
canonical value with full provenance — per Dr. Makadzange's canonical
adjudication data model specification.

Table hierarchy:
  ImportBatch → Participant → CanonicalField
  MappingRule (admin-configured, drives CanonicalField population)
  DerivationResult (output of derivation_engine.py per case)
  Narrative (AI draft + human edits)
  AdjudicationRecord (Reviewer A and B — blinded)
  CommitteeDecision (Chair consensus)
  AuditEvent (immutable append-only log, 21 CFR Part 11)
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from database import Base


# ── Enums ──────────────────────────────────────────────────────────────────

class StudyCode(str, enum.Enum):
    EOPE = "PROTECT-Africa"
    LOPE = "LOPE-Nigeria"


class SourceSystem(str, enum.Enum):
    EDC = "EDC"
    ESOURCE = "eSource"
    DERIVED = "DERIVED"
    MANUAL = "MANUAL"


class DiscrepancyCategory(str, enum.Enum):
    EXACT_MATCH = "EXACT_MATCH"
    EQUIVALENT_AFTER_CONVERSION = "EQUIVALENT_AFTER_CONVERSION"
    EDC_POPULATED_ESOURCE_MISSING = "EDC_POPULATED_ESOURCE_MISSING"
    ESOURCE_POPULATED_EDC_MISSING = "ESOURCE_POPULATED_EDC_MISSING"
    VALUE_DISCREPANCY = "VALUE_DISCREPANCY"
    DATE_DISCREPANCY = "DATE_DISCREPANCY"
    CODING_DISCREPANCY = "CODING_DISCREPANCY"
    PARTICIPANT_UNMATCHED = "PARTICIPANT_UNMATCHED"


class AdjudicationStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    CONCORDANT = "CONCORDANT"
    DISCORDANT = "DISCORDANT"
    COMMITTEE_PENDING = "COMMITTEE_PENDING"
    FINALIZED = "FINALIZED"
    LOCKED = "LOCKED"


class ReviewerRole(str, enum.Enum):
    REVIEWER_A = "REVIEWER_A"
    REVIEWER_B = "REVIEWER_B"
    CHAIR = "CHAIR"


class DiagnosisCode(str, enum.Enum):
    PREECLAMPSIA = "Pre-eclampsia"
    GESTATIONAL_HTN = "Gestational hypertension"
    CHRONIC_HTN = "Chronic HTN"
    SUPERIMPOSED_PE = "Superimposed PE"
    ECLAMPSIA = "Eclampsia"
    HELLP = "HELLP Syndrome"
    NOT_PE = "Not PE"


class OnsetClass(str, enum.Enum):
    EOPE = "EOPE"   # < 34+0 weeks
    LOPE = "LOPE"   # >= 34+0 weeks


class SeverityGrade(str, enum.Enum):
    WITH_SEVERE = "With severe features"
    WITHOUT_SEVERE = "Without severe features"
    ECLAMPSIA_SAE = "Eclampsia / SAE"


class CertaintyLevel(str, enum.Enum):
    DEFINITE = "Definite"
    PROBABLE = "Probable"
    POSSIBLE = "Possible"
    NOT_PE = "Not PE"


# ── Import Batch ───────────────────────────────────────────────────────────

class ImportBatch(Base):
    """
    One record per import event. Retains raw file metadata for traceability.
    Every CanonicalField links back to the ImportBatch that produced it.
    """
    __tablename__ = "import_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study = Column(SAEnum(StudyCode), nullable=False)
    edc_filename = Column(String(255))
    esource_filename = Column(String(255))
    edc_export_date = Column(DateTime)
    esource_export_date = Column(DateTime)
    edc_row_count = Column(Integer)
    esource_row_count = Column(Integer)
    mapping_version = Column(String(50), nullable=False)
    imported_by = Column(String(255))             # Entra ID UPN
    import_timestamp = Column(DateTime, default=datetime.utcnow)
    validation_errors = Column(JSON, default=list) # List of validation error strings
    status = Column(String(50), default="COMPLETE")

    participants = relationship("Participant", back_populates="import_batch")


# ── Mapping Rule ───────────────────────────────────────────────────────────

class MappingRule(Base):
    """
    Admin-configurable canonical field mapping.
    Drives how EDC and eSource columns map to canonical field names.
    Not hard-coded — configurable via the mapping manager UI.
    """
    __tablename__ = "mapping_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_field = Column(String(100), nullable=False, index=True)
    edc_field = Column(String(100))
    esource_field = Column(String(100))
    authority = Column(SAEnum(SourceSystem), default=SourceSystem.EDC)  # Preferred source
    transformation = Column(String(500))  # e.g. "mg/dL to mmol/L: value * 88.42"
    unit_in = Column(String(50))
    unit_out = Column(String(50))
    is_active = Column(Boolean, default=True)
    version = Column(String(20), nullable=False, default="1.0")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Participant ────────────────────────────────────────────────────────────

class Participant(Base):
    """
    One record per study participant. Links to all their canonical fields,
    derivation results, narratives, and adjudication records.
    """
    __tablename__ = "participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = Column(String(50), nullable=False, index=True)  # e.g. ZWE001-0292
    case_number = Column(String(50))                              # e.g. ADJ-0412
    site_code = Column(String(20))                                # e.g. ZWE001
    site_name = Column(String(255))
    study = Column(SAEnum(StudyCode), nullable=False)
    import_batch_id = Column(UUID(as_uuid=True), ForeignKey("import_batches.id"))
    status = Column(SAEnum(AdjudicationStatus), default=AdjudicationStatus.PENDING)
    trigger_code = Column(String(20))                             # e.g. DV-30
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    import_batch = relationship("ImportBatch", back_populates="participants")
    canonical_fields = relationship("CanonicalField", back_populates="participant",
                                    cascade="all, delete-orphan")
    derivation_results = relationship("DerivationResult", back_populates="participant",
                                      cascade="all, delete-orphan")
    narratives = relationship("Narrative", back_populates="participant",
                              cascade="all, delete-orphan")
    adjudication_records = relationship("AdjudicationRecord", back_populates="participant",
                                        cascade="all, delete-orphan")
    committee_decision = relationship("CommitteeDecision", back_populates="participant",
                                      uselist=False, cascade="all, delete-orphan")


# ── Canonical Field ────────────────────────────────────────────────────────

class CanonicalField(Base):
    """
    The core of the canonical data model.

    For EVERY variable, we store:
      - edc_value:         raw value from EDC
      - esource_value:     raw value from eSource
      - canonical_value:   resolved value (per resolve_value() logic)
      - source_used:       which system the canonical_value came from
      - discrepant:        True if EDC and eSource disagree
      - discrepancy_cat:   classification of the discrepancy
      - transformation:    unit conversion or coding applied
      - mapping_version:   version of MappingRule used
      - import_batch_id:   links to the source import
    """
    __tablename__ = "canonical_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    import_batch_id = Column(UUID(as_uuid=True), ForeignKey("import_batches.id"))
    mapping_version = Column(String(20))

    # Identity
    canonical_field = Column(String(100), nullable=False, index=True)
    visit_label = Column(String(50))    # e.g. "V02", "EVENT-01"
    event_datetime = Column(DateTime)

    # Source values (raw — never altered)
    edc_value = Column(String(500))
    esource_value = Column(String(500))

    # Resolved canonical value
    canonical_value = Column(String(500))
    canonical_value_numeric = Column(Float)
    unit = Column(String(50))
    source_used = Column(SAEnum(SourceSystem))

    # Discrepancy flags
    discrepant = Column(Boolean, default=False)
    discrepancy_category = Column(SAEnum(DiscrepancyCategory))
    discrepancy_note = Column(Text)
    clinically_meaningful = Column(Boolean)  # Null = not assessed yet

    # Blinding guard — biomarkers are never surfaced in canonical fields
    is_blinded = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    participant = relationship("Participant", back_populates="canonical_fields")


# ── Derivation Result ──────────────────────────────────────────────────────

class DerivationResult(Base):
    """
    Output of the deterministic clinical derivation engine for one criterion.
    Every result shows the formula, input values, and source fields used.
    AI must NEVER override these — they are the scientific record.
    """
    __tablename__ = "derivation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False)

    criterion_id = Column(String(30), nullable=False)  # e.g. "HTN-01"
    criterion_name = Column(String(255))
    met = Column(Boolean, nullable=False)
    formula = Column(Text)              # Human-readable formula applied
    inputs = Column(JSON)               # Dict of field_name: value used
    source_fields = Column(JSON)        # List of canonical_field IDs used
    first_date_met = Column(DateTime)   # Date the criterion was first satisfied
    gestational_age_at_event = Column(String(10))  # e.g. "31+2"
    rule_version = Column(String(20), nullable=False, default="ISSHP-2021-v1.0")
    derived_at = Column(DateTime, default=datetime.utcnow)

    # Final derived composite outputs
    derived_subtype = Column(SAEnum(OnsetClass))   # EOPE or LOPE
    derived_severity = Column(String(50))           # e.g. SEVERE_FEATURES, ECLAMPSIA
    derived_onset_date = Column(DateTime)

    participant = relationship("Participant", back_populates="derivation_results")


# ── Narrative ─────────────────────────────────────────────────────────────

class Narrative(Base):
    """
    AI-generated clinical narrative with full version tracking.
    Human edits are stored separately — original is never overwritten.
    """
    __tablename__ = "narratives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False)

    # AI generation metadata
    prompt_version = Column(String(20), nullable=False, default="v1.0")
    model_used = Column(String(100))                     # e.g. "gpt-4o-2024-08-06"
    generated_at = Column(DateTime, default=datetime.utcnow)

    # Original AI output (immutable after generation)
    ai_section_1 = Column(Text)
    ai_section_2 = Column(Text)
    ai_section_3 = Column(Text)
    ai_section_4 = Column(Text)
    ai_section_5 = Column(Text)
    ai_criteria_met = Column(JSON)          # List of criteria codes
    ai_missing_evidence = Column(JSON)      # List of missing data items
    ai_discrepancies = Column(JSON)         # List of EDC/eSource discrepancies flagged

    # Human-edited version (may differ from AI original)
    edited_section_1 = Column(Text)
    edited_section_2 = Column(Text)
    edited_section_3 = Column(Text)
    edited_section_4 = Column(Text)
    edited_section_5 = Column(Text)
    edited_by = Column(String(255))          # Entra ID UPN of editor
    edited_at = Column(DateTime)
    edit_rationale = Column(Text)

    participant = relationship("Participant", back_populates="narratives")


# ── Adjudication Record ────────────────────────────────────────────────────

class AdjudicationRecord(Base):
    """
    Individual reviewer submission (Reviewer A or Reviewer B).
    Blinded: the backend enforces that reviewer A cannot see reviewer B's
    submission (and vice versa) until concordance check runs.
    """
    __tablename__ = "adjudication_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False)

    reviewer_role = Column(SAEnum(ReviewerRole), nullable=False)
    reviewer_upn = Column(String(255), nullable=False)   # Entra ID UPN
    reviewer_name = Column(String(255))

    # Clinical decision
    meets_criteria = Column(Boolean)
    diagnosis = Column(SAEnum(DiagnosisCode))
    onset_class = Column(SAEnum(OnsetClass))
    severity = Column(SAEnum(SeverityGrade))
    certainty = Column(SAEnum(CertaintyLevel))
    differential_diagnosis = Column(String(500))
    rationale = Column(Text)
    narrative_id = Column(UUID(as_uuid=True), ForeignKey("narratives.id"))

    # 21 CFR Part 11 e-signature
    signed = Column(Boolean, default=False)
    signed_at = Column(DateTime)
    signature_hash = Column(String(255))   # SHA-256 of case record + reviewer decision
    mfa_verified = Column(Boolean, default=False)

    submitted_at = Column(DateTime, default=datetime.utcnow)

    participant = relationship("Participant", back_populates="adjudication_records")


# ── Committee Decision ─────────────────────────────────────────────────────

class CommitteeDecision(Base):
    """
    Chair's final consensus outcome for a discordant case.
    Locked after Chair signature — immutable thereafter.
    """
    __tablename__ = "committee_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False,
                            unique=True)

    adopted_reviewer = Column(SAEnum(ReviewerRole))  # REVIEWER_A or REVIEWER_B
    final_diagnosis = Column(SAEnum(DiagnosisCode))
    final_onset_class = Column(SAEnum(OnsetClass))
    final_severity = Column(SAEnum(SeverityGrade))
    final_certainty = Column(SAEnum(CertaintyLevel))
    chair_rationale = Column(Text, nullable=False)
    quorum_met = Column(Boolean, default=True)
    members_present = Column(Integer)

    # Chair signature
    chair_upn = Column(String(255))
    chair_name = Column(String(255))
    signed_at = Column(DateTime)
    signature_hash = Column(String(255))
    locked = Column(Boolean, default=False)
    locked_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    participant = relationship("Participant", back_populates="committee_decision")


# ── Audit Event (Immutable) ────────────────────────────────────────────────

class AuditEvent(Base):
    """
    Immutable append-only audit log.
    21 CFR Part 11 §11.10(e): Audit trails must be computer-generated
    and include operator ID, date/time, and a description of the action.

    NEVER updated or deleted — only INSERT operations permitted.
    """
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)   # e.g. "IMPORT", "DERIVE", "SIGN"
    participant_id = Column(UUID(as_uuid=True), nullable=True)
    import_batch_id = Column(UUID(as_uuid=True), nullable=True)

    actor_upn = Column(String(255))          # Entra ID UPN
    actor_name = Column(String(255))
    actor_role = Column(String(50))

    description = Column(Text, nullable=False)
    previous_value = Column(Text)            # For edits: what it was before
    new_value = Column(Text)                 # For edits: what it changed to
    event_metadata = Column(JSON)            # Additional context (renamed from 'metadata' — SQLAlchemy reserved)

    # Integrity
    record_hash = Column(String(255))        # SHA-256 hash of this audit record
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    ip_address = Column(String(50))
