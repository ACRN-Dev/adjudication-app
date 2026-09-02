import React, { useState, useEffect, useMemo } from 'react';
import {
  X, Eye, CheckCircle2, AlertTriangle, AlertOctagon, Scale, ShieldCheck,
  Activity, Stethoscope, FlaskConical, Calendar, Baby, FileText, HeartPulse,
  Clock, Copy, Check, Printer, Search, ListFilter, Users, ChevronDown,
  ChevronUp, Lock, ArrowRight, ExternalLink, Sparkles, User, Info, FileSpreadsheet
} from 'lucide-react';

/**
 * Standard protocol section definitions & iconography for FORM-ADJ-15A / 15B
 */
const SECTION_CONFIG = {
  1: { title: 'Case Metadata & Identifier', category: 'metadata', icon: FileText, color: '#3b82f6' },
  2: { title: 'Endpoint & Prediction Window', category: 'clinical', icon: Clock, color: '#6366f1' },
  3: { title: 'Pregnancy Dating', category: 'dating', icon: Calendar, color: '#8b5cf6' },
  4: { title: 'Clinical Presentation Summary', category: 'clinical', icon: Stethoscope, color: '#0ea5e9' },
  5: { title: 'Blood Pressure Course', category: 'vitals', icon: Activity, color: '#ef4444' },
  6: { title: 'Proteinuria Evidence', category: 'labs', icon: FlaskConical, color: '#f59e0b' },
  7: { title: 'Laboratory Course (Haematology & Biochem)', category: 'labs', icon: FlaskConical, color: '#10b981' },
  8: { title: 'Maternal Clinical Course', category: 'maternal', icon: HeartPulse, color: '#ec4899' },
  9: { title: 'Fetal Assessment (Growth & Doppler)', category: 'fetal', icon: Baby, color: '#14b8a6' },
  10: { title: 'Delivery Record', category: 'delivery', icon: FileText, color: '#64748b' },
  11: { title: 'Maternal Outcome & SAEs', category: 'outcomes', icon: AlertTriangle, color: '#dc2626' },
  12: { title: 'Neonatal Outcome', category: 'outcomes', icon: Baby, color: '#0284c7' },
  13: { title: 'Missing Data & Queries', category: 'quality', icon: ShieldCheck, color: '#6b7280' },
};

/**
 * Parse structured or freeform reviewer rationale into structured section items.
 */
