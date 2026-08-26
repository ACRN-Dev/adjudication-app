import React,{useEffect,useMemo,useState} from 'react'
import * as Icon from 'lucide-react'
import * as data from './adminData'
import { listUsers,setUserStatus,unlockUser,resetDemoPassword,setUserRole,setPortalRole,createUser } from '../services/authApi'
import './admin.css'

const NAV=[['OVERVIEW',[['/admin','Dashboard','LayoutDashboard']]],['ACCESS & PEOPLE',[['/admin/users','Users','Users'],['/admin/adjudicator-profiles','Adjudicator Profiles','ContactRound'],['/admin/committee-assignments','Committee Assignments','UserCog'],['/admin/access','Roles and Permissions','ShieldCheck'],['/admin/access-reviews','Access Reviews','UserCheck'],['/admin/training','Training and COI','GraduationCap']]],['STUDY CONFIGURATION',[['/admin/studies','Studies','BookOpen'],['/admin/sites','Sites','MapPin'],['/admin/endpoints','Endpoints and Windows','CalendarRange'],['/admin/workflows','Workflow Configuration','Workflow']]],['DATA CONFIGURATION',[['/admin/mappings','Canonical Field Mappings','GitCompare'],['/admin/terminology','Units and Terminology','Languages'],['/admin/dictionaries','Clinical Dictionaries','Library'],['/admin/import-contracts','Import Contracts','FileInput']]],['CONTROLLED CONTENT',[['/admin/rules','DV Rule Versions','Binary'],['/admin/forms','Forms and Templates','Files'],['/admin/sops','SOP References','FileCheck2']]],['SYSTEM',[['/admin/integrations','Integrations','PlugZap'],['/admin/audit','Audit Trail','ScrollText'],['/admin/reports','Reports','FileBarChart'],['/admin/health','Environment and Health','Activity']]]]
const TITLES=Object.fromEntries(NAV.flatMap(([,x])=>x.map(([p,l])=>[p,l])))
const DEFAULT_DASH={environment:'DEMO / STANDALONE',api:'Checking',database:'Checking',metrics:{active_studies:1,configured_sites:2,active_users:3,pending_approval:1,expiring_access:2,incomplete_training:1,open_access_reviews:1,integration_warnings:2},action_queue:[{type:'access',label:'Approve pending user access',count:1},{type:'expiry',label:'Review expiring access',count:2},{type:'training',label:'Review incomplete training',count:1},{type:'integration',label:'Resolve integration warnings',count:2}]}
const apiHeaders={'X-Demo-User':'clinical.ops.demo@acrnhealth.com','X-Demo-Role':'CLINICAL_OPS_ADMIN','X-Study-Scope':'PROTECT-Africa,LOPE-Nigeria'}

