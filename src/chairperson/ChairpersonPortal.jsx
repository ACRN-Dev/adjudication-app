import React, { useState, useEffect } from 'react';
import {
  Users, FileText, CheckCircle, AlertTriangle, Scale, Lock, LogOut,
  Calendar, Download, RefreshCw, Send, CheckSquare, ShieldCheck, ChevronRight
} from 'lucide-react';
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
        setSelectedCaseIds(items.map(i => i.subject_id));
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
          <img src="/acrn-logo.png" alt="ACRN" style={{ height: '32px', filter: 'brightness(0) invert(1)' }} />
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
              <button onClick={fetchAdjudications} className="chair-btn chair-btn-secondary" style={{ fontSize: '12px' }}>
                <RefreshCw size={13} className={loading ? 'spin' : ''} /> Refresh
              </button>
            </div>

            <div className="chair-table-wrap">
              <table className="chair-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '110px' }}>Subject ID</th>
                    <th style={{ minWidth: '90px' }}>Site</th>
                    <th style={{ minWidth: '120px' }}>Study</th>
                    <th style={{ minWidth: '160px' }}>Reviewer A</th>
                    <th style={{ minWidth: '160px' }}>Reviewer B</th>
                    <th style={{ minWidth: '160px' }}>Reviewer C</th>
                    <th style={{ minWidth: '160px' }}>Concordance Status</th>
                    <th style={{ minWidth: '140px' }}>Final Decision</th>
                  </tr>
                </thead>
                <tbody>
                  {adjudications.length === 0 ? (
                    <tr>
                      <td colSpan="8" style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
                        No completed adjudication cases found in current batch.
                      </td>
                    </tr>
                  ) : (
                    adjudications.map((adj) => {
                      const rawStatus = String(adj.concordance_status || adj.concordance || adj.status || '').toUpperCase();
                      const isLope = String(adj.study_code || '').toUpperCase().includes('LOPE');
                      
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
                          </div>
                        );
                      };

                      return (
                        <tr key={adj.id}>
                          <td><span className="subj-id-cell">{adj.subject_id}</span></td>
                          <td><span className="site-cell">{adj.site_code || 'HARARE_01'}</span></td>
                          <td><span className={`study-badge ${isLope ? 'lope' : ''}`}>{adj.study_code || 'PROTECT-Africa'}</span></td>
                          <td>{renderRev(adj.reviewer_a)}</td>
                          <td>{renderRev(adj.reviewer_b)}</td>
                          <td>{renderRev(adj.reviewer_c, true)}</td>
                          <td>{renderBadge()}</td>
                          <td>
                            {adj.final_outcome ? (
                              <div className="rev-cell">
                                <div className="diag-title">{adj.final_outcome.diagnosis || 'Locked'}</div>
                                <div style={{ fontSize: '10.5px', color: '#64748b' }}>Adopted: {adj.final_outcome.adopted_reviewer}</div>
                              </div>
                            ) : <span className="cell-pending">Pending arbitration</span>}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
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
                        <td>{item.reviewer_a?.diagnosis} ({item.reviewer_a?.certainty})</td>
                        <td>{item.reviewer_b?.diagnosis} ({item.reviewer_b?.certainty})</td>
                        <td>{item.reviewer_c?.diagnosis || '—'}</td>
                        <td><span className="tag-discordant">{item.concordance}</span></td>
                      </tr>
                    ))}
                    {(!agendaPack?.items_for_committee_arbitration || agendaPack.items_for_committee_arbitration.length === 0) && (
                      <tr><td colSpan="5" style={{ textAlign: 'center', color: '#94a3b8' }}>No discordant cases pending.</td></tr>
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
                      <th>Consensus Outcome</th>
                      <th>Certainty</th>
                      <th>Concordance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(agendaPack?.concordant_cases_consent_calendar || []).map(item => (
                      <tr key={item.id}>
                        <td><strong>{item.subject_id}</strong></td>
                        <td>{item.reviewer_a?.diagnosis}</td>
                        <td>{item.reviewer_a?.certainty}</td>
                        <td><span className="tag-concordant">A = B Concordant</span></td>
                      </tr>
                    ))}
                    {(!agendaPack?.concordant_cases_consent_calendar || agendaPack.concordant_cases_consent_calendar.length === 0) && (
                      <tr><td colSpan="4" style={{ textAlign: 'center', color: '#94a3b8' }}>No concordant cases pending.</td></tr>
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
                  {adjudications.map(adj => (
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
          <div className="chair-table-card">
            <div className="chair-table-header">
              <h2>Archived Committee Meetings &amp; Signed Minutes</h2>
            </div>
            <table className="chair-table">
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
