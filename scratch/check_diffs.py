import subprocess

for f in ['backend/services/realtime_mapping.py', 'src/services/visitEvidence.js', 'src/components/VisitEvidenceSections.jsx']:
    print(f"=== DIFF SUMMARY FOR {f} ===")
    res = subprocess.run(['git', 'diff', f], capture_output=True, text=True, encoding='utf-8', errors='replace')
    lines = res.stdout.splitlines()
    print(f"Total lines of diff: {len(lines)}")
    # Print lines that look like additions or deletions around labs or alc or anc or rbc or protein
    for l in lines:
        if any(k in l.lower() for k in ['lymphocyte', 'neutrophil', 'hematocrit', 'alc', 'anc', 'rbc', 'dipstick', 'protein', '40 - 90', 'biochemistry']):
            print(l[:120])
