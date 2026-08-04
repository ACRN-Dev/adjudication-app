import React,{useEffect,useState} from 'react';import * as I from 'lucide-react';import '../admin/admin.css';import './monitor.css';
import {listBatches,listPatients,getPatient,uploadRealtime,approvePatient,assignPatient} from '../services/realtimeApi';
const nav=[['/monitor','Dashboard','LayoutDashboard'],['/monitor/imports','RealTime Imports','Upload'],['/monitor/patients','Patient Database','Database'],['/monitor/reconstruction','Visit Reconstruction QC','GitCompare'],['/monitor/longitudinal','Longitudinal Review','Activity'],['/monitor/assignments','Assignments','UsersRound'],['/monitor/queries','Queries','MessagesSquare'],['/monitor/audit','Audit History','ScrollText']];
const H=({user})=>({'X-Demo-User':user.email,'X-Demo-Role':user.roleCode});
function Table({cols,rows,onOpen}){return <div className="a-table-wrap"><table className="a-table"><thead><tr>{cols.map(x=><th key={x}>{x}</th>)}{onOpen&&<th>Action</th>}</tr></thead><tbody>{rows.map((r,i)=><tr key={r.id||i}>{r.cells.map((v,j)=><td key={j}>{v??'—'}</td>)}{onOpen&&<td><button className="a-link" onClick={()=>onOpen(r)}>Open</button></td>}</tr>)}{!rows.length&&<tr><td colSpan={cols.length+(onOpen?1:0)}>No records. Import a RealTime batch to create the patient database.</td></tr>}</tbody></table></div>}
function Imports({user,onNavigate}){const [batches,setBatches]=useState([]),[msg,setMsg]=useState(''),[msgType,setMsgType]=useState('info'),[busy,setBusy]=useState(false),[dragging,setDragging]=useState(false);const load=()=>listBatches(user).then(setBatches).catch(e=>{setMsg(e.message);setMsgType('error')});useEffect(()=>{load()},[]);useEffect(()=>{if(!batches.some(b=>!['MONITOR_QC_REQUIRED','FAILED','CANCELLED'].includes(b.status)))return;const t=setInterval(()=>{load()},1000);return()=>clearInterval(t)},[batches]);const handleFile=async f=>{if(!f)return;if(!f.name.toLowerCase().endsWith('.csv')){setMsg('Invalid file format. Please upload a RealTime long-form .csv file.');setMsgType('error');return}setBusy(true);setMsg(`Streaming upload: ${f.name} (${(f.size/1024/1024).toFixed(2)} MB)…`);setMsgType('info');try{const newBatch=await uploadRealtime(f,user,setMsg);if(newBatch&&newBatch.id){setBatches(prev=>[newBatch,...prev.filter(x=>x.id!==newBatch.id)])}setMsg(`Batch '${f.name}' accepted. Visit reconstruction pipeline active.`);setMsgType('success');load()}catch(x){setMsg(x.message||'Import failed.');setMsgType('error')}finally{setBusy(false)}};const onDrop=e=>{e.preventDefault();setDragging(false);if(busy)return;const f=e.dataTransfer.files[0];if(f)handleFile(f)};return <Page title="RealTime Batch Imports" desc="Immutable, checksummed source snapshots. Files are streamed and parsed into pseudonymized visit blocks."><div className={`rt-upload ${dragging?'dragging':''}`} onDragOver={e=>{e.preventDefault();setDragging(true)}} onDragLeave={()=>setDragging(false)} onDrop={onDrop}><I.Upload size={32} color={dragging?'#F07E26':'#64748b'}/><b>{dragging?'Drop RealTime CSV snapshot here':'Import RealTime Patient Batch'}</b><span>Drag &amp; drop your approved long-form CSV snapshot here, or click to browse files</span><input type="file" accept=".csv,text/csv" disabled={busy} onChange={e=>{if(e.target.files[0])handleFile(e.target.files[0])}}/></div>{msg&&<div className={`a-notice ${msgType==='error'?'a-notice-error':msgType==='success'?'a-notice-success':''}`} style={{marginBottom:'16px',display:'flex',justify:'space-between',alignItems:'center'}}><div style={{display:'flex',alignItems:'center',gap:'8px'}}><I.Info size={18}/><span>{msg}</span></div>{onNavigate&&msgType==='success'&&<button className="a-primary" style={{fontSize:'11px',padding:'4px 10px'}} onClick={()=>onNavigate('/monitor/reconstruction')}>Inspect Reconstructed Patients →</button>}</div>}<Table cols={['Batch ID','Filename','Stage','Rows processed','Participants','Visits','Excluded blinded','Errors']} rows={(batches||[]).map(b=>({id:b.id,cells:[(b.id||'').slice(0,8)||"—",b.filename||"—",<span style={{fontWeight:700,color:b.status==='MONITOR_QC_REQUIRED'?'#16a34a':b.status==='FAILED'?'#dc2626':'#ea580c'}}>{b.status||"—"}</span>,(b.rows_processed||0).toLocaleString(),b.participants??0,b.visits??0,b.prohibited_excluded??0,b.errors??0]}))}/></Page>}
function ReconstructionQC({user,onOpen}){
  const [data,setData]=useState({items:[],total:0}),[busy,setBusy]=useState(false),[msg,setMsg]=useState('');
  const load=()=>listPatients(user,{page_size:100}).then(setData);
  useEffect(()=>{load()},[]);
  const approveAll=async()=>{
    setBusy(true); setMsg('Approving all visit reconstructions…');
    try{
      for(const p of data.items){
        if(p.qc_status!=='QC_APPROVED'&&p.qc_status!=='ASSIGNED') await approvePatient(p.id,user);
      }
      setMsg('All visit reconstructions QC approved!'); load();
    }catch(e){setMsg(e.message)}finally{setBusy(false)}
  };
  return <Page title="Visit Reconstruction QC" desc="Inspect and verify reconstructed longitudinal visit blocks. Approve packages for adjudicator assignment.">
    <div className="monitor-toolbar" style={{marginBottom:'16px'}}>
      <button className="a-primary" onClick={approveAll} disabled={busy}>
        <I.CheckCheck size={14}/> {busy?'Approving…':'QC Approve All Reconstructions'}
      </button>
    </div>
    {msg&&<div className="a-notice" style={{marginBottom:'16px'}}><I.Info size={18}/><span>{msg}</span></div>}
    <Table cols={['Blinded Subject','Study','Visits Reconstructed','First Visit','Latest Visit','Derivation','Completeness','QC Status','Action']} rows={data.items.map(p=>({
      id:p.id,data:p,
      cells:[
        p.subject_id, p.study, `${p.visit_count} visits`, date(p.first_visit), date(p.latest_visit),
        p.onset_classification, `${Math.round((p.packet_completeness||0)*100)}%`,
        <span style={{fontWeight:700,color:p.qc_status==='QC_APPROVED'||p.qc_status==='ASSIGNED'?'#16a34a':'#d97706'}}>{p.qc_status}</span>,
        <div style={{display:'flex',gap:'6px'}}>
          <button className="a-link" onClick={()=>onOpen(p)}>Inspect</button>
          {p.qc_status==='MONITOR_QC_REQUIRED'&&(
            <button className="a-primary" style={{fontSize:'10px',padding:'3px 8px'}} onClick={async()=>{await approvePatient(p.id,user);load();}}>QC Approve</button>
          )}
        </div>
      ]
    }))}/>
  </Page>;
}

