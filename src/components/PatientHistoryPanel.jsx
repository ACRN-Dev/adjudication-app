import React, { useState } from 'react';
import * as I from 'lucide-react';

function TriStateBadge({ value }) {
  if (value === 'Yes') return <span style={{ background: '#fef2f2', color: '#991b1b', padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>Yes</span>;
  if (value === 'No') return <span style={{ background: '#f8fafc', color: '#475569', padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>No</span>;
  if (value === 'Not known' || value === 'Unknown') return <span style={{ background: '#f1f5f9', color: '#64748b', padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>Not known</span>;
  return <span>{value || '—'}</span>;
}

function AmberFlag({ reason }) {
  return (
    <span title={reason} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#b45309', background: '#fef3c7', padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, marginLeft: '8px' }}>
      <I.AlertTriangle size={12} /> Flag
    </span>
  );
}

function HistoryTable({ title, items, columns, renderRow }) {
  if (!items || items.length === 0) return null;
  return (
    <div style={{ marginBottom: '16px' }}>
      <h4 style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#334155', display: 'flex', alignItems: 'center', gap: '6px' }}>
        {title}
      </h4>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#64748b', textAlign: 'left' }}>
            {columns.map((c, i) => <th key={i} style={{ padding: '6px 8px', fontWeight: 600 }}>{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
              {renderRow(item).map((cell, j) => <td key={j} style={{ padding: '6px 8px', color: '#334155' }}>{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PatientHistoryPanel({ caseData }) {
  const { history = {}, risk_summary = {} } = caseData;
  const [expanded, setExpanded] = useState(true); // Always expanded by default, or collapse if empty

  const medCondsRaw = history.medical || [];
  // Group medical conditions by instance
  const medInstances = {};
  medCondsRaw.forEach(f => {
    if (f.instance !== null) {
      if (!medInstances[f.instance]) medInstances[f.instance] = { instance: f.instance, amber: false };
      medInstances[f.instance][f.key] = f.value;
      if (f.amber_flag) medInstances[f.instance].amber = true;
    }
  });
  const medConds = Object.values(medInstances).sort((a, b) => {
    if (a.end_date && !b.end_date) return 1;
    if (!a.end_date && b.end_date) return -1;
    return 0;
  });

  const getVal = (domain, key) => {
    const f = (history[domain] || []).find(x => x.key === key);
    return f ? { val: f.value, amber: f.amber_flag, reason: f.flag_reason } : { val: null };
  };

  return (
    <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', marginBottom: '24px', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
      <div 
        style={{ padding: '12px 16px', borderBottom: expanded ? '1px solid #e2e8f0' : 'none', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', background: '#f8fafc', borderTopLeftRadius: '8px', borderTopRightRadius: '8px' }}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: '#0f172a' }}>
            <I.ClipboardList size={16} color="#64748b" /> Patient History
          </div>
          {risk_summary.chips?.length > 0 && (
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {risk_summary.chips.map(c => (
                <span key={c} style={{ background: '#fee2e2', color: '#991b1b', border: '1px solid #fca5a5', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600 }}>
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>
        <I.ChevronDown size={18} color="#64748b" style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
      </div>

      {expanded && (
        <div style={{ padding: '16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          
          {/* Obstetric History */}
          <div>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <I.Baby size={16} color="#3b82f6" /> Obstetric History
            </h3>
            {risk_summary.parity_summary && (
              <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', color: '#1e40af', padding: '8px 12px', borderRadius: '6px', fontWeight: 700, fontFamily: 'monospace', fontSize: '13px', marginBottom: '12px', display: 'inline-block' }}>
                {risk_summary.parity_summary}
              </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
              {['preeclampsia', 'severe_preeclampsia', 'eclampsia', 'hellp', 'iugr', 'raised_blood_pressure_during_pregnancy'].map(cond => {
                const f = (history.obstetric || []).find(x => x.key.includes(cond) && x.key.includes('history'));
                if (!f) return null;
                return (
                  <div key={cond} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed #e2e8f0', paddingBottom: '4px' }}>
                    <span style={{ color: '#475569' }}>{f.label.replace('Does the participant have any history of ', '').replace(' in previous pregnancies?', '')}</span>
                    <div>
                      <TriStateBadge value={f.value} />
                      {f.amber_flag && <AmberFlag reason={f.flag_reason} />}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Medical Conditions */}
          <div>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <I.Activity size={16} color="#10b981" /> Medical Conditions
            </h3>
            {medConds.length === 0 ? (
              <span style={{ fontSize: '12px', color: '#64748b' }}>No medical conditions reported.</span>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {medConds.map(mc => (
                  <div key={mc.instance} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '8px 12px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <strong style={{ color: '#0f172a' }}>{mc.medical_condition || 'Unknown Condition'}</strong>
                      <span style={{ color: mc.end_date ? '#64748b' : '#059669', fontWeight: mc.end_date ? 400 : 600 }}>
                        {mc.end_date ? 'Resolved' : 'Ongoing'}
                      </span>
                    </div>
                    <div style={{ color: '#475569', display: 'flex', gap: '12px' }}>
                      <span>Started: {mc.start_date || '—'}</span>
                      {mc.end_date && <span>Ended: {mc.end_date}</span>}
                      <span>Severity: {mc.severity || '—'}</span>
                    </div>
                    {mc.amber && <div style={{ marginTop: '4px' }}><AmberFlag reason="Incomplete detail" /></div>}
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
