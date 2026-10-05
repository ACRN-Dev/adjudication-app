import re

def remove_duplicates():
    with open('src/components/AdjudicatorWorkbench.jsx', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We are looking for: {evidenceVisits.some(v => v.visit_number === 5 || v.visit_code === 'V05' || v.name?.includes('Visit 5')) && (
    # followed by <DropdownSection title="Fetal &amp; Neonatal Outcomes" ... up to </DropdownSection>}
    
    pattern = re.compile(
        r"\{evidenceVisits\.some\([^)]+\)\s*&&\s*\(\s*<DropdownSection title=\"Fetal &amp; Neonatal Outcomes\".*?</DropdownSection>\s*\)\}",
        re.DOTALL
    )
    
    matches = list(pattern.finditer(content))
    print(f"Found {len(matches)} occurrences.")
    
    if len(matches) == 3:
        # Remove the first two occurrences (which are in Step 1 and Step 2)
        # Keep the last one which is in Step 3
        new_content = content[:matches[0].start()] + content[matches[0].end():matches[1].start()] + content[matches[1].end():]
        
        with open('src/components/AdjudicatorWorkbench.jsx', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Removed the first two occurrences successfully.")
    else:
        print("Expected 3 occurrences, got something else.")

remove_duplicates()