function goTo(path){history.pushState({},'',path);dispatchEvent(new PopStateEvent('popstate'))}
function downloadCsv(name,columns,rows){const quote=v=>`"${String(v??'').replaceAll('"','""')}"`;const csv=[columns,...rows].map(r=>r.map(quote).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`${name}-DEMO.csv`;a.click();URL.revokeObjectURL(url)}
function controlledAction(label){if(!confirm(`${label}? This demonstration action will not affect production data.`))return;const reason=prompt('Enter the required reason for this demonstration action:');if(reason?.trim())alert(`${label} completed in demo mode.\n\nReason: ${reason}\nAn immutable demonstration audit event would be created.`)}
function demoInfo(label){alert(`${label}\n\nThis function is operating on synthetic demonstration data. A production deployment will apply server-side permission, approval and audit controls.`)}

function AdjudicatorProfiles(){
  const [rows,setRows]=useState([]),[msg,setMsg]=useState('');
  const load=()=>fetch('/api/admin/adjudicator-profiles',{credentials:'include'}).then(r=>r.ok?r.json():Promise.reject(new Error('Profile request failed'))).then(x=>setRows(x.items||[])).catch(e=>setMsg(e.message));
  useEffect(()=>{load()},[]);
  const edit=async row=>{const study=prompt('Study code (PROTECT-Africa or LOPE-Nigeria)');if(!study)return;const contract=prompt('Contract signing date (YYYY-MM-DD)');const reference=prompt('Contract reference');const tor=prompt('Terms of Reference link (optional)')||'';const reason=prompt('Reason for contract update');if(!contract||!reference||!reason?.trim())return;try{const res=await fetch(`/api/admin/adjudicator-profiles/${encodeURIComponent(row.adjudicator_upn)}/contract`,{method:'PUT',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({study_code:study,contract_signed_at:`${contract}T00:00:00`,contract_reference:reference,terms_of_reference_url:tor,reason})});if(!res.ok){const x=await res.json();throw new Error(x.detail||'Update failed')}setMsg('Study contract versioned.');load()}catch(e){setMsg(e.message)}};
  return <Page title="Adjudicator Profiles" desc="Clinical identity, study contracts, committee membership and ledger-derived workload. Finance data is restricted to Finance users.">{msg&&<div className="a-success" role="status">{msg}</div>}<Table caption="Adjudicator profile register" columns={['Name','Email','Role','Study contracts','Committee membership','A/B signed','C signed','Active assignments','Account']} rows={rows.map(r=>[r.display_name,r.adjudicator_upn,'ADJUDICATOR',(r.contracts||[]).map(c=>`${c.study_code}: ${c.contract_signed_at?new Date(c.contract_signed_at).toLocaleDateString():'Not signed'}`).join(' · ')||'Not configured',(r.committee_memberships||[]).map(m=>`${m.committee_name} (${m.membership_role})`).join(' · ')||'None',r.cases_reviewed_by_role?.REVIEWER_A+r.cases_reviewed_by_role?.REVIEWER_B||0,r.cases_reviewed_by_role?.REVIEWER_C||0,r.active_assignments,r.account_status])} actions={r=><button className="a-link" onClick={()=>edit(rows.find(x=>x.adjudicator_upn===r[1]))}>Manage contract</button>}/></Page>
}

function Badge({children}){let s=String(children).toLowerCase(),c=s.includes('active')||s.includes('healthy')||s.includes('passed')||s.includes('current')||s.includes('success')?'ok':s.includes('pending')||s.includes('warning')||s.includes('validation')?'warn':s.includes('failed')?'bad':'';return <span className={'a-badge '+c}>{children}</span>}
function Table({caption,columns,rows,actions}){const [filter,setFilter]=useState({query:'',status:''});useEffect(()=>{const f=e=>setFilter(e.detail);addEventListener('admin-table-filter',f);return()=>removeEventListener('admin-table-filter',f)},[]);const shown=useMemo(()=>rows.filter(r=>{const text=r.join(' ').toLowerCase();return (!filter.query||text.includes(filter.query.toLowerCase()))&&(!filter.status||text.includes(filter.status.toLowerCase()))}),[rows,filter]);return <div className="a-table-wrap"><table className="a-table"><caption>{caption} — {shown.length} record{shown.length===1?'':'s'}</caption><thead><tr>{columns.map(c=><th scope="col" key={c}>{c}</th>)}{actions&&<th>Actions</th>}</tr></thead><tbody>{shown.map((r,i)=><tr key={i}>{r.map((v,j)=><td key={j}>{/status|training|tests|outcome/i.test(columns[j])?<Badge>{v}</Badge>:v}</td>)}{actions&&<td>{actions(r)}</td>}</tr>)}{!shown.length&&<tr><td colSpan={columns.length+(actions?1:0)}>No demonstration records match the current filters.</td></tr>}</tbody></table></div>}
function Page({title,desc,action,children}){return <><div className="a-page-head"><div><h1>{title}</h1><p>{desc}</p></div>{action}</div>{children}</>}
function Toolbar({children}){const [query,setQuery]=useState(''),[status,setStatus]=useState('');const apply=(q,s)=>dispatchEvent(new CustomEvent('admin-table-filter',{detail:{query:q,status:s}}));return <div className="a-toolbar"><label className="sr-only" htmlFor="admin-search">Search records</label><div><Icon.Search size={14}/><input id="admin-search" value={query} onChange={e=>{setQuery(e.target.value);apply(e.target.value,status)}} placeholder="Search or filter records…"/></div><select aria-label="Status filter" value={status} onChange={e=>{setStatus(e.target.value);apply(query,e.target.value)}}><option value="">All statuses</option><option>Active</option><option>Pending</option><option>Draft</option><option>Warning</option></select>{children}<button type="button" onClick={()=>{setQuery('');setStatus('');apply('','')}}>Clear filters</button></div>}
const Primary=({children,onClick,title='Create controlled draft'})=><button className="a-primary" onClick={onClick||(()=>controlledAction(title))}>{children}</button>
function Notice({kind='info',title,children}){return <div className={'a-notice '+kind}><Icon.ShieldAlert size={17}/><div><strong>{title}</strong><span>{children}</span></div></div>}

function Dashboard({dash}){let m=dash.metrics;const target={access:'/admin/users',expiry:'/admin/access-reviews',training:'/admin/training',integration:'/admin/integrations',ACCESS_APPROVAL:'/admin/users',EXPIRY:'/admin/access-reviews',TRAINING:'/admin/training',INTEGRATION:'/admin/integrations'};return <Page title="Administration Overview" desc="Operational governance, access and configuration status. Clinical case content is not available here."><Notice title="Demonstration administration environment">Synthetic records only · Demo identity is not Microsoft Entra authentication.</Notice><div className="a-metrics">{[['Active studies',m.active_studies],['Configured sites',m.configured_sites],['Active users',m.active_users],['Pending approval',m.pending_approval],['Expiring access',m.expiring_access],['Incomplete training',m.incomplete_training],['Open access reviews',m.open_access_reviews],['Integration warnings',m.integration_warnings]].map(([l,v])=><button onClick={()=>goTo(l.includes('stud')?'/admin/studies':l.includes('site')?'/admin/sites':l.includes('user')||l.includes('approval')?'/admin/users':l.includes('training')?'/admin/training':l.includes('review')?'/admin/access-reviews':'/admin/integrations')} key={l}><strong>{v}</strong><span>{l}</span></button>)}</div><div className="a-grid2"><section className="a-panel"><h2>Action queue</h2>{dash.action_queue.map(q=><button className="a-queue" key={q.type} onClick={()=>goTo(target[q.type]||'/admin')}><span>{q.label}</span><Badge>{q.count} open</Badge><Icon.ChevronRight size={14}/></button>)}</section><section className="a-panel"><h2>Environment and health</h2><dl><div><dt>Environment</dt><dd><Badge>{dash.environment}</Badge></dd></div><div><dt>API status</dt><dd><Badge>{dash.api}</Badge></dd></div><div><dt>Database / migration</dt><dd>{dash.database} · schema current</dd></div><div><dt>Clinical case access</dt><dd>Denied</dd></div></dl></section></div><Table caption="Recent security and configuration events" columns={['Event ID','Timestamp','Acting user','Role','Action','Entity','Reason','Outcome']} rows={data.audits}/></Page>}
function Users(){
  const [rows,setRows]=useState([]),
        [msg,setMsg]=useState(''),
        [q,setQ]=useState(''),
        [role,setRole]=useState(''),
        [status,setStatus]=useState(''),
        [showAddModal,setShowAddModal]=useState(false),
        [addBusy,setAddBusy]=useState(false),
        [createdNotice,setCreatedNotice]=useState(null),
        [newUser,setNewUser]=useState({
          email:'',
          display_name:'',
          role:'MONITOR',
          password:'',
          study_scope:'*',
          reason:'Initial user onboarding via Admin Portal'
        });

  const load=()=>listUsers({search:q,role,status,page_size:100}).then(x=>setRows(x.items)).catch(e=>setMsg(e.message));
  useEffect(()=>{load()},[q,role,status]);

  const reason=label=>prompt(`${label}\n\nEnter the required audit reason:`);
  const action=async(fn,label)=>{
    const why=reason(label);
    if(!why?.trim())return;
    try{
      await fn(why.trim());
      setMsg(`${label} completed and audited.`);
      load();
    }catch(e){
      setMsg(e.message);
    }
  };

  const handleCreateUser=async(e)=>{
    e.preventDefault();
    if(!newUser.email||!newUser.display_name||!newUser.reason){
      setMsg('Please fill in all required fields (Name, Email, Reason).');
      return;
    }
    setAddBusy(true);
    setMsg('');
    try{
      const res=await createUser({
        email:newUser.email.trim(),
        display_name:newUser.display_name.trim(),
        role:newUser.role,
        password:newUser.password||undefined,
        study_scope:newUser.study_scope||'*',
        reason:newUser.reason.trim()
      });
      setCreatedNotice({
        email:res.email,
        name:res.display_name,
        role:res.role,
        password:res.temporary_password
      });
      setShowAddModal(false);
      setNewUser({
        email:'',
        display_name:'',
        role:'MONITOR',
        password:'',
        study_scope:'*',
        reason:'Initial user onboarding via Admin Portal'
      });
      setMsg(`User ${res.display_name} (${res.email}) created successfully.`);
      load();
    }catch(err){
      setMsg(`Error creating user: ${err.message}`);
    }finally{
      setAddBusy(false);
    }
  };

  const tableRows=rows.map(u=>[
    u.display_name,
    u.email,
    u.roleCode,
    u.portal_role || 'Not configured',
    u.status,
    u.is_demo_account?'Yes':'No',
    u.last_login_at?new Date(u.last_login_at).toLocaleString():'Never',
    u.locked_until?new Date(u.locked_until).toLocaleString():'Not locked',
    u.id
  ]);

  return (
    <Page
      title="User Account Management"
      desc="Provision user accounts with default credentials, assign operational roles, and manage account statuses."
      action={
        <div style={{display:'flex', gap:'8px'}}>
          <button className="a-primary" onClick={()=>setShowAddModal(true)} style={{display:'flex', alignItems:'center', gap:'6px'}}>
            <Icon.UserPlus size={13}/> Add User
          </button>
          <button className="a-secondary" onClick={()=>downloadCsv('account-register',['Name','Email','Role','Status','Demo','Last login','Lock state'],tableRows.map(r=>r.slice(0,7)))}>
            Export access register
          </button>
        </div>
      }
    >
      {msg && <div className={msg.startsWith('Error') ? 'a-notice danger' : 'a-success'} role="status">{msg}</div>}

      {createdNotice && (
        <div style={{background:'#f0fdf4', border:'1px solid #86efac', borderRadius:'6px', padding:'14px 16px', marginBottom:'14px', position:'relative'}}>
          <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'8px'}}>
            <strong style={{color:'#15803d', fontSize:'13px', display:'flex', alignItems:'center', gap:'6px'}}>
              <Icon.CheckCircle2 size={16}/> New User Account Provisioned Successfully
            </strong>
            <button onClick={()=>setCreatedNotice(null)} style={{background:'none', border:'none', cursor:'pointer', color:'#64748b'}}>
              <Icon.X size={14}/>
            </button>
          </div>
          <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(200px, 1fr))', gap:'8px', fontSize:'12px', color:'#1e293b'}}>
            <div><strong>Name:</strong> {createdNotice.name}</div>
            <div><strong>Email:</strong> {createdNotice.email}</div>
            <div><strong>Assigned Role:</strong> <span className="a-badge ok">{createdNotice.role}</span></div>
            <div><strong>Temporary Password:</strong> <code style={{background:'#dcfce7', padding:'2px 6px', borderRadius:'4px', fontWeight:700, color:'#14532d'}}>{createdNotice.password}</code></div>
          </div>
          <p style={{fontSize:'11px', color:'#475569', margin:'8px 0 0'}}>Share this temporary password with the user out-of-band. It is unique to this account and they will be required to set their own password on first login.</p>
        </div>
      )}

      {showAddModal && (
        <div style={{position:'fixed', top:0, left:0, right:0, bottom:0, background:'rgba(15, 23, 42, 0.6)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000, padding:'20px'}}>
          <div style={{background:'#fff', borderRadius:'8px', width:'100%', maxWidth:'480px', boxShadow:'0 20px 25px -5px rgba(0,0,0,0.1)', overflow:'hidden'}}>
            <div style={{padding:'16px 20px', background:'var(--admin-navy)', color:'#fff', display:'flex', alignItems:'center', justifyContent:'space-between'}}>
              <strong style={{fontSize:'14px', display:'flex', alignItems:'center', gap:'8px'}}><Icon.UserPlus size={16}/> Add New User Account</strong>
              <button onClick={()=>setShowAddModal(false)} style={{background:'none', border:'none', color:'#fff', cursor:'pointer'}}><Icon.X size={16}/></button>
            </div>
            <form onSubmit={handleCreateUser} style={{padding:'20px', display:'grid', gap:'12px'}}>
              <div>
                <label style={{display:'block', fontSize:'11px', fontWeight:600, color:'#334155', marginBottom:'4px'}}>Full Name / Display Name *</label>
                <input required value={newUser.display_name} onChange={e=>setNewUser({...newUser, display_name:e.target.value})} placeholder="e.g. Dr. John Doe" style={{width:'100%', padding:'8px 10px', fontSize:'12px', border:'1px solid #cbd5e1', borderRadius:'4px', boxSizing:'border-box'}}/>
              </div>
              <div>
                <label style={{display:'block', fontSize:'11px', fontWeight:600, color:'#334155', marginBottom:'4px'}}>Email Address *</label>
                <input required type="email" value={newUser.email} onChange={e=>setNewUser({...newUser, email:e.target.value})} placeholder="e.g. user@acrnhealth.com" style={{width:'100%', padding:'8px 10px', fontSize:'12px', border:'1px solid #cbd5e1', borderRadius:'4px', boxSizing:'border-box'}}/>
              </div>
              <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'10px'}}>
                <div>
                  <label style={{display:'block', fontSize:'11px', fontWeight:600, color:'#334155', marginBottom:'4px'}}>Role *</label>
                  <select value={newUser.role} onChange={e=>setNewUser({...newUser, role:e.target.value})} style={{width:'100%', padding:'8px 10px', fontSize:'12px', border:'1px solid #cbd5e1', borderRadius:'4px', background:'#fff'}}>
                    <option value="MONITOR">Monitor</option>
                    <option value="ADJUDICATOR">Adjudicator</option>
                    <option value="CHAIRPERSON">Chairperson</option>
                    <option value="ADMIN">Admin</option>
                  </select>
                </div>
                <div>
                  <label style={{display:'block', fontSize:'11px', fontWeight:600, color:'#334155', marginBottom:'4px'}}>Temporary Password (optional)</label>
                  <input value={newUser.password} onChange={e=>setNewUser({...newUser, password:e.target.value})} placeholder="Leave blank to auto-generate a unique password" style={{width:'100%', padding:'8px 10px', fontSize:'12px', border:'1px solid #cbd5e1', borderRadius:'4px', boxSizing:'border-box'}}/>
                </div>
              </div>
              <div>
                <label style={{display:'block', fontSize:'11px', fontWeight:600, color:'#334155', marginBottom:'4px'}}>Audit Reason (21 CFR Part 11 Compliance) *</label>
                <input required value={newUser.reason} onChange={e=>setNewUser({...newUser, reason:e.target.value})} placeholder="Reason for creating user" style={{width:'100%', padding:'8px 10px', fontSize:'12px', border:'1px solid #cbd5e1', borderRadius:'4px', boxSizing:'border-box'}}/>
              </div>
              <div style={{display:'flex', justifyContent:'flex-end', gap:'8px', marginTop:'8px'}}>
                <button type="button" onClick={()=>setShowAddModal(false)} style={{padding:'8px 14px', fontSize:'12px', background:'#f1f5f9', border:'1px solid #cbd5e1', borderRadius:'4px', cursor:'pointer'}}>Cancel</button>
                <button type="submit" disabled={addBusy} className="a-primary" style={{padding:'8px 16px', fontSize:'12px', display:'flex', alignItems:'center', gap:'6px'}}>
                  {addBusy ? 'Creating...' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="a-toolbar">
        <div>
          <Icon.Search size={14}/>
          <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search users by name or email..."/>
        </div>
        <select value={role} onChange={e=>setRole(e.target.value)}>
          <option value="">All roles</option>
          <option value="ADMIN">Admin</option>
          <option value="MONITOR">Monitor</option>
          <option value="ADJUDICATOR">Adjudicator</option>
          <option value="CHAIRPERSON">Chairperson</option>
        </select>
        <select value={status} onChange={e=>setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
        </select>
        <button type="button" onClick={()=>{setQ('');setRole('');setStatus('')}}>Clear filters</button>
      </div>

      <Table
        caption="User account register"
        columns={['Name','Email','Role','Portal role','Status','Demo','Last login','Lock state']}
        rows={tableRows.map(r=>[r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7]])}
        actions={(r)=>{
          const u=rows.find(x=>x.email===r[1]);
          if(!u)return null;
          return (
            <span className="a-actions">
              <button onClick={()=>action(why=>setUserStatus(u.id,u.status==='ACTIVE'?'INACTIVE':'ACTIVE',why),u.status==='ACTIVE'?'Deactivate account':'Activate account')}>
                {u.status==='ACTIVE'?'Deactivate':'Activate'}
              </button>
              <button onClick={()=>action(why=>unlockUser(u.id,why),'Unlock account')}>
                Unlock
              </button>
              <button onClick={()=>{if(confirm(`Reset password for ${u.email}? They will be required to set a new password on next login.`))action(why=>resetDemoPassword(u.id,why),'Reset password')}}>
                Reset password
              </button>
              <select value={u.roleCode} onChange={e=>action(why=>setUserRole(u.id,e.target.value,why),'Change role')}>
                <option value="ADMIN">Admin</option>
                <option value="MONITOR">Monitor</option>
                <option value="ADJUDICATOR">Adjudicator</option>
                <option value="CHAIRPERSON">Chairperson</option>
              </select>
              {u.roleCode==='MONITOR' && <select value={u.portal_role||'MONITOR_QC_REVIEWER'} onChange={e=>action(why=>setPortalRole(u.id,e.target.value,why),'Change monitor portal role')}>
                <option value="MONITOR_QC_REVIEWER">Monitor QC Reviewer</option>
                <option value="ADJUDICATION_COORDINATOR">Adjudication Coordinator</option>
                <option value="QA_REVIEWER">QA Reviewer</option>
                <option value="RELEASE_OPERATOR">Release Operator</option>
              </select>}
            </span>
          );
        }}
      />
      <Notice kind="info" title="User Credential Management">
        Users created here receive a secure hashed password and can log in directly using their email and password or via Microsoft Single Sign-On.
      </Notice>
    </Page>
  );
}

function Roles(){return <Page title="Roles and Permissions" desc="Versioned roles, delegated authority and separation-of-duties controls." action={<Primary><Icon.Plus size={14}/> Draft custom role</Primary>}><Notice kind="warn" title="High-risk combinations">Technical admin + adjudicator; Monitor/QC + reviewer; reviewer + release approver; user admin + self-approver; committee + incompatible operations access are blocked or flagged.</Notice><Table caption="Administrative role register" columns={['Role','Purpose','Administrative scope','Clinical boundary']} rows={[["Technical Administrator","Platform configuration and identity","Users, integrations, audit","No case content"],["Clinical Operations Administrator","Study and content configuration","Studies, sites, rules, mappings, forms","No adjudication"],["QA/Auditor","Independent review and approval","Audit, reports, approvals","Read-only otherwise"],["Governance Reviewer","Governance oversight","Roles, studies, rules, audit","Read-only"],["Access Reviewer","Periodic certification","Users and access reviews","No self-approval"]]}/><Table caption="Portal permission matrix" columns={['Capability','Technical Admin','Clinical Ops','QA/Auditor','Governance','Access Reviewer']} rows={[["Admin Portal","Manage","Manage","Read/approve","Read","Review"],["Blinded case content","Denied","Denied","Denied","Denied","Denied"],["User administration","Manage","Read","Read","Read","Review"],["Rules / mappings / forms","Read","Draft/manage","Approve","Read","None"],["Clinical decisions","Denied","Denied","Denied","Denied","Denied"]]}/></Page>}
function Register({type}){let cfg={studies:['Studies','Versioned study configuration. Active records cannot be edited in place.',['Study code','Study name','Protocol','Countries','Status','Version','Active DV rules','Active mapping'],data.studies],sites:['Sites','Only approved blinded display names are exposed to adjudicators.',['Site code','Blinded display name','Country','Study','Status','Import identifier','Allowed sources'],data.sites],rules:['DV Rule Versions','DV-01 through DV-30; the Python engine remains authoritative.',['DV identifier','Name','Purpose','Version','Effective','Status','Approvals','Tests'],data.rules],mappings:['Canonical Field Mappings','Versioned source-to-canonical contracts and blinding classifications.',['Source system','Source field','Canonical field','Data type','Unit','Requirement','Study','Version','Status','Blinding'],data.mappings],forms:['Forms and Templates','Used form versions are never overwritten.',['Form code','Name','Version','Study applicability','Status','Supporting SOP'],data.forms],integrations:['Integrations','Connection metadata only; credentials are never displayed.',['Name','Type','Environment','Status','Last connection','Credential status','Enabled'],data.integrations]}[type];return <Page title={cfg[0]} desc={cfg[1]} action={<Primary title={`Create new ${cfg[0]} draft`}><Icon.Plus size={14}/> New controlled draft</Primary>}>{type==='rules'&&<Notice kind="warn" title="Immutable active rules">Activation requires passing tests plus clinical and QA approval. Browser-entered executable code is prohibited.</Notice>}{type==='mappings'&&<Notice kind="danger" title="Permanent prohibited-field registry">sFlt-1, PlGF, sEng, biomarker results, POC results, treatment allocation and configured unblinding fields can never map to adjudicator-facing data.</Notice>}<Toolbar><button onClick={()=>downloadCsv(type,cfg[2],cfg[3])}>Export register</button>{type==='rules'&&<button onClick={()=>demoInfo('Version comparison opened for the selected DV rule')}>Compare versions</button>}{type==='mappings'&&<button onClick={()=>demoInfo('Sample CSV validation passed: 3 mapped fields, 0 prohibited fields')}>Test sample CSV</button>}</Toolbar><Table caption={`Synthetic ${cfg[0].toLowerCase()} register`} columns={cfg[2]} rows={cfg[3]} actions={type==='integrations'?(r)=> <button className="a-link" onClick={()=>demoInfo(`${r[0]} connection test: ${r[3]==='Healthy'?'successful':'synthetic warning returned'}`)}>Test connection</button>:null}/><p className="a-foot">Active or historically used records are immutable; all changes create a reasoned successor version and audit event.</p></Page>}
function Workflow(){return <Page title="Workflow Configuration" desc="Validated states, transitions, authority, signatures, gates and release requirements." action={<Primary>New workflow draft</Primary>}><div className="a-flow">{data.workflow.map((x,i)=><React.Fragment key={x}><span><b>{i+1}</b>{x}</span>{i<data.workflow.length-1&&<Icon.ChevronRight size={12}/>}</React.Fragment>)}</div><div className="a-grid3">{[['Validation controls',['No import-to-adjudication shortcut','Final QC required before release','No modification after lock']],['Committee controls',['Minimum quorum: 3 of 5','Chair signature required','Recused member excluded']],['Controlled reopen',['Reason and approval required','Original history preserved','Immutable audit event created']]].map(([h,x])=><section className="a-panel" key={h}><h2>{h}</h2><ul>{x.map(y=><li key={y}>{y}</li>)}</ul></section>)}</div></Page>}
function Audit(){const cols=['Event ID','Timestamp','Acting user','Role','Action','Entity','Reason','Outcome'];return <Page title="Audit Trail" desc="Immutable administrative security and configuration history." action={<button className="a-secondary" onClick={()=>downloadCsv('administrative-audit-trail',cols,data.audits)}>Controlled export</button>}><Toolbar/><Table caption="Synthetic immutable audit events" columns={cols} rows={data.audits}/><p className="a-foot">Audit events cannot be edited or deleted. Participant filters require separate specific authority.</p></Page>}
function Reviews(){return <Page title="Access Reviews" desc="Periodic certification of portal, study and site access." action={<Primary>Generate campaign</Primary>}><div className="a-grid2"><section className="a-panel"><h2>Q3 2026 Admin Portal Review</h2><p>3 of 8 identities certified · Due 17 Aug 2026</p><progress value="3" max="8">3 of 8</progress><p><Badge>Open</Badge></p></section><section className="a-panel"><h2>Automatic flags</h2><ul><li>1 access expiry within 14 days</li><li>1 incomplete training / COI</li><li>1 inactive identity</li><li>No closed-study access</li></ul></section></div><Table caption="Review population" columns={['User','Role','Scope','Training / COI','Last login','Flag','Decision']} rows={[["Tariro Moyo","Technical Administrator","Platform","Current / Current","Today","High privilege","Confirm"],["Amara Okafor","Clinical Ops Admin","Two studies","Current / Current","Yesterday","None","Confirmed"],["Lindiwe Dube","Access requested","PROTECT-Africa","Incomplete / Pending","Never","Block","Revoke"]]}/></Page>}
function Reports(){let r=['User access register','Role-permission matrix','Study configuration register','Active rule versions','Active mapping versions','Form/template register','Access-review status','Training compliance','Configuration changes','Integration incidents','Import failures','Audit-event summary'];return <Page title="Administrative Reports" desc="Controlled exports constrained by role and delegated study scope."><div className="a-reports">{r.map(x=><button key={x} onClick={()=>downloadCsv(x.toLowerCase().replaceAll(' ','-'),['Report','Environment','Scope','Generated'],[[x,'DEMO','Delegated studies only',new Date().toISOString()]])}><Icon.FileSpreadsheet/><strong>{x}</strong><small>Demo data · scoped export</small><Icon.Download size={14}/></button>)}</div></Page>}
function Health(){const [msg,setMsg]=useState('');const [busy,setBusy]=useState(false);const doReset=async()=>{if(!confirm('Delete ALL imported batches, participants, adjudication records and demo data, then re-seed default accounts?\n\nThis cannot be undone.'))return;const reason=prompt('Enter reason for the full reset (required for audit trail):');if(!reason?.trim())return;setBusy(true);setMsg('');try{const r=await fetch('/api/admin/demo/reset-all',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:reason.trim()})});const body=await r.json();if(!r.ok)throw new Error(body.detail||'Reset failed');const total=Object.values(body.reset||{}).reduce((a,b)=>a+(b||0),0);setMsg(`Reset complete — ${total} demo records cleared and re-seeded.`)}catch(e){setMsg('Error: '+e.message)}finally{setBusy(false)}};return <Page title="Environment and Health" desc="Platform health, database status and demonstration environment controls."><Notice title="Demonstration environment">All data below is synthetic. Reset does not affect any production system.</Notice><div className="a-grid2"><section className="a-panel"><h2>Database / migration</h2><dl><div><dt>Mode</dt><dd>SQLite (demo) or PostgreSQL (production)</dd></div><div><dt>Auth tables</dt><dd>portal_users · auth_sessions · auth_audit_events</dd></div><div><dt>Longitudinal tables</dt><dd>rt_import_batches · longitudinal_participants · visit_instances</dd></div><div><dt>Adjudication tables</dt><dd>participants · adjudication_records · committee_decisions</dd></div></dl></section><section className="a-panel"><h2>Reset demo database</h2><p style={{fontSize:'13px',color:'var(--text-muted)',marginBottom:'12px'}}>Clears all imported batches, participants, adjudication records, narratives and admin demo fixtures, then re-seeds default demo accounts and configuration.</p>{msg&&<div className={msg.startsWith('Error')?'a-notice danger':'a-success'} role="status" style={{marginBottom:'12px'}}>{msg}</div>}<button onClick={doReset} disabled={busy} style={{background:'#dc2626',color:'#fff',border:'none',borderRadius:'6px',padding:'10px 20px',fontWeight:700,fontSize:'14px',cursor:busy?'wait':'pointer',opacity:busy?0.7:1,display:'flex',alignItems:'center',gap:'8px'}}><Icon.Trash2 size={15}/>{busy?'Resetting…':'Reset All Demo Data'}</button><p style={{fontSize:'11px',color:'var(--text-muted)',marginTop:'8px'}}>Requires admin role · Audited · Irreversible in demo session</p></section></div></Page>}
function CommitteeAssignments(){const [rows,setRows]=useState([]),[users,setUsers]=useState([]),[msg,setMsg]=useState('');const load=()=>Promise.all([fetch('/api/auth/committee-assignments',{credentials:'include'}).then(r=>r.ok?r.json():{items:[]}),listUsers({role:'CHAIRPERSON',page_size:100})]).then(([a,u])=>{setRows(a.items||[]);setUsers(u.items||[])}).catch(e=>setMsg(e.message));useEffect(()=>{load()},[]);const reason=label=>prompt(`${label}\n\nEnter the required audit reason:`);const assignChair=async(u)=>{const why=reason(`Assign committee chairperson: ${u.display_name}`);if(!why?.trim())return;try{await fetch(`/api/auth/users/${u.id}/committee-assignment`,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:why.trim(),committee_name:'PROTECT-Africa Committee'})}).then(r=>{if(!r.ok)return r.json().then(b=>{throw new Error(b.detail||'Assignment failed')})});setMsg(`${u.display_name} assigned as committee chairperson.`);load()}catch(e){setMsg(e.message)}};const deactivate=async(row)=>{const why=reason(`Deactivate assignment for user ${row.email}`);if(!why?.trim())return;try{await fetch(`/api/auth/committee-assignments/${row.id}/deactivate`,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:why.trim()})}).then(r=>{if(!r.ok)return r.json().then(b=>{throw new Error(b.detail||'Deactivation failed')})});setMsg('Assignment deactivated.');load()}catch(e){setMsg(e.message)}};const tableRows=rows.map(r=>[r.display_name||r.email||'—',r.email||'—',r.assignment_type,r.committee_name||'—',r.is_active?'Active':'Inactive',r.expires_at?new Date(r.expires_at).toLocaleDateString():'No expiry',r.assigned_at?new Date(r.assigned_at).toLocaleString():'—',r.id]);const unassignedChairs=users.filter(u=>!rows.some(r=>r.email===u.email&&r.is_active));return <Page title="Committee Assignments" desc="Manage active chairperson committee assignments. Assignments gate access to the Chairperson Portal."><Notice kind="warn" title="Governance control">Only CHAIRPERSON role users can be assigned. Deactivation is audited and immediate.</Notice>{msg&&<div className="a-success" role="status">{msg}</div>}{unassignedChairs.length>0&&<section className="a-panel" style={{marginBottom:'16px'}}><h2>Assign Chairperson</h2><p style={{fontSize:'13px',color:'var(--text-muted)',marginBottom:'8px'}}>The following CHAIRPERSON users have no active committee assignment and cannot access chairperson endpoints.</p>{unassignedChairs.map(u=><div key={u.id} style={{display:'flex',alignItems:'center',gap:'12px',marginBottom:'6px'}}><span style={{flex:1,fontSize:'13px'}}>{u.display_name} <small style={{color:'var(--text-muted)'}}>{u.email}</small></span><button className="a-primary" onClick={()=>assignChair(u)} style={{fontSize:'12px',padding:'4px 10px'}}><Icon.UserCog size={13}/> Assign Chair</button></div>)}</section>}<Table caption="Committee assignment register" columns={['Name','Email','Type','Committee','Status','Expires','Assigned at']} rows={tableRows.map(r=>r.slice(0,7))} actions={(r)=>{const row=rows.find(x=>x.id===r[7]||tableRows.find(t=>t[7]===x.id&&t[0]===r[0]));const found=rows.find(x=>x.email===r[1]&&x.assignment_type===r[2]);return found&&found.is_active?<button onClick={()=>deactivate(found)} style={{color:'#dc2626',fontWeight:600,fontSize:'12px',background:'none',border:'1px solid #dc2626',borderRadius:'4px',padding:'2px 8px',cursor:'pointer'}}>Deactivate</button>:<span style={{color:'var(--text-muted)',fontSize:'12px'}}>Inactive</span>}}/></Page>}
function Generic({path}){if(path==='/admin/adjudicator-profiles')return <AdjudicatorProfiles/>;return <Page title={TITLES[path]||'Administration'} desc="Governed administrative configuration for the ACRN adjudication platform."><section className="a-panel a-empty"><Icon.Settings2/><h2>{TITLES[path]}</h2><p>This controlled register is ready in demonstration mode. Production activation depends on approved dictionaries, integration contracts and governance ownership.</p><Primary>Create draft record</Primary></section></Page>}

