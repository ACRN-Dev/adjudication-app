with open('src/components/AdjudicatorWorkbench.jsx', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines(keepends=True)
for i in range(len(lines)-1, -1, -1):
    if lines[i].strip() == 'return null;':
        lines[i] = '''  return (
    <div className="wizard-card">
      <h2 className="wizard-title">Participant Adjudication</h2>
      <p className="wizard-subtitle">Click below to return to the subject queue or resume reviewing.</p>
      <button className="btn-large btn-back" onClick={() => setCurrentStep(1)}>
        <ArrowLeft size={15} /> Return to Subject Queue
      </button>
    </div>
  );
'''
        break

with open('src/components/AdjudicatorWorkbench.jsx', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Updated safely')
