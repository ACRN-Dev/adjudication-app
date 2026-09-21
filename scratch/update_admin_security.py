import sys

filepath = r'c:\Automation\Adjudication app\backend\services\admin_security.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add OWNER to ROLE_PERMISSIONS
if '"OWNER":' not in content:
    owner_perms = '"OWNER": {"admin.read", "users.read", "users.manage", "roles.read", "studies.manage", "studies.read", "sites.manage", "rules.manage", "rules.read", "rules.approve", "mappings.manage", "mappings.approve", "forms.manage", "forms.approve", "workflows.manage", "integrations.manage", "audit.read", "reports.read", "access.approve", "access.review", "finance.read", "finance.manage"},'
    content = content.replace('"ADMIN": {', f'{owner_perms}\n    "ADMIN": {{')

# Update get_identity to allow OWNER role
if 'user.role not in ("ADMIN", "OWNER")' not in content:
    content = content.replace('if user.role != "ADMIN" or user.portal_role not in ADMIN_ROLES:', 'if user.role not in ("ADMIN", "OWNER") or user.portal_role not in ADMIN_ROLES:')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated admin_security.py")
