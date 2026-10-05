import os
import glob

# Search for any data files (.csv, .xlsx, .json, .txt, .pdf) in workspace
matches = []
for root, dirs, files in os.walk("."):
    if any(ign in root for ign in [".git", "node_modules", "dist", ".gemini", "brain"]):
        continue
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in [".csv", ".xlsx", ".xls", ".json", ".txt"]:
            matches.append(os.path.join(root, f))

print("Found files:")
for m in matches:
    print(m)
