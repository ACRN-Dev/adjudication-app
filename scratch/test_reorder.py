import sys
sys.path.insert(0, 'backend')
from services.realtime_mapping import map_variable

row_26 = {
    "Form Title": "Visit 2",
    "Page Title": "Pregnancy Assessment",
    "Field Label": "Current Gestational Age  (calculated using first USS)",
    "Export Variable Name": "",
    "Data Value": "26"
}
row_2 = {
    "Form Title": "Visit 2",
    "Page Title": "Pregnancy Assessment",
    "Field Label": "Current Gestational Age  (calculated using first USS)",
    "Export Variable Name": "",
    "Data Value": "2"
}
row_wt = {
    "Form Title": "Visit 2",
    "Page Title": "Vital Signs/Weight Height",
    "Field Label": "Weight",
    "Export Variable Name": "",
    "Data Value": "60"
}
row_hr = {
    "Form Title": "Visit 2",
    "Page Title": "Vital Signs/Weight Height",
    "Field Label": "Heart rate",
    "Export Variable Name": "",
    "Data Value": "82"
}
print("Row 26 mapped:", map_variable(row_26))
print("Row 2 mapped:", map_variable(row_2))
print("Row wt mapped:", map_variable(row_wt))
print("Row hr mapped:", map_variable(row_hr))
