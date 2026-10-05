"""Streaming, chunk-committed RealTime batch pipeline."""
import base64, csv, hashlib, hmac, os, re, uuid
from collections import defaultdict
from datetime import datetime
from cryptography.fernet import Fernet
from database import SessionLocal
from models.history import PatientHistory, PatientHistoryField, PatientRiskSummary
from models.longitudinal import RTImportBatch,LongitudinalParticipant,RestrictedIdentityCrosswalk,VisitInstance,CanonicalObservation,ImportIssue,LongitudinalAuditEvent,LongitudinalCaseDerivation
from services.realtime_mapping import classify,map_variable,source_value,parse_datetime,parse_numeric,parse_coded,visit_code,MAPPING_VERSION,is_clinical_candidate
from services.longitudinal_derivation import derive_participant
from services.history_parser import is_history_form, process_history_row, finalize_history
from services.import_readiness import participant_import_readiness
from services.edc_mapping import is_edc_schema, is_clinical_one_schema, normalize_edc_rows, normalize_clinical_one_rows
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
def audit(db,actor,role,action,etype,eid,details=None,outcome="SUCCESS"):
    stamp=datetime.utcnow().isoformat(); safe=details or {}; digest=hashlib.sha256(f"{stamp}|{actor}|{action}|{eid}".encode()).hexdigest()
    db.add(LongitudinalAuditEvent(actor=actor,actor_role=role,action=action,entity_type=etype,entity_id=str(eid),safe_details=safe,record_hash=digest))

