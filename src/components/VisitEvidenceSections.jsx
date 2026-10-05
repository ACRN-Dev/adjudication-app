import React, { useState } from 'react';
import * as I from 'lucide-react';
import {
  buildDemographicString,
  buildLongitudinalRows,
  formatInterval,
  formatLabResult,
  formatVisitDate,
  formatVisitDateTime,
  inferLabInterpretation,
  isReviewerVisitSigned,
  isVisitComplete,
  normalizeVisitEvidence,
  pairBpReadings,
  statusLabel,
  visitLabel,
  getLabReferenceRange,
} from '../services/visitEvidence';
import { generateVisitNarrative, generateOverallNarrative } from '../services/clinicalNarrative';

const stateIcon = {
  available: I.CheckCircle2,
  normal: I.CheckCircle2,
  abnormal: I.AlertTriangle,
  severe: I.AlertOctagon,
  not_available: I.MinusCircle,
  pending: I.Clock3,
  blinded: I.EyeOff,
  conflicting: I.MessageSquareWarning,
};

export function EvidenceStatusBadge({ state = 'available', label }) {
  const Icon = stateIcon[state] || I.CheckCircle2;
  const isNorm = state === 'normal' || state === 'available';
  const isWarn = state === 'abnormal';
  const isSevere = state === 'severe';
  
  let bg = '#f1f5f9';
  let color = '#475569';
  let border = '#cbd5e1';

  if (isNorm) {
    bg = '#f0fdf4';
    color = '#15803d';
    border = '#bbf7d0';
  } else if (isWarn) {
    bg = '#fffbeb';
    color = '#b45309';
    border = '#fde68a';
  } else if (isSevere) {
    bg = '#fef2f2';
    color = '#b91c1c';
    border = '#fca5a5';
  }

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '11px',
      fontWeight: 600,
      background: bg,
      color: color,
      border: `1px solid ${border}`,
      whiteSpace: 'nowrap'
    }}>
      <Icon size={12} />
      {label || statusLabel(state)}
    </span>
  );
}

export function VisitRibbon({ visits = [], selectedIndex = 0, onSelectVisit, showOverall = true }) {
  const expectedVisits = visits.slice(0, 6);
  const isOverallSelected = selectedIndex >= expectedVisits.length;

  return (
    <nav className="visit-ribbon-wrap" aria-label="Adjudication visits" style={{ marginBottom: '16px' }}>
      <div className="visit-ribbon" style={{
        display: 'flex',
        gap: '6px',
        background: '#ffffff',
        padding: '6px',
        borderRadius: '8px',
        border: '1px solid var(--border-strong, #cbd5e1)',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        overflowX: 'auto'
      }}>
        {expectedVisits.map((visit, index) => {
          const vNum = index + 1;
          const isSelected = selectedIndex === index;
          const isPostDelivery = vNum >= 5;
          const title = visit.name || visit.visit_code || `Visit ${vNum}`;

          return (
            <button
              key={visit.id || `v-${index}`}
              type="button"
              onClick={() => onSelectVisit?.(index)}
              style={{
                flex: '1 1 0px',
                minWidth: '130px',
                padding: '8px 12px',
                borderRadius: '6px',
                border: isPostDelivery 
                  ? (isSelected ? '2px solid #8b5cf6' : '1px solid #c4b5fd')
                  : (isSelected ? '2px solid var(--acrn-orange-primary, #F07E26)' : '1px solid var(--border-strong, #cbd5e1)'),
                borderBottom: isPostDelivery ? '3px solid #8b5cf6' : undefined,
                background: isPostDelivery 
                  ? (isSelected ? '#f5f3ff' : '#faf5ff')
                  : (isSelected ? 'var(--acrn-orange-soft, #fff8f3)' : '#ffffff'),
                boxShadow: isSelected 
                  ? (isPostDelivery ? '0 0 0 1px #8b5cf6 inset' : '0 0 0 1px var(--acrn-orange-primary, #F07E26) inset') 
                  : 'none',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.15s ease',
                display: 'flex',
                flexDirection: 'column',
                gap: '2px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{
                  fontWeight: 700,
                  fontSize: '12.5px',
                  color: isSelected 
                    ? (isPostDelivery ? '#7c3aed' : 'var(--acrn-orange-primary, #F07E26)') 
                    : 'var(--acrn-navy-dark, #162035)'
                }}>
                  {title}
                </span>
                {isPostDelivery && (
                  <span style={{ 
                    fontSize: '9.5px', 
                    fontWeight: 700, 
                    padding: '1px 5px', 
                    borderRadius: '3px', 
                    background: '#f3e8ff', 
                    color: '#6b21a8', 
                    border: '1px solid #c084fc' 
                  }}>
                    {vNum === 5 ? 'DELIVERY' : 'POSTNATAL'}
                  </span>
                )}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted, #64748b)' }}>
                {formatVisitDate(visit.date || visit.visit_date)}
              </div>
              <div style={{ fontSize: '10.5px', fontWeight: 600, color: isPostDelivery ? '#7c3aed' : 'var(--acrn-sky-blue, #4771AD)' }}>
                {(visit.gestationalLabel && !/unclassifiable|null|undefined/i.test(String(visit.gestationalLabel)))
                  ? visit.gestationalLabel
                  : (visit.ga && !/unclassifiable|null|undefined/i.test(String(visit.ga)) ? visit.ga : 'Age not available')}
              </div>
            </button>
          );
        })}

        {showOverall && (
          <button
            type="button"
            onClick={() => onSelectVisit?.(expectedVisits.length)}
            style={{
              flex: '1 1 0px',
              minWidth: '140px',
              padding: '8px 12px',
              borderRadius: '6px',
              border: isOverallSelected ? '2px solid var(--acrn-orange-primary, #F07E26)' : '1px solid var(--border-strong, #cbd5e1)',
              background: isOverallSelected ? 'var(--acrn-orange-soft, #fff8f3)' : '#ffffff',
              boxShadow: isOverallSelected ? '0 0 0 1px var(--acrn-orange-primary, #F07E26) inset' : 'none',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'all 0.15s ease',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ 
                fontWeight: 700, 
                fontSize: '12.5px', 
                color: isOverallSelected ? 'var(--acrn-orange-primary, #F07E26)' : 'var(--acrn-navy-dark, #162035)' 
              }}>
                Overall Summary
              </span>
              <I.CheckCircle2 size={13} color={isOverallSelected ? 'var(--acrn-orange-primary, #F07E26)' : 'var(--acrn-teal-accent, #82CFCD)'} />
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted, #64748b)' }}>
              V1–V6 Longitudinal
            </div>
            <div style={{ fontSize: '10.5px', fontWeight: 600, color: isOverallSelected ? 'var(--acrn-orange-primary, #F07E26)' : 'var(--acrn-navy-base, #1e2d45)' }}>
              ISSHP Evaluation
            </div>
          </button>
        )}
      </div>
    </nav>
  );
}