export function parseClinicalSections(rawText) {
  if (!rawText || typeof rawText !== 'string' || !rawText.trim()) {
    return [];
  }

  const text = rawText.trim();
  const rawBlocks = text.split(/(?=\n*SECTION\s+\d+\s*[—–-]?|\n*\[SECTION\s+\d+\]|\n*Delivery Record:|\n*Medication Log:)/i);
  const sections = [];

  for (let i = 0; i < rawBlocks.length; i++) {
    const block = rawBlocks[i].trim();
    if (!block) continue;

    const numMatch = block.match(/^(?:SECTION\s+(\d+)\s*[—–-]?\s*([^\n\r]*)|\[SECTION\s+(\d+)\]\s*([^\n\r]*))/i);
    let secNum = null;
    let title = '';
    let body = '';

    if (numMatch) {
      secNum = parseInt(numMatch[1] || numMatch[3], 10);
      title = (numMatch[2] || numMatch[4] || '').trim();
      body = block.replace(numMatch[0], '').trim();
      if (!title && SECTION_CONFIG[secNum]) {
        title = SECTION_CONFIG[secNum].title;
      }
    } else {
      // Check for standalone header like "Delivery Record: ..."
      const lineMatch = block.match(/^([A-Za-z0-9\s/—–-]{3,40}):\s*([\s\S]*)$/);
      if (lineMatch) {
        title = lineMatch[1].trim();
        body = lineMatch[2].trim();
      } else {
        title = i === 0 ? 'Clinical Rationale / Notes' : `Evidence Note ${i + 1}`;
        body = block;
      }
    }

    const config = (secNum && SECTION_CONFIG[secNum]) || {
      title: title || 'Clinical Section',
      category: 'general',
      icon: FileText,
      color: '#475569',
    };

    const isNotDocumented = (
      /\[Not documented\s*[—–-]?\s*not assessable\]/i.test(body) ||
      /^not documented$/i.test(body) ||
      /^none reported$/i.test(body) ||
      /^\[Pending derivation\]/i.test(body)
    );

    const isSevere = (
      /≥\s*160\/110/i.test(body) ||
      /severe-range/i.test(body) ||
      /with severe features/i.test(body) ||
      /thrombocytopenia/i.test(body) ||
      /emergency caesarean/i.test(body) ||
      /aedf/i.test(body) ||
      /eclampsia/i.test(body) ||
      /hellp/i.test(body)
    );

    const isAbnormal = (
      isSevere ||
      /abnormal/i.test(body) ||
      /elevated/i.test(body) ||
      /dipstick (?:2\+|3\+|4\+)/i.test(body) ||
      /upcr\s*(?:≥|>=|>)\s*0\.3/i.test(body) ||
      /platelet(?: count)?:?\s*(?:[1-9]\d|\d)\b/i.test(body)
    );

    // Split body lines into key-value pairs where applicable
    const lines = body.split('\n').map(l => l.trim()).filter(Boolean);
    const pairs = [];
    const paragraphs = [];

    lines.forEach(line => {
      const kv = line.match(/^([^:]+):\s*(.+)$/);
      if (kv && kv[1].length < 45) {
        pairs.push({ key: kv[1].trim(), value: kv[2].trim() });
      } else {
        paragraphs.push(line);
      }
    });

    sections.push({
      secNum,
      title: title || config.title,
      category: config.category,
      icon: config.icon,
      color: config.color,
      body,
      pairs,
      paragraphs,
      isNotDocumented,
      isSevere,
      isAbnormal,
    });
  }

  return sections;
}

/**
 * Format ISO or SQL dates cleanly.
 */
function formatCleanDate(val, includeTime = false) {
  if (!val) return 'Not recorded';
  const d = new Date(val);
  if (isNaN(d.getTime())) return String(val);
  const dateStr = d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  if (!includeTime) return dateStr;
  const timeStr = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  return `${dateStr}, ${timeStr}`;
}

/**
 * Resolve concordance badge styling & human label.
 */
function getConcordanceMeta(raw) {
  const code = String(raw || '').toUpperCase();
  if (code.includes('MAJORITY') || code === 'RESOLVED_BY_MAJORITY') {
    return { label: 'Resolved by Majority', bg: '#f0fdf4', color: '#15803d', border: '#bbf7d0', icon: CheckCircle2 };
  }
  if (code === 'CONCORDANT_A_EQUALS_B' || code === 'CONCORDANT_ALL_THREE' || (code.includes('CONCORDANT') && !code.includes('DISCORDANT'))) {
    return { label: 'Concordant (A = B)', bg: '#ecfdf5', color: '#065f46', border: '#a7f3d0', icon: CheckCircle2 };
  }
  if (code.includes('THREE_WAY') || code.includes('DIVERGENT')) {
    return { label: '3-Way Divergent (A ≠ B ≠ C)', bg: '#fffbeb', color: '#b45309', border: '#fde68a', icon: Scale };
  }
  if (code === 'RESOLVED_BY_REVIEWER_C') {
    return { label: 'Resolved by Reviewer C', bg: '#eff6ff', color: '#1d4ed8', border: '#bfdbfe', icon: ShieldCheck };
  }
  if (code.includes('DISCORDANT')) {
    return { label: 'Discordant (A ≠ B)', bg: '#fff1f2', color: '#9f1239', border: '#fecdd3', icon: AlertTriangle };
  }
  if (code.includes('SINGLE')) {
    return { label: 'Single Reviewer Complete (1/2)', bg: '#f8fafc', color: '#475569', border: '#cbd5e1', icon: User };
  }
  if (code.includes('CLOSED')) {
    return { label: 'Closed & Locked', bg: '#f1f5f9', color: '#334155', border: '#cbd5e1', icon: Lock };
  }
  return { label: code || 'Pending', bg: '#f8fafc', color: '#64748b', border: '#e2e8f0', icon: Clock };
}

