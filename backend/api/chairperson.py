"""
Adjudication Chairperson API — /api/chairperson/*
Handles completed adjudication tracking, committee meeting agenda packs, minutes, attendance, and case closure.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
import uuid

from database import get_db
from models.auth import PortalUser, AuthAuditEvent
from models.admin import AdjudicationActivityLedger
from models.canonical import (
    Participant, AdjudicationVisit, AdjudicationRecord, CommitteeDecision, CommitteeMeeting,
    ReviewerRole, DiagnosisCode, OnsetClass, SeverityGrade, CertaintyLevel, AdjudicationStatus
)
from models.longitudinal import LongitudinalParticipant, VisitInstance
from services.auth_service import require_role, require_chairperson_assignment, ROLE_CHAIRPERSON, ROLE_ADMIN, audit_auth

router = APIRouter()


class MeetingSignOffRequest(BaseModel):
    meeting_title: str = Field(min_length=3)
    batch_id: Optional[str] = None
    attendees: List[str] = Field(min_items=1, description="List of attending committee members")
    quorum_met: bool = True
    minutes: str = Field(min_length=10, description="Comprehensive meeting minutes")
    case_ids: List[str] = Field(description="List of participant subject IDs finalized during this session")
    chair_name: Optional[str] = "Adjudication Chairperson"

class MeetingDelegationRequest(BaseModel):
    meeting_title: str = Field(min_length=3)
    scheduled_at: datetime
    delegate_upn: str = Field(min_length=3)
    case_ids: List[str] = Field(default_factory=list)
    note: str = Field(min_length=5)

@router.post("/meetings/delegate")
def delegate_meeting(req: MeetingDelegationRequest, db: Session = Depends(get_db),
                     user: PortalUser = Depends(require_chairperson_assignment())):
    delegate = db.query(PortalUser).filter_by(email=req.delegate_upn.strip().lower(), status="ACTIVE").first()
    if not delegate or delegate.role not in (ROLE_CHAIRPERSON, "ADJUDICATOR"):
        raise HTTPException(422, "Delegate must be an active chairperson or adjudicator.")
    meeting = CommitteeMeeting(
        meeting_title=req.meeting_title,
        scheduled_at=req.scheduled_at,
        chair_upn=user.email,
        chair_name=user.display_name,
        delegated_to_upn=delegate.email,
        delegated_by_upn=user.email,
        delegation_note=req.note,
        delegated_at=datetime.utcnow(),
        case_ids=req.case_ids,
        attendees=[delegate.email],
        quorum_met=False,
        signed=False,
        status="DELEGATED",
    )
    db.add(meeting)
    db.flush()
    # Delegation is not attendance or chair sign-off. Those ledger facts are
    # recorded only after the meeting actually occurs and is signed.
    db.add(AdjudicationActivityLedger(
        adjudicator_upn=delegate.email, study_code="PROTECT-Africa",
        blinded_case_reference=f"MEETING-{meeting.id}", role_served="DELEGATE_CHAIR",
        event_type="MEETING_DELEGATED", event_at=meeting.delegated_at, billable=False,
        source_record_id=str(meeting.id), idempotency_key=f"MEETING_DELEGATED:{meeting.id}",
    ))
    db.commit()
    return {"status": "delegated", "meeting_id": str(meeting.id), "delegate_upn": delegate.email}


@router.get("/completed-adjudications")
def list_completed_adjudications(
    batch_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user: PortalUser = Depends(require_chairperson_assignment())
):
    """
    Returns one concordance row per visit, including all signed A/B/C determinations.

    Concordance is visit-level. Collapsing records at participant level can pair
    Reviewer A from one visit with Reviewer B from another and hide later visits.
    """
    participants = db.query(Participant).all()
    results = []

    for p in participants:
        visits = (
            db.query(AdjudicationVisit)
            .filter_by(participant_id=p.id)
            .order_by(AdjudicationVisit.visit_number.asc())
            .all()
        )
        for visit in visits:
            records = (
                db.query(AdjudicationRecord)
                .filter_by(visit_id=visit.id, signed=True)
                .all()
            )
            decision = db.query(CommitteeDecision).filter_by(visit_id=visit.id).first()
            by_role = {record.reviewer_role: record for record in records}
            rec_a = by_role.get(ReviewerRole.REVIEWER_A)
            rec_b = by_role.get(ReviewerRole.REVIEWER_B)
            rec_c = by_role.get(ReviewerRole.REVIEWER_C)
            adopted_record = next(
                (record for record in records if visit.final_record_id and record.id == visit.final_record_id),
                None,
            )

            def signature(record):
                return (
                    record.meets_criteria, record.diagnosis, record.onset_class,
                    record.severity, record.certainty, record.date_of_diagnosis,
                )

            if (decision and decision.closed) or p.status == AdjudicationStatus.CLOSED:
                concordance = "CLOSED"
            elif decision and decision.locked:
                concordance = "CHAIR_FINALIZED"
            elif rec_a and rec_b and rec_c:
                if signature(rec_a) == signature(rec_b) == signature(rec_c):
                    concordance = "CONCORDANT_ALL_THREE"
                elif signature(rec_c) in (signature(rec_a), signature(rec_b)):
                    concordance = "RESOLVED_BY_MAJORITY"
                else:
                    concordance = "RESOLVED_BY_REVIEWER_C"
            elif rec_a and rec_b:
                concordance = (
                    "CONCORDANT_A_EQUALS_B"
                    if signature(rec_a) == signature(rec_b)
                    else "DISCORDANT_A_NEQ_B"
                )
            elif rec_a or rec_b:
                concordance = "SINGLE_REVIEWER_COMPLETE"
            else:
                concordance = "PENDING_REVIEW"

            if status_filter and status_filter.upper() != "ALL" and concordance != status_filter.upper():
                continue

            def reviewer_payload(record, include_rationale=False):
                if not record:
                    return None
                payload = {
                    "upn": record.reviewer_upn,
                    "name": record.reviewer_name,
                    "diagnosis": record.diagnosis.value if record.diagnosis else None,
                    "certainty": record.certainty.value if record.certainty else None,
                    "meets_criteria": record.meets_criteria,
                    "onset_class": record.onset_class.value if record.onset_class else None,
                    "severity": record.severity.value if record.severity else None,
                    "date_of_diagnosis": record.date_of_diagnosis.isoformat() if record.date_of_diagnosis else None,
                    "differential_diagnosis": record.differential_diagnosis,
                    "rationale": record.rationale,
                    "signed_at": record.signed_at.isoformat() if record.signed_at else None,
                }
                return payload

            results.append({
                "id": str(visit.id),
                "participant_id": str(p.id),
                "visit_id": str(visit.id),
                "visit_number": visit.visit_number,
                "visit_code": visit.visit_code,
                "visit_date": visit.visit_date.isoformat() if visit.visit_date else None,
                "subject_id": p.subject_id,
                "site_code": p.site_code,
                "study_code": p.study.value if hasattr(p.study, "value") else str(p.study),
                "concordance": concordance,
                "participant_status": p.status.value if hasattr(p.status, "value") else str(p.status),
                "visit_status": visit.status,
                "resolution_type": visit.resolution_type,
                "reviewer_a": reviewer_payload(rec_a),
                "reviewer_b": reviewer_payload(rec_b),
                "reviewer_c": reviewer_payload(rec_c, include_rationale=True),
                "final_outcome": {
                    "diagnosis": decision.final_diagnosis.value if decision.final_diagnosis else None,
                    "adopted_reviewer": decision.adopted_reviewer.value if decision.adopted_reviewer else None,
                    "chair_rationale": decision.chair_rationale,
                    "closed": decision.closed,
                } if decision else ({
                    "diagnosis": adopted_record.diagnosis.value if adopted_record.diagnosis else None,
                    "adopted_reviewer": adopted_record.reviewer_role.value,
                    "chair_rationale": None,
                    "closed": False,
                } if adopted_record else None),
            })

    return {
        "items": results,
        "total": len(results),
        "summary": {
            "concordant": sum(1 for r in results if r["concordance"] in ["CONCORDANT_A_EQUALS_B", "CONCORDANT_ALL_THREE"]),
            "resolved_by_majority": sum(1 for r in results if r["concordance"] == "RESOLVED_BY_MAJORITY"),
            "discordant": sum(1 for r in results if r["concordance"] in ["DISCORDANT_A_NEQ_B", "ESCALATED_TO_C", "THREE_WAY_DIVERGENT", "RESOLVED_BY_MAJORITY", "RESOLVED_BY_REVIEWER_C"]),
            "three_way_divergent": sum(1 for r in results if r["concordance"] == "THREE_WAY_DIVERGENT"),
            "closed": sum(1 for r in results if r["concordance"] == "CLOSED"),
        }
    }


@router.get("/agenda-pack")
def generate_agenda_pack(batch_id: Optional[str] = "DEFAULT_BATCH", db: Session = Depends(get_db),
                        user: PortalUser = Depends(require_chairperson_assignment())):
    """
    Generates structured meeting agenda pack summarizing all completed cases, flagging discordances for discussion.
    """
    completed_res = list_completed_adjudications(batch_id=batch_id, db=db, user=user)
    items = completed_res["items"]

    discordant_items = [i for i in items if i["concordance"] in ["DISCORDANT_A_NEQ_B", "ESCALATED_TO_C", "THREE_WAY_DIVERGENT"]]
    concordant_items = [i for i in items if i["concordance"] == "CONCORDANT_A_EQUALS_B"]

    agenda = {
        "pack_id": f"AGENDA-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}",
        "generated_at": datetime.utcnow().isoformat(),
        "batch_id": batch_id,
        "total_cases": len(items),
        "concordance_rate_pct": round((len(concordant_items) / len(items) * 100) if items else 100.0, 1),
        "items_for_committee_arbitration": discordant_items,
        "concordant_cases_consent_calendar": concordant_items,
        "recommendation": f"Review and arbitrate {len(discordant_items)} discordant case(s). Formalize consent calendar for {len(concordant_items)} concordant case(s)."
    }
    return agenda


from services.etmf_adapter import get_etmf_adapter
from models.canonical import AuditEvent


@router.post("/meetings/sign-off")
def sign_off_meeting(req: MeetingSignOffRequest, request: Request, db: Session = Depends(get_db),
                    user: PortalUser = Depends(require_chairperson_assignment())):
    """
    Captures committee meeting minutes, attendee roster, computes chair e-signature,
    marks cases as CLOSED, generates formal meeting report, and writes to eTMF.
    """
    chair_upn = user.email
    now_dt = datetime.utcnow()
    raw_sig = f"MEETING|{req.meeting_title}|{chair_upn}|{now_dt.isoformat()}|{len(req.case_ids)}"
    sig_hash = hashlib.sha256(raw_sig.encode()).hexdigest()

    meeting = CommitteeMeeting(
        meeting_title=req.meeting_title,
        batch_id=req.batch_id,
        chair_upn=chair_upn,
        chair_name=req.chair_name,
        attendees=req.attendees,
        quorum_met=req.quorum_met,
        minutes=req.minutes,
        case_ids=req.case_ids,
        signed=True,
        signed_at=now_dt,
        signature_hash=sig_hash,
        status="CLOSED"
    )
    db.add(meeting)

    # Mark all involved participant cases as CLOSED
    closed_cases_info = []
    for cid in req.case_ids:
        p = db.query(Participant).filter(
            (Participant.subject_id == cid) |
            (Participant.case_number == cid)
        ).first()
        if not p:
            try:
                p = db.query(Participant).filter_by(id=uuid.UUID(cid)).first()
            except Exception:
                p = None
        if p:
            p.status = AdjudicationStatus.CLOSED
            dec = db.query(CommitteeDecision).filter_by(participant_id=p.id).first()
            if dec:
                dec.closed = True
                dec.closed_at = now_dt
                dec.meeting_id = str(meeting.id)
            closed_cases_info.append({
                "subject_id": p.subject_id,
                "case_number": p.case_number,
                "final_diagnosis": dec.final_diagnosis.value if dec and dec.final_diagnosis else "CONCORDANT_CLOSED",
            })

    # Generate structured meeting report artifact
    report_content = (
        f"ACRN ENDPOINT ADJUDICATION COMMITTEE — FORMAL MEETING REPORT\n"
        f"{'='*65}\n"
        f"Meeting Title:   {req.meeting_title}\n"
        f"Batch ID:        {req.batch_id or 'N/A'}\n"
        f"Chairperson:     {req.chair_name} ({chair_upn})\n"
        f"Date & Time:     {now_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"Quorum Met:      {'YES' if req.quorum_met else 'NO'}\n"
        f"Attendees:       {', '.join(req.attendees)}\n"
        f"Signature Hash:  {sig_hash}\n\n"
        f"MEETING MINUTES:\n"
        f"{'-'*65}\n"
        f"{req.minutes}\n\n"
        f"ARBITRATED & FINALIZED CASES ({len(closed_cases_info)}):\n"
        f"{'-'*65}\n"
    )
    for c in closed_cases_info:
        report_content += f" • Case: {c['case_number']} | Final Outcome: {c['final_diagnosis']}\n"

    report_bytes = report_content.encode("utf-8")

    # Write to eTMF
    etmf_dest = None
    try:
        adapter = get_etmf_adapter()
        etmf_dest = adapter.write_meeting_report(
            meeting_id=str(meeting.id),
            meeting_title=req.meeting_title,
            study="PROTECT-Africa",
            report_bytes=report_bytes,
            timestamp=now_dt,
        )
    except Exception as exc:
        etmf_dest = f"eTMF write error: {exc}"

    # Write audit log
    db.add(AuditEvent(
        event_type="COMMITTEE_MEETING_SIGNED",
        actor_upn=chair_upn,
        actor_role="CHAIRPERSON",
        description=f"Committee meeting '{req.meeting_title}' signed by chair. {len(closed_cases_info)} cases closed.",
        event_metadata={
            "meeting_id": str(meeting.id),
            "meeting_title": req.meeting_title,
            "signature_hash": sig_hash,
            "closed_cases_count": len(closed_cases_info),
            "etmf_destination": etmf_dest,
        },
        timestamp=now_dt,
    ))

    db.commit()

    return {
        "status": "success",
        "meeting_id": str(meeting.id),
        "meeting_title": req.meeting_title,
        "signature_hash": sig_hash,
        "closed_cases_count": len(req.case_ids),
        "signed_at": meeting.signed_at.isoformat(),
        "etmf_destination": etmf_dest,
    }


@router.get("/meetings/{meeting_id}/report")
def get_meeting_report(
    meeting_id: str,
    db: Session = Depends(get_db),
    user: PortalUser = Depends(require_chairperson_assignment()),
):
    """Returns structured meeting summary report for an archived committee meeting."""
    meeting = None
    try:
        m_uuid = uuid.UUID(meeting_id)
        meeting = db.query(CommitteeMeeting).filter_by(id=m_uuid).first()
    except Exception:
        pass
    if not meeting:
        try:
            meeting = db.query(CommitteeMeeting).filter_by(id=meeting_id).first()
        except Exception:
            meeting = None

    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found.")


    return {
        "meeting_id": str(meeting.id),
        "meeting_title": meeting.meeting_title,
        "batch_id": meeting.batch_id,
        "chair_name": meeting.chair_name,
        "chair_upn": meeting.chair_upn,
        "attendees": meeting.attendees,
        "quorum_met": meeting.quorum_met,
        "minutes": meeting.minutes,
        "case_count": len(meeting.case_ids or []),
        "case_ids": meeting.case_ids,
        "signed_at": meeting.signed_at.isoformat() if meeting.signed_at else None,
        "signature_hash": meeting.signature_hash,
        "status": meeting.status,
    }


@router.get("/meetings")
def list_meetings(db: Session = Depends(get_db), user: PortalUser = Depends(require_chairperson_assignment())):
    rows = db.query(CommitteeMeeting).order_by(CommitteeMeeting.created_at.desc()).all()
    return {
        "items": [
            {
                "id": str(m.id),
                "title": m.meeting_title,
                "batch_id": m.batch_id,
                "chair_name": m.chair_name,
                "chair_upn": m.chair_upn,
                "attendees": m.attendees,
                "quorum_met": m.quorum_met,
                "minutes": m.minutes,
                "case_count": len(m.case_ids or []),
                "case_ids": m.case_ids,
                "signed_at": m.signed_at.isoformat() if m.signed_at else None,
                "signature_hash": m.signature_hash,
                "status": m.status
                ,"delegated_to_upn": m.delegated_to_upn
                ,"scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None
            }
            for m in rows
        ]
    }
