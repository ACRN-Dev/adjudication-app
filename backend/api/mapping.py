"""
Field Mapping API — GET/POST /api/mappings
Administrative screen configuration for EDC -> Canonical and eSource -> Canonical mappings.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db
from models.canonical import MappingRule, SourceSystem

router = APIRouter()


class MappingRuleCreate(BaseModel):
    canonical_field: str
    edc_field: Optional[str] = None
    esource_field: Optional[str] = None
    authority: SourceSystem = SourceSystem.EDC
    transformation: Optional[str] = None
    unit_in: Optional[str] = None
    unit_out: Optional[str] = None
    version: str = "1.0"
    notes: Optional[str] = None


class MappingRuleResponse(MappingRuleCreate):
    id: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[MappingRuleResponse])
def get_mappings(db: Session = Depends(get_db)):
    rules = db.query(MappingRule).filter_by(is_active=True).all()
    return [
        MappingRuleResponse(
            id=str(r.id),
            canonical_field=r.canonical_field,
            edc_field=r.edc_field,
            esource_field=r.esource_field,
            authority=r.authority,
            transformation=r.transformation,
            unit_in=r.unit_in,
            unit_out=r.unit_out,
            version=r.version,
            notes=r.notes,
            is_active=r.is_active,
            created_at=r.created_at.isoformat() if r.created_at else ""
        ) for r in rules
    ]


@router.post("", response_model=MappingRuleResponse)
def create_mapping(rule: MappingRuleCreate, db: Session = Depends(get_db)):
    db_rule = MappingRule(
        canonical_field=rule.canonical_field,
        edc_field=rule.edc_field,
        esource_field=rule.esource_field,
        authority=rule.authority,
        transformation=rule.transformation,
        unit_in=rule.unit_in,
        unit_out=rule.unit_out,
        version=rule.version,
        notes=rule.notes
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return MappingRuleResponse(
        id=str(db_rule.id),
        canonical_field=db_rule.canonical_field,
        edc_field=db_rule.edc_field,
        esource_field=db_rule.esource_field,
        authority=db_rule.authority,
        transformation=db_rule.transformation,
        unit_in=db_rule.unit_in,
        unit_out=db_rule.unit_out,
        version=db_rule.version,
        notes=db_rule.notes,
        is_active=db_rule.is_active,
        created_at=db_rule.created_at.isoformat() if db_rule.created_at else ""
    )