export default function EvidenceInspectorModal({
  item,
  allPatientVisits = [],
  onClose,
  onSelectVisit,
}) {
  const [activeTab, setActiveTab] = useState('side_by_side'); // 'side_by_side' | 'crf_sections' | 'narrative_prose'
  const [selectedReviewerKey, setSelectedReviewerKey] = useState('reviewer_a');
  const [searchQuery, setSearchQuery] = useState('');
  const [hideEmptySections, setHideEmptySections] = useState(false);
  const [copied, setCopied] = useState(false);
  const [expandedSections, setExpandedSections] = useState({});

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!item) return null;

  const reviewers = [
    { key: 'reviewer_a', roleLabel: 'Reviewer A', roleBadge: 'Primary Reviewer', data: item.reviewer_a },
    { key: 'reviewer_b', roleLabel: 'Reviewer B', roleBadge: 'Secondary Reviewer', data: item.reviewer_b },
    { key: 'reviewer_c', roleLabel: 'Reviewer C', roleBadge: 'Arbitrator / 3rd Reviewer', data: item.reviewer_c },
  ].filter(r => r.data != null);

  // If active selected reviewer key is missing, default to first available
  const activeReviewer = reviewers.find(r => r.key === selectedReviewerKey) || reviewers[0];

  const concordanceMeta = getConcordanceMeta(item.concordance_status || item.concordance);
  const ConcordanceIcon = concordanceMeta.icon;

  const parsedSections = useMemo(() => {
    return parseClinicalSections(activeReviewer?.data?.rationale || '');
  }, [activeReviewer]);

  const filteredSections = useMemo(() => {
    return parsedSections.filter(sec => {
      if (hideEmptySections && sec.isNotDocumented) return false;
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return (
        sec.title.toLowerCase().includes(q) ||
        sec.body.toLowerCase().includes(q) ||
        (sec.secNum && String(sec.secNum).includes(q))
      );
    });
  }, [parsedSections, hideEmptySections, searchQuery]);

  const handleCopySummary = () => {
    if (!item) return;
    const summaryText = `ACRN EVIDENCE SUMMARY — Subject ${item.subject_id} (${item.visit_code || `Visit ${item.visit_number || 1}`})
Study: ${item.study_code || 'PROTECT-Africa'} | Site: ${item.site_code || 'HARARE_01'}
Visit Date: ${formatCleanDate(item.visit_date)}
Concordance: ${concordanceMeta.label}
${reviewers.map(r => `• ${r.roleLabel} (${r.data.name || r.data.upn || 'N/A'}): ${r.data.diagnosis || 'Pending'} | Certainty: ${r.data.certainty || 'N/A'} | Severity: ${r.data.severity || 'N/A'} | Criteria: ${r.data.meets_criteria ? 'Yes' : 'No'}`).join('\n')}
${item.final_outcome ? `Final Decision: ${item.final_outcome.diagnosis} (${item.final_outcome.adopted_reviewer || 'Consensus'})` : ''}`;
    
    navigator.clipboard.writeText(summaryText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleSection = (idx) => {
    setExpandedSections(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const isLope = String(item.study_code || '').toUpperCase().includes('LOPE');

  return (
    <div className="evidence-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="evidence-modal modern-inspector"
        role="dialog"
        aria-modal="true"
        aria-labelledby="inspector-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* TOP TOOLBAR & HEADER */}
        <header className="inspector-header">
          <div className="inspector-title-group">
            <div className="inspector-kicker">
              <Stethoscope size={13} className="text-teal" />
              <span>Independent Endpoint Adjudication • Evidence Inspector</span>
              <span className={`study-pill ${isLope ? 'lope' : ''}`}>{item.study_code || 'PROTECT-Africa'}</span>
              <span className="site-pill">Site: {item.site_code || 'HARARE_01'}</span>
            </div>
            <div className="inspector-title-row">
              <h2 id="inspector-title" className="inspector-patient-id">{item.subject_id}</h2>
              <span className="visit-badge-pill">{item.visit_code || `Visit ${item.visit_number || 1}`}</span>
              {item.visit_date && (
                <span className="visit-date-pill">
                  <Calendar size={13} /> {formatCleanDate(item.visit_date)}
                </span>
              )}
            </div>
          </div>

          <div className="inspector-header-actions">
            <button
              type="button"
              className="inspector-action-btn"
              onClick={handleCopySummary}
              title="Copy case summary to clipboard"
            >
              {copied ? <Check size={14} className="text-green" /> : <Copy size={14} />}
              <span>{copied ? 'Copied' : 'Copy Summary'}</span>
            </button>
            <button
              type="button"
              className="inspector-action-btn"
              onClick={() => window.print()}
              title="Print evidence view"
            >
              <Printer size={14} />
              <span>Print</span>
            </button>
            <button
              type="button"
              className="inspector-close-btn"
              onClick={onClose}
              aria-label="Close Evidence Inspector"
            >
              <X size={18} />
            </button>
          </div>
        </header>

        {/* MULTI-VISIT RIBBON (If patient has multiple visits) */}
        {allPatientVisits.length > 1 && (
          <div className="inspector-visit-nav">
            <span className="visit-nav-label">Patient Visits:</span>
            <div className="visit-nav-buttons">
              {allPatientVisits.map((v) => {
                const isCurrent = v.id === item.id || (v.visit_number === item.visit_number && v.subject_id === item.subject_id);
                return (
                  <button
                    key={v.id || v.visit_number}
                    type="button"
                    className={`visit-nav-btn ${isCurrent ? 'active' : ''}`}
                    onClick={() => onSelectVisit?.(v)}
                  >
                    <span>{v.visit_code || `Visit ${v.visit_number}`}</span>
                    <small>{formatCleanDate(v.visit_date)}</small>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* SUMMARY STATS & CONCORDANCE BAR */}
        <div className="inspector-summary-bar">
          <div className="inspector-stat-card">
            <span className="stat-label">Concordance Determination</span>
            <div
              className="concordance-pill"
              style={{
                backgroundColor: concordanceMeta.bg,
                color: concordanceMeta.color,
                borderColor: concordanceMeta.border,
              }}
            >
              <ConcordanceIcon size={14} />
              <strong>{concordanceMeta.label}</strong>
            </div>
          </div>

          <div className="inspector-stat-card">
            <span className="stat-label">Independent Reviewers</span>
            <div className="reviewers-count-pill">
              <Users size={14} />
              <span><strong>{reviewers.length}</strong> submitted ({reviewers.map(r => r.roleLabel).join(', ')})</span>
            </div>
          </div>

          <div className="inspector-stat-card">
            <span className="stat-label">Protocol Safety Gate</span>
            <div className="gate-status-pill">
              <ShieldCheck size={14} />
              <span>ICH E6(R2) / 21 CFR Part 11 Blinded</span>
            </div>
          </div>

          {item.final_outcome && (
            <div className="inspector-stat-card highlight-final">
              <span className="stat-label">Chair / Committee Outcome</span>
              <div className="final-verdict-pill">
                <strong>{item.final_outcome.diagnosis || 'Consensus Locked'}</strong>
                <small>({item.final_outcome.adopted_reviewer || 'Arbitrated'})</small>
              </div>
            </div>
          )}
        </div>

        {/* VIEW MODE TABS */}
        <nav className="inspector-tabs" aria-label="Evidence Inspector Views">
          <button
            type="button"
            className={`inspector-tab-btn ${activeTab === 'side_by_side' ? 'active' : ''}`}
            onClick={() => setActiveTab('side_by_side')}
          >
            <Users size={15} />
            <span>Side-by-Side Reviewer Comparison</span>
            <span className="tab-count">{reviewers.length}</span>
          </button>

          <button
            type="button"
            className={`inspector-tab-btn ${activeTab === 'crf_sections' ? 'active' : ''}`}
            onClick={() => setActiveTab('crf_sections')}
          >
            <FileSpreadsheet size={15} />
            <span>Structured CRF Sections</span>
            <span className="tab-count">{parsedSections.length}</span>
          </button>

          <button
            type="button"
            className={`inspector-tab-btn ${activeTab === 'narrative_prose' ? 'active' : ''}`}
            onClick={() => setActiveTab('narrative_prose')}
          >
            <FileText size={15} />
            <span>Full Blinded Narrative Prose</span>
          </button>
        </nav>

        {/* MODAL MAIN CONTENT BODY */}
        <main className="inspector-body">
          {/* TAB 1: SIDE-BY-SIDE REVIEWER COMPARISON */}
          {activeTab === 'side_by_side' && (
            <div className={`reviewer-grid columns-${Math.min(reviewers.length, 3)}`}>
              {reviewers.map(({ key, roleLabel, roleBadge, data }) => {
                const isArbitrator = key === 'reviewer_c';
                const sections = parseClinicalSections(data.rationale);
                const hasDifferential = Boolean(data.differential_diagnosis);
                const cert = String(data.certainty || '').toLowerCase();
                const certClass = cert.includes('definite') ? 'definite' : cert.includes('probable') ? 'probable' : cert.includes('possible') ? 'possible' : 'neutral';

                return (
                  <article className={`reviewer-card ${isArbitrator ? 'arbitrator-card' : ''}`} key={key}>
                    {/* REVIEWER HEADER */}
                    <div className="reviewer-card-header">
                      <div>
                        <div className="reviewer-role-row">
                          <span className="reviewer-role-title">{roleLabel}</span>
                          <span className="reviewer-role-tag">{roleBadge}</span>
                        </div>
                        <h3 className="reviewer-name">{data.name || data.upn || 'Independent Adjudicator'}</h3>
                        {data.upn && data.name && <div className="reviewer-email">{data.upn}</div>}
                      </div>
                      {data.signed_at && (
                        <div className="reviewer-signature-badge">
                          <ShieldCheck size={13} className="text-emerald" />
                          <span>e-Signed: {formatCleanDate(data.signed_at, true)}</span>
                        </div>
                      )}
                    </div>

                    {/* CLINICAL VERDICT HERO */}
                    <div className="verdict-hero">
                      <div className="verdict-primary">
                        <span className="verdict-label">Diagnosis Verdict</span>
                        <div className="verdict-diagnosis-pill">
                          <strong>{data.diagnosis || 'Pending'}</strong>
                        </div>
                      </div>

                      <div className="verdict-pills-row">
                        {data.certainty && (
                          <span className={`cert-pill ${certClass}`}>
                            Certainty: <strong>{data.certainty}</strong>
                          </span>
                        )}
                        <span className={`criteria-pill ${data.meets_criteria ? 'meets' : 'fails'}`}>
                          {data.meets_criteria ? '✓ Meets Protocol Criteria' : '✗ Protocol Criteria Not Met'}
                        </span>
                      </div>
                    </div>

                    {/* KEY CLINICAL PARAMETERS */}
                    <div className="clinical-params-grid">
                      <div className="param-item">
                        <span className="param-label">Onset Class</span>
                        <strong className="param-value">{data.onset_class || 'Not recorded'}</strong>
                      </div>
                      <div className="param-item">
                        <span className="param-label">Severity Grade</span>
                        <strong className="param-value">{data.severity || 'Not recorded'}</strong>
                      </div>
                      <div className="param-item">
                        <span className="param-label">Date of Diagnosis</span>
                        <strong className="param-value">{formatCleanDate(data.date_of_diagnosis)}</strong>
                      </div>
                      <div className="param-item">
                        <span className="param-label">Visit Assessed</span>
                        <strong className="param-value">{item.visit_code || `Visit ${item.visit_number || 1}`}</strong>
                      </div>
                    </div>

                    {/* DIFFERENTIAL DIAGNOSIS (IF DOCUMENTED) */}
                    {hasDifferential && (
                      <div className="differential-box">
                        <AlertTriangle size={14} className="text-amber" />
                        <div>
                          <strong>Differential Diagnosis:</strong>
                          <p>{data.differential_diagnosis}</p>
                        </div>
                      </div>
                    )}

                    {/* STRUCTURED RATIONALE & EVIDENCE BREAKDOWN */}
                    <div className="reviewer-rationale-wrapper">
                      <div className="rationale-header-bar">
                        <span className="rationale-heading">Clinical Evidence & Rationale ({sections.length} sections)</span>
                      </div>

                      <div className="rationale-sections-list">
                        {sections.length === 0 ? (
                          <div className="rationale-empty">
                            <Info size={14} /> No narrative text attached to this determination.
                          </div>
                        ) : (
                          sections.map((sec, sIdx) => {
                            const Icon = sec.icon || FileText;
                            return (
                              <div
                                key={sIdx}
                                className={`rationale-section-card ${sec.isSevere ? 'severe' : sec.isAbnormal ? 'abnormal' : ''} ${sec.isNotDocumented ? 'muted' : ''}`}
                              >
                                <div className="sec-header">
                                  <div className="sec-title-wrap">
                                    <Icon size={14} style={{ color: sec.color }} />
                                    <span className="sec-title">
                                      {sec.secNum ? `Section ${sec.secNum}: ` : ''}{sec.title}
                                    </span>
                                  </div>
                                  {sec.isSevere && <span className="severe-tag"><AlertOctagon size={11} /> Severe Finding</span>}
                                  {sec.isNotDocumented && <span className="not-doc-tag">Not Documented</span>}
                                </div>

                                <div className="sec-content">
                                  {sec.pairs.length > 0 ? (
                                    <div className="sec-kv-grid">
                                      {sec.pairs.map((p, pIdx) => (
                                        <div className="sec-kv-row" key={pIdx}>
                                          <span className="sec-k">{p.key}:</span>
                                          <span className="sec-v">{p.value}</span>
                                        </div>
                                      ))}
                                    </div>
                                  ) : (
                                    <p className="sec-prose">{sec.body}</p>
                                  )}
                                </div>
                              </div>
                            );
                          })
                        )}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}

          {/* TAB 2: STRUCTURED CRF SECTIONS DEEP DIVE */}
          {activeTab === 'crf_sections' && (
            <div className="crf-view-container">
              {/* REVIEWER SELECTOR (IF MULTIPLE) */}
              {reviewers.length > 1 && (
                <div className="reviewer-selector-bar">
                  <span className="selector-label">Inspect Rationale From:</span>
                  <div className="selector-buttons">
                    {reviewers.map(r => (
                      <button
                        key={r.key}
                        type="button"
                        className={`selector-btn ${activeReviewer?.key === r.key ? 'active' : ''}`}
                        onClick={() => setSelectedReviewerKey(r.key)}
                      >
                        <strong>{r.roleLabel}</strong>
                        <small>{r.data.diagnosis || 'Pending'}</small>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* SEARCH & FILTERS BAR */}
              <div className="crf-filter-toolbar">
                <div className="search-input-wrapper">
                  <Search size={14} className="search-icon" />
                  <input
                    type="text"
                    placeholder="Search clinical evidence, vitals, labs, findings..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="crf-search-input"
                  />
                  {searchQuery && (
                    <button type="button" className="clear-search-btn" onClick={() => setSearchQuery('')}>
                      <X size={13} />
                    </button>
                  )}
                </div>

                <label className="toggle-filter-label">
                  <input
                    type="checkbox"
                    checked={hideEmptySections}
                    onChange={(e) => setHideEmptySections(e.target.checked)}
                  />
                  <span>Hide unrecorded / empty sections</span>
                </label>
              </div>

              {/* SECTION CARDS */}
              <div className="crf-sections-grid">
                {filteredSections.length === 0 ? (
                  <div className="no-sections-found">
                    <Search size={24} />
                    <p>No clinical sections match your search "{searchQuery}".</p>
                    <button type="button" className="reset-btn" onClick={() => { setSearchQuery(''); setHideEmptySections(false); }}>
                      Reset filters
                    </button>
                  </div>
                ) : (
                  filteredSections.map((sec, idx) => {
                    const Icon = sec.icon || FileText;
                    const isExpanded = expandedSections[idx] ?? true;

                    return (
                      <div
                        key={idx}
                        className={`crf-card ${sec.isSevere ? 'is-severe' : sec.isAbnormal ? 'is-abnormal' : ''} ${sec.isNotDocumented ? 'is-empty' : ''}`}
                      >
                        <header className="crf-card-header" onClick={() => toggleSection(idx)}>
                          <div className="crf-header-left">
                            <div className="crf-icon-badge" style={{ backgroundColor: `${sec.color}18`, color: sec.color }}>
                              <Icon size={16} />
                            </div>
                            <div>
                              <div className="crf-sec-category">{sec.category.toUpperCase()}</div>
                              <h4 className="crf-sec-title">
                                {sec.secNum ? `Section ${sec.secNum}: ` : ''}{sec.title}
                              </h4>
                            </div>
                          </div>

                          <div className="crf-header-right">
                            {sec.isSevere && <span className="tag-severe"><AlertOctagon size={12} /> Severe Metric</span>}
                            {sec.isNotDocumented && <span className="tag-muted">Not Documented</span>}
                            <button type="button" className="accordion-btn" aria-label="Toggle section">
                              {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </button>
                          </div>
                        </header>

                        {isExpanded && (
                          <div className="crf-card-body">
                            {sec.pairs.length > 0 ? (
                              <table className="crf-table">
                                <tbody>
                                  {sec.pairs.map((p, pIdx) => {
                                    const isHighlighted = (
                                      /severe/i.test(p.value) ||
                                      /≥\s*160\/110/i.test(p.value) ||
                                      /thrombocytopenia/i.test(p.value) ||
                                      /emergency/i.test(p.value)
                                    );
                                    return (
                                      <tr key={pIdx} className={isHighlighted ? 'row-highlighted' : ''}>
                                        <th scope="row" className="crf-prop-name">{p.key}</th>
                                        <td className="crf-prop-value">{p.value}</td>
                                      </tr>
                                    );
                                  })}
                                </tbody>
                              </table>
                            ) : (
                              <div className="crf-raw-prose">{sec.body}</div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* TAB 3: FULL BLINDED NARRATIVE PROSE */}
          {activeTab === 'narrative_prose' && (
            <div className="narrative-prose-container">
              <div className="prose-toolbar">
                <div className="prose-info">
                  <FileText size={15} className="text-teal" />
                  <span>Blinded Narrative Documentation • Reviewer: <strong>{activeReviewer?.roleLabel} ({activeReviewer?.data?.name || activeReviewer?.data?.upn || 'Adjudicator'})</strong></span>
                </div>
                {reviewers.length > 1 && (
                  <div className="prose-switcher">
                    {reviewers.map(r => (
                      <button
                        key={r.key}
                        type="button"
                        className={`prose-switch-btn ${activeReviewer?.key === r.key ? 'active' : ''}`}
                        onClick={() => setSelectedReviewerKey(r.key)}
                      >
                        {r.roleLabel}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="narrative-prose-paper">
                <pre className="narrative-pre-text">
                  {activeReviewer?.data?.rationale || 'No narrative text recorded for this determination.'}
                </pre>
              </div>
            </div>
          )}
        </main>

        {/* MODAL FOOTER */}
        <footer className="inspector-footer">
          <div className="footer-left">
            <span className="audit-note">
              ICH GCP E6(R2) &amp; 21 CFR Part 11 Audit Trail Compliant • Case {item.subject_id} • Visit {item.visit_code || item.visit_number}
            </span>
          </div>
          <div className="footer-right">
            <button type="button" className="chair-btn chair-btn-secondary" onClick={onClose}>
              Close Inspector
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
