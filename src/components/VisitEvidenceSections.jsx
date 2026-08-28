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

export function EvidenceStatusBadge({ state = 'available' }) {
  const Icon = stateIcon[state] || I.CheckCircle2;
  return <span className={`evidence-status ${state}`}><Icon size={12} />{statusLabel(state)}</span>;
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
            <small>{complete ? 'V1–V6 signed' : `Review after V1–V6 (${signedCount}/6)`}</small>
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

export function LongitudinalEvidenceTable({ visits, selectedIndex, onSelectVisit }) {
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
                <th key={visit.id} scope="col" className={selectedIndex === index ? 'selected' : ''}>
                  <button type="button" onClick={() => onSelectVisit?.(index)}>
                    {visitLabel(visit, index)}
                    <span>{formatVisitDate(visit.date)}</span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <th scope="row">{row.label}{row.unit && <span>{row.unit}</span>}</th>
                {row.cells.map((cell, index) => (
                  <td key={`${row.key}-${cell.visitId}`} className={selectedIndex === index ? 'selected' : ''} onClick={() => onSelectVisit?.(index)}>
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
    const currentTime = new Date(row.observed_at || 0).getTime();
    const existingTime = new Date(existing?.observed_at || 0).getTime();
    if (!existing || currentRank > existingRank || (currentRank === existingRank && currentTime >= existingTime)) {
      grouped.set(row.key, { ...row, source_count: (existing?.source_count || 0) + 1 });
    } else {
      existing.source_count = (existing.source_count || 1) + 1;
    }
  });
  return ['PLATELETS', 'CREATININE', 'AST', 'ALT', 'LDH'].map(key => grouped.get(key)).filter(Boolean);
}

function labInterpretation(row) {
  if (row.evidence_state === 'severe') return 'Severe or decision-changing abnormality flagged';
  if (row.evidence_state === 'abnormal') return 'Abnormal result flagged';
  if (row.evidence_state === 'pending') return 'Result pending';
  if (row.evidence_state === 'conflicting') return 'Conflicting evidence, query required';
  if (row.evidence_state === 'not_available') return 'Not available';
  return 'Recorded, no abnormal flag supplied';
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
              <small>{formatVisitDateTime(pair.initial?.observed_at)} · {pair.initial?.source_label}</small>
              <EvidenceStatusBadge state={pair.severe ? 'severe' : pair.initial?.evidence_state} />
            </div>
            <div>
              <span>Recheck</span>
              {pair.recheck ? (
                <>
                  <strong>{pair.recheck.sbp ?? '-'} / {pair.recheck.dbp ?? '-'} mmHg</strong>
                  <small>{formatVisitDateTime(pair.recheck.observed_at)} · {pair.recheck.source_label}</small>
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
  const renderLabRow = (row) => (
    <div className="evidence-row" key={row.id}>
      <div><strong>{row.label}</strong><small>{labInterpretation(row)}</small></div>
      <div><span>{row.raw ?? row.value} {row.unit || ''}</span><EvidenceStatusBadge state={row.evidence_state} />{row.observed_at && <small>Latest recorded {formatVisitDateTime(row.observed_at)}</small>}</div>
    </div>
  );
  return (
    <section className="clinical-block lab-results-block">
      <h5><I.Database size={14} />Biochemistry and haematology</h5>
      {keyLabs.length ? <div className="evidence-list clinical-lab-list">{keyLabs.map(renderLabRow)}</div> : <div className="evidence-empty"><EvidenceStatusBadge state="not_available" />No permitted platelet, renal or liver laboratory result is available for this visit.</div>}
      <EvidenceList
        rows={keyLabs}
        empty="No permitted platelet, renal or liver laboratory result is available for this visit."
        render={(row) => (
          <div className="evidence-row" key={row.id}>
            <div><strong>{row.label}</strong><small>{formatVisitDateTime(row.observed_at)} · {row.source_label}</small></div>
            <div><span>{row.raw ?? row.value} {row.unit || ''}</span><EvidenceStatusBadge state={row.evidence_state} /></div>
          </div>
        )}
      />
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
            <div><strong>{row.method}</strong><small>{formatVisitDateTime(row.observed_at)} · {row.source_label}</small></div>
            <div><span>{row.value} {row.unit || ''}</span><EvidenceStatusBadge state={row.evidence_state} /></div>
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
              render={(row) => <p key={row.id}>{row.value}<small>{formatVisitDateTime(row.observed_at)} · {row.source_label}</small><EvidenceStatusBadge state={row.evidence_state} /></p>}
            />
          </div>
        ))}
      </div>
    </section>
  );
}

export function VisitInterpretationCard({ visit }) {
  const i = visit.interpretation;
  return (
    <section className="visit-interpretation-card" aria-labelledby={`interpretation-${visit.id}`}>
      <h5 id={`interpretation-${visit.id}`}><I.FileSearch size={14} />Visit interpretation</h5>
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

export function VisitEvidencePanel({ visit }) {
  return (
    <section className="visit-section">
      <div className="visit-panel-heading">
        <div>
          <strong>{visit.label}</strong>
          <span>{formatVisitDate(visit.date)} · {visit.gestationalLabel || 'GA/postpartum status not documented'}</span>
        </div>
        <span className="visit-scope-badge">Visit-specific evidence</span>
      </div>
      <BloodPressureGroup visit={visit} />
      <LaboratoryResultsGroup visit={visit} />
      <ProteinuriaGroup visit={visit} />
      <OtherEvidenceGroup visit={visit} />
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
      {showRibbon && <VisitRibbon visits={visits} selectedIndex={selectedIndex} onSelectVisit={onSelectVisit} />}
      {showComparison && <LongitudinalEvidenceTable visits={visits} selectedIndex={Math.min(selectedIndex, visits.length - 1)} onSelectVisit={onSelectVisit} />}
      {overall ? <OverallSummary visits={visits} /> : <VisitEvidencePanel visit={selected} />}
    </div>
  );
}