function Assignments({user,onOpen}){
  const [data,setData]=useState({items:[],total:0}),[busy,setBusy]=useState(false),[msg,setMsg]=useState('');
  const load=()=>listPatients(user,{page_size:100}).then(setData);
  useEffect(()=>{load()},[]);
  const demoAdjudicators=[
    {email:'adjudicatora@acrnhealth.com',label:'Adjudicator A (adjudicatora@acrnhealth.com)'},
    {email:'adjudicatorb@acrnhealth.com',label:'Adjudicator B (adjudicatorb@acrnhealth.com)'},
    {email:'adjudicatorc@acrnhealth.com',label:'Adjudicator C (adjudicatorc@acrnhealth.com)'},
  ];
  const doAssign=async(patientId,email,role)=>{
    try{
      await assignPatient(patientId,email,role,user);
      setMsg(`Assigned ${email} as ${role}.`);
      load();
    }catch(e){setMsg(e.message)}
  };
  const autoAssignAll=async()=>{
    setBusy(true); setMsg('Assigning demo adjudicators A & B to all subjects…');
    try{
      for(const p of data.items){
        await assignPatient(p.id,'adjudicatora@acrnhealth.com','REVIEWER_A',user);
        await assignPatient(p.id,'adjudicatorb@acrnhealth.com','REVIEWER_B',user);
      }
      setMsg('Auto-assigned Adjudicator A & Adjudicator B to all participants!');
      load();
    }catch(e){setMsg(e.message)}finally{setBusy(false)}
  };

  return <Page title="Adjudicator Assignments" desc="Assign independent blinded adjudicator accounts (Reviewer A & Reviewer B) to QC-approved participant packages.">
    <div className="monitor-toolbar" style={{marginBottom:'16px'}}>
      <button className="a-primary" onClick={autoAssignAll} disabled={busy}>
        <I.Users size={14}/> {busy?'Assigning…':'Auto-Assign Demo Adjudicators (A & B to All)'}
      </button>
    </div>
    {msg&&<div className="a-notice" style={{marginBottom:'16px'}}><I.Info size={18}/><span>{msg}</span></div>}
    <Table cols={['Blinded Subject','Visits','Derivation','QC Status','Reviewer A','Reviewer B','Actions']} rows={data.items.map(p=>{
      const revA = (p.assignments||[]).find(a=>a.reviewer_role==='REVIEWER_A')?.reviewer_upn || '';
      const revB = (p.assignments||[]).find(a=>a.reviewer_role==='REVIEWER_B')?.reviewer_upn || '';
      return {
        id:p.id,data:p,
        cells:[
          p.subject_id, `${p.visit_count} visits`, p.onset_classification,
          <span style={{fontWeight:700,color:p.qc_status==='ASSIGNED'?'#16a34a':'#3b82f6'}}>{p.qc_status}</span>,
          <select value={revA} onChange={e=>doAssign(p.id,e.target.value,'REVIEWER_A')} style={{padding:'4px 8px',borderRadius:'4px',fontSize:'11px'}}>
            <option value="">-- Assign Reviewer A --</option>
            {demoAdjudicators.map(a=><option key={a.email} value={a.email} disabled={a.email===revB}>{a.label}</option>)}
          </select>,
          <select value={revB} onChange={e=>doAssign(p.id,e.target.value,'REVIEWER_B')} style={{padding:'4px 8px',borderRadius:'4px',fontSize:'11px'}}>
            <option value="">-- Assign Reviewer B --</option>
            {demoAdjudicators.map(a=><option key={a.email} value={a.email} disabled={a.email===revA}>{a.label}</option>)}
          </select>,
          <button className="a-link" onClick={()=>onOpen(p)}>View Package</button>
        ]
      };
    })}/>
  </Page>;
}

