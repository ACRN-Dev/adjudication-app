const fs = require('fs');
let code = fs.readFileSync('src/components/AdjudicatorWorkbench.jsx', 'utf8');

// 1. Move 'Completed and signed record view' to before 'Review evidence and system derivation'
const completedViewStart = code.indexOf('// Completed and signed record view');
const approveSummaryStart = code.indexOf('// Approve clinical summary and sign (Overall Flow)');

const completedViewCode = code.substring(completedViewStart, approveSummaryStart);
code = code.replace(completedViewCode, '');

// Update the condition for completed view
const updatedCompletedViewCode = completedViewCode.replace(
  'if (currentStep === 4 || (currentStep === 3 && isSigned)) {',
  'if (currentStep === 4 || currentStep === 3 || (currentStep === 2 && isSigned)) {'
);

const reviewEvidenceStart = code.indexOf('// Review evidence and system derivation');
code = code.substring(0, reviewEvidenceStart) + updatedCompletedViewCode + '\n' + code.substring(reviewEvidenceStart);

// 2. Remove 'if (currentStep === 2) { return (' and its closing tags, letting it fall through to the form.
code = code.replace(
  /\/\/ Review evidence and system derivation\s+if \(currentStep === 2\) \{\s+return \(\s+<div>\s+<div className="wizard-card">\s+/,
  '// Review evidence and system derivation\n  return (\n    <div>\n      <div className="wizard-card">\n        '
);

// 3. Remove the wizard-footer for step 2
const footerRegex = /<div className="wizard-footer"><div><\/div><button className="btn-large btn-next" onClick=\{[^}]+\} disabled=\{\!activeCase\}>Review Patient Evidence <ArrowRight size=\{16\}\/><\/button><\/div>\s*<\/div>\s*<\/div>\s*\);\s*\}/;
code = code.replace(footerRegex, '');

// 4. Remove the duplicate 'Approve clinical summary and sign' header since we are merging
const formHeaderRegex = /\/\/ Approve clinical summary and sign \(Overall Flow\)\s*return \(\s*<div>\s*<div className="wizard-card">\s*<h2 className="wizard-title">Final Adjudication &amp; Sign Record \(\{activeCase\.id\}\)<\/h2>\s*<p className="wizard-subtitle">Record your overall determination for this case and classify the onset per visit\.<\/p>/;

code = code.replace(formHeaderRegex,
  '<h2 className="wizard-title" style={{marginTop: \'24px\', borderTop: \'1px solid #cbd5e1\', paddingTop: \'24px\'}}>Final Adjudication &amp; Sign Record ({activeCase.id})</h2>\n<p className="wizard-subtitle">Record your overall determination for this case and classify the onset per visit.</p>'
);

// 5. Remove duplicate Fetal & Neonatal outcomes from the form
const fetalOutcomeStr = "{evidenceVisits.some(v => v.visit_number === 5 || v.visit_code === 'V05' || v.name?.includes('Visit 5')) && (";
const firstFetalIdx = code.indexOf(fetalOutcomeStr);
const secondFetalIdx = code.indexOf(fetalOutcomeStr, firstFetalIdx + 1);

if (secondFetalIdx > -1) {
  // Find the end of the second Fetal block. It ends right before <div className="wizard-footer" style={{ marginTop: '24px' }}>
  const endOfSecondFetal = code.indexOf('<div className="wizard-footer" style={{ marginTop: \'24px\' }}>', secondFetalIdx);
  if (endOfSecondFetal > -1) {
    code = code.substring(0, secondFetalIdx) + code.substring(endOfSecondFetal);
  }
}

// 6. Fix the 'Back to Evidence' button to just 'Back to Queue'
code = code.replace(
  '<button className="btn-large btn-back" onClick={() => setCurrentStep(2)}>',
  '<button className="btn-large btn-back" onClick={() => setCurrentStep(1)}>'
).replace('Back to Evidence', 'Back to Queue');

fs.writeFileSync('src/components/AdjudicatorWorkbench.jsx', code);
console.log('Refactoring complete');