// Clean Medical Vitals Strip Component
export function ClinicalVitalsStrip({ vitals, ga }) {
  if (!vitals) return null;

  if (vitals.notCaptured) {
    return (
      <div style={{
        background: '#fffbeb',
        border: '1px solid #fde68a',
        borderRadius: '6px',
        padding: '10px 14px',
        marginBottom: '16px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        color: '#92400e',
        fontSize: '12.5px'
      }}>
        <I.Info size={16} color="#d97706" />
        <div>
          <strong>Vitals:</strong> {vitals.note}
        </div>
      </div>
    );
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
      gap: '10px',
      marginBottom: '16px'
    }}>
      {/* Gestational Age Card */}
      <div style={{
        background: '#ffffff',
        border: '1px solid var(--border-subtle, #e2e8f0)',
        borderRadius: '6px',
        padding: '10px 12px',
        borderLeft: '4px solid var(--acrn-sky-blue, #4771AD)'
      }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted, #64748b)', fontWeight: 600, textTransform: 'uppercase' }}>Gestational Age</div>
        <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--acrn-navy-dark, #162035)', marginTop: '2px' }}>{ga || 'Not specified'}</div>
        <div style={{ fontSize: '10.5px', color: 'var(--acrn-sky-blue, #4771AD)', marginTop: '2px', fontWeight: 600 }}>Clinical Milestone</div>
      </div>

      {/* Blood Pressure Card */}
      <div style={{
        background: '#ffffff',
        border: '1px solid var(--border-subtle, #e2e8f0)',
        borderRadius: '6px',
        padding: '10px 12px',
        borderLeft: '4px solid var(--acrn-orange-primary, #F07E26)'
      }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted, #64748b)', fontWeight: 600, textTransform: 'uppercase' }}>Blood Pressure</div>
        <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--acrn-navy-dark, #162035)', marginTop: '2px' }}>
          {vitals.bp}
        </div>
        <div style={{ fontSize: '10.5px', color: 'var(--acrn-navy-base, #1e2d45)', marginTop: '2px', fontWeight: 600 }}>
          {vitals.recheck ? `Recheck: ${vitals.recheck} (${vitals.interval || 'interval not documented'})` : (vitals.bpInterpretation || 'Interpretation not available')}
        </div>
      </div>

      {/* Heart Rate Card */}
      <div style={{
        background: '#ffffff',
        border: '1px solid var(--border-subtle, #e2e8f0)',
        borderRadius: '6px',
        padding: '10px 12px',
        borderLeft: '4px solid var(--acrn-teal-accent, #82CFCD)'
      }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted, #64748b)', fontWeight: 600, textTransform: 'uppercase' }}>Heart Rate</div>
        <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--acrn-navy-dark, #162035)', marginTop: '2px' }}>{vitals.hr || '—'}</div>
        <div style={{ fontSize: '10.5px', color: 'var(--text-muted, #64748b)', marginTop: '2px' }}>Maternal Pulse</div>
      </div>

      {/* Temperature Card */}
      <div style={{
        background: '#ffffff',
        border: '1px solid var(--border-subtle, #e2e8f0)',
        borderRadius: '6px',
        padding: '10px 12px',
        borderLeft: '4px solid var(--border-strong, #cbd5e1)'
      }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted, #64748b)', fontWeight: 600, textTransform: 'uppercase' }}>Temperature</div>
        <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--acrn-navy-dark, #162035)', marginTop: '2px' }}>{vitals.temp || '—'}</div>
        <div style={{ fontSize: '10.5px', color: 'var(--text-muted, #64748b)', marginTop: '2px' }}>Source recorded</div>
      </div>

      {/* Weight Card */}
      <div style={{
        background: '#ffffff',
        border: '1px solid var(--border-subtle, #e2e8f0)',
        borderRadius: '6px',
        padding: '10px 12px',
        borderLeft: '4px solid var(--border-strong, #cbd5e1)'
      }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted, #64748b)', fontWeight: 600, textTransform: 'uppercase' }}>Weight</div>
        <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--acrn-navy-dark, #162035)', marginTop: '2px' }}>{vitals.weight || '—'}</div>
        <div style={{ fontSize: '10.5px', color: 'var(--text-muted, #64748b)', marginTop: '2px' }}>Maternal Mass</div>
      </div>
    </div>
  );
}

// Sonographic Data Card Component
export function SonographicCard({ sonography }) {
  if (!sonography) return null;

  if (sonography.noScan) {
    return (
      <div style={{
        background: '#f8fafc',
        border: '1px solid var(--border-strong, #cbd5e1)',
        borderRadius: '6px',
        padding: '10px 14px',
        marginBottom: '16px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        fontSize: '12px',
        color: 'var(--text-muted, #64748b)'
      }}>
        <I.Activity size={15} color="var(--acrn-teal-accent, #82CFCD)" />
        <span><strong style={{ color: 'var(--acrn-navy-dark, #162035)' }}>Ultrasound Assessment:</strong> {sonography.note}</span>
      </div>
    );
  }

  return (
    <div style={{
      background: '#ffffff',
      border: '1px solid var(--border-strong, #cbd5e1)',
      borderLeft: '4px solid var(--acrn-teal-accent, #82CFCD)',
      borderRadius: '6px',
      padding: '12px 16px',
      marginBottom: '16px',
      boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: 'var(--acrn-navy-dark, #162035)', fontWeight: 700, fontSize: '13px' }}>
        <I.Activity size={16} color="var(--acrn-teal-accent, #82CFCD)" />
        Sonographic Assessment (Scan Date: {sonography.scanDate})
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px', fontSize: '12px', color: 'var(--text-main, #162035)' }}>
        <div><strong>EGA at scan:</strong> {sonography.ega}</div>
        {sonography.fetalWeight && <div><strong>Fetal weight:</strong> {sonography.fetalWeight}</div>}
        {sonography.presentation && <div><strong>Presentation:</strong> {sonography.presentation}</div>}
        {sonography.fhr && <div><strong>Fetal Heart Rate:</strong> {sonography.fhr}</div>}
      </div>
      <div style={{ fontSize: '12px', color: 'var(--text-main, #162035)', marginTop: '6px' }}>
        <strong>Findings:</strong> {sonography.placentaFluid}
      </div>
    </div>
  );
}

// High-Density Medical Diagnostic Laboratory Table Component
export function StructuredLabTable({ labs, labsNote }) {
  if (!labs || labs.length === 0) {
    if (labsNote) {
      return (
        <div style={{
          background: '#f8fafc',
          border: '1px dashed #cbd5e1',
          borderRadius: '6px',
          padding: '16px',
          textAlign: 'center',
          color: '#64748b',
          fontSize: '12.5px',
          fontStyle: 'italic',
          marginBottom: '16px'
        }}>
          {labsNote}
        </div>
      );
    }
    return null;
  }

  // Group labs by category
  const categories = [
    'Urinalysis',
    'Haematology',
    'Renal function',
    'Liver function and haemolysis',
    'Maternal assessment',
    'Sonography and fetal assessment',
    'Delivery',
    'Neonatal assessment',
    'Other mapped clinical results',
    'Biochemistry',
    'Other',
  ];
  const grouped = {};
  categories.forEach(c => { grouped[c] = []; });
  labs.forEach(lab => {
    if (!grouped[lab.category]) grouped[lab.category] = [];
    grouped[lab.category].push(lab);
  });

  return (
    <div style={{
      background: '#ffffff',
      border: '1px solid #cbd5e1',
      borderRadius: '6px',
      overflow: 'hidden',
      marginBottom: '16px',
      boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
    }}>
      <div style={{
        background: '#f8fafc',
        borderBottom: '1px solid var(--border-strong, #cbd5e1)',
        padding: '10px 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--acrn-navy-dark, #162035)', fontWeight: 700, fontSize: '13px' }}>
          <I.Database size={15} color="var(--acrn-orange-primary, #F07E26)" />
          Structured Laboratory Diagnostic Panel
        </div>
        <span style={{ fontSize: '11px', color: 'var(--text-muted, #64748b)' }}>
          ISSHP Diagnostic Panel Alignment
        </span>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid var(--border-strong, #cbd5e1)', textAlign: 'left', color: 'var(--acrn-navy-dark, #162035)' }}>
              <th style={{ padding: '8px 12px', width: '18%' }}>Category</th>
              <th style={{ padding: '8px 12px', width: '24%' }}>Test / Analyte</th>
              <th style={{ padding: '8px 12px', width: '18%' }}>Result</th>
              <th style={{ padding: '8px 12px', width: '16%' }}>Interpretation</th>
              <th style={{ padding: '8px 12px', width: '12%' }}>Date</th>
              <th style={{ padding: '8px 12px', width: '12%' }}>Source</th>
            </tr>
          </thead>
          <tbody>
            {categories.map(category => {
              const items = grouped[category] || [];
              if (items.length === 0) return null;
              return items.map((item, index) => (
                <tr key={`${category}-${item.test}-${index}`} style={{
                  borderBottom: '1px solid #f1f5f9',
                  background: index % 2 === 0 ? '#ffffff' : '#fafafa'
                }}>
                  {index === 0 ? (
                    <td 
                      rowSpan={items.length} 
                      style={{ 
                        padding: '8px 12px', 
                        fontWeight: 700, 
                        color: 'var(--acrn-navy-dark, #162035)', 
                        verticalAlign: 'top',
                        background: '#f8fafc',
                        borderRight: '1px solid #e2e8f0'
                      }}
                    >
                      {category}
                    </td>
                  ) : null}
                  <td style={{ padding: '8px 12px', color: 'var(--text-main, #162035)' }}>
                    {item.test}
                  </td>
                  <td style={{ padding: '8px 12px', fontWeight: 600, color: item.state === 'abnormal' ? '#b45309' : 'var(--acrn-navy-dark, #162035)' }}>
                    {item.result}
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <EvidenceStatusBadge state={item.state} label={item.label} />
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-muted, #64748b)' }}>
                    {item.observed_at ? formatVisitDateTime(item.observed_at) : 'Not available'}
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-muted, #64748b)' }}>
                    {item.source_label || 'Source recorded'}
                  </td>
                </tr>
              ));
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Special Visit 5 Delivery & Neonatal Module Component
export function VisitFiveDeliveryCard({ deliveryModule }) {
  if (!deliveryModule) return null;
  const f = deliveryModule.fetalOutcome || {};

  return (
    <div style={{
      background: '#ffffff',
      border: '1px solid var(--border-strong, #cbd5e1)',
      borderRadius: '8px',
      padding: '16px',
      marginBottom: '16px',
      borderLeft: '5px solid var(--acrn-orange-primary, #F07E26)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--acrn-navy-dark, #162035)', fontWeight: 700, fontSize: '14px', marginBottom: '12px' }}>
        <I.Baby size={18} color="var(--acrn-orange-primary, #F07E26)" />
        Visit 5: Operative Delivery &amp; Neonatal Outcome Record
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '14px' }}>
        {/* Maternal Section */}
        <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle, #e2e8f0)', borderRadius: '6px', padding: '12px' }}>
          <div style={{ fontWeight: 700, fontSize: '12.5px', color: 'var(--acrn-navy-base, #1e2d45)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <I.Stethoscope size={14} color="var(--acrn-orange-primary, #F07E26)" /> Maternal Delivery Status
          </div>
          <div style={{ fontSize: '12px', lineHeight: '1.6', color: 'var(--text-main, #162035)' }}>
            <div><strong>Delivery Mode:</strong> {deliveryModule.deliveryOutcome}</div>
            <div><strong>Indication:</strong> {deliveryModule.indication}</div>
            <div><strong>Estimated Blood Loss:</strong> {deliveryModule.ebl}</div>
            <div><strong>Hospital Stay:</strong> {deliveryModule.hospitalStay}</div>
            <div><strong>Postpartum Course:</strong> {deliveryModule.maternalStatus}</div>
          </div>
        </div>

        {/* Infant Section */}
        <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle, #e2e8f0)', borderRadius: '6px', padding: '12px' }}>
          <div style={{ fontWeight: 700, fontSize: '12.5px', color: 'var(--acrn-navy-base, #1e2d45)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <I.Baby size={14} color="var(--acrn-teal-accent, #82CFCD)" /> Fetal / Newborn Anthropometry &amp; Vitals
          </div>
          <div style={{ fontSize: '12px', lineHeight: '1.6', color: 'var(--text-main, #162035)' }}>
            <div><strong>Status &amp; Sex:</strong> {f.status}</div>
            <div><strong>Birth Weight:</strong> <strong style={{ color: 'var(--acrn-navy-dark, #162035)' }}>{f.birthWeight}</strong> | <strong>Length:</strong> {f.length} | <strong>HC:</strong> {f.headCircumference}</div>
            <div><strong>Apgar Scores:</strong> <strong>{f.apgar1}</strong> (at 1 min) | <strong>{f.apgar5}</strong> (at 5 mins)</div>
            <div><strong>Vitals:</strong> Heart rate {f.heartRate} | Respiration {f.respiration}</div>
            <div><strong>Feeding:</strong> {f.feeding}</div>
          </div>
        </div>
      </div>

      {/* Clinical Exam Narrative */}
      <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle, #e2e8f0)', borderRadius: '6px', padding: '10px 12px', fontSize: '12px', color: 'var(--text-main, #162035)' }}>
        <strong>Neonatal Physical &amp; Neurological Examinations:</strong> {f.exams}
      </div>
    </div>
  );
}

// Special Visit 6 Postnatal Module Component
export function VisitSixPostnatalCard({ postnatalModule }) {
  if (!postnatalModule) return null;

  return (
    <div style={{
      background: '#ffffff',
      border: '1px solid var(--border-strong, #cbd5e1)',
      borderRadius: '8px',
      padding: '14px',
      marginBottom: '16px',
      borderLeft: '5px solid var(--acrn-sky-blue, #4771AD)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--acrn-navy-dark, #162035)', fontWeight: 700, fontSize: '13.5px', marginBottom: '10px' }}>
        <I.Stethoscope size={16} color="var(--acrn-sky-blue, #4771AD)" />
        Visit 6: Postnatal 4-Week Status Evaluation
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12px', color: 'var(--text-main, #162035)' }}>
        <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle, #e2e8f0)', borderRadius: '6px', padding: '10px 12px' }}>
          <strong style={{ display: 'block', color: 'var(--acrn-navy-dark, #162035)', marginBottom: '4px' }}>Maternal Postnatal Status:</strong>
          {postnatalModule.maternalStatus}
        </div>
        <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle, #e2e8f0)', borderRadius: '6px', padding: '10px 12px' }}>
          <strong style={{ display: 'block', color: 'var(--acrn-navy-dark, #162035)', marginBottom: '4px' }}>Infant Development Status:</strong>
          {postnatalModule.infantStatus}
        </div>
      </div>
    </div>
  );
}

// ISSHP Clinical Diagnostic Evaluation Card Component
export function IsshpSummaryCard({ isshpEvaluation }) {
  if (!isshpEvaluation) return null;

  return (
    <div style={{
      background: '#ffffff',
      border: '1px solid var(--border-strong, #cbd5e1)',
      borderRadius: '8px',
      padding: '18px',
      marginBottom: '16px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--acrn-navy-dark, #162035)', fontWeight: 700, fontSize: '14px', marginBottom: '8px' }}>
        <I.ShieldCheck size={18} color="var(--acrn-orange-primary, #F07E26)" />
        Preeclampsia Diagnostic Synthesis (ISSHP Criteria Focus)
      </div>
      <p style={{ fontSize: '12.5px', color: 'var(--text-muted, #64748b)', lineHeight: '1.5', margin: '0 0 14px' }}>
        {isshpEvaluation.guideline}
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
        {/* Hemodynamics */}
        <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle, #e2e8f0)', borderLeft: '4px solid var(--acrn-orange-primary, #F07E26)', borderRadius: '6px', padding: '12px' }}>
          <div style={{ fontWeight: 700, fontSize: '12.5px', color: 'var(--acrn-navy-dark, #162035)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <I.Activity size={14} color="var(--acrn-orange-primary, #F07E26)" /> 1. Hemodynamics &amp; BP Trajectory
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-main, #162035)', lineHeight: '1.5' }}>
            {isshpEvaluation.hemodynamics}
          </div>
        </div>

        {/* Organ Dysfunction */}
        <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle, #e2e8f0)', borderLeft: '4px solid var(--acrn-teal-accent, #82CFCD)', borderRadius: '6px', padding: '12px' }}>
          <div style={{ fontWeight: 700, fontSize: '12.5px', color: 'var(--acrn-navy-dark, #162035)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <I.Database size={14} color="var(--acrn-teal-accent, #82CFCD)" /> 2. Maternal Organ Function &amp; Platelets
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-main, #162035)', lineHeight: '1.5' }}>
            {isshpEvaluation.organDysfunction}
          </div>
        </div>

        {/* Proteinuria */}
        <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle, #e2e8f0)', borderLeft: '4px solid var(--acrn-sky-blue, #4771AD)', borderRadius: '6px', padding: '12px' }}>
          <div style={{ fontWeight: 700, fontSize: '12.5px', color: 'var(--acrn-navy-dark, #162035)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <I.FlaskConical size={14} color="var(--acrn-sky-blue, #4771AD)" /> 3. Proteinuria Assessment
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-main, #162035)', lineHeight: '1.5' }}>
            {isshpEvaluation.proteinuria}
          </div>
        </div>
      </div>
    </div>
  );
}

// Per-Visit Header Banner
export function VisitHeaderBanner({ visit, selectedIndex, visitCount, onSelectVisit }) {
  const visitNum = visit.visit_number || selectedIndex + 1;
  const visitName = (visit.name && !visit.name.startsWith('V0')) ? `Visit ${visitNum}: ${visit.name}` : (visit.name || visit.visit_code || `Visit ${visitNum}`);
  const isNotPerformed = Boolean(visit?.is_not_performed || visit?.not_performed_reason);
  const notPerformedReason = visit?.not_performed_reason || 'Visit not performed';
  const dateStr = formatVisitDate(visit.date || visit.visit_date);
  const rawGa = visit.gestationalLabel || visit.ga || visit.gestational_age || null;
  const gaLabel = (rawGa && !/unclassifiable|null|undefined/i.test(String(rawGa))) ? rawGa : null;
  const isPostDelivery = visitNum >= 5;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: '#ffffff',
      border: '1px solid var(--border-strong, #cbd5e1)',
      borderRadius: '8px',
      padding: '12px 16px',
      marginBottom: '14px',
      gap: '12px',
      flexWrap: 'wrap',
      boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
        <div style={{
          background: isNotPerformed ? '#64748b' : 'var(--acrn-navy-dark, #162035)',
          border: isNotPerformed ? '2px solid #cbd5e1' : '2px solid var(--acrn-orange-primary, #F07E26)',
          color: '#ffffff',
          fontWeight: 800,
          fontSize: '14px',
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0
        }}>
          {visitNum}
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: '15px', color: 'var(--acrn-navy-dark, #162035)' }}>
            {visitName}
          </div>
          {isNotPerformed ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '3px' }}>
              <span style={{
                background: '#fef3c7',
                color: '#92400e',
                border: '1px solid #fde68a',
                padding: '2px 8px',
                borderRadius: '4px',
                fontWeight: 600,
                fontSize: '11.5px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                Not Performed: {notPerformedReason}
              </span>
            </div>
          ) : (
            <div style={{ fontSize: '12px', color: 'var(--text-muted, #64748b)', marginTop: '2px' }}>
              {dateStr} {gaLabel ? ` · Gestational Age: ${gaLabel}` : ''}
            </div>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
        <button
          type="button"
          className="btn-secondary"
          style={{ padding: '5px 12px', fontSize: '12px' }}
          disabled={selectedIndex <= 0}
          onClick={() => onSelectVisit?.(selectedIndex - 1)}
          aria-label="Previous visit"
        >
          <I.ChevronLeft size={14} /> Previous Visit
        </button>
        <button
          type="button"
          className="btn-secondary"
          style={{ padding: '5px 12px', fontSize: '12px' }}
          disabled={selectedIndex >= visitCount - 1}
          onClick={() => onSelectVisit?.(selectedIndex + 1)}
          aria-label="Next visit"
        >
          Next Visit <I.ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

// Convert normalized live visit results into the StructuredLabTable row format.
function buildLabsForTable(liveLabs, otherResults = []) {
  const rows = [...(liveLabs || []), ...(otherResults || [])];
  if (rows.length > 0) {
    const seenTests = new Set();
    const dedupedRows = [];
    for (const r of rows) {
      const testKey = (r.label || r.key || '').trim().toLowerCase();
      if (/protein.*dipstick|dipstick.*protein|^ua_protein$/i.test(testKey)) {
        if (seenTests.has('protein_dipstick')) continue;
        seenTests.add('protein_dipstick');
      }
      dedupedRows.push(r);
    }
    return dedupedRows.map((row) => {
      // Format the result value with proper unit
      const formattedResult = formatLabResult(row.key, row.raw ?? row.value, row.unit);

      // Derive interpretation from evidence_state first, then reference ranges
      let state;
      let label;
      if (row.evidence_state === 'not_available') {
        state = 'not_available'; label = 'Not available';
      } else if (row.evidence_state === 'pending') {
        state = 'pending'; label = 'Pending';
      } else if (['abnormal', 'severe'].includes(row.evidence_state)) {
        // Use reference-range / qualitative label (High/Low/Normal) when available
        const interp = inferLabInterpretation(row.key, row.value, row.raw);
        state = 'abnormal';
        label = (interp.label !== 'Normal') ? interp.label : 'Abnormal';
      } else {
        // evidence_state is 'normal' or 'available' — verify against ranges / qualitative map
        const interp = inferLabInterpretation(row.key, row.value, row.raw);
        state = interp.state;
        label = interp.label;
      }

      return {
        category: row.category || 'Other',
        test: row.label || row.key,
        result: formattedResult,
        state,
        label,
        observed_at: row.observed_at,
        reference: row.reference || getLabReferenceRange(row.key),
        source_label: row.source_label,
      };
    });
  }
  return null;
}

// Unified Visit Evidence Panel
function MarkdownDisclosure({ title, icon, defaultOpen = true, children }) {
  return (
    <details
      open={defaultOpen}
      style={{
        border: '1px solid var(--border-strong, #cbd5e1)',
        borderRadius: '8px',
        background: '#ffffff',
        marginBottom: '12px',
        overflow: 'hidden',
      }}
    >
      <summary
        style={{
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 14px',
          background: '#f8fafc',
          color: 'var(--acrn-navy-dark, #162035)',
          fontSize: '13px',
          fontWeight: 700,
        }}
      >
        {icon}
        {title}
      </summary>
      <div style={{ padding: '14px 16px' }}>
        {children}
      </div>
    </details>
  );
}

function clinicalValue(row) {
  if (!row) return null;
  const value = row.raw ?? row.value ?? row.raw_source_value ?? row.parsed_text_value ?? row.coded_value;
  if (value == null || value === '') return null;
  const str = String(value).trim();
  const num = Number(str);
  const isDipstick = /protein|dipstick|urinalysis|ua_/i.test(`${row.key || ''} ${row.label || ''} ${row.method || ''} ${row.source_label || ''}`);
  if (isDipstick && Number.isInteger(num)) {
    if (num === 0) return 'Negative';
    if (num > 0 && num <= 5) return `${num}+`;
  }
  return row.unit ? `${value} ${row.unit}` : String(value);
}

function firstResult(visit, patterns) {
  const rows = [
    ...(visit?.labs || []),
    ...(visit?.otherResults || []),
    ...(visit?.maternal || []),
    ...(visit?.neonatal || []),
    ...(visit?.proteinuria || []),
    ...(visit?.symptoms || []),
  ];
  return rows.find((row) => patterns.some((pattern) => pattern.test(`${row.key || ''} ${row.label || ''} ${row.method || ''}`)));
}

function visitNumberFor(visit, selectedIndex) {
  return visit?.visit_number || (Number.isInteger(selectedIndex) ? selectedIndex + 1 : null);
}

function visitHeadingTitle(visit, visitNum) {
  const source = `${visit?.name || ''} ${visit?.visit_code || ''} ${visit?.label || ''}`;
  if (visitNum === 5 || /delivery|v05|visit 5/i.test(source)) return 'Delivery Visit';
  if (visitNum === 6 || /post|eos|end.of.study|v06|visit 6/i.test(source)) return 'Postnatal Follow-up';
  if (visitNum === 1 || /screen|baseline|v01|visit 1/i.test(source)) return 'Baseline / Screening';
  return 'Routine Follow-up';
}

function describeProteinuria(visit) {
  const rows = visit?.proteinuria || [];
  if (!rows.length) return 'Proteinuria status was not available for this visit.';
  const seen = new Set();
  const sentences = [];
  for (const row of rows) {
    const method = row.method || row.label || row.key || 'proteinuria';
    const value = clinicalValue(row) || row.evidence_state || 'recorded without a displayable value';
    const phrase = /negative/i.test(value) ? `The source records a negative ${method} result.` : `${method}: ${value}.`;
    if (!seen.has(phrase)) {
      seen.add(phrase);
      sentences.push(phrase);
    }
  }
  return sentences.join(' ');
}

function describeSymptoms(visit) {
  const rows = visit?.symptoms || [];
  if (!rows.length) return 'Symptom status was not available for this visit.';
  const values = rows.map((row) => clinicalValue(row)).filter(Boolean);
  return values.length ? `Recorded symptom evidence: ${values.join('; ')}.` : 'Symptom status was not available for this visit.';
}

function describeOrganEvidence(visit) {
  const required = ['PLATELETS', 'CREATININE', 'AST', 'ALT', 'LDH'];
  const present = (visit?.labs || []).filter((row) => required.includes(row.key));
  if (!present.length) return 'Maternal organ laboratory evidence was not available in the mapped visit data.';
  const abnormal = present.filter((row) => ['abnormal', 'severe', 'conflicting'].includes(row.evidence_state));
  if (abnormal.length) {
    return `Mapped maternal organ results requiring review include ${abnormal.map((row) => row.label || row.key).join(', ')}.`;
  }
  return 'The available platelet, creatinine and transaminase/haemolysis results did not meet the configured alert thresholds.';
}

function buildVisitNarrative(visit, visitNum, caseData) {
  // Delegate to the new FORM-ADJ-PROSE-v2.0 engine
  return generateVisitNarrative(visit, visitNum, caseData);
}

function _legacyBuildVisitNarrative(visit, visitNum, caseData) {
  const title = visitHeadingTitle(visit, visitNum);
  const ev = visit?.evidence || {};

  // 1. Detect if the visit was not performed
  let notPerformedReason = visit?.not_performed_reason || null;
  if (!notPerformedReason) {
    const rawReason = ev.visit_date?.[0]?.value || visit?.observations?.find(o =>
      o.source_field_label?.toLowerCase().includes('not performing') ||
      ['delivered', 'missed visit', 'withdrew', 'lost to follow-up'].includes(String(o.raw_source_value || '').toLowerCase())
    )?.raw_source_value;
    if (rawReason && ['delivered', 'missed visit', 'withdrew', 'lost to follow-up'].includes(String(rawReason).toLowerCase())) {
      notPerformedReason = String(rawReason);
    }
  }

  const hasBp = (visit?.bp || []).length > 0;
  const hasLabs = (visit?.labs || []).filter(l => l.value != null && !['not_available', 'missing'].includes(l.evidence_state)).length > 0;
  const hasVitals = Boolean(visit?.vitals?.bp || visit?.vitals?.hr || visit?.vitals?.weight);

  if (visit?.is_not_performed || notPerformedReason) {
    const reason = notPerformedReason || visit?.not_performed_reason || 'delivered';
    if (/delivered/i.test(reason)) {
      const delDate = caseData?.delivery_date || caseData?.visits?.find(v => v.visit_number === 5)?.date;
      const formattedDelDate = delDate ? ` (delivery documented on ${formatVisitDate(delDate)})` : '';
      return `Visit ${visitNum} (${title}) was not performed because the participant had already delivered prior to this scheduled assessment window${formattedDelDate}. No clinical measurements or laboratory tests were conducted for this visit.`;
    }
    if (/missed/i.test(reason)) {
      return `Visit ${visitNum} (${title}) was not performed. Mapped trial records confirm this was a missed visit; the participant did not attend and no clinical evaluations were recorded.`;
    }
    return `Visit ${visitNum} (${title}) was not performed (source records state: "${reason}"). No clinical measurements were recorded.`;
  }

  if (!hasBp && !hasLabs && !hasVitals && !visit?.date && (visit?.observations?.length || 0) <= 1) {
    return `Visit ${visitNum} (${title}) was not conducted; no clinical measurements or laboratory evaluations were recorded in the study database.`;
  }

  // 2. Performed visit: Build cohesive medical narrative
  const dateStr = visit?.date ? formatVisitDate(visit.date) : 'date not documented';
  const rawGa = visit?.gestationalLabel || visit?.ga || visit?.gestational_age;
  const gaStr = (rawGa && !/unclassifiable|null|undefined/i.test(String(rawGa))) ? rawGa : null;
  const paragraphs = [];

  // Opening & Hemodynamics
  const initialBp = visit?.vitals?.bp;
  const recheckBp = visit?.vitals?.recheck;
  const sbp = visit?.bp?.[0]?.sbp;
  const dbp = visit?.bp?.[0]?.dbp;

  let bpSentence = '';
  if (initialBp) {
    if (sbp >= 160 || dbp >= 110) {
      bpSentence = `Maternal blood pressure was severely elevated at ${initialBp}${recheckBp ? ` with repeat confirmation of ${recheckBp}` : ''}.`;
    } else if (sbp >= 140 || dbp >= 90) {
      bpSentence = `Maternal blood pressure met hypertensive criteria at ${initialBp}${recheckBp ? ` (recheck: ${recheckBp})` : ''}.`;
    } else {
      bpSentence = `Blood pressure was within normal limits at ${initialBp}${recheckBp ? ` (recheck: ${recheckBp})` : ''}.`;
    }
  }

  const vitalsExtras = [];
  if (visit?.vitals?.hr) vitalsExtras.push(`heart rate ${visit.vitals.hr}`);
  if (visit?.vitals?.temp) vitalsExtras.push(`temperature ${visit.vitals.temp}`);
  if (visit?.vitals?.weight) vitalsExtras.push(`maternal weight ${visit.vitals.weight}`);
  const vitalsClause = vitalsExtras.length ? ` Vital signs noted ${vitalsExtras.join(', ')}.` : '';

  if (visitNum === 1) {
    paragraphs.push(`Screening and baseline evaluation conducted on ${dateStr}${gaStr && gaStr !== 'Antenatal' ? ` at ${gaStr}` : ''}. ${bpSentence}${vitalsClause}`.trim());
  } else if (visitNum === 5) {
    // Delivery Visit: synthesize complete delivery and newborn findings
    const findObs = (keys, requireDescriptive = false) => {
      for (const k of keys) {
        const rows = ev[k];
        if (rows?.length) {
          if (requireDescriptive) {
            const desc = rows.find(r => r.value && !/^(yes|no|true|false)$/i.test(String(r.value).trim()));
            if (desc) return desc.value;
          }
          return rows[0].value;
        }
      }
      return null;
    };
    const delDate = findObs(['delivery_date', 'date_of_delivery']) || visit?.date;
    const delMode = findObs(['delivery_mode', 'type_of_delivery']);
    const delIndication = findObs(['indication', 'reason_for_cesarean_section']);
    const rawDelGa = findObs(['ega_delivery', 'ga_at_delivery', 'ga_weeks']) || (visit?.ga_days ? `${Math.floor(visit.ga_days/7)}` : null);
    const delGa = rawDelGa ? (String(rawDelGa).toLowerCase().includes('week') ? rawDelGa : `${rawDelGa} weeks`) : null;
    const ebl = findObs(['ebl_ml', 'estimated_blood_loss']);
    const stay = findObs(['delivery_outcome']) && !isNaN(Number(findObs(['delivery_outcome']))) ? findObs(['delivery_outcome']) : null;
    const matStatus = findObs(['health_status_description', 'health_status']);

    // Neonatal
    const babyStatus = findObs(['pregnancy_outcome', 'newborn_status']);
    const sex = findObs(['neonatal_gender', 'gender']);
    const wt = findObs(['newborn_weight_g', 'birth_weight']);
    const len = findObs(['neonatal_length', 'length']);
    const hc = findObs(['neonatal_hc', 'head_circumference']);
    const ap1 = findObs(['apgar_1m', 'apgar_score_at_1_minute']);
    const ap5 = findObs(['apgar_5m', 'apgar_score_at_5_minutes']);
    const ap10 = findObs(['apgar_10m', 'apgar_score_at_10_minutes']);
    const bComp = findObs(['birth_complications', 'delivery_outcome'], true);

    let delPara = `Delivery evaluation documented on ${formatVisitDate(delDate)}${delGa ? ` at ${delGa} gestation` : ''}. `;
    if (delMode) {
      delPara += `Delivery was by ${delMode}${delIndication ? ` (indication: ${delIndication})` : ''}. `;
    }
    if (ebl) delPara += `Estimated blood loss was ${ebl} mL. `;
    if (stay) delPara += `Postpartum hospital stay was ${stay} days. `;
    if (matStatus) delPara += `Maternal clinical status was recorded as ${matStatus.toLowerCase()}. `;
    paragraphs.push(delPara.trim());

    if (wt || babyStatus || sex) {
      let neoPara = `Neonatal outcome: Liveborn ${sex ? `${sex.toLowerCase()} ` : ''}infant`;
      if (wt) neoPara += ` weighing ${wt} g`;
      if (len) neoPara += ` (length ${len} cm`;
      if (hc) neoPara += `, head circumference ${hc} cm)`;
      else if (len) neoPara += `)`;
      neoPara += `.`;
      if (ap1 && ap5) {
        neoPara += ` Apgar scores were ${ap1} at 1 min, ${ap5} at 5 min${ap10 ? `, and ${ap10} at 10 min` : ''}.`;
      }
      if (bComp && !/^(no|none|false)$/i.test(bComp)) {
        neoPara += ` Neonatal complications: ${bComp}.`;
      } else {
        neoPara += ` No birth complications reported.`;
      }
      paragraphs.push(neoPara);
    }
    return paragraphs.join('\n\n');
  } else if (visitNum === 6) {
    paragraphs.push(`Postnatal follow-up conducted on ${dateStr} (${gaStr || 'approximately 4 weeks postpartum'}). ${bpSentence}${vitalsClause}`.trim());
  } else {
    paragraphs.push(`Antenatal follow-up conducted on ${dateStr}${gaStr && gaStr !== 'Antenatal' ? ` at ${gaStr}` : ''}. ${bpSentence}${vitalsClause}`.trim());
  }

  // Proteinuria & Symptoms
  const seenProt = new Set();
  const protParts = [];
  const protRows = visit?.proteinuria || [];
  if (protRows.length > 0) {
    for (const p of protRows) {
      const val = String(p.value ?? '').trim();
      let phrase = '';
      if (/negative/i.test(val)) {
        phrase = 'dipstick urinalysis was negative for protein';
      } else if (val) {
        phrase = `${p.method || 'urinalysis'}: ${val}`;
      }
      if (phrase && !seenProt.has(phrase)) {
        seenProt.add(phrase);
        protParts.push(phrase);
      }
    }
  }
  const protText = protParts.length ? `Urinalysis review: ${protParts.join('; ')}.` : null;

  const sympRows = visit?.symptoms || [];
  const sympVals = sympRows.map(s => s.value).filter(v => v && !/^(no|none|false|normal|unchanged)$/i.test(String(v).trim()));
  let sympText = null;
  if (sympVals.length > 0) {
    sympText = `Reported symptoms included ${sympVals.join(', ')}.`;
  } else if (sympRows.length > 0) {
    sympText = 'The participant reported no acute preeclamptic symptoms.';
  }

  if (protText || sympText) {
    paragraphs.push([protText, sympText].filter(Boolean).join(' '));
  }

  // Laboratories & Organ Function
  const labRows = visit?.labs || [];
  if (labRows.length > 0) {
    const getLab = (k) => labRows.find(l => l.key === k && l.value != null);
    const plt = getLab('PLATELETS');
    const cr = getLab('CREATININE');
    const ast = getLab('AST');
    const alt = getLab('ALT');
    const ldh = getLab('LDH');
    const hgb = getLab('HAEMOGLOBIN');

    const organAlerts = labRows.filter(l => ['abnormal', 'severe', 'conflicting'].includes(l.evidence_state));
    if (organAlerts.length > 0) {
      paragraphs.push(`Laboratory evaluation identified findings requiring clinical review: ${organAlerts.map(l => `${l.label || l.key} ${l.value} ${l.unit || ''}`.trim()).join(', ')}.`);
    } else if (plt || cr || ast || alt) {
      const core = [];
      if (plt) core.push(`platelets ${plt.value} ×10⁹/L`);
      if (cr) core.push(`creatinine ${cr.value} µmol/L`);
      if (ast && alt) core.push(`AST ${ast.value} U/L, ALT ${alt.value} U/L`);
      if (ldh) core.push(`LDH ${ldh.value} U/L`);
      if (hgb) core.push(`haemoglobin ${hgb.value} g/dL`);
      paragraphs.push(`Laboratory investigations demonstrated normal end-organ markers (${core.join(', ')}).`);
    }
  }

  // Sonography
  if (visit?.sonography) {
    const s = visit.sonography;
    paragraphs.push(
      `Obstetric ultrasound at ${s.ega} gestation demonstrated a single viable foetus in ${s.presentation} presentation with a foetal heart rate of ${s.fhr} and an estimated foetal weight of ${s.efwRaw}. Environmental findings included: cervical length ${s.cervicalLength}. ${s.anomalies}. Sonographer notes: ${s.notes}`
    );
  }

  return paragraphs.join('\n\n');
}

function BulletList({ items }) {
  const visible = items.filter((item) => item?.value);
  if (!visible.length) {
    return <p style={{ margin: 0, color: 'var(--text-muted, #64748b)', fontSize: '12.5px' }}>No mapped evidence was available for this section.</p>;
  }
  return (
    <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12.5px', lineHeight: 1.7, color: 'var(--text-main, #162035)' }}>
      {visible.map((item) => (
        <li key={item.label}><strong>{item.label}:</strong> {item.value}</li>
      ))}
    </ul>
  );
}

function MarkdownResultTable({ labs, labsNote }) {
  if (!labs || labs.length === 0) {
    return (
      <div style={{ border: '1px dashed #cbd5e1', borderRadius: '6px', padding: '12px', color: '#64748b', fontSize: '12.5px' }}>
        {labsNote || 'No mapped laboratory or clinical result was available for this visit.'}
      </div>
    );
  }

  // Group by category to apply rowSpan
  const categories = [
    'Urinalysis',
    'Haematology',
    'Renal function',
    'Liver function and haemolysis',
    'Biochemistry',
    'Other mapped clinical results',
    'Other',
  ];
  const grouped = {};
  categories.forEach(c => { grouped[c] = []; });
  labs.forEach(lab => {
    const cat = lab.category || 'Other mapped clinical results';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(lab);
  });
  
  // Make sure we only iterate over categories that have items
  const activeCategories = Object.keys(grouped).filter(c => grouped[c].length > 0);

  return (
    <div style={{ overflowX: 'auto', border: '1px solid var(--border-strong, #cbd5e1)', borderRadius: '6px' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
        <thead>
          <tr style={{ background: '#f8fafc', borderBottom: '1px solid #cbd5e1', textAlign: 'left', color: 'var(--acrn-navy-dark, #162035)' }}>
            <th style={{ padding: '10px 12px', width: '20%' }}>Category</th>
            <th style={{ padding: '10px 12px', width: '25%' }}>Test</th>
            <th style={{ padding: '10px 12px', width: '20%' }}>Result</th>
            <th style={{ padding: '10px 12px', width: '15%' }}>Reference Range</th>
            <th style={{ padding: '10px 12px', width: '20%' }}>Interpretation</th>
          </tr>
        </thead>
        <tbody>
          {activeCategories.map(category => {
            const items = grouped[category];
            return items.map((item, index) => (
              <tr key={`${category}-${item.test}-${index}`} style={{ borderBottom: '1px solid #f1f5f9', background: '#ffffff' }}>
                {index === 0 ? (
                  <td 
                    rowSpan={items.length} 
                    style={{ padding: '10px 12px', fontWeight: 700, verticalAlign: 'top', borderRight: '1px solid #f1f5f9', background: '#fafafa' }}
                  >
                    {category}
                  </td>
                ) : null}
                <td style={{ padding: '10px 12px', color: 'var(--text-main, #162035)' }}>{item.test}</td>
                <td style={{ padding: '10px 12px', fontWeight: 600, color: item.state === 'abnormal' ? '#b45309' : 'var(--acrn-navy-dark, #162035)' }}>{item.result}</td>
                <td style={{ padding: '10px 12px', color: 'var(--text-muted, #64748b)' }}>{item.reference || '—'}</td>
                <td style={{ padding: '10px 12px' }}>
                  <EvidenceStatusBadge state={item.state} label={item.label} />
                </td>
              </tr>
            ));
          })}
        </tbody>
      </table>
    </div>
  );
}

function SourceProvenanceList({ labs }) {
  const rows = (labs || []).filter((row) => row.source_label || row.observed_at || row.reference);
  if (!rows.length) {
    return <p style={{ margin: 0, color: 'var(--text-muted, #64748b)', fontSize: '12.5px' }}>Source row metadata was not available for the displayed results.</p>;
  }
  return (
    <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', lineHeight: 1.65, color: 'var(--text-main, #162035)' }}>
      {rows.map((row, index) => (
        <li key={`${row.test}-${index}`}>
          <strong>{row.test}:</strong> {row.source_label || 'source recorded'}
          {row.observed_at ? `; observed ${formatVisitDateTime(row.observed_at)}` : ''}
          {row.reference ? `; reference ${row.reference}` : ''}
        </li>
      ))}
    </ul>
  );
}

// Patient-agnostic Markdown-style visit evidence panel.
export function VisitEvidencePanel({ visit, selectedIndex, visitCount, onSelectVisit, caseData, narrativeText }) {
  const safeSelectedIndex = Number.isInteger(selectedIndex) ? selectedIndex : 0;
  const safeVisitCount = Number.isInteger(visitCount) && visitCount > 0 ? visitCount : 6;
  const visitNum = visitNumberFor(visit, safeSelectedIndex);
  const title = visitHeadingTitle(visit, visitNum);
  const visitDate = visit?.date ? formatVisitDate(visit.date) : 'Date not documented';
  const labs = buildLabsForTable(visit?.labs) || [];
  const bpPairs = pairBpReadings(visit?.bp || []);
  const firstPair = bpPairs[0] || {};
  const initialBp = visit?.vitals?.bp || (firstPair.initial ? `${firstPair.initial.sbp}/${firstPair.initial.dbp} mmHg` : null);
  const recheckBp = visit?.vitals?.recheck || (firstPair.recheck ? `${firstPair.recheck.sbp}/${firstPair.recheck.dbp} mmHg` : null);
  const sonographyValue = visit?.sonography ? [
    visit.sonography.scanDate ? `scan date ${visit.sonography.scanDate}` : null,
    visit.sonography.ega ? `EGA ${visit.sonography.ega}` : null,
    visit.sonography.fetalWeight ? `fetal weight ${visit.sonography.fetalWeight}` : null,
    visit.sonography.presentation ? `presentation ${visit.sonography.presentation}` : null,
    visit.sonography.fhr ? `FHR ${visit.sonography.fhr}` : null,
  ].filter(Boolean).join('; ') : 'Not available from mapped evidence';
  const deliveryRows = [
    { label: 'Delivery date', value: clinicalValue(firstResult(visit, [/delivery.*date/i])) || (visitNum === 5 && visit?.date ? formatVisitDate(visit.date) : null) },
    { label: 'Gestational age at delivery', value: clinicalValue(firstResult(visit, [/ega.*delivery/i, /ga.*delivery/i])) || (visitNum === 5 ? visit?.gestationalLabel : null) },
    { label: 'Mode / outcome', value: clinicalValue(firstResult(visit, [/delivery.*mode/i, /pregnancy.*outcome/i, /delivery.*outcome/i])) },
    { label: 'Indication', value: clinicalValue(firstResult(visit, [/indication/i])) },
    { label: 'Blood loss', value: clinicalValue(firstResult(visit, [/blood.*loss/i, /\bebl\b/i])) },
    { label: 'Hospital stay', value: clinicalValue(firstResult(visit, [/hospital.*stay/i])) },
    { label: 'Maternal outcome', value: clinicalValue(firstResult(visit, [/maternal.*outcome/i, /maternal.*status/i])) },
  ];
  const neonatalRows = [
    { label: 'Newborn status', value: clinicalValue(firstResult(visit, [/newborn.*status/i, /neonatal.*status/i, /neonatal.*outcome/i])) },
    { label: 'Sex', value: clinicalValue(firstResult(visit, [/neonatal.*sex/i, /newborn.*sex/i, /\bsex\b/i])) },
    { label: 'Weight', value: clinicalValue(firstResult(visit, [/newborn.*weight/i, /birth.*weight/i, /neonatal.*weight/i])) },
    { label: 'Length', value: clinicalValue(firstResult(visit, [/newborn.*length/i, /neonatal.*length/i])) },
    { label: 'Head circumference', value: clinicalValue(firstResult(visit, [/head.*circ/i])) },
    { label: 'Apgar', value: clinicalValue(firstResult(visit, [/apgar/i])) },
    { label: 'NICU admission', value: clinicalValue(firstResult(visit, [/nicu/i])) },
    { label: 'Feeding', value: clinicalValue(firstResult(visit, [/feeding/i])) },
  ];

  return (
    <section className="visit-section" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <VisitHeaderBanner
        visit={visit}
        selectedIndex={safeSelectedIndex}
        visitCount={safeVisitCount}
        onSelectVisit={onSelectVisit}
      />

      <div style={{
        background: '#ffffff',
        border: '1px solid var(--border-strong, #cbd5e1)',
        borderLeft: '4px solid var(--acrn-orange-primary, #F07E26)',
        borderRadius: '8px',
        padding: '14px 16px',
      }}>
        <div style={{ margin: 0, fontSize: '13px', lineHeight: 1.7, color: 'var(--text-main, #162035)', whiteSpace: 'pre-wrap' }}>
          {narrativeText || buildVisitNarrative(visit, visitNum, caseData)}
        </div>
      </div>



      {visit?.is_not_performed ? (
        <div style={{
          background: '#f8fafc',
          border: '1px dashed #cbd5e1',
          borderRadius: '8px',
          padding: '24px 20px',
          color: '#64748b',
          fontSize: '13px',
          textAlign: 'center',
          lineHeight: 1.6,
        }}>
          <I.Info size={22} color="#94a3b8" style={{ margin: '0 auto 8px', display: 'block' }} />
          <div style={{ fontWeight: 700, color: 'var(--acrn-navy-dark, #162035)', fontSize: '14px' }}>
            Scheduled Study Visit Not Performed
          </div>
          <div style={{ marginTop: '6px', fontSize: '13px', maxWidth: '540px', margin: '6px auto 0' }}>
            {visit.not_performed_reason
              ? `Source records confirm: "${visit.not_performed_reason}". No clinical assessments, vital signs, or laboratory investigations were conducted for this scheduled window.`
              : 'No clinical assessments or laboratory samples were collected for this scheduled interval.'}
          </div>
        </div>
      ) : (
        <>
          <MarkdownDisclosure title={visitNum === 5 ? 'Delivery and Newborn Findings' : visitNum === 6 ? 'Postpartum and Infant Status' : 'Patient History and Assessment'} icon={<I.ClipboardList size={15} color="var(--acrn-orange-primary, #F07E26)" />} defaultOpen>
            {visitNum === 5 ? (
              <>
                <BulletList items={deliveryRows} />
                <div style={{ height: '10px' }} />
                <BulletList items={neonatalRows} />
              </>
            ) : (
              <BulletList
                items={[
                  { label: 'Visit purpose', value: title },
                  { label: 'Heart rate', value: visit?.vitals?.hr || null },
                  { label: 'Temperature', value: visit?.vitals?.temp || null },
                  { label: 'Weight', value: visit?.vitals?.weight || null },
                  { label: 'Sonography', value: sonographyValue },
                ]}
              />
            )}
          </MarkdownDisclosure>

          <MarkdownDisclosure title="Labs and Clinical Results" icon={<I.Database size={15} color="var(--acrn-orange-primary, #F07E26)" />} defaultOpen>
            <MarkdownResultTable
              labs={labs}
              labsNote={visitNum === 5 ? 'Routine laboratory testing is shown as not required only when supported by protocol/workflow configuration.' : null}
            />
          </MarkdownDisclosure>

        </>
      )}

      <p className="visit-evidence-note" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11.5px', color: 'var(--text-muted, #64748b)', margin: '0 0 4px' }}>
        <I.EyeOff size={13} />
        Blinded biomarker fields (sFlt-1/PlGF, sEng, POC) remain withheld per SOP-ADJ-002 section 5.1.
      </p>
    </section>
  );
}

// Overall Adjudication Summary & Longitudinal Review
export function OverallSummary({ visits = [], caseData }) {
  const clinicalCourseText = generateOverallNarrative(visits, caseData);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', paddingBottom: '24px' }}>
      {/* ── Narrative Synthesis ───────────────────────────────────────────── */}
      <div style={{
        background: '#ffffff',
        border: '1px solid var(--border-strong, #cbd5e1)',
        borderLeft: '4px solid var(--acrn-sky-blue, #4771AD)',
        borderRadius: '8px',
        padding: '16px 20px',
      }}>
        <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: 'var(--acrn-navy-dark, #162035)' }}>
          Combined Longitudinal Narrative
        </h4>
        <pre style={{
          margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          fontSize: '13.5px', lineHeight: '1.75', fontFamily: 'inherit',
          color: 'var(--text-main, #1e293b)',
        }}>
          {clinicalCourseText || <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>No longitudinal narrative available.</span>}
        </pre>
      </div>

      {/* ── Longitudinal Evidence Matrix ─────────────────────────────────── */}
      <details open style={{
        background: '#ffffff', border: '1px solid #cbd5e1',
        borderLeft: '4px solid var(--acrn-teal-accent, #82CFCD)',
        borderRadius: '8px', overflow: 'hidden',
      }}>
        <summary style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '12px 16px', cursor: 'pointer',
          background: '#f8fafc', borderBottom: '1px solid #e2e8f0',
          fontWeight: 700, fontSize: '12.5px', color: 'var(--acrn-navy-dark, #162035)',
          listStyle: 'none',
        }}>
          <I.Table2 size={15} color="var(--acrn-teal-accent, #82CFCD)" />
          Cross-Visit Evidence Trajectory
        </summary>
        <div style={{ padding: '12px', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ background: '#f8fafc', textAlign: 'left', borderBottom: '2px solid #cbd5e1' }}>
                <th style={{ ...hdrCellStyle, minWidth: '130px' }}>Parameter</th>
                {visits.map((v, i) => {
                  const isDel = v.visit_number === 5 || /deliv/i.test(v.name || '');
                  const isPost = v.visit_number === 6 || /post|eos/i.test(v.name || '');
                  return (
                    <th key={v.id || i} style={{
                      ...cellStyle, fontWeight: 700,
                      color: isDel || isPost ? '#6b21a8' : 'var(--acrn-navy-dark, #162035)',
                      borderTop: isDel || isPost ? '3px solid #8b5cf6' : 'none',
                      background: isDel || isPost ? '#f5f3ff' : '#f8fafc',
                    }}>
                      {v.label || `V${i+1}`}
                      {v.date ? <div style={{ fontSize: '10px', fontWeight: 400, color: '#64748b' }}>{formatVisitDate(v.date)}</div> : null}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {[
                { label: 'Blood Pressure', fn: v => v.vitals?.bp || (v.bp?.[0] ? `${v.bp[0].sbp}/${v.bp[0].dbp}` : null) },
                { label: 'Recheck BP', fn: v => v.vitals?.recheck || null },
                { label: 'Proteinuria', fn: v => v.proteinuria?.[0]?.value || null },
                { label: 'Platelets', fn: v => v.labs?.find(l => l.key === 'PLATELETS')?.raw || null },
                { label: 'Creatinine', fn: v => v.labs?.find(l => l.key === 'CREATININE')?.raw || null },
                { label: 'AST / ALT', fn: v => { const a = v.labs?.find(l => l.key === 'AST')?.raw; const b = v.labs?.find(l => l.key === 'ALT')?.raw; return a && b ? `${a} / ${b}` : (a || b || null); } },
                { label: 'LDH', fn: v => v.labs?.find(l => l.key === 'LDH')?.raw || null },
                { label: 'GA', fn: v => v.gestationalLabel || null },
              ].map((row, ri) => (
                <tr key={row.label} style={{ background: ri % 2 === 0 ? '#ffffff' : '#fafafa' }}>
                  <td style={{ ...hdrCellStyle, fontSize: '12px' }}>{row.label}</td>
                  {visits.map((v, i) => {
                    const val = row.fn(v);
                    return (
                      <td key={i} style={{ ...cellStyle, color: val ? '#162035' : '#94a3b8', fontStyle: val ? 'normal' : 'italic' }}>
                        {val || '—'}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      {/* ── Adjudicator Notice ───────────────────────────────────────────── */}
      <div style={{
        background: '#fffbeb', border: '1px solid #fde68a',
        borderLeft: '4px solid #f59e0b', borderRadius: '8px',
        padding: '14px 18px', display: 'flex', gap: '10px', alignItems: 'flex-start',
      }}>
        <I.AlertTriangle size={18} color="#b45309" style={{ flexShrink: 0, marginTop: '1px' }} />
        <div style={{ fontSize: '12.5px', color: '#78350f', lineHeight: 1.65 }}>
          <strong>Adjudicator Responsibility:</strong> This automated synthesis presents structured source evidence only. No automated classification constitutes a clinical determination. The reviewing physician must independently assess the full clinical trajectory against ISSHP criteria and document a formal determination with rationale below.
        </div>
      </div>
    </div>
  );
}


// Retain compatibility exports for legacy references
export function BloodPressureGroup({ visit }) {
  return <ClinicalVitalsStrip vitals={visit?.vitals} ga={visit?.gestationalLabel || visit?.ga} />;
}

export function LaboratoryResultsGroup({ visit }) {
  return <StructuredLabTable labs={buildLabsForTable(visit?.labs, visit?.otherResults)} />;
}

export function VisitInterpretationCard({ visit }) {
  return null;
}

export function LongitudinalEvidenceTable({ visits }) {
  return <OverallSummary visits={visits} />;
}

// Default Export Component
export default function VisitEvidenceSections({
  caseData,
  visits: rawVisits,
  selectedIndex = 0,
  onSelectVisit,
  showRibbon = true,
  showComparison = true
}) {
  const visits = normalizeVisitEvidence(caseData || { visits: rawVisits || [] });
  if (!visits.length) {
    return (
      <div style={{ background: '#f8fafc', padding: '20px', borderRadius: '8px', textAlign: 'center', border: '1px solid #cbd5e1' }}>
        <strong style={{ color: '#0f172a' }}>No visit-level evidence is available.</strong>
        <p style={{ color: '#64748b', fontSize: '13px', margin: '6px 0 0' }}>The coordinator must reconcile the visit packet before adjudication.</p>
      </div>
    );
  }

  const overall = selectedIndex >= visits.length;
  const selected = visits[Math.min(selectedIndex, visits.length - 1)];

  return (
    <div className="visit-evidence-container" style={{ gridColumn: '1 / -1' }}>
      {showRibbon && (
        <VisitRibbon
          visits={visits}
          selectedIndex={selectedIndex}
          onSelectVisit={onSelectVisit}
        />
      )}
      {overall ? (
        <OverallSummary visits={visits} caseData={caseData} />
      ) : (
        <VisitEvidencePanel
          visit={selected}
          selectedIndex={selectedIndex}
          visitCount={visits.length}
          onSelectVisit={onSelectVisit}
          caseData={caseData}
        />
      )}
    </div>
  );
}
