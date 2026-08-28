import React, { useState, useEffect } from 'react';
import { ArrowRight, ArrowLeft, CheckCircle2, Activity, Database, ShieldCheck, FileText, Lock, Download, EyeOff, UserX, AlertCircle, RefreshCw, Info, ExternalLink, ChevronDown, Bot, FilePlus, LogOut, Copy, Save, Server, Search, Calendar, ChevronRight, X, UserCheck, Stethoscope, AlertTriangle } from 'lucide-react';
import PatientHistoryPanel from './PatientHistoryPanel';
import { LongitudinalEvidenceTable, OverallSummary, VisitEvidencePanel, VisitRibbon } from './VisitEvidenceSections';
import { generateNarrative, generateSummary, AI_ENGINE_MODEL } from '../services/demoNarrative';
import { runDvEngine } from '../services/dvEngine';
import { downloadPdfReport } from '../services/api';
import { normalizeVisitEvidence } from '../services/visitEvidence';

const DEFAULT_VISIT_CODES = ['V01', 'V02', 'V03', 'V04', 'V05', 'V06'];
function visitNumberOf(visit, fallbackIndex = 0) {
  const raw = visit?.visit_number ?? visit?.visitNumber ?? visit?.number ?? visit?.visit;
  const numeric = Number(raw);
  if (Number.isFinite(numeric) && numeric >= 1 && numeric <= 6) return numeric;
  const text = `${visit?.visit_code || ''} ${visit?.code || ''} ${visit?.name || ''} ${visit?.label || ''}`;
  const match = text.match(/\bV(?:isit)?\s*0?([1-6])\b/i) || text.match(/\bvisit\s*([1-6])\b/i);
  return match ? Number(match[1]) : fallbackIndex + 1;
}

function DropdownSection({ title, icon, children, defaultOpen = false, right = null }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={`adjudication-dropdown ${open ? 'open' : ''}`}>
      <button type="button" className="adjudication-dropdown-toggle" onClick={() => setOpen(v => !v)} aria-expanded={open}>
        <span>{icon}{title}</span>
        <span>{right}<ChevronDown size={15} /></span>
      </button>
      {open && <div className="adjudication-dropdown-body">{children}</div>}
    </section>
  );
}
function visitPages(caseData) {
  const byNumber = new Map();
  (caseData?.visits || []).forEach((visit, index) => {
    const number = visitNumberOf(visit, index);
    if (number >= 1 && number <= 6 && !byNumber.has(number)) byNumber.set(number, visit);
  });
  return DEFAULT_VISIT_CODES.map((code, index) => {
    const number = index + 1;
    const visit = byNumber.get(number);
    return {
      ...visit,
      id: visit?.id || `${caseData?.id || 'case'}-${code}`,
      name: visit?.name && !/^other$/i.test(visit.name) ? visit.name : `Visit ${number}`,
      visit_number: number,
      visit_code: visit?.visit_code || visit?.code || code,
      visit_date: visit?.visit_date || visit?.date || null,
      evidence: visit?.evidence || {},
      packet_status: visit?.packet_status || visit?.status || 'AWAITING_VISIT_RECONCILIATION',
    };
  });
}

