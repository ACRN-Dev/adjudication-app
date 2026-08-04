"""Streaming, chunk-committed RealTime batch pipeline."""
import base64, csv, hashlib, hmac, os, re
from collections import defaultdict
from datetime import datetime
from cryptography.fernet import Fernet
from database import SessionLocal
from models.longitudinal import RTImportBatch,LongitudinalParticipant,RestrictedIdentityCrosswalk,VisitInstance,CanonicalObservation,ImportIssue,LongitudinalAuditEvent
from services.realtime_mapping import classify,map_variable,source_value,parse_datetime,parse_numeric,parse_coded,visit_code,MAPPING_VERSION
from services.longitudinal_derivation import derive_participant

REQUIRED_HEADERS={"MRN","Screening #","Randomization #","Form Title","Form Version","Page Title","Field type","Field Label","Data Input","Data Value","Audit Trails","Export Variable Name"}
PSEUDO_SECRET=os.getenv("RT_PSEUDONYM_SECRET","acrn-demo-only-change-in-production").encode()
FERNET_KEY=os.getenv("RT_IDENTITY_ENCRYPTION_KEY")
# Stable demo fallback permits controlled crosswalk recovery after restart. Production
# must supply an independently managed key from the approved secret vault.
_fallback_key=base64.urlsafe_b64encode(hashlib.sha256(PSEUDO_SECRET+b"|identity").digest())
_fernet=Fernet(FERNET_KEY.encode() if FERNET_KEY else _fallback_key)

def checksum_file(path,chunk=1024*1024):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(chunk),b""): h.update(block)
    return h.hexdigest()
def pseudonym(mrn,screening): return "ACRN-"+hmac.new(PSEUDO_SECRET,f"{mrn}|{screening}".encode(),hashlib.sha256).hexdigest()[:12].upper()
def audit(db,actor,role,action,etype,eid,details=None):
    stamp=datetime.utcnow().isoformat(); safe=details or {}; digest=hashlib.sha256(f"{stamp}|{actor}|{action}|{eid}".encode()).hexdigest()
    db.add(LongitudinalAuditEvent(actor=actor,actor_role=role,action=action,entity_type=etype,entity_id=str(eid),safe_details=safe,record_hash=digest))

