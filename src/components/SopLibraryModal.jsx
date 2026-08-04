import React, { useState } from 'react';
import { X, BookOpen, ShieldCheck, FileText, CheckCircle2, Lock, Award, ClipboardList } from 'lucide-react';

const SOP_DOCUMENTS = {
  AGENT_SOP: {
    title: "ACRN AI Adjudication Agent Master Specification",
    code: "SPEC-AI-001 v1.0",
    scope: "PROTECT-Africa (EOPE) & LOPE-Nigeria (LOPE)",
    content: `0. Scope and Governance Boundary (NON-NEGOTIABLE)
The OAC's adjudicated classifications are the clinical reference standard under GCP produced by an independent panel of physicians.

The AI agent is designed strictly as an operational and decision-support tool, NOT an autonomous adjudicator.

NON-NEGOTIABLE RULES:
1. The agent must NEVER be the adjudicator of record.
2. It does not cast votes, count toward quorum, resolve discordance, break ties, sign off, or self-unblind.
3. Two independent human classifications and Chair sign-off remain mandatory.
4. Biomarker/POC results (sFlt-1/PlGF, sEng) are strictly withheld until database lock.
5. The agent provides advisory decision-support drafts with source citations only.

1. Mandatory Source Hierarchy
   Primary authority: EDC (Oracle Clinical One) system of record.
   Supplement only: eSource (Castor / GCP-Sense vitals) when EDC field is absent and charter permits.
   eSource narrative may supplement context but MUST NOT silently overwrite EDC values.
   All discrepancies between EDC and eSource must be displayed to the adjudicator.

2. Blinding Architecture
   sFlt-1/PlGF ratio, sEng, and all POC biomarker outputs are programmatically withheld.
   FORM-ADJ-01 pre-release QC check must be executed and logged before any package release.`
  },
  OAC_CHARTER: {
    title: "Independent OAC Charter v2.0",
    code: "OAC Charter v2.0",
    scope: "PROTECT-Africa & LOPE-Nigeria — All Endpoint Adjudication",
    content: `§1. Purpose and Independence
The Outcomes Adjudication Committee (OAC) is an independent body that provides blinded, unbiased adjudication of primary and key secondary endpoints for PROTECT-Africa (EOPE) and LOPE-Nigeria (LOPE).

§5. Membership and Conflict of Interest
§5.2 Study Separation: Adjudicators must never be able to access biomarker or POC results. Studies must never be intermingled.
§5.3 Site Recusal: A member must not adjudicate a case from a site where they are an investigator or provided clinical care (see FORM-ADJ-08, SOP-ADJ-003).

§7. Adjudication Workflow
§7.3 Blinding: Biomarker outputs (sFlt-1/PlGF) withheld until database lock per SOP-ADJ-002.
§7.4 Discordance: Cases where Reviewer A and B disagree on primary endpoint are routed to Committee Consensus (SOP-ADJ-001).

§8. Quorum
A minimum of 3 of 5 voting members must be present for Committee sessions. A recused member does not count toward quorum for that case.

§10. Sign-Off and Filing
§10.3 Chair Sign-Off: Final adjudication outcome is signed by the OAC Chair via a 21 CFR Part 11-compliant electronic signature (validated e-signature service). The signed record carries signer identity, meaning of signature, and secure timestamp.`
  },
  SOP_001: {
    title: "SOP-ADJ-001: Adjudication Process, Case Selection & Concordance",
    code: "SOP-ADJ-001 v1.0",
    scope: "Case Selection, Dual Review & Concordance Management",
    content: `1. Purpose & Principles:
To define the end-to-end operational pipeline for selecting, packaging, assigning, adjudicating, and reconciling clinical endpoints.

2. Dual Independent Review:
- Every primary endpoint case is reviewed independently by two voting members.
- Reviewers are blinded to each other's submissions until concordance is established.
- Concordant cases are locked automatically.
- Discordant cases are routed to the Committee Consensus Queue for Chair arbitration.

3. Adjudication Trigger Criteria (PROTECT-Africa):
- DV-30: BP ≥ 140/90 mmHg on ≥ 2 occasions ≥ 4 hours apart at any visit after 20+0 weeks.
- DV-31: Any maternal SAE (eclampsia, HELLP, abruption, pulmonary edema).
- DV-32: EFW < 10th centile with abnormal Doppler flow at any assessment.
- DV-33: Preterm birth < 37 weeks with documented obstetric indication.

4. Case Packaging:
- Coordinator prepares blinded case package (E12 library, SharePoint).
- FORM-ADJ-01 blinding check completed before release.
- Package includes: EDC vitals, LIMS results, ultrasound reports, delivery records.
- Biomarker outputs (sFlt-1/PlGF) removed per SOP-ADJ-002.`
  },
  SOP_002: {
    title: "SOP-ADJ-002: Blinding Integrity & Unblinding Incident Management",
    code: "SOP-ADJ-002 v1.0",
    scope: "Blinding Protection & Unblinding Incident Containment",
    content: `1. Purpose:
To protect the blinding on which the OAC's reference standard depends.

2. Withheld Content (MANDATORY — NON-NEGOTIABLE):
- All sFlt-1/PlGF, sEng, and Point-of-Care (POC) biomarker outputs are strictly withheld from adjudicators until database lock.
- Applies at all stages: case preparation, package review, adjudication form submission, narrative editing.
- DLP rules are programmed to detect and block any file containing biomarker terms.

3. Pre-Release Check (FORM-ADJ-01):
- Executed and logged by Coordinator before every case package release.
- Checks: No biomarker fields present, study cross-contamination absent, correct participant ID.
- Failed checks trigger a hold — case not released until remediation is complete.

4. Unblinding Incidents (FORM-ADJ-09):
- Any exposure to biomarker values must be logged within 24 hours via FORM-ADJ-09.
- Affected reviewers are recused and replaced per SOP-ADJ-003.
- Incident escalated to QA and study sponsor.
- Case re-adjudicated by unaffected reviewers.`
  },
  SOP_003: {
    title: "SOP-ADJ-003: Conflict of Interest, Recusal & Committee Independence",
    code: "SOP-ADJ-003 v1.0",
    scope: "COI Declarations & Site Recusals (FORM-ADJ-08)",
    content: `1. Purpose:
To preserve the independence of the OAC and prevent institutional or clinical conflicts from biasing adjudications.

2. Pre-Start Declarations (FORM-ADJ-08):
- All members declare conflicts before the study begins.
- Declaration covers: site investigator roles, patient care relationships, financial interests, institutional affiliations.
- COI assessment must be cleared before portal access is provisioned.

3. Per-Case Recusal:
- If a reviewer is an investigator at, or provided direct clinical care for, a case's site, they MUST recuse.
- Recusal is declared via FORM-ADJ-08 and recorded in the attributable adjudication log.
- Coordinator does not assign a conflicted member to that case.
- For sensitive cases, item-level permissions physically remove the conflicted member from that SharePoint library item.

4. Recusal Consequences:
- A recused member does not count toward quorum for that case (OAC Charter §8).
- Case is reassigned to a non-conflicted reviewer.
- If quorum cannot be met, the Coordinator escalates to VP Clinical Operations.`
  },
  SOP_004: {
    title: "SOP-ADJ-004: Calibration, Training & Consistency Monitoring",
    code: "SOP-ADJ-004 v1.0",
    scope: "Adjudicator Onboarding, Calibration Rounds & Inter-Rater Agreement",
    content: `1. Pre-Start Training Requirements (FORM-ADJ-14):
All adjudicators must complete the following before accessing the adjudication portal:
- GCP certification (ICH E6 R2 compliant).
- Protocol-specific training (PROTECT-Africa / LOPE-Nigeria).
- ISSHP 2021 / ACOG preeclampsia diagnostic criteria review.
- Adjudication manual and SOP walk-through.
- Electronic signature training (21 CFR Part 11 attestation).

2. Pre-Live Calibration Rounds:
- Minimum 3 calibration cases per reviewer before live adjudication begins.
- Reference cases are drawn from protocol-specific examples with known expected outcomes.
- Purpose: Align interpretation of edge-case definitions (e.g., proteinuria method hierarchy, Doppler abnormality grading).

3. Inter-Rater Agreement Monitoring:
- Cohen's Kappa calculated monthly across all concordant and discordant cases.
- Target: κ ≥ 0.80 (substantial agreement).
- Percent concordance tracked by endpoint category (HTN, PROT, HAEM, HEPAT, RENAL, FGR).
- Systematic discordance patterns trigger a protocol clarification or calibration re-run.

4. Annual Recertification:
- GCP refresher annually.
- Protocol amendment training mandatory within 14 days of any protocol version change.`
  },
  FORM_15A: {
    title: "FORM-ADJ-15A: EOPE Blinded Case Narrative Template (< 34+0 Weeks)",
    code: "FORM-ADJ-15A v1.0",
    scope: "Standardized Narrative Structure for Early-Onset Preeclampsia",
    content: `Mandatory 5-Section Blinded Structure (< 34+0 weeks gestation):

SECTION 1: CLINICAL HISTORY & GESTATIONAL AGE ANCHOR
- Participant demographics (age, parity) — NO name, initials, or site staff names.
- Gestational age dating anchor: 1st trimester USS preferred (≤ 13+6 weeks). LMP if USS unavailable.
- EDD, LMP, USS date and GA at scan.
- Relevant medical/obstetric history (pre-existing HTN, renal disease, diabetes).

SECTION 2: BLOOD PRESSURE & PROTEINURIA TIMELINE
- All BP measurements from screening/enrollment to delivery.
- Format: Date, gestational age, SBP/DBP mmHg, measurement method, 4-hour recheck status.
- Proteinuria: Method (dipstick / UPCR / 24h collection), result, date, severity classification.
- First date criteria ≥ 140/90 met (two occasions ≥ 4 hours apart).
- First date severe criteria ≥ 160/110 met.

SECTION 3: LABORATORY ANALYTICS & ORGAN DYSFUNCTION
- Platelet count (baseline and nadir): Flag if < 150, < 100, < 50 x10³/µL.
- Serum creatinine (with baseline): Flag if > 1.1 mg/dL or ≥ 2× baseline.
- AST, ALT (with ULN): Flag if > 2× ULN.
- LDH if available (HELLP pathway).
- Uric acid, albumin (supplementary).
- NOTE: sFlt-1/PlGF, sEng, POC results NOT included (SOP-ADJ-002).

SECTION 4: FETAL GROWTH & UTEROPLACENTAL DOPPLER
- Fetal biometry: EFW centile, HC, AC, FL measurements and dates.
- Umbilical artery Doppler: PI, S/D ratio, AEDF, REDF.
- Middle cerebral artery Doppler: PI, cerebroplacental ratio (CPR).
- Amniotic fluid index (AFI) or single deepest pocket (SDP).
- Uterine artery Doppler (if available): PI and notching.

SECTION 5: DELIVERY DETAILS & NEONATAL OUTCOMES
- Mode and indication of delivery.
- Gestational age at delivery.
- Magnesium sulfate exposure (antepartum/intrapartum/postpartum).
- Antihypertensive medications used.
- Neonatal: Birthweight (g and centile), sex, Apgar scores (1 min, 5 min), NICU admission.`
  },
  FORM_15B: {
    title: "FORM-ADJ-15B: LOPE Blinded Case Narrative Template (≥ 34+0 Weeks)",
    code: "FORM-ADJ-15B v1.0",
    scope: "Standardized Narrative Structure for Late-Onset Preeclampsia",
    content: `Mandatory 5-Section Blinded Structure (≥ 34+0 weeks gestation):

SECTION 1: PRESENTATION & GESTATIONAL AGE TIMELINE
- Participant demographics (age, parity) — blinded.
- GA at presentation ≥ 34+0 weeks confirmed.
- Dating anchor: 1st or 2nd trimester USS.

SECTION 2: BLOOD PRESSURE TRAJECTORY & PROTEINURIA
- BP at first antenatal visit (baseline).
- Serial BP readings at all subsequent visits.
- Identify first visit where ≥ 140/90 confirmed on 2 occasions ≥ 4h apart.
- Proteinuria confirmation method and result.

SECTION 3: SYSTEMIC MATERNAL ORGAN FUNCTION LABS
- Same panel as FORM-ADJ-15A Section 3.
- Note: LOPE commonly presents with milder lab derangement — document normal values explicitly.

SECTION 4: FETAL WELLBEING & AMNIOTIC FLUID INDEX
- Biophysical profile score (if performed).
- Growth assessment: EFW centile at most recent scan.
- Doppler (typically normal in LOPE — document normal explicitly).
- AFI / SDP.

SECTION 5: INTRAPARTUM COURSE, DELIVERY & POSTPARTUM RESOLUTION
- Indication for induction or delivery.
- Mode of delivery.
- Postpartum BP resolution trajectory (key LOPE differentiator from chronic HTN).
- Antihypertensive step-down and discharge BP.
- Neonatal outcomes: birthweight, Apgar, NICU.`
  },
  FORM_ADJ_PACK: {
    title: "FORM_ADJ_Pack: Forms ADJ-01 through ADJ-14",
    code: "FORM_ADJ_Pack v1.0",
    scope: "All Operational Adjudication Forms — PROTECT-Africa & LOPE-Nigeria",
    content: `FORM-ADJ-01: Pre-Release Blinding Check
Completed by Coordinator before releasing any case package to reviewers.
Verifies: No biomarker fields, no unblinding content, correct participant ID, correct study library.

FORM-ADJ-02: Case Package Receipt Acknowledgement
Signed by Reviewer on receipt of case package. Confirms identity, role, and no prior exposure to case data.

FORM-ADJ-03: Individual Reviewer Adjudication Form
Captures: Diagnosis, onset class (EOPE/LOPE), severity grade, certainty level, differential diagnosis, clinical rationale.
Fields: Meets criteria (Yes/No), primary endpoint classification, ISSHP 2021 criteria checklist, reviewer signature.

FORM-ADJ-04: Concordance Verification Form
Completed by Coordinator after both reviewers submit.
Documents: Concordant (auto-lock) vs. Discordant (committee queue).

FORM-ADJ-05: Committee Session Agenda
Agenda for discordant case review sessions. Documents quorum, attendees, cases reviewed.

FORM-ADJ-06: Committee Consensus & Chair Decision Form
Captures Chair's deciding view, committee rationale, final locked classification.

FORM-ADJ-07: Query Response Form
Response from Data Manager or Site to a FORM-ADJ-09 query. Documents resolution date and action taken.

FORM-ADJ-08: Conflict of Interest & Recusal Declaration
Per-case recusal: reason, affected participant ID, date declared, replacement reviewer assigned.

FORM-ADJ-09: Data Query & Unblinding Incident Form
Categories: Missing timestamp, unit anomaly, suspected unblinding, missing ultrasound, contradictory values.
Routes to: Data Manager (data quality), QA (unblinding incidents).

FORM-ADJ-10: Protocol Deviation Log (Adjudication)
Documents any departure from adjudication SOP with justification and impact assessment.

FORM-ADJ-11: Narrative Edit Audit Log
Tracks all human edits to AI-generated narrative (original vs. edited text, editor identity, timestamp).

FORM-ADJ-12: Calibration Round Record
Pre-live: expected outcome vs. reviewer response per calibration case. Concordance and discordance documented.

FORM-ADJ-13: Inter-Rater Agreement Report
Monthly: Cohen's Kappa by endpoint category, overall % concordance, trend vs. target (κ ≥ 0.80).

FORM-ADJ-14: Adjudicator Training Completion Certificate
GCP, protocol training, e-signature training — date completed, trainer, version of materials.`
  }
};

