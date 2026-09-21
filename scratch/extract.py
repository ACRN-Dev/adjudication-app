import subprocess
result = subprocess.run(['git', 'show', 'HEAD:src/components/AdjudicatorWorkbench.jsx'], capture_output=True, text=True)
content = result.stdout
start_idx = content.find('<DropdownSection title="Fetal')
if start_idx != -1:
    end_idx = content.find('</DropdownSection>', start_idx) + 18
    print(content[start_idx:end_idx])
else:
    print('Not found')
