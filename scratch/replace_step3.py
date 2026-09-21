import sys

filepath = r'c:\Automation\Adjudication app\src\components\AdjudicatorWorkbench.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = '  // Approve clinical summary and sign'
if start_marker in content:
    start_idx = content.find(start_marker)
    
    new_code = '''  // Approve clinical summary and sign (Overall Flow)
  return (
    <div>
      <div className="wizard-card">
        <h2 className="wizard-title">Final Adjudication &amp; Sign Record ({activeCase.id})</h2>
        <p className="wizard-subtitle">Record your overall determination for this case and classify the onset per visit.</p>

        {/* Overall Determination */}
        <DropdownSection title="Overall Case Determination" icon={<ShieldCheck size={16} />} defaultOpen>
          <div className="summary-card-grid" style={{ marginBottom: '16px' }}>
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontWeight: 700, fontSize: '15px' }}>Does this participant meet criteria for pre-eclampsia?</label>
              <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                  <input type="radio" name="meetsCriteria" checked={meetsCriteria === true} onChange={() => { setMeetsCriteria(true); setSelectedDiagnosis('PE'); }} disabled={isSigned} /> Yes
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                  <input type="radio" name="meetsCriteria" checked={meetsCriteria === false} onChange={() => { setMeetsCriteria(false); setSelectedDiagnosis('Not PE'); }} disabled={isSigned} /> No
                </label>
              </div>
            </div>

            {meetsCriteria && (
              <>
                <div className="form-group">
                  <label style={{ fontWeight: 700 }}>Overall Classification</label>
                  <select className="form-select" value={selectedDiagnosis} onChange={(e) => setSelectedDiagnosis(e.target.value)} disabled={isSigned}>
                    <option value="PE">PE</option>
                    <option value="Severe PE">Severe PE</option>
                    <option value="Eclampsia">Eclampsia</option>
                    <option value="HELLP">HELLP</option>
                    {isReviewerC && <option value="Other">Other</option>}
                  </select>
                </div>
                
                <div className="form-group">
                  <label style={{ fontWeight: 700 }}>Overall Severity</label>
                  <select className="form-select" value={selectedSeverity} onChange={(e) => setSelectedSeverity(e.target.value)} disabled={isSigned}>
                    <option value="With severe features">With severe features</option>
                    <option value="Without severe features">Without severe features</option>
                    <option value="Eclampsia / severe SAE">Eclampsia / severe SAE</option>
                  </select>
                </div>
              </>
            )}
            
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontWeight: 700 }}>Differential Diagnosis / Alternative Explanation <span style={{color: 'red'}}>*</span></label>
              <input
                className="form-input"
                type="text"
                value={differentialDiagnosis}
                onChange={(e) => setDifferentialDiagnosis(e.target.value)}
                placeholder="Record important alternatives considered or why none applied"
                disabled={isSigned}
                required
              />
              <small>This field is mandatory.</small>
            </div>
          </div>
        </DropdownSection>

        {/* Per-visit Onset Grid */}
        {meetsCriteria && (
          <DropdownSection title="Per-Visit Onset Grid" icon={<Database size={16} />} defaultOpen>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '12px' }}>
              For each visit with evidence, indicate if pre-eclampsia criteria were met and the onset classification.
            </p>
            <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                <thead style={{ background: '#f8fafc', borderBottom: '1px solid var(--border-subtle)' }}>
                  <tr>
                    <th style={{ padding: '10px' }}>Visit</th>
                    <th style={{ padding: '10px' }}>Date</th>
                    <th style={{ padding: '10px' }}>PE Present?</th>
                    <th style={{ padding: '10px' }}>Onset Classification (if Yes)</th>
                  </tr>
                </thead>
                <tbody>
                  {evidenceVisits.map((v, i) => {
                    const dec = visitDecisions[v.id] || { meetsCriteria: false, onset: 'Onset not yet classifiable' };
                    return (
                      <tr key={v.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '10px', fontWeight: 600 }}>{v.name || v.visit_code || `Visit ${i+1}`}</td>
                        <td style={{ padding: '10px' }}>{new Date(v.date || v.visit_date).toLocaleDateString()}</td>
                        <td style={{ padding: '10px' }}>
                          <select 
                            className="form-select" 
                            style={{ padding: '4px', fontSize: '13px' }}
                            value={dec.meetsCriteria ? 'Yes' : 'No'}
                            onChange={e => {
                              const val = e.target.value === 'Yes';
                              setVisitDecisions(prev => ({...prev, [v.id]: {...(prev[v.id]||{}), meetsCriteria: val}}));
                            }}
                            disabled={isSigned}
                          >
                            <option value="No">No</option>
                            <option value="Yes">Yes</option>
                          </select>
                        </td>
                        <td style={{ padding: '10px' }}>
                          <select 
                            className="form-select" 
                            style={{ padding: '4px', fontSize: '13px' }}
                            value={dec.onset || 'Onset not yet classifiable'}
                            onChange={e => {
                               setVisitDecisions(prev => ({...prev, [v.id]: {...(prev[v.id]||{}), onset: e.target.value}}));
                            }}
                            disabled={!dec.meetsCriteria || isSigned}
                          >
                            <option value="Early-onset pre-eclampsia (EOPE)">Early-onset (EOPE) &lt; 34 weeks</option>
                            <option value="Late-onset pre-eclampsia (LOPE)">Late-onset (LOPE) ≥ 34 weeks</option>
                            <option value="Postpartum-only presentation">Postpartum-only presentation</option>
                            <option value="Onset not yet classifiable">Onset not yet classifiable</option>
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </DropdownSection>
        )}

        <div className="wizard-footer" style={{ marginTop: '24px' }}>
          <button className="btn-large btn-back" onClick={() => setCurrentStep(2)}>
            <ArrowLeft size={15} /> Back to Evidence
          </button>

          <button className="btn-large btn-next" onClick={() => {
            // Build per_visit_onset array
            const perVisitOnset = evidenceVisits.map(v => {
               const dec = visitDecisions[v.id] || { meetsCriteria: false, onset: null };
               return {
                  visit_number: v.visit_number || parseInt((v.visit_code || '').replace('V', '') || (v.name || '').replace('Visit ', '')) || 1,
                  meets_criteria: dec.meetsCriteria,
                  diagnosis: dec.meetsCriteria ? selectedDiagnosis : 'Not PE',
                  onset_class: dec.meetsCriteria ? (dec.onset || selectedOnset) : null
               };
            });

            onOpenSignature({
              is_overall_first: true,
              per_visit_onset: perVisitOnset,
              reviewerRole: activeCase?.reviewerRole || 'REVIEWER_A',
              reviewerName: user?.display_name || user?.name || user?.email,
              diagnosis: meetsCriteria ? selectedDiagnosis : 'Not PE',
              meetsCriteria,
              onset: selectedOnset, // default overall
              severity: selectedSeverity,
              certainty: selectedCertainty,
              rationale: "Overall case determination signature.", // placeholder
              differentialDiagnosis: differentialDiagnosis.trim() || null,
              visitNumber: 1, // backend will override this in the loop
              
              fetalNeonatalAssessments: fetalNeonatalAssessments,
              gestationalAgeAtDelivery: gestationalAgeAtDelivery !== '' ? Number(gestationalAgeAtDelivery) : null,
              pregnancyOutcome: pregnancyOutcome,
              fetalAssessmentStatus: fetalNeonatalAssessments?.length > 0 ? 'CONFIRMED' : null,
              fetalNeonatalProvenance: fetalProvenance
            });
          }} disabled={!differentialDiagnosis.trim()}>
            <ShieldCheck size={16} /> Sign &amp; Lock Adjudication Record
          </button>
        </div>
      </div>
    </div>
  );
}
'''
    content = content[:start_idx] + new_code
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success")
else:
    print("Could not find start marker")
