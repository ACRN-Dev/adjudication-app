import json
import glob
import os

brain_dir = r"C:\Users\TinotendaChibongore\.gemini\antigravity-ide\brain"
transcripts = sorted(glob.glob(os.path.join(brain_dir, "*", ".system_generated", "logs", "transcript.jsonl")), key=os.path.getmtime, reverse=True)

target = r"C:\Users\TinotendaChibongore\.gemini\antigravity-ide\brain\b231abc4-7b57-4aa9-ad6a-cea241f2a879\.system_generated\logs\transcript.jsonl"
if os.path.exists(target):
    print("=== TARGET EXISTS ===")
    with open(target, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if '"type":"USER_INPUT"' in line:
                data = json.loads(line)
                content = data.get('content', '')
                clean = content.encode('ascii', errors='replace').decode('ascii')
                print(f"[STEP {data.get('step_index')}] {clean}")
                print("="*40)
else:
    print("TARGET DOES NOT EXIST")
