import sys

filepath = r'c:\Automation\Adjudication app\src\components\VisitEvidenceSections.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''          return (
            <button
              key={visit.id || `${visitLabel(visit, index)}-${index}`}
              type="button"
              className={`visit-ribbon-tab ${selectedIndex === index ? 'active' : ''} ${completeVisit ? 'complete' : reviewerSigned ? 'signed' : ''}`}
              aria-current={selectedIndex === index ? 'step' : undefined}
              onClick={() => onSelectVisit?.(index)}
            >'''

if target in content:
    replacement = '''          const isPostDelivery = visit.visit_number >= 5 || parseInt((visit.visit_code || '').replace('V', '') || '0') >= 5;
          const bgStyle = isPostDelivery ? { borderBottom: '3px solid #8b5cf6', background: selectedIndex === index ? '#f5f3ff' : undefined } : {};
          return (
            <button
              key={visit.id || `${visitLabel(visit, index)}-${index}`}
              type="button"
              className={`visit-ribbon-tab ${selectedIndex === index ? 'active' : ''} ${completeVisit ? 'complete' : reviewerSigned ? 'signed' : ''}`}
              style={bgStyle}
              aria-current={selectedIndex === index ? 'step' : undefined}
              onClick={() => onSelectVisit?.(index)}
            >'''
    content = content.replace(target, replacement)
    
    # Also update LongitudinalEvidenceTable to color headers for Visit 5+
    target2 = '''            {expectedVisits.map((v, i) => (
              <th 
                key={v.id || i}
                className={i === selectedIndex ? 'active' : ''}
                onClick={() => onSelectVisit?.(i)}
              >'''
    if target2 in content:
        replacement2 = '''            {expectedVisits.map((v, i) => {
              const isPostDelivery = v.visit_number >= 5 || parseInt((v.visit_code || '').replace('V', '') || '0') >= 5;
              const thStyle = isPostDelivery ? { borderTop: '3px solid #8b5cf6', background: i === selectedIndex ? '#f5f3ff' : undefined } : {};
              return (
              <th 
                key={v.id || i}
                className={i === selectedIndex ? 'active' : ''}
                style={thStyle}
                onClick={() => onSelectVisit?.(i)}
              >'''
        content = content.replace(target2, replacement2).replace('              </th>\n            ))}','              </th>\n            ); })}')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success coloring post-delivery visits")
else:
    print("Could not find target in VisitEvidenceSections.jsx")