export default function AdminPortal({user,onLogout}){const [path,setPath]=useState(location.pathname.startsWith('/admin')?location.pathname:'/admin'),[collapsed,setCollapsed]=useState(false),[dash,setDash]=useState(DEFAULT_DASH);useEffect(()=>{let pop=()=>setPath(location.pathname);addEventListener('popstate',pop);fetch('/api/admin/dashboard',{credentials:'include'}).then(r=>r.ok?r.json():Promise.reject()).then(setDash).catch(()=>setDash(x=>({...x,api:'Offline demo data',database:'Local synthetic fixtures'})));return()=>removeEventListener('popstate',pop)},[]);let go=p=>{history.pushState({},'',p);setPath(p)};let view=path==='/admin'?<Dashboard dash={dash}/>:path==='/admin/users'?<Users/>:path==='/admin/committee-assignments'?<CommitteeAssignments/>:path==='/admin/access'?<Roles/>:path==='/admin/studies'?<Register type="studies"/>:path==='/admin/sites'?<Register type="sites"/>:path==='/admin/rules'?<Register type="rules"/>:path==='/admin/mappings'?<Register type="mappings"/>:path==='/admin/forms'?<Register type="forms"/>:path==='/admin/integrations'?<Register type="integrations"/>:path==='/admin/workflows'?<Workflow/>:path==='/admin/audit'?<Audit/>:path==='/admin/access-reviews'?<Reviews/>:path==='/admin/reports'?<Reports/>:path==='/admin/health'?<Health/>:<Generic path={path}/>;return <div className="admin-app"><header className="a-header"><div className="a-brand"><span><img src="/acrn-logo.png" alt="Africa Clinical Research Network"/></span><div><strong>ACRN Adjudication Platform</strong><small>Administration Portal</small></div></div><div className="a-boundary"><Icon.Shield size={14}/> Operational metadata only · clinical case access disabled</div><div className="a-user"><div><strong>{user.name}</strong><small>{user.role}</small></div><Badge>DEMO IDENTITY</Badge><button onClick={onLogout} aria-label="Sign out"><Icon.LogOut size={16}/></button></div></header><div className="a-body"><aside className={'a-nav '+(collapsed?'collapsed':'')}><button className="a-collapse" onClick={()=>setCollapsed(!collapsed)} aria-label="Toggle navigation"><span>ADMINISTRATION</span>{collapsed?<Icon.ChevronsRight/>:<Icon.ChevronsLeft/>}</button>{NAV.map(([g,x])=><section key={g}><h2>{g}</h2>{x.map(([p,l,ic])=>{let C=Icon[ic];return <button key={p} title={l} className={path===p?'active':''} onClick={()=>go(p)}><C size={15}/><span>{l}</span></button>})}</section>)}<div className="a-env"><Icon.Database size={14}/><span>DEMO DATA<br/><small>{dash.api}</small></span></div></aside><main className="a-main"><div className="a-crumb"><button onClick={()=>go('/admin')}>Admin</button><Icon.ChevronRight size={12}/><span>{TITLES[path]||'Dashboard'}</span></div>{view}</main></div></div>}

