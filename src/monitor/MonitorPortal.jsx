import React, { useEffect, useState } from 'react';
import * as I from 'lucide-react';
import '../admin/admin.css';
import './monitor.css';
import {
  listBatches,
  listPatients,
  getPatient,
  uploadRealtime,
  uploadRealtimeBulk,
  approvePatient,
  assignPatient,
  listAdjudicators,
  listReferenceRanges,
  upsertReferenceRange,
  deactivateReferenceRange
} from '../services/realtimeApi';

const nav = [
  ['/monitor', 'Dashboard', 'LayoutDashboard'],
  ['/monitor/imports', 'RealTime Imports', 'Upload'],
  ['/monitor/patients', 'Patient Database', 'Database'],
  ['/monitor/reconstruction', 'Visit Reconstruction QC', 'GitCompare'],
  ['/monitor/longitudinal', 'Longitudinal Review', 'Activity'],
  ['/monitor/assignments', 'Assignments', 'UsersRound'],
  ['/monitor/reference-ranges', 'Lab Reference Ranges', 'SlidersHorizontal'],
  ['/monitor/queries', 'Queries', 'MessagesSquare'],
  ['/monitor/audit', 'Audit History', 'ScrollText']
];

const date = (x) => (x ? new Date(x).toLocaleDateString() : '—');

