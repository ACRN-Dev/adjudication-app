"""Development-only seed command for fixed ACRN demo accounts."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import Base, SessionLocal, engine
from models import auth  # noqa: F401
from services.auth_service import DEMO_ACCOUNTS, seed_demo_accounts


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        created = seed_demo_accounts(db)
        print(f"Demo accounts ready. Created {created}; total fixed accounts {len(DEMO_ACCOUNTS)}.")
    finally:
        db.close()
