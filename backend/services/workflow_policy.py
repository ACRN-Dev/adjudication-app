"""
ACRN PROTECT-Africa Adjudication Platform
Workflow Policy & Dual-Reviewer Isolation Engine
================================================

Standards: ICH E6(R2) GCP | 21 CFR Part 11 | EU Annex 11 | GAMP 5
SOPs: SOP-ADJ-001 (Committee Charter), SOP-ADJ-002 (Blinding & Workflow Rules)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


class WorkflowState(str, Enum):
    PENDING = "PENDING"
    QA_REVIEW = "QA_REVIEW"
    QA_RELEASED = "QA_RELEASED"
    REVIEWER_A_SUBMITTED = "REVIEWER_A_SUBMITTED"
    REVIEWER_B_SUBMITTED = "REVIEWER_B_SUBMITTED"
    CONCORDANT = "CONCORDANT"
    DISCORDANT = "DISCORDANT"
    COMMITTEE_PENDING = "COMMITTEE_PENDING"
    FINALIZED = "FINALIZED"
    LOCKED = "LOCKED"


@dataclass
class WorkflowGateResult:
    allowed: bool
    reason: str
    next_state: Optional[WorkflowState] = None


def check_qa_release_gate(current_status: str, qa_cleared: bool) -> WorkflowGateResult:
    """QA must release packet before adjudication can begin."""
    if not qa_cleared:
        return WorkflowGateResult(
            allowed=False,
            reason="QA Gate: Evidence packet has not been cleared by Data Management/QA."
        )
    return WorkflowGateResult(
        allowed=True,
        reason="QA Gate cleared. Packet released for dual-reviewer adjudication.",
        next_state=WorkflowState.QA_RELEASED
    )


def check_reviewer_gate(current_status: str, reviewer_role: str, existing_submissions: List[Dict[str, Any]]) -> WorkflowGateResult:
    """Check if reviewer is allowed to submit."""
    has_sub = any(s.get("reviewer_role") == reviewer_role for s in existing_submissions)
    if has_sub:
        return WorkflowGateResult(
            allowed=False,
            reason=f"Reviewer {reviewer_role} has already submitted an adjudication for this case."
        )
    
    return WorkflowGateResult(
        allowed=True,
        reason=f"Reviewer {reviewer_role} permitted to submit adjudication.",
        next_state=WorkflowState.REVIEWER_A_SUBMITTED if reviewer_role == "REVIEWER_A" else WorkflowState.REVIEWER_B_SUBMITTED
    )


def check_reviewer_isolation(requesting_reviewer: str, target_reviewer: str, current_state: str) -> bool:
    """
    Reviewer A submits first; Reviewer B cannot see A's submission until B has also submitted.
    Returns True (can see target's submission) only if both submitted or case is in committee/finalized.
    """
    if requesting_reviewer == target_reviewer:
        return True
    
    state_str = str(current_state).upper()
    unblinded_states = [
        WorkflowState.CONCORDANT.value,
        WorkflowState.DISCORDANT.value,
        WorkflowState.COMMITTEE_PENDING.value,
        WorkflowState.FINALIZED.value,
        WorkflowState.LOCKED.value,
    ]
    return state_str in unblinded_states


def check_committee_quorum(members_present: int, required_quorum: int = 3) -> WorkflowGateResult:
    """Committee review requires minimum quorum (default: 3 members)."""
    if members_present < required_quorum:
        return WorkflowGateResult(
            allowed=False,
            reason=f"Quorum check failed: {members_present} members present (minimum required: {required_quorum})."
        )
    return WorkflowGateResult(
        allowed=True,
        reason=f"Quorum satisfied ({members_present}/{required_quorum} members present)."
    )


def check_transfer_authority(actor_role: str, target_state: WorkflowState) -> WorkflowGateResult:
    """Check if actor has administrative/governance authority for transition."""
    role = (actor_role or "").upper()
    
    if target_state in (WorkflowState.FINALIZED, WorkflowState.LOCKED):
        if role not in ("CHAIR", "CO_CHAIR", "SYSTEM_ADMIN"):
            return WorkflowGateResult(
                allowed=False,
                reason="Governance Authority: Only the Committee Chair or Co-Chair can lock a final adjudication record."
            )

    if target_state == WorkflowState.QA_RELEASED:
        if role not in ("QA", "DATA_MANAGER", "SYSTEM_ADMIN"):
            return WorkflowGateResult(
                allowed=False,
                reason="Governance Authority: Only QA/Data Management can release packets for adjudication."
            )

    return WorkflowGateResult(allowed=True, reason="Authority verified.")


def check_signing_gate(password_confirmed: bool) -> WorkflowGateResult:
    """
    Signature verification gate.
    NOTE: In this prototype, electronic signature records intent and creates a cryptographic audit trail hash.
    For full 21 CFR Part 11 compliance in production, dual-factor authentication and PKI hardware token signing are required.
    """
    if not password_confirmed:
        return WorkflowGateResult(
            allowed=False,
            reason="Signature Gate: Password re-authentication required before signing."
        )
    return WorkflowGateResult(
        allowed=True,
        reason="Signature authentication verified. Cryptographic audit entry generated."
    )


def evaluate_concordance(sub_a: Dict[str, Any], sub_b: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate concordance between Reviewer A and Reviewer B submissions."""
    fields = ["primary_diagnosis", "onset_classification", "severity_phenotype", "certainty_level"]
    discordant_fields = []

    for f in fields:
        val_a = str(sub_a.get(f, "")).strip().lower()
        val_b = str(sub_b.get(f, "")).strip().lower()
        if val_a != val_b:
            discordant_fields.append({
                "field": f,
                "reviewer_a": sub_a.get(f),
                "reviewer_b": sub_b.get(f),
            })

    concordant = len(discordant_fields) == 0

    return {
        "concordant": concordant,
        "fields_compared": fields,
        "discordant_fields": discordant_fields,
        "recommended_state": WorkflowState.CONCORDANT if concordant else WorkflowState.DISCORDANT
    }