function Table({ cols, rows, onOpen }) {
  return (
    <div className="a-table-wrap">
      <table className="a-table">
        <thead>
          <tr>
            {cols.map((x) => (
              <th key={x}>{x}</th>
            ))}
            {onOpen && <th>Action</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id || i}>
              {r.cells.map((v, j) => (
                <td key={j}>{v ?? '—'}</td>
              ))}
              {onOpen && (
                <td>
                  <button className="a-link" onClick={() => onOpen(r)}>
                    Open
                  </button>
                </td>
              )}
            </tr>
          ))}
          {!rows.length && (
            <tr>
              <td colSpan={cols.length + (onOpen ? 1 : 0)} style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
                No records. Import a RealTime batch to create the patient database.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function Page({ title, desc, children }) {
  return (
    <>
      <div className="a-page-head">
        <div>
          <h1>{title}</h1>
          <p>{desc}</p>
        </div>
      </div>
      {children}
    </>
  );
}

function ProgressBar({ pct, tone = 'info' }) {
  const color = tone === 'error' ? '#dc2626' : tone === 'success' ? '#16a34a' : '#F07E26';
  return (
    <div style={{ background: '#e2e8f0', borderRadius: '999px', height: '8px', width: '100%', overflow: 'hidden' }}>
      <div style={{ width: `${Math.max(0, Math.min(100, pct || 0))}%`, height: '100%', background: color, transition: 'width 0.2s ease' }} />
    </div>
  );
}

function Imports({ user, onNavigate }) {
  const [batches, setBatches] = useState([]);
  const [msg, setMsg] = useState('');
  const [roster, setRoster] = useState([]);
  const [msgType, setMsgType] = useState('info');
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  // Per-file upload progress, keyed by a synthetic id, for single + bulk uploads.
  const [uploads, setUploads] = useState([]);

  const load = () =>
    listBatches(user)
      .then(setBatches)
      .catch((e) => {
        setMsg(e.message);
        setMsgType('error');
      });

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!batches.some((b) => !['MONITOR_QC_REQUIRED', 'FAILED', 'CANCELLED'].includes(b.status))) return;
    const t = setInterval(() => {
      load();
    }, 1000);
    return () => clearInterval(t);
  }, [batches]);

  const handleFiles = async (fileList) => {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    const invalid = files.filter((f) => !f.name.toLowerCase().endsWith('.csv'));
    if (invalid.length) {
      setMsg(`Invalid file format: ${invalid.map((f) => f.name).join(', ')}. Please upload RealTime long-form .csv files.`);
      setMsgType('error');
      return;
    }
    setBusy(true);
    setMsg('');
    const uploadId = Date.now();
    const entries = files.map((f, idx) => ({ key: `${uploadId}-${idx}`, name: f.name, size: f.size, pct: 0, status: 'uploading' }));
    setUploads(entries);

    try {
      if (files.length === 1) {
        const f = files[0];
        try {
          const newBatch = await uploadRealtime(f, user, (pct) =>
            setUploads((prev) => prev.map((u) => (u.key === entries[0].key ? { ...u, pct } : u)))
          );
          setUploads((prev) => prev.map((u) => (u.key === entries[0].key ? { ...u, pct: 100, status: 'queued' } : u)));
          if (newBatch && newBatch.id) {
            setBatches((prev) => [newBatch, ...prev.filter((x) => x.id !== newBatch.id)]);
          }
          setMsg(`Batch '${f.name}' accepted. Visit reconstruction pipeline active.`);
          setMsgType('success');
        } catch (x) {
          setUploads((prev) => prev.map((u) => (u.key === entries[0].key ? { ...u, status: 'error', error: x.message } : u)));
          setMsg(x.message || 'Import failed.');
          setMsgType('error');
        }
      } else {
        // Bulk upload: one request carrying every file; overall progress reflects total bytes sent.
        const result = await uploadRealtimeBulk(
          files,
          user,
          (pct) => setUploads((prev) => prev.map((u) => ({ ...u, pct })))
        );
        setUploads((prev) =>
          prev.map((u, idx) => {
            const item = result?.items?.[idx];
            return { ...u, pct: 100, status: (item?.status || 'queued').toLowerCase(), error: item?.error };
          })
        );
        setMsg(`Bulk upload complete: ${result.accepted}/${result.total} file(s) queued for processing.`);
        setMsgType(result.accepted === result.total ? 'success' : 'error');
      }
      load();
    } finally {
      setBusy(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (busy) return;
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
  };

  return (
    <Page
      title="RealTime Batch Imports"
      desc="Immutable, checksummed source snapshots. Files are streamed and parsed into pseudonymized visit blocks."
    >
      <div
        className={`rt-upload ${dragging ? 'dragging' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <I.Upload size={32} color={dragging ? '#F07E26' : '#64748b'} />
        <b>{dragging ? 'Drop RealTime CSV snapshot(s) here' : 'Import RealTime Patient Batch'}</b>
        <span>Drag &amp; drop one or more approved long-form CSV snapshots here, or click to browse files</span>
        <input
          type="file"
          accept=".csv,text/csv"
          multiple
          disabled={busy}
          onChange={(e) => {
            if (e.target.files.length) handleFiles(e.target.files);
            e.target.value = '';
          }}
        />
      </div>

      {uploads.length > 0 && (
        <div className="a-notice" style={{ marginBottom: '16px', display: 'grid', gap: '10px' }}>
          {uploads.map((u) => (
            <div key={u.key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span>{u.name} {u.size ? `(${(u.size / 1024 / 1024).toFixed(2)} MB)` : ''}</span>
                <span style={{ fontWeight: 600, color: u.status === 'error' ? '#dc2626' : u.status === 'queued' ? '#16a34a' : '#64748b' }}>
                  {u.status === 'uploading' ? `${u.pct}%` : u.status === 'error' ? `Failed: ${u.error || 'error'}` : u.status}
                </span>
              </div>
              <ProgressBar pct={u.pct} tone={u.status === 'error' ? 'error' : u.status === 'queued' ? 'success' : 'info'} />
            </div>
          ))}
        </div>
      )}

      {msg && (
        <div
          className={`a-notice ${msgType === 'error' ? 'a-notice-error' : msgType === 'success' ? 'a-notice-success' : ''}`}
          style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <I.Info size={18} />
            <span>{msg}</span>
          </div>
          {onNavigate && msgType === 'success' && (
            <button
              className="a-primary"
              style={{ fontSize: '11px', padding: '4px 10px' }}
              onClick={() => onNavigate('/monitor/reconstruction')}
            >
              Inspect Reconstructed Patients →
            </button>
          )}
        </div>
      )}

      <Table
        cols={['Batch ID', 'Filename', 'Stage', 'Progress', 'Rows Processed', 'Participants', 'Visits', 'Excluded Blinded', 'Errors']}
        rows={(batches || []).map((b) => ({
          id: b.id,
          cells: [
            <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{(b.id || '').slice(0, 8) || '—'}</span>,
            b.filename || '—',
            <span
              style={{
                fontWeight: 700,
                color: b.status === 'MONITOR_QC_REQUIRED' ? '#16a34a' : b.status === 'FAILED' ? '#dc2626' : '#ea580c'
              }}
            >
              {b.status || '—'}
            </span>,
            <div style={{ minWidth: '90px' }}>
              <ProgressBar pct={b.progress_pct ?? 0} tone={b.status === 'FAILED' ? 'error' : b.status === 'MONITOR_QC_REQUIRED' ? 'success' : 'info'} />
              <span style={{ fontSize: '10px', color: '#64748b' }}>{b.progress_pct ?? 0}%</span>
            </div>,
            (b.rows_processed || 0).toLocaleString(),
            b.participants ?? 0,
            b.visits ?? 0,
            b.prohibited_excluded ?? 0,
            b.errors ?? 0
          ]
        }))}
      />
    </Page>
  );
}

function ReconstructionQC({ user, onOpen }) {
  const [data, setData] = useState({ items: [], total: 0 });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  const load = () => listPatients(user, { page_size: 100 }).then(setData);

  useEffect(() => {
    load();
  }, []);

  const approveAll = async () => {
    setBusy(true);
    setMsg('Approving all visit reconstructions…');
    try {
      for (const p of data.items) {
        if (p.qc_status !== 'QC_APPROVED' && p.qc_status !== 'ASSIGNED') {
          await approvePatient(p.id, user);
        }
      }
      setMsg('All visit reconstructions QC approved!');
      load();
    } catch (e) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page
      title="Visit Reconstruction QC"
      desc="Inspect and verify reconstructed longitudinal visit blocks. Approve packages for adjudicator assignment."
    >
      <div className="monitor-toolbar" style={{ marginBottom: '16px' }}>
        <button className="a-primary" onClick={approveAll} disabled={busy}>
          <I.CheckCheck size={14} /> {busy ? 'Approving…' : 'QC Approve All Reconstructions'}
        </button>
      </div>

      {msg && (
        <div className="a-notice" style={{ marginBottom: '16px' }}>
          <I.Info size={18} />
          <span>{msg}</span>
        </div>
      )}

      <Table
        cols={['Blinded Subject', 'Study', 'Visits', 'First Visit', 'Latest Visit', 'Derived Onset', 'Completeness', 'History', 'QC Status', 'Action']}
        rows={data.items.map((p) => ({
          id: p.id,
          data: p,
          cells: [
            <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{p.subject_id}</span>,
            <span className="study-badge">{p.study}</span>,
            `${p.visit_count} visits`,
            date(p.first_visit),
            date(p.latest_visit),
            p.onset_classification,
            `${Math.round((p.packet_completeness || 0) * 100)}%`,
            `${Math.round((p.history_completeness || 0) * 100)}%`,
            <span
              className={`badge-qc ${
                p.qc_status === 'QC_APPROVED' || p.qc_status === 'ASSIGNED' ? 'approved' : 'pending'
              }`}
            >
              {p.qc_status}
            </span>,
            <div style={{ display: 'flex', gap: '6px' }}>
              <button className="a-link" onClick={() => onOpen(p)}>
                Inspect
              </button>
              {p.qc_status === 'MONITOR_QC_REQUIRED' && (
                <button
                  className="a-primary"
                  style={{ fontSize: '10px', padding: '3px 8px' }}
                  onClick={async () => {
                    await approvePatient(p.id, user);
                    load();
                  }}
                >
                  QC Approve
                </button>
              )}
            </div>
          ]
        }))}
      />
    </Page>
  );
}

function Assignments({ user, onOpen }) {
  const [data, setData] = useState({ items: [], total: 0 });
  const [roster, setRoster] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  const load = () =>
    Promise.all([listPatients(user, { page_size: 100 }), listAdjudicators(user)])
      .then(([patients, adjudicators]) => {
        setData(patients);
        setRoster(adjudicators);
      });

  useEffect(() => {
    load();
  }, []);

  const doAssign = async (patientId, email, role) => {
    try {
      await assignPatient(patientId, email, role, user);
      setMsg(`Assigned ${email} as ${role}.`);
      load();
    } catch (e) {
      setMsg(e.message);
    }
  };

  const autoAssignAll = async () => {
    setBusy(true);
    setMsg('Assigning demo adjudicators A & B to all subjects…');
    try {
      if (roster.length < 2) { setMsg('At least two active adjudicators are required.'); return; }
      for (const p of data.items) {
        const ordered=[...roster].sort((a,b)=>(a.active_workload||0)-(b.active_workload||0)||a.email.localeCompare(b.email));
        await assignPatient(p.id, ordered[0].email, 'REVIEWER_A', user);
        await assignPatient(p.id, ordered[1].email, 'REVIEWER_B', user);
      }
      setMsg('Auto-assigned Adjudicator A & Adjudicator B to all participants!');
      load();
    } catch (e) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page
      title="Adjudicator Assignments"
      desc="Assign independent blinded adjudicator accounts (Reviewer A & Reviewer B) to QC-approved participant packages."
    >
      <div className="monitor-toolbar" style={{ marginBottom: '16px' }}>
        <button className="a-primary" onClick={autoAssignAll} disabled={busy}>
          <I.Users size={14} /> {busy ? 'Assigning…' : 'Auto-Assign Demo Adjudicators (A & B to All)'}
        </button>
      </div>

      {msg && (
        <div className="a-notice" style={{ marginBottom: '16px' }}>
          <I.Info size={18} />
          <span>{msg}</span>
        </div>
      )}

      <Table
        cols={['Blinded Subject', 'Visits', 'Derivation', 'QC Status', 'Reviewer A', 'Reviewer B', 'Actions']}
        rows={data.items.map((p) => {
          const revA = (p.assignments || []).find((a) => a.reviewer_role === 'REVIEWER_A')?.reviewer_upn || '';
          const revB = (p.assignments || []).find((a) => a.reviewer_role === 'REVIEWER_B')?.reviewer_upn || '';
          return {
            id: p.id,
            data: p,
            cells: [
              <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{p.subject_id}</span>,
              `${p.visit_count} visits`,
              p.onset_classification,
              <span className={`badge-qc ${p.qc_status === 'ASSIGNED' ? 'assigned' : 'approved'}`}>
                {p.qc_status}
              </span>,
              <select
                value={revA}
                onChange={(e) => doAssign(p.id, e.target.value, 'REVIEWER_A')}
                style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '11.5px', border: '1px solid #cbd5e1' }}
              >
                <option value="">-- Assign Reviewer A --</option>
                {roster.map((a) => (
                  <option key={a.email} value={a.email} disabled={a.email === revB}>
                    {a.display_name} ({a.email})
                  </option>
                ))}
              </select>,
              <select
                value={revB}
                onChange={(e) => doAssign(p.id, e.target.value, 'REVIEWER_B')}
                style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '11.5px', border: '1px solid #cbd5e1' }}
              >
                <option value="">-- Assign Reviewer B --</option>
                {roster.map((a) => (
                  <option key={a.email} value={a.email} disabled={a.email === revA}>
                    {a.display_name} ({a.email})
                  </option>
                ))}
              </select>,
              <button className="a-link" onClick={() => onOpen(p)}>
                View Package
              </button>
            ]
          };
        })}
      />
    </Page>
  );
}

function Patients({ user, onOpen }) {
  const [data, setData] = useState({ items: [], total: 0 });
  const [q, setQ] = useState('');

  useEffect(() => {
    listPatients(user, { search: q, page_size: 100 }).then(setData);
  }, [q]);

  return (
    <Page title="Longitudinal Patient Database" desc="Pseudonymised participants from QC-controlled RealTime batches.">
      <div className="monitor-toolbar">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search blinded subject ID..." />
      </div>
      <Table
        cols={['Blinded Subject', 'Study', 'Visits', 'First Visit', 'Latest Visit', 'Derived Onset', 'Severity', '% Data', '% History', 'Issues', 'QC']}
        rows={data.items.map((p) => {
          const labStatus = p.lab_issues?.status || 'NO_DATA';
          const abnormalCount = p.lab_issues?.abnormal_count || 0;
          const issueLabel = labStatus === 'ABNORMAL' ? `Abnormal (${abnormalCount})` : labStatus === 'NORMAL' ? 'Normal' : 'No Data';
          const issueColor = labStatus === 'ABNORMAL' ? '#dc2626' : labStatus === 'NORMAL' ? '#16a34a' : '#94a3b8';
          return {
            id: p.id,
            data: p,
            cells: [
              <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{p.subject_id}</span>,
              <span className="study-badge">{p.study}</span>,
              p.visit_count,
              date(p.first_visit),
              date(p.latest_visit),
              p.onset_classification,
              p.maximum_severity,
              `${Math.round((p.packet_completeness || 0) * 100)}%`,
              `${Math.round((p.history_completeness || 0) * 100)}%`,
              <span title={p.open_issues ? `${p.open_issues} unresolved import issue(s)` : 'No unresolved import issues'} style={{ fontWeight: 700, color: issueColor }}>
                {issueLabel}
              </span>,
              <span className={`badge-qc ${p.qc_status === 'ASSIGNED' || p.qc_status === 'QC_APPROVED' ? 'approved' : 'pending'}`}>{p.qc_status}</span>
            ]
          };
        })}
        onOpen={onOpen}
      />
    </Page>
  );
}

function Timeline({ patient, user, onClose }) {
  if (!patient) return null;
  const [assignRole, setAssignRole] = useState('REVIEWER_A');
  const [roster, setRoster] = useState([]);
  const [selectedAdjudicator, setSelectedAdjudicator] = useState('');
  const [msg, setMsg] = useState('');
  useEffect(() => { listAdjudicators(user).then(setRoster).catch(e => setMsg(e.message)); }, [user]);

  const approve = async () => {
    try {
      await approvePatient(patient.id, user);
      setMsg('Participant package QC approved.');
    } catch (e) {
      setMsg(e.message);
    }
  };

  const assign = async () => {
    try {
      await assignPatient(patient.id, selectedAdjudicator, assignRole, user);
      setMsg(`Assigned ${selectedAdjudicator} as ${assignRole}.`);
    } catch (e) {
      setMsg(e.message);
    }
  };

  return (
    <Page title={`Participant ${patient.subject_id}`} desc="Visit-by-visit source evidence and cumulative PE support.">
      <div className="monitor-toolbar" style={{ alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        <button onClick={onClose}>
          <I.ArrowLeft size={14} /> Back
        </button>
        <button className="a-primary" onClick={approve}>
          Approve Package QC
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#f1f5f9', padding: '4px 8px', borderRadius: '6px' }}>
          <select value={assignRole} onChange={(e) => setAssignRole(e.target.value)} style={{ fontSize: '11px', padding: '4px' }}>
            <option value="REVIEWER_A">Reviewer A</option>
            <option value="REVIEWER_B">Reviewer B</option>
          </select>
          <select
            value={selectedAdjudicator}
            onChange={(e) => setSelectedAdjudicator(e.target.value)}
            style={{ fontSize: '11px', padding: '4px' }}
          >
            <option value="">Select active adjudicator</option>
            {roster.map(a => <option key={a.email} value={a.email}>{a.display_name} ({a.email})</option>)}
          </select>
          <button className="a-primary" style={{ fontSize: '11px', padding: '4px 8px' }} onClick={assign}>
            Assign Adjudicator
          </button>
        </div>
      </div>

      {msg && (
        <div className="a-notice" style={{ marginTop: '8px', marginBottom: '12px' }}>
          <I.Info size={16} />
          <span>{msg}</span>
        </div>
      )}

      {patient.longitudinal && (
        <div className="a-notice">
          <I.Activity />
          <div>
            <strong>Longitudinal Advisory</strong>
            <span>{patient.longitudinal.explanation}</span>
          </div>
        </div>
      )}

      <div className="rt-timeline">
        {patient.visits.map((v) => (
          <details key={v.id}>
            <summary>
              <b>
                {v.name} (Occurrence #{v.occurrence})
              </b>
              <div className="rt-timeline-meta">
                <span>{date(v.date)}</span>
                <span className={`badge-reconstruction ${String(v.reconstruction.confidence || '').toLowerCase()}`}>
                  {v.reconstruction.confidence} Confidence
                </span>
                <span className={`badge-qc ${String(v.reconstruction.qc_status || '').toLowerCase() === 'qc_approved' ? 'approved' : 'pending'}`}>
                  {v.reconstruction.qc_status}
                </span>
              </div>
            </summary>
            <Table
              cols={['Variable', 'Value', 'Observed', 'Date Confidence', 'Provenance', 'Source']}
              rows={Object.entries(v.evidence).flatMap(([k, a]) =>
                a.map((x, i) => ({
                  id: k + i,
                  cells: [
                    <span style={{ fontWeight: 600 }}>{k}</span>,
                    String(x.value ?? '—'),
                    date(x.observed_at),
                    x.date_confidence,
                    x.provenance,
                    `${x.source.form} / ${x.source.page} / row ${x.source.row}`
                  ]
                }))
              )}
            />
          </details>
        ))}
      </div>
    </Page>
  );
}

class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error('Monitor error:', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '30px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#991b1b', margin: '20px' }}>
          <h3 style={{ margin: 0, marginBottom: '8px' }}>⚠ View Error</h3>
          <p>{this.state.error?.message || 'A render exception occurred.'}</p>
          <button
            className="a-primary"
            style={{ marginTop: '12px' }}
            onClick={() => {
              this.setState({ hasError: false });
              location.reload();
            }}
          >
            Reload Monitor Portal
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function ReferenceRanges({ user }) {
  const [state, setState] = useState({ analytes: [], items: [] });
  const [msg, setMsg] = useState('');
  const [form, setForm] = useState({ analyte: '', site_code: '', lab_code: '', unit: '', low: '', high: '' });

  const load = () => listReferenceRanges(user).then(setState).catch((e) => setMsg(e.message));
  useEffect(() => {
    load();
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.analyte || (form.low === '' && form.high === '')) {
      setMsg('Select an analyte and provide at least a low or high bound.');
      return;
    }
    try {
      await upsertReferenceRange(
        {
          analyte: form.analyte,
          site_code: form.site_code || null,
          lab_code: form.lab_code || null,
          unit: form.unit || null,
          low: form.low === '' ? null : Number(form.low),
          high: form.high === '' ? null : Number(form.high)
        },
        user
      );
      setMsg('Reference range saved.');
      setForm({ analyte: '', site_code: '', lab_code: '', unit: '', low: '', high: '' });
      load();
    } catch (e) {
      setMsg(e.message);
    }
  };

  return (
    <Page title="Lab Reference Ranges" desc="Configure per-site / per-lab Normal vs. Abnormal thresholds used by the Issues column. Leave Site/Lab blank to set a study-wide default.">
      <form onSubmit={submit} className="monitor-toolbar" style={{ flexWrap: 'wrap', gap: '8px', marginBottom: '16px' }}>
        <select value={form.analyte} onChange={(e) => setForm({ ...form, analyte: e.target.value })}>
          <option value="">-- Analyte --</option>
          {state.analytes.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <input placeholder="Site code (optional)" value={form.site_code} onChange={(e) => setForm({ ...form, site_code: e.target.value })} />
        <input placeholder="Lab code (optional)" value={form.lab_code} onChange={(e) => setForm({ ...form, lab_code: e.target.value })} />
        <input placeholder="Unit" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
        <input placeholder="Low" type="number" step="any" value={form.low} onChange={(e) => setForm({ ...form, low: e.target.value })} style={{ width: '90px' }} />
        <input placeholder="High" type="number" step="any" value={form.high} onChange={(e) => setForm({ ...form, high: e.target.value })} style={{ width: '90px' }} />
        <button className="a-primary" type="submit">
          Save Range
        </button>
      </form>

      {msg && (
        <div className="a-notice" style={{ marginBottom: '16px' }}>
          <I.Info size={18} />
          <span>{msg}</span>
        </div>
      )}

      <Table
        cols={['Analyte', 'Scope', 'Unit', 'Low', 'High', 'Active', 'Action']}
        rows={state.items.map((r) => ({
          id: r.id,
          cells: [
            r.analyte,
            r.site_code ? `Site: ${r.site_code}${r.lab_code ? ` / Lab: ${r.lab_code}` : ''}` : 'Study-wide default',
            r.unit || '—',
            r.low ?? '—',
            r.high ?? '—',
            <span style={{ color: r.is_active ? '#16a34a' : '#94a3b8', fontWeight: 700 }}>{r.is_active ? 'Active' : 'Inactive'}</span>,
            r.is_active ? (
              <button
                className="a-link"
                onClick={() => {
                  if (confirm('Deactivate this reference range?')) deactivateReferenceRange(r.id, user).then(load);
                }}
              >
                Deactivate
              </button>
            ) : (
              '—'
            )
          ]
        }))}
      />
    </Page>
  );
}

export default function MonitorPortal({ user, onLogout }) {
  const [path, setPath] = useState(location.pathname);
  const [selected, setSelected] = useState(null);

  const go = (p) => {
    history.pushState({}, '', p);
    setPath(p);
    setSelected(null);
  };

  const open = async (r) => setSelected(await getPatient(r.id, user));

  let content = selected ? (
    <Timeline patient={selected} user={user} onClose={() => setSelected(null)} />
  ) : path === '/monitor/imports' ? (
    <Imports user={user} onNavigate={go} />
  ) : path === '/monitor/reconstruction' ? (
    <ReconstructionQC user={user} onOpen={open} />
  ) : path === '/monitor/assignments' ? (
    <Assignments user={user} onOpen={open} />
  ) : path === '/monitor/patients' || path === '/monitor/longitudinal' ? (
    <Patients user={user} onOpen={open} />
  ) : path === '/monitor/reference-ranges' ? (
    <ReferenceRanges user={user} />
  ) : (
    <Page
      title="Monitor / QC Dashboard"
      desc="Import, reconstruct, derive, approve and assign longitudinal patient packages."
    >
      <div className="a-notice">
        <I.Shield />
        <div>
          <strong>Clinical Operations Boundary</strong>
          <span>Identifiers and prohibited biomarker content are excluded from adjudicator packages. All monitor actions are audited.</span>
        </div>
      </div>
      <div className="monitor-metrics" style={{ marginTop: '16px' }}>
        <button onClick={() => go('/monitor/imports')}>
          <b>Import</b>
          <span>RealTime CSV Batch</span>
        </button>
        <button onClick={() => go('/monitor/reconstruction')}>
          <b>QC Review</b>
          <span>Visit Reconstructions</span>
        </button>
        <button onClick={() => go('/monitor/assignments')}>
          <b>Assignments</b>
          <span>Reviewers A &amp; B</span>
        </button>
        <button onClick={() => go('/monitor/patients')}>
          <b>Database</b>
          <span>Blinded Participants</span>
        </button>
      </div>
    </Page>
  );

  return (
    <div className="admin-app">
      <header className="a-header">
        <div className="a-brand">
          <span>
            <img src="/acrn-logo.png" alt="ACRN" />
          </span>
          <div>
            <strong>ACRN Adjudication Platform</strong>
            <small>Monitor / Quality Control Portal</small>
          </div>
        </div>
        <div className="a-boundary">
          <I.EyeOff size={14} /> Operational QC &amp; Ingestion Role
        </div>
        <div className="a-user">
          <div>
            <strong>{user?.name || user?.display_name || 'Monitor User'}</strong>
            <small>{user?.role || 'Monitor'}</small>
          </div>
          <button onClick={onLogout} aria-label="Sign out">
            <I.LogOut size={16} />
          </button>
        </div>
      </header>
      <div className="a-body">
        <aside className="a-nav">
          <section>
            <h2>LONGITUDINAL OPERATIONS</h2>
            {nav.map(([p, l, n]) => {
              const Icon = I[n] || I.Circle;
              return (
                <button className={path === p ? 'active' : ''} onClick={() => go(p)} key={p}>
                  <Icon size={15} />
                  <span>{l}</span>
                </button>
              );
            })}
          </section>
        </aside>
        <main className="a-main">
          <ErrorBoundary>{content}</ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
