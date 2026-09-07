"""
ACRN PROTECT-Africa / LOPE-Nigeria Endpoint Adjudication Platform
CLI Script: Reset & Re-seed Demo Environment
"""
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ["ENABLE_DEMO_ACCOUNTS"] = "true"
os.environ["ENABLE_DEMO_DATA"] = "true"

from database import Base, SessionLocal, engine
from services.demo_reset_service import reset_demo_environment


def main():
    print("=" * 65)
    print(" ACRN CLINICAL ENDPOINT ADJUDICATION PLATFORM")
    print(" Resetting and Re-seeding Demo Environment...")
    print("=" * 65)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        res = reset_demo_environment(db, reseed_cases=True)
        print("\n[OK] Reset completed successfully.")
        print(f" * Total purged test records : {res.get('total_purged', 0)}")
        print(f" * Demo accounts active     : {res.get('accounts_active', 0)} (Shared password: ACRN@2026)")
        cases = res.get('cases_reseeded', {})
        print(f" * Baseline cases re-seeded  : {cases.get('participants', 0)} participants, {cases.get('visits', 0)} visits, {cases.get('records', 0)} determinations")
        print(" * Governance rules active   : DV-01 to DV-30")
        print(" * Studies configured        : PROTECT-Africa (EOPE) & LOPE-Nigeria (LOPE)")
        print("\nReady for live testing in all 4 portals (Adjudicator, Chair, Monitor, Admin).")
        print("=" * 65)
    except Exception as exc:
        print(f"\n[ERROR] Error resetting demo environment: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
