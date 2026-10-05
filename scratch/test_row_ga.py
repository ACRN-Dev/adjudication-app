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
print("Row 26 mapped:", map_variable(row_26))
print("Row 2 mapped:", map_variable(row_2))
