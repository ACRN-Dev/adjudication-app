import React, { useState, useEffect } from 'react';
import { ArrowRight, ArrowLeft, CheckCircle2, Activity, Database, ShieldCheck, FileText, Lock, Download, EyeOff, UserX, AlertCircle, RefreshCw, Info, ExternalLink, ChevronDown, Bot, FilePlus, LogOut, Copy, Save, Server, Search, Calendar, ChevronRight, X, UserCheck, Stethoscope, AlertTriangle } from 'lucide-react';
import PatientHistoryPanel from './PatientHistoryPanel';
import { OverallSummary, VisitEvidencePanel, VisitRibbon } from './VisitEvidenceSections';
import { generateNarrative, generateSummary, AI_ENGINE_MODEL } from '../services/demoNarrative';
import { runDvEngine } from '../services/dvEngine';
import { downloadPdfReport } from '../services/api';
import { isReviewerVisitSigned, isVisitComplete, normalizeVisitEvidence } from '../services/visitEvidence';

const DEFAULT_VISIT_CODES = ['V01', 'V02', 'V03', 'V04', 'V05', 'V06'];

export const VISIT5_ASSESSMENT_OPTIONS = [
  { code: 'PERINATAL_FETAL_DEATH', label: 'Perinatal / fetal death', adverse: true },
  { code: 'DELIVERY_GE_37W', label: 'Delivery at or after 37 weeks', adverse: false },
  { code: 'DELIVERY_LT_34W', label: 'Delivery before 34 weeks', adverse: true },
  { code: 'IUGR', label: 'IUGR (Intrauterine Growth Restriction)', adverse: true },
  { code: 'SGA', label: 'SGA (Small for Gestational Age)', adverse: true },
  { code: 'NORMAL_OUTCOME', label: 'Normal fetal / neonatal outcome, where clinically approved', adverse: false, isNormal: true },
];
function visitNumberOf(visit, fallbackIndex = 0) {
  const raw = visit?.visit_number ?? visit?.visitNumber ?? visit?.number ?? visit?.visit;
  const numeric = Number(raw);
  if (Number.isFinite(numeric) && numeric >= 1 && numeric <= 6) return numeric;
  const text = `${visit?.visit_code || ''} ${visit?.code || ''} ${visit?.name || ''} ${visit?.label || ''}`;
  const match = text.match(/\bV(?:isit)?\s*0?([1-6])\b/i) || text.match(/\bvisit\s*([1-6])\b/i);
  return match ? Number(match[1]) : fallbackIndex + 1;
}