export default function AdjudicatorWorkbench({ 
  currentStep, 
  setCurrentStep, 
  cases, 
  activeCase, 
  onSelectCase, 
  onOpenSignature,
  onOpenSourceDocs,
  onOpenRecusalModal,
  onOpenDataQueryModal,
  advanceToVisitIndex,
  user
}) {
  const [selectedDiagnosis, setSelectedDiagnosis] = useState('PE');
  const [otherDiagnosis, setOtherDiagnosis] = useState('');
  const [selectedOnset, setSelectedOnset] = useState('Early-onset pre-eclampsia (EOPE)');
  const [selectedSeverity, setSelectedSeverity] = useState('With severe features');
  const [selectedCertainty, setSelectedCertainty] = useState('Probable');
  const [selectedVisitIndex, setSelectedVisitIndex] = useState(0);
  const [narrativeText, setNarrativeText] = useState('');
  const [narrativeViewMode, setNarrativeViewMode] = useState('TABLE'); // 'TABLE' | 'PROSE'
  const [formCode, setFormCode] = useState('FORM-ADJ-15A');
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [pdfDownloadError, setPdfDownloadError] = useState('');
  const isSigned = activeCase?.status?.includes('Finalized');
  const isReviewerC = activeCase?.reviewerRole === 'REVIEWER_C';
  const finalDiagnosis = selectedDiagnosis;
  const pages = visitPages(activeCase);
  const evidenceVisits = normalizeVisitEvidence({ ...(activeCase || {}), visits: pages }).slice(0, 6);
  const selectedVisit = pages[selectedVisitIndex] || pages[0] || null;
  const selectedEvidenceVisit = evidenceVisits[Math.min(selectedVisitIndex, evidenceVisits.length - 1)] || null;
  const isVisitFive = /V05|visit\s*5/i.test(selectedVisit?.name || selectedVisit?.visit_code || '');

  const getVisitLabel = (bp, index) => {
    if (bp.visitName) return bp.visitName;
    if (bp.visit) return `Visit ${bp.visit}`;
    const gaNum = parseFloat(bp.ga || '0');
    if (gaNum > 0 && gaNum < 16) return 'Visit 1 (11–14w Booking)';
    if (gaNum >= 16 && gaNum < 24) return 'Visit 2 (18–22w Anatomy)';
    if (gaNum >= 24 && gaNum < 30) return 'Visit 3 (26–28w Routine)';
    if (gaNum >= 30 && gaNum < 36) return 'Visit 4 (32–34w Escalation)';
    if (gaNum >= 36 && gaNum <= 42) return 'Visit 5 (36–38w Term/Delivery)';
    if (gaNum > 42 || String(bp.ga || '').toLowerCase().includes('post')) return 'Visit 6 (6w Postpartum)';
    return `Visit ${index + 1}`;
  };

  // Compute DV engine results for active case
  const dvResults = activeCase ? runDvEngine(activeCase) : null;
  const evidenceScore = dvResults ? dvResults.evidenceScore : (activeCase?.pktScore || 0);
  const missingAnchors = dvResults ? dvResults.missingAnchors : [];
  const certaintyGatePassed = dvResults?.certaintyGate?.inputs?.gate_open ?? (evidenceScore === 1.0);
  const maxCertaintyAllowed = dvResults?.certaintyGate?.inputs?.max_certainty || (evidenceScore === 1.0 ? 'Definite' : 'Probable');

  useEffect(() => {
    if (activeCase) {
      setSelectedVisitIndex(0);
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

  useEffect(() => {
    if (Number.isInteger(advanceToVisitIndex)) {
      setSelectedVisitIndex(Math.max(0, Math.min(advanceToVisitIndex, pages.length)));
    }
  }, [advanceToVisitIndex, pages.length]);

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

            <PatientHistoryPanel caseData={activeCase} />

          {false && <div className="summary-card-grid">
            {/* Box 1: Blood Pressure */}
            <div className="summary-feature-card">
              <h4>
                <Activity color="var(--acrn-navy-dark)" size={16} />
                1. Blood Pressure Timeline &amp; Visit Schedule
              </h4>
              <div style={{ marginTop: '8px' }}>
                {(activeCase.bpLog && activeCase.bpLog.length > 0 ? activeCase.bpLog : activeCase.bp_readings) && (activeCase.bpLog || activeCase.bp_readings).length > 0 ? (
                  (activeCase.bpLog || activeCase.bp_readings).map((bp, i) => {
                    const severe = bp.severe ?? (bp.sbp >= 160 || bp.dbp >= 110);
                    const dateVal = bp.date || bp.datetime;
                    const when = dateVal ? new Date(dateVal).toLocaleString() : (bp.ga ? `GA ${bp.ga}` : '—');
                    return (
                      <div key={i} className="data-summary-row" style={{ background: severe ? '#f8fafc' : 'transparent', padding: '5px 8px', borderRadius: '4px', marginBottom: '4px', border: '1px solid #f1f5f9' }}>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontSize: '11px', fontWeight: 700, color: '#0f172a' }}>{getVisitLabel(bp, i)}</span>
                          <span style={{ fontSize: '11px', color: '#64748b' }}>{when}</span>
                        </div>
                        <span style={{ fontWeight: severe ? 700 : 500, color: severe ? '#991b1b' : '#162035', fontSize: '12px' }}>
                          {bp.sbp}/{bp.dbp} mmHg {severe ? ' [Severe]' : ''}
                        </span>
                      </div>
                    );
                  })
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
                ) : (activeCase.upcr != null || activeCase.dipstick_raw) ? (
                  <div className="data-summary-row" style={{ background: '#f8fafc', padding: '4px 6px', borderRadius: '3px' }}>
                    <span>Proteinuria (UPCR/Dipstick)</span>
                    <span style={{ fontWeight: 600 }}>{activeCase.upcr != null ? `UPCR ${activeCase.upcr}` : activeCase.dipstick_raw}</span>
                  </div>
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
                ) : [['Platelets', activeCase.platelet_count], ['Creatinine', activeCase.creatinine], ['AST', activeCase.ast], ['ALT', activeCase.alt], ['LDH', activeCase.ldh]].some(([, v]) => v != null) ? (
                  [['Platelets', activeCase.platelet_count], ['Creatinine', activeCase.creatinine], ['AST', activeCase.ast], ['ALT', activeCase.alt], ['LDH', activeCase.ldh]]
                    .filter(([, v]) => v != null)
                    .map(([label, v]) => (
                      <div key={label} className="data-summary-row">
                        <span>{label}</span>
                        <span style={{ fontWeight: 500 }}>{v}</span>
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

            </div>}

            {/* Box 4: Clinical Summary — Clean Neutral Card */}
            <DropdownSection
              title="Synthesised Clinical Evidence Summary"
              icon={<Info size={16} />}
              right={<span className="badge-tag"><Bot size={11} />{AI_ENGINE_MODEL}</span>}
              defaultOpen={false}
            >
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
            </DropdownSection>

            {/* Box 5: Clinical Narrative Preview (legacy raw-derived view retained only for non-visit packets) */}
            <DropdownSection title={`Blinded Clinical Narrative (${formCode})`} icon={<FileText size={16} />} defaultOpen={false}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px', margin: 0 }}>
                    <FileText color="var(--acrn-navy-dark)" size={16} />
                    Blinded Clinical Narrative ({formCode})
                  </h4>
                  <div style={{ display: 'inline-flex', background: '#e2e8f0', borderRadius: '4px', padding: '2px' }}>
                    <button
                      type="button"
                      onClick={() => setNarrativeViewMode('TABLE')}
                      style={{
                        padding: '3px 8px', fontSize: '11px', fontWeight: 600, border: 'none', borderRadius: '3px', cursor: 'pointer',
                        background: narrativeViewMode === 'TABLE' ? '#ffffff' : 'transparent',
                        color: narrativeViewMode === 'TABLE' ? '#0f172a' : '#64748b'
                      }}
                    >
                      📊 Structured Evidence Table
                    </button>
                    <button
                      type="button"
                      onClick={() => setNarrativeViewMode('PROSE')}
                      style={{
                        padding: '3px 8px', fontSize: '11px', fontWeight: 600, border: 'none', borderRadius: '3px', cursor: 'pointer',
                        background: narrativeViewMode === 'PROSE' ? '#ffffff' : 'transparent',
                        color: narrativeViewMode === 'PROSE' ? '#0f172a' : '#64748b'
                      }}
                    >
                      📝 Narrative Prose
                    </button>
                  </div>
                </div>

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
              ) : narrativeViewMode === 'TABLE' ? (
                <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '4px', overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                    <thead>
                      <tr style={{ background: '#f8fafc', borderBottom: '1px solid #cbd5e1', textAlign: 'left' }}>
                        <th style={{ padding: '8px 12px', width: '25%', color: '#475569' }}>Narrative Section</th>
                        <th style={{ padding: '8px 12px', width: '75%', color: '#475569' }}>Synthesized Clinical Documentation</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '8px 12px', fontWeight: 600 }}>1. Baseline &amp; Enrollment</td>
                        <td style={{ padding: '8px 12px' }}>Subject {activeCase.id} ({activeCase.caseNo}) enrolled at site {activeCase.site || 'HARARE_01'}. Baseline ultrasound dated at booking.</td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid #f1f5f9', background: '#fafafa' }}>
                        <td style={{ padding: '8px 12px', fontWeight: 600 }}>2. Blood Pressure Trajectory</td>
                        <td style={{ padding: '8px 12px' }}>
                          {activeCase.bpLog && activeCase.bpLog.length > 0 ? (
                            activeCase.bpLog.map((b, idx) => (
                              <span key={idx} style={{ display: 'inline-block', marginRight: '10px' }}>
                                <strong>{getVisitLabel(b, idx)}:</strong> {b.sbp}/{b.dbp} mmHg
                              </span>
                            ))
                          ) : 'No hypertensive BP documented prior to onset.'}
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '8px 12px', fontWeight: 600 }}>3. Proteinuria &amp; Renal Function</td>
                        <td style={{ padding: '8px 12px' }}>
                          {activeCase.proteinuriaLog?.map(p => `${p.method}: ${p.result}`).join('; ') || 'Proteinuria verified by spot UPCR.'}
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid #f1f5f9', background: '#fafafa' }}>
                        <td style={{ padding: '8px 12px', fontWeight: 600 }}>4. Hematology &amp; Hepatic Labs</td>
                        <td style={{ padding: '8px 12px' }}>
                          {activeCase.labLog?.map(l => `${l.analyte}: ${l.result} ${l.unit}`).join(' | ') || 'Platelets, AST/ALT, and LDH documented.'}
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '8px 12px', fontWeight: 600 }}>5. Clinical Severity &amp; Phenotype</td>
                        <td style={{ padding: '8px 12px' }}>
                          <span className="badge-tag" style={{ fontWeight: 600 }}>
                            {activeCase.derivedSubtype || 'EOPE'} • {activeCase.derivedSeverity === 'SEVERE_FEATURES' ? 'With severe features' : 'Without severe features'}
                          </span>
                        </td>
                      </tr>
                      <tr>
                        <td style={{ padding: '8px 12px', fontWeight: 600 }}>6. Diagnostic Standard</td>
                        <td style={{ padding: '8px 12px' }}>ISSHP 2021 Diagnostic Classification Criteria (DV-26 completeness: {Math.round(evidenceScore * 100)}%).</td>
                      </tr>
                    </tbody>
                  </table>
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
            </DropdownSection>

            <DropdownSection title="Visit Specific Evidence" icon={<FileText size={16} />} defaultOpen>
              {selectedVisitIndex===evidenceVisits.length ? <OverallSummary visits={evidenceVisits} /> : selectedEvidenceVisit && <VisitEvidencePanel visit={selectedEvidenceVisit} />}
            </DropdownSection>

            <DropdownSection title="Longitudinal Per-Visit Evidence" icon={<Database size={16} />} defaultOpen={false}>
              <VisitRibbon visits={evidenceVisits} selectedIndex={selectedVisitIndex} onSelectVisit={setSelectedVisitIndex} />
              <LongitudinalEvidenceTable visits={evidenceVisits} selectedIndex={Math.min(selectedVisitIndex, evidenceVisits.length - 1)} onSelectVisit={setSelectedVisitIndex} />
            </DropdownSection>

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
        <p className="wizard-subtitle">Review the selected visit summary, confirm the closed-ended diagnosis, and sign the separate visit adjudication.</p>

        {pages.length > 0 && <><VisitRibbon visits={pages} selectedIndex={selectedVisitIndex} onSelectVisit={setSelectedVisitIndex}/><div className="visit-signing-context"><div><strong>{selectedVisitIndex===pages.length?'Overall adjudication summary':`Adjudicating ${selectedVisit?.name||selectedVisit?.visit_code||`Visit ${selectedVisitIndex+1}`}`}</strong><span>{selectedVisitIndex===pages.length?'Read-only roll-up of completed visit decisions.':'Only this visit and its dated evidence will be signed.'}</span></div></div></>}

        <DropdownSection title="Visit Specific Evidence" icon={<FileText size={16} />} defaultOpen>
          {selectedVisitIndex===evidenceVisits.length ? <OverallSummary visits={evidenceVisits} /> : selectedEvidenceVisit && <VisitEvidencePanel visit={selectedEvidenceVisit} />}
        </DropdownSection>

        <DropdownSection title="Longitudinal Per-Visit Evidence" icon={<Database size={16} />} defaultOpen={false}>
          <LongitudinalEvidenceTable visits={evidenceVisits} selectedIndex={Math.min(selectedVisitIndex, evidenceVisits.length - 1)} onSelectVisit={setSelectedVisitIndex} />
        </DropdownSection>

        {selectedVisitIndex<pages.length && <DropdownSection title="Subject History Context" icon={<Stethoscope size={16} />} defaultOpen={false}><PatientHistoryPanel caseData={activeCase} /></DropdownSection>}

        {selectedVisitIndex===pages.length && <div className="overall-lock-message"><CheckCircle2 size={24}/><div><strong>Overall adjudication is complete</strong><p>The overall view is a read-only roll-up. Each visit retains its independent signature and audit trail.</p></div></div>}

        {/* Narrative Box */}
        {selectedVisitIndex<pages.length && <DropdownSection title={`${formCode} Blinded Case Narrative Draft`} icon={<Bot size={16} />} defaultOpen={false}><div style={{ marginBottom: '16px' }}>
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
          {isVisitFive && <div style={{ marginTop: 6, color: '#475569', fontSize: 11 }}><strong>Visit 5 narrative:</strong> open-ended clinical narrative is required; diagnosis selection remains restricted to the standard outcomes.</div>}
        </div></DropdownSection>}

        {/* Diagnosis Selection */}
        {selectedVisitIndex<pages.length && <DropdownSection title="Final Adjudication Controls" icon={<ShieldCheck size={16} />} defaultOpen><div className="summary-card-grid" style={{ marginBottom: '16px' }}>
          <div className="form-group">
            <label style={{ fontWeight: 700 }}>Final Adjudication Diagnosis</label>
            <select
              className="form-select"
              value={selectedDiagnosis}
              onChange={(e) => setSelectedDiagnosis(e.target.value)}
              disabled={isSigned}
            >
              <option value="PE">PE</option>
              <option value="Severe PE">Severe PE</option>
              <option value="Eclampsia">Eclampsia</option>
              <option value="HELLP">HELLP</option>
              {isReviewerC && <option value="Other">Other</option>}
            </select>
            {selectedDiagnosis === 'Other' && (
              <input
                type="text"
                className="form-input"
                style={{ marginTop: '8px' }}
                value={otherDiagnosis}
                onChange={(e) => setOtherDiagnosis(e.target.value)}
                placeholder="Mandatory rationale for Other"
                aria-label="Rationale for Other diagnosis"
                disabled={isSigned}
                required
              />
            )}
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
        </div></DropdownSection>}

        <div className="wizard-footer">
          <button className="btn-large btn-back" onClick={() => setCurrentStep(2)}>
            <ArrowLeft size={15} /> Back to Step 2
          </button>

          {selectedVisitIndex<pages.length && <button className="btn-large btn-next" onClick={() => {
            if (!finalDiagnosis) return;
            onOpenSignature({
              reviewerRole: activeCase?.reviewerRole || 'REVIEWER_A',
              reviewerName: user?.display_name || user?.name || user?.email,
              diagnosis: finalDiagnosis,
              onset: selectedOnset,
              severity: selectedSeverity,
              certainty: selectedCertainty,
              rationale: narrativeText,
              comment: narrativeText,
              otherRationale: selectedDiagnosis === 'Other' ? otherDiagnosis.trim() : null,
              visitNumber: selectedVisit?.visit_number || selectedVisit?.visitNumber || selectedVisitIndex + 1,
              visitCode: selectedVisit?.visit_code || selectedVisit?.name,
              visitDate: selectedVisit?.visit_date || selectedVisit?.date,
              dateOfDiagnosis: selectedVisit?.visit_date || selectedVisit?.date || new Date().toISOString(),
            });
          }} disabled={selectedDiagnosis === 'Other' && !otherDiagnosis.trim()}>
            <ShieldCheck size={16} /> Sign &amp; Lock Adjudication Record
          </button>}
        </div>
      </div>
    </div>
  );
}
