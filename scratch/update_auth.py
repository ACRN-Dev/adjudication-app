import sys

filepath = r'c:\Automation\Adjudication app\backend\services\auth_service.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add ROLE_OWNER
if 'ROLE_OWNER = "OWNER"' not in content:
    content = content.replace('ROLE_CHAIRPERSON = "CHAIRPERSON"', 'ROLE_CHAIRPERSON = "CHAIRPERSON"\nROLE_OWNER = "OWNER"')
    content = content.replace('ROLES = {ROLE_ADMIN, ROLE_MONITOR, ROLE_ADJUDICATOR, ROLE_CHAIRPERSON}', 'ROLES = {ROLE_ADMIN, ROLE_MONITOR, ROLE_ADJUDICATOR, ROLE_CHAIRPERSON, ROLE_OWNER}')
    
# 2. Update AuthIdentity.portal
if '"OWNER": "owner"' not in content:
    content = content.replace('{"ADMIN": "admin", "MONITOR": "monitor", "ADJUDICATOR": "adjudicator", "CHAIRPERSON": "chairperson"}', '{"ADMIN": "admin", "MONITOR": "monitor", "ADJUDICATOR": "adjudicator", "CHAIRPERSON": "chairperson", "OWNER": "owner"}')

# 3. Update DEMO_ACCOUNTS
if 'tariro@acrnhealth.com' not in content:
    demo_accounts_old = '''DEMO_ACCOUNTS = [
    ("admin@acrnhealth.com", "ACRN Demo Administrator", ROLE_ADMIN, "ADMIN"),
    ("chairperson@acrnhealth.com", "ACRN Demo Chairperson", ROLE_CHAIRPERSON, None),
    ("monitor1@acrnhealth.com", "ACRN Demo Monitor 1", ROLE_MONITOR, "MONITOR_QC_REVIEWER"),
    ("monitor2@acrnhealth.com", "ACRN Demo Monitor 2", ROLE_MONITOR, "QA_REVIEWER"),
    ("adjudicatora@acrnhealth.com", "ACRN Demo Adjudicator A", ROLE_ADJUDICATOR, None),
    ("adjudicatorb@acrnhealth.com", "ACRN Demo Adjudicator B", ROLE_ADJUDICATOR, None),
    ("adjudicatorc@acrnhealth.com", "ACRN Demo Adjudicator C", ROLE_ADJUDICATOR, None),
    ("adjudicatord@acrnhealth.com", "ACRN Demo Adjudicator D", ROLE_ADJUDICATOR, None),
]'''
    demo_accounts_new = '''DEMO_ACCOUNTS = [
    ("tariro@acrnhealth.com", "Tariro Makadzange", ROLE_OWNER, "OWNER"),
    ("it@acrnhealth.com", "IT Systems Admin", ROLE_ADMIN, "ADMIN"),
    ("admin@acrnhealth.com", "ACRN Demo Administrator", ROLE_ADMIN, "ADMIN"),
    ("chairperson@acrnhealth.com", "ACRN Demo Chairperson", ROLE_CHAIRPERSON, None),
    ("monitor1@acrnhealth.com", "ACRN Demo Monitor 1", ROLE_MONITOR, "MONITOR_QC_REVIEWER"),
    ("monitor2@acrnhealth.com", "ACRN Demo Monitor 2", ROLE_MONITOR, "QA_REVIEWER"),
    ("adjudicatora@acrnhealth.com", "ACRN Demo Adjudicator A", ROLE_ADJUDICATOR, None),
    ("adjudicatorb@acrnhealth.com", "ACRN Demo Adjudicator B", ROLE_ADJUDICATOR, None),
    ("adjudicatorc@acrnhealth.com", "ACRN Demo Adjudicator C", ROLE_ADJUDICATOR, None),
    ("adjudicatord@acrnhealth.com", "ACRN Demo Adjudicator D", ROLE_ADJUDICATOR, None),
]'''
    content = content.replace(demo_accounts_old, demo_accounts_new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Success modifying auth_service.py")
