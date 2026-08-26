import React from 'react';
import * as I from 'lucide-react';

const fmt = value => value ? new Date(value).toLocaleString() : 'Not documented';
const values = (evidence, names) => names.flatMap(name => (evidence?.[name] || []).map(row => ({ name, ...row })));

function SummaryLine({ label, value, warning = false }) {
  return <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '7px 0', borderBottom: '1px solid #f1f5f9' }}><span style={{ color: '#64748b', fontSize: 12 }}>{label}</span><strong style={{ color: warning ? '#991b1b' : '#0f172a', fontSize: 12, textAlign: 'right' }}>{value || 'Not documented'}</strong></div>;
}

function VisitSummary({ visit }) {
  const evidence = visit?.evidence || {};
  const bp = values(evidence, ['SBP', 'DBP']);
  const labs = values(evidence, ['PLATELETS', 'CREATININE', 'AST', 'ALT', 'LDH']);
  const protein = values(evidence, ['UPCR', 'DIPSTICK_PROTEIN']);
  const severeBp = bp.find(row => Number(row.value) >= 160 || Number(row.value) >= 110);
  const abnormalLabs = labs.filter(row => row.abnormal === true || row.severe === true);
  return <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(210px,1fr))', gap: 12 }}>
    <div><h5 style={{ margin: '0 0 4px', color: '#334155' }}><I.Activity size={14}/> Blood pressure</h5><SummaryLine label="Summary" value={severeBp ? 'Severe-range reading documented' : bp.length ? 'BP documented; no severe-range flag' : null} warning={!!severeBp}/><SummaryLine label="Latest observation" value={fmt(bp[0]?.observed_at || visit?.date)}/></div>
    <div><h5 style={{ margin: '0 0 4px', color: '#334155' }}><I.Database size={14}/> Labs & proteinuria</h5><SummaryLine label="Proteinuria" value={protein.length ? 'Protein result documented' : null}/><SummaryLine label="Laboratory pattern" value={abnormalLabs.length ? `${abnormalLabs.length} abnormal result(s) flagged` : labs.length ? 'Results documented; no abnormal flag' : null} warning={!!abnormalLabs.length}/></div>
    <div><h5 style={{ margin: '0 0 4px', color: '#334155' }}><I.Calendar size={14}/> Visit timing</h5><SummaryLine label="Visit date" value={fmt(visit?.date || visit?.visit_date)}/><SummaryLine label="Gestational age" value={visit?.ga || visit?.gestational_age || null}/></div>
    {/V05|visit\s*5/i.test(visit?.name || visit?.visit_code || '') && <div><h5 style={{ margin: '0 0 4px', color: '#334155' }}><I.HeartPulse size={14}/> Delivery / outcomes</h5><SummaryLine label="Outcome evidence" value="Available in source evidence viewer"/></div>}
  </div>;
}

export default function VisitEvidenceSections({ visits, selectedIndex = 0, onSelectVisit }) {
  if (!visits?.length) return <div className="summary-feature-card"><strong>No visit-level summary is available.</strong><p style={{ color: '#64748b', fontSize: 12 }}>The coordinator must reconcile the visit packet before adjudication.</p></div>;
  const index = Math.min(selectedIndex, visits.length - 1);
  const selected = visits[index];
  return <div className="summary-feature-card" style={{ gridColumn: '1 / -1' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}><h4 style={{ margin: 0 }}><I.ClipboardList color="var(--acrn-navy-dark)" size={16}/> Visit-level clinical summary</h4><select aria-label="Select visit for adjudication" value={index} onChange={e => onSelectVisit?.(Number(e.target.value))} style={{ minWidth: 220 }}>{visits.map((visit, i) => <option key={visit.id || i} value={i}>{visit.name || visit.visit_code || `Visit ${i + 1}`} {visit.date ? `— ${new Date(visit.date).toLocaleDateString()}` : ''}</option>)}</select></div>
    <div style={{ marginTop: 10, padding: '10px 12px', background: '#f8fafc', borderRadius: 6 }}><strong style={{ color: '#0f172a' }}>{selected.name || selected.visit_code || `Visit ${index + 1}`}</strong><span style={{ color: '#64748b', fontSize: 12, marginLeft: 10 }}>{fmt(selected.date || selected.visit_date)}</span><div style={{ marginTop: 10 }}><VisitSummary visit={selected}/></div></div>
    <p style={{ margin: '10px 0 0', fontSize: 11, color: '#64748b' }}><I.EyeOff size={12}/> This is a synthesized clinical summary. Raw values and source provenance are available only through “Inspect Raw Docs”.</p>
  </div>;
}
