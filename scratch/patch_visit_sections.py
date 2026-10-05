with open("src/components/VisitEvidenceSections.jsx", "rb") as f:
    c = f.read().replace(b"\r\n", b"\n")

# 1. Update clinicalValue to map 0 -> 'Negative' and 1..5 -> '1+'..'5+' for dipstick/protein
old_cv = b'''function clinicalValue(row) {
  if (!row) return null;
  const value = row.raw ?? row.value ?? row.raw_source_value ?? row.parsed_text_value ?? row.coded_value;
  if (value == null || value === '') return null;
  return row.unit ? `${value} ${row.unit}` : String(value);
}'''

new_cv = b'''function clinicalValue(row) {
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
}'''

assert old_cv in c, "old_cv not found"
c = c.replace(old_cv, new_cv, 1)

# 2. Update buildLabsForTable to deduplicate protein dipstick
old_bl = b'''function buildLabsForTable(liveLabs, otherResults = []) {
  const rows = [...(liveLabs || []), ...(otherResults || [])];
  if (rows.length > 0) {
    return rows.map((row) => {'''

new_bl = b'''function buildLabsForTable(liveLabs, otherResults = []) {
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
    return dedupedRows.map((row) => {'''

assert old_bl in c, "old_bl not found"
c = c.replace(old_bl, new_bl, 1)

with open("src/components/VisitEvidenceSections.jsx", "wb") as f:
    f.write(c)

print("Updated src/components/VisitEvidenceSections.jsx successfully")
