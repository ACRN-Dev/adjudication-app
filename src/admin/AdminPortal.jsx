import React, { useEffect, useMemo, useState } from 'react';
import * as Icon from 'lucide-react';
import * as data from './adminData';
import { 
  listUsers, 
  setUserStatus, 
  unlockUser, 
  resetDemoPassword, 
  setUserRole, 
  setPortalRole, 
  createUser 
} from '../services/authApi';
import { SOP_DOCUMENTS } from '../components/SopLibraryModal';
import './admin.css';

const NAV = [
  ['OVERVIEW', [
    ['/admin', 'Dashboard', 'LayoutDashboard']
  ]],
  ['ACCESS & PEOPLE', [
    ['/admin/users', 'Users', 'Users'],
    ['/admin/adjudicator-profiles', 'Adjudicator Profiles', 'ContactRound'],
    ['/admin/committee-assignments', 'Committee Assignments', 'UserCog'],
    ['/admin/access', 'Roles and Permissions', 'ShieldCheck'],
    ['/admin/access-reviews', 'Access Reviews', 'UserCheck'],
    ['/admin/training', 'Training and COI', 'GraduationCap']
  ]],
  ['STUDY CONFIGURATION', [
    ['/admin/studies', 'Studies', 'BookOpen'],
    ['/admin/sites', 'Sites', 'MapPin'],
    ['/admin/endpoints', 'Endpoints and Windows', 'CalendarRange'],
    ['/admin/workflows', 'Workflow Configuration', 'Workflow']
  ]],
  ['DATA CONFIGURATION', [
    ['/admin/mappings', 'Canonical Field Mappings', 'GitCompare'],
    ['/admin/terminology', 'Units and Terminology', 'Languages'],
    ['/admin/dictionaries', 'Clinical Dictionaries', 'Library'],
    ['/admin/import-contracts', 'Import Contracts', 'FileInput']
  ]],
  ['CONTROLLED CONTENT', [
    ['/admin/rules', 'DV Rule Versions', 'Binary'],
    ['/admin/forms', 'Forms and Templates', 'Files'],
    ['/admin/sops', 'SOP References', 'FileCheck2']
  ]],
  ['SYSTEM', [
    ['/admin/integrations', 'Integrations', 'PlugZap'],
    ['/admin/audit', 'Audit Trail', 'ScrollText'],
    ['/admin/reports', 'Reports', 'FileBarChart'],
    ['/admin/health', 'Environment and Health', 'Activity']
  ]]
];

const TITLES = Object.fromEntries(NAV.flatMap(([, x]) => x.map(([p, l]) => [p, l])));

const DEFAULT_DASH = {
  environment: 'DEMO / STANDALONE',
  api: 'Healthy',
  database: 'PostgreSQL / SQLite fallback',
  metrics: {
    active_studies: 2,
    configured_sites: 5,
    active_users: 6,
    pending_approval: 1,
    expiring_access: 1,
    incomplete_training: 1,
    open_access_reviews: 1,
    integration_warnings: 2
  },
  action_queue: [
    { type: 'access', label: 'Approve pending user access (Lindiwe Dube)', count: 1 },
    { type: 'expiry', label: 'Review expiring GCP certificates (Dr. Miriam Ndlovu)', count: 1 },
    { type: 'training', label: 'Review incomplete staff training records', count: 1 },
    { type: 'integration', label: 'Resolve eSource / eTMF adapter warnings', count: 2 }
  ]
};

function goTo(path) {
  history.pushState({}, '', path);
  dispatchEvent(new CustomEvent('app-nav', { detail: path }));
}

