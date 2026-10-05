with open("src/components/VisitEvidenceSections.jsx", "rb") as f:
    c = f.read().replace(b"\r\n", b"\n")

# 1. Remove the Summary MarkdownDisclosure block
old_summary_block = b'''      <MarkdownDisclosure title="Summary" icon={<I.FileText size={15} color="var(--acrn-orange-primary, #F07E26)" />} defaultOpen>
        <BulletList
          items={[
            { label: 'Gestational / postpartum age', value: visit?.gestationalLabel || 'Not available from mapped evidence' },
            { label: 'Initial BP', value: initialBp || 'Not available from mapped evidence' },
            { label: 'BP recheck', value: recheckBp || 'Not available from mapped evidence' },
            { label: 'Proteinuria', value: describeProteinuria(visit) },
            { label: 'Symptoms', value: describeSymptoms(visit) },
            { label: 'Maternal organ findings', value: describeOrganEvidence(visit) },
          ]}
        />
      </MarkdownDisclosure>'''

assert old_summary_block in c, "old_summary_block not found"
c = c.replace(old_summary_block, b"", 1)

# 2. Also ensure describeProteinuria doesn't repeat identical sentences
old_desc_prot = b'''function describeProteinuria(visit) {
  const rows = visit?.proteinuria || [];
  if (!rows.length) return 'Proteinuria status was not available for this visit.';
  return rows.map((row) => {
    const method = row.method || row.label || row.key || 'proteinuria';
    const value = clinicalValue(row) || row.evidence_state || 'recorded without a displayable value';
    if (/negative/i.test(value)) return `The source records a negative ${method} result.`;
    return `${method}: ${value}.`;
  }).join(' ');
}'''

new_desc_prot = b'''function describeProteinuria(visit) {
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
}'''

assert old_desc_prot in c, "old_desc_prot not found"
c = c.replace(old_desc_prot, new_desc_prot, 1)

with open("src/components/VisitEvidenceSections.jsx", "wb") as f:
    f.write(c)

print("Successfully removed Summary block and deduplicated describeProteinuria")
