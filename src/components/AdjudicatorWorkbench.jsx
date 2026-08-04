import React, { useState, useEffect } from 'react';
import { 
  ArrowRight, 
  ArrowLeft, 
  CheckCircle2, 
  Activity, 
  Database, 
  ShieldCheck, 
  FileText, 
  Lock,
  Download,
  EyeOff,
  UserX,
  AlertCircle,
  RefreshCw,
  Info,
  ExternalLink,
  ChevronDown,
  Bot
} from 'lucide-react';
import { generateNarrative, generateSummary, AI_ENGINE_MODEL } from '../services/demoNarrative';
import { runDvEngine } from '../services/dvEngine';
import { downloadPdfReport } from '../services/api';

export default function AdjudicatorWorkbench({ 
  currentStep, 
  setCurrentStep, 
  cases, 
  activeCase, 
  onSelectCase, 
  onOpenSignature,
  onOpenSourceDocs,
  onOpenRecusalModal,
  onOpenDataQueryModal
}) {
  const [selectedDiagnosis, setSelectedDiagnosis] = useState('Pre-eclampsia');
  const [selectedOnset, setSelectedOnset] = useState('Early-onset pre-eclampsia (EOPE)');
  const [selectedSeverity, setSelectedSeverity] = useState('With severe features');
  const [selectedCertainty, setSelectedCertainty] = useState('Probable');
  const [narrativeText, setNarrativeText] = useState('');
  const [formCode, setFormCode] = useState('FORM-ADJ-15A');
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [pdfDownloadError, setPdfDownloadError] = useState('');
  const isSigned = activeCase?.status?.includes('Finalized');

  // Compute DV engine results for active case
  const dvResults = activeCase ? runDvEngine(activeCase) : null;
  const evidenceScore = dvResults ? dvResults.evidenceScore : (activeCase?.pktScore || 0);
  const missingAnchors = dvResults ? dvResults.missingAnchors : [];
  const certaintyGatePassed = dvResults?.certaintyGate?.inputs?.gate_open ?? (evidenceScore === 1.0);
  const maxCertaintyAllowed = dvResults?.certaintyGate?.inputs?.max_certainty || (evidenceScore === 1.0 ? 'Definite' : 'Probable');

  useEffect(() => {
    if (activeCase) {
      const generated = generateNarrative(activeCase);
      setNarrativeText(generated.fullText);
      setFormCode(generated.formCode);

      if (activeCase.derivedSubtype === 'LOPE') {
        setSelectedOnset('Late-onset pre-eclampsia (LOPE)');
      } else if (activeCase.derivedSubtype === 'POSTPARTUM') {
        setSelectedOnset('Postpartum-only presentation');
      } else {
        setSelectedOnset('Early-onset pre-eclampsia (EOPE)');
      }

      if (activeCase.derivedSeverity === 'SEVERE_FEATURES') {
        setSelectedSeverity('With severe features');
      } else {
        setSelectedSeverity('Without severe features');
      }

      if (certaintyGatePassed) {
        setSelectedCertainty('Definite');
      } else {
        setSelectedCertainty('Probable');
      }
    }
  }, [activeCase?.id]);

  const handleRegenerateNarrative = () => {
    if (!activeCase) return;
    setIsGeneratingAi(true);
    setTimeout(() => {
      const generated = generateNarrative(activeCase, formCode);
      setNarrativeText(generated.fullText);
      setIsGeneratingAi(false);
    }, 450);
  };

  // STEP 1: ASSIGNED, QC-APPROVED PATIENT DATABASE
  if (currentStep === 1) {
    return (
      <div>
        {/* RealTime Roster Container */}
        <div className="rt-roster-card">
          <div className="rt-roster-header">
            <div className="rt-roster-title">
              {cases.length} Assigned Subjects — Adjudication Queue
            </div>

            <div className="rt-roster-toolbar"><span className="rt-status-badge enrolled">QC-approved assignments only</span></div>
          </div>

          {/* Group Header Bar (RealTime Style) */}
          <div className="rt-roster-group-bar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ChevronDown size={14} />
              <span>Enrolled / Pending Endpoint Adjudication</span>
            </div>
            <span className="rt-roster-group-badge">{cases.length}</span>
          </div>

          {cases.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table className="rt-roster-table">
                <thead>
                  <tr>
                    <th>Subject ID ↕</th>
                    <th>Case Number ↕</th>
                    <th>Site (Blinded) ↕</th>
                    <th>GA at Event ↕</th>
                    <th>Derived Phenotype</th>
                    <th>DV-26 Score</th>
                    <th>Status ↕</th>
                    <th>eSource Action</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map(c => {
                    const isSelected = activeCase && c.id === activeCase.id;
                    const isCaseSigned = c.status?.includes('Finalized');
                    const cDv = runDvEngine(c);
                    const score = Math.round(cDv.evidenceScore * 100);

                    return (
                      <tr
                        key={c.id}
                        className={isSelected ? 'selected' : ''}
                        style={{ cursor: 'pointer' }}
                        onClick={() => onSelectCase(c.id)}
                      >
                        <td>
                          <span className="rt-subject-link">
                            {c.id} <ExternalLink size={11} style={{ display: 'inline' }} />
                          </span>
                        </td>
                        <td>
                          <span style={{ fontWeight: 600, color: '#475569' }}>{c.caseNo}</span>
                        </td>
                        <td>
                          <span style={{ fontSize: '11.5px', color: '#64748b' }}>{c.site}</span>
                        </td>
                        <td>
                          <strong style={{ color: '#162035' }}>GA {c.gaAtEvent || 'N/A'}</strong>
                        </td>
                        <td>
                          {c.derivedSeverity === 'SEVERE_FEATURES' ? (
                            <span style={{ color: '#162035', fontWeight: 600 }}>
                              {c.derivedSubtype || 'EOPE'} • Severe
                            </span>
                          ) : (
                            <span>{c.derivedSubtype || 'LOPE'} • Standard</span>
                          )}
                        </td>
                        <td>
                          <span style={{
                            fontWeight: 700,
                            color: score === 100 ? '#15803d' : '#475569'
                          }}>
                            {score}%
                          </span>
                        </td>
                        <td>
                          {isCaseSigned ? (
                            <span className="rt-status-badge signed">
                              <CheckCircle2 size={11} /> Finalized &amp; Signed
                            </span>
                          ) : (
                            <span className="rt-status-badge enrolled">
                              Enrolled / Pending
                            </span>
                          )}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="rt-esource-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectCase(c.id);
                              setCurrentStep(2);
                            }}
                          >
                            <FileText size={11} /> Review eSource
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{
              padding: '24px',
              textAlign: 'center',
              background: '#ffffff',
              color: '#64748b'
            }}>
              <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--acrn-navy-dark)', marginBottom: '4px' }}>
                Assigned Patient Database Empty
              </div>
              <div style={{ fontSize: '12px', marginBottom: '14px' }}>
                No QC-approved participants are assigned to your reviewer identity. A Monitor/QC user must import a RealTime batch, approve the package, and assign it to you.
              </div>
            </div>
          )}
        </div>

        <div className="wizard-footer"><div></div><button className="btn-large btn-next" onClick={() => setCurrentStep(2)} disabled={!activeCase}>Next: Review Patient Evidence <ArrowRight size={16}/></button></div>
      </div>
    );
  }

  // STEP 2: REVIEW EVIDENCE & SYSTEM DERIVATION — NEUTRAL CORPORATE STYLE
  if (currentStep === 2) {
    return (
      <div>
        <div className="wizard-card">
          {/* Header Actions */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <h2 className="wizard-title">Step 2: Review Findings for Participant {activeCase.id}</h2>
              <p className="wizard-subtitle">
                {activeCase.qcStatus || "FORM-ADJ-01 QC Check Passed"} • SOP-ADJ-002 Blinding Active
              </p>
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button className="btn-secondary" onClick={onOpenRecusalModal}>
                <UserX size={13} /> Declare Recusal (FORM-ADJ-08)
              </button>
              <button className="btn-secondary" onClick={onOpenDataQueryModal}>
                <AlertCircle size={13} /> Raise Query (FORM-ADJ-09)
              </button>
              <button className="btn-back" style={{ padding: '5px 10px' }} onClick={onOpenSourceDocs}>
                Inspect Raw Docs
              </button>
            </div>
          </div>

          {/* SOP-ADJ-002 Biomarker Blinding Guardrail Banner — Neutral */}
          <div style={{
            background: '#f8fafc',
            border: '1px solid #cbd5e1',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <EyeOff size={16} color="#64748b" />
              <div>
                <strong style={{ fontSize: '12.5px', color: '#1e293b' }}>Biomarker Blinding Guardrail (SOP-ADJ-002 §5.1)</strong>
                <div style={{ fontSize: '11.5px', color: '#64748b' }}>
                  sFlt-1/PlGF ratio &amp; POC outputs are strictly withheld until database lock.
                </div>
              </div>
            </div>
            <span className="badge-tag">BLINDED</span>
          </div>

          <div className="summary-card-grid">
            {/* Box 1: Blood Pressure */}
            <div className="summary-feature-card">
              <h4>
                <Activity color="var(--acrn-navy-dark)" size={16} />
                1. Blood Pressure Timeline
              </h4>
              <div style={{ marginTop: '8px' }}>
                {activeCase.bpLog && activeCase.bpLog.length > 0 ? (
                  activeCase.bpLog.map((bp, i) => (
                    <div key={i} className="data-summary-row" style={{ background: bp.severe ? '#f8fafc' : 'transparent', padding: '4px 6px', borderRadius: '3px' }}>
                      <span>{bp.date || 'GA ' + bp.ga}</span>
                      <span style={{ fontWeight: bp.severe ? 700 : 500, color: '#162035' }}>
                        {bp.sbp}/{bp.dbp} mmHg {bp.severe ? '[Severe Range]' : ''}
                      </span>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '11.5px', color: '#94a3b8', fontStyle: 'italic' }}>
                    A confirmatory dated/timed BP or eligible severe-range recheck not documented
                  </div>
                )}
              </div>
            </div>

            {/* Box 2: Key Labs */}
            <div className="summary-feature-card">
              <h4>
                <Database color="var(--acrn-navy-dark)" size={16} />
                2. Key Lab Results &amp; Proteinuria
              </h4>
              <div style={{ marginTop: '8px' }}>
                {activeCase.proteinuriaLog && activeCase.proteinuriaLog.length > 0 ? (
                  activeCase.proteinuriaLog.map((p, i) => (
                    <div key={i} className="data-summary-row" style={{ background: '#f8fafc', padding: '4px 6px', borderRadius: '3px' }}>
                      <span>Proteinuria ({p.method})</span>
                      <span style={{ fontWeight: 600 }}>{p.result}</span>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '11.5px', color: '#94a3b8', fontStyle: 'italic', marginBottom: '6px' }}>
                    A dated UPCR, 24-hour protein or dipstick result not documented
                  </div>
                )}
                {activeCase.labLog && activeCase.labLog.length > 0 ? (
                  activeCase.labLog.map((l, i) => (
                    <div key={i} className="data-summary-row">
                      <span>{l.analyte}</span>
                      <span style={{ fontWeight: l.severe ? 700 : 500 }}>{l.result} {l.unit}</span>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '11.5px', color: '#94a3b8', fontStyle: 'italic' }}>
                    Dated platelet count with AST/ALT evidence not documented
                  </div>
                )}
              </div>
            </div>

            {/* Box 3: Gate Status Panel — Clean Neutral Style */}
            <div className="summary-feature-card">
              <h4>
                <CheckCircle2 color="var(--acrn-navy-dark)" size={16} />
                3. Gate Status &amp; Automated Rules (PROTECT-DV-2026.08)
              </h4>
              
              <div style={{ marginTop: '8px', background: '#f8fafc', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-subtle)', marginBottom: '8px' }}>
                <div style={{ fontSize: '10.5px', color: 'var(--acrn-navy-dark)', fontWeight: 700, textTransform: 'uppercase' }}>Derived Outcome</div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--acrn-navy-dark)', marginTop: '2px' }}>
                  {activeCase.derivedSubtype || 'EOPE'} • {activeCase.derivedSeverity === 'SEVERE_FEATURES' ? 'With severe features' : 'Without severe features'}
                </div>
              </div>

              {/* DV-26 Evidence Completeness */}
              <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '4px', padding: '10px', marginBottom: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '10.5px', fontWeight: 700, color: '#1e293b', textTransform: 'uppercase' }}>
                    DV-26 Evidence Completeness
                  </span>
                  <span style={{ fontSize: '13px', fontWeight: 800, color: '#1e293b' }}>
                    {Math.round(evidenceScore * 100)}%
                  </span>
                </div>
                {missingAnchors.length > 0 && (
                  <ul style={{ margin: 0, paddingLeft: '14px', fontSize: '11px', color: '#475569' }}>
                    {missingAnchors.map((m, i) => <li key={i}>{m}</li>)}
                  </ul>
                )}
                {evidenceScore === 1.0 && (
                  <div style={{ fontSize: '11px', color: '#15803d', fontWeight: 600 }}>✓ All 6 evidence classes present</div>
                )}
              </div>

              {/* DV-27 Certainty Gate */}
              <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '4px', padding: '8px 10px', fontSize: '11.5px', color: '#1e293b' }}>
                <strong>
                  DV-27 Certainty Gate: {certaintyGatePassed ? '✓ OPEN ("Definite" Permitted)' : `🔒 RESTRICTED (Max: "${maxCertaintyAllowed}")`}
                </strong>
              </div>
            </div>

            {/* Box 4: Clinical Summary — Clean Neutral Card */}
            <div className="summary-feature-card" style={{ gridColumn: '1 / -1' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ color: 'var(--acrn-navy-dark)' }}>
                  <Info color="var(--acrn-navy-dark)" size={16} />
                  Synthesised Clinical Evidence Summary
                </h4>
                <span className="badge-tag">
                  <Bot size={11} style={{ display: 'inline', marginRight: '3px' }} />
                  {AI_ENGINE_MODEL}
                </span>
              </div>
              <div style={{
                marginTop: '8px',
                background: '#f8fafc',
                border: '1px solid #cbd5e1',
                borderRadius: '4px',
                padding: '10px 12px',
                fontSize: '12px',
                color: '#162035',
                whiteSpace: 'pre-wrap',
                lineHeight: '1.5'
              }}>
                {generateSummary(activeCase, dvResults)}
              </div>
            </div>

            {/* Box 5: Clinical Narrative Preview */}
            <div className="summary-feature-card" style={{ gridColumn: '1 / -1' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
                <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <FileText color="var(--acrn-navy-dark)" size={16} />
                  Blinded Clinical Narrative ({formCode})
                </h4>

                <button
                  type="button"
                  className="btn-primary"
                  style={{ fontSize: '11px', padding: '4px 10px' }}
                  onClick={handleRegenerateNarrative}
                  disabled={isGeneratingAi}
                >
                  <Bot size={13} />
                  {isGeneratingAi ? 'Synthesizing via AI Engine...' : '✨ Generate AI Narrative Summary'}
                </button>
              </div>

              {isGeneratingAi ? (
                <div style={{
                  padding: '20px',
                  textAlign: 'center',
                  background: '#f8fafc',
                  border: '1px dashed #cbd5e1',
                  borderRadius: '4px',
                  color: 'var(--acrn-navy-dark)',
                  fontSize: '12px',
                  fontWeight: 600
                }}>
                  <RefreshCw size={18} className="spin" color="var(--acrn-navy-dark)" style={{ margin: '0 auto 6px', display: 'block' }} />
                  🤖 AI Generative Engine: Synthesizing 13-section blinded clinical timeline for {activeCase.id}...
                </div>
              ) : (
                <pre style={{
                  marginTop: '6px',
                  background: '#ffffff',
                  padding: '12px',
                  borderRadius: '4px',
                  border: '1px solid #cbd5e1',
                  fontSize: '12px',
                  lineHeight: '1.5',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'monospace',
                  color: '#162035',
                  maxHeight: '240px',
                  overflowY: 'auto'
                }}>
                  {narrativeText}
                </pre>
              )}
            </div>
          </div>

          <div className="wizard-footer">
            <button className="btn-large btn-back" onClick={() => setCurrentStep(1)}>
              <ArrowLeft size={16} /> Back to Step 1
            </button>
            <button className="btn-large btn-next" onClick={() => setCurrentStep(3)}>
              Next: Approve Summary &amp; Sign <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // STEP 4: COMPLETED & SIGNED RECORD VIEW
  if (currentStep === 4 || (currentStep === 3 && isSigned)) {
    const sig = activeCase.signature || {
      signer: "Dr. Tinotenda Chibongore",
      email: "tinotenda.chibongore@acrnhealth.com",
      timestamp: new Date().toLocaleDateString() + ' ' + new Date().toLocaleTimeString(),
      hash: "SHA256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    };

    return (
      <div>
        <div className="wizard-card" style={{ borderLeft: '4px solid #15803d' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <div style={{ background: '#f0fdf4', color: '#15803d', width: '40px', height: '40px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <CheckCircle2 size={24} />
            </div>
            <div>
              <span className="badge-tag" style={{ background: '#f0fdf4', color: '#15803d', fontSize: '10.5px' }}>21 CFR Part 11 Lock Complete</span>
              <h2 style={{ fontSize: '17px', fontWeight: 700, color: 'var(--acrn-navy-dark)', marginTop: '2px' }}>
                Case {activeCase.caseNo} ({activeCase.id}) Finalized &amp; Filed to TMF
              </h2>
            </div>
          </div>

          <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '14px', marginBottom: '16px' }}>
            <h4 style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--acrn-navy-dark)', marginBottom: '8px' }}>
              Signature Audit Trail &amp; Checksum
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '12px' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Signed By:</span>
                <div style={{ fontWeight: 600 }}>{sig.signer} ({sig.email})</div>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Timestamp:</span>
                <div style={{ fontWeight: 600 }}>{sig.timestamp}</div>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Final Diagnosis:</span>
                <div style={{ fontWeight: 700, color: 'var(--acrn-navy-dark)' }}>{activeCase.derivedSubtype} • {activeCase.derivedSeverity}</div>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Cryptographic Hash:</span>
                <div style={{ fontWeight: 600, fontSize: '11px', color: 'var(--acrn-sky-blue)', wordBreak: 'break-all' }}>{sig.hash}</div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button className="btn-large btn-next" disabled={isDownloadingPdf} onClick={async () => {
              setIsDownloadingPdf(true);
              setPdfDownloadError('');
              try {
                await downloadPdfReport(activeCase.id);
              } catch (error) {
                setPdfDownloadError(error.message || 'Unable to download the TMF report.');
              } finally {
                setIsDownloadingPdf(false);
              }
            }}>
              <Download size={15} /> {isDownloadingPdf ? 'Preparing TMF PDF…' : 'Download Signed TMF PDF Report'}
            </button>

            <button className="btn-large btn-back" onClick={() => {
              const nextCase = cases.find(c => c.id !== activeCase.id && !c.status?.includes('Finalized'));
              if (nextCase) {
                onSelectCase(nextCase.id);
                setCurrentStep(1);
              } else {
                setCurrentStep(1);
              }
            }}>
              Proceed to Next Patient in Queue <ArrowRight size={15} />
            </button>
          </div>
          {pdfDownloadError && (
            <div role="alert" style={{ marginTop: '10px', color: 'var(--danger, #b42318)', fontSize: '12px', fontWeight: 600 }}>
              {pdfDownloadError} Confirm that the backend service is running, then try again.
            </div>
          )}
        </div>
      </div>
    );
  }

  // STEP 3: APPROVE CLINICAL SUMMARY & SIGN
  return (
    <div>
      <div className="wizard-card">
        <h2 className="wizard-title">Step 3: Approve Summary &amp; Sign Record ({activeCase.id})</h2>
        <p className="wizard-subtitle">Review the 13-section narrative draft ({formCode}), confirm your final diagnosis, and sign.</p>

        {/* Narrative Box */}
        <div style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
            <label style={{ fontWeight: 700, fontSize: '12.5px', color: 'var(--acrn-navy-dark)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Bot size={15} color="var(--acrn-navy-dark)" />
              {formCode} Blinded Case Narrative Draft
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                type="button"
                className="btn-primary"
                style={{ fontSize: '11px', padding: '3px 8px' }}
                onClick={handleRegenerateNarrative}
                disabled={isSigned || isGeneratingAi}
              >
                <Bot size={12} />
                {isGeneratingAi ? 'Synthesizing...' : '✨ Generate AI Narrative Summary'}
              </button>
            </div>
          </div>

          {isGeneratingAi ? (
            <div style={{
              padding: '20px',
              textAlign: 'center',
              background: '#f8fafc',
              border: '1px dashed #cbd5e1',
              borderRadius: '4px',
              color: 'var(--acrn-navy-dark)',
              fontSize: '12px',
              fontWeight: 600
            }}>
              <RefreshCw size={18} className="spin" color="var(--acrn-navy-dark)" style={{ margin: '0 auto 6px', display: 'block' }} />
              🤖 AI Generative Engine: Synthesizing 13-section blinded clinical timeline for {activeCase.id}...
            </div>
          ) : (
            <textarea
              className="narrative-box"
              style={{ height: '240px', fontFamily: 'monospace', fontSize: '12px', lineHeight: '1.45' }}
              value={narrativeText}
              onChange={(e) => setNarrativeText(e.target.value)}
              disabled={isSigned}
            />
          )}
        </div>

        {/* Diagnosis Selection */}
        <div className="summary-card-grid" style={{ marginBottom: '16px' }}>
          <div className="form-group">
            <label style={{ fontWeight: 700 }}>Final Adjudication Diagnosis</label>
            <select
              className="form-select"
              value={selectedDiagnosis}
              onChange={(e) => setSelectedDiagnosis(e.target.value)}
              disabled={isSigned}
            >
              <option value="Pre-eclampsia">Pre-eclampsia</option>
              <option value="Gestational hypertension">Gestational hypertension</option>
              <option value="Chronic HTN">Chronic HTN</option>
              <option value="Superimposed PE">Superimposed PE</option>
              <option value="Eclampsia">Eclampsia</option>
              <option value="HELLP Syndrome">HELLP Syndrome</option>
            </select>
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 700 }}>Severity &amp; Phenotype</label>
            <select
              className="form-select"
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              disabled={isSigned}
            >
              <option value="With severe features">With severe features</option>
              <option value="Without severe features">Without severe features</option>
              <option value="Eclampsia / severe SAE">Eclampsia / severe SAE</option>
              <option value="Severity requires review">Severity requires review</option>
            </select>
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 700 }}>Onset Classification</label>
            <select
              className="form-select"
              value={selectedOnset}
              onChange={(e) => setSelectedOnset(e.target.value)}
              disabled={isSigned}
            >
              <option value="Early-onset pre-eclampsia (EOPE)">Early-onset pre-eclampsia (EOPE)</option>
              <option value="Late-onset pre-eclampsia (LOPE)">Late-onset pre-eclampsia (LOPE)</option>
              <option value="Postpartum-only presentation">Postpartum-only presentation</option>
              <option value="Onset not yet classifiable">Onset not yet classifiable</option>
            </select>
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label style={{ fontWeight: 700 }}>Diagnostic Certainty</label>
              <span style={{
                fontSize: '10.5px',
                fontWeight: 600,
                padding: '1px 6px',
                borderRadius: '4px',
                background: '#f8fafc',
                color: '#1e293b',
                border: '1px solid #cbd5e1'
              }}>
                DV-27 Gate: {certaintyGatePassed ? '✓ OPEN' : `🔒 RESTRICTED (Max: ${maxCertaintyAllowed})`}
              </span>
            </div>
            <select
              className="form-select"
              value={selectedCertainty}
              onChange={(e) => setSelectedCertainty(e.target.value)}
              disabled={isSigned}
            >
              <option
                value="Definite"
                disabled={!certaintyGatePassed}
                style={{ color: certaintyGatePassed ? 'inherit' : '#94a3b8' }}
              >
                {certaintyGatePassed ? 'Definite — All criteria met (100% evidence)' : 'Definite — 🔒 Locked (incomplete evidence, DV-27)'}
              </option>
              <option value="Probable">Probable — Criteria met, evidence partial</option>
              <option value="Possible">Possible — Clinical judgment required</option>
              <option value="Not PE">Not PE — Does not meet diagnostic criteria</option>
            </select>
          </div>
        </div>

        <div className="wizard-footer">
          <button className="btn-large btn-back" onClick={() => setCurrentStep(2)}>
            <ArrowLeft size={15} /> Back to Step 2
          </button>

          <button className="btn-large btn-next" onClick={onOpenSignature}>
            <ShieldCheck size={16} /> Sign &amp; Lock Adjudication Record
          </button>
        </div>
      </div>
    </div>
  );
}
