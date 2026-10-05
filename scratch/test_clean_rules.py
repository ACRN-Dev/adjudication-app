import sys, re
sys.path.insert(0, 'backend')
import services.realtime_mapping as rm

test_cases = [
    # (page, label, expected_canonical)
    ("Vital Signs/Weight Height", "Height", "height"),
    ("Vital Signs/Weight Height", "Weight", "weight"),
    ("Vital Signs/Weight Height", "BMI", "bmi"),
    ("Vital Signs/Weight Height", "Oxygen saturation", "o2_sat"),
    ("Vital Signs/Weight Height", "Heart rate", "heart_rate"),
    ("Vital Signs/Weight Height", "Pulse", "heart_rate"),
    ("Vital Signs/Weight Height", "Body temperature", "temperature"),
    ("Vital Signs/Weight Height", "Systolic blood pressure", "bp_systolic"),
    ("Vital Signs/Weight Height", "Diastolic blood pressure", "bp_diastolic"),
    ("Vital Signs/Weight Height", "Systolic blood pressure recheck", "bp_systolic_recheck"),
    ("Vital signs/ Weight", "Weight", "weight"),
    ("Vital signs/ Weight", "Heart rate", "heart_rate"),
    ("Vital signs/ Weight", "Systolic blood pressure", "bp_systolic"),
    ("Vital signs/ Weight", "Diastolic blood pressure", "bp_diastolic"),
    ("Pregnancy Assessment", "Current Gestational Age  (calculated using first USS)", "ega_weeks"),
    ("Pregnancy Assessment", "Current Gestational Age (claculated using first USS)", "ega_weeks"),
    ("Maternal Preeclampsia Assessment", "Elevated systolic blood pressure?", "pe_symptom_elevated_sbp"),
    ("Maternal Preeclampsia Assessment", "Elevated diastolic blood pressure?", "pe_symptom_elevated_dbp"),
    ("Maternal Preeclampsia Assessment", "Sudden weight gain (>1 kg/week in the third trimester)?", "pe_symptom_sudden_weight_gain"),
    ("Sonographic Data", "US Fetal Weight", "efw"),
    ("Sonographic Data", "Estimated US Fetal Weight", "efw"),
    ("Sonographic Data", "Fetal heart rate", "fetal_heart_rate"),
    ("Newborn Assessment Form", "Birth Weight", "newborn_weight_g"),
    ("Newborn Assessment Form", "Heart rate", "neonatal_heart_rate"),
    ("Newborn Assessment Form", "Heart", None),
    ("Newborn Assessment Form", "Heart Examination Description", None),
    ("Inclusion/Exclusion", "a. New onset of elevated BP (systolic BP ? 130mmHg or DBP ? 80)", None),
]

# Let's inspect how rules can be refined
print("Script ready for validation")