export default function SopLibraryModal({ onClose }) {
  const [activeSopTab, setActiveSopTab] = useState('AGENT_SOP');

  const tabs = [
    { key: 'AGENT_SOP',      label: 'AI Agent Spec' },
    { key: 'OAC_CHARTER',    label: 'OAC Charter v2.0' },
    { key: 'SOP_001',        label: 'SOP-ADJ-001' },
    { key: 'SOP_002',        label: 'SOP-ADJ-002' },
    { key: 'SOP_003',        label: 'SOP-ADJ-003' },
    { key: 'SOP_004',        label: 'SOP-ADJ-004' },
    { key: 'FORM_15A',       label: 'FORM-15A (EOPE)' },
    { key: 'FORM_15B',       label: 'FORM-15B (LOPE)' },
    { key: 'FORM_ADJ_PACK',  label: 'Forms ADJ-01–14' },
  ];

  const currentDoc = SOP_DOCUMENTS[activeSopTab] || SOP_DOCUMENTS.AGENT_SOP;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-card"
        style={{ maxWidth: '920px', height: '88vh' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BookOpen size={22} color="var(--acrn-orange-primary)" />
            <div>
              <h3 style={{ margin: 0, fontSize: '17px' }}>ACRN Trial SOP & Governance Library</h3>
              <p style={{ margin: 0, fontSize: '11px', color: 'var(--acrn-teal-accent)' }}>
                PROTECT-Africa & LOPE-Nigeria • 9 Documents
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '22px', lineHeight: 1 }}>
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex',
          background: '#f1f5f9',
          borderBottom: '1px solid var(--border-subtle)',
          overflowX: 'auto',
          flexShrink: 0
        }}>
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveSopTab(tab.key)}
              style={{
                padding: '11px 15px',
                border: 'none',
                background: activeSopTab === tab.key ? '#fff' : 'transparent',
                fontWeight: 700,
                fontSize: '12px',
                cursor: 'pointer',
                color: activeSopTab === tab.key ? 'var(--acrn-navy-base)' : 'var(--text-muted)',
                borderBottom: activeSopTab === tab.key ? '3px solid var(--acrn-orange-primary)' : '3px solid transparent',
                whiteSpace: 'nowrap',
                fontFamily: 'var(--font-family)',
                transition: 'all 0.15s'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Document Content */}
        <div style={{ flex: 1, overflowY: 'auto', background: '#fff', padding: '24px' }}>
          <div style={{
            background: '#f8fafc',
            padding: '16px 20px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            marginBottom: '18px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start'
          }}>
            <div>
              <h4 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--acrn-navy-base)', marginBottom: '4px' }}>
                {currentDoc.title}
              </h4>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Scope: <strong>{currentDoc.scope}</strong>
              </div>
            </div>
            <span className="badge-tag ope">{currentDoc.code}</span>
          </div>

          <pre style={{
            fontFamily: 'inherit',
            fontSize: '13.5px',
            lineHeight: 1.75,
            whiteSpace: 'pre-wrap',
            color: '#334155',
            background: '#fafafa',
            padding: '20px 24px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)'
          }}>
            {currentDoc.content}
          </pre>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>Close Library</button>
        </div>
      </div>
    </div>
  );
}
