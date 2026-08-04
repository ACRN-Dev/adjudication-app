import React, { useState } from 'react';
import { Users, CheckCircle, Scale, Lock, AlertTriangle, UserCheck, CheckSquare } from 'lucide-react';
import { MOCK_CASES } from '../data/mockCases';

export default function CommitteeDashboard({ caseData, onAdoptOutcome }) {
  const discordantCase = MOCK_CASES.find(c => c.discordance) || caseData;

  const [selectedOutcome, setSelectedOutcome] = useState('ADOPT_A');
  const [chairComment, setChairComment] = useState(
    'Committee accepts eclampsia classification. The midwife contemporaneous note constitutes adequate documentation; certainty downgraded to Probable by majority consensus given second-hand account and undocumented seizure duration.'
  );
  const [isLocked, setIsLocked] = useState(false);

  const discordance = discordantCase.discordance || {
    reviewerA: {
      name: 'Reviewer A (Primary)', diagnosis: 'Preeclampsia', onsetClass: 'EOPE (<34+0)',
      severity: 'With severe features', certainty: 'Definite', comment: 'Severe features confirmed via platelets (88) and renal impairment.'
    },
    reviewerB: {
      name: 'Reviewer B (Secondary)', diagnosis: 'Gestational HTN', onsetClass: 'LOPE (≥34+0)',
      severity: 'Without severe features', certainty: 'Probable', comment: 'Proteinuria documentation unverified.'
    }
  };

  const handleFinalLock = () => {
    setIsLocked(true);
    if (onAdoptOutcome) {
      onAdoptOutcome({
        caseId: discordantCase.id,
        outcome: selectedOutcome,
        chairComment
      });
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>

      {/* Case Header Card — Minimal Neutral Design */}
      <div className="rt-roster-card" style={{ borderLeft: '4px solid #162035', padding: '12px 16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge-tag" style={{ background: '#f1f5f9', color: '#1e293b', border: '1px solid #cbd5e1', fontWeight: 600 }}>
                <Scale size={12} style={{ display: 'inline', marginRight: '3px' }} />
                Discordant Adjudication Review
              </span>
              <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                Quorum Status: <strong>3 of 5 Members Present (Met)</strong>
              </span>
            </div>

            <h2 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--acrn-navy-dark)' }}>
              Committee Consensus Review — Case {discordantCase.caseNo} ({discordantCase.id})
            </h2>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Trigger: {discordantCase.trigger} &nbsp;·&nbsp; GA at Event: {discordantCase.gaAtEvent} &nbsp;·&nbsp; Convened: 31 Jul 2026
            </div>
          </div>

          <div>
            {isLocked ? (
              <div style={{ background: '#f0fdf4', color: '#15803d', border: '1px solid #bbf7d0', padding: '5px 12px', borderRadius: '4px', fontWeight: 700, fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Lock size={14} /> Finalized &amp; Locked to TMF
              </div>
            ) : (
              <div style={{ background: '#f8fafc', color: '#334155', border: '1px solid #cbd5e1', padding: '5px 12px', borderRadius: '4px', fontWeight: 600, fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Scale size={14} /> Chair Consensus Pending
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Discordance Alert Box — Neutral Corporate Style */}
      <div style={{
        background: '#ffffff',
        border: '1px solid #cbd5e1',
        borderLeft: '4px solid #475569',
        borderRadius: 'var(--radius-sm)',
        padding: '10px 14px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '10px'
      }}>
        <AlertTriangle size={16} color="#475569" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '12px' }}>
          <strong style={{ color: '#1e293b', fontSize: '12.5px' }}>
            Discordance Detected: Primary Endpoint Classification
          </strong>
          <div style={{ color: '#475569', marginTop: '2px', lineHeight: '1.45' }}>
            Reviewer A classified as <strong>{discordance.reviewerA.diagnosis}</strong> ({discordance.reviewerA.certainty}).
            Reviewer B classified as <strong>{discordance.reviewerB.diagnosis}</strong> ({discordance.reviewerB.certainty}).
            Point of disagreement: validity of witnessed seizure and proteinuria documentation.
          </div>
        </div>
      </div>

      {/* Side-by-Side Reviewer Comparison Matrix (Clean Monochrome Roster Table) */}
      <div className="rt-roster-card">
        <div className="rt-roster-header">
          <div className="rt-roster-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Users size={15} color="var(--acrn-navy-dark)" />
            Side-by-Side Reviewer Comparison Matrix (SOP-ADJ-001 §7.4)
          </div>
          <span className="badge-tag">Dual Blinded Review</span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="rt-roster-table">
            <thead>
              <tr>
                <th style={{ width: '24%' }}>Adjudication Field</th>
                <th style={{ width: '38%' }}>
                  Reviewer A: {discordance.reviewerA.name}
                </th>
                <th style={{ width: '38%' }}>
                  Reviewer B: {discordance.reviewerB.name}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Meets Diagnostic Criteria?</strong></td>
                <td><span style={{ color: '#15803d', fontWeight: 600 }}>✓ Yes</span></td>
                <td><span style={{ color: '#15803d', fontWeight: 600 }}>✓ Yes</span></td>
              </tr>
              <tr style={{ background: '#f8fafc' }}>
                <td><strong>Primary Diagnosis</strong></td>
                <td><strong style={{ color: '#1e293b' }}>{discordance.reviewerA.diagnosis}</strong></td>
                <td><strong style={{ color: '#1e293b' }}>{discordance.reviewerB.diagnosis}</strong></td>
              </tr>
              <tr>
                <td><strong>Onset Classification</strong></td>
                <td>{discordance.reviewerA.onsetClass}</td>
                <td>{discordance.reviewerB.onsetClass}</td>
              </tr>
              <tr>
                <td><strong>Severity Grade</strong></td>
                <td>{discordance.reviewerA.severity}</td>
                <td>{discordance.reviewerB.severity}</td>
              </tr>
              <tr>
                <td><strong>Diagnostic Certainty</strong></td>
                <td>
                  <span className="badge-tag">{discordance.reviewerA.certainty}</span>
                </td>
                <td>
                  <span className="badge-tag">{discordance.reviewerB.certainty}</span>
                </td>
              </tr>
              <tr>
                <td><strong>Clinical Rationale</strong></td>
                <td style={{ fontStyle: 'italic', fontSize: '11.5px', color: '#475569' }}>
                  "{discordance.reviewerA.comment}"
                </td>
                <td style={{ fontStyle: 'italic', fontSize: '11.5px', color: '#475569' }}>
                  "{discordance.reviewerB.comment}"
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Chair Consensus Decision Panel */}
      <div className="wizard-card">
        <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: 'var(--acrn-navy-dark)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <UserCheck size={16} color="var(--acrn-navy-dark)" />
          OAC Chair Consensus Decision (OAC Charter §10)
        </h3>

        <div style={{ marginBottom: '12px' }}>
          <label style={{ fontSize: '11px', fontWeight: 700, display: 'block', marginBottom: '6px', color: 'var(--acrn-navy-dark)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
            Adopted Consensus Outcome
          </label>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <button
              type="button"
              className={`btn-secondary ${selectedOutcome === 'ADOPT_A' ? 'active' : ''}`}
              style={{
                padding: '8px 12px',
                justify: 'flex-start',
                textAlign: 'left',
                borderColor: selectedOutcome === 'ADOPT_A' ? '#162035' : '#cbd5e1',
                background: selectedOutcome === 'ADOPT_A' ? '#f8fafc' : '#ffffff'
              }}
              onClick={() => setSelectedOutcome('ADOPT_A')}
              disabled={isLocked}
            >
              <CheckSquare size={15} color={selectedOutcome === 'ADOPT_A' ? '#162035' : '#94a3b8'} />
              <div>
                <strong style={{ display: 'block', fontSize: '12px', color: '#162035' }}>Adopt Reviewer A Outcome</strong>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{discordance.reviewerA.diagnosis} ({discordance.reviewerA.certainty})</span>
              </div>
            </button>

            <button
              type="button"
              className={`btn-secondary ${selectedOutcome === 'ADOPT_B' ? 'active' : ''}`}
              style={{
                padding: '8px 12px',
                justify: 'flex-start',
                textAlign: 'left',
                borderColor: selectedOutcome === 'ADOPT_B' ? '#162035' : '#cbd5e1',
                background: selectedOutcome === 'ADOPT_B' ? '#f8fafc' : '#ffffff'
              }}
              onClick={() => setSelectedOutcome('ADOPT_B')}
              disabled={isLocked}
            >
              <CheckSquare size={15} color={selectedOutcome === 'ADOPT_B' ? '#162035' : '#94a3b8'} />
              <div>
                <strong style={{ display: 'block', fontSize: '12px', color: '#162035' }}>Adopt Reviewer B Outcome</strong>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{discordance.reviewerB.diagnosis} ({discordance.reviewerB.certainty})</span>
              </div>
            </button>
          </div>
        </div>

        <div className="form-group" style={{ marginBottom: '14px' }}>
          <label style={{ fontWeight: 700 }}>Chair Rationale &amp; Committee Meeting Minutes (Required — OAC Charter §10.3)</label>
          <textarea
            className="narrative-box"
            style={{ height: '70px', fontSize: '12px' }}
            value={chairComment}
            onChange={(e) => setChairComment(e.target.value)}
            disabled={isLocked}
          />
        </div>

        <div className="wizard-footer">
          <div></div>
          {isLocked ? (
            <div style={{ color: '#15803d', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '6px 12px', borderRadius: 'var(--radius-sm)', fontSize: '12px' }}>
              <CheckCircle size={15} /> Adjudication Finalized &amp; Filed to TMF
            </div>
          ) : (
            <button className="btn-primary" style={{ padding: '7px 14px' }} onClick={handleFinalLock}>
              <Lock size={14} /> Sign &amp; Lock Final Committee Classification
            </button>
          )}
        </div>
      </div>

    </div>
  );
}
