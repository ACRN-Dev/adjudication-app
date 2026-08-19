import React, { useState } from 'react';
import {
  Users, CheckCircle, Scale, Lock, AlertTriangle, UserCheck, CheckSquare,
  FileText, ShieldCheck, ChevronRight, Edit3
} from 'lucide-react';
import { MOCK_CASES } from '../data/mockCases';

export default function CommitteeDashboard({ caseData, onAdoptOutcome }) {
  const discordantCase = MOCK_CASES.find(c => c.discordance) || caseData || {};

  const [selectedOutcomeMode, setSelectedOutcomeMode] = useState('ADOPT_A'); // 'ADOPT_A', 'ADOPT_B', 'ADOPT_C', 'INDEPENDENT_3RD'
  const [independentDiagnosis, setIndependentDiagnosis] = useState('Pre-eclampsia');
  const [independentOnset, setIndependentOnset] = useState('EOPE');
  const [independentSeverity, setIndependentSeverity] = useState('With severe features');
  const [independentCertainty, setIndependentCertainty] = useState('Definite');
  const [chairComment, setChairComment] = useState(
    'Committee reviewed discordant determinations. The contemporaneous midwife record and platelet nadir of 88 confirm thrombocytopenia with severe features. Consensus established.'
  );
  const [reviewerCName, setReviewerCName] = useState('Dr. C. Chitiyo (Reviewer C)');
  const [isLocked, setIsLocked] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [threeWayDivergenceAlert, setThreeWayDivergenceAlert] = useState(false);

  const discordance = discordantCase.discordance || {
    reviewerA: {
      name: 'Reviewer A (Primary)', diagnosis: 'Pre-eclampsia', onsetClass: 'EOPE (<34+0)',
      severity: 'With severe features', certainty: 'Definite', comment: 'Severe features confirmed via platelets (88) and renal impairment.'
    },
    reviewerB: {
      name: 'Reviewer B (Secondary)', diagnosis: 'Gestational HTN', onsetClass: 'LOPE (≥34+0)',
      severity: 'Without severe features', certainty: 'Probable', comment: 'Proteinuria documentation unverified.'
    },
    reviewerC: discordantCase.reviewerC || {
      name: 'Reviewer C (Third Adjudicator)', diagnosis: 'Chronic HTN', onsetClass: 'EOPE (<34+0)',
      severity: 'Without severe features', certainty: 'Probable', comment: 'Pre-existing elevated BP documented at 11 weeks booking.'
    }
  };

  const handleOutcomeModeChange = (mode) => {
    setSelectedOutcomeMode(mode);
    if (mode === 'INDEPENDENT_3RD') {
      const isDivergent = independentDiagnosis !== discordance.reviewerA.diagnosis && independentDiagnosis !== discordance.reviewerB.diagnosis;
      setThreeWayDivergenceAlert(isDivergent);
    } else {
      setThreeWayDivergenceAlert(false);
    }
  };

  const handleIndependentDiagChange = (val) => {
    setIndependentDiagnosis(val);
    const isDivergent = val !== discordance.reviewerA.diagnosis && val !== discordance.reviewerB.diagnosis;
    setThreeWayDivergenceAlert(isDivergent);
  };

  const handleFinalLock = async () => {
    if (!chairComment || chairComment.trim().length < 10) {
      alert('Mandatory clinical rationale is required (minimum 10 characters).');
      return;
    }

    setIsSubmitting(true);
    try {
      let finalDiag = discordance.reviewerA.diagnosis;
      let adoptedRole = 'REVIEWER_A';

      if (selectedOutcomeMode === 'ADOPT_B') {
        finalDiag = discordance.reviewerB.diagnosis;
        adoptedRole = 'REVIEWER_B';
      } else if (selectedOutcomeMode === 'ADOPT_C') {
        finalDiag = discordance.reviewerC?.diagnosis || independentDiagnosis;
        adoptedRole = 'REVIEWER_C';
      } else if (selectedOutcomeMode === 'INDEPENDENT_3RD') {
        finalDiag = independentDiagnosis;
        adoptedRole = 'CHAIR';
      }

      const res = await fetch(`/api/committee/${discordantCase.id || discordantCase.caseNo}/lock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          adopted_reviewer: adoptedRole,
          final_diagnosis: finalDiag,
          final_onset_class: independentOnset,
          final_severity: independentSeverity,
          final_certainty: independentCertainty,
          chair_rationale: chairComment,
          chair_upn: 'chairperson@acrnhealth.com',
          chair_name: 'Adjudication Chairperson',
          quorum_met: true,
          members_present: 4,
          visit_number: 1
        })
      });

      setIsLocked(true);
      if (onAdoptOutcome) {
        onAdoptOutcome({
          caseId: discordantCase.id,
          outcome: selectedOutcomeMode,
          finalDiagnosis: finalDiag,
          chairComment
        });
      }
    } catch (e) {
      // Fallback for standalone / mock state
      setIsLocked(true);
      if (onAdoptOutcome) {
        onAdoptOutcome({
          caseId: discordantCase.id,
          outcome: selectedOutcomeMode,
          chairComment
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>

      {/* Case Header Card */}
      <div className="rt-roster-card" style={{ borderLeft: '4px solid #0f172a', padding: '14px 18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge-tag" style={{ background: '#f1f5f9', color: '#1e293b', border: '1px solid #cbd5e1', fontWeight: 600 }}>
                <Scale size={12} style={{ display: 'inline', marginRight: '3px' }} />
                Discordant Adjudication Committee Arbitration
              </span>
              <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                Quorum Status: <strong>4 of 5 Voting Members Present (Met)</strong>
              </span>
            </div>

            <h2 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--acrn-navy-dark)', margin: '2px 0' }}>
              Consensus Adjudication Review — Subject {discordantCase.caseNo || discordantCase.id}
            </h2>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Protocol: PROTECT-Africa (A202501 v1.2) &nbsp;·&nbsp; Study Site: HARARE_01 &nbsp;·&nbsp; GA at Event: 32+4 wks
            </div>
          </div>

          <div>
            {isLocked ? (
              <div style={{ background: '#f0fdf4', color: '#15803d', border: '1px solid #bbf7d0', padding: '6px 14px', borderRadius: '4px', fontWeight: 700, fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Lock size={14} /> Finalized &amp; Locked to eTMF
              </div>
            ) : (
              <div style={{ background: '#f8fafc', color: '#334155', border: '1px solid #cbd5e1', padding: '6px 14px', borderRadius: '4px', fontWeight: 600, fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Scale size={14} /> Chair Deliberation Active
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Discordance / 3-Way Divergence Alert */}
      <div style={{
        background: threeWayDivergenceAlert ? '#fffbeb' : '#ffffff',
        border: `1px solid ${threeWayDivergenceAlert ? '#fde68a' : '#cbd5e1'}`,
        borderLeft: `4px solid ${threeWayDivergenceAlert ? '#d97706' : '#475569'}`,
        borderRadius: 'var(--radius-sm)',
        padding: '12px 16px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px'
      }}>
        <AlertTriangle size={18} color={threeWayDivergenceAlert ? '#d97706' : '#475569'} style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '12.5px' }}>
          <strong style={{ color: '#1e293b' }}>
            {threeWayDivergenceAlert ? '3-Way Divergence Escalation Active (A ≠ B ≠ C)' : 'Discordance Detected: Primary Endpoint Classification'}
          </strong>
          <div style={{ color: '#475569', marginTop: '3px', lineHeight: '1.45' }}>
            Reviewer A classified as <strong>{discordance.reviewerA.diagnosis}</strong> ({discordance.reviewerA.certainty}). &nbsp;|&nbsp;
            Reviewer B classified as <strong>{discordance.reviewerB.diagnosis}</strong> ({discordance.reviewerB.certainty}).
            {threeWayDivergenceAlert && (
              <span style={{ display: 'block', marginTop: '4px', color: '#92400e', fontWeight: 600 }}>
                ⚠️ Reviewer C / Chair is adopting an independent 3rd outcome ({independentDiagnosis}). Mandatory rationale required under SOP-ADJ-001 §7.4.
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 3-Way Side-by-Side Comparison Matrix */}
      <div className="rt-roster-card">
        <div className="rt-roster-header">
          <div className="rt-roster-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Users size={15} color="var(--acrn-navy-dark)" />
            Tripartite Reviewer Comparison Matrix (SOP-ADJ-001 §7.4)
          </div>
          <span className="badge-tag">Blinded Adjudication Record</span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="rt-roster-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th style={{ width: '22%' }}>Adjudication Parameter</th>
                <th style={{ width: '26%' }}>Reviewer A (Primary)</th>
                <th style={{ width: '26%' }}>Reviewer B (Secondary)</th>
                <th style={{ width: '26%' }}>Reviewer C (Arbitrator)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Meets Diagnostic Criteria?</strong></td>
                <td><span style={{ color: '#15803d', fontWeight: 600 }}>✓ Yes</span></td>
                <td><span style={{ color: '#15803d', fontWeight: 600 }}>✓ Yes</span></td>
                <td><span style={{ color: '#15803d', fontWeight: 600 }}>✓ Yes</span></td>
              </tr>
              <tr style={{ background: '#f8fafc' }}>
                <td><strong>Primary Diagnosis</strong></td>
                <td><strong style={{ color: '#0f172a' }}>{discordance.reviewerA.diagnosis}</strong></td>
                <td><strong style={{ color: '#0f172a' }}>{discordance.reviewerB.diagnosis}</strong></td>
                <td><strong style={{ color: '#9a3412' }}>{discordance.reviewerC?.diagnosis || 'Pending / Independent'}</strong></td>
              </tr>
              <tr>
                <td><strong>Onset Classification</strong></td>
                <td>{discordance.reviewerA.onsetClass}</td>
                <td>{discordance.reviewerB.onsetClass}</td>
                <td>{discordance.reviewerC?.onsetClass || 'EOPE (<34+0)'}</td>
              </tr>
              <tr>
                <td><strong>Severity Grade</strong></td>
                <td>{discordance.reviewerA.severity}</td>
                <td>{discordance.reviewerB.severity}</td>
                <td>{discordance.reviewerC?.severity || 'With severe features'}</td>
              </tr>
              <tr>
                <td><strong>Diagnostic Certainty</strong></td>
                <td><span className="badge-tag">{discordance.reviewerA.certainty}</span></td>
                <td><span className="badge-tag">{discordance.reviewerB.certainty}</span></td>
                <td><span className="badge-tag">{discordance.reviewerC?.certainty || 'Definite'}</span></td>
              </tr>
              <tr>
                <td><strong>Clinical Rationale</strong></td>
                <td style={{ fontStyle: 'italic', fontSize: '11.5px', color: '#475569' }}>
                  "{discordance.reviewerA.comment}"
                </td>
                <td style={{ fontStyle: 'italic', fontSize: '11.5px', color: '#475569' }}>
                  "{discordance.reviewerB.comment}"
                </td>
                <td style={{ fontStyle: 'italic', fontSize: '11.5px', color: '#475569' }}>
                  "{discordance.reviewerC?.comment || 'Independent review conducted.'}"
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Chair Consensus & Independent 3rd Option Panel */}
      <div className="wizard-card">
        <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: 'var(--acrn-navy-dark)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <UserCheck size={16} color="var(--acrn-navy-dark)" />
          Chair Consensus Determination &amp; Independent 3rd Outcome (WS2)
        </h3>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ fontSize: '11px', fontWeight: 700, display: 'block', marginBottom: '8px', color: 'var(--acrn-navy-dark)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
            Consensus Determination Mode
          </label>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
            <button
              type="button"
              className={`btn-secondary ${selectedOutcomeMode === 'ADOPT_A' ? 'active' : ''}`}
              style={{
                padding: '10px 12px', textAlign: 'left',
                borderColor: selectedOutcomeMode === 'ADOPT_A' ? '#0f172a' : '#cbd5e1',
                background: selectedOutcomeMode === 'ADOPT_A' ? '#f8fafc' : '#ffffff'
              }}
              onClick={() => handleOutcomeModeChange('ADOPT_A')}
              disabled={isLocked}
            >
              <CheckSquare size={15} color={selectedOutcomeMode === 'ADOPT_A' ? '#0f172a' : '#94a3b8'} />
              <div>
                <strong style={{ display: 'block', fontSize: '12px', color: '#0f172a' }}>Adopt Reviewer A</strong>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{discordance.reviewerA.diagnosis}</span>
              </div>
            </button>

            <button
              type="button"
              className={`btn-secondary ${selectedOutcomeMode === 'ADOPT_B' ? 'active' : ''}`}
              style={{
                padding: '10px 12px', textAlign: 'left',
                borderColor: selectedOutcomeMode === 'ADOPT_B' ? '#0f172a' : '#cbd5e1',
                background: selectedOutcomeMode === 'ADOPT_B' ? '#f8fafc' : '#ffffff'
              }}
              onClick={() => handleOutcomeModeChange('ADOPT_B')}
              disabled={isLocked}
            >
              <CheckSquare size={15} color={selectedOutcomeMode === 'ADOPT_B' ? '#0f172a' : '#94a3b8'} />
              <div>
                <strong style={{ display: 'block', fontSize: '12px', color: '#0f172a' }}>Adopt Reviewer B</strong>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{discordance.reviewerB.diagnosis}</span>
              </div>
            </button>

            <button
              type="button"
              className={`btn-secondary ${selectedOutcomeMode === 'ADOPT_C' ? 'active' : ''}`}
              style={{
                padding: '10px 12px', textAlign: 'left',
                borderColor: selectedOutcomeMode === 'ADOPT_C' ? '#0f172a' : '#cbd5e1',
                background: selectedOutcomeMode === 'ADOPT_C' ? '#f8fafc' : '#ffffff'
              }}
              onClick={() => handleOutcomeModeChange('ADOPT_C')}
              disabled={isLocked}
            >
              <CheckSquare size={15} color={selectedOutcomeMode === 'ADOPT_C' ? '#0f172a' : '#94a3b8'} />
              <div>
                <strong style={{ display: 'block', fontSize: '12px', color: '#0f172a' }}>Adopt Reviewer C</strong>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{discordance.reviewerC?.diagnosis || 'Reviewer C'}</span>
              </div>
            </button>

            <button
              type="button"
              className={`btn-secondary ${selectedOutcomeMode === 'INDEPENDENT_3RD' ? 'active' : ''}`}
              style={{
                padding: '10px 12px', textAlign: 'left',
                borderColor: selectedOutcomeMode === 'INDEPENDENT_3RD' ? '#ea580c' : '#cbd5e1',
                background: selectedOutcomeMode === 'INDEPENDENT_3RD' ? '#fff7ed' : '#ffffff'
              }}
              onClick={() => handleOutcomeModeChange('INDEPENDENT_3RD')}
              disabled={isLocked}
            >
              <Edit3 size={15} color={selectedOutcomeMode === 'INDEPENDENT_3RD' ? '#ea580c' : '#94a3b8'} />
              <div>
                <strong style={{ display: 'block', fontSize: '12px', color: '#9a3412' }}>Independent 3rd Outcome</strong>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Custom / Other diagnosis</span>
              </div>
            </button>
          </div>
        </div>

        {/* Independent 3rd Determination Form (if selected) */}
        {selectedOutcomeMode === 'INDEPENDENT_3RD' && (
          <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '14px', marginBottom: '16px' }}>
            <div style={{ fontWeight: 700, fontSize: '12.5px', marginBottom: '10px', color: '#0f172a' }}>
              Reviewer C / Chair Independent Clinical Classification:
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '11.5px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Diagnosis Code</label>
                <select
                  value={independentDiagnosis}
                  onChange={(e) => handleIndependentDiagChange(e.target.value)}
                  disabled={isLocked}
                  style={{ width: '100%', padding: '7px 10px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '12.5px' }}
                >
                  <option value="Pre-eclampsia">Pre-eclampsia (non-severe)</option>
                  <option value="Pre-eclampsia with severe features">Pre-eclampsia with severe features</option>
                  <option value="Severe Hypertension alone">Severe Hypertension alone</option>
                  <option value="Gestational hypertension">Gestational hypertension</option>
                  <option value="Chronic HTN">Chronic HTN</option>
                  <option value="Superimposed PE">Superimposed PE</option>
                  <option value="HELLP Syndrome">HELLP Syndrome</option>
                  <option value="Eclampsia">Eclampsia</option>
                  <option value="Not PE">Normotensive / Not PE</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '11.5px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Onset Classification</label>
                <select
                  value={independentOnset}
                  onChange={(e) => setIndependentOnset(e.target.value)}
                  disabled={isLocked}
                  style={{ width: '100%', padding: '7px 10px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '12.5px' }}
                >
                  <option value="EOPE">EOPE (&lt; 34+0 weeks)</option>
                  <option value="LOPE">LOPE (≥ 34+0 weeks)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '11.5px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Severity Grade</label>
                <select
                  value={independentSeverity}
                  onChange={(e) => setIndependentSeverity(e.target.value)}
                  disabled={isLocked}
                  style={{ width: '100%', padding: '7px 10px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '12.5px' }}
                >
                  <option value="With severe features">With severe features</option>
                  <option value="Without severe features">Without severe features</option>
                  <option value="Eclampsia / SAE">Eclampsia / SAE</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '11.5px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Diagnostic Certainty</label>
                <select
                  value={independentCertainty}
                  onChange={(e) => setIndependentCertainty(e.target.value)}
                  disabled={isLocked}
                  style={{ width: '100%', padding: '7px 10px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '12.5px' }}
                >
                  <option value="Definite">Definite</option>
                  <option value="Probable">Probable</option>
                  <option value="Possible">Possible</option>
                </select>
              </div>
            </div>
          </div>
        )}

        <div className="form-group" style={{ marginBottom: '14px' }}>
          <label style={{ fontWeight: 700, fontSize: '12.5px' }}>
            Chair Rationale &amp; Deliberation Minutes {threeWayDivergenceAlert ? '(Mandatory for 3-Way Divergence)' : '(Required — OAC Charter §10.3)'}
          </label>
          <textarea
            className="narrative-box"
            style={{ height: '75px', fontSize: '12px' }}
            value={chairComment}
            onChange={(e) => setChairComment(e.target.value)}
            disabled={isLocked}
            placeholder="Document clinical justification, laboratory correlation, and rationale for consensus..."
            required
          />
        </div>

        <div className="wizard-footer">
          <div></div>
          {isLocked ? (
            <div style={{ color: '#15803d', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '6px 14px', borderRadius: 'var(--radius-sm)', fontSize: '12px' }}>
              <CheckCircle size={15} /> Consensus Finalized &amp; Locked to eTMF
            </div>
          ) : (
            <button
              className="btn-primary"
              style={{ padding: '8px 16px', fontSize: '13px' }}
              onClick={handleFinalLock}
              disabled={isSubmitting}
            >
              <Lock size={14} /> {isSubmitting ? 'Recording Sign-Off...' : 'Sign & Lock Final Committee Classification'}
            </button>
          )}
        </div>
      </div>

    </div>
  );
}
