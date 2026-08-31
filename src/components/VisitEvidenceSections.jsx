import React from 'react';
import * as I from 'lucide-react';
import {
  buildLongitudinalRows,
  formatInterval,
  formatVisitDate,
  formatVisitDateTime,
  isReviewerVisitSigned,
  isVisitComplete,
  normalizeVisitEvidence,
  pairBpReadings,
  statusLabel,
  visitLabel,
} from '../services/visitEvidence';

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
  return <span className={`evidence-status ${state}`}><Icon size={12} />{label || statusLabel(state)}</span>;
}

export function VisitRibbon({ visits = [], selectedIndex = 0, onSelectVisit, showOverall = true }) {
  const expectedVisits = visits.slice(0, 6);
  const signedCount = expectedVisits.filter((visit) => isReviewerVisitSigned(visit) || isVisitComplete(visit)).length;
  const complete = expectedVisits.length === 6 && expectedVisits.every((visit) => isReviewerVisitSigned(visit) || isVisitComplete(visit));
  return (
    <nav className="visit-ribbon-wrap" aria-label="Adjudication visits">
      <div className="visit-ribbon">
        {expectedVisits.map((visit, index) => {
          const completeVisit = isVisitComplete(visit);
          const reviewerSigned = isReviewerVisitSigned(visit);
          return (
            <button
              key={visit.id || `${visitLabel(visit, index)}-${index}`}
              type="button"
              className={`visit-ribbon-tab ${selectedIndex === index ? 'active' : ''} ${completeVisit ? 'complete' : reviewerSigned ? 'signed' : ''}`}
              aria-current={selectedIndex === index ? 'step' : undefined}
              onClick={() => onSelectVisit?.(index)}
            >
              <span>{visitLabel(visit, index)}</span>
              <small>{formatVisitDate(visit.date || visit.visit_date)}</small>
              {completeVisit ? <I.CheckCircle2 size={13} /> : reviewerSigned ? <I.PenLine size={13} /> : null}
            </button>
          );
        })}
        {showOverall && (
          <button
            type="button"
            disabled={!complete}
            title={complete ? 'View overall adjudication' : 'Available after all visits have final adjudication status'}
            className={`visit-ribbon-tab overall ${selectedIndex === visits.length ? 'active' : ''}`}
            onClick={() => complete && onSelectVisit?.(expectedVisits.length)}
          >
            <span>Overall</span>
            <small>{complete ? 'V1â€“V6 signed' : `Review after V1â€“V6 (${signedCount}/6)`}</small>
            {complete ? <I.CheckCircle2 size={13} /> : <I.Lock size={13} />}
          </button>
        )}
      </div>
    </nav>
  );
}

function ValueWithState({ value, state, change }) {
  return (
    <div className="longitudinal-cell">
      <span>{value}</span>
      <EvidenceStatusBadge state={state} />
      {change && <small>{change}</small>}
    </div>
  );
}

