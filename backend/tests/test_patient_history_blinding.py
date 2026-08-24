import pytest
from sqlalchemy.orm import Session
from services.history_parser import sanitize_audit_trail
from models.history import PatientHistoryField

def test_blinding_audit_trail():
    raw_audit = "Makaha, Edward - 04/Mar/2026 01:20:21 PM CAT"
    dt, actor_hash = sanitize_audit_trail(raw_audit)
    
    # Must not contain any part of the name
    assert actor_hash is not None
    assert "Makaha" not in str(actor_hash)
    assert "Edward" not in str(actor_hash)
    
    raw_audit_2 = "Doe, Jane - 01/Jan/2026 10:00:00 AM"
    dt2, hash2 = sanitize_audit_trail(raw_audit_2)
    assert "Doe" not in str(hash2)
    assert "Jane" not in str(hash2)
    assert hash2 != actor_hash # Different actors should have different hashes
