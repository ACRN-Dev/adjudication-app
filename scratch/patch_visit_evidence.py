# Patch src/services/visitEvidence.js
with open("src/services/visitEvidence.js", "rb") as f:
    c = f.read().replace(b"\r\n", b"\n")

# 1. Update CREATININE in LAB_RANGES
old_creat = b"  CREATININE:      { low: 48,    high: 131  },"
new_creat = b"  CREATININE:      { low: 40,    high: 90   },"
assert old_creat in c, "old_creat not found"
c = c.replace(old_creat, new_creat, 1)

# 2. Update formatLabResult for urinalysis numbers (e.g. 2 -> 2+, 0 -> Negative)
old_fmt = b'''    if (key && key.startsWith('UA_') && Number.isInteger(num) && num > 0 && num <= 5) {
      return `${num}+`;
    }
    return String(num);'''

new_fmt = b'''    const isUa = (key && /^(ua_|dipstick|protein)/i.test(key));
    if (isUa && Number.isInteger(num)) {
      if (num === 0) return 'Negative';
      if (num > 0 && num <= 5) return `${num}+`;
    }
    return String(num);'''

assert old_fmt in c, "old_fmt not found"
c = c.replace(old_fmt, new_fmt, 1)

# 3. Update getLabReferenceRange to append unit
old_ref = b'''export function getLabReferenceRange(key) {
  const range = LAB_RANGES[key];
  if (!range) return null;
  if (range.low != null && range.high != null) return `${range.low} - ${range.high}`;
  if (range.high != null) return `< ${range.high}`;
  if (range.low != null) return `> ${range.low}`;
  return null;
}'''

new_ref = b'''export function getLabReferenceRange(key) {
  const range = LAB_RANGES[key];
  if (!range) return null;
  const unit = LAB_UNITS[key];
  const unitStr = unit ? ` ${unit}` : '';
  if (range.low != null && range.high != null) return `${range.low} - ${range.high}${unitStr}`;
  if (range.high != null) return `< ${range.high}${unitStr}`;
  if (range.low != null) return `> ${range.low}${unitStr}`;
  return null;
}'''

assert old_ref in c, "old_ref not found"
c = c.replace(old_ref, new_ref, 1)

# 4. In normalizeLabs, deduplicate UA_PROTEIN so only one appears per visit
old_dedup = b'''  }))).filter((row) => {
    const sig = `${row.key}-${row.value}`;
    if (seenByName.has(sig)) return false;
    seenByName.add(sig);
    return true;
  });'''

new_dedup = b'''  }))).filter((row) => {
    if (row.key === 'UA_PROTEIN') {
      if (seenByName.has('UA_PROTEIN')) return false;
      seenByName.add('UA_PROTEIN');
      return true;
    }
    const sig = `${row.key}-${row.value}`;
    if (seenByName.has(sig)) return false;
    seenByName.add(sig);
    return true;
  });'''

assert old_dedup in c, "old_dedup not found"
c = c.replace(old_dedup, new_dedup, 1)

with open("src/services/visitEvidence.js", "wb") as f:
    f.write(c)
print("Updated src/services/visitEvidence.js successfully")
