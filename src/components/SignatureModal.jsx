import React, { useState } from 'react';
import { Lock, ShieldCheck, Key, AlertCircle, CheckCircle } from 'lucide-react';
import { DEMO_UI_BUILD_ENABLED } from '../config/featureFlags';

export default function SignatureModal({ caseData, user, submission, onSignConfirm, onClose }) {
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSignature = (e) => {
    e.preventDefault();
    if (!password) {
      setErrorMsg('Please enter your ACRN account credentials to authenticate.');
      return;
    }
    setIsSubmitting(true);
    setErrorMsg('');
    const normalizeOnsetClass = (raw) => {
      if (!raw) return 'UNCLASSIFIABLE';
      const str = String(raw).toUpperCase();
      if (str.includes('LOPE') || str.includes('LATE')) return 'LOPE';
      if (str.includes('POST')) return 'POSTPARTUM';
      if (str.includes('NOT YET') || str.includes('UNCLASSIFIABLE')) return 'UNCLASSIFIABLE';
      return 'EOPE';
    };
    const onset = normalizeOnsetClass(submission?.onset);
    const diagnosis = submission?.diagnosis || 'PE';
    const cleanPerVisitOnset = (submission?.per_visit_onset || []).map(o => ({
      visit_number: Number(o.visit_number || 1),
      meets_criteria: Boolean(o.meets_criteria),
      diagnosis: o.meets_criteria ? (o.diagnosis || submission?.diagnosis || 'PE') : 'Not PE',
      onset_class: o.meets_criteria ? normalizeOnsetClass(o.onset_class || submission?.onset) : 'UNCLASSIFIABLE',
    }));

    const rawSev = submission?.severity;
    const cleanSeverity = rawSev === 'Eclampsia / severe SAE' ? 'Eclampsia / SAE' : (rawSev || 'Without severe features');

    fetch(`/api/adjudication/${encodeURIComponent(caseData.id)}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        is_overall_first: submission?.is_overall_first || false,
        per_visit_onset: cleanPerVisitOnset,
        reviewer_role: submission?.reviewerRole || 'REVIEWER_A',
        reviewer_upn: user?.email,
        reviewer_name: submission?.reviewerName || user?.display_name || user?.email,
        reviewer_password: password,
        mfa_code: mfaCode,
        visit_number: submission?.visitNumber || 1,
        visit_code: submission?.visitCode,
        visit_date: submission?.visitDate,
        meets_criteria: submission?.meetsCriteria !== false,
        diagnosis,
        date_of_diagnosis: submission?.dateOfDiagnosis || submission?.firstPeDate || (submission?.meetsCriteria !== false ? (submission?.visitDate || new Date().toISOString().slice(0, 10)) : null),
        onset_class: onset,
        severity: cleanSeverity,
        certainty: submission?.certainty || 'Probable',
        rationale: submission?.rationale || 'Adjudication completed after review of the available evidence.',
        comment: submission?.comment || null,
        differential_diagnosis: submission?.differentialDiagnosis || null,
        longitudinal_comment: submission?.longitudinalComment || null,
        first_pe_visit_number: submission?.firstPeVisitNumber || null,
        first_pe_date: submission?.firstPeDate || submission?.dateOfDiagnosis || null,
        other_rationale: submission?.otherRationale || null,
        fetal_neonatal_assessments: submission?.fetalNeonatalAssessments || [],
        gestational_age_at_delivery: submission?.gestationalAgeAtDelivery != null ? Number(submission.gestationalAgeAtDelivery) : null,
        pregnancy_outcome: submission?.pregnancyOutcome || null,
        fetal_assessment_status: submission?.fetalAssessmentStatus || null,
        fetal_neonatal_provenance: submission?.fetalNeonatalProvenance || null,
      }),
    })
      .then(async response => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          const detailMsg = Array.isArray(data.detail)
            ? data.detail.map(d => `${d.loc ? d.loc.filter(x => x !== 'body').join('.') + ': ' : ''}${d.msg}`).join('\n')
            : (typeof data.detail === 'object' ? JSON.stringify(data.detail) : (data.detail || `Signature submission failed (${response.status})`));
          throw new Error(detailMsg);
        }
        onSignConfirm(data);
      })
      .catch(error => setErrorMsg(error.message))
      .finally(() => setIsSubmitting(false));
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Lock size={20} color="var(--acrn-orange-primary)" />
            <h3 style={{ margin: 0, fontSize: '16px' }}>21 CFR Part 11 Electronic Signature</h3>
          </div>
        </div>

        <form onSubmit={handleSignature}>
          <div className="modal-body">
            <div style={{
              background: '#f8fafc',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '14px',
              marginBottom: '16px'
            }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Signing Target</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--acrn-navy-base)' }}>
                Case {caseData.caseNo} ({caseData.id})
              </div>
              <div style={{ fontSize: '12.5px', marginTop: '6px', color: '#1e293b' }}>
                Determination: <strong>{submission?.diagnosis || 'PE'}</strong> · Criteria Met: <strong>{submission?.meetsCriteria !== false ? 'Yes' : 'No'}</strong>
                {submission?.meetsCriteria !== false && (
                  <span style={{ display: 'block', marginTop: '4px', fontSize: '12px', color: '#0369a1' }}>
                    Date of Diagnosis: <strong>{submission?.dateOfDiagnosis || submission?.firstPeDate || 'Today'}</strong> {submission?.firstPeVisitNumber ? `(Visit ${submission.firstPeVisitNumber})` : ''}
                  </span>
                )}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--acrn-sky-blue)', marginTop: '6px' }}>
                The server will bind the authenticated identity, determination, visit, and signing time into the immutable signature record.
              </div>
            </div>

            {submission?.visitNumber === 5 && (
              <div style={{
                background: '#eff6ff',
                border: '1px solid #bfdbfe',
                borderRadius: 'var(--radius-md)',
                padding: '10px 14px',
                marginBottom: '16px',
                fontSize: '12px',
                color: '#1e40af'
              }}>
                <div style={{ fontWeight: 700, marginBottom: '2px' }}>Visit 5 Closed-Ended Assessments Included:</div>
                <div>GA at delivery: <strong>{submission?.gestationalAgeAtDelivery ? `${submission.gestationalAgeAtDelivery} wks` : 'Not documented'}</strong> · Outcome: <strong>{submission?.pregnancyOutcome || 'Not specified'}</strong></div>
                <div style={{ marginTop: '2px' }}>Endpoints: <strong>{submission?.fetalNeonatalAssessments?.length ? submission.fetalNeonatalAssessments.join(', ') : 'None selected'}</strong></div>
              </div>
            )}

            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              By signing below, I certify that I have reviewed the source data, derived criteria, and clinical narrative for participant <strong>{caseData.id}</strong>. This record will be cryptographically locked and filed directly to the TMF.
            </p>

            {errorMsg && (
              <div style={{
                background: '#ffebe9',
                color: '#cf222e',
                padding: '10px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                marginBottom: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <AlertCircle size={16} />
                {errorMsg}
              </div>
            )}

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label>Re-enter Password</label>
              <input
                type="password"
                className="form-input"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            {DEMO_UI_BUILD_ENABLED && <div className="form-group">
              <label>Demo signature passcode</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  className="form-input"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                />
                <button type="button" className="btn-secondary" style={{ whiteSpace: 'nowrap' }} onClick={() => alert('Request a new demo passcode from the demo administrator.')}>
                  Resend OTP
                </button>
              </div>
            </div>}
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={isSubmitting}>
              {isSubmitting ? (
                <>Signing Case...</>
              ) : (
                <>
                  <ShieldCheck size={16} /> Authenticate & Lock Record
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
