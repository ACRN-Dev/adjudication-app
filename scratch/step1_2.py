import sys

filepath = r'c:\Automation\Adjudication app\src\components\AdjudicatorWorkbench.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Ultrasound link to Header Actions
header_old = '''<button className="btn-back" style={{ padding: '5px 10px' }} onClick={onOpenSourceDocs}>
                Inspect Raw Docs
              </button>'''
header_new = '''<button className="btn-back" style={{ padding: '5px 10px' }} onClick={onOpenSourceDocs}>
                Inspect Raw Docs
              </button>
              <button 
                className="btn-secondary" 
                style={{ padding: '5px 10px', background: '#f5f3ff', color: '#6d28d9', borderColor: '#c4b5fd', fontWeight: 600 }} 
                onClick={onOpenSourceDocs}
              >
                <FileText size={13} style={{ marginRight: '4px' }} />
                View Dating Ultrasound Scan
              </button>'''
content = content.replace(header_old, header_new)

# 2. Add Inclusion/Exclusion Criteria above PatientHistoryPanel
inc_exc_html = '''
          <DropdownSection title="Study Inclusion / Exclusion Criteria" icon={<ShieldCheck size={16} />} defaultOpen={true}>
            <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '6px', border: '1px solid #cbd5e1' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                <div>
                  <h4 style={{ color: '#15803d', display: 'flex', alignItems: 'center', gap: '6px', marginTop: 0 }}>
                    <CheckCircle2 size={16} /> Inclusion Criteria Met
                  </h4>
                  <ul style={{ listStyleType: 'none', padding: 0, margin: 0, fontSize: '13px', color: '#334155' }}>
                    <li style={{ marginBottom: '6px' }}>✅ Female, aged 18 to 45 years.</li>
                    <li style={{ marginBottom: '6px' }}>✅ Viable singleton pregnancy.</li>
                    <li style={{ marginBottom: '6px' }}>✅ Gestational age &lt; 20 weeks at enrollment.</li>
                    <li>✅ Signed informed consent.</li>
                  </ul>
                </div>
                <div>
                  <h4 style={{ color: '#b91c1c', display: 'flex', alignItems: 'center', gap: '6px', marginTop: 0 }}>
                    <AlertCircle size={16} /> Exclusion Criteria Cleared
                  </h4>
                  <ul style={{ listStyleType: 'none', padding: 0, margin: 0, fontSize: '13px', color: '#334155' }}>
                    <li style={{ marginBottom: '6px' }}>🚫 Chronic hypertension diagnosed prior to 20 weeks.</li>
                    <li style={{ marginBottom: '6px' }}>🚫 Pre-existing chronic kidney disease.</li>
                    <li style={{ marginBottom: '6px' }}>🚫 Known severe fetal anomaly.</li>
                    <li>🚫 History of eclampsia in previous pregnancy.</li>
                  </ul>
                </div>
              </div>
            </div>
          </DropdownSection>

          <PatientHistoryPanel caseData={activeCase} />'''
content = content.replace('<PatientHistoryPanel caseData={activeCase} />', inc_exc_html)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Success applying UI changes to AdjudicatorWorkbench")
