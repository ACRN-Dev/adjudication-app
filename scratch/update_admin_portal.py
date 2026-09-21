import sys

filepath = r'c:\Automation\Adjudication app\src\admin\AdminPortal.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Create User dropdown
if '<option value="OWNER">Owner</option>' not in content:
    content = content.replace(
        '<option value="ADMIN">Admin</option>\n</select>',
        '<option value="ADMIN">Admin</option>\n<option value="OWNER">Owner</option>\n</select>'
    )
    
# 2. Update Filter dropdown
if '<option value="OWNER">Owner</option>' not in content:
    content = content.replace(
        '<option value="CHAIRPERSON">Chairperson</option>\n</select>',
        '<option value="CHAIRPERSON">Chairperson</option>\n<option value="OWNER">Owner</option>\n</select>'
    )
    
# 3. Update User Table role change dropdown
if '<option value="OWNER">Owner</option>' not in content:
    content = content.replace(
        '<option value="CHAIRPERSON">Chairperson</option>\n</select>',
        '<option value="CHAIRPERSON">Chairperson</option>\n<option value="OWNER">Owner</option>\n</select>'
    )

# 4. Update the Portal permission matrix table
if "['Capability','Owner','Technical Admin'" not in content:
    old_table = "columns={['Capability','Technical Admin','Clinical Ops','QA/Auditor','Governance','Access Reviewer']} rows={[[\"Admin Portal\",\"Manage\",\"Manage\",\"Read/approve\",\"Read\",\"Review\"],[\"Blinded case content\",\"Denied\",\"Denied\",\"Denied\",\"Denied\",\"Denied\"],[\"User administration\",\"Manage\",\"Read\",\"Read\",\"Read\",\"Review\"],[\"Rules / mappings / forms\",\"Read\",\"Draft/manage\",\"Approve\",\"Read\",\"None\"],[\"Clinical decisions\",\"Denied\",\"Denied\",\"Denied\",\"Denied\",\"Denied\"]]}"
    
    new_table = "columns={['Capability','Owner','Technical Admin','Clinical Ops','QA/Auditor','Governance','Access Reviewer']} rows={[[\"Admin Portal\",\"Manage\",\"Manage\",\"Manage\",\"Read/approve\",\"Read\",\"Review\"],[\"Blinded case content\",\"View all\",\"Denied\",\"Denied\",\"Denied\",\"Denied\",\"Denied\"],[\"User administration\",\"Manage\",\"Manage\",\"Read\",\"Read\",\"Read\",\"Review\"],[\"Rules / mappings / forms\",\"Manage\",\"Read\",\"Draft/manage\",\"Approve\",\"Read\",\"None\"],[\"Clinical decisions\",\"Monitor\",\"Denied\",\"Denied\",\"Denied\",\"Denied\",\"Denied\"]]}"
    
    content = content.replace(old_table, new_table)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated AdminPortal.jsx")
