const BASE=(import.meta.env.VITE_API_BASE_URL||'/api').replace(/\/$/,'')+'/realtime';
const headers=(user)=>user?({'X-Demo-User':user.email,'X-Demo-Role':user.roleCode}):({});
async function request(path,user,options={}){const r=await fetch(BASE+path,{...options,credentials:'include',headers:{...headers(user),...(options.headers||{})}});if(!r.ok){let x;try{x=await r.json()}catch{x={}}throw new Error(typeof x.detail==='string'?x.detail:x.detail?.message||`Request failed (${r.status})`)}return r.json()}
export const listBatches=(user)=>request('/batches',user);
export const getBatch=(id,user)=>request(`/batches/${id}`,user);
export const listPatients=(user,params={})=>request(`/patients?${new URLSearchParams(params)}`,user);
export const getPatient=(id,user)=>request(`/patients/${id}`,user);
export const approvePatient=(id,user)=>request(`/patients/${id}/approve`,user,{method:'POST'});
export const assignPatient=(id,email,role,user)=>request(`/patients/${id}/assign?${new URLSearchParams({reviewer_upn:email,reviewer_role:role})}`,user,{method:'POST'});
export const listAssigned=(user)=>request('/assigned',user);
export const getAssigned=(id,user)=>request(`/assigned/${id}`,user);
export async function uploadRealtime(file,user,onProgress){const body=new FormData();body.append('file',file);onProgress?.('Uploading');return request('/batches',user,{method:'POST',body})}
export function asWorkbenchCase(data, user){
 const values=(name)=>data.visits?.flatMap(v=>(v.evidence?.[name]||[]).map(x=>({...x,visit:v.name})))||[];
 const first=n=>values(n)[0]?.value;
 const bps=values('SBP').map((x,i)=>({sbp:Number(x.value),dbp:Number(values('DBP')[i]?.value)||null,datetime:x.observed_at,visit:x.visit}));
 const userUpn=(user?.email||'').trim().toLowerCase();
 const assignment=(data.assignments||[]).find(a=>(a.reviewer_upn||'').trim().toLowerCase()===userUpn) || data.assignments?.[0];
 return {id:data.subject_id,databaseId:data.id,caseNo:`ADJ-${data.subject_id.slice(-6)}`,site:'Blinded site',status:data.qc_status||'Assigned',study:data.study,pktScore:data.packet_completeness||0,gaAtEvent:data.longitudinal?.onset_classification||'Unclassifiable',derivedSubtype:data.longitudinal?.onset_classification||'UNCLASSIFIABLE',derivedSeverity:data.longitudinal?.maximum_severity||'NOT_ASSESSABLE',trigger:data.longitudinal?.trigger_status||'DV-30 pending',reviewerRole:assignment?.reviewer_role || 'REVIEWER_A',bp_readings:bps,upcr:first('UPCR'),dipstick_raw:first('DIPSTICK_PROTEIN'),platelet_count:first('PLATELETS'),creatinine:first('CREATININE'),ast:first('AST'),alt:first('ALT'),ldh:first('LDH'),delivery_date:first('DELIVERY_DATE'),visits:data.visits||[],longitudinal:data.longitudinal,provenance:'SOURCE_RECORDED'};
}
