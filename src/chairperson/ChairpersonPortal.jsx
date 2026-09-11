import React, { useState, useEffect } from 'react';
import {
  Users, FileText, CheckCircle, AlertTriangle, Scale, Lock, LogOut,
  Calendar, Download, RefreshCw, Send, CheckSquare, ShieldCheck, ChevronRight, Eye, X
} from 'lucide-react';
import EvidenceInspectorModal from './EvidenceInspectorModal';
import './chairperson.css';

export default function ChairpersonPortal({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('concordance');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [adjudications, setAdjudications] = useState([]);
  const [summary, setSummary] = useState({ concordant: 0, discordant: 0, three_way_divergent: 0, closed: 0 });
  const [agendaPack, setAgendaPack] = useState(null);
  const [meetings, setMeetings] = useState([]);
  const [isUsingDemoData, setIsUsingDemoData] = useState(false);

  // Minutes Form state
  const [meetingTitle, setMeetingTitle] = useState('PROTECT-Africa Adjudication Committee Session #1');
  const [batchId, setBatchId] = useState('BATCH-2026-08');
  const [attendees, setAttendees] = useState('chairperson@acrnhealth.com, adjudicatora@acrnhealth.com, adjudicatorb@acrnhealth.com, monitor1@acrnhealth.com');
  const [quorumMet, setQuorumMet] = useState(true);
  const [minutesText, setMinutesText] = useState('Committee convened at 14:00 CAT. Quorum established with 4 members present. Discordant cases arbitrated according to ISSHP 2021 criteria. Consensus achieved and all records locked.');
  const [selectedCaseIds, setSelectedCaseIds] = useState([]);
  const [isSigning, setIsSigning] = useState(false);
  const [signSuccess, setSignSuccess] = useState(null);
  const [inspectionItem, setInspectionItem] = useState(null);
  const [finalizeItem, setFinalizeItem] = useState(null);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [releaseStudy, setReleaseStudy] = useState('PROTECT-Africa');
  const [releaseFormat, setReleaseFormat] = useState('');
  const [finalizeDraft, setFinalizeDraft] = useState({
    meeting_title: 'Single-case committee arbitration',
    minutes: '',
    chair_rationale: '',
    final_diagnosis: 'PE',
    final_onset_class: 'EOPE',
    final_severity: 'With severe features',
    final_certainty: 'Definite',
    attendees: 'chairperson@acrnhealth.com, adjudicatora@acrnhealth.com, adjudicatorb@acrnhealth.com',
    members_present: 3,
  });
  const [newMeetingTitle, setNewMeetingTitle] = useState('Committee review and discordant case arbitration');
  const [newMeetingDateTime, setNewMeetingDateTime] = useState('2026-09-15T14:00');
  const [newMeetingAttendees, setNewMeetingAttendees] = useState('chairperson@acrnhealth.com, adjudicatora@acrnhealth.com, adjudicatorb@acrnhealth.com');
  const [newMeetingBatchId, setNewMeetingBatchId] = useState('BATCH-2026-08');
  const [newMeetingAgenda, setNewMeetingAgenda] = useState('Review discordant cases, confirm consensus and finalize decisions, then record chairperson sign-off.');
  const meetingCases = adjudications.filter((item, index, rows) =>
    rows.findIndex(candidate => candidate.subject_id === item.subject_id) === index
  );
  const groupedAdjudications = adjudications.reduce((groups, item) => {
    const key = item.subject_id || item.participant_id || 'Unknown participant';
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
    return groups;
  }, {});
  const formatDate = (value) => value ? new Date(value).toLocaleString() : 'Not recorded';
  const displayDiagnosis = (reviewer) => reviewer?.diagnosis || 'Pending';
  const renderRationale = (rationale) => {
    const sections = String(rationale || '').split(/\s*(?=SECTION\s+\d+)/i).filter(Boolean);
    return sections.map((section, index) => {
      const match = section.match(/^(SECTION\s+\d+\s*[—-]?\s*[^:]*)(?::)?\s*/i);
      const title = match ? match[1].trim() : `Evidence detail ${index + 1}`;
      const body = match ? section.slice(match[0].length).trim() : section.trim();
      return <div className="rationale-section" key={`${title}-${index}`}><strong>{title}</strong><p>{body}</p></div>;
    });
  };

  const fetchAdjudications = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch('/api/chairperson/completed-adjudications');
      if (res.ok) {
        const data = await res.json();
        const items = Array.isArray(data.items) ? data.items : [];
        setAdjudications(items);
        setSummary(data.summary || { concordant: 0, discordant: 0, three_way_divergent: 0, closed: 0 });
        setSelectedCaseIds([...new Set(items.map(i => i.subject_id))]);
      } else {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Chairperson data request failed (${res.status})`);
      }
    } catch (e) {
      console.error('Failed to fetch adjudications:', e);
      setErrorMsg(e.message);
      setAdjudications([]);
      setSummary({ concordant: 0, discordant: 0, three_way_divergent: 0, closed: 0 });
      setSelectedCaseIds([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchAgenda = async () => {
    try {
      const res = await fetch(`/api/chairperson/agenda-pack?batch_id=${encodeURIComponent(batchId)}`);
      if (res.ok) {
        const data = await res.json();
        setAgendaPack(data.total_cases > 0 ? data : null);
      }
    } catch (e) {
      console.error('Failed to fetch agenda:', e);
    }
  };

  const fetchMeetings = async () => {
    try {
      const res = await fetch('/api/chairperson/meetings');
      if (res.ok) {
        const data = await res.json();
        setMeetings(data.items || []);
      }
    } catch (e) {
      console.error('Failed to fetch meetings:', e);
    }
  };

  const downloadFinalRelease = async (format) => {
    setReleaseFormat(format);
    try {
      const response = await fetch(`/api/export/final-study.${format}?study=${encodeURIComponent(releaseStudy)}`, { credentials: 'include' });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || `Final study ${format.toUpperCase()} export failed (${response.status}).`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `ACRN_Final_Study_Release_${releaseStudy}.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      alert(error.message || 'Final study release export failed.');
    } finally {
      setReleaseFormat('');
    }
  };

  const createMeeting = async (e) => {
    e.preventDefault();
    try {
      const attendees = newMeetingAttendees.split(',').map(item => item.trim()).filter(Boolean);
      const payload = {
        meeting_title: newMeetingTitle,
        scheduled_at: newMeetingDateTime,
        batch_id: newMeetingBatchId || 'BATCH-UNSPECIFIED',
        attendees,
        case_ids: selectedCaseIds,
        agenda: newMeetingAgenda,
        chair_name: user?.display_name || 'Adjudication Chairperson'
      };
      const res = await fetch('/api/chairperson/meetings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Unable to create meeting.');
      }
      await fetchMeetings();
      setNewMeetingTitle('Committee review and discordant case arbitration');
      setNewMeetingAttendees('chairperson@acrnhealth.com, adjudicatora@acrnhealth.com, adjudicatorb@acrnhealth.com');
      setNewMeetingAgenda('Review discordant cases, confirm consensus and finalize decisions, then record chairperson sign-off.');
      setActiveTab('archive');
    } catch (err) {
      alert(err.message || 'Meeting could not be created.');
    }
  };

  const cancelMeeting = async (meetingId, reason = 'Meeting cancelled by chairperson.') => {
    try {
      const res = await fetch(`/api/chairperson/meetings/${meetingId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Unable to cancel meeting.');
      }
      await fetchMeetings();
      alert('Meeting cancelled successfully.');
    } catch (err) {
      alert(err.message || 'Meeting cancellation failed.');
    }
  };

  const openFinalizeCase = (item) => {
    const reviewer = item.reviewer_a || {};
    setFinalizeItem(item);
    setFinalizeDraft({
      meeting_title: 'Single-case committee arbitration',
      minutes: '',
      chair_rationale: '',
      final_diagnosis: reviewer.diagnosis || 'PE',
      final_onset_class: reviewer.onset_class || 'EOPE',
      final_severity: reviewer.severity || 'With severe features',
      final_certainty: reviewer.certainty || 'Definite',
      attendees: 'chairperson@acrnhealth.com, adjudicatora@acrnhealth.com, adjudicatorb@acrnhealth.com',
      members_present: 3,
    });
  };

  const handleFinalizeCase = async (e) => {
    e.preventDefault();
    if (!finalizeItem) return;
    setIsFinalizing(true);
    try {
      const res = await fetch(`/api/chairperson/cases/${encodeURIComponent(finalizeItem.subject_id)}/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...finalizeDraft,
          attendees: finalizeDraft.attendees.split(',').map(value => value.trim()).filter(Boolean),
          members_present: Number(finalizeDraft.members_present),
          visit_number: finalizeItem.visit_number || 1,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Unable to finalize case.');
      setFinalizeItem(null);
      setSignSuccess(data);
      await fetchAdjudications();
      await fetchMeetings();
      await fetchAgenda();
    } catch (err) {
      alert(err.message || 'Case finalization failed.');
    } finally {
      setIsFinalizing(false);
    }
  };

  useEffect(() => {
    fetchAdjudications();
    fetchAgenda();
    fetchMeetings();
  }, []);

  const handleToggleCaseSelection = (subjId) => {
    setSelectedCaseIds(prev =>
      prev.includes(subjId) ? prev.filter(id => id !== subjId) : [...prev, subjId]
    );
  };

  const handleSignOffMeeting = async (e) => {
    e.preventDefault();
    if (!meetingTitle || !minutesText || selectedCaseIds.length === 0) {
      alert('Please fill in the meeting title, minutes, and select at least one case to close.');
      return;
    }
    setIsSigning(true);
    try {
      const attendeeList = attendees.split(',').map(a => a.trim()).filter(Boolean);
      const res = await fetch('/api/chairperson/meetings/sign-off', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          meeting_title: meetingTitle,
          batch_id: batchId,
          attendees: attendeeList,
          quorum_met: quorumMet,
          minutes: minutesText,
          case_ids: selectedCaseIds,
          chair_name: user?.display_name || 'Adjudication Chairperson'
        })
      });
      if (res.ok) {
        const data = await res.json();
        setSignSuccess(data);
        fetchAdjudications();
        fetchMeetings();
        fetchAgenda();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || 'Sign-off failed'}`);
      }
    } catch (err) {
      alert(`Network error: ${err.message}`);
    } finally {
      setIsSigning(false);
    }
  };

  return (
    <div className="chair-container">
      {/* Chairperson Header */}
      <header className="chair-header">
        <div className="chair-header-title">
          <img src="/acrn-logo.png" alt="ACRN" style={{ height: '32px', width: 'auto', objectFit: 'contain' }} />
          <div>
            <h1>Adjudication Chairperson Workspace</h1>
            <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
              PROTECT-Africa &amp; LOPE-Nigeria Endpoint Consensus Management
            </div>
          </div>
          <span className="chair-badge">Chairperson Role</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '13px', fontWeight: 600 }}>{user?.display_name || 'Chairperson'}</div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>{user?.email}</div>
          </div>
          <button
            onClick={onLogout}
            className="chair-btn chair-btn-secondary"
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            <LogOut size={14} /> Sign Out
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="chair-nav">
        <button
          className={`chair-nav-btn ${activeTab === 'concordance' ? 'active' : ''}`}
          onClick={() => setActiveTab('concordance')}
        >
          <Scale size={15} /> Completed Adjudications &amp; Concordance
        </button>
        <button
          className={`chair-nav-btn ${activeTab === 'agenda' ? 'active' : ''}`}
          onClick={() => { setActiveTab('agenda'); fetchAgenda(); }}
        >
          <FileText size={15} /> Meeting Agenda Pack
        </button>
        <button
          className={`chair-nav-btn ${activeTab === 'minutes' ? 'active' : ''}`}
          onClick={() => setActiveTab('minutes')}
        >
          <ShieldCheck size={15} /> Record Minutes &amp; Sign-Off
        </button>
        <button
          className={`chair-nav-btn ${activeTab === 'archive' ? 'active' : ''}`}
          onClick={() => { setActiveTab('archive'); fetchMeetings(); }}
        >
          <Calendar size={15} /> Meeting Archive ({meetings.length})
        </button>
      </nav>

      {/* Content Body */}
      <main className="chair-content">
        {/* Demo Data Orientation Banner */}
        {isUsingDemoData && (
          <div role="status" style={{
            background: '#fffbeb',
            border: '1px solid #f59e0b',
            borderRadius: '8px',
            padding: '10px 16px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '13px',
            color: '#92400e',
          }}>
            <AlertTriangle size={16} color="#f59e0b" />
            <span>
              <strong>Demo orientation data:</strong> No live adjudication cases were found in the database.
              The records shown below are illustrative examples only. Complete an A/B submission cycle to populate real cases.
            </span>
            <button
              onClick={() => setIsUsingDemoData(false)}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#92400e', fontWeight: 700, fontSize: '14px' }}
              aria-label="Dismiss"
            >✕</button>
          </div>
        )}

        {/* KPI Stat Cards */}
        <div className="chair-stats-grid">
          <div className="chair-stat-card" style={{ borderLeft: '4px solid #10b981' }}>
            <div className="chair-stat-label">Concordant (A = B)</div>
            <div className="chair-stat-val" style={{ color: '#047857' }}>{summary.concordant}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Ready for consent calendar</div>
          </div>
          <div className="chair-stat-card" style={{ borderLeft: '4px solid #ef4444' }}>
            <div className="chair-stat-label">Discordant (A ≠ B)</div>
            <div className="chair-stat-val" style={{ color: '#b91c1c' }}>{summary.discordant}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Requires committee discussion</div>
          </div>
          <div className="chair-stat-card" style={{ borderLeft: '4px solid #f59e0b' }}>
            <div className="chair-stat-label">3-Way Divergent (A ≠ B ≠ C)</div>
            <div className="chair-stat-val" style={{ color: '#b45309' }}>{summary.three_way_divergent}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Reviewer C independent outcome</div>
          </div>
          <div className="chair-stat-card" style={{ borderLeft: '4px solid #64748b' }}>
            <div className="chair-stat-label">Closed &amp; Archived</div>
            <div className="chair-stat-val" style={{ color: '#334155' }}>{summary.closed}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Meeting minutes e-signed</div>
          </div>
        </div>

        {/* TAB 1: Completed Adjudications & Concordance Tracker */}
        {activeTab === 'concordance' && (
          <div className="chair-table-card">
            {errorMsg && (
              <div style={{ margin: '16px 20px 0', padding: '12px 14px', color: '#991b1b', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', fontSize: '13px' }}>
                {errorMsg}
              </div>
            )}
            <div className="chair-table-header">
              <div>
                <h2>Completed Adjudications Roster</h2>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                  Live batch monitoring of primary (A) and secondary (B) reviewer submissions and Reviewer C escalations.
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                <select className="chair-input" value={releaseStudy} onChange={(e) => setReleaseStudy(e.target.value)} aria-label="Final release study">
                  <option value="PROTECT-Africa">PROTECT-Africa</option>
                  <option value="LOPE-Nigeria">LOPE-Nigeria</option>
                </select>
                <button onClick={() => downloadFinalRelease('csv')} className="chair-btn chair-btn-primary" style={{ fontSize: '12px' }} disabled={Boolean(releaseFormat)}>
                  <Download size={13} /> {releaseFormat === 'csv' ? 'Preparing…' : 'Final CSV'}
                </button>
                <button onClick={() => downloadFinalRelease('pdf')} className="chair-btn chair-btn-secondary" style={{ fontSize: '12px' }} disabled={Boolean(releaseFormat)}>
                  <FileText size={13} /> {releaseFormat === 'pdf' ? 'Preparing…' : 'Final PDF'}
                </button>
                <button onClick={fetchAdjudications} className="chair-btn chair-btn-secondary" style={{ fontSize: '12px' }}>
                  <RefreshCw size={13} className={loading ? 'spin' : ''} /> Refresh
                </button>
              </div>
            </div>

            <div className="chair-table-wrap">
              <table className="chair-table chair-decision-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '150px' }}>Patient</th>
                    <th style={{ minWidth: '85px' }}>Visit</th>
                    <th style={{ minWidth: '90px' }}>Site</th>
                    <th style={{ minWidth: '120px' }}>Study</th>
                    <th style={{ minWidth: '160px' }}>Reviewer A</th>
                    <th style={{ minWidth: '160px' }}>Reviewer B</th>
                    <th style={{ minWidth: '160px' }}>Reviewer C</th>
                    <th style={{ minWidth: '160px' }}>Concordance Status</th>
                    <th style={{ minWidth: '140px' }}>Inspect</th>
                  </tr>
                </thead>
                <tbody>
                  {adjudications.length === 0 ? (
                    <tr>
                      <td colSpan="9" style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
                        No completed adjudication cases found in current batch.
                      </td>
                    </tr>
                  ) : (
                    adjudications.map((adj, index) => {
                      const rawStatus = String(adj.concordance_status || adj.concordance || adj.status || '').toUpperCase();
                      const isLope = String(adj.study_code || '').toUpperCase().includes('LOPE');
                      const isNewPatient = index === 0 || adjudications[index - 1].subject_id !== adj.subject_id;
                      
                      const renderBadge = () => {
                        if (rawStatus.includes('MAJORITY') || rawStatus === 'RESOLVED_BY_MAJORITY') {
                          return <span className="tag-majority"><CheckCircle size={12} /> Resolved by Majority</span>;
                        }
                        if (rawStatus === 'CONCORDANT' || rawStatus === 'CONCORDANT_A_EQUALS_B' || (rawStatus.includes('CONCORDANT') && !rawStatus.includes('DISCORDANT'))) {
                          return <span className="tag-concordant"><CheckCircle size={12} /> Concordant (A=B)</span>;
                        }
                        if (rawStatus.includes('THREE_WAY') || rawStatus.includes('DIVERGENT')) {
                          return <span className="tag-divergent"><Scale size={12} /> 3-Way Divergent</span>;
                        }
                        if (rawStatus === 'RESOLVED_BY_REVIEWER_C') {
                          return <span className="tag-concordant"><ShieldCheck size={12} /> Reviewer C Final</span>;
                        }
                        if (rawStatus.includes('ESCALATED') || rawStatus.includes('REVIEWER_C') || rawStatus === 'ESCALATED_TO_C') {
                          return <span className="tag-active-c"><Users size={12} /> Reviewer C Active</span>;
                        }
                        if (rawStatus.includes('DISCORDANT')) {
                          return <span className="tag-discordant"><AlertTriangle size={12} /> Discordant (A≠B)</span>;
                        }
                        if (rawStatus.includes('CLOSED')) {
                          return <span className="tag-closed"><Lock size={12} /> Closed</span>;
                        }
                        if (rawStatus.includes('FINAL') || rawStatus.includes('CHAIR')) {
                          return <span className="tag-concordant"><ShieldCheck size={12} /> Finalized</span>;
                        }
                        return <span className="tag-closed">{rawStatus || 'Pending'}</span>;
                      };

                      const renderRev = (rev, isC = false) => {
                        if (!rev) return <span className="cell-pending">{isC ? '—' : 'Pending'}</span>;
                        const diag = typeof rev === 'string' ? rev : rev.diagnosis || '—';
                        const cert = typeof rev === 'object' ? rev.certainty : null;
                        const certLower = String(cert || '').toLowerCase();
                        const certCls = certLower.includes('definite') ? 'definite' : certLower.includes('probable') ? 'probable' : certLower.includes('possible') ? 'possible' : '';
                        return (
                          <div className="rev-cell">
                            <div className={`diag-title ${isC ? 'rev-c-diag' : ''}`}>{diag}</div>
                            {cert && <span className={`certainty-pill ${certCls}`}>{cert}</span>}
                            {typeof rev === 'object' && (
                              <div className="inline-evidence-details" style={{ marginTop: '5px', fontSize: '10px', color: '#475569', lineHeight: 1.35 }}>
                                <div className="inline-evidence-details"><strong>Criteria:</strong> {rev.meets_criteria === true ? 'Yes' : rev.meets_criteria === false ? 'No' : 'Not recorded'}</div>
                                <div><strong>Onset:</strong> {rev.onset_class || 'Not recorded'}</div>
                                <div><strong>Severity:</strong> {rev.severity || 'Not recorded'}</div>
                                <div><strong>Diagnosis date:</strong> {rev.date_of_diagnosis ? new Date(rev.date_of_diagnosis).toLocaleString() : 'Not recorded'}</div>
                                {rev.differential_diagnosis && <div><strong>Differential:</strong> {rev.differential_diagnosis}</div>}
                                {rev.rationale && <div title={rev.rationale}><strong>Rationale:</strong> {rev.rationale}</div>}
                              </div>
                            )}
                          </div>
                        );
                      };

                      return (
                        <React.Fragment key={adj.id}>
                        {isNewPatient && <tr className="next-patient-divider"><td colSpan="9"><span className="next-patient-kicker">Next patient</span><strong>{adj.subject_id}</strong><span>{adj.study_code || 'Study not recorded'}</span></td></tr>}
                        <tr className="patient-visit-row">
                          <td><span className="patient-label">Patient</span><span className="subj-id-cell">{adj.subject_id}</span></td>
                          <td><strong>{adj.visit_code || `Visit ${adj.visit_number || 1}`}</strong></td>
                          <td><span className="site-cell">{adj.site_code || 'HARARE_01'}</span></td>
                          <td><span className={`study-badge ${isLope ? 'lope' : ''}`}>{adj.study_code || 'PROTECT-Africa'}</span></td>
                          <td>{renderRev(adj.reviewer_a)}</td>
                          <td>{renderRev(adj.reviewer_b)}</td>
                          <td>{renderRev(adj.reviewer_c, true)}</td>
                          <td>{renderBadge()}</td>
                          <td>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                              <button className="chair-btn chair-btn-secondary inspect-btn" onClick={() => setInspectionItem(adj)}><Eye size={14} /> Inspect evidence</button>
                              {(rawStatus.includes('DISCORDANT') || rawStatus.includes('DIVERGENT') || rawStatus.includes('REVIEWER_C')) && (
                                <button className="chair-btn chair-btn-primary inspect-btn" onClick={() => openFinalizeCase(adj)}><CheckSquare size={14} /> Finalize case</button>
                              )}
                            </div>
                          </td>
                        </tr>
                        </React.Fragment>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {inspectionItem && (
          <EvidenceInspectorModal
            item={inspectionItem}
            allPatientVisits={groupedAdjudications[inspectionItem.subject_id] || []}
            onClose={() => setInspectionItem(null)}
            onSelectVisit={(v) => setInspectionItem(v)}
          />
        )}

        {finalizeItem && (
          <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, zIndex: 40, background: 'rgba(15, 23, 42, 0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
            <form onSubmit={handleFinalizeCase} className="chair-table-card" style={{ width: 'min(720px, 100%)', maxHeight: '90vh', overflowY: 'auto', padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', gap: '16px', marginBottom: '18px' }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: '18px' }}>Finalize {finalizeItem.subject_id}</h2>
                  <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>Visit {finalizeItem.visit_number || 1} · {finalizeItem.concordance}</div>
                </div>
                <button type="button" className="chair-btn chair-btn-secondary" onClick={() => setFinalizeItem(null)} aria-label="Close finalization form"><X size={16} /></button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="chair-form-group"><label>Final diagnosis</label><select className="chair-input" value={finalizeDraft.final_diagnosis} onChange={e => setFinalizeDraft({ ...finalizeDraft, final_diagnosis: e.target.value })}><option value="PE">PE</option><option value="Not PE">Not PE</option><option value="Severe PE">Severe PE</option><option value="Eclampsia">Eclampsia</option><option value="HELLP">HELLP</option></select></div>
                <div className="chair-form-group"><label>Adopted onset</label><select className="chair-input" value={finalizeDraft.final_onset_class} onChange={e => setFinalizeDraft({ ...finalizeDraft, final_onset_class: e.target.value })}><option value="EOPE">EOPE</option><option value="LOPE">LOPE</option><option value="POSTPARTUM">POSTPARTUM</option><option value="UNCLASSIFIABLE">UNCLASSIFIABLE</option></select></div>
                <div className="chair-form-group"><label>Final severity</label><select className="chair-input" value={finalizeDraft.final_severity} onChange={e => setFinalizeDraft({ ...finalizeDraft, final_severity: e.target.value })}><option value="With severe features">With severe features</option><option value="Without severe features">Without severe features</option><option value="Eclampsia / SAE">Eclampsia / SAE</option></select></div>
                <div className="chair-form-group"><label>Final certainty</label><select className="chair-input" value={finalizeDraft.final_certainty} onChange={e => setFinalizeDraft({ ...finalizeDraft, final_certainty: e.target.value })}><option value="Definite">Definite</option><option value="Probable">Probable</option><option value="Possible">Possible</option><option value="Not PE">Not PE</option></select></div>
              </div>
              <div className="chair-form-group"><label>Meeting title</label><input className="chair-input" value={finalizeDraft.meeting_title} onChange={e => setFinalizeDraft({ ...finalizeDraft, meeting_title: e.target.value })} required /></div>
              <div className="chair-form-group"><label>Attendees</label><input className="chair-input" value={finalizeDraft.attendees} onChange={e => setFinalizeDraft({ ...finalizeDraft, attendees: e.target.value })} required /></div>
              <div className="chair-form-group"><label>Minutes</label><textarea className="chair-textarea" rows="4" value={finalizeDraft.minutes} onChange={e => setFinalizeDraft({ ...finalizeDraft, minutes: e.target.value })} placeholder="Record the case discussion and meeting outcome." minLength="10" required /></div>
              <div className="chair-form-group"><label>Chair rationale</label><textarea className="chair-textarea" rows="4" value={finalizeDraft.chair_rationale} onChange={e => setFinalizeDraft({ ...finalizeDraft, chair_rationale: e.target.value })} placeholder="Explain why this final determination was adopted." minLength="5" required /></div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '18px' }}><button type="button" className="chair-btn chair-btn-secondary" onClick={() => setFinalizeItem(null)}>Cancel</button><button type="submit" className="chair-btn chair-btn-primary" disabled={isFinalizing}><ShieldCheck size={14} /> {isFinalizing ? 'Finalizing...' : 'Finalize and lock case'}</button></div>
            </form>
          </div>
        )}

        {/* TAB 2: Meeting Agenda Pack Generator */}
        {activeTab === 'agenda' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="chair-table-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: '16px' }}>Meeting Agenda Pack — {batchId}</h2>
                  <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                    Pack ID: <code>{agendaPack?.pack_id || 'PENDING'}</code> &nbsp;·&nbsp; Concordance Rate: <strong>{agendaPack?.concordance_rate_pct || 0}%</strong>
                  </div>
                </div>
                <button className="chair-btn chair-btn-primary" onClick={() => window.print()}>
                  <Download size={14} /> Print / Export Agenda Pack
                </button>
              </div>

              {/* Discordant Arbitration Items */}
              <div style={{ marginBottom: '24px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#991b1b', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertTriangle size={16} /> Item 1: Cases for Committee Arbitration ({agendaPack?.items_for_committee_arbitration?.length || 0})
                </h3>
                <table className="chair-table" style={{ border: '1px solid #fee2e2' }}>
                  <thead>
                    <tr style={{ background: '#fff5f5' }}>
                      <th>Subject ID</th>
                      <th>Visit</th>
                      <th>Reviewer A (Primary)</th>
                      <th>Reviewer B (Secondary)</th>
                      <th>Reviewer C (if escalated)</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(agendaPack?.items_for_committee_arbitration || []).map(item => (
                      <tr key={item.id}>
                        <td><strong>{item.subject_id}</strong></td>
                        <td>{item.visit_code || `Visit ${item.visit_number || 1}`}</td>
                        <td>{item.reviewer_a?.diagnosis} ({item.reviewer_a?.certainty})</td>
                        <td>{item.reviewer_b?.diagnosis} ({item.reviewer_b?.certainty})</td>
                        <td>{item.reviewer_c?.diagnosis || '—'}</td>
                        <td><span className="tag-discordant">{item.concordance}</span></td>
                      </tr>
                    ))}
                    {(!agendaPack?.items_for_committee_arbitration || agendaPack.items_for_committee_arbitration.length === 0) && (
                      <tr><td colSpan="6" style={{ textAlign: 'center', color: '#94a3b8' }}>No discordant cases pending.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Consent Calendar Items */}
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#166534', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <CheckCircle size={16} /> Item 2: Consent Calendar ({agendaPack?.concordant_cases_consent_calendar?.length || 0})
                </h3>
                <table className="chair-table" style={{ border: '1px solid #dcfce7' }}>
                  <thead>
                    <tr style={{ background: '#f0fdf4' }}>
                      <th>Subject ID</th>
                      <th>Visit</th>
                      <th>Consensus Outcome</th>
                      <th>Certainty</th>
                      <th>Concordance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(agendaPack?.concordant_cases_consent_calendar || []).map(item => (
                      <tr key={item.id}>
                        <td><strong>{item.subject_id}</strong></td>
                        <td>{item.visit_code || `Visit ${item.visit_number || 1}`}</td>
                        <td>{item.reviewer_a?.diagnosis}</td>
                        <td>{item.reviewer_a?.certainty}</td>
                        <td><span className="tag-concordant">A = B Concordant</span></td>
                      </tr>
                    ))}
                    {(!agendaPack?.concordant_cases_consent_calendar || agendaPack.concordant_cases_consent_calendar.length === 0) && (
                      <tr><td colSpan="5" style={{ textAlign: 'center', color: '#94a3b8' }}>No concordant cases pending.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: Record Meeting Minutes & Sign-Off */}
        {activeTab === 'minutes' && (
          <div className="chair-table-card" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '16px', marginBottom: '4px' }}>Formal Committee Meeting Minutes &amp; 21 CFR Part 11 Sign-Off</h2>
            <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '20px' }}>
              Record official minutes, verify attendee roster, and execute Chairperson electronic signature to close out the adjudication batch.
            </div>

            {signSuccess && (
              <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '16px', borderRadius: '6px', marginBottom: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#166534', fontWeight: 700, fontSize: '14px' }}>
                  <CheckCircle size={18} /> Meeting Formally Signed &amp; Closed
                </div>
                <div style={{ fontSize: '12px', color: '#166534', marginTop: '6px' }}>
                  Meeting ID: <code>{signSuccess.meeting_id}</code> &nbsp;·&nbsp; Closed Cases: <strong>{signSuccess.closed_cases_count}</strong>
                </div>
                <div style={{ fontSize: '11px', color: '#4b5563', marginTop: '4px', wordBreak: 'break-all' }}>
                  21 CFR Part 11 Digital Signature Hash: <code>{signSuccess.signature_hash}</code>
                </div>
              </div>
            )}

            <form onSubmit={handleSignOffMeeting}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div className="chair-form-group">
                  <label>Meeting Title / Session Name</label>
                  <input
                    type="text"
                    className="chair-input"
                    value={meetingTitle}
                    onChange={(e) => setMeetingTitle(e.target.value)}
                    required
                  />
                </div>
                <div className="chair-form-group">
                  <label>Adjudication Batch Reference</label>
                  <input
                    type="text"
                    className="chair-input"
                    value={batchId}
                    onChange={(e) => setBatchId(e.target.value)}
                  />
                </div>
              </div>

              <div className="chair-form-group">
                <label>Committee Attendees (comma-separated UPNs / Names)</label>
                <input
                  type="text"
                  className="chair-input"
                  value={attendees}
                  onChange={(e) => setAttendees(e.target.value)}
                  required
                />
              </div>

              <div className="chair-form-group" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <input
                  type="checkbox"
                  id="quorumCheck"
                  checked={quorumMet}
                  onChange={(e) => setQuorumMet(e.target.checked)}
                />
                <label htmlFor="quorumCheck" style={{ margin: 0, cursor: 'pointer' }}>
                  <strong>Quorum Verified:</strong> At least 3 qualified voting committee members present throughout session
                </label>
              </div>

              <div className="chair-form-group">
                <label>Official Meeting Minutes &amp; Deliberation Summary</label>
                <textarea
                  rows="6"
                  className="chair-textarea"
                  value={minutesText}
                  onChange={(e) => setMinutesText(e.target.value)}
                  required
                />
              </div>

              <div className="chair-form-group">
                <label>Select Cases Finalized &amp; Closed in this Session ({selectedCaseIds.length} selected):</label>
                <div style={{ maxHeight: '180px', overflowY: 'auto', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '10px', background: '#f8fafc' }}>
                  {meetingCases.map(adj => (
                    <label key={adj.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', cursor: 'pointer', fontSize: '12.5px' }}>
                      <input
                        type="checkbox"
                        checked={selectedCaseIds.includes(adj.subject_id)}
                        onChange={() => handleToggleCaseSelection(adj.subject_id)}
                      />
                      <span><strong>{adj.subject_id}</strong> ({adj.study_code}) — {adj.concordance}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', padding: '16px', borderRadius: '6px', marginBottom: '20px' }}>
                <div style={{ fontWeight: 700, fontSize: '13px', marginBottom: '4px' }}>
                  21 CFR Part 11 Electronic Signature Attestation
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', lineHeight: '1.5' }}>
                  By clicking <strong>"Sign &amp; Close Adjudication Batch"</strong>, I certify that I am the Chairperson of the Clinical Endpoint Adjudication Committee, that these minutes accurately reflect committee deliberations, and that all finalized cases are closed in compliance with ICH E6(R2) and the study protocol.
                </div>
              </div>

              <button
                type="submit"
                className="chair-btn chair-btn-primary"
                style={{ width: '100%', padding: '12px', justifyContent: 'center', fontSize: '14px' }}
                disabled={isSigning}
              >
                <Lock size={16} /> {isSigning ? 'Computing Cryptographic Sign-Off...' : 'Sign & Close Adjudication Batch'}
              </button>
            </form>
          </div>
        )}

        {/* TAB 4: Meeting Archive */}
        {activeTab === 'archive' && (
          <div className="chair-table-card" style={{ padding: '20px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '20px' }}>
              <div>
                <div className="chair-table-header" style={{ marginBottom: '12px' }}>
                  <h2>Committee Meeting Scheduling</h2>
                </div>
                <form onSubmit={createMeeting} style={{ display: 'grid', gap: '12px' }}>
                  <div className="chair-form-group">
                    <label>Meeting Title</label>
                    <input className="chair-input" value={newMeetingTitle} onChange={(e) => setNewMeetingTitle(e.target.value)} required />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div className="chair-form-group">
                      <label>Scheduled Date &amp; Time</label>
                      <input className="chair-input" type="datetime-local" value={newMeetingDateTime} onChange={(e) => setNewMeetingDateTime(e.target.value)} required />
                    </div>
                    <div className="chair-form-group">
                      <label>Batch</label>
                      <input className="chair-input" value={newMeetingBatchId} onChange={(e) => setNewMeetingBatchId(e.target.value)} />
                    </div>
                  </div>
                  <div className="chair-form-group">
                    <label>Attendees</label>
                    <input className="chair-input" value={newMeetingAttendees} onChange={(e) => setNewMeetingAttendees(e.target.value)} />
                  </div>
                  <div className="chair-form-group">
                    <label>Agenda / Meeting Notes</label>
                    <textarea className="chair-textarea" rows="4" value={newMeetingAgenda} onChange={(e) => setNewMeetingAgenda(e.target.value)} />
                  </div>
                  <button type="submit" className="chair-btn chair-btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
                    <Calendar size={14} /> Save Meeting
                  </button>
                </form>
              </div>

              <div>
                <div className="chair-table-header" style={{ marginBottom: '12px' }}>
                  <h2>Scheduled Meetings</h2>
                </div>
                <div style={{ display: 'grid', gap: '10px' }}>
                  {meetings.length === 0 ? (
                    <div style={{ padding: '20px', background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: '8px', color: '#64748b' }}>No meetings scheduled yet.</div>
                  ) : (
                    meetings.map(m => (
                      <div key={m.id} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start' }}>
                          <div>
                            <div style={{ fontWeight: 700 }}>{m.title}</div>
                            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
                              {m.scheduled_at ? new Date(m.scheduled_at).toLocaleString() : 'No date'} · {m.status}
                            </div>
                          </div>
                          {m.status !== 'CANCELLED' && (
                            <button onClick={() => cancelMeeting(m.id)} className="chair-btn chair-btn-secondary" style={{ fontSize: '11px', padding: '6px 10px' }}>
                              <X size={12} /> Cancel
                            </button>
                          )}
                        </div>
                        <div style={{ fontSize: '11px', color: '#475569', marginTop: '8px' }}>
                          Batch: {m.batch_id || '—'} · Cases: {m.case_count || 0}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="chair-table-header" style={{ marginTop: '24px' }}>
              <h2>Archived Committee Meetings &amp; Signed Minutes</h2>
            </div>
            <table className="chair-table" style={{ marginTop: '12px' }}>
              <thead>
                <tr>
                  <th>Session Title</th>
                  <th>Batch</th>
                  <th>Chairperson</th>
                  <th>Signed Date</th>
                  <th>Cases Closed</th>
                  <th>Part 11 Hash</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {meetings.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
                      No signed meeting records archived yet.
                    </td>
                  </tr>
                ) : (
                  meetings.map(m => (
                    <tr key={m.id}>
                      <td><strong>{m.title}</strong></td>
                      <td><code>{m.batch_id || '—'}</code></td>
                      <td>{m.chair_name} ({m.chair_upn})</td>
                      <td>{m.signed_at ? new Date(m.signed_at).toLocaleString() : '—'}</td>
                      <td><span className="tag-concordant">{m.case_count} cases</span></td>
                      <td><code style={{ fontSize: '11px' }}>{m.signature_hash?.slice(0, 16)}...</code></td>
                      <td><span className="tag-closed">{m.status}</span></td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
