import React, { useState, useEffect } from 'react';
import { ArrowRight, ArrowLeft, CheckCircle2, Activity, Database, ShieldCheck, FileText, Lock, Download, EyeOff, UserX, AlertCircle, RefreshCw, Info, ExternalLink, ChevronDown, Bot, FilePlus, LogOut, Copy, Save, Server, Search, Calendar, ChevronRight, X, UserCheck, Stethoscope, AlertTriangle, Baby } from 'lucide-react';
import { OverallSummary, VisitEvidencePanel, VisitRibbon } from './VisitEvidenceSections';
import { generateNarrative, generateSummary, AI_ENGINE_MODEL } from '../services/demoNarrative';
import { generateVisitNarrative, generateOverallNarrative } from '../services/clinicalNarrative';
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
  const [showAiAssistant, setShowAiAssistant] = useState(false);
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
    // Use new v2.0 per-visit narrative engine via the normalised evidence visits
    const visitNum = selectedVisitIndex + 1;
    const ev = evidenceVisits[selectedVisitIndex];
    if (ev) {
      const visitText = generateVisitNarrative(ev, visitNum, activeCase);
      setVisitNarratives((current) => ({ ...current, [visitKey]: visitText }));
      setNarrativeText(visitText);
    } else {
      // Fallback to legacy overall narrative
      const generated = generateNarrative({ ...activeCase, visits: pages.slice(0, selectedVisitIndex + 1) }, formCode);
      setVisitNarratives((current) => ({ ...current, [visitKey]: generated.fullText }));
      setNarrativeText(generated.fullText);
    }
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
      if (selectedVisitIndex >= pages.length) {
        // Overall summary — use new v2.0 engine
        const overallText = generateOverallNarrative(evidenceVisits, activeCase);
        setNarrativeText(overallText);
      } else {
        // Per-visit — use new v2.0 engine
        const visitNum = selectedVisitIndex + 1;
        const ev = evidenceVisits[selectedVisitIndex];
        const visitText = ev
          ? generateVisitNarrative(ev, visitNum, activeCase)
          : generateNarrative({ ...activeCase, visits: pages.slice(0, selectedVisitIndex + 1) }, formCode).fullText;
        setNarrativeText(visitText);
        const key = pages[selectedVisitIndex]?.visit_code || String(selectedVisitIndex + 1);
        setVisitNarratives((current) => ({ ...current, [key]: visitText }));
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

        
        

        <div className="wizard-footer"><div></div><button className="btn-large btn-next" onClick={() => setCurrentStep(2)} disabled={!activeCase}>Review Patient Evidence <ArrowRight size={16}/></button></div>
      </div>
    );
  }

  // Review evidence and system derivation
  if (currentStep === 2) {
    return (
      <div>
        <div className="wizard-card">
          {/* Header Actions & Patient Context */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <h2 className="wizard-title" style={{ margin: 0, fontSize: '18px' }}>
                  Review Findings for Participant {activeCase.id}
                </h2>
                <span style={{ fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '4px', background: '#e0f2fe', color: '#0369a1' }}>
                  {activeCase.caseNo || `ADJ-${activeCase.id}`}
                </span>
                <span style={{ fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '4px', background: '#f1f5f9', color: '#475569', display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <EyeOff size={12} /> SOP-ADJ-002 Blinding Active
                </span>
              </div>
              <p className="wizard-subtitle" style={{ margin: '4px 0 0', color: '#64748b', fontSize: '12.5px' }}>
                Study: <strong>{activeCase.study || 'PROTECT-Africa'}</strong> · Site: <strong>{activeCase.site || 'ZWE001 (Harare Central)'}</strong> · Reviewer: <strong>{activeCase.reviewerRole || 'Reviewer A'}</strong>
              </p>
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <button className="btn-secondary" style={{ fontSize: '12px' }} onClick={onOpenRecusalModal} title="Declare recusal under FORM-ADJ-08">
                <UserX size={13} /> Recusal
              </button>
              <button className="btn-secondary" style={{ fontSize: '12px' }} onClick={onOpenDataQueryModal} title="Raise clinical data query under FORM-ADJ-09">
                <AlertCircle size={13} /> Raise Query
              </button>
              <button className="btn-back" style={{ padding: '5px 12px', fontSize: '12px' }} onClick={onOpenSourceDocs}>
                <FileText size={13} style={{ marginRight: '4px' }} /> Inspect Raw Docs
              </button>
            </div>
          </div>

          {/* Top-Level Visit Navigation Ribbon */}
          <VisitRibbon
            visits={evidenceVisits}
            selectedIndex={selectedVisitIndex}
            onSelectVisit={handleVisitSelect}
          />

          {/* Active Visit Clinical Evidence or Overall Case Summary */}
          {selectedVisitIndex === evidenceVisits.length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <OverallSummary visits={evidenceVisits} caseData={activeCase} />


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

                  {!meetsCriteria && (
                    <div className="form-group">
                      <label style={{ fontWeight: 700 }}>Non-PE Determination / Clinical Finding</label>
                      <select className="form-select" value={selectedDiagnosis} onChange={(e) => setSelectedDiagnosis(e.target.value)} disabled={isSigned}>
                        <option value="Chronic Hypertension (Superimposed PE Excluded)">Chronic Hypertension (Superimposed PE Excluded)</option>
                        <option value="Gestational Hypertension">Gestational Hypertension</option>
                        <option value="Normotensive / Normal Pregnancy">Normotensive / Normal Pregnancy</option>
                        <option value="Transient Gestational Proteinuria (Resolved)">Transient Gestational Proteinuria (Resolved)</option>
                        <option value="Unclassifiable">Unclassifiable</option>
                      </select>
                    </div>
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

              <div className="wizard-footer" style={{ marginTop: '24px' }}>
                <button className="btn-large btn-back" onClick={() => setCurrentStep(1)}>
                  <ArrowLeft size={16} /> Back to Queue
                </button>
                <button className="btn-large btn-next" onClick={() => {
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
                    onset: selectedOnset,
                    severity: selectedSeverity,
                    certainty: selectedCertainty,
                    rationale: "Overall case determination signature.", 
                    differentialDiagnosis: differentialDiagnosis.trim() || null,
                    visitNumber: 1, 
                    fetalNeonatalAssessments: fetalNeonatalAssessments,
                    gestationalAgeAtDelivery: gestationalAgeAtDelivery !== '' ? Number(gestationalAgeAtDelivery) : null,
                    pregnancyOutcome: pregnancyOutcome,
                  });
                }}>
                  <Lock size={15} /> Sign &amp; Submit Adjudication
                </button>
              </div>

            </div>
          ) : selectedEvidenceVisit && (
            <>
              <VisitEvidencePanel
                visit={selectedEvidenceVisit}
                selectedIndex={selectedVisitIndex}
                visitCount={evidenceVisits.length}
                onSelectVisit={handleVisitSelect}
                caseData={activeCase}
                narrativeText={narrativeText}
              />

              <div style={{ marginTop: '16px' }}>
                <DropdownSection title={`Adjudicate ${selectedEvidenceVisit.name || selectedEvidenceVisit.visit_code || 'this Visit'}`} icon={<ShieldCheck size={16} />} defaultOpen>
                  {(() => {
                    const dec = visitDecisions[selectedEvidenceVisit.id] || { meetsCriteria: false, onset: 'Onset not yet classifiable' };
                    return (
                      <div className="summary-card-grid" style={{ marginBottom: '0' }}>
                        <div className="form-group">
                          <label style={{ fontWeight: 700 }}>PE Criteria Met at this Visit?</label>
                          <select 
                            className="form-select" 
                            value={dec.meetsCriteria ? 'Yes' : 'No'}
                            onChange={e => {
                              const val = e.target.value === 'Yes';
                              setVisitDecisions(prev => ({...prev, [selectedEvidenceVisit.id]: {...(prev[selectedEvidenceVisit.id]||{}), meetsCriteria: val}}));
                              if (val) setMeetsCriteria(true);
                            }}
                            disabled={isSigned}
                          >
                            <option value="No">No</option>
                            <option value="Yes">Yes</option>
                          </select>
                        </div>
                        <div className="form-group">
                          <label style={{ fontWeight: 700 }}>Onset Classification (if Yes)</label>
                          <select 
                            className="form-select" 
                            value={dec.onset || 'Onset not yet classifiable'}
                            onChange={e => {
                               setVisitDecisions(prev => ({...prev, [selectedEvidenceVisit.id]: {...(prev[selectedEvidenceVisit.id]||{}), onset: e.target.value}}));
                            }}
                            disabled={!dec.meetsCriteria || isSigned}
                          >
                            <option value="Early-onset pre-eclampsia (EOPE)">Early-onset (EOPE) &lt; 34 weeks</option>
                            <option value="Late-onset pre-eclampsia (LOPE)">Late-onset (LOPE) ≥ 34 weeks</option>
                            <option value="Postpartum-only presentation">Postpartum-only presentation</option>
                            <option value="Onset not yet classifiable">Onset not yet classifiable</option>
                          </select>
                        </div>
                      </div>
                    );
                  })()}
                </DropdownSection>
              </div>

              {/* Special Visit 5 Closed-Ended Outcome Endpoints Adjudication */}
              {(selectedEvidenceVisit.visit_number === 5 || selectedEvidenceVisit.visit_code === 'V05' || selectedEvidenceVisit.name?.includes('Visit 5')) && (
                <div style={{ marginTop: '16px' }}>
                  <DropdownSection title="Adjudicate Visit 5 Fetal &amp; Neonatal Outcome Endpoints" icon={<Baby size={16} />} defaultOpen>
                    {(() => {
                      // Derive live CRF hints from the patient's mapped evidence
                      const ev = selectedEvidenceVisit?.evidence || {};
                      const getFirst = (keys) => {
                        for (const k of keys) {
                          const rows = ev[k];
                          if (rows?.length) {
                            const r = rows[0];
                            return r.numeric_value ?? r.raw_source_value ?? r.parsed_text_value ?? r.coded_value ?? null;
                          }
                        }
                        return null;
                      };
                      const crfGaDelivery = getFirst(['ega_delivery', 'EGA_DELIVERY', 'ga_at_delivery', 'GA_AT_DELIVERY']);
                      const crfOutcome = getFirst(['pregnancy_outcome', 'PREGNANCY_OUTCOME', 'delivery_outcome', 'DELIVERY_OUTCOME']);
                      const gaWeeks = crfGaDelivery != null ? parseFloat(crfGaDelivery) : null;
                      const gaLabel = gaWeeks != null
                        ? `${Math.floor(gaWeeks)} weeks, ${Math.round((gaWeeks % 1) * 10)} days`
                        : null;
                      const gaHint = crfGaDelivery != null
                        ? `CRF: ${parseFloat(crfGaDelivery).toFixed(1)}${gaLabel ? ` (${gaLabel})` : ''}`
                        : null;
                      const outcomeHint = crfOutcome ? `CRF: ${crfOutcome}` : null;
                      const gaDefault = crfGaDelivery != null ? String(parseFloat(crfGaDelivery).toFixed(1)) : '';
                      const gaNote = gaWeeks != null
                        ? (gaWeeks >= 37 ? `Documented delivery GA: ${gaLabel} (Term delivery ≥37w).`
                          : gaWeeks < 34 ? `Documented delivery GA: ${gaLabel} (Preterm delivery <34w).`
                          : `Documented delivery GA: ${gaLabel} (Late preterm 34–37w).`)
                        : 'Gestational age at delivery not mapped from CRF — enter manually.';
                      return (
                        <div className="summary-card-grid" style={{ marginBottom: '14px' }}>
                          <div className="form-group">
                            <label style={{ fontWeight: 700, display: 'flex', justifyContent: 'space-between', fontSize: '12.5px' }}>
                              <span>Gestational Age at Delivery (weeks)</span>
                              {gaHint && (
                                <span style={{ fontSize: '10.5px', color: 'var(--acrn-sky-blue, #4771AD)', fontWeight: 600 }}>
                                  {gaHint}
                                </span>
                              )}
                            </label>
                            <div className="form-input" style={{ backgroundColor: '#f8fafc', color: '#475569', cursor: 'not-allowed', display: 'flex', alignItems: 'center', minHeight: '38px' }}>
                              {gaDefault ? `${gaDefault} weeks` : 'Not mapped from CRF'}
                            </div>
                            <small>{gaNote}</small>
                          </div>

                          <div className="form-group">
                            <label style={{ fontWeight: 700, display: 'flex', justifyContent: 'space-between', fontSize: '12.5px' }}>
                              <span>Pregnancy Outcome</span>
                              {outcomeHint && (
                                <span style={{ fontSize: '10.5px', color: '#0369a1', fontWeight: 600 }}>
                                  {outcomeHint}
                                </span>
                              )}
                            </label>
                            <div className="form-input" style={{ backgroundColor: '#f8fafc', color: '#475569', cursor: 'not-allowed', display: 'flex', alignItems: 'center', minHeight: '38px' }}>
                              {crfOutcome || 'Not mapped from CRF'}
                            </div>
                            <small>Mapped delivery outcome from clinical records.</small>
                          </div>
                        </div>
                      );
                    })()}

                    <label style={{ fontWeight: 700, display: 'block', marginBottom: '8px', fontSize: '12.5px' }}>
                      Closed-Ended Endpoints (SOP-ADJ-002 §6)
                    </label>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '8px', marginBottom: '12px' }}>
                      {VISIT5_ASSESSMENT_OPTIONS.map((opt) => {
                        const isChecked = fetalNeonatalAssessments.includes(opt.code) || (opt.code === 'DELIVERY_GE_37W' && !isSigned && fetalNeonatalAssessments.length === 0) || (opt.code === 'NORMAL_OUTCOME' && !isSigned && fetalNeonatalAssessments.length === 0);
                        return (
                          <label
                            key={opt.code}
                            style={{
                              border: isChecked ? '1px solid #0284c7' : '1px solid #cbd5e1',
                              background: isChecked ? '#f0f9ff' : '#ffffff',
                              borderRadius: '6px',
                              padding: '10px 12px',
                              cursor: isSigned ? 'default' : 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px',
                              fontSize: '12.5px'
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => handleToggleAssessment(opt.code)}
                              disabled={isSigned}
                              style={{ cursor: 'pointer' }}
                            />
                            <div style={{ flex: 1 }}>
                              <span style={{ fontWeight: isChecked ? 700 : 500, color: isChecked ? '#0369a1' : '#1e293b' }}>
                                {opt.label}
                              </span>
                              {opt.adverse && (
                                <span style={{ marginLeft: '6px', fontSize: '10px', color: '#b91c1c', fontWeight: 700 }}>
                                  (Adverse)
                                </span>
                              )}
                            </div>
                          </label>
                        );
                      })}
                    </div>
                  </DropdownSection>
                </div>
              )}
            </>
          )}

          {/* Clean Wizard Navigation Footer */}
          {selectedVisitIndex !== evidenceVisits.length && (
            <div className="wizard-footer" style={{ marginTop: '24px' }}>
              <button className="btn-large btn-back" onClick={() => setCurrentStep(1)}>
                <ArrowLeft size={16} /> Back to Queue
              </button>
              <button className="btn-large btn-next" onClick={() => handleVisitSelect(selectedVisitIndex + 1)}>
                Next <ArrowRight size={16} />
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Completed and signed record view
  if (currentStep === 4 || isSigned) {
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
                <div style={{ fontWeight: 700, color: 'var(--acrn-navy-dark)' }}>
                  {activeCase.last_diagnosis || activeCase.determination || 'Adjudicator determination — see signed record'}
                </div>
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

  return null;
}
