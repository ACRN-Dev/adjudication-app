"""Additive operational records for the non-adjudicating Monitor/QC Portal."""
import uuid
from datetime import datetime
from sqlalchemy import Column,String,DateTime,Boolean,Text,JSON,Integer,ForeignKey,UniqueConstraint,event
from database import Base
def uid(): return str(uuid.uuid4())

class MonitorRecord(Base):
    __tablename__="monitor_records"
    id=Column(String(36),primary_key=True,default=uid); record_type=Column(String(40),nullable=False,index=True)
    study_code=Column(String(50),nullable=False,index=True); case_id=Column(String(50),index=True); status=Column(String(50),index=True)
    owner_upn=Column(String(255)); due_at=Column(DateTime,index=True); payload=Column(JSON,default=dict)
    version=Column(Integer,default=1); locked=Column(Boolean,default=False); is_demo=Column(Boolean,default=False,index=True)
    created_at=Column(DateTime,default=datetime.utcnow); updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

class MonitorImportBatch(Base):
    __tablename__="monitor_import_batches"
    id=Column(String(36),primary_key=True,default=uid); batch_id=Column(String(60),unique=True,nullable=False)
    study_code=Column(String(50),index=True); source_type=Column(String(30)); filename=Column(String(255)); checksum=Column(String(64),unique=True)
    file_size=Column(Integer); mapping_version=Column(String(40)); row_count=Column(Integer); participant_count=Column(Integer)
    validation_result=Column(String(40)); blinding_result=Column(String(40)); status=Column(String(40)); error_summary=Column(Text)
    imported_by=Column(String(255)); imported_at=Column(DateTime,default=datetime.utcnow); is_demo=Column(Boolean,default=False)

class ReconciliationItem(Base):
    __tablename__="monitor_reconciliation_items"
    id=Column(String(36),primary_key=True,default=uid); study_code=Column(String(50),index=True); case_id=Column(String(50),index=True)
    canonical_field=Column(String(100)); edc_value=Column(String(500)); esource_value=Column(String(500)); canonical_value=Column(String(500))
    source_used=Column(String(30)); discrepancy_category=Column(String(60)); clinically_meaningful=Column(Boolean); resolution_history=Column(JSON,default=list)
    is_demo=Column(Boolean,default=False)

class MonitorAuditEvent(Base):
    __tablename__="monitor_audit_events"
    id=Column(String(36),primary_key=True,default=uid); timestamp=Column(DateTime,default=datetime.utcnow,index=True)
    actor_upn=Column(String(255)); actor_role=Column(String(80)); action=Column(String(100),index=True); entity_type=Column(String(50)); entity_id=Column(String(80))
    study_code=Column(String(50),index=True); reason=Column(Text,nullable=False); outcome=Column(String(30)); details=Column(JSON); record_hash=Column(String(64)); is_demo=Column(Boolean,default=False)
@event.listens_for(MonitorAuditEvent,"before_update")
def no_update(*_): raise ValueError("Monitor audit events are immutable")
@event.listens_for(MonitorAuditEvent,"before_delete")
def no_delete(*_): raise ValueError("Monitor audit events are immutable")

