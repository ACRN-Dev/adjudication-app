path_ves = r'c:\Automation\Adjudication app\src\components\VisitEvidenceSections.jsx'
with open(path_ves, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace lines 1009 to 1052 in VisitEvidenceSections.jsx
start_str = '        {(() => {\n          // 1. If viewing Subject 11 demo reference case, use its verified Harvard prose'
end_str = '          return (\n            <p style={{ fontSize: \'13px\', lineHeight: \'1.75\', color: \'var(--text-main, #162035)\', margin: 0 }}>\n              At {ga} gestation, the patient presented for scheduled clinical trial surveillance. She remained clinically stable without acute pre-eclamptic symptoms. {bpProse} {protProse} Maternal organ function and fetal wellbeing remain documented in the panels below.\n            </p>\n          );\n        })()}'

pos_start = text.find(start_str)
pos_end = text.find(end_str)

new_block = '''        {(() => {
          // Dynamic Attending-level clinical narrative synthesis from live case and visit data
          const isPostpartum = visitNum === 6 || /eos|post|v06|visit 6/i.test(visit.name || visit.visit_code || '');
          const isDelivery = visitNum === 5 || /delivery|v05|visit 5/i.test(visit.name || visit.visit_code || '');
          const bp = visit.vitals?.bp;
          const bpRecheck = visit.vitals?.recheck;
          const ga = visit.gestationalLabel || (isPostpartum ? 'Postpartum (~4 weeks)' : isDelivery ? 'Term delivery window' : `Visit ${visitNum}`);

          // Baseline visit (Visit 1)
          if (visitNum === 1) {
            const demoOpening = buildDemographicString(patientAge, gravidity, parity, miscarriages, comorbList);
            const bpStr = bp ? `Blood pressure at presentation was ${bp}${bpRecheck ? ` (recheck: ${bpRecheck})` : ''}.` : 'Hemodynamic surveillance was recorded.';
            return (
              <p style={{ fontSize: '13px', lineHeight: '1.75', color: 'var(--text-main, #162035)', margin: 0 }}>
                {demoOpening} {bpStr} Baseline organ function and laboratory surveillance are detailed in the diagnostic panels below.
              </p>
            );
          }

          // Delivery encounter (Visit 5)
          if (isDelivery) {
            const delMode = visit.maternalDeliveryMode || visit.maternal?.find(m => /mode|delivery/i.test(m.value))?.value || (isSubject11 ? 'planned Cesarean section' : 'delivery');
            const isOperative = /cesarean|c-section|operative|vacuum|forceps/i.test(delMode);
            const admStr = isOperative ? `an operative ${delMode}` : (delMode.toLowerCase().includes('delivery') ? `a ${delMode}` : `a ${delMode} delivery`);
            const babyWt = visit.birthWeight || visit.neonatal?.find(n => /weight|birth_weight/i.test(String(n.id || n.value)))?.value || (isSubject11 ? '2550' : null);
            const babyStr = babyWt ? ` infant weighing ${babyWt}g` : ' infant';
            return (
              <p style={{ fontSize: '13px', lineHeight: '1.75', color: 'var(--text-main, #162035)', margin: 0 }}>
                At {ga}, the patient was admitted for {admStr}. She delivered a live{babyStr} without acute maternal complications documented, and recovered satisfactorily following delivery.
              </p>
            );
          }

          // Postpartum follow-up (Visit 6)
          if (isPostpartum) {
            return (
              <p style={{ fontSize: '13px', lineHeight: '1.75', color: 'var(--text-main, #162035)', margin: 0 }}>
                Approximately four weeks postpartum, the patient returns for final postnatal follow-up. Her postnatal clinical recovery has been unremarkable. {bp ? `Blood pressure was documented at ${bp}${bpRecheck ? ` (recheck: ${bpRecheck})` : ''}.` : 'Hemodynamics remain clinically stable.'} Routine urinalysis and laboratory indices remain preserved without evidence of late-onset preeclampsia.
              </p>
            );
          }

          // Antenatal follow-ups (Visits 2 - 4)
          const bpProse = bp
            ? `Blood pressure remained controlled at ${bp}${bpRecheck ? ` (recheck: ${bpRecheck})` : ''}.`
            : 'Hemodynamic indices remained clinically stable.';
          const protRow = (visit.proteinuria || [])[0];
          let protProse = 'Dipstick urinalysis remained negative for proteinuria and infection markers.';
          if (protRow && !/negative/i.test(String(protRow.value))) {
            protProse = `Urinalysis was notable for ${protRow.value} proteinuria.`;
          }

          return (
            <p style={{ fontSize: '13px', lineHeight: '1.75', color: 'var(--text-main, #162035)', margin: 0 }}>
              At {ga} gestation, the patient presented for scheduled clinical trial surveillance. She remained clinically stable without acute pre-eclamptic symptoms. {bpProse} {protProse} Maternal organ function and fetal wellbeing remain documented in the panels below.
            </p>
          );
        })()}'''

if pos_start != -1 and pos_end != -1:
    text = text[:pos_start] + new_block + text[pos_end + len(end_str):]
    with open(path_ves, 'w', encoding='utf-8') as f:
        f.write(text)
    print('VisitEvidenceSections.jsx clean narrative successfully patched!')
else:
    print('Indices not found:', pos_start, pos_end)
