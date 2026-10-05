import os
import re

with open('src/components/AdjudicatorWorkbench.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add Baby to lucide-react imports
code = code.replace("AlertTriangle }", "AlertTriangle, Baby }")

# 2. Re-order the component body:
# Step 4 (Completed) should come FIRST before Step 2, and catch currentStep >= 2 if isSigned.
completed_start = code.find("  // Completed and signed record view")
completed_end = code.find("  // Approve clinical summary and sign (Overall Flow)")
completed_block = code[completed_start:completed_end]

# Modify completed block condition
completed_block = completed_block.replace(
    "if (currentStep === 4 || (currentStep === 3 && isSigned)) {",
    "if (currentStep === 4 || currentStep === 3 || (currentStep >= 2 && isSigned)) {"
)

# Extract Form Block (from start of form to the end)
form_start = code.find("  // Approve clinical summary and sign (Overall Flow)")
# the form ends exactly before `  return (` which is never, it is the bottom of the file!
# Wait, actually form block is the rest of the file until the final trailing }
form_block = code[form_start:]

# Remove completed and form from the main body
code = code[:completed_start]

# 3. Now `code` just contains up to the end of Step 2.
# We insert completed_block BEFORE Step 2.
step2_start = code.find("  // Review evidence and system derivation")
code = code[:step2_start] + completed_block + code[step2_start:]

# 4. Remove Step 2's `if (currentStep === 2) {` and `return (` wrappers so it just returns directly.
code = code.replace(
    '  if (currentStep === 2) {\n    return (\n      <div>\n        <div className="wizard-card">\n',
    '  return (\n      <div>\n        <div className="wizard-card">\n'
)

# 5. Remove Step 2's footer
step2_footer_regex = r'<div className="wizard-footer">.*?Approve Summary &amp; Sign.*?</div>'
code = re.sub(step2_footer_regex, '', code, flags=re.DOTALL)

# 6. Format the Form Block by removing `if (currentStep === 3)`
form_block = re.sub(r'  // Approve clinical summary and sign \(Overall Flow\).*?if \(currentStep === 3\) \{.*?return \(.*?<div>.*?<div className="wizard-card">', 
    '// Adjudication Form Section\n        <div style={{marginTop: "32px", borderTop: "2px solid #cbd5e1", paddingTop: "24px"}}>\n', 
    form_block, flags=re.DOTALL)

# Remove the final `</div>\n    </div>\n  );\n}\n` from Form Block, because we're inserting it inside Step 2
form_block = re.sub(r'</div>\s*</div>\s*\);\s*}\s*$', '</div>\n', form_block)

# 7. Remove duplicate fetal section inside Form Block
fetal_start = form_block.rfind('<DropdownSection title="Fetal &amp; Neonatal Outcomes"')
form_footer_start = form_block.find('<div className="wizard-footer"', fetal_start)
if fetal_start != -1 and form_footer_start != -1:
    # Find the start of the condition block {evidenceVisits...
    cond_start = form_block.rfind('{evidenceVisits.some', 0, fetal_start)
    if cond_start != -1:
        form_block = form_block[:cond_start] + form_block[form_footer_start:]

# 8. Fix Form Footer (Change "Back to Evidence" to "Back to Queue")
form_block = form_block.replace(
    '<button className="btn-large btn-back" onClick={() => setCurrentStep(2)}>',
    '<button className="btn-large btn-back" onClick={() => setCurrentStep(1)}>'
).replace('Back to Evidence', 'Back to Queue')

# 9. Insert the Form Block inside Step 2, right before `Visit Specific Evidence` Dropdown
checklist = """
          {/* Inclusion / Exclusion Criteria Checklist */}
          <div style={{
            background: '#e0f2fe',
            border: '1px solid #bae6fd',
            borderLeft: '4px solid #0ea5e9',
            borderRadius: 'var(--radius-sm)',
            padding: '12px 16px',
            marginBottom: '16px'
          }}>
            <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 8px 0', color: '#0369a1' }}>
              <CheckCircle2 size={16} />
              Inclusion & Exclusion Criteria Review
            </h4>
            <p style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#0c4a6e' }}>
              Please review the narrative and assess evidence against inclusion criteria (<a href="https://www.acog.org/clinical/clinical-guidance/practice-bulletin/articles/2020/06/gestational-hypertension-and-preeclampsia" target="_blank" rel="noreferrer" style={{color: '#0284c7', textDecoration: 'underline'}}>ACOG 2020 Guidelines</a>) at a 5th-grade reading level.
            </p>
            <div style={{ display: 'flex', gap: '16px', fontSize: '13px', color: '#0c4a6e' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input type="checkbox" disabled={isSigned} /> Participant meets all inclusion criteria
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input type="checkbox" disabled={isSigned} /> Participant meets NO exclusion criteria
              </label>
            </div>
          </div>
"""

insert_idx = code.find('<DropdownSection title="Visit Specific Evidence"')
code = code[:insert_idx] + checklist + form_block + '\n\n' + code[insert_idx:]

# Since we stripped the bottom `</div>\n    </div>\n  );\n}\n` from Form Block, but we still need it to close Step 2:
code += '\n      </div>\n    </div>\n  );\n}\n'

with open('src/components/AdjudicatorWorkbench.jsx', 'w', encoding='utf-8') as f:
    f.write(code)

print("Done")