function downloadCsv(name, columns, rows) {
  const quote = v => `"${String(v ?? '').replaceAll('"', '""')}"`;
  const csv = [columns, ...rows].map(r => r.map(quote).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `${name}-DEMO.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// 21 CFR Part 11 Audit Reason Modal
function AuditReasonModal({ isOpen, title, actionLabel, defaultReason = '', onConfirm, onCancel, isBusy }) {
  const [reason, setReason] = useState(defaultReason);

  useEffect(() => {
    setReason(defaultReason);
  }, [defaultReason, isOpen]);

  if (!isOpen) return null;

  return (
    <div className="a-modal-overlay" role="dialog" aria-modal="true">
      <div className="a-modal-card">
        <div className="a-modal-header">
          <strong><Icon.ShieldCheck size={16} /> 21 CFR Part 11 Audit Reason Required</strong>
          <button type="button" onClick={onCancel} disabled={isBusy} aria-label="Close">
            <Icon.X size={16} />
          </button>
        </div>
        <form onSubmit={(e) => { e.preventDefault(); if (reason.trim()) onConfirm(reason.trim()); }}>
          <div className="a-modal-body">
            <p style={{ margin: '0 0 10px', fontSize: '13px', color: '#1e293b' }}>
              <strong>Action:</strong> {actionLabel || title}
            </p>
            <p style={{ margin: '0 0 12px', fontSize: '12px', color: '#64748b' }}>
              Per FDA 21 CFR Part 11 and ICH-GCP regulatory compliance, administrative security modifications must record an immutable audit justification.
            </p>
            <div>
              <label style={{ display: 'block', fontSize: '11.5px', fontWeight: 700, color: 'var(--admin-navy)', marginBottom: '4px' }}>
                Required Justification / Audit Reason *
              </label>
              <textarea
                required
                rows={3}
                value={reason}
                onChange={e => setReason(e.target.value)}
                placeholder="Enter justification for this administrative action..."
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  fontSize: '12.5px',
                  fontFamily: 'var(--font-family)',
                  border: '1px solid var(--admin-border)',
                  borderRadius: '4px',
                  boxSizing: 'border-box'
                }}
              />
            </div>
          </div>
          <div className="a-modal-footer">
            <button type="button" onClick={onCancel} disabled={isBusy} className="a-secondary">
              Cancel
            </button>
            <button type="submit" disabled={isBusy || !reason.trim()} className="a-primary">
              {isBusy ? 'Saving...' : 'Confirm & Sign Audit Entry'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Badge({ children }) {
  let s = String(children || '').toLowerCase();
  let c = s.includes('active') || s.includes('healthy') || s.includes('passed') || s.includes('current') || s.includes('success') || s.includes('disclosed') || s.includes('governed') ? 'ok' :
          s.includes('pending') || s.includes('warning') || s.includes('expiring') || s.includes('validation') || s.includes('draft') ? 'warn' :
          s.includes('failed') || s.includes('incomplete') || s.includes('prohibited') || s.includes('disabled') || s.includes('inactive') ? 'bad' : '';
  return <span className={'a-badge ' + c}>{children}</span>;
}

function Table({ caption, columns, rows, actions }) {
  const [filter, setFilter] = useState({ query: '', status: '' });
  useEffect(() => {
    const f = e => setFilter(e.detail);
    addEventListener('admin-table-filter', f);
    return () => removeEventListener('admin-table-filter', f);
  }, []);

  const shown = useMemo(() => rows.filter(r => {
    const text = r.join(' ').toLowerCase();
    return (!filter.query || text.includes(filter.query.toLowerCase())) &&
           (!filter.status || text.includes(filter.status.toLowerCase()));
  }), [rows, filter]);

  return (
    <div className="a-table-wrap">
      <table className="a-table">
        <caption>{caption} — {shown.length} record{shown.length === 1 ? '' : 's'}</caption>
        <thead>
          <tr>
            {columns.map(c => <th scope="col" key={c}>{c}</th>)}
            {actions && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {shown.map((r, i) => (
            <tr key={i}>
              {r.map((v, j) => (
                <td key={j}>
                  {/status|training|tests|outcome|compliance|certification/i.test(columns[j]) ? <Badge>{v}</Badge> : v}
                </td>
              ))}
              {actions && <td>{actions(r)}</td>}
            </tr>
          ))}
          {!shown.length && (
            <tr>
              <td colSpan={columns.length + (actions ? 1 : 0)} style={{ textAlign: 'center', padding: '16px', color: '#64748b' }}>
                No demonstration records match the current filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function Page({ title, desc, action, children }) {
  return (
    <>
      <div className="a-page-head">
        <div>
          <h1>{title}</h1>
          <p>{desc}</p>
        </div>
        {action}
      </div>
      {children}
    </>
  );
}

function Toolbar({ children, onSearchChange, onStatusChange }) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');

  const apply = (q, s) => {
    dispatchEvent(new CustomEvent('admin-table-filter', { detail: { query: q, status: s } }));
  };

  return (
    <div className="a-toolbar">
      <div>
        <Icon.Search size={14} />
        <input
          id="admin-search"
          value={query}
          onChange={e => {
            const val = e.target.value;
            setQuery(val);
            apply(val, status);
            onSearchChange?.(val);
          }}
          placeholder="Search or filter records…"
        />
      </div>
      <select
        aria-label="Status filter"
        value={status}
        onChange={e => {
          const val = e.target.value;
          setStatus(val);
          apply(query, val);
          onStatusChange?.(val);
        }}
      >
        <option value="">All statuses</option>
        <option value="Active">Active</option>
        <option value="Current">Current</option>
        <option value="Pending">Pending</option>
        <option value="Expiring">Expiring Soon</option>
        <option value="Draft">Draft</option>
        <option value="Warning">Warning</option>
      </select>
      {children}
      <button
        type="button"
        onClick={() => {
          setQuery('');
          setStatus('');
          apply('', '');
          onSearchChange?.('');
          onStatusChange?.('');
        }}
      >
        Clear filters
      </button>
    </div>
  );
}

const Primary = ({ children, onClick, title = 'Create controlled draft' }) => (
  <button className="a-primary" onClick={onClick || (() => alert(`${title}: Function ready in controlled demonstration mode.`))}>
    {children}
  </button>
);

function Notice({ kind = 'info', title, children }) {
  return (
    <div className={'a-notice ' + kind}>
      <Icon.ShieldAlert size={17} />
      <div>
        <strong>{title}</strong>
        <span>{children}</span>
      </div>
    </div>
  );
}

/* =============================================
   1. DASHBOARD COMPONENT
   ============================================= */
function Dashboard({ dash }) {
  let m = dash.metrics;
  const target = {
    access: '/admin/users',
    expiry: '/admin/training',
    training: '/admin/training',
    integration: '/admin/integrations',
    ACCESS_APPROVAL: '/admin/users',
    EXPIRY: '/admin/training',
    TRAINING: '/admin/training',
    INTEGRATION: '/admin/integrations'
  };

  return (
    <Page title="Administration Overview" desc="Operational governance, access and configuration status. Clinical case content is not available here.">
      <Notice title="Demonstration administration environment">
        Synthetic records only · Governed Part 11 trial infrastructure · Real-time operational audit active.
      </Notice>
      <div className="a-metrics">
        {[
          ['Active studies', m.active_studies, '/admin/studies'],
          ['Configured sites', m.configured_sites, '/admin/sites'],
          ['Active users', m.active_users, '/admin/users'],
          ['Pending approval', m.pending_approval, '/admin/users'],
          ['Expiring access', m.expiring_access, '/admin/training'],
          ['Incomplete training', m.incomplete_training, '/admin/training'],
          ['Open access reviews', m.open_access_reviews, '/admin/access-reviews'],
          ['Integration warnings', m.integration_warnings, '/admin/integrations']
        ].map(([l, v, p]) => (
          <button onClick={() => goTo(p)} key={l}>
            <strong>{v}</strong>
            <span>{l}</span>
          </button>
        ))}
      </div>
      <div className="a-grid2">
        <section className="a-panel">
          <h2><Icon.ClipboardCheck size={16} color="var(--admin-orange)" /> Action queue</h2>
          {dash.action_queue.map(q => (
            <button className="a-queue" key={q.type} onClick={() => goTo(target[q.type] || '/admin')}>
              <span>{q.label}</span>
              <Badge>{q.count} open</Badge>
              <Icon.ChevronRight size={14} />
            </button>
          ))}
        </section>
        <section className="a-panel">
          <h2><Icon.Activity size={16} color="var(--admin-teal)" /> Environment and health</h2>
          <dl>
            <div><dt>Environment</dt><dd><Badge>{dash.environment}</Badge></dd></div>
            <div><dt>API status</dt><dd><Badge>{dash.api}</Badge></dd></div>
            <div><dt>Database / migration</dt><dd>{dash.database} · schema current</dd></div>
            <div><dt>Clinical case access</dt><dd><span style={{ color: '#15803d', fontWeight: 600 }}>Strictly Isolated (Blinded)</span></dd></div>
          </dl>
        </section>
      </div>
      <Table caption="Recent security and configuration events" columns={['Event ID', 'Timestamp', 'Acting user', 'Role', 'Action', 'Entity', 'Reason', 'Outcome']} rows={data.audits} />
    </Page>
  );
}

/* =============================================
   2. USERS COMPONENT
   ============================================= */
function Users() {
  const [rows, setRows] = useState([]);
  const [msg, setMsg] = useState('');
  const [q, setQ] = useState('');
  const [role, setRole] = useState('');
  const [status, setStatus] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [addBusy, setAddBusy] = useState(false);
  const [createdNotice, setCreatedNotice] = useState(null);
  const [auditModal, setAuditModal] = useState({ isOpen: false, title: '', actionFn: null });
  const [newUser, setNewUser] = useState({
    email: '',
    display_name: '',
    role: 'MONITOR',
    password: '',
    study_scope: '*',
    reason: 'Initial user onboarding via Admin Portal'
  });

  const load = () => listUsers({ search: q, role, status, page_size: 100 })
    .then(x => setRows(x.items))
    .catch(e => setMsg(e.message));

  useEffect(() => { load(); }, [q, role, status]);

  const requestAuditAction = (title, actionFn, defaultReason = '') => {
    setAuditModal({
      isOpen: true,
      title,
      actionLabel: title,
      defaultReason,
      actionFn
    });
  };

  const handleAuditConfirm = async (reason) => {
    if (!auditModal.actionFn) return;
    try {
      await auditModal.actionFn(reason);
      setMsg(`${auditModal.title} successfully executed and logged to audit trail.`);
      setAuditModal({ isOpen: false, title: '', actionFn: null });
      load();
    } catch (e) {
      setMsg('Error: ' + e.message);
      setAuditModal({ isOpen: false, title: '', actionFn: null });
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newUser.email || !newUser.display_name || !newUser.reason) {
      setMsg('Please fill in all required fields (Name, Email, Reason).');
      return;
    }

    const ownerCount = rows.filter(u => u.role === 'OWNER' || u.roleCode === 'OWNER').length;
    const adminCount = rows.filter(u => u.role === 'ADMIN' || u.roleCode === 'ADMIN').length;
    
    if (newUser.role === 'OWNER' && ownerCount >= 1) {
      setMsg('Error creating user: There can only be one Owner in the system.');
      return;
    }
    if (newUser.role === 'ADMIN' && adminCount >= 2) {
      setMsg('Error creating user: There can only be a maximum of 2 Admins in the system.');
      return;
    }

    setAddBusy(true);
    setMsg('');
    try {
      const res = await createUser({
        email: newUser.email.trim(),
        display_name: newUser.display_name.trim(),
        role: newUser.role,
        password: newUser.password || undefined,
        study_scope: newUser.study_scope || '*',
        reason: newUser.reason.trim()
      });
      setCreatedNotice({
        email: res.email,
        name: res.display_name,
        role: res.role,
        password: res.temporary_password
      });
      setShowAddModal(false);
      setNewUser({
        email: '',
        display_name: '',
        role: 'MONITOR',
        password: '',
        study_scope: '*',
        reason: 'Initial user onboarding via Admin Portal'
      });
      load();
    } catch (e) {
      setMsg('Error creating user: ' + e.message);
    } finally {
      setAddBusy(false);
    }
  };

  const tableRows = rows.map(u => [
    u.display_name || '—',
    u.email,
    u.role,
    u.portal_role ? u.portal_role.replace(/_/g, ' ') : 'Standard',
    u.status,
    u.is_demo ? 'Yes' : 'No',
    u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Never',
    u.locked_until ? 'Locked' : 'Unlocked'
  ]);

  return (
    <Page
      title="User Account Management"
      desc="Active user accounts, role-based access control, locking and credential resets."
      action={
        <Primary onClick={() => setShowAddModal(true)}>
          <Icon.UserPlus size={14} /> Add User Account
        </Primary>
      }
    >
      <Notice title="Account Security & Access Controls">
        Adjudicator, Monitor, Chairperson, and Admin identities are governed under 21 CFR Part 11. All state transitions create permanent audit entries.
      </Notice>

      {msg && (
        <div className={msg.startsWith('Error') ? 'a-notice danger' : 'a-success'} role="status">
          {msg}
        </div>
      )}

      {createdNotice && (
        <div style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: '6px', padding: '14px', marginBottom: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <strong style={{ color: '#166534', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Icon.CheckCircle2 size={16} /> User Account Created Successfully
            </strong>
            <button onClick={() => setCreatedNotice(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}>
              <Icon.X size={14} />
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px', fontSize: '12px', color: '#1e293b' }}>
            <div><strong>Name:</strong> {createdNotice.name}</div>
            <div><strong>Email:</strong> {createdNotice.email}</div>
            <div><strong>Assigned Role:</strong> <span className="a-badge ok">{createdNotice.role}</span></div>
            <div><strong>Temporary Password:</strong> <code style={{ background: '#dcfce7', padding: '2px 6px', borderRadius: '4px', fontWeight: 700, color: '#14532d' }}>{createdNotice.password}</code></div>
          </div>
          <p style={{ fontSize: '11.5px', color: '#475569', margin: '8px 0 0' }}>Share this temporary password with the user out-of-band. They will be prompted to reset their password on initial login.</p>
        </div>
      )}

      {showAddModal && (
        <div className="a-modal-overlay" role="dialog" aria-modal="true">
          <div className="a-modal-card">
            <div className="a-modal-header">
              <strong><Icon.UserPlus size={16} /> Add New User Account</strong>
              <button onClick={() => setShowAddModal(false)}><Icon.X size={16} /></button>
            </div>
            <form onSubmit={handleCreateUser} style={{ padding: '20px', display: 'grid', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11.5px', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>Full Name / Display Name *</label>
                <input required value={newUser.display_name} onChange={e => setNewUser({ ...newUser, display_name: e.target.value })} placeholder="e.g. Dr. John Doe" style={{ width: '100%', padding: '8px 10px', fontSize: '12px', border: '1px solid #cbd5e1', borderRadius: '4px', boxSizing: 'border-box' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '11.5px', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>Email Address *</label>
                <input required type="email" value={newUser.email} onChange={e => setNewUser({ ...newUser, email: e.target.value })} placeholder="e.g. user@acrnhealth.com" style={{ width: '100%', padding: '8px 10px', fontSize: '12px', border: '1px solid #cbd5e1', borderRadius: '4px', boxSizing: 'border-box' }} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '11.5px', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>Role *</label>
                  <select value={newUser.role} onChange={e => setNewUser({ ...newUser, role: e.target.value })} style={{ width: '100%', padding: '8px 10px', fontSize: '12px', border: '1px solid #cbd5e1', borderRadius: '4px', background: '#fff' }}>
                    <option value="MONITOR">Monitor</option>
                    <option value="ADJUDICATOR">Adjudicator</option>
                    <option value="CHAIRPERSON">Chairperson</option>
                    <option value="ADMIN">Admin</option>
                    <option value="OWNER">Owner</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '11.5px', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>Temporary Password (optional)</label>
                  <input value={newUser.password} onChange={e => setNewUser({ ...newUser, password: e.target.value })} placeholder="Leave blank to auto-generate" style={{ width: '100%', padding: '8px 10px', fontSize: '12px', border: '1px solid #cbd5e1', borderRadius: '4px', boxSizing: 'border-box' }} />
                </div>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '11.5px', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>Audit Reason (21 CFR Part 11 Compliance) *</label>
                <input required value={newUser.reason} onChange={e => setNewUser({ ...newUser, reason: e.target.value })} placeholder="Reason for creating user" style={{ width: '100%', padding: '8px 10px', fontSize: '12px', border: '1px solid #cbd5e1', borderRadius: '4px', boxSizing: 'border-box' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <button type="button" onClick={() => setShowAddModal(false)} className="a-secondary">Cancel</button>
                <button type="submit" disabled={addBusy} className="a-primary">
                  {addBusy ? 'Creating...' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <AuditReasonModal
        isOpen={auditModal.isOpen}
        title={auditModal.title}
        actionLabel={auditModal.actionLabel}
        defaultReason={auditModal.defaultReason}
        onConfirm={handleAuditConfirm}
        onCancel={() => setAuditModal({ isOpen: false, title: '', actionFn: null })}
      />

      <div className="a-toolbar">
        <div>
          <Icon.Search size={14} />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search users by name or email..." />
        </div>
        <select value={role} onChange={e => setRole(e.target.value)}>
          <option value="">All roles</option>
          <option value="ADMIN">Admin</option>
          <option value="MONITOR">Monitor</option>
          <option value="ADJUDICATOR">Adjudicator</option>
          <option value="CHAIRPERSON">Chairperson</option>
          <option value="OWNER">Owner</option>
        </select>
        <select value={status} onChange={e => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
        </select>
        <button type="button" onClick={() => { setQ(''); setRole(''); setStatus(''); }}>Clear filters</button>
      </div>

      <Table
        caption="User account register"
        columns={['Name', 'Email', 'Role', 'Portal role', 'Status', 'Demo', 'Last login', 'Lock state']}
        rows={tableRows}
        actions={(r) => {
          const u = rows.find(x => x.email === r[1]);
          if (!u) return null;
          return (
            <span className="a-actions">
              <button
                onClick={() => requestAuditAction(
                  `${u.status === 'ACTIVE' ? 'Deactivate' : 'Activate'} user account (${u.email})`,
                  why => setUserStatus(u.id, u.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE', why),
                  'Routine administrative credential management'
                )}
              >
                {u.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
              </button>
              <button
                onClick={() => requestAuditAction(
                  `Unlock user account (${u.email})`,
                  why => unlockUser(u.id, why),
                  'User reported accidental lock-out'
                )}
              >
                Unlock
              </button>
              <button
                onClick={() => requestAuditAction(
                  `Reset password for ${u.email}`,
                  why => resetDemoPassword(u.id, why),
                  'User requested credential reset'
                )}
              >
                Reset password
              </button>
              {u.roleCode === 'ADJUDICATOR' && (
                <button onClick={() => goTo(`/admin/adjudicator-profiles?upn=${encodeURIComponent(u.email)}`)}>
                  View profile
                </button>
              )}
              <select
                value={u.roleCode}
                onChange={e => {
                  const newRole = e.target.value;
                  const ownerCount = rows.filter(x => x.role === 'OWNER' || x.roleCode === 'OWNER').length;
                  const adminCount = rows.filter(x => x.role === 'ADMIN' || x.roleCode === 'ADMIN').length;
                  if (newRole === 'OWNER' && ownerCount >= 1 && u.roleCode !== 'OWNER') {
                    setMsg('Error updating role: There can only be one Owner in the system.');
                    window.scrollTo(0, 0);
                    return;
                  }
                  if (newRole === 'ADMIN' && adminCount >= 2 && u.roleCode !== 'ADMIN') {
                    setMsg('Error updating role: There can only be a maximum of 2 Admins in the system.');
                    window.scrollTo(0, 0);
                    return;
                  }
                  requestAuditAction(
                    `Change role of ${u.email} to ${newRole}`,
                    why => setUserRole(u.id, newRole, why),
                    'Role update per study assignment charter'
                  );
                }}
              >
                <option value="ADMIN">Admin</option>
                <option value="MONITOR">Monitor</option>
                <option value="ADJUDICATOR">Adjudicator</option>
                <option value="CHAIRPERSON">Chairperson</option>
                <option value="OWNER">Owner</option>
              </select>
            </span>
          );
        }}
      />
    </Page>
  );
}

/* =============================================
   3. ADJUDICATOR PROFILES COMPONENT
   ============================================= */
function AdjudicatorProfiles() {
  const [rows, setRows] = useState([]);
  const [msg, setMsg] = useState('');
  const [selectedUpn, setSelectedUpn] = useState(() => new URLSearchParams(location.search).get('upn'));

  const load = () => fetch('/api/admin/adjudicator-profiles', { credentials: 'include' })
    .then(r => r.ok ? r.json() : Promise.reject(new Error('Profile request failed')))
    .then(x => setRows(x.items || []))
    .catch(e => setMsg(e.message));

  useEffect(() => { load(); }, []);

  const selected = rows.find(r => r.adjudicator_upn.toLowerCase() === (selectedUpn || '').toLowerCase());

  if (selected) {
    return (
      <Page title={selected.display_name} desc="Clinical workload and committee profile. Contracts and committee seats are tracked under GCP.">
        <button
          className="a-link"
          style={{ marginBottom: '12px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
          onClick={() => { setSelectedUpn(null); history.pushState({}, '', '/admin/adjudicator-profiles'); }}
        >
          <Icon.ArrowLeft size={14} /> Back to Adjudicator Profiles Register
        </button>

        <Notice kind="info" title="Workload & Committee Portfolio">
          Clinical workload is ledger-derived from immutable determinations signed by this physician. Study contracts and committee appointments are governed by Clinical Operations.
        </Notice>

        <div className="a-metrics">
          {[
            ['Total Cases Reviewed', selected.cases_reviewed || 0],
            ['Committee Meetings Attended', selected.meetings_attended || 0],
            ['Active Assignments in Queue', selected.active_assignments || 0],
            ['Overdue Assessments', selected.overdue_assignments || 0],
            ['Reviewer C Tie-Breaker Cases', selected.cases_reviewed_by_role?.REVIEWER_C || 0]
          ].map(([l, v]) => (
            <div key={l}>
              <strong>{v}</strong>
              <span>{l}</span>
            </div>
          ))}
        </div>

        <div className="a-grid2">
          <section className="a-panel">
            <h2><Icon.BookOpen size={16} color="var(--admin-orange)" /> Study Contracts</h2>
            {(selected.contracts || []).length > 0 ? (
              <ul>
                {selected.contracts.map((c, i) => (
                  <li key={i}>
                    <strong>{c.study_code}</strong>: {c.contract_signed_at ? `Signed on ${new Date(c.contract_signed_at).toLocaleDateString()}` : 'Pending signature'} (Ref: {c.contract_reference || 'N/A'})
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ color: '#64748b' }}>No study contract records configured for this adjudicator.</p>
            )}
          </section>

          <section className="a-panel">
            <h2><Icon.UserCheck size={16} color="var(--admin-teal)" /> Committee Memberships</h2>
            <Table
              caption="Committee memberships"
              columns={['Committee', 'Role', 'Effective from', 'Effective to']}
              rows={(selected.committee_memberships || []).map(m => [
                m.committee_name,
                m.membership_role,
                m.effective_from ? new Date(m.effective_from).toLocaleDateString() : '—',
                m.effective_to ? new Date(m.effective_to).toLocaleDateString() : 'Active / Open'
              ])}
            />
          </section>
        </div>
      </Page>
    );
  }

  return (
    <Page
      title="Adjudicator Profiles & Workload"
      desc="Clinical identity, study contracts, committee membership and ledger-derived adjudication workload."
    >
      {msg && <div className="a-notice danger" role="status">{msg}</div>}
      <Toolbar />
      <Table
        caption="Adjudicator profile register"
        columns={['Name', 'Email', 'Role', 'Study contracts', 'Committee membership', 'A/B signed', 'C signed', 'Active assignments', 'Account']}
        rows={rows.map(r => [
          r.display_name,
          r.adjudicator_upn,
          'ADJUDICATOR',
          (r.contracts || []).map(c => `${c.study_code}: ${c.contract_signed_at ? new Date(c.contract_signed_at).toLocaleDateString() : 'Pending'}`).join(' · ') || 'Not configured',
          (r.committee_memberships || []).map(m => `${m.committee_name} (${m.membership_role})`).join(' · ') || 'None',
          (r.cases_reviewed_by_role?.REVIEWER_A || 0) + (r.cases_reviewed_by_role?.REVIEWER_B || 0),
          r.cases_reviewed_by_role?.REVIEWER_C || 0,
          r.active_assignments,
          r.account_status
        ])}
        actions={(r) => (
          <button className="a-link" onClick={() => setSelectedUpn(r[1])}>
            Inspect workload
          </button>
        )}
      />
    </Page>
  );
}

/* =============================================
   4. COMMITTEE ASSIGNMENTS COMPONENT
   ============================================= */
function CommitteeAssignments() {
  const [rows, setRows] = useState([]);
  const [users, setUsers] = useState([]);
  const [msg, setMsg] = useState('');
  const [auditModal, setAuditModal] = useState({ isOpen: false, title: '', actionFn: null });

  const load = () => Promise.all([
    fetch('/api/auth/committee-assignments', { credentials: 'include' }).then(r => r.ok ? r.json() : { items: [] }),
    listUsers({ role: 'CHAIRPERSON', page_size: 100 })
  ]).then(([a, u]) => {
    setRows(a.items || []);
    setUsers(u.items || []);
  }).catch(e => setMsg(e.message));

  useEffect(() => { load(); }, []);

  const requestAuditAction = (title, actionFn) => {
    setAuditModal({
      isOpen: true,
      title,
      actionLabel: title,
      defaultReason: 'Governance roster adjustment per trial committee charter',
      actionFn
    });
  };

  const handleAuditConfirm = async (reason) => {
    if (!auditModal.actionFn) return;
    try {
      await auditModal.actionFn(reason);
      setMsg(`${auditModal.title} completed.`);
      setAuditModal({ isOpen: false, title: '', actionFn: null });
      load();
    } catch (e) {
      setMsg('Error: ' + e.message);
      setAuditModal({ isOpen: false, title: '', actionFn: null });
    }
  };

  const assignChair = (u) => {
    requestAuditAction(
      `Assign Chairperson Role: ${u.display_name}`,
      async (why) => {
        const res = await fetch(`/api/auth/users/${u.id}/committee-assignment`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: why, committee_name: 'PROTECT-Africa Committee' })
        });
        if (!res.ok) {
          const body = await res.json();
          throw new Error(body.detail || 'Assignment failed');
        }
      }
    );
  };

  const deactivate = (row) => {
    requestAuditAction(
      `Deactivate Chairperson assignment for ${row.email}`,
      async (why) => {
        const res = await fetch(`/api/auth/committee-assignments/${row.id}/deactivate`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: why })
        });
        if (!res.ok) {
          const body = await res.json();
          throw new Error(body.detail || 'Deactivation failed');
        }
      }
    );
  };

  const tableRows = rows.map(r => [
    r.display_name || r.email || '—',
    r.email || '—',
    r.assignment_type,
    r.committee_name || '—',
    r.is_active ? 'Active' : 'Inactive',
    r.expires_at ? new Date(r.expires_at).toLocaleDateString() : 'No expiry',
    r.assigned_at ? new Date(r.assigned_at).toLocaleString() : '—',
    r.id
  ]);

  const unassignedChairs = users.filter(u => !rows.some(r => r.email === u.email && r.is_active));

  return (
    <Page title="Committee Assignments" desc="Manage active chairperson committee assignments. Assignments gate access to the Chairperson Portal.">
      <Notice kind="warn" title="Governance requirement">
        Only physicians with the verified CHAIRPERSON credential can be assigned. Deactivations take effect immediately and are logged to the 21 CFR Part 11 audit trail.
      </Notice>

      {msg && <div className={msg.startsWith('Error') ? 'a-notice danger' : 'a-success'} role="status">{msg}</div>}

      <AuditReasonModal
        isOpen={auditModal.isOpen}
        title={auditModal.title}
        actionLabel={auditModal.actionLabel}
        defaultReason={auditModal.defaultReason}
        onConfirm={handleAuditConfirm}
        onCancel={() => setAuditModal({ isOpen: false, title: '', actionFn: null })}
      />

      {unassignedChairs.length > 0 && (
        <section className="a-panel" style={{ marginBottom: '16px' }}>
          <h2><Icon.UserPlus size={16} color="var(--admin-orange)" /> Unassigned Chairperson Credentials</h2>
          <p style={{ fontSize: '12px', color: '#64748b', marginBottom: '10px' }}>
            The following CHAIRPERSON accounts are verified but do not currently hold an active committee assignment.
          </p>
          {unassignedChairs.map(u => (
            <div key={u.id} style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px', background: '#f8fafc', padding: '8px 12px', borderRadius: '4px', border: '1px solid var(--admin-border-subtle)' }}>
              <span style={{ flex: 1, fontSize: '13px' }}>
                <strong>{u.display_name}</strong> <small style={{ color: '#64748b' }}>({u.email})</small>
              </span>
              <button className="a-primary" onClick={() => assignChair(u)} style={{ fontSize: '12px', padding: '4px 10px' }}>
                <Icon.UserCog size={13} /> Assign Chair
              </button>
            </div>
          ))}
        </section>
      )}

      <Table
        caption="Committee assignment register"
        columns={['Name', 'Email', 'Type', 'Committee', 'Status', 'Expires', 'Assigned at']}
        rows={tableRows.map(r => r.slice(0, 7))}
        actions={(r) => {
          const found = rows.find(x => x.email === r[1] && x.assignment_type === r[2]);
          return found && found.is_active ? (
            <button
              onClick={() => deactivate(found)}
              style={{ color: '#dc2626', fontWeight: 600, fontSize: '12px', background: 'none', border: '1px solid #dc2626', borderRadius: '4px', padding: '3px 8px', cursor: 'pointer' }}
            >
              Deactivate
            </button>
          ) : (
            <span style={{ color: '#64748b', fontSize: '12px' }}>Inactive</span>
          );
        }}
      />
    </Page>
  );
}

/* =============================================
   5. TRAINING & COI COMPONENT (REPLACING UNFUNCTIONAL TAB)
   ============================================= */
function TrainingAndCoi() {
  const [list, setList] = useState(data.training);
  const [msg, setMsg] = useState('');
  const [filterRole, setFilterRole] = useState('');

  const currentCount = list.filter(x => x.status === 'Current').length;
  const expiringCount = list.filter(x => x.status === 'Expiring Soon').length;
  const incompleteCount = list.filter(x => x.status === 'Incomplete').length;

  const handleVerifyCert = (email) => {
    setList(prev => prev.map(item => {
      if (item.email === email) {
        return { ...item, status: 'Current', gcpExpiry: '22 Sep 2028' };
      }
      return item;
    }));
    setMsg(`Certification verified and updated for ${email}. Audit entry created.`);
  };

  const filtered = filterRole ? list.filter(x => x.role === filterRole) : list;

  return (
    <Page
      title="Training & Conflict of Interest (COI)"
      desc="Good Clinical Practice (ICH-GCP), Protocol, Charter training compliance, and annual COI disclosure tracking."
      action={
        <Primary onClick={() => alert('GCP Compliance Audit Report downloaded for study master file.')}>
          <Icon.Download size={14} /> Export Compliance Report
        </Primary>
      }
    >
      <Notice title="GCP Regulatory Training Compliance Requirement">
        Per ICH-GCP E6(R2) §4.1 and US FDA 21 CFR §312.50, all clinical adjudicators, monitors, and committee members must maintain verified GCP certification and annual COI disclosures prior to participating in outcome determinations.
      </Notice>

      {msg && <div className="a-success" role="status">{msg}</div>}

      <div className="a-metrics">
        <div>
          <strong>{list.length}</strong>
          <span>Total Governed Personnel</span>
        </div>
        <div>
          <strong style={{ color: '#15803d' }}>{currentCount}</strong>
          <span>Compliant (Current)</span>
        </div>
        <div>
          <strong style={{ color: '#b45309' }}>{expiringCount}</strong>
          <span>Expiring Within 60 Days</span>
        </div>
        <div>
          <strong style={{ color: '#b91c1c' }}>{incompleteCount}</strong>
          <span>Incomplete / Action Required</span>
        </div>
      </div>

      <div className="a-toolbar">
        <div>
          <Icon.Search size={14} />
          <input placeholder="Search personnel or study..." onChange={e => {
            const term = e.target.value.toLowerCase();
            dispatchEvent(new CustomEvent('admin-table-filter', { detail: { query: term, status: '' } }));
          }} />
        </div>
        <select value={filterRole} onChange={e => setFilterRole(e.target.value)}>
          <option value="">All Governed Roles</option>
          <option value="ADJUDICATOR">Adjudicators</option>
          <option value="CHAIRPERSON">Chairpersons</option>
          <option value="MONITOR">Monitors</option>
        </select>
        <button type="button" onClick={() => setFilterRole('')}>Reset</button>
      </div>

      <Table
        caption="Personnel training and conflict disclosure register"
        columns={['Name', 'Email', 'Role', 'Assigned Study', 'GCP Certification', 'Protocol & Charter', 'ISSHP Criteria', 'COI Status', 'Status']}
        rows={filtered.map(x => [
          x.name,
          x.email,
          x.role,
          x.study,
          `${x.gcpCert} (Exp: ${x.gcpExpiry})`,
          x.protocolCharter,
          x.isshpCriteria,
          x.coiStatus,
          x.status
        ])}
        actions={(r) => {
          const item = list.find(x => x.email === r[1]);
          if (!item) return null;
          return item.status !== 'Current' ? (
            <button
              className="a-primary"
              style={{ fontSize: '11px', padding: '3px 8px', height: 'auto' }}
              onClick={() => handleVerifyCert(item.email)}
            >
              Verify Certificate
            </button>
          ) : (
            <span style={{ color: '#15803d', fontSize: '11.5px', fontWeight: 600 }}>Verified</span>
          );
        }}
      />
    </Page>
  );
}

/* =============================================
   6. ENDPOINTS & WINDOWS COMPONENT (REPLACING UNFUNCTIONAL TAB)
   ============================================= */
function EndpointsAndWindows() {
  const [activeTab, setActiveTab] = useState('endpoints');

  return (
    <Page
      title="Trial Endpoints & Gestational Windows"
      desc="Authoritative diagnostic definitions under ISSHP guidelines and longitudinal visit timeline specifications."
      action={
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className={activeTab === 'endpoints' ? 'a-primary' : 'a-secondary'}
            onClick={() => setActiveTab('endpoints')}
          >
            <Icon.ShieldCheck size={14} /> Governed Endpoints
          </button>
          <button
            type="button"
            className={activeTab === 'windows' ? 'a-primary' : 'a-secondary'}
            onClick={() => setActiveTab('windows')}
          >
            <Icon.CalendarRange size={14} /> Visit Schedule Windows
          </button>
        </div>
      }
    >
      <Notice title="Diagnostic Standard: ISSHP 2021 / 2022 Criteria">
        All adjudication determinations strictly reference the International Society for the Study of Hypertension in Pregnancy (ISSHP) criteria. Automated rules (DV-01 through DV-30) flag discrepancies against these definitions.
      </Notice>

      {activeTab === 'endpoints' ? (
        <>
          <div className="a-grid2" style={{ marginBottom: '16px' }}>
            <section className="a-panel">
              <h2><Icon.Scale size={16} color="var(--admin-orange)" /> Consensus &amp; Adjudication Thresholds</h2>
              <ul>
                <li><strong>Primary Endpoints (EOPE / LOPE):</strong> Two concordant independent reviewer determinations are required. If discordant, routed to Reviewer C (Arbitrator) or Committee Review.</li>
                <li><strong>Severe Maternal Adverse Outcomes:</strong> Requires full Outcomes Adjudication Committee quorum (minimum 3 of 5 voting members).</li>
                <li><strong>Superimposed PE in Chronic HTN:</strong> Requires evidence of new-onset maternal organ dysfunction or severe hypertension escalation.</li>
              </ul>
            </section>
            <section className="a-panel">
              <h2><Icon.Clock size={16} color="var(--admin-teal)" /> Gestational Window Distinction</h2>
              <ul>
                <li><strong>Early-Onset Pre-eclampsia (EOPE):</strong> Diagnosis confirmed at or prior to <strong>34 weeks, 0 days</strong> gestation.</li>
                <li><strong>Late-Onset Pre-eclampsia (LOPE):</strong> Diagnosis confirmed after <strong>34 weeks, 0 days</strong> gestation up to delivery.</li>
                <li><strong>Postpartum Pre-eclampsia:</strong> New-onset pre-eclampsia presenting up to 6 weeks post-delivery.</li>
              </ul>
            </section>
          </div>

          <Table
            caption="Governed clinical endpoints register"
            columns={['Code', 'Clinical Endpoint', 'Diagnostic Standard', 'Gestational Window', 'Consensus Rule', 'Endpoint Type', 'Status']}
            rows={data.endpoints.map(ep => [
              ep.code,
              ep.name,
              ep.standard,
              ep.window,
              ep.consensus,
              ep.type,
              ep.status
            ])}
          />
        </>
      ) : (
        <Table
          caption="Protocol longitudinal visit windows"
          columns={['Visit', 'Clinical Stage', 'Target GA', 'Permitted Window', 'Mandatory Diagnostic Labs']}
          rows={data.visitWindows.map(w => [
            w.visit,
            w.name,
            w.targetGa,
            w.permittedWindow,
            w.mandatoryLabs
          ])}
        />
      )}
    </Page>
  );
}

/* =============================================
   7. UNITS & TERMINOLOGY COMPONENT (REPLACING UNFUNCTIONAL TAB)
   ============================================= */
function UnitsAndTerminology() {
  const [testAnalyte, setTestAnalyte] = useState('Serum Creatinine');
  const [testVal, setTestVal] = useState('0.8');
  const [calcResult, setCalcResult] = useState('');

  const calculateUnit = () => {
    const num = parseFloat(testVal);
    if (isNaN(num)) {
      setCalcResult('Invalid number entered');
      return;
    }
    if (testAnalyte === 'Serum Creatinine') {
      const umol = (num * 88.4).toFixed(1);
      const isHigh = parseFloat(umol) > 90;
      setCalcResult(`${num} mg/dL = ${umol} µmol/L ${isHigh ? '⚠️ (ABOVE ISSHP 90 µmol/L THRESHOLD)' : '✓ (Normal pregnant range)'}`);
    } else if (testAnalyte === 'Total Bilirubin') {
      const umol = (num * 17.1).toFixed(1);
      setCalcResult(`${num} mg/dL = ${umol} µmol/L (Target range 2–100 µmol/L)`);
    } else if (testAnalyte === 'Estimated Fetal Weight') {
      const g = (num * 1000).toFixed(0);
      setCalcResult(`${num} kg = ${g} grams`);
    } else {
      setCalcResult(`${num} (Standard canonical 1:1 format)`);
    }
  };

  return (
    <Page
      title="Canonical Units & Clinical Terminology"
      desc="Laboratory measurement normalization standards, unit conversion matrices, and physiological range rules."
      action={
        <Primary onClick={() => alert('Terminology validation specification exported.')}>
          <Icon.Download size={14} /> Export Specification
        </Primary>
      }
    >
      <Notice title="Automated Laboratory Normalization">
        Source laboratory values collected across clinical sites (Zimbabwe, South Africa, Nigeria, Ghana) use differing regional units (e.g. mg/dL vs µmol/L). The ingestion engine normalizes all values to the canonical standard before display to adjudicators.
      </Notice>

      {/* Interactive Unit Conversion Tester */}
      <section className="a-panel" style={{ marginBottom: '16px', background: '#f8fafc' }}>
        <h2><Icon.Calculator size={16} color="var(--admin-orange)" /> Interactive Laboratory Unit Normalization Tool</h2>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div>
            <label style={{ display: 'block', fontSize: '11.5px', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>Analyte</label>
            <select
              value={testAnalyte}
              onChange={e => { setTestAnalyte(e.target.value); setCalcResult(''); }}
              style={{ padding: '6px 10px', fontSize: '12px', borderRadius: '4px', border: '1px solid var(--admin-border)' }}
            >
              <option value="Serum Creatinine">Serum Creatinine (mg/dL to µmol/L)</option>
              <option value="Total Bilirubin">Total Bilirubin (mg/dL to µmol/L)</option>
              <option value="Estimated Fetal Weight">Fetal Weight (kg to grams)</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '11.5px', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>Site Reported Value</label>
            <input
              type="number"
              step="0.01"
              value={testVal}
              onChange={e => setTestVal(e.target.value)}
              style={{ padding: '6px 10px', fontSize: '12px', borderRadius: '4px', border: '1px solid var(--admin-border)', width: '130px' }}
            />
          </div>
          <button type="button" onClick={calculateUnit} className="a-primary">
            Convert &amp; Test Threshold
          </button>
        </div>
        {calcResult && (
          <div style={{ marginTop: '10px', padding: '8px 12px', background: '#ffffff', borderRadius: '4px', border: '1px solid var(--admin-border)', fontSize: '12.5px', fontWeight: 600, color: 'var(--admin-navy)' }}>
            <strong>Canonical Output:</strong> {calcResult}
          </div>
        )}
      </section>

      <Table
        caption="Standardized laboratory and clinical parameter matrix"
        columns={['Parameter', 'Canonical Unit', 'Accepted Site Units', 'Conversion Formula', 'Physiological Range', 'ISSHP Validation Rule']}
        rows={data.terminology.map(t => [
          t.parameter,
          t.canonicalUnit,
          t.acceptedUnits,
          t.conversion,
          t.range,
          t.validation
        ])}
      />
    </Page>
  );
}

/* =============================================
   8. CLINICAL DICTIONARIES COMPONENT (REPLACING UNFUNCTIONAL TAB)
   ============================================= */
function ClinicalDictionaries() {
  const [testText, setTestText] = useState('Patient presented with elevated BP. No POC biomarker test was administered.');
  const [scanResult, setScanResult] = useState(null);

  const scanForProhibitedWords = () => {
    const found = data.prohibitedWords.filter(w => testText.toLowerCase().includes(w.toLowerCase()));
    setScanResult({
      checked: true,
      found,
      passed: found.length === 0
    });
  };

  return (
    <Page
      title="Clinical Dictionaries & Blinding Control"
      desc="Governed medical dictionaries, MedDRA versions, WHO Drug Global, and automated blinding token enforcement."
      action={
        <Primary onClick={() => alert('Dictionary sync verified with central terminology service.')}>
          <Icon.RefreshCw size={14} /> Check Updates
        </Primary>
      }
    >
      <Notice kind="danger" title="Strict Blinding Token Enforcement (SOP-ADJ-002)">
        Any textual references to study biomarkers (sFlt-1/PlGF ratio, sEng, POC) or randomized treatment arms (Arm A/B, active, placebo) are programmatically redacted before narrative release to prevent adjudicator unblinding.
      </Notice>

      {/* Interactive Blinding Token Scanner */}
      <section className="a-panel" style={{ marginBottom: '16px' }}>
        <h2><Icon.EyeOff size={16} color="var(--admin-orange)" /> Prohibited Blinding Term Scanner (Demo Verifier)</h2>
        <p style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px' }}>
          Test raw clinical notes or site correspondence to verify that the redaction engine intercepts unblinding tokens.
        </p>
        <textarea
          rows={2}
          value={testText}
          onChange={e => setTestText(e.target.value)}
          style={{ width: '100%', padding: '8px 10px', fontSize: '12px', border: '1px solid var(--admin-border)', borderRadius: '4px', boxSizing: 'border-box' }}
        />
        <div style={{ marginTop: '8px', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button type="button" onClick={scanForProhibitedWords} className="a-primary">
            Scan for Prohibited Tokens
          </button>
          {scanResult && (
            scanResult.passed ? (
              <span className="a-badge ok">✓ Clean: No Prohibited Biomarker Terms Detected</span>
            ) : (
              <span className="a-badge bad">⚠️ Intercepted Tokens: {scanResult.found.join(', ')}</span>
            )
          )}
        </div>
      </section>

      <Table
        caption="Governed clinical classification dictionaries"
        columns={['Code', 'Dictionary Name', 'Governing Authority', 'Current Version', 'Release Date', 'Status', 'Governed Scope']}
        rows={data.dictionaries.map(d => [
          d.code,
          d.name,
          d.authority,
          d.version,
          d.releaseDate,
          d.status,
          d.scope
        ])}
      />
    </Page>
  );
}

/* =============================================
   9. IMPORT CONTRACTS COMPONENT (REPLACING UNFUNCTIONAL TAB)
   ============================================= */
function ImportContracts() {
  const [testResult, setTestResult] = useState('');

  const runTestContract = (name) => {
    setTestResult(`Validated connection to ${name}. Schema version matches RFC 4180 / HL7 FHIR baseline. Zero unblinding fields detected.`);
  };

  return (
    <Page
      title="Data Ingestion Contracts & Source Interfaces"
      desc="Validated integration interfaces, file schemas, payload checksums, and automated quarantine criteria."
      action={
        <Primary onClick={() => alert('New data interface contract wizard opened in demonstration mode.')}>
          <Icon.Plus size={14} /> Register New Interface
        </Primary>
      }
    >
      <Notice title="Automated Data Quality & Quarantine Architecture">
        Inbound clinical datasets from EDC, eSource tablets, central laboratories, and ultrasound machines are validated against strict contracts. Batches with checksum mismatches or prohibited fields are quarantined immediately.
      </Notice>

      {testResult && <div className="a-success" role="status">{testResult}</div>}

      <Table
        caption="Governed source ingestion interfaces"
        columns={['Interface Channel', 'Source System', 'Protocol', 'Data Format', 'Sync Frequency', 'Integrity Checksum', 'Operational Status']}
        rows={data.importContracts.map(c => [
          c.channel,
          c.source,
          c.protocol,
          c.format,
          c.frequency,
          c.checksum,
          c.status
        ])}
        actions={(r) => (
          <button className="a-link" onClick={() => runTestContract(r[0])}>
            Test validation
          </button>
        )}
      />
    </Page>
  );
}

/* =============================================
   10. SOP REFERENCES COMPONENT (REPLACING UNFUNCTIONAL TAB)
   ============================================= */
function SopReferences() {
  const [selectedSop, setSelectedSop] = useState(null);

  const getSopContent = (code) => {
    if (code.includes('AI') || code.includes('SPEC')) return SOP_DOCUMENTS.AGENT_SOP;
    if (code.includes('Charter')) return SOP_DOCUMENTS.OAC_CHARTER;
    if (code.includes('001')) return SOP_DOCUMENTS.SOP_001;
    if (code.includes('002')) return SOP_DOCUMENTS.SOP_002;
    if (code.includes('003')) return SOP_DOCUMENTS.SOP_003;
    if (code.includes('004')) return SOP_DOCUMENTS.SOP_004;
    if (code.includes('005')) return SOP_DOCUMENTS.SOP_005;
    if (code.includes('006')) return SOP_DOCUMENTS.SOP_006;
    return SOP_DOCUMENTS.SOP_001;
  };

  return (
    <Page
      title="Standard Operating Procedures (SOPs) & Charters"
      desc="Governed regulatory procedures, committee charters, blinding protocols, and 21 CFR Part 11 requirements."
      action={
        <Primary onClick={() => alert('SOP audit dossier exported for regulatory review.')}>
          <Icon.Download size={14} /> Export SOP Dossier
        </Primary>
      }
    >
      <Notice title="Controlled Regulatory Documents Repository">
        All trial operations follow these audited Standard Operating Procedures. In accordance with GCP inspection readiness, procedural changes trigger versioning, committee review, and audit logging.
      </Notice>

      {/* Full Document Reader Modal */}
      {selectedSop && (
        <div className="a-modal-overlay" role="dialog" aria-modal="true">
          <div className="a-modal-card" style={{ maxWidth: '720px', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
            <div className="a-modal-header">
              <strong><Icon.BookOpen size={16} /> {selectedSop.title} ({selectedSop.code})</strong>
              <button onClick={() => setSelectedSop(null)}><Icon.X size={16} /></button>
            </div>
            <div className="a-modal-body" style={{ overflowY: 'auto', flex: 1 }}>
              <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--admin-border-subtle)', marginBottom: '14px', fontSize: '12px' }}>
                <div><strong>Version:</strong> {selectedSop.version} | <strong>Effective:</strong> {selectedSop.effectiveDate} | <strong>Review:</strong> {selectedSop.reviewCycle}</div>
                <div style={{ marginTop: '4px' }}><strong>Governed Scope:</strong> {selectedSop.scope}</div>
              </div>
              <pre style={{
                whiteSpace: 'pre-wrap',
                fontFamily: 'Consolas, monospace',
                fontSize: '12px',
                lineHeight: '1.6',
                color: '#1e293b',
                background: '#ffffff',
                padding: '12px',
                border: '1px solid var(--admin-border)',
                borderRadius: '4px'
              }}>
                {selectedSop.fullContent}
              </pre>
            </div>
            <div className="a-modal-footer">
              <button type="button" onClick={() => setSelectedSop(null)} className="a-primary">
                Close Document
              </button>
            </div>
          </div>
        </div>
      )}

      <Table
        caption="Governed trial SOP register"
        columns={['Document Code', 'Document Title', 'Version', 'Effective Date', 'Review Cycle', 'Governed Scope', 'Status']}
        rows={data.sops.map(s => [
          s.code,
          s.title,
          s.version,
          s.effectiveDate,
          s.reviewCycle,
          s.scope,
          s.status
        ])}
        actions={(r) => (
          <button
            className="a-primary"
            style={{ fontSize: '11px', padding: '3px 8px', height: 'auto' }}
            onClick={() => {
              const doc = getSopContent(r[0]);
              const rawSop = data.sops.find(s => s.code === r[0]);
              setSelectedSop({
                ...rawSop,
                fullContent: doc?.content || rawSop?.summary
              });
            }}
          >
            Read SOP
          </button>
        )}
      />
    </Page>
  );
}

/* =============================================
   11. ROLES & PERMISSIONS COMPONENT
   ============================================= */
function Roles() {
  return (
    <Page
      title="Roles and Permissions"
      desc="Versioned roles, delegated authority and separation-of-duties controls."
      action={<Primary><Icon.Plus size={14} /> Draft custom role</Primary>}
    >
      <Notice kind="warn" title="Separation-of-Duties Enforcement">
        Technical Admin + Adjudicator; Monitor/QC + Reviewer; Reviewer + Release Approver; User Admin + Self-Approver; and Committee member + Site investigator combinations are strictly prohibited or flagged.
      </Notice>
      <Table
        caption="Administrative role register"
        columns={['Role', 'Purpose', 'Administrative scope', 'Clinical boundary']}
        rows={[
          ['Technical Administrator', 'Platform configuration and identity', 'Users, integrations, audit', 'No case content'],
          ['Clinical Operations Administrator', 'Study and content configuration', 'Studies, sites, rules, mappings, forms', 'No adjudication'],
          ['QA / Auditor', 'Independent review and approval', 'Audit, reports, approvals', 'Read-only otherwise'],
          ['Governance Reviewer', 'Governance oversight', 'Roles, studies, rules, audit', 'Read-only'],
          ['Access Reviewer', 'Periodic certification', 'Users and access reviews', 'No self-approval']
        ]}
      />
      <Table
        caption="Portal permission matrix"
        columns={['Capability', 'Technical Admin', 'Clinical Ops', 'QA / Auditor', 'Governance', 'Access Reviewer']}
        rows={[
          ['Admin Portal Access', 'Manage', 'Manage', 'Read/approve', 'Read', 'Review'],
          ['Blinded Case Content', 'Denied', 'Denied', 'Denied', 'Denied', 'Denied'],
          ['User Administration', 'Manage', 'Read', 'Read', 'Read', 'Review'],
          ['Rules / Mappings / Forms', 'Read', 'Draft/manage', 'Approve', 'Read', 'None'],
          ['Clinical Decisions', 'Denied', 'Denied', 'Denied', 'Denied', 'Denied']
        ]}
      />
    </Page>
  );
}

/* =============================================
   12. GENERIC REGISTER COMPONENT (STUDIES, SITES, RULES, ETC.)
   ============================================= */
function Register({ type }) {
  let cfg = {
    studies: ['Studies', 'Versioned study configuration. Active records cannot be edited in place.', ['Study code', 'Study name', 'Protocol', 'Countries', 'Status', 'Version', 'Active DV rules', 'Active mapping'], data.studies],
    sites: ['Sites', 'Only approved blinded display names are exposed to adjudicators.', ['Site code', 'Blinded display name', 'Country', 'Study', 'Status', 'Import identifier', 'Allowed sources'], data.sites],
    rules: ['DV Rule Versions', 'DV-01 through DV-30; the Python engine remains authoritative.', ['DV identifier', 'Name', 'Purpose', 'Version', 'Effective', 'Status', 'Approvals', 'Tests'], data.rules],
    mappings: ['Canonical Field Mappings', 'Versioned source-to-canonical contracts and blinding classifications.', ['Source system', 'Source field', 'Canonical field', 'Data type', 'Unit', 'Requirement', 'Study', 'Version', 'Status', 'Blinding'], data.mappings],
    forms: ['Forms and Templates', 'Used form versions are never overwritten.', ['Form code', 'Name', 'Version', 'Study applicability', 'Status', 'Supporting SOP'], data.forms],
    integrations: ['Integrations', 'Connection metadata only; credentials are never displayed.', ['Name', 'Type', 'Environment', 'Status', 'Last connection', 'Credential status', 'Enabled'], data.integrations]
  }[type];

  if (!cfg) return null;

  return (
    <Page
      title={cfg[0]}
      desc={cfg[1]}
      action={<Primary title={`Create new ${cfg[0]} draft`}><Icon.Plus size={14} /> New controlled draft</Primary>}
    >
      {type === 'rules' && (
        <Notice kind="warn" title="Immutable Active Rules (21 CFR Part 11)">
          Activation requires passing automated test suites plus clinical and QA approval. Browser-entered executable code is strictly prohibited.
        </Notice>
      )}
      {type === 'mappings' && (
        <Notice kind="danger" title="Permanent Prohibited-Field Registry">
          sFlt-1, PlGF, sEng, biomarker concentrations, POC results, treatment allocation, and configured unblinding fields can never map to adjudicator-facing data.
        </Notice>
      )}
      <Toolbar>
        <button onClick={() => downloadCsv(type, cfg[2], cfg[3])}>Export register</button>
      </Toolbar>
      <Table
        caption={`Governed ${cfg[0].toLowerCase()} register`}
        columns={cfg[2]}
        rows={cfg[3]}
        actions={type === 'integrations' ? (r) => (
          <button className="a-link" onClick={() => alert(`${r[0]} connection test: ${r[3] === 'Healthy' ? 'Connection Successful' : 'Synthetic Warning Verified'}`)}>
            Test connection
          </button>
        ) : null}
      />
      <p className="a-foot">Active or historically used records are immutable; all changes create a reasoned successor version and audit event.</p>
    </Page>
  );
}

/* =============================================
   13. WORKFLOW CONFIGURATION COMPONENT
   ============================================= */
function Workflow() {
  return (
    <Page title="Workflow Configuration" desc="Validated states, transitions, authority, signatures, gates and release requirements." action={<Primary>New workflow draft</Primary>}>
      <div className="a-flow">
        {data.workflow.map((x, i) => (
          <React.Fragment key={x}>
            <span><b>{i + 1}</b>{x}</span>
            {i < data.workflow.length - 1 && <Icon.ChevronRight size={14} />}
          </React.Fragment>
        ))}
      </div>
      <div className="a-grid3">
        {[
          ['Validation controls', ['No import-to-adjudication shortcut', 'Final QC required before release', 'No modification after lock']],
          ['Committee controls', ['Minimum quorum: 3 of 5 voting members', 'Chair signature required', 'Recused member excluded']],
          ['Controlled reopen', ['Reason and approval required', 'Original history preserved', 'Immutable audit event created']]
        ].map(([h, x]) => (
          <section className="a-panel" key={h}>
            <h2>{h}</h2>
            <ul>{x.map(y => <li key={y}>{y}</li>)}</ul>
          </section>
        ))}
      </div>
    </Page>
  );
}

/* =============================================
   14. AUDIT TRAIL COMPONENT
   ============================================= */
function Audit() {
  const cols = ['Event ID', 'Timestamp', 'Acting user', 'Role', 'Action', 'Entity', 'Reason', 'Outcome'];
  return (
    <Page
      title="Audit Trail"
      desc="Immutable administrative security and configuration history."
      action={<button className="a-secondary" onClick={() => downloadCsv('administrative-audit-trail', cols, data.audits)}>Controlled export</button>}
    >
      <Toolbar />
      <Table caption="Synthetic immutable audit events" columns={cols} rows={data.audits} />
      <p className="a-foot">Audit events cannot be edited or deleted. Participant filters require separate specific authority.</p>
    </Page>
  );
}

/* =============================================
   15. ACCESS REVIEWS COMPONENT
   ============================================= */
function Reviews() {
  return (
    <Page title="Access Reviews" desc="Periodic certification of portal, study and site access." action={<Primary>Generate campaign</Primary>}>
      <div className="a-grid2">
        <section className="a-panel">
          <h2>Q3 2026 Admin Portal Review</h2>
          <p>6 of 7 identities certified · Due 17 Oct 2026</p>
          <progress value="6" max="7" style={{ width: '100%', height: '8px', margin: '8px 0' }}>6 of 7</progress>
          <p><Badge>Open</Badge></p>
        </section>
        <section className="a-panel">
          <h2>Automatic flags</h2>
          <ul>
            <li>1 access expiry within 60 days (Dr. Miriam Ndlovu)</li>
            <li>1 incomplete training / COI (Lindiwe Dube)</li>
            <li>0 inactive identities</li>
            <li>No unauthorized closed-study access</li>
          </ul>
        </section>
      </div>
      <Table
        caption="Review population"
        columns={['User', 'Role', 'Scope', 'Training / COI', 'Last login', 'Flag', 'Decision']}
        rows={[
          ['Tariro Moyo', 'Technical Administrator', 'Platform', 'Current / Current', 'Today', 'High privilege', 'Confirm'],
          ['Amara Okafor', 'Clinical Ops Admin', 'Two studies', 'Current / Current', 'Yesterday', 'None', 'Confirmed'],
          ['Dr. Miriam Ndlovu', 'Adjudicator', 'PROTECT-Africa', 'Expiring Soon / Recused Site', '3 days ago', 'Site Recusal', 'Confirmed'],
          ['Lindiwe Dube', 'Access requested', 'PROTECT-Africa', 'Incomplete / Pending', 'Never', 'Missing GCP', 'Block']
        ]}
      />
    </Page>
  );
}

/* =============================================
   16. REPORTS COMPONENT
   ============================================= */
function Reports() {
  let r = [
    'User access register',
    'Role-permission matrix',
    'Study configuration register',
    'Active rule versions',
    'Active mapping versions',
    'Form/template register',
    'Access-review status',
    'Training compliance',
    'Configuration changes',
    'Integration incidents',
    'Import failures',
    'Audit-event summary'
  ];

  return (
    <Page title="Administrative Reports" desc="Controlled exports constrained by role and delegated study scope.">
      <div className="a-reports">
        {r.map(x => (
          <button
            key={x}
            onClick={() => downloadCsv(x.toLowerCase().replaceAll(' ', '-'), ['Report', 'Environment', 'Scope', 'Generated'], [[x, 'DEMO', 'Delegated studies only', new Date().toISOString()]])}
          >
            <Icon.FileSpreadsheet />
            <strong>{x}</strong>
            <small>Demo data · scoped export</small>
            <Icon.Download size={14} />
          </button>
        ))}
      </div>
    </Page>
  );
}

/* =============================================
   17. ENVIRONMENT & HEALTH COMPONENT
   ============================================= */
function Health() {
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [auditModal, setAuditModal] = useState({ isOpen: false, title: '', actionFn: null });

  const requestReset = (title, actionFn) => {
    setAuditModal({
      isOpen: true,
      title,
      actionLabel: title,
      defaultReason: 'Periodic baseline reset for system verification',
      actionFn
    });
  };

  const handleAuditConfirm = async (reason) => {
    if (!auditModal.actionFn) return;
    setBusy(true);
    setMsg('');
    try {
      await auditModal.actionFn(reason);
      setAuditModal({ isOpen: false, title: '', actionFn: null });
    } catch (e) {
      setMsg('Error: ' + e.message);
      setAuditModal({ isOpen: false, title: '', actionFn: null });
    } finally {
      setBusy(false);
    }
  };

  const doResetFull = (reason) => {
    return fetch('/api/admin/demo/reset-environment', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason })
    }).then(async r => {
      const body = await r.json();
      if (!r.ok) throw new Error(body.detail || 'Reset failed');
      const purged = body.result?.total_purged || 0;
      const cases = body.result?.cases_reseeded?.participants || 0;
      const visits = body.result?.cases_reseeded?.visits || 0;
      setMsg(`Full demo environment reset complete — ${purged} test records purged, ${cases} baseline cases (${visits} visits) re-seeded, accounts refreshed.`);
    });
  };

  const doResetScenarios = (reason) => {
    return fetch('/api/admin/demo/reset-all', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason })
    }).then(async r => {
      const body = await r.json();
      if (!r.ok) throw new Error(body.detail || 'Reset failed');
      setMsg('Scoped reset complete — baseline demo cases and accounts refreshed.');
    });
  };

  return (
    <Page title="Environment and Health" desc="Platform health, database status and demonstration environment controls.">
      <Notice title="Demonstration environment">All data below is synthetic. Reset does not affect any production system.</Notice>

      <AuditReasonModal
        isOpen={auditModal.isOpen}
        title={auditModal.title}
        actionLabel={auditModal.actionLabel}
        defaultReason={auditModal.defaultReason}
        onConfirm={handleAuditConfirm}
        onCancel={() => setAuditModal({ isOpen: false, title: '', actionFn: null })}
      />

      <div className="a-grid2">
        <section className="a-panel">
          <h2><Icon.Database size={16} color="var(--admin-teal)" /> Database / migration</h2>
          <dl>
            <div><dt>Mode</dt><dd>SQLite (demo) or PostgreSQL (production)</dd></div>
            <div><dt>Auth tables</dt><dd>portal_users · auth_sessions · auth_audit_events</dd></div>
            <div><dt>Longitudinal tables</dt><dd>rt_import_batches · longitudinal_participants · visit_instances</dd></div>
            <div><dt>Adjudication tables</dt><dd>participants · adjudication_records · committee_decisions</dd></div>
          </dl>
        </section>
        <section className="a-panel">
          <h2><Icon.RotateCcw size={16} color="var(--admin-orange)" /> Demo Environment Reset Controls</h2>
          <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '12px' }}>
            Restore the demonstration environment to a clean, deterministic baseline or wipe custom test batches.
          </p>
          {msg && <div className={msg.startsWith('Error') ? 'a-notice danger' : 'a-success'} role="status" style={{ marginBottom: '14px' }}>{msg}</div>}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <button
              onClick={() => requestReset('Reset & Re-seed Full Demo Environment', doResetFull)}
              disabled={busy}
              style={{ background: '#b91c1c', color: '#fff', border: 'none', borderRadius: '6px', padding: '10px 18px', fontWeight: 700, fontSize: '13px', cursor: busy ? 'wait' : 'pointer', opacity: busy ? 0.7 : 1, display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Icon.RotateCcw size={15} />{busy ? 'Resetting…' : 'Reset & Re-seed Full Demo Environment'}
            </button>
            <button
              onClick={() => requestReset('Clear Scenario Imports Only', doResetScenarios)}
              disabled={busy}
              style={{ background: '#f1f5f9', color: '#334155', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '8px 16px', fontWeight: 600, fontSize: '13px', cursor: busy ? 'wait' : 'pointer', opacity: busy ? 0.7 : 1, display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Icon.Trash2 size={14} />{busy ? 'Resetting…' : 'Clear Scenario Imports Only'}
            </button>
          </div>
          <p style={{ fontSize: '11.5px', color: '#64748b', marginTop: '12px' }}>
            Requires admin role · Part 11 audited · Restores standard demo password (ACRN@2026)
          </p>
        </section>
      </div>
    </Page>
  );
}

/* =============================================
   18. MAIN ADMIN PORTAL WRAPPER & ROUTER
   ============================================= */
export default function AdminPortal({ user, onLogout, isEmbedded }) {
  const [path, setPath] = useState(location.pathname.startsWith('/admin') ? location.pathname : '/admin');
  const [collapsed, setCollapsed] = useState(false);
  const [dash, setDash] = useState(DEFAULT_DASH);

  useEffect(() => {
    let pop = () => setPath(location.pathname);
    let navEvent = (e) => setPath(e.detail);
    addEventListener('popstate', pop);
    addEventListener('app-nav', navEvent);
    fetch('/api/admin/dashboard', { credentials: 'include' })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(setDash)
      .catch(() => setDash(x => ({ ...x, api: 'Offline demo data', database: 'Local synthetic fixtures' })));
    return () => {
      removeEventListener('popstate', pop);
      removeEventListener('app-nav', navEvent);
    };
  }, []);

  let go = p => {
    history.pushState({}, '', p);
    setPath(p);
    dispatchEvent(new CustomEvent('app-nav', { detail: p }));
  };

  // Route Dispatcher (ALL 22 ROUTES FULLY FUNCTIONAL)
  let view = 
    path === '/admin' ? <Dashboard dash={dash} /> :
    path === '/admin/users' ? <Users /> :
    path === '/admin/adjudicator-profiles' ? <AdjudicatorProfiles /> :
    path === '/admin/committee-assignments' ? <CommitteeAssignments /> :
    path === '/admin/access' ? <Roles /> :
    path === '/admin/access-reviews' ? <Reviews /> :
    path === '/admin/training' ? <TrainingAndCoi /> :
    path === '/admin/studies' ? <Register type="studies" /> :
    path === '/admin/sites' ? <Register type="sites" /> :
    path === '/admin/endpoints' ? <EndpointsAndWindows /> :
    path === '/admin/workflows' ? <Workflow /> :
    path === '/admin/mappings' ? <Register type="mappings" /> :
    path === '/admin/terminology' ? <UnitsAndTerminology /> :
    path === '/admin/dictionaries' ? <ClinicalDictionaries /> :
    path === '/admin/import-contracts' ? <ImportContracts /> :
    path === '/admin/rules' ? <Register type="rules" /> :
    path === '/admin/forms' ? <Register type="forms" /> :
    path === '/admin/sops' ? <SopReferences /> :
    path === '/admin/integrations' ? <Register type="integrations" /> :
    path === '/admin/audit' ? <Audit /> :
    path === '/admin/reports' ? <Reports /> :
    path === '/admin/health' ? <Health /> :
    <Dashboard dash={dash} />;

  if (isEmbedded) return <>{view}</>;

  return (
    <div className="admin-app">
      <header className="a-header">
        <div className="a-brand">
          <span><img src="/acrn-logo.png" alt="Africa Clinical Research Network" /></span>
          <div>
            <strong>ACRN Adjudication Platform</strong>
            <small>Administration Portal</small>
          </div>
        </div>
        <div className="a-boundary">
          <Icon.Shield size={14} /> Operational metadata only · clinical case access disabled
        </div>
        <div className="a-user">
          <div>
            <strong>{user?.name || 'Administrator'}</strong>
            <small>{user?.role || 'CLINICAL_OPS_ADMIN'}</small>
          </div>
          <Badge>DEMO IDENTITY</Badge>
          <button onClick={onLogout} aria-label="Sign out" title="Sign out">
            <Icon.LogOut size={16} />
          </button>
        </div>
      </header>

      <div className="a-body">
        <aside className={'a-nav ' + (collapsed ? 'collapsed' : '')}>
          <button className="a-collapse" onClick={() => setCollapsed(!collapsed)} aria-label="Toggle navigation">
            <span>ADMINISTRATION</span>
            {collapsed ? <Icon.ChevronsRight size={14} /> : <Icon.ChevronsLeft size={14} />}
          </button>
          {NAV.map(([g, x]) => (
            <section key={g}>
              <h2>{g}</h2>
              {x.map(([p, l, ic]) => {
                let C = Icon[ic] || Icon.Circle;
                const isActive = path === p || (p === '/admin/adjudicator-profiles' && path.startsWith('/admin/adjudicator-profiles'));
                return (
                  <button
                    key={p}
                    title={l}
                    className={isActive ? 'active' : ''}
                    onClick={() => go(p)}
                  >
                    <C size={15} />
                    <span>{l}</span>
                  </button>
                );
              })}
            </section>
          ))}
          <div className="a-env">
            <Icon.Database size={15} />
            <span>
              DEMO DATA<br />
              <small>{dash.api}</small>
            </span>
          </div>
        </aside>

        <main className="a-main">
          <div className="a-crumb">
            <button onClick={() => go('/admin')}>Admin</button>
            <Icon.ChevronRight size={12} />
            <span>{TITLES[path] || 'Dashboard'}</span>
          </div>
          {view}
        </main>
      </div>
    </div>
  );
}