export function LongitudinalEvidenceTable({ visits }) {
  const rows = buildLongitudinalRows(visits);
  return (
    <section className="visit-section">
      <div className="visit-section-title"><I.Table2 size={15} />Longitudinal comparison</div>
      <div className="longitudinal-table-wrap">
        <table className="longitudinal-table">
          <caption>Structured visit evidence compared across available visits</caption>
          <thead>
            <tr>
              <th scope="col">Clinical measure</th>
              {visits.map((visit, index) => (
                <th key={visit.id} scope="col">
                  {visitLabel(visit, index)}
                  <span>{formatVisitDate(visit.date)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <th scope="row">{row.label}{row.unit && <span>{row.unit}</span>}</th>
                {row.cells.map((cell) => (
                  <td key={`${row.key}-${cell.visitId}`}>
                    <ValueWithState value={cell.value} state={cell.state} change={cell.change} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function EvidenceList({ rows, empty, render }) {
  if (!rows.length) return <div className="evidence-empty"><EvidenceStatusBadge state="not_available" />{empty}</div>;
  return <div className="evidence-list">{rows.map(render)}</div>;
}

function latestByMeasure(rows) {
  const rank = { severe: 5, conflicting: 4, abnormal: 3, pending: 2, not_available: 1, blinded: 1, available: 0, normal: 0 };
  const grouped = new Map();
  rows.forEach((row) => {
    const existing = grouped.get(row.key);
    const currentRank = rank[row.evidence_state] ?? 0;
    const existingRank = rank[existing?.evidence_state] ?? 0;
    const currentHasValue = row.raw != null || row.value != null;
    const existingHasValue = existing?.raw != null || existing?.value != null;
    const currentTime = new Date(row.observed_at || 0).getTime();
    const existingTime = new Date(existing?.observed_at || 0).getTime();
    if (
      !existing ||
      (currentHasValue && !existingHasValue) ||
      currentRank > existingRank ||
      (currentRank === existingRank && currentHasValue === existingHasValue && currentTime >= existingTime)
    ) {
      grouped.set(row.key, { ...row, source_count: (existing?.source_count || 0) + 1 });
    } else {
      existing.source_count = (existing.source_count || 1) + 1;
    }
  });
  return ['PLATELETS', 'CREATININE', 'AST', 'ALT', 'LDH'].map(key => grouped.get(key)).filter(Boolean);
}

const DEFAULT_LAB_RANGES = {
  PLATELETS: { low: 150, high: 400, unit: 'x10^3 cells/uL' },
  CREATININE: { low: 48, high: 131, unit: 'umol/L' },
  AST: { low: 10, high: 30, unit: 'U/L' },
  ALT: { low: 5, high: 44, unit: 'U/L' },
  LDH: { low: 180, high: 325, unit: 'U/L' },
};

function rangeLabel(row) {
  const ref = row.reference || row.reference_range || row.range || DEFAULT_LAB_RANGES[row.key];
  if (!ref) return 'Reference range not configured';
  if (typeof ref === 'string') return ref;
  const low = ref.low ?? ref.lower;
  const high = ref.high ?? ref.upper;
  const unit = ref.unit || row.unit || '';
  if (low != null && high != null) return `Range ${low}-${high} ${unit}`.trim();
  if (low != null) return `Range >= ${low} ${unit}`.trim();
  if (high != null) return `Range <= ${high} ${unit}`.trim();
  return 'Reference range not configured';
}

function numericValue(value) {
  if (typeof value === 'number') return value;
  const match = String(value ?? '').replace(',', '.').match(/-?\d+(\.\d+)?/);
  return match ? Number(match[0]) : null;
}

function referenceBounds(row) {
  const ref = row.reference || row.reference_range || row.range || DEFAULT_LAB_RANGES[row.key];
  if (!ref) return {};
  if (typeof ref === 'string') {
    const numbers = ref.match(/-?\d+(\.\d+)?/g)?.map(Number) || [];
    if (numbers.length >= 2) return { low: numbers[0], high: numbers[1] };
    if (/<=|<|up to/i.test(ref) && numbers.length) return { high: numbers[0] };
    if (/>=|>|from/i.test(ref) && numbers.length) return { low: numbers[0] };
    return {};
  }
  return { low: ref.low ?? ref.lower, high: ref.high ?? ref.upper };
}

function labValueLabel(row) {
  const actual = row.raw ?? row.value;
  if (actual == null || String(actual).trim() === '') return 'Actual value not imported';
  return `${actual}${row.unit ? ` ${row.unit}` : ''}`;
}

function labRangeStatus(row) {
  const value = numericValue(row.raw ?? row.value);
  const { low, high } = referenceBounds(row);
  if (value == null || (low == null && high == null)) {
    return { state: row.evidence_state || 'available', label: statusLabel(row.evidence_state || 'available') };
  }
  if (low != null && value < low) return { state: 'abnormal', label: 'Low' };
  if (high != null && value > high) return { state: 'abnormal', label: 'High' };
  return { state: 'normal', label: 'Normal' };
}

export function BloodPressureGroup({ visit }) {
  const pairs = pairBpReadings(visit.bp);
  return (
    <section className="clinical-block">
      <h5><I.Activity size={14} />Blood pressure</h5>
      <EvidenceList
        rows={pairs}
        empty="No blood pressure observation is available for this visit."
        render={(pair, index) => (
          <div className="bp-pair" key={`${pair.initial?.id || 'bp'}-${index}`}>
            <div>
              <span>Initial</span>
              <strong>{pair.initial?.sbp ?? '-'} / {pair.initial?.dbp ?? '-'} mmHg</strong>
              <small>{formatVisitDateTime(pair.initial?.observed_at)} Â· {pair.initial?.source_label}</small>
              <EvidenceStatusBadge state={pair.severe ? 'severe' : pair.initial?.evidence_state} />
            </div>
            <div>
              <span>Recheck</span>
              {pair.recheck ? (
                <>
                  <strong>{pair.recheck.sbp ?? '-'} / {pair.recheck.dbp ?? '-'} mmHg</strong>
                  <small>{formatVisitDateTime(pair.recheck.observed_at)} Â· {pair.recheck.source_label}</small>
                  <EvidenceStatusBadge state={pair.recheck.evidence_state} />
                </>
              ) : (
                <><strong>Not documented</strong><small>Confirmation not assessable</small><EvidenceStatusBadge state="not_available" /></>
              )}
            </div>
            <div>
              <span>Interval</span>
              <strong>{formatInterval(pair.interval)}</strong>
              <small>{pair.confirmed ? 'Confirmation criterion met' : 'Confirmation criterion not met or not assessable'}</small>
            </div>
          </div>
        )}
      />
    </section>
  );
}

export function LaboratoryResultsGroup({ visit }) {
  const keyLabs = latestByMeasure(visit.labs.filter((row) => ['PLATELETS', 'CREATININE', 'AST', 'ALT', 'LDH'].includes(row.key)));
  const renderLabRow = (row) => {
    const interpretation = labRangeStatus(row);
    return (
      <div className="evidence-row" key={row.id}>
        <div><strong>{row.label}</strong></div>
        <div>
          <span>{labValueLabel(row)}</span>
          <small>{rangeLabel(row)}</small>
          <EvidenceStatusBadge state={interpretation.state} label={interpretation.label} />
          {row.observed_at && <small>Latest recorded {formatVisitDateTime(row.observed_at)}</small>}
        </div>
      </div>
    );
  };
  return (
    <section className="clinical-block lab-results-block">
      <h5><I.Database size={14} />Biochemistry and haematology</h5>
      {keyLabs.length ? <div className="evidence-list clinical-lab-list">{keyLabs.map(renderLabRow)}</div> : <div className="evidence-empty"><EvidenceStatusBadge state="not_available" />No permitted platelet, renal or liver laboratory result is available for this visit.</div>}
      {false && <EvidenceList
        rows={keyLabs}
        empty="No permitted platelet, renal or liver laboratory result is available for this visit."
        render={(row) => (
          <div className="evidence-row" key={row.id}>
            <div><strong>{row.label}</strong><small>{formatVisitDateTime(row.observed_at)} Â· {row.source_label}</small></div>
            <div><span>{row.raw ?? row.value} {row.unit || ''}</span><EvidenceStatusBadge state={row.evidence_state} /></div>
          </div>
        )}
      />}
    </section>
  );
}

function ProteinuriaGroup({ visit }) {
  return (
    <section className="clinical-block">
      <h5><I.FlaskConical size={14} />Proteinuria</h5>
      <EvidenceList
        rows={visit.proteinuria}
        empty="No proteinuria observation is available for this visit."
        render={(row) => (
          <div className="evidence-row" key={row.id}>
            <div><strong>{row.method}</strong></div>
            <div><span>{row.value} {row.unit || ''}</span></div>
          </div>
        )}
      />
    </section>
  );
}

function OtherEvidenceGroup({ visit }) {
  const groups = [
    ['Symptoms', visit.symptoms, I.Stethoscope],
    ['Medication / intervention', visit.medications, I.Pill],
    ['Fetal assessment', visit.fetal, I.Baby],
  ];
  return (
    <section className="clinical-block">
      <h5><I.ClipboardList size={14} />Other visit evidence</h5>
      <div className="other-evidence-grid">
        {groups.map(([title, rows, Icon]) => (
          <div key={title}>
            <strong><Icon size={13} />{title}</strong>
            <EvidenceList
              rows={rows}
              empty="Not available"
              render={(row) => <p key={row.id}>{row.value}<small>{formatVisitDateTime(row.observed_at)} Â· {row.source_label}</small><EvidenceStatusBadge state={row.evidence_state} /></p>}
            />
          </div>
        ))}
      </div>
    </section>
  );
}

function VisitFiveOutcomeGroup({ visit }) {
  const groups = [
    ['Maternal outcome', visit.maternal || [], I.Stethoscope],
    ['Neonatal outcome', visit.neonatal || [], I.Baby],
  ];
  return <section className="clinical-block"><h5><I.ClipboardList size={14} />Visit 5 maternal and neonatal outcomes</h5><div className="other-evidence-grid">{groups.map(([title, rows, Icon]) => <div key={title}><strong><Icon size={13}/>{title}</strong><EvidenceList rows={rows} empty="Not collected or not available" render={(row)=><p key={row.id}>{row.value}<small>{formatVisitDateTime(row.observed_at)} Â· {row.source_label}</small><EvidenceStatusBadge state={row.evidence_state}/></p>}/></div>)}</div></section>;
}

export function VisitInterpretationCard({ visit }) {
  const i = visit.interpretation;
  return (
    <section className="visit-interpretation-card" aria-labelledby={`interpretation-${visit.id}`}>
      <h5 id={`interpretation-${visit.id}`}><I.FileSearch size={14} />Cumulative interpretation through this visit</h5>
      <p>{i.summary}</p>
      <dl>
        <div><dt>Classification</dt><dd>{i.classification}</dd></div>
        <div><dt>Certainty</dt><dd>{i.certainty}</dd></div>
        <div><dt>Evidence completeness</dt><dd>{i.completeness}%</dd></div>
        <div><dt>Criteria met</dt><dd>{i.criteriaMet.length ? i.criteriaMet.join('; ') : 'None documented'}</dd></div>
        <div><dt>Not assessable</dt><dd>{i.missing.length ? i.missing.join(', ') : 'None'}</dd></div>
        <div><dt>Outstanding queries</dt><dd>{i.queries.length ? i.queries.join('; ') : 'None flagged in structured evidence'}</dd></div>
      </dl>
    </section>
  );
}

export function VisitEvidencePanel({ visit, selectedIndex, visitCount, onSelectVisit }) {
  const safeSelectedIndex = Number.isInteger(selectedIndex) ? selectedIndex : 0;
  const safeVisitCount = Number.isInteger(visitCount) && visitCount > 0 ? visitCount : 1;
  return (
    <section className="visit-section">
      <div className="visit-panel-heading">
        <div>
          <strong>{visit.label}</strong>
          <span>{formatVisitDate(visit.date)} Â· {visit.gestationalLabel || 'GA/postpartum status not documented'}</span>
        </div>
        <div className="visit-step-actions">
          <button type="button" onClick={() => onSelectVisit?.(safeSelectedIndex - 1)} disabled={safeSelectedIndex <= 0}><I.ChevronLeft size={15} />Previous visit</button>
          <span className="visit-scope-badge">Visit {safeSelectedIndex + 1} of {safeVisitCount}</span>
          <button type="button" onClick={() => onSelectVisit?.(safeSelectedIndex + 1)} disabled={safeSelectedIndex >= safeVisitCount - 1}>Next visit<I.ChevronRight size={15} /></button>
        </div>
      </div>
      <BloodPressureGroup visit={visit} />
      <LaboratoryResultsGroup visit={visit} />
      <ProteinuriaGroup visit={visit} />
      <OtherEvidenceGroup visit={visit} />
      {Number(visit.visit_number) === 5 && <VisitFiveOutcomeGroup visit={visit} />}
      <VisitInterpretationCard visit={visit} />
      <p className="visit-evidence-note"><I.EyeOff size={12} />Blinded biomarker fields remain withheld. Values shown here come from permitted structured evidence only.</p>
    </section>
  );
}

export function OverallSummary({ visits }) {
  return (
    <div className="overall-visit-summary">
      <div><I.CheckCircle2 size={28} /><section><h4>Overall adjudication</h4><p>All visits have final adjudication status. This roll-up stays separate from the independently signed visit records.</p></section></div>
      <table>
        <thead><tr><th>Visit</th><th>Visit date</th><th>Interpretation</th><th>Decision status</th><th>Filing</th></tr></thead>
        <tbody>{visits.map((v, i) => <tr key={v.id}><td>{visitLabel(v, i)}</td><td>{formatVisitDate(v.date)}</td><td>{v.interpretation.classification}</td><td>{v.status || v.resolution_status || 'Finalized'}</td><td>{v.filing_status || 'Pending final filing'}</td></tr>)}</tbody>
      </table>
    </div>
  );
}

export default function VisitEvidenceSections({ caseData, visits: rawVisits, selectedIndex = 0, onSelectVisit, showRibbon = true, showComparison = true }) {
  const visits = normalizeVisitEvidence(caseData || { visits: rawVisits || [] });
  if (!visits.length) {
    return <div className="summary-feature-card"><strong>No visit-level summary is available.</strong><p>The coordinator must reconcile the visit packet before adjudication.</p></div>;
  }
  const overall = selectedIndex === visits.length;
  const selected = visits[Math.min(selectedIndex, visits.length - 1)];
  return (
    <div className="summary-feature-card visit-evidence-card" style={{ gridColumn: '1 / -1' }}>
      {showComparison && <LongitudinalEvidenceTable visits={visits} />}
      {showRibbon && (
        <section className="visit-navigation-section">
          <div className="visit-section-title"><I.ClipboardList size={15} />Select visit-specific evidence</div>
          <VisitRibbon visits={visits} selectedIndex={selectedIndex} onSelectVisit={onSelectVisit} />
        </section>
      )}
      {overall ? <OverallSummary visits={visits} /> : <VisitEvidencePanel visit={selected} selectedIndex={selectedIndex} visitCount={visits.length} onSelectVisit={onSelectVisit} />}
    </div>
  );
}
