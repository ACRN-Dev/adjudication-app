with open("backend/services/lab_reference.py", "rb") as f:
    content = f.read().replace(b"\r\n", b"\n")

old_default = b'''    "BUN":              {"low": 7.0, "high": 20.0, "unit": "mg/dL"},
    "BILIRUBIN":        {"low": 0.1, "high": 1.2, "unit": "mg/dL"},
}'''

new_default = b'''    "BUN":              {"low": 7.0, "high": 20.0, "unit": "mg/dL"},
    "BILIRUBIN":        {"low": 0.1, "high": 1.2, "unit": "mg/dL"},
    "ALC":              {"low": 1.0, "high": 3.5, "unit": "10^9/L"},
    "ANC":              {"low": 2.0, "high": 7.5, "unit": "10^9/L"},
}'''

assert old_default in content, "old_default not found"
content = content.replace(old_default, new_default, 1)

old_aliases = b'''    "total_bilirubin": "BILIRUBIN",
    "bun": "BUN",
}'''

new_aliases = b'''    "total_bilirubin": "BILIRUBIN",
    "bun": "BUN",
    "alc": "ALC",
    "absolute_lymphocyte_count": "ALC",
    "absolute_lymphocytes_count": "ALC",
    "anc": "ANC",
    "absolute_neutrophil_count": "ANC",
    "absolute_neutrophils_count": "ANC",
    "hematocrit": "HEMATOCRIT",
}'''

assert old_aliases in content, "old_aliases not found"
content = content.replace(old_aliases, new_aliases, 1)

with open("backend/services/lab_reference.py", "wb") as f:
    f.write(content)

print("Successfully updated backend/services/lab_reference.py")
