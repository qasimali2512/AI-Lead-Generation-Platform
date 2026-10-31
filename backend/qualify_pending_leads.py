"""
One-time script: Qualify all pending leads in batches.
Run this once to fix the 3,231 leads stuck in 'pending' qualification status.
"""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models.lead import Lead
from app.services.lead_qualification import qualify_lead, calculate_qualification, save_qualification, get_latest_scan, get_website_issues, get_website_opportunity
from sqlalchemy import select

BATCH_SIZE = 100

db = SessionLocal()
try:
    total_qualified = 0
    batch_num = 0

    while True:
        pending_leads = list(
            db.scalars(
                select(Lead).where(
                    Lead.qualification_status == "pending"
                ).limit(BATCH_SIZE)
            ).all()
        )

        if not pending_leads:
            break

        batch_num += 1
        print(f"Batch {batch_num}: qualifying {len(pending_leads)} leads...")

        qualified_in_batch = 0
        for lead in pending_leads:
            try:
                scan = get_latest_scan(db=db, lead_id=lead.id, user_id=lead.user_id)
                issues = get_website_issues(db=db, lead_id=lead.id, user_id=lead.user_id)
                opportunity = get_website_opportunity(db=db, lead_id=lead.id, user_id=lead.user_id)
                data = calculate_qualification(lead=lead, scan=scan, issues=issues, opportunity=opportunity)
                save_qualification(db=db, lead=lead, data=data)
                qualified_in_batch += 1
            except Exception as e:
                print(f"  SKIP lead {lead.id}: {e}")

        try:
            db.commit()
            total_qualified += qualified_in_batch
            print(f"  Batch {batch_num} committed: {qualified_in_batch} leads qualified. Total so far: {total_qualified}")
        except Exception as e:
            db.rollback()
            print(f"  Batch {batch_num} commit FAILED: {e}")

    print(f"\nDone! Total leads qualified: {total_qualified}")

except Exception as e:
    db.rollback()
    print(f"FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
