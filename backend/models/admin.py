"""Versioned, non-clinical administration domain for the ACRN Admin Portal."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, Integer, ForeignKey, UniqueConstraint
from database import Base


def uid():
    return str(uuid.uuid4())


class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(String(36), primary_key=True, default=uid)
    display_name = Column(String(160), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    organisation = Column(String(160), nullable=False, default="ACRN Foundation")
    country = Column(String(80)); job_title = Column(String(120))
    account_type = Column(String(40), default="Demo")
    authentication_source = Column(String(40), default="DEMO")
    entra_object_id = Column(String(80)); status = Column(String(40), default="Invited", index=True)
    training_status = Column(String(40), default="Incomplete")
    coi_status = Column(String(40), default="Pending")
    access_start = Column(DateTime); access_expiry = Column(DateTime, index=True); last_login = Column(DateTime)
    created_by = Column(String(255)); approved_by = Column(String(255)); deactivated_by = Column(String(255))
    status_reason = Column(Text); is_demo = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AdminRole(Base):
    __tablename__ = "admin_roles"
    id = Column(String(36), primary_key=True, default=uid)
    code = Column(String(80), nullable=False, index=True)
    name = Column(String(120), nullable=False); version = Column(Integer, default=1)
    status = Column(String(30), default="Active"); permissions = Column(JSON, default=list)
    delegated_permissions = Column(JSON, default=list); high_risk = Column(Boolean, default=False)
    is_system = Column(Boolean, default=True); is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("code", "version", name="uq_admin_role_version"),)


class UserRole(Base):
    __tablename__ = "admin_user_roles"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("admin_users.id"), nullable=False, index=True)
    role_code = Column(String(80), nullable=False); effective_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime); assigned_by = Column(String(255)); reason = Column(Text, nullable=False)
    is_demo = Column(Boolean, default=False)


class Permission(Base):
    __tablename__ = "admin_permissions"
    id = Column(String(36), primary_key=True, default=uid)
    code = Column(String(100), nullable=False, unique=True); description = Column(String(255))
    portal = Column(String(30)); risk_level = Column(String(20), default="STANDARD"); is_demo = Column(Boolean, default=False)


class PortalAccess(Base):
    __tablename__ = "admin_portal_access"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("admin_users.id"), nullable=False, index=True)
    portal = Column(String(30), nullable=False); status = Column(String(30), default="Pending approval")
    starts_at = Column(DateTime); expires_at = Column(DateTime); approved_by = Column(String(255)); is_demo = Column(Boolean, default=False)


class AccessRequest(Base):
    __tablename__ = "admin_access_requests"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("admin_users.id"), nullable=False, index=True)
    requested_roles = Column(JSON, default=list); requested_studies = Column(JSON, default=list)
    requested_by = Column(String(255), nullable=False); justification = Column(Text, nullable=False)
    status = Column(String(30), default="Pending"); requested_at = Column(DateTime, default=datetime.utcnow); is_demo = Column(Boolean, default=False)


class AccessApproval(Base):
    __tablename__ = "admin_access_approvals"
    id = Column(String(36), primary_key=True, default=uid)
    request_id = Column(String(36), ForeignKey("admin_access_requests.id"), nullable=False, index=True)
    approver_upn = Column(String(255), nullable=False); decision = Column(String(30), nullable=False)
    reason = Column(Text, nullable=False); decided_at = Column(DateTime, default=datetime.utcnow); is_demo = Column(Boolean, default=False)


class TrainingRecord(Base):
    __tablename__ = "admin_training_records"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("admin_users.id"), nullable=False, index=True)
    course_code = Column(String(80), nullable=False); status = Column(String(30), nullable=False)
    completed_at = Column(DateTime); expires_at = Column(DateTime); evidence_reference = Column(String(255)); is_demo = Column(Boolean, default=False)


class AdjudicatorProfile(Base):
    __tablename__ = "adjudicator_profiles"
    id = Column(String(36), primary_key=True, default=uid)
    adjudicator_upn = Column(String(255), nullable=False, unique=True, index=True)
    contract_signed_at = Column(DateTime)  # legacy compatibility; use study contracts below
    billing_status = Column(String(30), nullable=False, default="NOT_READY", index=True)  # Finance-only legacy field
    billing_note = Column(Text)  # Finance-only legacy field
    updated_by = Column(String(255))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AdjudicatorStudyContract(Base):
    __tablename__ = "adjudicator_study_contracts"
    id = Column(String(36), primary_key=True, default=uid)
    adjudicator_upn = Column(String(255), nullable=False, index=True)
    study_code = Column(String(80), nullable=False, index=True)
    contract_signed_at = Column(DateTime)
    contract_reference = Column(String(255))
    terms_of_reference_url = Column(String(1000))
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    status = Column(String(30), nullable=False, default="ACTIVE")
    changed_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("adjudicator_upn", "study_code", "effective_from", name="uq_adjudicator_study_contract"),)


class AdjudicatorCommitteeMembership(Base):
    __tablename__ = "adjudicator_committee_memberships"
    id = Column(String(36), primary_key=True, default=uid)
    adjudicator_upn = Column(String(255), nullable=False, index=True)
    committee_name = Column(String(160), nullable=False)
    membership_role = Column(String(30), nullable=False, default="MEMBER")
    effective_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    effective_to = Column(DateTime)
    status = Column(String(30), nullable=False, default="ACTIVE")
    changed_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AdjudicationActivityLedger(Base):
    """Immutable activity facts; no true subject identifier is stored or serialized."""
    __tablename__ = "adjudication_activity_ledger"
    id = Column(String(36), primary_key=True, default=uid)
    adjudicator_upn = Column(String(255), nullable=False, index=True)
    study_code = Column(String(80), nullable=False, index=True)
    blinded_case_reference = Column(String(100), nullable=False, index=True)
    subject_visit_id = Column(String(36), nullable=True, index=True)
    role_served = Column(String(30), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    billable = Column(Boolean, nullable=False, default=False)
    status = Column(String(30), nullable=False, default="RECORDED")
    source_record_id = Column(String(36))
    idempotency_key = Column(String(255), nullable=False, unique=True)
    metadata_json = Column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("adjudicator_upn", "blinded_case_reference", "role_served", "event_type", name="uq_activity_event"),)


class BillingRateCard(Base):
    __tablename__ = "billing_rate_cards"
    id = Column(String(36), primary_key=True, default=uid)
    study_code = Column(String(80), nullable=False, index=True)
    role_served = Column(String(30), nullable=False)
    event_type = Column(String(50), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    rate_amount = Column(Integer, nullable=False)  # minor currency units
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime)
    status = Column(String(30), nullable=False, default="ACTIVE")
    approved_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BillingPeriod(Base):
    __tablename__ = "billing_periods"
    id = Column(String(36), primary_key=True, default=uid)
    period_code = Column(String(40), nullable=False, unique=True)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    due_at = Column(DateTime)
    status = Column(String(30), nullable=False, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BillingPayment(Base):
    __tablename__ = "billing_payments"
    id = Column(String(36), primary_key=True, default=uid)
    adjudicator_upn = Column(String(255), nullable=False, index=True)
    billing_period_id = Column(String(36), ForeignKey("billing_periods.id"), nullable=False)
    amount_minor = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    paid_at = Column(DateTime)
    payment_reference = Column(String(255))
    status = Column(String(30), nullable=False, default="OUTSTANDING")
    recorded_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ConflictDeclaration(Base):
    __tablename__ = "admin_conflict_declarations"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("admin_users.id"), nullable=False, index=True)
    study_code = Column(String(50), index=True); status = Column(String(30), nullable=False)
    declared_at = Column(DateTime, default=datetime.utcnow); expires_at = Column(DateTime); reviewed_by = Column(String(255)); is_demo = Column(Boolean, default=False)


class StudyAccess(Base):
    __tablename__ = "admin_study_access"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("admin_users.id"), nullable=False, index=True)
    study_code = Column(String(50), nullable=False, index=True); site_codes = Column(JSON, default=list)
    status = Column(String(30), default="Pending approval"); starts_at = Column(DateTime); expires_at = Column(DateTime)
    requested_by = Column(String(255)); approved_by = Column(String(255)); reason = Column(Text)
    is_demo = Column(Boolean, default=False)


class AdminStudy(Base):
    __tablename__ = "admin_studies"
    id = Column(String(36), primary_key=True, default=uid)
    study_code = Column(String(50), nullable=False, index=True); version = Column(Integer, nullable=False, default=1)
    name = Column(String(200), nullable=False); protocol_number = Column(String(80)); protocol_version = Column(String(40))
    endpoint_type = Column(String(100)); countries = Column(JSON, default=list); sponsor = Column(String(160))
    owner = Column(String(160)); start_date = Column(DateTime); end_date = Column(DateTime)
    status = Column(String(40), default="Draft"); applicable_sops = Column(JSON, default=list)
    form_versions = Column(JSON, default=list); mapping_version = Column(String(40)); rule_version = Column(String(40))
    adjudication_model = Column(String(100)); retention_classification = Column(String(80))
    export_destination = Column(String(120)); environment = Column(String(30), default="DEMO")
    approved_by = Column(String(255)); change_reason = Column(Text); is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("study_code", "version", name="uq_admin_study_version"),)


class AdminSite(Base):
    __tablename__ = "admin_sites"
    id = Column(String(36), primary_key=True, default=uid)
    site_code = Column(String(40), nullable=False); blinded_name = Column(String(160), nullable=False)
    country = Column(String(80)); study_code = Column(String(50), nullable=False, index=True)
    status = Column(String(40)); import_identifier = Column(String(80)); source_types = Column(JSON, default=list)
    contact_reference = Column(String(100)); activation_date = Column(DateTime); closure_date = Column(DateTime)
    is_demo = Column(Boolean, default=False)


class ControlledVersion(Base):
    """Rules, mappings, forms and workflows; active versions are immutable."""
    __tablename__ = "admin_controlled_versions"
    id = Column(String(36), primary_key=True, default=uid)
    resource_type = Column(String(30), nullable=False, index=True)
    code = Column(String(80), nullable=False, index=True); name = Column(String(200), nullable=False)
    version = Column(String(40), nullable=False); study_codes = Column(JSON, default=list)
    status = Column(String(30), default="Draft", index=True); effective_at = Column(DateTime)
    definition = Column(JSON, default=dict); supporting_reference = Column(String(255))
    test_status = Column(String(30), default="Not run"); clinical_approved_by = Column(String(255))
    qa_approved_by = Column(String(255)); approved_by = Column(String(255)); supersedes_id = Column(String(36))
    change_reason = Column(Text); is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("resource_type", "code", "version", name="uq_controlled_version"),)


class IntegrationStatus(Base):
    __tablename__ = "admin_integrations"
    id = Column(String(36), primary_key=True, default=uid)
    name = Column(String(100), nullable=False); integration_type = Column(String(60), nullable=False)
    environment = Column(String(30)); status = Column(String(30)); last_success = Column(DateTime)
    last_failure = Column(DateTime); last_transfer = Column(DateTime); config_version = Column(String(30))
    credential_status = Column(String(40)); enabled = Column(Boolean, default=False); is_demo = Column(Boolean, default=False)


class AdminAuditEvent(Base):
    __tablename__ = "admin_audit_events"
    id = Column(String(36), primary_key=True, default=uid)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    actor_upn = Column(String(255), nullable=False); actor_role = Column(String(80), nullable=False)
    portal = Column(String(30), default="ADMIN"); action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(60), nullable=False); entity_id = Column(String(80)); study_code = Column(String(50))
    previous_value = Column(JSON); new_value = Column(JSON); reason = Column(Text, nullable=False)
    session_reference = Column(String(100)); outcome = Column(String(30), default="SUCCESS")
    configuration_version = Column(String(40)); is_demo = Column(Boolean, default=False, index=True)
    record_hash = Column(String(64), nullable=False)


class AccessReview(Base):
    __tablename__ = "admin_access_reviews"
    id = Column(String(36), primary_key=True, default=uid)
    name = Column(String(160), nullable=False); scope_type = Column(String(30)); scope_value = Column(String(80))
    reviewer_upn = Column(String(255)); status = Column(String(30), default="Open")
    due_at = Column(DateTime); completed_at = Column(DateTime); locked = Column(Boolean, default=False)
    decisions = Column(JSON, default=list); is_demo = Column(Boolean, default=False)
