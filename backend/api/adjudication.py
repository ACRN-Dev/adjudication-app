"""
Adjudication API — Dual Blinded Reviewer Submissions (A/B)
==========================================================
Enforces:
  - Server-side credential re-verification (21 CFR Part 11 §11.200)
  - Blinding: Reviewer A cannot view Reviewer B's submission until both have signed
  - Immutability: a signed record cannot be re-submitted
  - Adjudicator stickiness: assigned Reviewer A/B holds all visits 1..N of a subject
  - Mandatory date_of_diagnosis: required at the visit where diagnosis is made
  - Audit trail: every signature writes an AuditEvent
  - Pseudonymisation: adjudicators receive the blinded case ID, NOT the true subject_id
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import hashlib
import random

from database import get_db
from models.canonical import (
    Participant, AdjudicationRecord, SubjectAssignment, AuditEvent,
    ReviewerRole, DiagnosisCode, OnsetClass, SeverityGrade, CertaintyLevel,
    AdjudicationStatus, StudyCode,
)
from models.auth import PortalUser
from models.longitudinal import LongitudinalParticipant, ReviewerAssignment
from services.auth_service import verify_password

router = APIRouter()


def _audit(db: Session, event_type: str, participant_id, actor_upn: str,
           actor_role: str, description: str, metadata: dict | None = None):
    db.add(AuditEvent(
        event_type=event_type,
        participant_id=participant_id,
        actor_upn=actor_upn,
        actor_role=actor_role,
        description=description,
        event_metadata=metadata or {},
        timestamp=datetime.utcnow(),
    ))


class ReviewerSubmission(BaseModel):
    reviewer_role: ReviewerRole
    reviewer_upn: str = Field(min_length=3)
    reviewer_name: str
    reviewer_password: str = Field(
        min_length=1,
        description="Reviewer's actual password for 21 CFR Part 11 re-authentication"
    )
    visit_number: int = Field(default=1, ge=1, le=10)
    meets_criteria: bool
    diagnosis: DiagnosisCode
    date_of_diagnosis: Optional[datetime] = None
    onset_class: OnsetClass
    severity: SeverityGrade
    certainty: CertaintyLevel
    differential_diagnosis: Optional[str] = None
    rationale: str = Field(min_length=10)


@router.post("/{subject_id}/submit")
def submit_adjudication(
    subject_id: str,
    sub: ReviewerSubmission,
    db: Session = Depends(get_db),
):
    """
    Submit a blinded adjudication determination for a specific visit.
    subject_id is the BLINDED case reference (e.g. ADJ-E2E-001).
    """
    # ── 1. Locate participant by blinded case_number ──────────────────────────
    participant = (
        db.query(Participant)
        .filter(
            (Participant.case_number == subject_id) |
            (Participant.subject_id == subject_id)
        )
        .first()
    )
    if not participant:
        realtime_case = db.query(LongitudinalParticipant).filter_by(blinded_subject_id=subject_id).first()
        if not realtime_case:
            raise HTTPException(status_code=404, detail=f"Case {subject_id} not found.")
        study = StudyCode.EOPE
        if str(realtime_case.study).upper().startswith("LOPE"):
            study = StudyCode.LOPE
        participant = Participant(
            subject_id=realtime_case.blinded_subject_id,
            case_number=realtime_case.blinded_subject_id,
            site_code=realtime_case.site_code,
            study=study,
            status=AdjudicationStatus.IN_REVIEW,
            qc_approved=True,
            visit_count=realtime_case.available_visit_count or 0,
        )
        db.add(participant)
        db.flush()
        rt_assignments = db.query(ReviewerAssignment).filter_by(participant_id=realtime_case.id, status="ASSIGNED").all()
        assignment_map = {a.reviewer_role: a.reviewer_upn.strip().lower() for a in rt_assignments}
        if assignment_map.get("REVIEWER_A") and assignment_map.get("REVIEWER_B"):
            db.add(SubjectAssignment(
                participant_id=participant.id,
                reviewer_a_upn=assignment_map["REVIEWER_A"],
                reviewer_b_upn=assignment_map["REVIEWER_B"],
                status="ACTIVE",
                assigned_by="REALTIME_BRIDGE",
            ))
            db.flush()

    # ── 2. Server-side credential re-verification (21 CFR Part 11 §11.200) ───
    sub_upn = sub.reviewer_upn.strip().lower()
    reviewer_user = (
        db.query(PortalUser)
        .filter_by(email=sub_upn)
        .first()
    )
    if not reviewer_user:
        _audit(db, "SIGN_REJECTED", participant.id, sub.reviewer_upn, "ADJUDICATOR",
               "Signature rejected: unknown reviewer UPN", {"reason": "user_not_found"})
        db.commit()
        raise HTTPException(status_code=401,
                            detail="Invalid credentials. Signature rejected (21 CFR Part 11).")
    if not reviewer_user.password_hash or not verify_password(
        sub.reviewer_password, reviewer_user.password_hash
    ):
        _audit(db, "SIGN_REJECTED", participant.id, sub.reviewer_upn, "ADJUDICATOR",
               "Signature rejected: incorrect password", {"reason": "wrong_password"})
        db.commit()
        raise HTTPException(status_code=401,
                            detail="Invalid credentials. Signature rejected (21 CFR Part 11).")

    # ── 3. Adjudicator Stickiness Enforcement ────────────────────────────────
    assignment = (
        db.query(SubjectAssignment)
        .filter_by(participant_id=participant.id, status="ACTIVE")
        .first()
    )
    if assignment:
        assigned_a = assignment.reviewer_a_upn.strip().lower() if assignment.reviewer_a_upn else None
        assigned_b = assignment.reviewer_b_upn.strip().lower() if assignment.reviewer_b_upn else None
        assigned_c = assignment.reviewer_c_upn.strip().lower() if assignment.reviewer_c_upn else None

        if sub_upn == assigned_a:
            sub.reviewer_role = ReviewerRole.REVIEWER_A
        elif sub_upn == assigned_b:
            sub.reviewer_role = ReviewerRole.REVIEWER_B
        elif sub_upn == assigned_c:
            sub.reviewer_role = ReviewerRole.REVIEWER_C
        elif sub.reviewer_role == ReviewerRole.REVIEWER_A and assigned_a and sub_upn != assigned_a:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Reviewer {sub.reviewer_upn} is not assigned as Reviewer A for case {subject_id} "
                    f"(Assigned: {assignment.reviewer_a_upn}). Adjudicator stickiness violated."
                ),
            )
        elif sub.reviewer_role == ReviewerRole.REVIEWER_B and assigned_b and sub_upn != assigned_b:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Reviewer {sub.reviewer_upn} is not assigned as Reviewer B for case {subject_id} "
                    f"(Assigned: {assignment.reviewer_b_upn}). Adjudicator stickiness violated."
                ),
            )
        elif sub.reviewer_role == ReviewerRole.REVIEWER_C:
            if not assigned_c:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"No Reviewer C has been assigned to case {subject_id} yet. "
                        "Reviewer C is only assigned automatically after A/B discordance is detected."
                    ),
                )
            if sub_upn != assigned_c:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Reviewer {sub.reviewer_upn} is not assigned as Reviewer C for case {subject_id} "
                        f"(Assigned: {assignment.reviewer_c_upn}). Adjudicator stickiness violated."
                    ),
                )
        else:
            raise HTTPException(
                status_code=403,
                detail=f"Reviewer {sub.reviewer_upn} is not assigned to case {subject_id}. Adjudicator stickiness violated.",
            )
    elif sub.reviewer_role == ReviewerRole.REVIEWER_C:
        # No assignment row at all — C cannot submit without prior A/B discordance
        raise HTTPException(
            status_code=409,
            detail=(
                f"Case {subject_id} has no active assignment record. "
                "Reviewer C submission requires a prior discordant A/B review."
            ),
        )

    # ── 4. Visit-Level Completeness Gating & Mandatory date_of_diagnosis ─
    if sub.diagnosis != DiagnosisCode.NOT_PE and sub.meets_criteria:
        if not sub.date_of_diagnosis:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"date_of_diagnosis is mandatory when diagnosing {sub.diagnosis.value}. "
                    "The exact date and visit are required to link with biomarker assay collection dates."
                ),
            )

        now_utc = datetime.utcnow()
        # Hardened check 1: Date cannot be in the future
        if sub.date_of_diagnosis > now_utc:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"date_of_diagnosis {sub.date_of_diagnosis.isoformat()} cannot be in the future. "
                    f"Current UTC time is {now_utc.isoformat()}."
                ),
            )

        # Hardened check 2: Plausible clinical study timeframe
        if sub.date_of_diagnosis.year < 2020:
            raise HTTPException(
                status_code=422,
                detail=f"date_of_diagnosis {sub.date_of_diagnosis.isoformat()} precedes the study period."
            )

        # Hardened check 3: Cross-visit consistency
        prior_records = (
            db.query(AdjudicationRecord)
            .filter(
                AdjudicationRecord.participant_id == participant.id,
                AdjudicationRecord.reviewer_role == sub.reviewer_role,
                AdjudicationRecord.visit_number < sub.visit_number,
                AdjudicationRecord.date_of_diagnosis != None,
            )
            .order_by(AdjudicationRecord.visit_number.asc())
            .all()
        )
        for pr in prior_records:
            if pr.date_of_diagnosis and sub.date_of_diagnosis < pr.date_of_diagnosis:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"date_of_diagnosis ({sub.date_of_diagnosis.isoformat()}) at visit {sub.visit_number} "
                        f"cannot precede the established diagnosis date ({pr.date_of_diagnosis.isoformat()}) "
                        f"from visit {pr.visit_number}."
                    ),
                )

    # Hardened check 4: Definite certainty requires full diagnostic criteria and evidence sufficiency
    if sub.certainty == CertaintyLevel.DEFINITE:
        if not sub.meets_criteria or not sub.rationale or len(sub.rationale.strip()) < 10:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Definite certainty requires complete visit diagnostic criteria (meets_criteria=True) "
                    "and full supporting clinical documentation. Use PROBABLE or POSSIBLE if data is partial."
                ),
            )


    # ── 5. Immutability Check ────────────────────────────────────────────────
    existing = (
        db.query(AdjudicationRecord)
        .filter_by(
            participant_id=participant.id,
            reviewer_role=sub.reviewer_role,
            visit_number=sub.visit_number,
        )
        .first()
    )
    if existing and existing.signed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A signed record for {sub.reviewer_role.value} visit {sub.visit_number} "
                f"on case {subject_id} already exists and is immutable."
            ),
        )

    # ── 6. Generate e-signature hash (SHA-256, 21 CFR Part 11) ───────────────
    raw_sig = (
        f"{subject_id}|{sub.reviewer_upn}|{sub.reviewer_role.value}|"
        f"{sub.diagnosis.value}|{sub.visit_number}|"
        f"{sub.date_of_diagnosis.isoformat() if sub.date_of_diagnosis else ''}|"
        f"{datetime.utcnow().isoformat()}"
    )
    sig_hash = hashlib.sha256(raw_sig.encode()).hexdigest()

    # ── 7. Persist Adjudication Record ───────────────────────────────────────
    if existing:
        rec = existing
    else:
        rec = AdjudicationRecord(
            participant_id=participant.id,
            reviewer_role=sub.reviewer_role,
            reviewer_upn=sub.reviewer_upn,
            reviewer_name=sub.reviewer_name,
            visit_number=sub.visit_number,
        )
        db.add(rec)

    rec.meets_criteria = sub.meets_criteria
    rec.diagnosis = sub.diagnosis
    rec.date_of_diagnosis = sub.date_of_diagnosis
    rec.onset_class = sub.onset_class
    rec.severity = sub.severity
    rec.certainty = sub.certainty
    rec.differential_diagnosis = sub.differential_diagnosis
    rec.rationale = sub.rationale
    rec.signed = True
    rec.signed_at = datetime.utcnow()
    rec.signature_hash = sig_hash
    rec.mfa_verified = True
    rec.submitted_at = datetime.utcnow()

    db.flush()

    # ── 8. Audit Event ───────────────────────────────────────────────────────
    _audit(
        db, "ADJUDICATION_SIGNED", participant.id,
        sub.reviewer_upn, "ADJUDICATOR",
        f"{sub.reviewer_role.value} signed visit {sub.visit_number}; "
        f"diagnosis={sub.diagnosis.value}; certainty={sub.certainty.value}; "
        f"date_of_diagnosis={sub.date_of_diagnosis.isoformat() if sub.date_of_diagnosis else 'N/A'}",
        {
            "reviewer_role": sub.reviewer_role.value,
            "visit_number": sub.visit_number,
            "diagnosis": sub.diagnosis.value,
            "date_of_diagnosis": sub.date_of_diagnosis.isoformat() if sub.date_of_diagnosis else None,
            "certainty": sub.certainty.value,
            "signature_hash": sig_hash,
        },
    )

    # ── 9. Concordance check ─────────────────────────────────────────────────
    visit_records = (
        db.query(AdjudicationRecord)
        .filter_by(participant_id=participant.id, visit_number=sub.visit_number, signed=True)
        .all()
    )
    rev_a = next((r for r in visit_records if r.reviewer_role == ReviewerRole.REVIEWER_A), None)
    rev_b = next((r for r in visit_records if r.reviewer_role == ReviewerRole.REVIEWER_B), None)
    rev_c = next((r for r in visit_records if r.reviewer_role == ReviewerRole.REVIEWER_C), None)

    if rev_a and rev_b and rev_c:
        # ── Three-reviewer resolution (Reviewer C has now submitted) ─────────
        diag_a = rev_a.diagnosis
        diag_b = rev_b.diagnosis
        diag_c = rev_c.diagnosis
        onset_a = rev_a.onset_class
        onset_b = rev_b.onset_class
        onset_c = rev_c.onset_class
        criteria_a = rev_a.meets_criteria
        criteria_b = rev_b.meets_criteria
        criteria_c = rev_c.meets_criteria

        # C agrees with A
        c_agrees_a = (diag_c == diag_a and onset_c == onset_a and criteria_c == criteria_a)
        # C agrees with B
        c_agrees_b = (diag_c == diag_b and onset_c == onset_b and criteria_c == criteria_b)
        # All three agree
        all_agree = (diag_a == diag_b == diag_c and onset_a == onset_b == onset_c
                     and criteria_a == criteria_b == criteria_c)

        if all_agree:
            participant.status = AdjudicationStatus.CONCORDANT
            resolution = "CONCORDANT_ALL_THREE"
        elif c_agrees_a or c_agrees_b:
            participant.status = AdjudicationStatus.RESOLVED_BY_MAJORITY
            resolution = "RESOLVED_BY_MAJORITY"
        else:
            participant.status = AdjudicationStatus.THREE_WAY_DIVERGENT
            resolution = "THREE_WAY_DIVERGENT"

        _audit(
            db, "REVIEWER_C_OUTCOME_RESOLVED", participant.id,
            sub.reviewer_upn, "ADJUDICATOR",
            f"Three-reviewer outcome: {resolution} (visit {sub.visit_number})",
            {
                "resolution": resolution,
                "diag_a": diag_a.value if diag_a else None,
                "diag_b": diag_b.value if diag_b else None,
                "diag_c": diag_c.value if diag_c else None,
                "visit_number": sub.visit_number,
            },
        )

    elif rev_a and rev_b:
        # ── Two-reviewer A/B check (C not yet submitted) ──────────────────────
        is_concordant = (
            rev_a.diagnosis == rev_b.diagnosis and
            rev_a.onset_class == rev_b.onset_class and
            rev_a.meets_criteria == rev_b.meets_criteria
        )
        if is_concordant:
            participant.status = AdjudicationStatus.CONCORDANT
        else:
            participant.status = AdjudicationStatus.COMMITTEE_PENDING
            if assignment and not assignment.reviewer_c_upn:
                excluded = {assigned_a, assigned_b}
                eligible_reviewers = [
                    user.email for user in db.query(PortalUser)
                    .filter_by(role="ADJUDICATOR", status="ACTIVE")
                    .all()
                    if user.email.strip().lower() not in excluded
                ]
                if not eligible_reviewers:
                    raise HTTPException(
                        status_code=409,
                        detail="Discordant case requires Reviewer C, but no independent adjudicator is available.",
                    )
                assignment.reviewer_c_upn = random.choice(sorted(eligible_reviewers))
                _audit(
                    db, "REVIEWER_C_ASSIGNED", participant.id, "SYSTEM", "SYSTEM",
                    f"Discordance detected; Reviewer C assigned to {assignment.reviewer_c_upn}",
                    {"reviewer_a": assigned_a, "reviewer_b": assigned_b,
                     "reviewer_c": assignment.reviewer_c_upn},
                )
        _audit(
            db, "CONCORDANCE_CHECKED", participant.id,
            sub.reviewer_upn, "ADJUDICATOR",
            f"Concordance result: {'CONCORDANT' if is_concordant else 'DISCORDANT'} "
            f"(visit {sub.visit_number})",
            {"concordant": is_concordant, "visit_number": sub.visit_number},
        )


    db.commit()

    return {
        "status": "success",
        "case_reference": subject_id,
        "reviewer_role": sub.reviewer_role,
        "visit_number": sub.visit_number,
        "signature_hash": sig_hash,
        "signed_at": rec.signed_at.isoformat(),
        "date_of_diagnosis": rec.date_of_diagnosis.isoformat() if rec.date_of_diagnosis else None,
        "participant_status": participant.status.value,
    }


@router.get("/{subject_id}")
def get_adjudication_status(
    subject_id: str,
    requesting_upn: str,
    db: Session = Depends(get_db),
):
    """
    Returns case status and visible records.
    Blinding rule: a reviewer can ONLY see their own submission unless the case is
    DISCORDANT / COMMITTEE_PENDING / THREE_WAY_DIVERGENT / FINALIZED / CLOSED.
    The true subject_id is NEVER returned — only the case_number (blinded reference).
    """
    participant = (
        db.query(Participant)
        .filter(
            (Participant.case_number == subject_id) |
            (Participant.subject_id == subject_id)
        )
        .first()
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Case not found.")

    records = (
        db.query(AdjudicationRecord)
        .filter_by(participant_id=participant.id)
        .all()
    )

    is_committee_phase = participant.status in (
        AdjudicationStatus.DISCORDANT,
        AdjudicationStatus.FINALIZED,
        AdjudicationStatus.COMMITTEE_PENDING,
        AdjudicationStatus.THREE_WAY_DIVERGENT,
        AdjudicationStatus.CLOSED,
    )

    visible_records = []
    for r in records:
        if is_committee_phase or r.reviewer_upn == requesting_upn:
            visible_records.append({
                "reviewer_role": r.reviewer_role.value,
                "reviewer_name": r.reviewer_name,
                "visit_number": r.visit_number,
                "diagnosis": r.diagnosis.value if r.diagnosis else None,
                "onset_class": r.onset_class.value if r.onset_class else None,
                "severity": r.severity.value if r.severity else None,
                "certainty": r.certainty.value if r.certainty else None,
                "date_of_diagnosis": r.date_of_diagnosis.isoformat() if r.date_of_diagnosis else None,
                "rationale": r.rationale,
                "signed_at": r.signed_at.isoformat() if r.signed_at else None,
                "signature_hash": r.signature_hash,
            })

    return {
        "case_reference": participant.case_number,
        "status": participant.status.value,
        "records": visible_records,
        "is_committee_phase": is_committee_phase,
        "visit_count": participant.visit_count,
    }

