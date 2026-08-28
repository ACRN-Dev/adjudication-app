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

function cleanHistoryLabel(label = '') {
  return String(label)
    .replace(/^Does (the )?participant (have|had) (any )?/i, '')
    .replace(/^Did (the )?participant (have|had) (any )?/i, '')
    .replace(/^If yes,?\s*/i, '')
    .replace(/\?$/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function findExactField(fields, keys) {
  const wanted = Array.isArray(keys) ? keys : [keys];
  return fields.find(f => wanted.includes(String(f.key || '')));
}

function fieldHasValue(field) {
  return field && field.value != null && String(field.value).trim() !== '';
}

function isSystemHistoryField(field) {
  const key = String(field?.key || '');
  const label = String(field?.label || '').toLowerCase();
  return /electronic_signature|signature_lock|file_upload|upload|audit|facility|source_file/.test(key) || /electronic signature|file upload|facility/.test(label);
}

function HistoryValue({ field, fallback = null }) {
  if (!field && fallback == null) return <span style={{ color: '#94a3b8' }}>Not documented</span>;
  if (fallback != null && String(fallback).trim() !== '') return <>{fallback}{field?.amber_flag && <AmberFlag reason={field.flag_reason} />}</>;
  if (field?.value === 'Yes' || field?.value === 'No' || field?.value === 'Not known' || field?.value === 'Unknown') {
    return <>{<TriStateBadge value={field.value} />}{field.amber_flag && <AmberFlag reason={field.flag_reason} />}</>;
  }
  return <>{field?.value ?? fallback}{field?.amber_flag && <AmberFlag reason={field.flag_reason} />}</>;
}

function ObstetricHistoryTable({ fields = [], riskSummary = {} }) {
  const safeFields = fields.filter(f => !isSystemHistoryField(f));
  const previousPregnancyGate = findExactField(safeFields, 'has_participant_had_any_previous_pregnancies');
  const previousPregnancyCount = findExactField(safeFields, 'if_yes_how_many_previous_pregnancies');
  const cSectionGate = findExactField(safeFields, [
    'did_the_participant_have_any_cesarean_sections',
    'did_the_participant_have_any_caesarean_sections',
  ]);
  const cSectionCount = findExactField(safeFields, [
    'number_of_cesarean_sections',
    'number_of_caesarean_sections',
  ]);
  const cSectionReason = findExactField(safeFields, [
    'reason_for_cesarean_section',
    'reason_for_caesarean_section',
  ]);
  const rows = [
    ['Previous pregnancies', previousPregnancyGate || previousPregnancyCount, previousPregnancyGate ? (fieldHasValue(previousPregnancyCount) ? `${previousPregnancyGate.value}, ${previousPregnancyCount.value} previous pregnancies` : previousPregnancyGate.value) : previousPregnancyCount?.value, 'Source recorded'],
    ['Gravidity', null, riskSummary.gravidity, 'Derived from structured history'],
    ['Parity', null, riskSummary.parity, 'Derived from structured history'],
    ['Live births', findExactField(safeFields, 'number_of_live_births'), riskSummary.parity, 'Source recorded'],
    ['Miscarriages', findExactField(safeFields, 'number_of_miscarriages'), riskSummary.miscarriages, 'Source recorded'],
    ['Stillbirth / IUFD', findExactField(safeFields, ['number_of_still_births', 'number_of_stillbirths']), riskSummary.stillbirths, 'Source recorded'],
    ['Vaginal deliveries', findExactField(safeFields, 'number_of_vaginal_deliveries'), riskSummary.vaginal_deliveries, 'Source recorded'],
    ['Caesarean sections', cSectionGate || cSectionCount, cSectionGate?.value || cSectionCount?.value || riskSummary.c_sections, 'Source recorded'],
    ...(fieldHasValue(cSectionReason) || cSectionGate?.amber_flag ? [['Reason for caesarean section', cSectionReason || cSectionGate, cSectionReason?.value || '', cSectionGate?.amber_flag ? 'Required because caesarean section gate is Yes' : 'Source recorded']] : []),
    ['Previous pre-eclampsia', findExactField(safeFields, 'does_the_participant_have_any_history_of_preeclampsia_in_previous_pregnancies'), null, 'Source recorded'],
    ['Previous severe pre-eclampsia', findExactField(safeFields, 'does_the_participant_have_any_history_of_severe_preeclampsia_in_previous_pregnancies'), null, 'Source recorded'],
    ['Previous eclampsia', findExactField(safeFields, 'does_the_participant_have_any_history_of_eclampsia_in_previous_pregnancies'), null, 'Source recorded'],
    ['Previous HELLP', findExactField(safeFields, 'does_the_participant_have_any_history_of_hellp_in_previous_pregnancies'), null, 'Source recorded'],
    ['Previous IUGR', findExactField(safeFields, 'does_the_participant_have_any_history_of_iugr_in_previous_pregnancies') || findExactField(safeFields, 'did_the_participant_have_iugr_in_a_previous_pregnancy'), null, 'Source recorded'],
    ['Raised BP during pregnancy', findExactField(safeFields, 'does_participant_have_any_history_of_raised_blood_pressure_during_pregnancy'), null, 'Source recorded'],
  ].filter(([label, field, fallback]) => field || fallback != null);

  const consumedKeys = new Set([
    previousPregnancyGate?.key,
    previousPregnancyCount?.key,
    cSectionGate?.key,
    cSectionCount?.key,
    cSectionReason?.key,
    ...rows.map(([, field]) => field?.key),
  ].filter(Boolean));
  const extra = safeFields.filter(f => !consumedKeys.has(f.key) && fieldHasValue(f));

  return (
    <div className="history-clinical-table-wrap">
      {riskSummary.parity_summary && <div className="history-parity-line">Obstetric summary: {riskSummary.parity_summary}</div>}
      <table className="history-clinical-table">
        <thead><tr><th>Item</th><th>Recorded value</th><th>Source field</th></tr></thead>
        <tbody>
          {rows.map(([label, field, fallback, note]) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              <td><HistoryValue field={field} fallback={fallback} /></td>
              <td>{note || (field ? cleanHistoryLabel(field.label) : 'Derived from structured history')}</td>
            </tr>
          ))}
          {extra.map(field => (
            <tr key={field.key}>
              <th scope="row">{cleanHistoryLabel(field.label)}</th>
              <td><HistoryValue field={field} /></td>
              <td>Additional obstetric history</td>
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

  const medCondsRaw = history.conditions || history.medical || [];
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

  // Group Medications (Prior & Concomitant Medications form) by instance, pulled straight from source data.
  const medicationsRaw = history.medications || [];
  const medicationInstances = {};
  medicationsRaw.forEach(f => {
    if (f.instance !== null) {
      if (!medicationInstances[f.instance]) medicationInstances[f.instance] = { instance: f.instance, amber: false };
      medicationInstances[f.instance][f.key] = f.value;
      if (f.amber_flag) medicationInstances[f.instance].amber = true;
    }
  });
  const medications = Object.values(medicationInstances).map(m => {
    const ongoing = String(m.ongoing || m.ongoing_flag || m.is_ongoing || '').toLowerCase();
    const stop = m.stop_date || m.end_date;
    return { ...m, medication_status: ongoing === 'yes' || !stop ? 'CURRENT' : 'PRIOR' };
  }).sort((a, b) => a.medication_status === b.medication_status ? 0 : a.medication_status === 'CURRENT' ? -1 : 1);

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
          <div style={{ gridColumn: '1 / -1' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <I.Baby size={16} color="#3b82f6" /> Obstetric History
            </h3>
            <ObstetricHistoryTable fields={history.obstetric || []} riskSummary={risk_summary} />
          </div>

          {/* Medical Conditions */}
          <div>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <I.Activity size={16} color="#10b981" /> Medical Conditions
            </h3>
            {medConds.length === 0 ? (
              <span style={{ fontSize: '12px', color: '#64748b' }}>No medical condition, surgery, allergy or family-history detail is available in the source history extract.</span>
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
                    <div style={{ color: '#475569', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                      {mc.body_system && <span>Body system: {mc.body_system}</span>}
                      <span>Started: {mc.start_date || '—'}</span>
                      {mc.end_date && <span>Ended: {mc.end_date}</span>}
                    </div>
                    {mc.amber && <div style={{ marginTop: '4px' }}><AmberFlag reason="Incomplete detail" /></div>}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Medications — pulled straight from source RealTime data (Prior & Concomitant Medications form) */}
          <div style={{ gridColumn: '1 / -1' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <I.Pill size={16} color="#7c3aed" /> Medications
            </h3>
            {medications.length === 0 ? (
              <span style={{ fontSize: '12px', color: '#64748b' }}>No prior or concomitant medications reported in source data.</span>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {medications.map(m => {
                  const name = m.medication_name || m.drug_name || m.name_of_medication || m.drug || 'Unspecified medication';
                  const skip = new Set(['instance', 'amber', 'medication_name', 'drug_name', 'name_of_medication', 'drug', 'medication_status']);
                  const details = Object.entries(m).filter(([k, v]) => !skip.has(k) && v != null && v !== '');
                  return (
                    <div key={m.instance} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '8px 12px', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
                        <strong style={{ color: '#0f172a' }}>{name}</strong>
                        <span style={{ background: m.medication_status === 'CURRENT' ? '#ecfdf5' : '#f1f5f9', color: m.medication_status === 'CURRENT' ? '#166534' : '#475569', border: '1px solid #cbd5e1', borderRadius: '999px', padding: '2px 8px', fontSize: '10px', fontWeight: 700 }}>{m.medication_status}</span>
                      </div>
                      {details.length > 0 && (
                        <div style={{ color: '#475569', display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '4px' }}>
                          {details.map(([k, v]) => (
                            <span key={k}>{k.replace(/_/g, ' ')}: {String(v)}</span>
                          ))}
                        </div>
                      )}
                      {m.amber && <div style={{ marginTop: '4px' }}><AmberFlag reason="Incomplete detail" /></div>}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
