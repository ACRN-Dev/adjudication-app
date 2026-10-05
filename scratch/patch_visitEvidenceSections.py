import re

with open('src/components/VisitEvidenceSections.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update VisitHeaderBanner to handle non-performed visits
target_header_banner = """  const visitNum = visit.visit_number || selectedIndex + 1;
  const visitName = (visit.name && !visit.name.startsWith('V0')) ? `Visit ${visitNum}: ${visit.name}` : (visit.name || visit.visit_code || `Visit ${visitNum}`);
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
          background: 'var(--acrn-navy-dark, #162035)',
          border: '2px solid var(--acrn-orange-primary, #F07E26)',
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
          <div style={{ fontSize: '12px', color: 'var(--text-muted, #64748b)', marginTop: '2px' }}>
            {dateStr} {gaLabel ? ` · Gestational Age: ${gaLabel}` : ''}
          </div>
        </div>
      </div>"""

replacement_header_banner = """  const visitNum = visit.visit_number || selectedIndex + 1;
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
      </div>"""

# 2. Update buildVisitNarrative and its helpers
target_narrative = """function buildVisitNarrative(visit, visitNum) {
  const title = visitHeadingTitle(visit, visitNum);
  const visitDate = visit?.date ? formatVisitDate(visit.date) : 'date not documented';
  const bp = visit?.vitals?.bp;
  const bpRecheck = visit?.vitals?.recheck;
  const bpClause = bp
    ? `Blood pressure was recorded as ${bp}${bpRecheck ? ` with recheck ${bpRecheck}` : ''}.`
    : 'Blood pressure evidence was not available for this visit.';
  const ga = visit?.gestationalLabel || (visitNum === 6 ? 'postpartum timing not calculated from mapped dates' : 'gestational age not available');
  const proteinClause = describeProteinuria(visit);

  if (visitNum === 5) {
    return `Visit ${visitNum} is presented as ${title.toLowerCase()} dated ${visitDate}. Delivery, maternal outcome and newborn findings below are limited to mapped source evidence. ${proteinClause}`;
  }
  if (visitNum === 6) {
    return `Visit ${visitNum} is presented as a postpartum/end-of-study visit dated ${visitDate}. Gestational/postpartum timing: ${ga}. ${bpClause} ${proteinClause} ${describeOrganEvidence(visit)}`;
  }
  return `Visit ${visitNum} is dated ${visitDate}. Gestational/postpartum age: ${ga}. ${bpClause} ${proteinClause} ${describeSymptoms(visit)} ${describeOrganEvidence(visit)}`;
}"""

replacement_narrative = """function buildVisitNarrative(visit, visitNum, caseData) {
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
    return paragraphs.join('\\n\\n');
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

  return paragraphs.join('\\n\\n');
}"""

# 3. Update narrativeText call in VisitEvidencePanel
target_panel_call = "{narrativeText || buildVisitNarrative(visit, visitNum)}"
replacement_panel_call = "{narrativeText || buildVisitNarrative(visit, visitNum, caseData)}"

# Normalize newlines
content_nl = content.replace('\r\n', '\n')
target_hb_nl = target_header_banner.replace('\r\n', '\n')
replacement_hb_nl = replacement_header_banner.replace('\r\n', '\n')
target_nar_nl = target_narrative.replace('\r\n', '\n')
replacement_nar_nl = replacement_narrative.replace('\r\n', '\n')

assert target_hb_nl in content_nl, "Header banner target not found"
content_nl = content_nl.replace(target_hb_nl, replacement_hb_nl, 1)

assert target_nar_nl in content_nl, "Narrative target not found"
content_nl = content_nl.replace(target_nar_nl, replacement_nar_nl, 1)

assert target_panel_call in content_nl, "Panel call target not found"
content_nl = content_nl.replace(target_panel_call, replacement_panel_call, 1)

with open('src/components/VisitEvidenceSections.jsx', 'w', encoding='utf-8') as f:
    f.write(content_nl)

print('SUCCESSFULLY PATCHED VisitEvidenceSections.jsx')