function Patients({user,onOpen}){const [data,setData]=useState({items:[],total:0}),[q,setQ]=useState('');useEffect(()=>{listPatients(user,{search:q,page_size:100}).then(setData)},[q]);return <Page title="Longitudinal Patient Database" desc="Pseudonymised participants from QC-controlled RealTime batches."><div className="monitor-toolbar"><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search blinded subject ID"/></div><Table cols={['Blinded subject','Study','Visits','First visit','Latest visit','Derived onset','Severity','Completeness','Issues','QC']} rows={data.items.map(p=>({id:p.id,data:p,cells:[p.subject_id,p.study,p.visit_count,date(p.first_visit),date(p.latest_visit),p.onset_classification,p.maximum_severity,`${Math.round((p.packet_completeness||0)*100)}%`,p.open_issues,p.qc_status]}))} onOpen={onOpen}/></Page>}

function Timeline({patient,user,onClose}){
  if(!patient)return null;
  const [assignRole,setAssignRole]=useState('REVIEWER_A');
  const [selectedAdjudicator,setSelectedAdjudicator]=useState('adjudicatora@acrnhealth.com');
  const [msg,setMsg]=useState('');
  const approve=async()=>{try{await approvePatient(patient.id,user);setMsg('Participant package QC approved.')}catch(e){setMsg(e.message)}};
  const assign=async()=>{
    try{
      await assignPatient(patient.id,selectedAdjudicator,assignRole,user);
      setMsg(`Assigned ${selectedAdjudicator} as ${assignRole}.`);
    }catch(e){setMsg(e.message)}
  };
  return <Page title={`Participant ${patient.subject_id}`} desc="Visit-by-visit source evidence and cumulative PE support.">
    <div className="monitor-toolbar" style={{alignItems:'center',gap:'8px',flexWrap:'wrap'}}>
      <button onClick={onClose}><I.ArrowLeft size={14}/> Back</button>
      <button className="a-primary" onClick={approve}>Approve Package QC</button>
      <div style={{display:'flex',alignItems:'center',gap:'6px',background:'#f1f5f9',padding:'4px 8px',borderRadius:'6px'}}>
        <select value={assignRole} onChange={e=>setAssignRole(e.target.value)} style={{fontSize:'11px',padding:'4px'}}>
          <option value="REVIEWER_A">Reviewer A</option>
          <option value="REVIEWER_B">Reviewer B</option>
        </select>
        <select value={selectedAdjudicator} onChange={e=>setSelectedAdjudicator(e.target.value)} style={{fontSize:'11px',padding:'4px'}}>
          <option value="adjudicatora@acrnhealth.com">adjudicatora@acrnhealth.com (Adjudicator A)</option>
          <option value="adjudicatorb@acrnhealth.com">adjudicatorb@acrnhealth.com (Adjudicator B)</option>
          <option value="adjudicatorc@acrnhealth.com">adjudicatorc@acrnhealth.com (Adjudicator C)</option>
        </select>
        <button className="a-primary" style={{fontSize:'11px',padding:'4px 8px'}} onClick={assign}>Assign Adjudicator</button>
      </div>
    </div>
    {msg&&<div className="a-notice" style={{marginTop:'8px',marginBottom:'12px'}}><I.Info size={16}/><span>{msg}</span></div>}
    {patient.longitudinal&&<div className="a-notice"><I.Activity/><div><strong>Longitudinal advisory</strong><span>{patient.longitudinal.explanation}</span></div></div>}
    <div className="rt-timeline">{patient.visits.map(v=><details key={v.id}><summary><b>{v.name} · occurrence {v.occurrence}</b><span>{date(v.date)} · {v.reconstruction.confidence} reconstruction · {v.reconstruction.qc_status}</span></summary><Table cols={['Variable','Value','Observed','Date confidence','Provenance','Source']} rows={Object.entries(v.evidence).flatMap(([k,a])=>a.map((x,i)=>({id:k+i,cells:[k,String(x.value??'—'),date(x.observed_at),x.date_confidence,x.provenance,`${x.source.form} / ${x.source.page} / row ${x.source.row}`]})))}/></details>)}</div>
  </Page>;
}

function Page({title,desc,children}){return <><div className="a-page-head"><div><h1>{title}</h1><p>{desc}</p></div></div>{children}</>};const date=x=>x?new Date(x).toLocaleDateString():'—';
class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  componentDidCatch(error, errorInfo) { console.error("Monitor error:", error, errorInfo); }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '30px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#991b1b', margin: '20px' }}>
          <h3 style={{ margin: 0, marginBottom: '8px' }}>⚠ Import View Notice</h3>
          <p>{this.state.error?.message || 'A render exception occurred.'}</p>
          <button className="a-primary" style={{ marginTop: '12px' }} onClick={() => { this.setState({ hasError: false }); location.reload(); }}>Reload Monitor Portal</button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function MonitorPortal({user,onLogout}){
  const [path,setPath]=useState(location.pathname),[selected,setSelected]=useState(null);
  const go=p=>{history.pushState({},'',p);setPath(p);setSelected(null)};
  const open=async r=>setSelected(await getPatient(r.id,user));
  let content=selected?<Timeline patient={selected} user={user} onClose={()=>setSelected(null)}/>
    :path==='/monitor/imports'?<Imports user={user} onNavigate={go}/>
    :path==='/monitor/reconstruction'?<ReconstructionQC user={user} onOpen={open}/>
    :path==='/monitor/assignments'?<Assignments user={user} onOpen={open}/>
    :path==='/monitor/patients'||path==='/monitor/longitudinal'?<Patients user={user} onOpen={open}/>
    :<Page title="Monitor / QC Dashboard" desc="Import, reconstruct, derive, approve and assign longitudinal patient packages.">
      <div className="a-notice"><I.Shield/><div><strong>Clinical operations boundary</strong><span>Identifiers and prohibited biomarker content are excluded from adjudicator packages. Monitor actions are audited.</span></div></div>
      <div style={{display:'flex',gap:'10px',marginTop:'16px'}}>
        <button className="a-primary" onClick={()=>go('/monitor/imports')}>Import RealTime batch</button>
        <button className="a-primary" style={{background:'#2563eb'}} onClick={()=>go('/monitor/reconstruction')}>Visit Reconstruction QC</button>
        <button className="a-primary" style={{background:'#059669'}} onClick={()=>go('/monitor/assignments')}>Adjudicator Assignments</button>
      </div>
     </Page>;
  return <div className="admin-app"><header className="a-header"><div className="a-brand"><span><img src="/acrn-logo.png"/></span><div><strong>ACRN Adjudication Platform</strong><small>Monitor / Quality Control Portal</small></div></div><div className="a-boundary"><I.EyeOff/> No adjudication authority</div><div className="a-user"><div><strong>{user.name}</strong><small>{user.role}</small></div><button onClick={onLogout}><I.LogOut/></button></div></header><div className="a-body"><aside className="a-nav"><section><h2>LONGITUDINAL OPERATIONS</h2>{nav.map(([p,l,n])=>{let C=I[n];return <button className={path===p?'active':''} onClick={()=>go(p)} key={p}><C/><span>{l}</span></button>})}</section></aside><main className="a-main"><ErrorBoundary>{content}</ErrorBoundary></main></div></div>
}