def process_batch(batch_id):
    db=SessionLocal(); batch=db.get(RTImportBatch,batch_id)
    try:
        if batch.status in {"MONITOR_QC_REQUIRED","PUBLISHED","SUPERSEDED"}:
            return
        batch.status="STRUCTURE_VALIDATION"; batch.processing_started_at=datetime.utcnow(); db.commit()
        with open(batch.source_path,encoding="utf-8-sig",errors="replace",newline="") as f:
            pos=0
            line=f.readline()
            while line and not {"MRN","Screening #"}.issubset(set(x.strip() for x in line.split(","))):
                pos=f.tell()
                line=f.readline()
            f.seek(pos)
            reader=csv.DictReader(f); missing=REQUIRED_HEADERS-set(reader.fieldnames or [])
            if missing: raise ValueError(f"Missing required headers: {sorted(missing)}")
            batch.validation_result={"passed":True,"headers":len(reader.fieldnames or [])}; batch.status="ROWS_STAGED"; db.commit()
            resume_at=batch.rows_processed or 0
            existing_participants=db.query(LongitudinalParticipant).filter_by(source_batch_id=batch.id).all()
            participants={p.blinded_subject_id:p for p in existing_participants}
            existing_visits=db.query(VisitInstance).filter_by(source_batch_id=batch.id).all()
            visits={(str(v.participant_id),v.form_title,v.visit_occurrence):v for v in existing_visits}
            form_occurrence=defaultdict(int); last_form={}; prohibited_labels=set()
            seen_fingerprints={x[0] for x in db.query(CanonicalObservation.source_fingerprint).filter_by(source_batch_id=batch.id).all()}
            total_rows=resume_at
            for row_no,row in enumerate(reader,2):
                total_rows=row_no-1
                if batch.cancel_requested: raise RuntimeError("IMPORT_CANCELLED")
                mrn=(row.get("MRN") or "").strip(); screening=(row.get("Screening #") or "").strip()
                if not mrn and not screening: batch.warning_count+=1; continue
                key=mrn or screening
                form=(row.get("Form Title") or "Unclassified").strip(); block=(key,form)
                if last_form.get(key)!=form: form_occurrence[block]+=1; last_form[key]=form
                occ=form_occurrence[block]
                if row_no-1<=resume_at: continue
                blind=pseudonym(mrn,screening)
                if blind not in participants:
                    p=LongitudinalParticipant(blinded_subject_id=blind,study="PROTECT-Africa",site_code=(screening.split("-")[0] if "-" in screening else None),source_batch_id=batch.id)
                    db.add(p); db.flush(); db.add(RestrictedIdentityCrosswalk(participant_id=p.id,protected_mrn=_fernet.encrypt(mrn.encode()).decode(),screening_number=_fernet.encrypt(screening.encode()).decode() if screening else None,restricted_randomisation_reference=_fernet.encrypt((row.get("Randomization #") or "").encode()).decode()))
                    participants[blind]=p; audit(db,batch.uploaded_by,"MONITOR_QC_REVIEWER","PSEUDONYM_CREATED","PARTICIPANT",p.id,{"blinded_subject_id":blind})
                p=participants[blind]; vkey=(str(p.id),form,occ)
                if vkey not in visits:
                    code,seq,vtype=visit_code(form); visits[vkey]=VisitInstance(participant_id=p.id,source_batch_id=batch.id,form_title=form,form_version=(row.get("Form Version") or "").strip(),scheduled_visit_code=code,visit_type=vtype,visit_occurrence=occ,visit_sequence=seq,reconstruction_method="FORM_BLOCK_SOURCE_ORDER",reconstruction_confidence="MEDIUM" if vtype in {"UNSCHEDULED","EVENT"} else "HIGH",qc_status="PENDING")
                    db.add(visits[vkey]); db.flush()
                visit=visits[vkey]; category=classify(row)
                if category=="PROHIBITED_BLINDED": batch.prohibited_count+=1; prohibited_labels.add(hashlib.sha256((row.get("Field Label") or "").encode()).hexdigest()[:12]); continue
                canonical=map_variable(row)
                if not canonical: continue
                value=source_value(row); fp=hashlib.sha256(f"{key}|{form}|{occ}|{canonical}|{value}|{row.get('Page Title')}|{row.get('Field Label')}".encode()).hexdigest()
                if fp in seen_fingerprints: continue
                seen_fingerprints.add(fp); dt=parse_datetime(value) if canonical.endswith("DATE") or "DATETIME" in canonical else None
                if canonical=="VISIT_DATE" and dt: visit.visit_datetime=dt
                obs=CanonicalObservation(participant_id=p.id,visit_id=visit.id,source_batch_id=batch.id,canonical_variable=canonical,raw_source_value=value,parsed_text_value=value or None,numeric_value=parse_numeric(value),datetime_value=dt,coded_value=parse_coded(value),observation_datetime=dt or visit.visit_datetime,date_confidence="EXACT" if dt else ("INFERRED" if visit.visit_datetime else "MISSING"),source_form=form,source_page=row.get("Page Title"),source_field_label=row.get("Field Label"),source_row_number=row_no,mapping_version=MAPPING_VERSION,quality_status="VALID" if value else "MISSING",provenance_type="SOURCE_RECORDED",prohibited_flag=False,source_fingerprint=fp)
                db.add(obs); batch.rows_processed=row_no-1
                if row_no%5000==0: db.commit()
            batch.rows_processed=total_rows
            batch.status="VISITS_RECONSTRUCTED"; db.commit()
        all_participants=db.query(LongitudinalParticipant).filter_by(source_batch_id=batch.id).all()
        for p in all_participants:
            pvis=db.query(VisitInstance).filter_by(participant_id=p.id,source_batch_id=batch.id).all(); dated=[v.visit_datetime for v in pvis if v.visit_datetime]
            p.available_visit_count=len(pvis); p.first_visit_date=min(dated) if dated else None; p.latest_visit_date=max(dated) if dated else None
            derive_participant(db,p,pvis); db.flush()
        batch.row_count=total_rows; batch.rows_processed=total_rows; batch.participant_count=len(all_participants); batch.visit_count=db.query(VisitInstance).filter_by(source_batch_id=batch.id).count()
        batch.blinding_result={"passed":True,"excluded_rows":batch.prohibited_count,"safe_field_fingerprints":sorted(prohibited_labels)}
        batch.status="MONITOR_QC_REQUIRED"; batch.error_count=0; batch.error_summary=None; batch.processing_finished_at=datetime.utcnow(); audit(db,batch.uploaded_by,"MONITOR_QC_REVIEWER","BATCH_PROCESSED","IMPORT_BATCH",batch.id,{"rows":batch.row_count,"participants":batch.participant_count,"visits":batch.visit_count,"prohibited_excluded":batch.prohibited_count}); db.commit()
    except Exception as exc:
        db.rollback(); batch=db.get(RTImportBatch,batch_id); batch.status="CANCELLED" if str(exc)=="IMPORT_CANCELLED" else "FAILED"; batch.error_count+=1; batch.error_summary=str(exc)[:1000]; batch.processing_finished_at=datetime.utcnow(); audit(db,batch.uploaded_by,"MONITOR_QC_REVIEWER","IMPORT_PROCESSING_FAILED","IMPORT_BATCH",batch.id,{"stage":batch.status,"error_type":type(exc).__name__},"FAILED"); db.commit()
    finally: db.close()
