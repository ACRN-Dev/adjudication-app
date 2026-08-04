"""Streaming RealTime long-form classification with no clinical-outcome leakage."""
import csv, hashlib, re
from dataclasses import dataclass
from services.clinical_import_policy import is_recorded_pe_outcome

DIRECT_IDENTIFIER_COLUMNS={"MRN","Screening #","Randomization #"}
BIOMARKER=re.compile(r"sflt|plgf|pigf|seng|soluble endoglin|biomarker|angiogenic|poc result|point.of.care",re.I)
ALLOCATION=re.compile(r"treatment allocation|randomisation assignment|randomization assignment|study arm",re.I)

def blinded_subject_id(source_id,study="MUTALA",secret="demo-pseudonymisation-key"):
    digest=hashlib.sha256(f"{secret}|{study}|{source_id}".encode()).hexdigest()[:12].upper()
    return f"{study[:3].upper()}-{digest}"

def classify_row(row):
    labels=[row.get("Form Title",""),row.get("Page Title",""),row.get("Field Label",""),row.get("Export Variable Name","")]
    text=" | ".join(labels)
    if BIOMARKER.search(text) or ALLOCATION.search(text): return "PROHIBITED_BLINDED"
    if is_recorded_pe_outcome(*labels): return "RESTRICTED_RECORDED_OUTCOME"
    if row.get("Field type")=="electronic_signature": return "RESTRICTED_OPERATIONAL_METADATA"
    return "PERMITTED_CLINICAL_EVIDENCE"

@dataclass
class StreamStats:
    rows:int=0; permitted:int=0; restricted_outcomes:int=0; restricted_operational:int=0; prohibited:int=0

def stream_classified_rows(path,chunk_size=5000):
    """Yield bounded chunks; never loads the full 186 MB export into memory."""
    chunk=[]; stats=StreamStats()
    with open(path,encoding="utf-8-sig",newline="",errors="replace") as handle:
        for number,row in enumerate(csv.DictReader(handle),start=2):
            category=classify_row(row); stats.rows+=1
            if category=="PERMITTED_CLINICAL_EVIDENCE": stats.permitted+=1
            elif category=="RESTRICTED_RECORDED_OUTCOME": stats.restricted_outcomes+=1
            elif category=="RESTRICTED_OPERATIONAL_METADATA": stats.restricted_operational+=1
            else: stats.prohibited+=1
            # Raw MRN is used only to form a pseudonymous reference and is not yielded.
            safe={k:v for k,v in row.items() if k not in DIRECT_IDENTIFIER_COLUMNS and k!="Audit Trails"}
            safe.update({"source_row_number":number,"subject_ref":blinded_subject_id(row.get("MRN") or row.get("Screening #") or "UNKNOWN","MUTALA"),"classification":category})
            chunk.append(safe)
            if len(chunk)>=chunk_size: yield chunk,stats; chunk=[]
    if chunk: yield chunk,stats

def adjudicator_evidence(row):
    """Only explicitly permitted rows can cross into adjudicator evidence."""
    return row if row.get("classification")=="PERMITTED_CLINICAL_EVIDENCE" else None
