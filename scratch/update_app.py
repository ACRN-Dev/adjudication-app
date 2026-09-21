import sys

filepath = r'c:\Automation\Adjudication app\src\App.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Import OwnerPortal
if 'import OwnerPortal' not in content:
    content = content.replace('import ChairpersonPortal from \'./chairperson/ChairpersonPortal\';', 'import ChairpersonPortal from \'./chairperson/ChairpersonPortal\';\nimport OwnerPortal from \'./owner/OwnerPortal\';')

# Add routing target for Owner
if 'userData.portal === \'owner\'' not in content:
    content = content.replace('if (userData.portal === \'admin\') target = \'/admin\';', 'if (userData.portal === \'owner\') target = \'/owner\';\n    else if (userData.portal === \'admin\') target = \'/admin\';')
    
# Add path prefix handling for /owner
if 'window.location.pathname.startsWith(\'/owner\')' not in content:
    content = content.replace('window.location.pathname.startsWith(\'/admin\')', 'window.location.pathname.startsWith(\'/owner\') || window.location.pathname.startsWith(\'/admin\')')

# Update adminRoles
if 'OWNER' not in content and 'adminRoles = [' in content:
    content = content.replace('const adminRoles = [\'ADMIN\', \'TECHNICAL_ADMIN\', \'CLINICAL_OPS_ADMIN\', \'QA_AUDITOR\', \'GOVERNANCE_REVIEWER\', \'ACCESS_REVIEWER\'];', 'const adminRoles = [\'ADMIN\', \'TECHNICAL_ADMIN\', \'CLINICAL_OPS_ADMIN\', \'QA_AUDITOR\', \'GOVERNANCE_REVIEWER\', \'ACCESS_REVIEWER\', \'OWNER\'];')

# Update monitorRoles
if 'const monitorRoles=[' in content:
    content = content.replace('const monitorRoles=[\'MONITOR\',\'ADMIN\',\'CHAIRPERSON\',\'ADJUDICATION_COORDINATOR\',\'MONITOR_QC_REVIEWER\',\'QA_REVIEWER\',\'RELEASE_OPERATOR\'];', 'const monitorRoles=[\'MONITOR\',\'ADMIN\',\'CHAIRPERSON\',\'ADJUDICATION_COORDINATOR\',\'MONITOR_QC_REVIEWER\',\'QA_REVIEWER\',\'RELEASE_OPERATOR\',\'OWNER\'];')

# Add Chairperson check for OWNER
if 'user?.roleCode === \'OWNER\'' not in content and 'user?.roleCode === \'CHAIRPERSON\'' in content:
    content = content.replace('user?.roleCode === \'CHAIRPERSON\' || user?.portal === \'chairperson\'', 'user?.roleCode === \'CHAIRPERSON\' || user?.portal === \'chairperson\' || user?.roleCode === \'OWNER\'')

# Add Adjudicator workbench route for OWNER
# Currently it says:
# if (!isAuthenticated || user?.must_change_password || user?.portal !== 'adjudicator') return;
# But actually the adjudicator block in App.jsx must allow 'owner'
if 'user?.portal !== \'adjudicator\' && user?.portal !== \'owner\'' not in content:
    content = content.replace('user?.portal !== \'adjudicator\'', 'user?.portal !== \'adjudicator\' && user?.portal !== \'owner\'')

# Add /owner route rendering
if '<OwnerPortal user={user} onLogout={handleLogout} />' not in content:
    owner_route = '''      if (currentPath.startsWith('/owner') || user?.roleCode === 'OWNER' || user?.portal === 'owner') {
        return <OwnerPortal user={user} onLogout={handleLogout} />;
      }
      if (currentPath.startsWith('/admin')) {'''
    content = content.replace('if (currentPath.startsWith(\'/admin\')) {', owner_route)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated App.jsx routing and RBAC")
