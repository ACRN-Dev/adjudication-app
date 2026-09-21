import sys

filepath = r'c:\Automation\Adjudication app\src\components\AdjudicatorWorkbench.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

v5_code = '''
        {evidenceVisits.some(v => v.visit_number === 5 || v.visit_code === 'V05' || v.name?.includes('Visit 5')) && (
          <DropdownSection title="Fetal &amp; Neonatal Outcomes" icon={<Baby size={16} />} defaultOpen>
            <div className="summary-card-grid" style={{ marginBottom: '16px' }}>
              <div className="form-group">
                <label style={{ fontWeight: 700, display: 'flex', justifyContent: 'space-between' }}>
                  <span>Gestational Age at Delivery (weeks)</span>
                  {fetalProvenance?.GA_AT_DELIVERY && (
                    <span style={{ fontSize: '10.5px', color: '#0369a1', fontWeight: 600 }}>
                      CRF: {fetalProvenance.GA_AT_DELIVERY.raw_value || 'Documented'}
                    </span>
                  )}
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="15"
                  max="45"
                  className="form-input"
                  placeholder="e.g. 38.2"
                  value={gestationalAgeAtDelivery}
                  onChange={(e) => {
                    const val = e.target.value;
                    setGestationalAgeAtDelivery(val);
                    const n = parseFloat(val);
                    if (!Number.isNaN(n)) {
                      if (n >= 37.0) {
                        setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'DELIVERY_LT_34W'), 'DELIVERY_GE_37W'])));
                      } else if (n < 34.0) {
                        setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'DELIVERY_GE_37W' && c !== 'NORMAL_OUTCOME'), 'DELIVERY_LT_34W'])));
                      }
                    }
                  }}
                  disabled={isSigned}
                />
                <small>Numeric gestational age in weeks. Delivery outcome precedence applied.</small>
              </div>

              <div className="form-group">
                <label style={{ fontWeight: 700, display: 'flex', justifyContent: 'space-between' }}>
                  <span>Pregnancy Outcome</span>
                  {fetalProvenance?.PREGNANCY_OUTCOME && (
                    <span style={{ fontSize: '10.5px', color: '#0369a1', fontWeight: 600 }}>
                      CRF: {fetalProvenance.PREGNANCY_OUTCOME.raw_value || 'Documented'}
                    </span>
                  )}
                </label>
                <select
                  className="form-select"
                  value={pregnancyOutcome}
                  onChange={(e) => {
                    const val = e.target.value;
                    setPregnancyOutcome(val);
                    if (val.toLowerCase() === 'stillbirth' || val.toLowerCase().includes('death')) {
                      setFetalNeonatalAssessments(prev => Array.from(new Set([...prev.filter(c => c !== 'NORMAL_OUTCOME'), 'PERINATAL_FETAL_DEATH'])));
                    }
                  }}
                  disabled={isSigned}
                >
                  <option value="Normal baby">Normal baby</option>
                  <option value="Preterm birth">Preterm birth</option>
                  <option value="Stillbirth">Stillbirth (Intrauterine / Fetal Death)</option>
                  <option value="Early neonatal death">Early neonatal death</option>
                  <option value="Ongoing pregnancy">Ongoing pregnancy</option>
                  <option value="Other">Other</option>
                </select>
                <small>Applies delivery-outcome precedence (Death &gt; Preterm &gt; Normal baby).</small>
              </div>
            </div>

            <label style={{ fontWeight: 700, display: 'block', marginBottom: '8px' }}>
              Closed-Ended Fetal and Neonatal Assessments (Select all that apply)
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '10px', marginBottom: '12px' }}>
              {VISIT5_ASSESSMENT_OPTIONS.map((opt) => {
                const isChecked = fetalNeonatalAssessments.includes(opt.code);
                const prov = fetalProvenance[opt.code];
                const provState = prov?.state;

                return (
                  <div
                    key={opt.code}
                    onClick={() => handleToggleAssessment(opt.code)}
                    style={{
                      border: isChecked ? '2px solid #0284c7' : '1px solid #cbd5e1',
                      background: isChecked ? '#f0f9ff' : '#ffffff',
                      borderRadius: '6px',
                      padding: '12px',
                      cursor: isSigned ? 'default' : 'pointer',
                      transition: 'all 0.15s ease',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '6px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleToggleAssessment(opt.code)}
                        disabled={isSigned}
                        style={{ marginTop: '3px', cursor: 'pointer' }}
                      />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: isChecked ? 700 : 600, fontSize: '13px', color: isChecked ? '#0369a1' : '#1e293b' }}>
                          {opt.label}
                        </div>
                        {opt.adverse && (
                          <span style={{ fontSize: '10.5px', color: '#b91c1c', fontWeight: 600 }}>
                            Adverse endpoint
                          </span>
                        )}
                      </div>
                    </div>

                    {prov && (
                      <div style={{
                        marginTop: '4px',
                        padding: '4px 8px',
                        background: provState === 'CONFIRMED_POSITIVE' ? '#dcfce7' : provState === 'CONFIRMED_NEGATIVE' ? '#f1f5f9' : '#fef3c7',
                        borderRadius: '4px',
                        fontSize: '11px',
                        color: provState === 'CONFIRMED_POSITIVE' ? '#166534' : provState === 'CONFIRMED_NEGATIVE' ? '#475569' : '#92400e',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <span>
                          {provState === 'CONFIRMED_POSITIVE' && '✓ Source Confirmed'}
                          {provState === 'CONFIRMED_NEGATIVE' && '— Source Confirmed Negative'}
                          {provState === 'NOT_ASSESSED_OR_MISSING' && '⚠ Not Assessed / Missing in CRF'}
                        </span>
                        {prov.provenance?.field && (
                          <span style={{ fontSize: '10px', opacity: 0.85 }}>
                            {prov.provenance.form ? `${prov.provenance.form} / ` : ''}{prov.provenance.field}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {visit5ValidationWarning && (
              <div role="alert" style={{
                background: '#fef2f2',
                border: '1px solid #f87171',
                borderRadius: '6px',
                padding: '10px 14px',
                color: '#991b1b',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginTop: '10px'
              }}>
                <AlertTriangle size={18} color="#dc2626" />
                <div>
                  <strong>Validation Rule Violation:</strong> {visit5ValidationWarning}
                </div>
              </div>
            )}
          </DropdownSection>
        )}
'''

target = '<div className="wizard-footer"'
if target in content:
    content = content.replace(target, v5_code + '\n        ' + target)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success")
else:
    print("Could not find insertion point")
