import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models.auth import PortalUser

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def test_sso_managed_user_has_no_password_but_keeps_portal_role_and_scope():
    db = TestingSession()
    user = PortalUser(
        email="sso.admin@acrnhealth.com",
        display_name="SSO Admin",
        password_hash=None,
        role="ADMIN",
        portal_role="TECHNICAL_ADMIN",
        study_scope="PROTECT-Africa",
    )
    db.add(user)
    db.commit()
    fetched = db.query(PortalUser).filter_by(email="sso.admin@acrnhealth.com").first()
    assert fetched.password_hash is None
    assert fetched.portal_role == "TECHNICAL_ADMIN"
    assert fetched.study_scope == "PROTECT-Africa"
    db.close()


def test_study_scope_defaults_to_wildcard_and_portal_role_defaults_to_none():
    db = TestingSession()
    user = PortalUser(
        email="plain.adjudicator@acrnhealth.com",
        display_name="Plain Adjudicator",
        password_hash="some-hash",
        role="ADJUDICATOR",
    )
    db.add(user)
    db.commit()
    fetched = db.query(PortalUser).filter_by(email="plain.adjudicator@acrnhealth.com").first()
    assert fetched.portal_role is None
    assert fetched.study_scope == "*"
    db.close()
