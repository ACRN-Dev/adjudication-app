import re

with open('src/components/AdjudicatorWorkbench.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(r"\{\s*evidenceVisits\.some[^}]+\s*&&\s*\(\s*(<DropdownSection title=\"Fetal &amp; Neonatal Outcomes\".*?</DropdownSection>)\s*\)\s*\}", re.DOTALL)
match = pattern.search(content)

if match:
    block = match.group(1)
    # Remove it
    content = content[:match.start()] + content[match.end():]
    
    inject_target = r"{selectedVisitIndex===evidenceVisits.length ? <OverallSummary visits={evidenceVisits} /> : selectedEvidenceVisit && <VisitEvidencePanel visit={selectedEvidenceVisit} selectedIndex={selectedVisitIndex} visitCount={evidenceVisits.length} onSelectVisit={handleVisitSelect} />}"
    
    replacement = """{selectedVisitIndex===evidenceVisits.length ? <OverallSummary visits={evidenceVisits} /> : selectedEvidenceVisit && (
                <>
                  <VisitEvidencePanel visit={selectedEvidenceVisit} selectedIndex={selectedVisitIndex} visitCount={evidenceVisits.length} onSelectVisit={handleVisitSelect} />
                  
                  {(selectedEvidenceVisit.visit_number === 5 || selectedEvidenceVisit.visit_code === 'V05' || selectedEvidenceVisit.name?.includes('Visit 5')) && (
                    <div style={{ marginTop: '24px' }}>
                      <div style={{ 
                        background: '#f0f9ff', 
                        border: '1px solid #bae6fd', 
                        borderRadius: '6px', 
                        padding: '12px 16px', 
                        marginBottom: '16px', 
                        color: '#0369a1',
                        fontSize: '13.5px'
                      }}>
                        <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Info size={16} /> Please adjudicate Fetal & Neonatal Outcomes here based on the Visit 5 delivery CRF above.
                        </strong>
                      </div>
                      BLOCK_PLACEHOLDER
                    </div>
                  )}
                </>
              )}""".replace('BLOCK_PLACEHOLDER', block)
              
    new_content = content.replace(inject_target, replacement)
    
    with open('src/components/AdjudicatorWorkbench.jsx', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Success")
else:
    print("Not found")