def process_batch(batch_id, reset=False):
    if isinstance(batch_id, str):
        try:
            batch_id = uuid.UUID(batch_id)
        except Exception:
            pass
    db=SessionLocal(); batch=db.get(RTImportBatch,batch_id)
    if not batch:
        db.close()
        return
    try:
        if batch.status in {"AUTO_QC_COMPLETE","MONITOR_QC_REQUIRED","PUBLISHED","SUPERSEDED"}:
            return
        if reset or batch.status == "FAILED":
            db.query(CanonicalObservation).filter_by(source_batch_id=batch.id).delete()
            db.query(VisitInstance).filter_by(source_batch_id=batch.id).delete()
            db.query(PatientHistoryField).filter_by(source_batch_id=batch.id).delete()
            p_ids = [p[0] for p in db.query(LongitudinalParticipant.id).filter_by(source_batch_id=batch.id).all()]
            if p_ids:
                db.query(RestrictedIdentityCrosswalk).filter(RestrictedIdentityCrosswalk.participant_id.in_(p_ids)).delete(synchronize_session=False)
                db.query(PatientRiskSummary).filter(PatientRiskSummary.participant_id.in_(p_ids)).delete(synchronize_session=False)
                db.query(PatientHistory).filter(PatientHistory.participant_id.in_(p_ids)).delete(synchronize_session=False)
                db.query(LongitudinalCaseDerivation).filter(LongitudinalCaseDerivation.participant_id.in_(p_ids)).delete(synchronize_session=False)
                db.query(LongitudinalParticipant).filter(LongitudinalParticipant.id.in_(p_ids)).delete(synchronize_session=False)
            batch.rows_processed = 0
            batch.prohibited_count = 0
            batch.warning_count = 0
            batch.error_count = 0
            batch.error_summary = None
            db.commit()
        batch.status="STRUCTURE_VALIDATION"; batch.processing_started_at=datetime.utcnow(); db.commit()
        batch.mapping_version=MAPPING_VERSION
        with open(batch.source_path,encoding="utf-8-sig",errors="replace",newline="") as f:
            pos=0
            line=f.readline()
            header_pos=0
            found=False
            while line:
                try:
                    row=next(csv.reader([line]))
                    cleaned={x.strip().strip('"\'') for x in row if x}
                    is_rt_hdr = {"MRN","Screening #"}.issubset(cleaned) or ({"MRN"}.issubset(cleaned) and {"Form Title"}.issubset(cleaned))
                    is_c1_hdr = ({"Subject ID", "Screening Number"}.issubset(cleaned) or
                                 {"Subject Number", "Visit/Event Title"}.issubset(cleaned) or
                                 ({"Question Label", "Value"}.issubset(cleaned) and {"Form Title"}.issubset(cleaned)))
                    if is_rt_hdr or is_c1_hdr:
                        header_pos=pos
                        found=True
                        break
                except Exception:
                    pass
                pos=f.tell()
                line=f.readline()
            if not found:
                raise ValueError(
                    f"No RealTime or EDC header row found in '{batch.filename}'. This usually means the "
                    "file was split from a larger export and only the first chunk kept the header row — "
                    "re-export the full file, or repeat the header row at the top of every split file, "
                    "then re-upload."
                )
            f.seek(header_pos)
            reader=csv.DictReader(f)
            fieldnames_clean={x.strip() for x in (reader.fieldnames or [])}
            is_c1 = is_clinical_one_schema(reader.fieldnames)
            edc_schema = is_edc_schema(reader.fieldnames)
            missing={"MRN","Screening #","Form Title","Field Label"}-fieldnames_clean
            if missing and not edc_schema and not is_c1 and not ({"MRN","Form Title"}.issubset(fieldnames_clean)):
                raise ValueError(f"Missing required headers: {sorted(missing)}")
            if is_c1:
                reader = normalize_clinical_one_rows(reader)
                batch.source_system="EDC_CLINICAL_ONE"; batch.mapping_version="CLINICAL-ONE-1.0"
            elif edc_schema:
                reader = normalize_edc_rows(reader)
                batch.source_system="EDC"; batch.mapping_version="EDC-MAP-1.0"
            schema_name = "EDC_CLINICAL_ONE" if is_c1 else ("EDC_WIDE" if edc_schema else "REALTIME_LONG")
            batch.validation_result={"passed":True,"schema":schema_name,"headers":len(fieldnames_clean)}; batch.status="ROWS_STAGED"; db.commit()
            resume_at=batch.rows_processed or 0
            existing_participants=db.query(LongitudinalParticipant).filter_by(source_batch_id=batch.id).all()
            participants={p.blinded_subject_id:p for p in existing_participants}
            existing_visits=db.query(VisitInstance).filter_by(source_batch_id=batch.id).all()
            visits={(str(v.participant_id),v.form_title,v.visit_occurrence):v for v in existing_visits}
            form_occurrence=defaultdict(int); last_form={}; prohibited_labels=set()
            seen_fingerprints={x[0] for x in db.query(CanonicalObservation.source_fingerprint).filter_by(source_batch_id=batch.id).all()}
            history_fields={(f.participant_id, f.domain, f.field_key, f.instance_index): f for f in db.query(PatientHistoryField).filter_by(source_batch_id=batch.id).all()}
            patient_histories={(ph.participant_id, ph.source_form): ph for ph in db.query(PatientHistory).filter_by(source_file=batch.filename).all()}
            total_rows=resume_at
            reconciliation=defaultdict(int)
            for row_no,row in enumerate(reader,2):
                total_rows=row_no-1
                if batch.cancel_requested: raise RuntimeError("IMPORT_CANCELLED")
                reconciliation["source_rows_received"] += 1
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
                # Wide-format column headers (EDC/ClinicalOne); also catches common label variants
                age_str = (row.get("Age") or row.get("age") or row.get("Patient Age") or row.get("Age (years)") or row.get("Age (yrs)") or row.get("AGE") or row.get("Age at Enrollment") or row.get("Age at Enrollment (yrs)") or row.get("Current Age") or "").strip()
                # Long-format RealTime rows: Field Label="Age (years)", Data Value="28"
                if not age_str:
                    _age_canonical = map_variable(row)
                    if _age_canonical == "age":
                        age_str = source_value(row)
                if age_str and (p.id, "baseline", "age", None) not in history_fields:
                    age_field = PatientHistoryField(
                        participant_id=p.id, subject_id=p.blinded_subject_id, domain="baseline",
                        field_key="age", field_label_raw="Age", field_type="numeric",
                        value=age_str, source_batch_id=batch.id
                    )
                    db.add(age_field)
                    history_fields[(p.id, "baseline", "age", None)] = age_field
                if vkey not in visits:
                    code,seq,vtype=visit_code(form); visits[vkey]=VisitInstance(participant_id=p.id,source_batch_id=batch.id,form_title=form,form_version=(row.get("Form Version") or "").strip(),scheduled_visit_code=code,visit_type=vtype,visit_occurrence=occ,visit_sequence=seq,reconstruction_method="FORM_BLOCK_SOURCE_ORDER",reconstruction_confidence="MEDIUM" if vtype in {"UNSCHEDULED","EVENT"} else "HIGH",qc_status="PENDING")
                    db.add(visits[vkey]); db.flush()
                visit=visits[vkey]; category=classify(row)
                if row.get("_EDC_MISSING_VISIT_KEY"):
                    visit.qc_status="EXCLUDED_MISSING_KEY_FIELDS"
                value = source_value(row)
                if value and value.strip():
                    reconciliation["populated_source_rows"] += 1
                if is_clinical_candidate(row):
                    reconciliation["clinical_candidate_rows"] += 1
                if category=="PROHIBITED_BLINDED":
                    reconciliation["prohibited_blinded_rows"] += 1
                    batch.prohibited_count+=1; prohibited_labels.add(hashlib.sha256((row.get("Field Label") or "").encode()).hexdigest()[:12]); continue
                if category=="DIRECT_IDENTIFIER":
                    reconciliation["restricted_identifier_rows"] += 1
                    batch.warning_count += 1
                    continue
                if category in {"RESTRICTED_OPERATIONAL_METADATA", "CLINICAL_COLLECTION_STATUS", "CLINICAL_RESULT_INTERPRETATION", "RESTRICTED_RECORDED_OUTCOME"}:
                    reconciliation["operational_or_context_rows_excluded"] += 1
                canonical=map_variable(row)
                if is_history_form(form): process_history_row(db, batch, p, row, row_no, history_fields=history_fields, patient_histories=patient_histories)
                if not canonical:
                    if value and value.strip() and is_clinical_candidate(row) and category == "UNMAPPED":
                        reconciliation["unmapped_clinically_relevant_rows"] += 1
                        db.add(ImportIssue(
                            batch_id=batch.id,
                            participant_id=p.id,
                            visit_id=visit.id,
                            source_row=row_no,
                            issue_type="UNMAPPED_CLINICAL_FIELD",
                            severity="WARNING",
                            description=f"Populated clinical candidate was not mapped: {form} / {row.get('Page Title')} / {row.get('Field Label')}",
                        ))
                    continue
                if not value or not value.strip():
                    continue
                fp = hashlib.sha256(f"{key}|{form}|{occ}|{canonical}|{value}|{row.get('Page Title')}|{row.get('Field Label')}".encode()).hexdigest()
                if fp in seen_fingerprints:
                    reconciliation["duplicate_or_superseded_rows"] += 1
                    continue
                canonical_lower = str(canonical or "").lower()
                seen_fingerprints.add(fp); dt=parse_datetime(value) if canonical_lower.endswith("date") or canonical_lower.endswith("datetime") else None
                if canonical in {"VISIT_DATE", "visit_date"} and dt:
                    if visit.visit_datetime is None:
                        visit.visit_datetime=dt
                    elif visit.visit_datetime != dt:
                        visit.qc_status="MONITOR_QC_REQUIRED"
                        reconciliation["conflicting_rows"] += 1
                if canonical in {"ega_weeks", "GA_WEEKS", "ega_delivery", "GA_AT_DELIVERY"} and parse_numeric(value) is not None:
                    val = parse_numeric(value)
                    if val >= 10:
                        curr_days = (visit.gestational_age_days or 0) % 7
                        visit.gestational_age_days = round(val * 7) + curr_days
                    elif val < 7 and (visit.gestational_age_days or 0) >= 45:
                        weeks = (visit.gestational_age_days or 0) // 7
                        visit.gestational_age_days = weeks * 7 + round(val)
                elif canonical in {"ega_days", "GA_DAYS"} and parse_numeric(value) is not None:
                    val = parse_numeric(value)
                    if val >= 45:
                        visit.gestational_age_days = round(val)
                    else:
                        weeks = (visit.gestational_age_days or 0) // 7
                        visit.gestational_age_days = weeks * 7 + round(val)
                obs=CanonicalObservation(participant_id=p.id,visit_id=visit.id,source_batch_id=batch.id,canonical_variable=canonical,raw_source_value=value,parsed_text_value=value or None,numeric_value=parse_numeric(value),datetime_value=dt,coded_value=parse_coded(value),observation_datetime=dt or visit.visit_datetime,date_confidence="EXACT" if dt else ("INFERRED" if visit.visit_datetime else "MISSING"),source_form=form,source_page=row.get("Page Title"),source_field_label=row.get("Field Label"),source_row_number=row_no,mapping_version=MAPPING_VERSION,quality_status="VALID" if value else "MISSING",provenance_type="SOURCE_RECORDED",prohibited_flag=False,source_fingerprint=fp)
                db.add(obs); batch.rows_processed=row_no-1
                reconciliation["successfully_mapped_clinical_rows"] += 1
                if row_no%5000==0: db.commit()
            batch.rows_processed=total_rows
            current_validation = dict(batch.validation_result or {})
            current_validation["reconciliation"] = dict(reconciliation)
            batch.validation_result=current_validation
            batch.status="VISITS_RECONSTRUCTED"; db.commit()
        all_participants=db.query(LongitudinalParticipant).filter_by(source_batch_id=batch.id).all()
        # SQLite permits only one writer.  Do not retain its write lock for the
        # full derivation pass on a large import, otherwise another upload cannot
        # even create its import-batch record.
        for participant_index, p in enumerate(all_participants, start=1):
            pvis=db.query(VisitInstance).filter_by(participant_id=p.id,source_batch_id=batch.id).all(); dated=[v.visit_datetime for v in pvis if v.visit_datetime]
            p.available_visit_count=len(pvis); p.first_visit_date=min(dated) if dated else None; p.latest_visit_date=max(dated) if dated else None
            derive_participant(db,p,pvis); db.flush()
            finalize_history(db, p); db.flush()
            readiness = participant_import_readiness(p)
            p.workflow_status = "QC_APPROVED" if readiness.get("meets_auto_approval") else "MONITOR_QC_REQUIRED"
            audit_action = "PARTICIPANT_AUTO_QC_APPROVED" if p.workflow_status == "QC_APPROVED" else ("PARTICIPANT_AUTO_QC_WARNINGS" if readiness["status"] == "ACCEPTED_WITH_WARNINGS" else "PARTICIPANT_AUTO_QC_REJECTED")
            audit(db, batch.uploaded_by, "MONITOR_QC_REVIEWER", audit_action, "PARTICIPANT", p.id, {"readiness": readiness})
            if participant_index % 50 == 0:
                db.commit()
        batch.row_count=total_rows; batch.rows_processed=total_rows; batch.participant_count=len(all_participants); batch.visit_count=db.query(VisitInstance).filter_by(source_batch_id=batch.id).count()
        rv=dict(batch.validation_result or {})
        recon=dict(rv.get("reconciliation") or {})
        recon["visits_reconstructed"]=batch.visit_count
        readiness_counts={"visits_accepted":0,"visits_accepted_with_warnings":0,"visits_rejected":0}
        for participant in all_participants:
            readiness=participant_import_readiness(participant)
            readiness_counts["visits_accepted"] += readiness.get("accepted_visits", 0)
            readiness_counts["visits_accepted_with_warnings"] += readiness.get("warning_visits", 0)
            readiness_counts["visits_rejected"] += readiness.get("rejected_visits", 0)
        recon.update(readiness_counts)
        rv["reconciliation"]=recon
        batch.validation_result=rv
        batch.blinding_result={"passed":True,"excluded_rows":batch.prohibited_count,"safe_field_fingerprints":sorted(prohibited_labels)}
        batch.status="AUTO_QC_COMPLETE"; batch.error_count=0; batch.error_summary=None; batch.processing_finished_at=datetime.utcnow(); audit(db,batch.uploaded_by,"MONITOR_QC_REVIEWER","BATCH_AUTO_QC_COMPLETE","IMPORT_BATCH",batch.id,{"rows":batch.row_count,"participants":batch.participant_count,"visits":batch.visit_count,"prohibited_excluded":batch.prohibited_count}); db.commit()
    except Exception as exc:
        db.rollback(); batch=db.get(RTImportBatch,batch_id)
        if batch:
            batch.status="CANCELLED" if str(exc)=="IMPORT_CANCELLED" else "FAILED"; batch.error_count+=1; batch.error_summary=str(exc)[:1000]; batch.processing_finished_at=datetime.utcnow(); audit(db,batch.uploaded_by,"MONITOR_QC_REVIEWER","IMPORT_PROCESSING_FAILED","IMPORT_BATCH",batch.id,{"stage":batch.status,"error_type":type(exc).__name__},"FAILED"); db.commit()
    finally:
        db.close()

