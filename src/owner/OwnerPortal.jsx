import React, { useState, useEffect, useMemo } from 'react';
import * as Icon from 'lucide-react';
import '../admin/admin.css';

// Reusable architectural UI components identical to AdminPortal
function Badge({ children }) {
  let s = String(children).toLowerCase();
  let c = s.includes('active') || s.includes('healthy') || s.includes('passed') || s.includes('success') || s.includes('concordant') ? 'ok' :
          s.includes('pending') || s.includes('warning') || s.includes('query') || s.includes('discordant') ? 'warn' :
          s.includes('failed') || s.includes('missing') ? 'bad' : '';
  return <span className={'a-badge ' + c}>{children}</span>;
}

function Table({ caption, columns, rows }) {
  const [filter, setFilter] = useState({ query: '', status: '' });
  
  useEffect(() => {
    const f = e => setFilter(e.detail);
    addEventListener('owner-table-filter', f);
    return () => removeEventListener('owner-table-filter', f);
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
          <tr>{columns.map(c => <th scope="col" key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {shown.map((r, i) => (
            <tr key={i}>
              {r.map((v, j) => <td key={j}>{/status|outcome|flag|determination|result/i.test(columns[j]) ? <Badge>{v}</Badge> : v}</td>)}
            </tr>
          ))}
          {!shown.length && <tr><td colSpan={columns.length}>No demonstration records match the current filters.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function Page({ title, desc, action, children }) {
  return (
    <>
      <div className="a-page-head">
        <div><h1>{title}</h1><p>{desc}</p></div>
        {action}
      </div>
      {children}
    </>
  );
}

function Toolbar({ children }) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');
  const apply = (q, s) => dispatchEvent(new CustomEvent('owner-table-filter', { detail: { query: q, status: s } }));
  return (
    <div className="a-toolbar">
      <label className="sr-only" htmlFor="owner-search">Search records</label>
      <div>
        <Icon.Search size={14} />
        <input id="owner-search" value={query} onChange={e => { setQuery(e.target.value); apply(e.target.value, status); }} placeholder="Search or filter records…" />
      </div>
      <select aria-label="Status filter" value={status} onChange={e => { setStatus(e.target.value); apply(query, e.target.value); }}>
        <option value="">All statuses</option>
        <option>Success</option>
        <option>Warning</option>
        <option>Pending</option>
        <option>Discordant</option>
      </select>
      {children}
      <button type="button" onClick={() => { setQuery(''); setStatus(''); apply('', ''); }}>Clear filters</button>
    </div>
  );
}

function Notice({ kind = 'info', title, children }) {
  return (
    <div className={'a-notice ' + kind}>
      <Icon.ShieldAlert size={17} />
      <div><strong>{title}</strong><span>{children}</span></div>
    </div>
  );
}

// Navigation Structure
const NAV = [
  ['COMMAND CENTER', [['/owner', 'Executive Overview', 'LayoutDashboard']]],
  ['ADMINISTRATION', [['/admin/audit', 'Global Audit Trail', 'ScrollText'], ['/admin/users', 'Platform Users', 'Users'], ['/admin/roles', 'Permissions', 'ShieldCheck'], ['/admin/health', 'System Health', 'Activity']]],
  ['MONITORING & QC', [['/monitor/dashboard', 'Operational Overview', 'Activity'], ['/monitor/issues', 'Data Queries', 'AlertTriangle'], ['/monitor/assignments', 'Adjudicator Assignments', 'Users']]],
  ['ADJUDICATION', [['/adjudicator', 'Adjudicator Workbench', 'Stethoscope']]],
  ['CHAIRPERSON', [['/chairperson', 'Consensus Queue', 'Users'], ['/chairperson/meetings', 'Committee Meetings', 'Calendar']]]
];

const TITLES = Object.fromEntries(NAV.flatMap(([, x]) => x.map(([p, l]) => [p, l])));

import AdminPortal from '../admin/AdminPortal';
import MonitorPortal from '../monitor/MonitorPortal';
import ChairpersonPortal from '../chairperson/ChairpersonPortal';



// Views
function Dashboard({ stats }) {
  return (
    <Page title="Executive Overview" desc="Cross-platform command center displaying live system aggregation.">
      <Notice title="Global Visibility Active">You are operating as Owner. Platform-wide operations are accessible.</Notice>
      <div className="a-metrics">
        {[
          ['Active Studies', stats?.ops?.summary?.total_subjects || 12],
          ['Pending QC', stats?.ops?.summary?.pending_qc || 5],
          ['Active Adjudicators', 4],
          ['Completion Rate', '85%'],
          ['Consensus Queue', 2],
          ['System Health', 'Healthy']
        ].map(([l, v]) => (
          <div key={l}><strong>{v}</strong><span>{l}</span></div>
        ))}
      </div>
      <div className="a-grid2">
        <section className="a-panel">
          <h2>Active Action Queues</h2>
          <button className="a-queue"><span>Pending User Approvals</span><Badge>1 open</Badge><Icon.ChevronRight size={14}/></button>
          <button className="a-queue"><span>Data Queries (Missing Labs)</span><Badge>2 open</Badge><Icon.ChevronRight size={14}/></button>
          <button className="a-queue"><span>Discordant Case Arbitration</span><Badge>1 pending</Badge><Icon.ChevronRight size={14}/></button>
        </section>
        <section className="a-panel">
          <h2>Environment Configuration</h2>
          <dl>
            <div><dt>Environment</dt><dd><Badge>DEMO / OFFLINE</Badge></dd></div>
            <div><dt>Database</dt><dd>SQLite (Fallback)</dd></div>
            <div><dt>Owner Privileges</dt><dd><Badge>Active</Badge></dd></div>
            <div><dt>Blinded Access</dt><dd><Badge>Authorized</Badge></dd></div>
          </dl>
        </section>
      </div>
    </Page>
  );
}

function AuditView() {
  const rows = [
    ['EVT-9092', 'Just now', 'System', 'SYSTEM', 'DB_BACKUP_COMPLETED', 'Backup', 'Routine scheduled backup', 'Success'],
    ['EVT-9091', '10 mins ago', 'Dr. Dube', 'ADJUDICATOR', 'CASE_SIGNED', 'Participant 104-B', 'Adjudication submission', 'Success'],
    ['EVT-9090', '1 hr ago', 'Amara Okafor', 'CLINICAL_OPS', 'MAPPING_UPDATED', 'Protocol v1.4', 'Added secondary endpoint', 'Warning'],
    ['EVT-9089', '2 hrs ago', 'IT Systems Admin', 'TECHNICAL_ADMIN', 'USER_PROVISIONED', 'New Account', 'Onboarded Dr. Osei', 'Success']
  ];
  return (
    <Page title="Global Audit Trail" desc="Immutable read-only view of all cross-platform events.">
      <Toolbar />
      <Table caption="System-wide audit events" columns={['Event ID','Timestamp','Acting user','Role','Action','Entity','Reason','Outcome']} rows={rows} />
    </Page>
  );
}

function MonitorIssuesView() {
  const [rows, setRows] = useState([]);
  
  useEffect(() => {
    const saved = JSON.parse(localStorage.getItem('data_queries') || '[]');
    const queryRows = saved.map(q => [
      'Blinded Site', 
      q.caseId, 
      q.queryCategory, 
      'High', 
      q.status, 
      new Date(q.timestamp).toLocaleString()
    ]);
    
    const defaultRows = [
      ['Site 01', 'SUBJ-104-B', 'Missing Visit 2 Lab Result', 'High', 'Pending Monitor Review', '2 hours ago'],
      ['Site 02', 'SUBJ-209-A', 'Protocol Deviation (Window Exceeded)', 'Medium', 'Pending Query Response', '1 day ago'],
      ['Site 01', 'SUBJ-099-C', 'Missing Source Document', 'High', 'Pending Monitor Review', '2 days ago']
    ];
    
    setRows([...queryRows, ...defaultRows]);
  }, []);

  return (
    <Page title="Data Queries & Issues" desc="Live feed of data quality checks and source document queries.">
      <Toolbar />
      <Table caption="Active Data Queries" columns={['Site','Subject','Issue Type','Severity','Status','Flagged']} rows={rows} />
    </Page>
  );
}

function DeterminationsView() {
  const rows = [
    ['Case #827', 'Dr. Dube (A)', 'Visit 5', 'Concordant', 'Submitted', 'Just now'],
    ['Case #828', 'Dr. Okafor (B)', 'Visit 2', 'Discordant', 'Submitted', '45 mins ago'],
    ['Case #911', 'Dr. Smith (C)', 'Visit 5', 'Pending Review', 'In Progress', '1 hr ago'],
    ['Case #827', 'Dr. Smith (C)', 'Visit 5', 'Concordant', 'Submitted', '2 hrs ago']
  ];
  return (
    <Page title="Recent Determinations" desc="Live feed of adjudicator workbench submissions.">
      <Toolbar />
      <Table caption="Adjudication Stream" columns={['Case','Reviewer','Visit','Determination','Status','Timestamp']} rows={rows} />
    </Page>
  );
}

function ConsensusView() {
  const rows = [
    ['Case #828', 'Dr. Dube (A) vs Dr. Okafor (B)', 'PE diagnosis divergent', 'Pending Arbitration', 'High', 'Just now'],
    ['Case #904', 'Dr. Smith (A) vs Dr. Osei (B)', 'Secondary endpoint mismatch', 'Pending Discussion', 'Medium', '1 day ago']
  ];
  return (
    <Page title="Consensus Queue" desc="Discordant cases awaiting chairperson arbitration.">
      <Toolbar />
      <Table caption="Arbitration Queue" columns={['Case','Reviewers','Divergence Reason','Status','Priority','Flagged']} rows={rows} />
    </Page>
  );
}


export default function OwnerPortal({ user, onLogout }) {
  const [path, setPath] = useState(location.pathname);
  const [collapsed, setCollapsed] = useState(false);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    let pop = () => setPath(location.pathname);
    let navEvent = (e) => setPath(e.detail);
    addEventListener('popstate', pop);
    addEventListener('app-nav', navEvent);
    
    // Fetch live dashboard ops stats
    Promise.all([
      fetch('/api/monitor/operational-dashboard', { credentials: 'include' }).then(r => r.ok ? r.json() : {}),
      fetch('/api/realtime/progress', { credentials: 'include' }).then(r => r.ok ? r.json() : {})
    ]).then(([ops, prog]) => {
      setStats({ ops, prog });
    }).catch(console.error);

    return () => {
      removeEventListener('popstate', pop);
      removeEventListener('app-nav', navEvent);
    };
  }, []);

  const go = (p) => {
    history.pushState({}, '', p);
    setPath(p);
    dispatchEvent(new CustomEvent('app-nav', { detail: p }));
  };

  const renderView = () => {
    const ReadOnlyBanner = ({ portalName }) => (
      <div style={{
        background: 'linear-gradient(135deg, #1e3a5f 0%, #0f2444 100%)',
        border: '1px solid #2d5986',
        borderRadius: '8px',
        padding: '10px 16px',
        marginBottom: '16px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        fontSize: '13px',
        color: '#93c5fd',
      }}>
        <Icon.Eye size={16} style={{ flexShrink: 0, color: '#60a5fa' }} />
        <span>
          <strong style={{ color: '#bfdbfe' }}>Observer Mode — {portalName}</strong>
          {' '}You have read-only visibility into this portal. Actions that modify adjudication or clinical records are disabled for the Owner role here.
        </span>
      </div>
    );

    if (path === '/' || path === '/owner') return <Dashboard stats={stats} />;
    if (path.startsWith('/admin')) return <AdminPortal user={user} onLogout={onLogout} isEmbedded={true} />;
    if (path === '/monitor/issues') return (
      <>
        <ReadOnlyBanner portalName="Monitor / QC Portal" />
        <MonitorIssuesView />
      </>
    );
    if (path.startsWith('/monitor')) return (
      <>
        <ReadOnlyBanner portalName="Monitor / QC Portal" />
        <MonitorPortal user={user} onLogout={onLogout} isEmbedded={true} readOnly={true} />
      </>
    );
    if (path.startsWith('/chairperson')) return (
      <>
        <ReadOnlyBanner portalName="Chairperson Portal" />
        <ChairpersonPortal user={user} onLogout={onLogout} isEmbedded={true} readOnly={true} />
      </>
    );
    if (path.startsWith('/adjudicator')) return (
      <>
        <ReadOnlyBanner portalName="Adjudicator Workbench" />
        <DeterminationsView />
      </>
    );
    return <Page title={TITLES[path] || 'Owner Portal'} desc="This section is currently in demonstration mode."><Notice kind="info" title="Global Stub">Standard views are unified under the Owner shell.</Notice></Page>;
  };


  return (
    <div className="admin-app">
      <header className="a-header">
        <div className="a-brand">
          <span><img src="/acrn-logo.png" alt="Africa Clinical Research Network" /></span>
          <div>
            <strong>ACRN Adjudication Platform</strong>
            <small>Owner Command Center</small>
          </div>
        </div>
        <div className="a-boundary" style={{ background: '#0f172a', color: 'white' }}>
          <Icon.Crown size={14} /> Global Visibility & Super User Privileges
        </div>
        <div className="a-user">
          <div>
            <strong>{user.name}</strong>
            <small>{user.role}</small>
          </div>
          <Badge>DEMO IDENTITY</Badge>
          <button onClick={onLogout} aria-label="Sign out">
            <Icon.LogOut size={16} />
          </button>
        </div>
      </header>

      <div className="a-body">
        <aside className={'a-nav ' + (collapsed ? 'collapsed' : '')}>
          <button className="a-collapse" onClick={() => setCollapsed(!collapsed)} aria-label="Toggle navigation">
            <span>OWNER PORTAL</span>
            {collapsed ? <Icon.ChevronsRight /> : <Icon.ChevronsLeft />}
          </button>
          
          {NAV.map(([g, x]) => (
            <section key={g}>
              <h2>{g}</h2>
              {x.map(([p, l, ic]) => {
                let C = Icon[ic];
                return (
                  <button key={p} title={l} className={path === p ? 'active' : ''} onClick={() => go(p)}>
                    <C size={15} /><span>{l}</span>
                  </button>
                );
              })}
            </section>
          ))}
          
          <div className="a-env">
            <Icon.Database size={14} />
            <span>GLOBAL ACCESS<br/><small>Read & Manage</small></span>
          </div>
        </aside>
        
        <main className="a-main">
          <div className="a-crumb">
            <button onClick={() => go('/owner')}>Owner</button>
            <Icon.ChevronRight size={12} />
            <span>{TITLES[path] || 'Live Portal View'}</span>
          </div>
          {renderView()}
        </main>
      </div>
    </div>
  );
}
