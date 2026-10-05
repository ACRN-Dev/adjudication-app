with open('src/components/VisitEvidenceSections.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

target = """      <MarkdownDisclosure title={visitNum === 5 ? 'Delivery and Newborn Findings' : visitNum === 6 ? 'Postpartum and Infant Status' : 'Patient History and Assessment'} icon={<I.ClipboardList size={15} color="var(--acrn-orange-primary, #F07E26)" />} defaultOpen>
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

      <MarkdownDisclosure title="Source Provenance" icon={<I.ListChecks size={15} color="var(--acrn-orange-primary, #F07E26)" />} defaultOpen={false}>
        <SourceProvenanceList labs={labs} />
      </MarkdownDisclosure>"""

replacement = """      {visit?.is_not_performed ? (
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

          <MarkdownDisclosure title="Source Provenance" icon={<I.ListChecks size={15} color="var(--acrn-orange-primary, #F07E26)" />} defaultOpen={false}>
            <SourceProvenanceList labs={labs} />
          </MarkdownDisclosure>
        </>
      )}"""

content_nl = content.replace('\r\n', '\n')
target_nl = target.replace('\r\n', '\n')
replacement_nl = replacement.replace('\r\n', '\n')

assert target_nl in content_nl, "Target disclosures not found in VisitEvidenceSections.jsx"
content_nl = content_nl.replace(target_nl, replacement_nl, 1)

with open('src/components/VisitEvidenceSections.jsx', 'w', encoding='utf-8') as f:
    f.write(content_nl)

print('SUCCESSFULLY PATCHED disclosures in VisitEvidenceSections.jsx')