function toDateTimeLocal(value) {
  if (!value) return '';
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(text)) return text.slice(0, 16);
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const pad = number => String(number).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
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
  const [meetsCriteria, setMeetsCriteria] = useState(true);
  const [otherDiagnosis, setOtherDiagnosis] = useState('');
  const [differentialDiagnosis, setDifferentialDiagnosis] = useState('');
  const [selectedOnset, setSelectedOnset] = useState('Early-onset pre-eclampsia (EOPE)');
  const [selectedSeverity, setSelectedSeverity] = useState('With severe features');
  const [selectedCertainty, setSelectedCertainty] = useState('Probable');
  const [selectedVisitIndex, setSelectedVisitIndex] = useState(0);
  const [visitDecisions, setVisitDecisions] = useState({});
  const [narrativeText, setNarrativeText] = useState('');
  const [visitNarratives, setVisitNarratives] = useState({});
  const [longitudinalComment, setLongitudinalComment] = useState('');
  const [firstPeVisitNumber, setFirstPeVisitNumber] = useState('');
  const [firstPeDate, setFirstPeDate] = useState('');
  const [diagnosisDateTime, setDiagnosisDateTime] = useState('');
  const [narrativeViewMode, setNarrativeViewMode] = useState('PROSE'); // 'TABLE' | 'PROSE'
  const [formCode, setFormCode] = useState('FORM-ADJ-15A');
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [pdfDownloadError, setPdfDownloadError] = useState('');
  const [fetalNeonatalAssessments, setFetalNeonatalAssessments] = useState([]);
  const [gestationalAgeAtDelivery, setGestationalAgeAtDelivery] = useState('');
  const [pregnancyOutcome, setPregnancyOutcome] = useState('Normal baby');
  const [fetalProvenance, setFetalProvenance] = useState({});
  const [visit5MappingLoading, setVisit5MappingLoading] = useState(false);
  const [visit5ValidationWarning, setVisit5ValidationWarning] = useState('');
  const [caseProgress, setCaseProgress] = useState(null);
  const isSigned = activeCase?.status?.includes('Finalized');
  const isReviewerC = activeCase?.reviewerRole === 'REVIEWER_C';
  const finalDiagnosis = selectedDiagnosis;
  const pages = visitPages(activeCase);
  const evidenceVisits = normalizeVisitEvidence({ ...(activeCase || {}), visits: pages }).slice(0, 6);
  const selectedVisit = pages[selectedVisitIndex] || pages[0] || null;
  const selectedEvidenceVisit = evidenceVisits[Math.min(selectedVisitIndex, evidenceVisits.length - 1)] || null;
  const isVisitFive = /V05|visit\s*5/i.test(selectedVisit?.name || selectedVisit?.visit_code || '') || selectedVisit?.visit_number === 5;
  const firstUnsignedVisitIndex = pages.findIndex((visit) => !isReviewerVisitSigned(visit));
  const allReviewerVisitsSigned = pages.length > 0 && firstUnsignedVisitIndex === -1;
  const allVisitsFinalized = pages.length > 0 && pages.every(isVisitComplete);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [currentStep, selectedVisitIndex, advanceToVisitIndex]);

  useEffect(() => {
    if (currentStep !== 1) return;
    let cancelled = false;
    fetch('/api/realtime/progress', { credentials: 'include' })
      .then(response => response.ok ? response.json() : null)
      .then(payload => {
        if (!cancelled && payload) setCaseProgress(payload);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [currentStep, user?.email]);

  if (currentStep > 1 && !activeCase) {
    return (
      <div className="wizard-card">
        <h2 className="wizard-title">No adjudication case selected</h2>
        <p className="wizard-subtitle">Select an assigned subject from the queue before opening evidence or signing a determination.</p>
        <button className="btn-large btn-back" onClick={() => setCurrentStep(1)}>
          <ArrowLeft size={15} /> Return to Subject Queue
        </button>
      </div>
    );
  }

  const decisionSnapshot = () => ({
    selectedDiagnosis,
    meetsCriteria,
    otherDiagnosis,
    differentialDiagnosis,
    selectedOnset,
    selectedSeverity,
    selectedCertainty,
    narrativeText,
    diagnosisDateTime,
    fetalNeonatalAssessments,
    gestationalAgeAtDelivery,
    pregnancyOutcome,
    fetalProvenance,
  });

  const handleVisitSelect = (nextIndex) => {
    if (nextIndex === selectedVisitIndex) return;
    if (selectedVisitIndex < pages.length) {
      setVisitDecisions(current => ({ ...current, [selectedVisitIndex]: decisionSnapshot() }));
    }
    const saved = visitDecisions[nextIndex];
    if (saved) {
      setSelectedDiagnosis(saved.selectedDiagnosis);
      setMeetsCriteria(saved.meetsCriteria);
      setOtherDiagnosis(saved.otherDiagnosis);
      setDifferentialDiagnosis(saved.differentialDiagnosis);
      setSelectedOnset(saved.selectedOnset);
      setSelectedSeverity(saved.selectedSeverity);
      setSelectedCertainty(saved.selectedCertainty);
      setNarrativeText(saved.narrativeText);
      setDiagnosisDateTime(saved.diagnosisDateTime);
      if (saved.fetalNeonatalAssessments !== undefined) {
        setFetalNeonatalAssessments(saved.fetalNeonatalAssessments);
        setGestationalAgeAtDelivery(saved.gestationalAgeAtDelivery || '');
        setPregnancyOutcome(saved.pregnancyOutcome || 'Normal baby');
        setFetalProvenance(saved.fetalProvenance || {});
      }
    } else if (nextIndex < pages.length) {
      setSelectedDiagnosis('PE');
      setMeetsCriteria(true);
      setOtherDiagnosis('');
      setDifferentialDiagnosis('');
      setSelectedOnset('Early-onset pre-eclampsia (EOPE)');
      setSelectedSeverity('With severe features');
      setSelectedCertainty('Probable');
      setNarrativeText('');
      setDiagnosisDateTime(toDateTimeLocal(pages[nextIndex]?.visit_date || pages[nextIndex]?.date));
      if (nextIndex + 1 === 5) {
        setFetalNeonatalAssessments([]);
        setGestationalAgeAtDelivery('');
        setPregnancyOutcome('Normal baby');
      }
    }
    setSelectedVisitIndex(nextIndex);
  };

  const handleToggleAssessment = (code) => {
    if (isSigned) return;
    setFetalNeonatalAssessments(prev => {
      const next = new Set(prev);
      if (next.has(code)) {
        next.delete(code);
      } else {
        if (code === 'NORMAL_OUTCOME') {
          next.delete('PERINATAL_FETAL_DEATH');
          next.delete('DELIVERY_LT_34W');
          next.delete('IUGR');
          next.delete('SGA');
        } else if (['PERINATAL_FETAL_DEATH', 'DELIVERY_LT_34W', 'IUGR', 'SGA'].includes(code)) {
          next.delete('NORMAL_OUTCOME');
        }
        if (code === 'DELIVERY_GE_37W') {
          next.delete('DELIVERY_LT_34W');
        } else if (code === 'DELIVERY_LT_34W') {
          next.delete('DELIVERY_GE_37W');
        }
        next.add(code);
      }
      return Array.from(next);
    });
  };

  useEffect(() => {
    if (!activeCase?.id || !isVisitFive) return;
    let isCancelled = false;
    setVisit5MappingLoading(true);
    fetch(`/api/adjudication/${encodeURIComponent(activeCase.id)}/visit-5-mapping`, {
      credentials: 'include',
    })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (isCancelled || !data) return;
        setFetalProvenance(data.assessments || {});
        setFetalNeonatalAssessments(prev => (prev.length > 0 ? prev : (data.suggested_assessments || [])));
        setGestationalAgeAtDelivery(prev => (prev !== '' ? prev : (data.gestational_age_at_delivery != null ? String(data.gestational_age_at_delivery) : '')));
        setPregnancyOutcome(prev => (prev !== '' ? prev : (data.pregnancy_outcome || 'Normal baby')));
      })
      .catch(() => {})
      .finally(() => {
        if (!isCancelled) setVisit5MappingLoading(false);
      });
    return () => { isCancelled = true; };
  }, [activeCase?.id, isVisitFive]);

  useEffect(() => {
    if (!isVisitFive) {
      setVisit5ValidationWarning('');
      return;
    }
    const selected = new Set(fetalNeonatalAssessments);
    if (selected.has('NORMAL_OUTCOME')) {
      const adversePresent = ['PERINATAL_FETAL_DEATH', 'DELIVERY_LT_34W', 'IUGR', 'SGA'].filter(c => selected.has(c));
      if (adversePresent.length > 0) {
        setVisit5ValidationWarning(
          `Normal fetal / neonatal outcome cannot coexist with adverse outcome(s): ${adversePresent.join(', ')}.`
        );
        return;
      }
    }
    if (selected.has('DELIVERY_GE_37W') && selected.has('DELIVERY_LT_34W')) {
      setVisit5ValidationWarning(
        "A delivery cannot be both 'Delivery at or after 37 weeks' and 'Delivery before 34 weeks'."
      );
      return;
    }
    const gaNum = parseFloat(gestationalAgeAtDelivery);
    if (!Number.isNaN(gaNum)) {
      if (selected.has('DELIVERY_GE_37W') && gaNum < 37.0) {
        setVisit5ValidationWarning(`Gestational age (${gaNum} weeks) contradicts 'Delivery at or after 37 weeks'.`);
        return;
      }
      if (selected.has('DELIVERY_LT_34W') && gaNum >= 34.0) {
        setVisit5ValidationWarning(`Gestational age (${gaNum} weeks) contradicts 'Delivery before 34 weeks'.`);
        return;
      }
    }
    if (selected.has('PERINATAL_FETAL_DEATH') && pregnancyOutcome.toLowerCase() === 'normal baby') {
      setVisit5ValidationWarning("Perinatal / fetal death cannot be selected when pregnancy outcome is 'Normal baby'.");
      return;
    }
    setVisit5ValidationWarning('');
  }, [isVisitFive, fetalNeonatalAssessments, gestationalAgeAtDelivery, pregnancyOutcome]);

  const getVisitLabel = (bp, index) => {
    if (bp.visitName) return bp.visitName;
    if (bp.visit) return `Visit ${bp.visit}`;
    const gaNum = parseFloat(bp.ga || '0');
    if (gaNum >= 16 && gaNum < 24) return 'Visit 2 (18–22w Anatomy)';
    if (gaNum >= 24 && gaNum < 30) return 'Visit 3 (26–28w Routine)';
    if (gaNum >= 30 && gaNum < 36) return 'Visit 4 (32–34w Escalation)';
    if (gaNum >= 36 && gaNum <= 42) return 'Visit 5 (36–38w Term/Delivery)';
    if (gaNum > 42 || String(bp.ga || '').toLowerCase().includes('post')) return 'Visit 6 (6w Postpartum)';
    return `Visit ${index + 1}`;
  };

  // Compute DV engine results for active case
  const dvResults = activeCase ? runDvEngine(activeCase) : null;
  const evidenceScore = selectedEvidenceVisit?.interpretation?.completeness != null
    ? selectedEvidenceVisit.interpretation.completeness / 100
    : (dvResults ? dvResults.evidenceScore : (activeCase?.pktScore || 0));
  const missingAnchors = selectedEvidenceVisit?.interpretation?.missing || dvResults?.missingAnchors || [];
  const certaintyGatePassed = selectedEvidenceVisit
    ? selectedEvidenceVisit.interpretation.missing.length === 0
    : (dvResults?.certaintyGate?.inputs?.gate_open ?? evidenceScore === 1.0);
  const maxCertaintyAllowed = certaintyGatePassed ? 'Definite' : 'Probable';

  useEffect(() => {
    if (activeCase) {
      setSelectedVisitIndex(0);
      setVisitDecisions({});
      const generated = generateNarrative(activeCase);
      setNarrativeText(generated.fullText);
      setVisitNarratives({});
      setFormCode(generated.formCode);
      setLongitudinalComment(activeCase.longitudinal_comment || '');
      setFirstPeVisitNumber(activeCase.first_pe_visit_number ? String(activeCase.first_pe_visit_number) : '');
      setFirstPeDate(activeCase.first_pe_date ? String(activeCase.first_pe_date).slice(0, 10) : '');
      setMeetsCriteria(true);
      setDifferentialDiagnosis('');
      setDiagnosisDateTime(toDateTimeLocal(activeCase.visits?.[0]?.date || activeCase.visits?.[0]?.visit_date));

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
    if (!activeCase || selectedVisitIndex >= pages.length) return;
    const visitKey = pages[selectedVisitIndex]?.visit_code || String(selectedVisitIndex + 1);
    const existing = visitNarratives[visitKey];
    if (existing != null) {
      setNarrativeText(existing);
      return;
    }
    const generated = generateNarrative({ ...activeCase, visits: pages.slice(0, selectedVisitIndex + 1) }, formCode);
    setVisitNarratives((current) => ({ ...current, [visitKey]: generated.fullText }));
    setNarrativeText(generated.fullText);
  }, [activeCase?.id, selectedVisitIndex]);

  useEffect(() => {
    if (selectedVisitIndex < pages.length && selectedVisit && !visitDecisions[selectedVisitIndex]) {
      setDiagnosisDateTime(toDateTimeLocal(selectedVisit.visit_date || selectedVisit.date));
    }
  }, [selectedVisitIndex, activeCase?.id, visitDecisions]);

  useEffect(() => {
    if (Number.isInteger(advanceToVisitIndex)) {
      handleVisitSelect(Math.max(0, Math.min(advanceToVisitIndex, pages.length)));
    }
  }, [advanceToVisitIndex, pages.length]);

  const handleRegenerateNarrative = () => {
    if (!activeCase) return;
    setIsGeneratingAi(true);
    setTimeout(() => {
      const scopedCase = selectedVisitIndex < pages.length ? { ...activeCase, visits: pages.slice(0, selectedVisitIndex + 1) } : activeCase;
      const generated = generateNarrative(scopedCase, formCode);
      setNarrativeText(generated.fullText);
      if (selectedVisitIndex < pages.length) {
        const key = pages[selectedVisitIndex]?.visit_code || String(selectedVisitIndex + 1);
        setVisitNarratives((current) => ({ ...current, [key]: generated.fullText }));
      }
      setIsGeneratingAi(false);
    }, 450);
  };

  // Assigned, QC-approved patient database
  if (currentStep === 1) {
    return (
      <div>
        {/* RealTime Roster Container */}
        <div className="rt-roster-card">
          <div className="a-panel" style={{ margin: '0 0 16px', padding: '16px' }}>
            <strong>My adjudication progress</strong>
            <div className="monitor-metrics" style={{ marginTop: '12px' }}>
              <div><b>{caseProgress?.summary?.unique_cases ?? 0}</b><span>Assigned unique cases</span></div>
              <div><b>{caseProgress?.by_case_status?.PENDING ?? 0}</b><span>Pending</span></div>
              <div><b>{caseProgress?.by_case_status?.IN_PROGRESS ?? 0}</b><span>In progress</span></div>
              <div><b>{caseProgress?.summary?.completed_cases ?? 0}</b><span>Completed cases</span></div>
              <div><b>{caseProgress?.summary?.adjudicated_visits ?? 0}</b><span>Adjudicated visits</span></div>
              <div><b>{caseProgress?.summary?.completion_pct ?? 0}%</b><span>Completion rate</span></div>
            </div>
            {(caseProgress?.summary?.duplicate_source_records ?? 0) > 0 && (
              <div style={{ marginTop: '10px', color: '#92400e', fontSize: '12px' }}>
                Duplicate source uploads detected and consolidated into unique case progress.
              </div>
            )}
          </div>
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
                    <th>Status ↕</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map(c => {
                    const isSelected = activeCase && c.id === activeCase.id;
                    const isCaseSigned = c.status?.includes('Finalized');

                    return (
                      <tr
                        key={c.id}
                        className={isSelected ? 'selected' : ''}
                        style={{ cursor: 'pointer' }}
                        onClick={() => { onSelectCase(c.id); setCurrentStep(2); }}
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

        
        {evidenceVisits.some(v => v.visit_number === 5 || v.visit_code === 'V05' || v.name?.includes('Visit 5')) && (
          <DropdownSection title="Fetal &amp; Neonatal Outcomes" icon={<Baby size={16} />} defaultOpen>
            <div className="summary-card-grid" style={{ marginBottom: '16px' }}>
              <div className="form-group">
                <label style={{ fontWeight: 700, display: 'flex', justifyContent: 'space-between' }}>
                  <span>Gestational Age at Delivery (weeks)</span>
                  {fetalProvenance?.GA_AT_DELIVERY && (
                    <span style={{ fontSize: '10.5px', color: '#0369a1', fontWeight: 600 }}>
                      CRF: {fetalProvenance.GA_AT_DELIVERY.raw_value || 'Documented'}
                    </span>
                  )}
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="15"
                  max="45"
                  className="form-input"
                  placeholder="e.g. 38.2"
                  value={gestationalAgeAtDelivery}
                  onChange={(e) => {
                    const val = e.target.value;
                    setGestationalAgeAtDelivery(val);
                    const n = parseFloat(val);
                    if (!Number.isNaN(n)) {
                      if (n >= 37.0) {
                        setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'DELIVERY_LT_34W'), 'DELIVERY_GE_37W'])));
                      } else if (n < 34.0) {
                        setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'DELIVERY_GE_37W' && c !== 'NORMAL_OUTCOME'), 'DELIVERY_LT_34W'])));
                      }
                    }
                  }}
                  disabled={isSigned}
                />
                <small>Numeric gestational age in weeks. Delivery outcome precedence applied.</small>
              </div>

              <div className="form-group">
                <label style={{ fontWeight: 700, display: 'flex', justifyContent: 'space-between' }}>
                  <span>Pregnancy Outcome</span>
                  {fetalProvenance?.PREGNANCY_OUTCOME && (
                    <span style={{ fontSize: '10.5px', color: '#0369a1', fontWeight: 600 }}>
                      CRF: {fetalProvenance.PREGNANCY_OUTCOME.raw_value || 'Documented'}
                    </span>
                  )}
                </label>
                <select
                  className="form-select"
                  value={pregnancyOutcome}
                  onChange={(e) => {
                    const val = e.target.value;
                    setPregnancyOutcome(val);
                    if (val.toLowerCase() === 'stillbirth' || val.toLowerCase().includes('death')) {
                      setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'NORMAL_OUTCOME'), 'PERINATAL_FETAL_DEATH'])));
                    }
                  }}
                  disabled={isSigned}
                >
                  <option value="Normal baby">Normal baby</option>
                  <option value="Preterm birth">Preterm birth</option>
                  <option value="Stillbirth">Stillbirth (Intrauterine / Fetal Death)</option>
                  <option value="Early neonatal death">Early neonatal death</option>
                  <option value="Ongoing pregnancy">Ongoing pregnancy</option>
                  <option value="Other">Other</option>
                </select>
                <small>Applies delivery-outcome precedence (Death &gt; Preterm &gt; Normal baby).</small>
              </div>
            </div>

            <label style={{ fontWeight: 700, display: 'block', marginBottom: '8px' }}>
              Closed-Ended Fetal and Neonatal Assessments (Select all that apply)
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '10px', marginBottom: '12px' }}>
              {VISIT5_ASSESSMENT_OPTIONS.map((opt) => {
                const isChecked = fetalNeonatalAssessments.includes(opt.code);
                const prov = fetalProvenance[opt.code];
                const provState = prov?.state;

                return (
                  <div
                    key={opt.code}
                    onClick={() => handleToggleAssessment(opt.code)}
                    style={{
                      border: isChecked ? '2px solid #0284c7' : '1px solid #cbd5e1',
                      background: isChecked ? '#f0f9ff' : '#ffffff',
                      borderRadius: '6px',
                      padding: '12px',
                      cursor: isSigned ? 'default' : 'pointer',
                      transition: 'all 0.15s ease',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '6px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleToggleAssessment(opt.code)}
                        disabled={isSigned}
                        style={{ marginTop: '3px', cursor: 'pointer' }}
                      />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: isChecked ? 700 : 600, fontSize: '13px', color: isChecked ? '#0369a1' : '#1e293b' }}>
                          {opt.label}
                        </div>
                        {opt.adverse && (
                          <span style={{ fontSize: '10.5px', color: '#b91c1c', fontWeight: 600 }}>
                            Adverse endpoint
                          </span>
                        )}
                      </div>
                    </div>

                    {prov && (
                      <div style={{
                        marginTop: '4px',
                        padding: '4px 8px',
                        background: provState === 'CONFIRMED_POSITIVE' ? '#dcfce7' : provState === 'CONFIRMED_NEGATIVE' ? '#f1f5f9' : '#fef3c7',
                        borderRadius: '4px',
                        fontSize: '11px',
                        color: provState === 'CONFIRMED_POSITIVE' ? '#166534' : provState === 'CONFIRMED_NEGATIVE' ? '#475569' : '#92400e',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <span>
                          {provState === 'CONFIRMED_POSITIVE' && '✓ Source Confirmed'}
                          {provState === 'CONFIRMED_NEGATIVE' && '— Source Confirmed Negative'}
                          {provState === 'NOT_ASSESSED_OR_MISSING' && '⚠ Not Assessed / Missing in CRF'}
                        </span>
                        {prov.provenance?.field && (
                          <span style={{ fontSize: '10px', opacity: 0.85 }}>
                            {prov.provenance.form ? `${prov.provenance.form} / ` : ''}{prov.provenance.field}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {visit5ValidationWarning && (
              <div role="alert" style={{
                background: '#fef2f2',
                border: '1px solid #f87171',
                borderRadius: '6px',
                padding: '10px 14px',
                color: '#991b1b',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginTop: '10px'
              }}>
                <AlertTriangle size={18} color="#dc2626" />
                <div>
                  <strong>Validation Rule Violation:</strong> {visit5ValidationWarning}
                </div>
              </div>
            )}
          </DropdownSection>
        )}

        <div className="wizard-footer"><div></div><button className="btn-large btn-next" onClick={() => setCurrentStep(2)} disabled={!activeCase}>Review Patient Evidence <ArrowRight size={16}/></button></div>
      </div>
    );
  }

  // Review evidence and system derivation
  if (currentStep === 2) {
    return (
      <div>
        <div className="wizard-card">
          {/* Header Actions */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <h2 className="wizard-title">Review Findings for Participant {activeCase.id}</h2>
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
              <button 
                className="btn-secondary" 
                style={{ padding: '5px 10px', background: '#f5f3ff', color: '#6d28d9', borderColor: '#c4b5fd', fontWeight: 600 }} 
                onClick={onOpenSourceDocs}
              >
                <FileText size={13} style={{ marginRight: '4px' }} />
                View Dating Ultrasound Scan
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

            {/* FDA-Style Narrative Block */}
          <div style={{
            background: '#ffffff',
            border: '1px solid #ea580c',
            borderLeft: '4px solid #ea580c',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '16px',
            overflow: 'hidden'
          }}>
            <div style={{ background: '#fff7ed', padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #ea580c' }}>
              <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: 0, color: '#9a3412' }}>
                <FileText size={16} />
                Blinded Clinical Narrative ({formCode})
              </h4>
              <div style={{ display: 'inline-flex', background: '#fdba74', borderRadius: '4px', padding: '2px' }}>
                <button
                  type="button"
                  onClick={() => setNarrativeViewMode('TABLE')}
                  style={{
                    padding: '3px 8px', fontSize: '11px', fontWeight: 600, border: 'none', borderRadius: '3px', cursor: 'pointer',
                    background: narrativeViewMode === 'TABLE' ? '#ffffff' : 'transparent',
                    color: narrativeViewMode === 'TABLE' ? '#9a3412' : '#c2410c'
                  }}
                >
                  📊 Structured
                </button>
                <button
                  type="button"
                  onClick={() => setNarrativeViewMode('PROSE')}
                  style={{
                    padding: '3px 8px', fontSize: '11px', fontWeight: 600, border: 'none', borderRadius: '3px', cursor: 'pointer',
                    background: narrativeViewMode === 'PROSE' ? '#ffffff' : 'transparent',
                    color: narrativeViewMode === 'PROSE' ? '#9a3412' : '#c2410c'
                  }}
                >
                  📝 Prose
                </button>
              </div>
            </div>
            <div style={{ padding: '16px' }}>
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
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{
                  background: '#ffffff',
                  padding: '16px',
                  borderRadius: '4px',
                  border: '1px solid #cbd5e1',
                  fontSize: '13px',
                  lineHeight: '1.7',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'var(--font-sans)',
                  color: '#1e293b',
                  maxHeight: '600px',
                  overflowY: 'auto'
                }}>
                {narrativeText}
                </div>
              )}
            </div>
          </div>
          
          <PatientHistoryPanel caseData={activeCase} />



            <DropdownSection title="Visit Specific Evidence" icon={<FileText size={16} />} defaultOpen>
              {selectedVisitIndex===evidenceVisits.length ? <OverallSummary visits={evidenceVisits} /> : selectedEvidenceVisit && <VisitEvidencePanel visit={selectedEvidenceVisit} selectedIndex={selectedVisitIndex} visitCount={evidenceVisits.length} onSelectVisit={handleVisitSelect} />}
            </DropdownSection>

            <DropdownSection title="Visit navigation" icon={<Database size={16} />} defaultOpen={false}>
              <VisitRibbon visits={evidenceVisits} selectedIndex={selectedVisitIndex} onSelectVisit={handleVisitSelect} />
              <p style={{ margin: '12px 0 0', color: 'var(--text-muted)', fontSize: '12px' }}>
                Use the visit tabs to review source evidence. Derived classifications are shown for context only and do not replace the recorded source data.
              </p>
            </DropdownSection>

          
        {evidenceVisits.some(v => v.visit_number === 5 || v.visit_code === 'V05' || v.name?.includes('Visit 5')) && (
          <DropdownSection title="Fetal &amp; Neonatal Outcomes" icon={<Baby size={16} />} defaultOpen>
            <div className="summary-card-grid" style={{ marginBottom: '16px' }}>
              <div className="form-group">
                <label style={{ fontWeight: 700, display: 'flex', justifyContent: 'space-between' }}>
                  <span>Gestational Age at Delivery (weeks)</span>
                  {fetalProvenance?.GA_AT_DELIVERY && (
                    <span style={{ fontSize: '10.5px', color: '#0369a1', fontWeight: 600 }}>
                      CRF: {fetalProvenance.GA_AT_DELIVERY.raw_value || 'Documented'}
                    </span>
                  )}
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="15"
                  max="45"
                  className="form-input"
                  placeholder="e.g. 38.2"
                  value={gestationalAgeAtDelivery}
                  onChange={(e) => {
                    const val = e.target.value;
                    setGestationalAgeAtDelivery(val);
                    const n = parseFloat(val);
                    if (!Number.isNaN(n)) {
                      if (n >= 37.0) {
                        setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'DELIVERY_LT_34W'), 'DELIVERY_GE_37W'])));
                      } else if (n < 34.0) {
                        setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'DELIVERY_GE_37W' && c !== 'NORMAL_OUTCOME'), 'DELIVERY_LT_34W'])));
                      }
                    }
                  }}
                  disabled={isSigned}
                />
                <small>Numeric gestational age in weeks. Delivery outcome precedence applied.</small>
              </div>

              <div className="form-group">
                <label style={{ fontWeight: 700, display: 'flex', justifyContent: 'space-between' }}>
                  <span>Pregnancy Outcome</span>
                  {fetalProvenance?.PREGNANCY_OUTCOME && (
                    <span style={{ fontSize: '10.5px', color: '#0369a1', fontWeight: 600 }}>
                      CRF: {fetalProvenance.PREGNANCY_OUTCOME.raw_value || 'Documented'}
                    </span>
                  )}
                </label>
                <select
                  className="form-select"
                  value={pregnancyOutcome}
                  onChange={(e) => {
                    const val = e.target.value;
                    setPregnancyOutcome(val);
                    if (val.toLowerCase() === 'stillbirth' || val.toLowerCase().includes('death')) {
                      setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'NORMAL_OUTCOME'), 'PERINATAL_FETAL_DEATH'])));
                    }
                  }}
                  disabled={isSigned}
                >
                  <option value="Normal baby">Normal baby</option>
                  <option value="Preterm birth">Preterm birth</option>
                  <option value="Stillbirth">Stillbirth (Intrauterine / Fetal Death)</option>
                  <option value="Early neonatal death">Early neonatal death</option>
                  <option value="Ongoing pregnancy">Ongoing pregnancy</option>
                  <option value="Other">Other</option>
                </select>
                <small>Applies delivery-outcome precedence (Death &gt; Preterm &gt; Normal baby).</small>
              </div>
            </div>

            <label style={{ fontWeight: 700, display: 'block', marginBottom: '8px' }}>
              Closed-Ended Fetal and Neonatal Assessments (Select all that apply)
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '10px', marginBottom: '12px' }}>
              {VISIT5_ASSESSMENT_OPTIONS.map((opt) => {
                const isChecked = fetalNeonatalAssessments.includes(opt.code);
                const prov = fetalProvenance[opt.code];
                const provState = prov?.state;

                return (
                  <div
                    key={opt.code}
                    onClick={() => handleToggleAssessment(opt.code)}
                    style={{
                      border: isChecked ? '2px solid #0284c7' : '1px solid #cbd5e1',
                      background: isChecked ? '#f0f9ff' : '#ffffff',
                      borderRadius: '6px',
                      padding: '12px',
                      cursor: isSigned ? 'default' : 'pointer',
                      transition: 'all 0.15s ease',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '6px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleToggleAssessment(opt.code)}
                        disabled={isSigned}
                        style={{ marginTop: '3px', cursor: 'pointer' }}
                      />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: isChecked ? 700 : 600, fontSize: '13px', color: isChecked ? '#0369a1' : '#1e293b' }}>
                          {opt.label}
                        </div>
                        {opt.adverse && (
                          <span style={{ fontSize: '10.5px', color: '#b91c1c', fontWeight: 600 }}>
                            Adverse endpoint
                          </span>
                        )}
                      </div>
                    </div>

                    {prov && (
                      <div style={{
                        marginTop: '4px',
                        padding: '4px 8px',
                        background: provState === 'CONFIRMED_POSITIVE' ? '#dcfce7' : provState === 'CONFIRMED_NEGATIVE' ? '#f1f5f9' : '#fef3c7',
                        borderRadius: '4px',
                        fontSize: '11px',
                        color: provState === 'CONFIRMED_POSITIVE' ? '#166534' : provState === 'CONFIRMED_NEGATIVE' ? '#475569' : '#92400e',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <span>
                          {provState === 'CONFIRMED_POSITIVE' && '✓ Source Confirmed'}
                          {provState === 'CONFIRMED_NEGATIVE' && '— Source Confirmed Negative'}
                          {provState === 'NOT_ASSESSED_OR_MISSING' && '⚠ Not Assessed / Missing in CRF'}
                        </span>
                        {prov.provenance?.field && (
                          <span style={{ fontSize: '10px', opacity: 0.85 }}>
                            {prov.provenance.form ? `${prov.provenance.form} / ` : ''}{prov.provenance.field}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {visit5ValidationWarning && (
              <div role="alert" style={{
                background: '#fef2f2',
                border: '1px solid #f87171',
                borderRadius: '6px',
                padding: '10px 14px',
                color: '#991b1b',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginTop: '10px'
              }}>
                <AlertTriangle size={18} color="#dc2626" />
                <div>
                  <strong>Validation Rule Violation:</strong> {visit5ValidationWarning}
                </div>
              </div>
            )}
          </DropdownSection>
        )}

        <div className="wizard-footer">
            <button className="btn-large btn-back" onClick={() => setCurrentStep(1)}>
              <ArrowLeft size={16} /> Back to Queue
            </button>
            <button className="btn-large btn-next" onClick={() => setCurrentStep(3)}>
              Approve Summary &amp; Sign <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Completed and signed record view
  if (currentStep === 4 || (currentStep === 3 && isSigned)) {
    const isConsensusFinal = isSigned || allVisitsFinalized;
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
                {isConsensusFinal
                  ? `Case ${activeCase.caseNo} (${activeCase.id}) Finalized & Filed to TMF`
                  : `Case ${activeCase.caseNo} (${activeCase.id}) Reviewer Adjudications Signed & Submitted`}
              </h2>
            </div>
          </div>

          {!isConsensusFinal && (
            <div className="overall-lock-message" style={{ marginBottom: '16px' }}>
              <CheckCircle2 size={24}/>
              <div>
                <strong>Submitted for concordance checking</strong>
                <p>Your six visit records are locked. Matching reviewer decisions will finalize automatically; discordant decisions will be routed to Reviewer C and the Chairperson workflow.</p>
              </div>
            </div>
          )}

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
            {isConsensusFinal && <button className="btn-large btn-next" disabled={isDownloadingPdf} onClick={async () => {
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
            </button>}

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
          {isConsensusFinal && pdfDownloadError && (
            <div role="alert" style={{ marginTop: '10px', color: 'var(--danger, #b42318)', fontSize: '12px', fontWeight: 600 }}>
              {pdfDownloadError} Confirm that the backend service is running, then try again.
            </div>
          )}
        </div>
      </div>
    );
  }

  // Approve clinical summary and sign (Overall Flow)
  return (
    <div>
      <div className="wizard-card">
        <h2 className="wizard-title">Final Adjudication &amp; Sign Record ({activeCase.id})</h2>
        <p className="wizard-subtitle">Record your overall determination for this case and classify the onset per visit.</p>

        {/* Overall Determination */}
        <DropdownSection title="Overall Case Determination" icon={<ShieldCheck size={16} />} defaultOpen>
          <div className="summary-card-grid" style={{ marginBottom: '16px' }}>
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontWeight: 700, fontSize: '15px' }}>Does this participant meet criteria for pre-eclampsia?</label>
              <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                  <input type="radio" name="meetsCriteria" checked={meetsCriteria === true} onChange={() => { setMeetsCriteria(true); setSelectedDiagnosis('PE'); }} disabled={isSigned} /> Yes
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                  <input type="radio" name="meetsCriteria" checked={meetsCriteria === false} onChange={() => { setMeetsCriteria(false); setSelectedDiagnosis('Not PE'); }} disabled={isSigned} /> No
                </label>
              </div>
            </div>

            {meetsCriteria && (
              <>
                <div className="form-group">
                  <label style={{ fontWeight: 700 }}>Overall Classification</label>
                  <select className="form-select" value={selectedDiagnosis} onChange={(e) => setSelectedDiagnosis(e.target.value)} disabled={isSigned}>
                    <option value="PE">PE</option>
                    <option value="Severe PE">Severe PE</option>
                    <option value="Eclampsia">Eclampsia</option>
                    <option value="HELLP">HELLP</option>
                    {isReviewerC && <option value="Other">Other</option>}
                  </select>
                </div>
                
                <div className="form-group">
                  <label style={{ fontWeight: 700 }}>Overall Severity</label>
                  <select className="form-select" value={selectedSeverity} onChange={(e) => setSelectedSeverity(e.target.value)} disabled={isSigned}>
                    <option value="With severe features">With severe features</option>
                    <option value="Without severe features">Without severe features</option>
                    <option value="Eclampsia / severe SAE">Eclampsia / severe SAE</option>
                  </select>
                </div>
              </>
            )}
            
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontWeight: 700 }}>Differential Diagnosis / Alternative Explanation <span style={{color: 'red'}}>*</span></label>
              <input
                className="form-input"
                type="text"
                value={differentialDiagnosis}
                onChange={(e) => setDifferentialDiagnosis(e.target.value)}
                placeholder="Record important alternatives considered or why none applied"
                disabled={isSigned}
                required
              />
              <small>This field is mandatory.</small>
            </div>
          </div>
        </DropdownSection>

        {/* Per-visit Onset Grid */}
        {meetsCriteria && (
          <DropdownSection title="Per-Visit Onset Grid" icon={<Database size={16} />} defaultOpen>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '12px' }}>
              For each visit with evidence, indicate if pre-eclampsia criteria were met and the onset classification.
            </p>
            <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                <thead style={{ background: '#f8fafc', borderBottom: '1px solid var(--border-subtle)' }}>
                  <tr>
                    <th style={{ padding: '10px' }}>Visit</th>
                    <th style={{ padding: '10px' }}>Date</th>
                    <th style={{ padding: '10px' }}>PE Present?</th>
                    <th style={{ padding: '10px' }}>Onset Classification (if Yes)</th>
                  </tr>
                </thead>
                <tbody>
                  {evidenceVisits.map((v, i) => {
                    const dec = visitDecisions[v.id] || { meetsCriteria: false, onset: 'Onset not yet classifiable' };
                    return (
                      <tr key={v.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '10px', fontWeight: 600 }}>{v.name || v.visit_code || `Visit ${i+1}`}</td>
                        <td style={{ padding: '10px' }}>{new Date(v.date || v.visit_date).toLocaleDateString()}</td>
                        <td style={{ padding: '10px' }}>
                          <select 
                            className="form-select" 
                            style={{ padding: '4px', fontSize: '13px' }}
                            value={dec.meetsCriteria ? 'Yes' : 'No'}
                            onChange={e => {
                              const val = e.target.value === 'Yes';
                              setVisitDecisions(prev => ({...prev, [v.id]: {...(prev[v.id]||{}), meetsCriteria: val}}));
                            }}
                            disabled={isSigned}
                          >
                            <option value="No">No</option>
                            <option value="Yes">Yes</option>
                          </select>
                        </td>
                        <td style={{ padding: '10px' }}>
                          <select 
                            className="form-select" 
                            style={{ padding: '4px', fontSize: '13px' }}
                            value={dec.onset || 'Onset not yet classifiable'}
                            onChange={e => {
                               setVisitDecisions(prev => ({...prev, [v.id]: {...(prev[v.id]||{}), onset: e.target.value}}));
                            }}
                            disabled={!dec.meetsCriteria || isSigned}
                          >
                            <option value="Early-onset pre-eclampsia (EOPE)">Early-onset (EOPE) &lt; 34 weeks</option>
                            <option value="Late-onset pre-eclampsia (LOPE)">Late-onset (LOPE) ≥ 34 weeks</option>
                            <option value="Postpartum-only presentation">Postpartum-only presentation</option>
                            <option value="Onset not yet classifiable">Onset not yet classifiable</option>
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </DropdownSection>
        )}

        
        {evidenceVisits.some(v => v.visit_number === 5 || v.visit_code === 'V05' || v.name?.includes('Visit 5')) && (
          <DropdownSection title="Fetal &amp; Neonatal Outcomes" icon={<Baby size={16} />} defaultOpen>
            <div className="summary-card-grid" style={{ marginBottom: '16px' }}>
              <div className="form-group">
                <label style={{ fontWeight: 700, display: 'flex', justifyContent: 'space-between' }}>
                  <span>Gestational Age at Delivery (weeks)</span>
                  {fetalProvenance?.GA_AT_DELIVERY && (
                    <span style={{ fontSize: '10.5px', color: '#0369a1', fontWeight: 600 }}>
                      CRF: {fetalProvenance.GA_AT_DELIVERY.raw_value || 'Documented'}
                    </span>
                  )}
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="15"
                  max="45"
                  className="form-input"
                  placeholder="e.g. 38.2"
                  value={gestationalAgeAtDelivery}
                  onChange={(e) => {
                    const val = e.target.value;
                    setGestationalAgeAtDelivery(val);
                    const n = parseFloat(val);
                    if (!Number.isNaN(n)) {
                      if (n >= 37.0) {
                        setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'DELIVERY_LT_34W'), 'DELIVERY_GE_37W'])));
                      } else if (n < 34.0) {
                        setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'DELIVERY_GE_37W' && c !== 'NORMAL_OUTCOME'), 'DELIVERY_LT_34W'])));
                      }
                    }
                  }}
                  disabled={isSigned}
                />
                <small>Numeric gestational age in weeks. Delivery outcome precedence applied.</small>
              </div>

              <div className="form-group">
                <label style={{ fontWeight: 700, display: 'flex', justifyContent: 'space-between' }}>
                  <span>Pregnancy Outcome</span>
                  {fetalProvenance?.PREGNANCY_OUTCOME && (
                    <span style={{ fontSize: '10.5px', color: '#0369a1', fontWeight: 600 }}>
                      CRF: {fetalProvenance.PREGNANCY_OUTCOME.raw_value || 'Documented'}
                    </span>
                  )}
                </label>
                <select
                  className="form-select"
                  value={pregnancyOutcome}
                  onChange={(e) => {
                    const val = e.target.value;
                    setPregnancyOutcome(val);
                    if (val.toLowerCase() === 'stillbirth' || val.toLowerCase().includes('death')) {
                      setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'NORMAL_OUTCOME'), 'PERINATAL_FETAL_DEATH'])));
                    }
                  }}
                  disabled={isSigned}
                >
                  <option value="Normal baby">Normal baby</option>
                  <option value="Preterm birth">Preterm birth</option>
                  <option value="Stillbirth">Stillbirth (Intrauterine / Fetal Death)</option>
                  <option value="Early neonatal death">Early neonatal death</option>
                  <option value="Ongoing pregnancy">Ongoing pregnancy</option>
                  <option value="Other">Other</option>
                </select>
                <small>Applies delivery-outcome precedence (Death &gt; Preterm &gt; Normal baby).</small>
              </div>
            </div>

            <label style={{ fontWeight: 700, display: 'block', marginBottom: '8px' }}>
              Closed-Ended Fetal and Neonatal Assessments (Select all that apply)
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '10px', marginBottom: '12px' }}>
              {VISIT5_ASSESSMENT_OPTIONS.map((opt) => {
                const isChecked = fetalNeonatalAssessments.includes(opt.code);
                const prov = fetalProvenance[opt.code];
                const provState = prov?.state;

                return (
                  <div
                    key={opt.code}
                    onClick={() => handleToggleAssessment(opt.code)}
                    style={{
                      border: isChecked ? '2px solid #0284c7' : '1px solid #cbd5e1',
                      background: isChecked ? '#f0f9ff' : '#ffffff',
                      borderRadius: '6px',
                      padding: '12px',
                      cursor: isSigned ? 'default' : 'pointer',
                      transition: 'all 0.15s ease',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '6px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleToggleAssessment(opt.code)}
                        disabled={isSigned}
                        style={{ marginTop: '3px', cursor: 'pointer' }}
                      />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: isChecked ? 700 : 600, fontSize: '13px', color: isChecked ? '#0369a1' : '#1e293b' }}>
                          {opt.label}
                        </div>
                        {opt.adverse && (
                          <span style={{ fontSize: '10.5px', color: '#b91c1c', fontWeight: 600 }}>
                            Adverse endpoint
                          </span>
                        )}
                      </div>
                    </div>

                    {prov && (
                      <div style={{
                        marginTop: '4px',
                        padding: '4px 8px',
                        background: provState === 'CONFIRMED_POSITIVE' ? '#dcfce7' : provState === 'CONFIRMED_NEGATIVE' ? '#f1f5f9' : '#fef3c7',
                        borderRadius: '4px',
                        fontSize: '11px',
                        color: provState === 'CONFIRMED_POSITIVE' ? '#166534' : provState === 'CONFIRMED_NEGATIVE' ? '#475569' : '#92400e',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <span>
                          {provState === 'CONFIRMED_POSITIVE' && '✓ Source Confirmed'}
                          {provState === 'CONFIRMED_NEGATIVE' && '— Source Confirmed Negative'}
                          {provState === 'NOT_ASSESSED_OR_MISSING' && '⚠ Not Assessed / Missing in CRF'}
                        </span>
                        {prov.provenance?.field && (
                          <span style={{ fontSize: '10px', opacity: 0.85 }}>
                            {prov.provenance.form ? `${prov.provenance.form} / ` : ''}{prov.provenance.field}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {visit5ValidationWarning && (
              <div role="alert" style={{
                background: '#fef2f2',
                border: '1px solid #f87171',
                borderRadius: '6px',
                padding: '10px 14px',
                color: '#991b1b',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginTop: '10px'
              }}>
                <AlertTriangle size={18} color="#dc2626" />
                <div>
                  <strong>Validation Rule Violation:</strong> {visit5ValidationWarning}
                </div>
              </div>
            )}
          </DropdownSection>
        )}

        <div className="wizard-footer" style={{ marginTop: '24px' }}>
          <button className="btn-large btn-back" onClick={() => setCurrentStep(2)}>
            <ArrowLeft size={15} /> Back to Evidence
          </button>

          <button className="btn-large btn-next" onClick={() => {
            // Build per_visit_onset array
            const perVisitOnset = evidenceVisits.map(v => {
               const dec = visitDecisions[v.id] || { meetsCriteria: false, onset: null };
               return {
                  visit_number: v.visit_number || parseInt((v.visit_code || '').replace('V', '') || (v.name || '').replace('Visit ', '')) || 1,
                  meets_criteria: dec.meetsCriteria,
                  diagnosis: dec.meetsCriteria ? selectedDiagnosis : 'Not PE',
                  onset_class: dec.meetsCriteria ? (dec.onset || selectedOnset) : null
               };
            });

            onOpenSignature({
              is_overall_first: true,
              per_visit_onset: perVisitOnset,
              reviewerRole: activeCase?.reviewerRole || 'REVIEWER_A',
              reviewerName: user?.display_name || user?.name || user?.email,
              diagnosis: meetsCriteria ? selectedDiagnosis : 'Not PE',
              meetsCriteria,
              onset: selectedOnset, // default overall
              severity: selectedSeverity,
              certainty: selectedCertainty,
              rationale: "Overall case determination signature.", // placeholder
              differentialDiagnosis: differentialDiagnosis.trim() || null,
              visitNumber: 1, // backend will override this in the loop
              
              fetalNeonatalAssessments: fetalNeonatalAssessments,
              gestationalAgeAtDelivery: gestationalAgeAtDelivery !== '' ? Number(gestationalAgeAtDelivery) : null,
              pregnancyOutcome: pregnancyOutcome,
              fetalAssessmentStatus: fetalNeonatalAssessments?.length > 0 ? 'CONFIRMED' : null,
              fetalNeonatalProvenance: fetalProvenance
            });
          }} disabled={!differentialDiagnosis.trim()}>
            <ShieldCheck size={16} /> Sign &amp; Lock Adjudication Record
          </button>
        </div>
      </div>
    </div>
  );
}
