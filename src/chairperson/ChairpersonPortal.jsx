import React, { useState, useEffect } from 'react';
import {
  Users, FileText, CheckCircle, AlertTriangle, Scale, Lock, LogOut,
  Calendar, Download, RefreshCw, Send, CheckSquare, ShieldCheck, ChevronRight, Eye, X
} from 'lucide-react';
import EvidenceInspectorModal from './EvidenceInspectorModal';
import '../admin/admin.css';
import './chairperson.css';

export default function ChairpersonPortal({ user, onLogout, isEmbedded, readOnly = false }) {
  const [activeTab, setActiveTab] = useState('concordance');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [adjudications, setAdjudications] = useState([]);
  const [summary, setSummary] = useState({ concordant: 0, discordant: 0, three_way_divergent: 0, closed: 0 });
  const [agendaPack, setAgendaPack] = useState(null);
  const [meetings, setMeetings] = useState([]);
  const [isUsingDemoData, setIsUsingDemoData] = useState(false);
  const [navCollapsed, setNavCollapsed] = useState(false);

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

  const NAV_ITEMS = [
    { key: 'concordance', label: 'Concordance Tracker', icon: <Scale size={15} /> },
    { key: 'agenda',      label: 'Meeting Agenda Pack', icon: <FileText size={15} /> },
    { key: 'minutes',     label: 'Record Minutes & Sign-Off', icon: <ShieldCheck size={15} /> },
    { key: 'archive',     label: `Meeting Archive (${meetings.length})`, icon: <Calendar size={15} /> },
  ];

  const handleTabChange = (key) => {
    setActiveTab(key);
    if (key === 'agenda') fetchAgenda();
    if (key === 'archive') fetchMeetings();
  };

  const TAB_DESCS = {
    concordance: 'Live batch monitoring of primary (A) and secondary (B) reviewer submissions and Reviewer C escalations.',
    agenda: 'Auto-generated committee agenda pack summarising all outstanding discordant and pending cases.',
    minutes: 'Record official committee deliberations and apply a 21 CFR Part 11 electronic signature to close the batch.',
    archive: 'Scheduled upcoming meetings and signed, archived session minutes.',
  };

  const content = (
    <>
      {/* Demo orientation banner */}
      {isUsingDemoData && (
        <div role="status" className="a-notice warn" style={{ marginBottom: '12px' }}>
          <AlertTriangle size={15} />
          <div>
            <strong>Demo orientation data</strong>
            <span>No live adjudication cases were found. Records shown below are illustrative examples only.</span>
          </div>
          <button style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#92400e', fontWeight: 700 }} onClick={() => setIsUsingDemoData(false)} aria-label="Dismiss">âœ•</button>
        </div>
      )}

      {/* KPI metrics strip */}
      <div className="a-metrics" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '14px' }}>
        <div style={{ borderLeft: '3px solid #10b981' }}>
          <strong style={{ color: '#047857' }}>{summary.concordant}</strong>
          <span>Concordant (A = B)</span>
        </div>
        <div style={{ borderLeft: '3px solid #ef4444' }}>
          <strong style={{ color: '#b91c1c' }}>{summary.discordant}</strong>
          <span>Discordant (A ≠ B)</span>
        </div>
        <div style={{ borderLeft: '3px solid #f59e0b' }}>
          <strong style={{ color: '#b45309' }}>{summary.three_way_divergent}</strong>
          <span>3-Way Divergent</span>
        </div>
        <div style={{ borderLeft: '3px solid #64748b' }}>
          <strong style={{ color: '#334155' }}>{summary.closed}</strong>
          <span>Closed &amp; Archived</span>
        </div>
      </div>

      {/* Page heading for active tab */}
      <div className="a-page-head">
        <div>
          <h1>{NAV_ITEMS.find(n => n.key === activeTab)?.label}</h1>
          <p>{TAB_DESCS[activeTab]}</p>
        </div>
        {activeTab === 'concordance' && !readOnly && (
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <select className="a-toolbar" style={{ padding: '0 8px', height: '30px', fontSize: '9.5px' }} value={releaseStudy} onChange={e => setReleaseStudy(e.target.value)}>
              <option value="PROTECT-Africa">PROTECT-Africa</option>
              <option value="LOPE-Nigeria">LOPE-Nigeria</option>
            </select>
            <button className="a-primary" onClick={() => downloadFinalRelease('csv')} disabled={Boolean(releaseFormat)}>
              <Download size={13} /> {releaseFormat === 'csv' ? 'Preparing…' : 'Final CSV'}
            </button>
            <button className="a-secondary" style={{ padding: '6px 9px', display:'inline-flex', gap:'5px', alignItems:'center', fontSize:'9.5px', cursor:'pointer' }} onClick={() => downloadFinalRelease('pdf')} disabled={Boolean(releaseFormat)}>
              <FileText size={13} /> {releaseFormat === 'pdf' ? 'Preparing…' : 'Final PDF'}
            </button>
          </div>
        )}
        {activeTab === 'concordance' && (
          <button className="a-primary" onClick={fetchAdjudications} disabled={loading}>
            <RefreshCw size={13} /> {loading ? 'Loading…' : 'Refresh'}
          </button>
        )}
      </div>

      {errorMsg && (
        <div className="a-notice" style={{ borderLeftColor: '#b91c1c', background: '#fef2f2', marginBottom: '10px' }}>
          <AlertTriangle size={14} /><span style={{ color: '#991b1b' }}>{errorMsg}</span>
        </div>
      )}

      {/* ── TAB 1: Concordance tracker ── */}
      {activeTab === 'concordance' && (
        <div className="a-table-wrap">
          <table className="a-table">
            <caption>Completed Adjudications Roster — {Object.keys(groupedAdjudications).length} subject{Object.keys(groupedAdjudications).length !== 1 ? 's' : ''}</caption>
            <thead>
              <tr>
                <th>Subject ID</th>
                <th>Visit</th>
                <th>Site / Study</th>
                <th>Reviewer A</th>
                <th>Reviewer B</th>
                <th>Reviewer C</th>
                <th>Concordance</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(groupedAdjudications).length === 0 ? (
                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>No adjudication records yet.</td></tr>
              ) : (
                Object.entries(groupedAdjudications).map(([subjectId, items]) =>
                  items.map((adj, adjIndex) => {
                    const rawStatus = String(adj.concordance || adj.status || '').toUpperCase();
                    const renderRev = (reviewer, isC = false) => reviewer ? (
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '9px' }}>{reviewer.diagnosis || 'Pending'}</div>
                        {reviewer.onset_class && <div style={{ fontSize: '8px', color: '#64748b' }}>{reviewer.onset_class}</div>}
                        {isC && <span className="a-badge warn" style={{ fontSize: '7px' }}>Reviewer C</span>}
                      </div>
                    ) : <span style={{ color: '#94a3b8', fontSize: '9px' }}>—</span>;
                    const renderBadge = () => {
                      if (rawStatus.includes('CONCORDANT')) return <span className="a-badge ok">Concordant</span>;
                      if (rawStatus.includes('THREE_WAY') || rawStatus.includes('DIVERGENT')) return <span className="a-badge" style={{ background: '#fef3c7', color: '#92400e' }}>3-Way Divergent</span>;
                      if (rawStatus.includes('DISCORDANT')) return <span className="a-badge bad">Discordant</span>;
                      if (rawStatus.includes('CLOSED')) return <span className="a-badge" style={{ background: '#e2e8f0', color: '#334155' }}>Closed</span>;
                      return <span className="a-badge">{adj.concordance || 'Pending'}</span>;
                    };
                    return (
                      <tr key={`${subjectId}-${adjIndex}`}>
                        <td><strong>{adjIndex === 0 ? subjectId : ''}</strong></td>
                        <td>Visit {adj.visit_number || '—'}</td>
                        <td><span style={{ fontSize: '9px' }}>{adj.site_code || 'HARARE_01'}<br/><span style={{ color: '#64748b' }}>{adj.study_code || 'PROTECT-Africa'}</span></span></td>
                        <td>{renderRev(adj.reviewer_a)}</td>
                        <td>{renderRev(adj.reviewer_b)}</td>
                        <td>{renderRev(adj.reviewer_c, true)}</td>
                        <td>{renderBadge()}</td>
                        <td>
                          <div className="a-actions">
                            <button onClick={() => setInspectionItem(adj)}>Inspect</button>
                            {!readOnly && (rawStatus.includes('DISCORDANT') || rawStatus.includes('DIVERGENT') || rawStatus.includes('REVIEWER_C')) && (
                              <button onClick={() => openFinalizeCase(adj)} style={{ color: '#b45309' }}>Finalize</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── TAB 2: Agenda Pack ── */}
      {activeTab === 'agenda' && (
        <div className="a-panel">
          {!agendaPack ? (
            <div className="a-empty"><FileText size={32} color="#cbd5e1" /><p style={{ color: '#94a3b8' }}>No agenda pack available. Discordant cases will appear here once A/B submissions are recorded.</p></div>
          ) : (
            <>
              <dl style={{ display: 'grid', gap: '6px', marginBottom: '12px' }}>
                {[
                  ['Batch', agendaPack.batch_id],
                  ['Total Cases', agendaPack.total_cases],
                  ['Discordant', agendaPack.discordant_count],
                  ['Concordant', agendaPack.concordant_count],
                  ['Three-Way Divergent', agendaPack.three_way_divergent_count],
                ].map(([label, value]) => (
                  <div key={label} className="a-panel" style={{ padding: '6px 10px', marginBottom: 0 }}>
                    <dt style={{ fontSize: '9px', color: '#64748b', textTransform: 'uppercase' }}>{label}</dt>
                    <dd style={{ fontWeight: 700, marginLeft: 0 }}>{value ?? '—'}</dd>
                  </div>
                ))}
              </dl>
              {(agendaPack.items || []).map((item, i) => (
                <div key={i} className="a-panel" style={{ marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <strong style={{ fontSize: '11px' }}>{item.subject_id} — Visit {item.visit_number}</strong>
                    <span className={`a-badge ${item.concordance?.includes('DISCORDANT') ? 'bad' : item.concordance?.includes('THREE_WAY') ? 'warn' : 'ok'}`}>{item.concordance}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '9.5px' }}>
                    <div><strong>Reviewer A:</strong> {item.reviewer_a?.diagnosis || '—'}</div>
                    <div><strong>Reviewer B:</strong> {item.reviewer_b?.diagnosis || '—'}</div>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* ── TAB 3: Record Minutes & Sign-Off ── */}
      {activeTab === 'minutes' && (
        <div className="a-panel">
          {signSuccess && (
            <div className="a-notice" style={{ borderLeftColor: '#15803d', background: '#f0fdf4', marginBottom: '12px' }}>
              <CheckCircle size={14} color="#15803d" />
              <div>
                <strong>Batch signed and closed successfully</strong>
                <span>Batch: {signSuccess.batch_id} · Cases closed: {signSuccess.cases_closed} · Hash: {signSuccess.signature_hash?.slice(0, 16)}…</span>
              </div>
            </div>
          )}
          {readOnly ? (
            <div className="a-notice" style={{ marginBottom: 0 }}>
              <ShieldCheck size={14} />
              <span>Sign-off is restricted to the Chairperson role. You are viewing this tab in read-only mode.</span>
            </div>
          ) : (
            <form onSubmit={handleSignOffMeeting} style={{ display: 'grid', gap: '12px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <label style={{ display: 'grid', gap: '4px', fontSize: '9.5px' }}>
                  Meeting Title / Session Name
                  <input className="a-toolbar" style={{ height: '30px', padding: '0 8px' }} type="text" value={meetingTitle} onChange={e => setMeetingTitle(e.target.value)} required />
                </label>
                <label style={{ display: 'grid', gap: '4px', fontSize: '9.5px' }}>
                  Adjudication Batch Reference
                  <input className="a-toolbar" style={{ height: '30px', padding: '0 8px' }} type="text" value={batchId} onChange={e => setBatchId(e.target.value)} />
                </label>
              </div>
              <label style={{ display: 'grid', gap: '4px', fontSize: '9.5px' }}>
                Committee Attendees (comma-separated UPNs)
                <input className="a-toolbar" style={{ height: '30px', padding: '0 8px' }} type="text" value={attendees} onChange={e => setAttendees(e.target.value)} required />
              </label>
              <label style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '9.5px', cursor: 'pointer' }}>
                <input type="checkbox" checked={quorumMet} onChange={e => setQuorumMet(e.target.checked)} />
                <strong>Quorum Verified:</strong> At least 3 qualified voting committee members present throughout session
              </label>
              <label style={{ display: 'grid', gap: '4px', fontSize: '9.5px' }}>
                Official Meeting Minutes &amp; Deliberation Summary
                <textarea className="a-toolbar" style={{ height: '120px', padding: '8px', resize: 'vertical', fontFamily: 'inherit' }} rows="6" value={minutesText} onChange={e => setMinutesText(e.target.value)} required />
              </label>
              <div style={{ fontSize: '9.5px' }}>
                <strong>Select Cases Finalized &amp; Closed in this Session ({selectedCaseIds.length} selected):</strong>
                <div style={{ maxHeight: '160px', overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: '4px', padding: '8px', background: '#f8fafc', marginTop: '4px' }}>
                  {meetingCases.map(adj => (
                    <label key={adj.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '3px 0', cursor: 'pointer' }}>
                      <input type="checkbox" checked={selectedCaseIds.includes(adj.subject_id)} onChange={() => handleToggleCaseSelection(adj.subject_id)} />
                      <span><strong>{adj.subject_id}</strong> ({adj.study_code}) — {adj.concordance}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="a-notice" style={{ borderLeftColor: '#1d4ed8', background: '#eff6ff' }}>
                <Lock size={13} />
                <span style={{ fontSize: '9.5px' }}>By clicking <strong>"Sign &amp; Close Adjudication Batch"</strong>, you certify as Chairperson that these minutes accurately reflect committee deliberations and all finalised cases are closed in compliance with ICH E6(R2) and the study protocol.</span>
              </div>
              <button type="submit" className="a-primary" style={{ width: '100%', justifyContent: 'center', padding: '10px', fontSize: '12px' }} disabled={isSigning}>
                <Lock size={15} /> {isSigning ? 'Computing Cryptographic Sign-Off…' : 'Sign & Close Adjudication Batch'}
              </button>
            </form>
          )}
        </div>
      )}

      {/* ── TAB 4: Meeting Archive ── */}
      {activeTab === 'archive' && (
        <>
          <div className="a-grid2">
            <div className="a-panel">
              <h2>Schedule New Meeting</h2>
              {!readOnly ? (
                <form onSubmit={createMeeting} style={{ display: 'grid', gap: '10px' }}>
                  <label style={{ display: 'grid', gap: '3px', fontSize: '9.5px' }}>
                    Meeting Title
                    <input className="a-toolbar" style={{ height: '30px', padding: '0 8px' }} value={newMeetingTitle} onChange={e => setNewMeetingTitle(e.target.value)} required />
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <label style={{ display: 'grid', gap: '3px', fontSize: '9.5px' }}>
                      Scheduled Date &amp; Time
                      <input className="a-toolbar" style={{ height: '30px', padding: '0 8px' }} type="datetime-local" value={newMeetingDateTime} onChange={e => setNewMeetingDateTime(e.target.value)} required />
                    </label>
                    <label style={{ display: 'grid', gap: '3px', fontSize: '9.5px' }}>
                      Batch
                      <input className="a-toolbar" style={{ height: '30px', padding: '0 8px' }} value={newMeetingBatchId} onChange={e => setNewMeetingBatchId(e.target.value)} />
                    </label>
                  </div>
                  <label style={{ display: 'grid', gap: '3px', fontSize: '9.5px' }}>
                    Attendees
                    <input className="a-toolbar" style={{ height: '30px', padding: '0 8px' }} value={newMeetingAttendees} onChange={e => setNewMeetingAttendees(e.target.value)} />
                  </label>
                  <label style={{ display: 'grid', gap: '3px', fontSize: '9.5px' }}>
                    Agenda / Meeting Notes
                    <textarea className="a-toolbar" style={{ height: '80px', padding: '8px', resize: 'vertical', fontFamily: 'inherit' }} rows="4" value={newMeetingAgenda} onChange={e => setNewMeetingAgenda(e.target.value)} />
                  </label>
                  <button type="submit" className="a-primary" style={{ width: '100%', justifyContent: 'center' }}>
                    <Calendar size={13} /> Save Meeting
                  </button>
                </form>
              ) : (
                <div className="a-notice" style={{ marginTop: '8px' }}>
                  <ShieldCheck size={13} />
                  <span>Meeting scheduling is restricted to the Chairperson role.</span>
                </div>
              )}
            </div>

            <div className="a-panel">
              <h2>Upcoming Meetings</h2>
              {meetings.length === 0 ? (
                <div className="a-empty"><Calendar size={28} color="#cbd5e1" /><p style={{ color: '#94a3b8' }}>No meetings scheduled yet.</p></div>
              ) : (
                <div style={{ display: 'grid', gap: '8px' }}>
                  {meetings.map(m => (
                    <div key={m.id} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '4px', padding: '10px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                        <div>
                          <div style={{ fontWeight: 700, fontSize: '10px' }}>{m.title}</div>
                          <div style={{ fontSize: '9px', color: '#64748b', marginTop: '2px' }}>
                            {m.scheduled_at ? new Date(m.scheduled_at).toLocaleString() : 'No date'} · {m.status}
                          </div>
                        </div>
                        {!readOnly && m.status !== 'CANCELLED' && (
                          <button onClick={() => cancelMeeting(m.id)} className="a-secondary" style={{ padding: '4px 8px', fontSize: '9px', cursor: 'pointer', display: 'flex', gap: '4px', alignItems: 'center' }}>
                            <X size={11} /> Cancel
                          </button>
                        )}
                      </div>
                      <div style={{ fontSize: '9px', color: '#475569', marginTop: '6px' }}>Batch: {m.batch_id || '—'} · Cases: {m.case_count || 0}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <h2 style={{ margin: '18px 0 8px', fontSize: '11px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Archived Committee Meetings &amp; Signed Minutes</h2>
          <div className="a-table-wrap">
            <table className="a-table">
              <caption>Signed session archive</caption>
              <thead>
                <tr>
                  <th>Session Title</th><th>Batch</th><th>Chairperson</th>
                  <th>Signed Date</th><th>Cases Closed</th><th>Part 11 Hash</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {meetings.length === 0 ? (
                  <tr><td colSpan="7" style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>No signed meeting records archived yet.</td></tr>
                ) : meetings.map(m => (
                  <tr key={m.id}>
                    <td><strong>{m.title}</strong></td>
                    <td><code>{m.batch_id || '—'}</code></td>
                    <td>{m.chair_name} ({m.chair_upn})</td>
                    <td>{m.signed_at ? new Date(m.signed_at).toLocaleString() : '—'}</td>
                    <td><span className="a-badge ok">{m.case_count} cases</span></td>
                    <td><code style={{ fontSize: '9px' }}>{m.signature_hash?.slice(0, 16)}…</code></td>
                    <td><span className="a-badge">{m.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );

  // ── Finalize Case Modal (inline panel overlay) ──────────────────
  const finalizeModal = finalizeItem && (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '16px' }}>
      <div style={{ background: '#fff', borderRadius: '4px', width: '100%', maxWidth: '680px', boxShadow: '0 10px 30px rgba(0,0,0,0.25)', border: '1px solid #d8dee7', overflow: 'hidden', fontFamily: 'Poppins,Arial,sans-serif' }}>
        <div style={{ background: '#162035', color: '#fff', padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', fontWeight: 700 }}>
          <span>Finalize Case — {finalizeItem.subject_id}</span>
          <button style={{ background: 'none', border: 0, color: '#cbd5e1', cursor: 'pointer', display: 'flex' }} onClick={() => setFinalizeItem(null)} aria-label="Close"><X size={16} /></button>
        </div>
        <form onSubmit={handleFinalizeCase} style={{ padding: '16px', display: 'grid', gap: '12px', maxHeight: '70vh', overflowY: 'auto' }}>
          {[
            { label: 'Meeting Title', field: 'meeting_title', type: 'text' },
            { label: 'Chair Rationale', field: 'chair_rationale', type: 'text' },
            { label: 'Final Diagnosis', field: 'final_diagnosis', type: 'select', options: ['PE', 'GH', 'cPE', 'Eclampsia', 'HELLP', 'Normal', 'Other'] },
            { label: 'Onset Class', field: 'final_onset_class', type: 'select', options: ['EOPE', 'LOPE', 'Not Applicable'] },
            { label: 'Severity', field: 'final_severity', type: 'select', options: ['With severe features', 'Without severe features', 'Not Applicable'] },
            { label: 'Certainty', field: 'final_certainty', type: 'select', options: ['Definite', 'Probable', 'Possible', 'Unlikely'] }
          ].map(({ label, field, type, options }) => (
            <label key={field} style={{ display: 'grid', gap: '3px', fontSize: '9.5px' }}>
              {label}
              {type === 'select' ? (
                <select className="a-toolbar" style={{ height: '30px', padding: '0 8px' }} value={finalizeDraft[field] || ''} onChange={e => setFinalizeDraft(p => ({ ...p, [field]: e.target.value }))} required>
                  <option value="" disabled>Select {label}</option>
                  {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                </select>
              ) : (
                <input className="a-toolbar" style={{ height: '30px', padding: '0 8px' }} type={type} value={finalizeDraft[field] || ''} onChange={e => setFinalizeDraft(p => ({ ...p, [field]: e.target.value }))} required={['meeting_title','chair_rationale'].includes(field)} />
              )}
            </label>
          ))}
          <label style={{ display: 'grid', gap: '3px', fontSize: '9.5px' }}>
            Official Minutes
            <textarea className="a-toolbar" style={{ height: '90px', padding: '8px', resize: 'vertical', fontFamily: 'inherit' }} rows="4" value={finalizeDraft.minutes || ''} onChange={e => setFinalizeDraft(p => ({ ...p, minutes: e.target.value }))} required />
          </label>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', paddingTop: '4px' }}>
            <button type="button" style={{ border: '1px solid #cbd5e1', background: '#fff', padding: '6px 12px', fontSize: '9.5px', cursor: 'pointer' }} onClick={() => setFinalizeItem(null)}>Cancel</button>
            <button type="submit" className="a-primary" disabled={isFinalizing}>
              <CheckSquare size={13} /> {isFinalizing ? 'Finalizing…' : 'Confirm & Finalize'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  if (isEmbedded) return <>{content}{finalizeModal}{inspectionItem && <EvidenceInspectorModal item={inspectionItem} onClose={() => setInspectionItem(null)} />}</>;

  return (
    <div className="admin-app">
      {finalizeModal}
      {inspectionItem && <EvidenceInspectorModal item={inspectionItem} onClose={() => setInspectionItem(null)} />}

      {/* ── Header ── */}
      <header className="a-header">
        <div className="a-brand">
          <span><img src="/acrn-logo.png" alt="Africa Clinical Research Network" /></span>
          <div>
            <strong>ACRN Adjudication Platform</strong>
            <small>Chairperson Consensus Portal</small>
          </div>
        </div>
        <div className="a-boundary">
          <Scale size={13} /> Committee Chairperson Role
        </div>
        <div className="a-user">
          <div>
            <strong>{user?.name || user?.display_name || 'Chairperson'}</strong>
            <small>{user?.email || user?.role}</small>
          </div>
          <button onClick={onLogout} aria-label="Sign out"><LogOut size={16} /></button>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="a-body">
        {/* Sidebar nav */}
        <aside className={`a-nav ${navCollapsed ? 'collapsed' : ''}`}>
          <section>
            <h2>CHAIRPERSON</h2>
            {NAV_ITEMS.map(item => (
              <button
                key={item.key}
                className={activeTab === item.key ? 'active' : ''}
                onClick={() => handleTabChange(item.key)}
                style={{ padding: '8px 12px', marginBottom: '6px', fontSize: '10px' }}
              >
                {item.icon}<span>{item.label}</span>
              </button>
            ))}
          </section>
          <button className="a-collapse" onClick={() => setNavCollapsed(!navCollapsed)} style={{ marginTop: 'auto' }}>
            {navCollapsed ? <ChevronRight size={13} /> : <><ChevronRight size={13} style={{ transform: 'rotate(180deg)' }} /> <span>Collapse</span></>}
          </button>
          <div className="a-env">
            <Lock size={13} />
            <span>CHAIRPERSON<br /><small>21 CFR Part 11</small></span>
          </div>
        </aside>

        {/* Main content */}
        <main className="a-main">
          <div className="a-crumb">
            <span>Chairperson</span>
            <ChevronRight size={12} />
            <span>{NAV_ITEMS.find(n => n.key === activeTab)?.label}</span>
          </div>
          {content}
        </main>
      </div>
    </div>
  );
}

