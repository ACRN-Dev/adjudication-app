
import sys
path = r'src\components\VisitEvidenceSections.jsx'
with open(path, encoding='utf-8') as f:
    content = f.read()

anchor = '// 1. Prioritize authentic Harvard attending clinical narrative for this visit if available'
start_idx = content.find(anchor)
if start_idx == -1:
    print('anchor not found'); sys.exit(1)

iife_open = content.rfind('{(() =>', 0, start_idx)
if iife_open == -1:
    print('iife open not found'); sys.exit(1)

end_idx = content.find('})()}', start_idx)
if end_idx == -1:
    print('end not found'); sys.exit(1)
end_idx += 5

old_block = content[iife_open:end_idx]
print('Found old block length:', len(old_block))
sys.exit(0)
